"""Timing core, baseline storage and run-to-run comparison.

Modelled on criterion's workflow: a run compares itself against the stored
baseline from the previous run and then replaces it. Nothing about the old
implementation needs to stay in the tree; the baseline is a JSON file of
numbers, so the comparison survives the code it measured.

Deliberately not pytest-benchmark: this needs to be runnable by a user who
installed the package without dev extras, and needs a throughput mode that
spawns a server process, which does not sit well inside a test session.
"""

from __future__ import annotations

import json
import math
import platform
import re
import statistics
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Sequence

BASELINE_DIR = Path(__file__).parent / ".baselines"

#: Relative change below this is treated as noise regardless of the spread.
#: Wall-clock benchmarks on a laptop with a scaling governor do not resolve
#: better than this.
NOISE_THRESHOLD = 0.05


@dataclass
class Result:
    """One benchmark's measurement."""

    name: str
    #: Median nanoseconds per operation.
    median_ns: float
    #: Interquartile range of per-sample ns/op, the spread used to decide
    #: whether a change is real.
    q1_ns: float
    q3_ns: float
    min_ns: float
    samples: int
    iters_per_sample: int
    #: Bytes moved per operation, when the benchmark knows. Drives the MiB/s
    #: column; zero means the column is omitted.
    bytes_per_op: int = 0
    #: Free-form extras a benchmark wants to carry into the report.
    meta: dict = field(default_factory=dict)

    @property
    def ops_per_sec(self) -> float:
        return 1e9 / self.median_ns if self.median_ns else math.inf

    @property
    def mib_per_sec(self) -> float:
        return self.ops_per_sec * self.bytes_per_op / (1024 * 1024)


@dataclass
class Comparison:
    name: str
    current: Result
    previous: Result | None

    @property
    def delta(self) -> float | None:
        if self.previous is None or not self.previous.median_ns:
            return None
        return (self.current.median_ns - self.previous.median_ns) / self.previous.median_ns

    @property
    def verdict(self) -> str:
        previous = self.previous
        if previous is None:
            return "new"
        d = self.delta
        if d is None or abs(d) < NOISE_THRESHOLD:
            return "same"
        # Require the spreads to be disjoint before calling it. Two runs whose
        # interquartile ranges overlap have not demonstrated anything.
        if self.current.q3_ns < previous.q1_ns:
            return "faster"
        if self.current.q1_ns > previous.q3_ns:
            return "slower"
        return "noisy"


class Bench:
    """A named unit of work to time.

    ``setup`` runs once per sample outside the timed region, and its return
    value is passed to ``fn``. Use it for anything that would otherwise be
    measured by accident, such as building the input payload.
    """

    def __init__(
        self,
        name: str,
        fn: Callable,
        *,
        setup: Callable[[], object] | None = None,
        bytes_per_op: int = 0,
        meta: dict | None = None,
    ) -> None:
        self.name = name
        self.fn = fn
        self.setup = setup
        self.bytes_per_op = bytes_per_op
        self.meta = meta or {}


def _time_loop(fn: Callable, arg: object, iters: int, has_arg: bool) -> int:
    """Time ``iters`` calls, returning elapsed nanoseconds.

    The two branches are spelled out rather than resolved per iteration so the
    argument check does not land inside the measured loop.
    """
    if has_arg:
        t0 = time.perf_counter_ns()
        for _ in range(iters):
            fn(arg)
        return time.perf_counter_ns() - t0
    t0 = time.perf_counter_ns()
    for _ in range(iters):
        fn()
    return time.perf_counter_ns() - t0


def run_bench(bench: Bench, *, samples: int = 20, min_time_ms: float = 50.0) -> Result:
    """Calibrate an iteration count, then take ``samples`` timed batches."""
    has_arg = bench.setup is not None
    arg = bench.setup() if bench.setup else None

    # Calibration: grow the batch until it runs long enough that timer
    # granularity and loop overhead stop dominating.
    iters = 1
    while True:
        elapsed = _time_loop(bench.fn, arg, iters, has_arg)
        if elapsed >= min_time_ms * 1e6:
            break
        if elapsed == 0:
            iters *= 100
            continue
        scale = (min_time_ms * 1e6) / elapsed
        iters = max(iters + 1, int(iters * min(scale * 1.2, 50)))
        if iters > 100_000_000:
            break

    # Warmup, discarded.
    _time_loop(bench.fn, arg, iters, has_arg)

    per_op: list[float] = []
    for _ in range(samples):
        if bench.setup:
            arg = bench.setup()
        elapsed = _time_loop(bench.fn, arg, iters, has_arg)
        per_op.append(elapsed / iters)

    per_op.sort()
    quantiles = statistics.quantiles(per_op, n=4) if len(per_op) >= 4 else [per_op[0], per_op[0], per_op[-1]]
    return Result(
        name=bench.name,
        median_ns=statistics.median(per_op),
        q1_ns=quantiles[0],
        q3_ns=quantiles[2],
        min_ns=per_op[0],
        samples=samples,
        iters_per_sample=iters,
        bytes_per_op=bench.bytes_per_op,
        meta=dict(bench.meta),
    )


def run_all(benches: Iterable[Bench], *, samples: int, min_time_ms: float, echo: bool = True) -> list[Result]:
    results = []
    for bench in benches:
        if echo:
            print(f"  running {bench.name} ...", end="", flush=True)
        result = run_bench(bench, samples=samples, min_time_ms=min_time_ms)
        if echo:
            print(f" {_fmt_time(result.median_ns)}")
        results.append(result)
    return results


# -- baselines ------------------------------------------------------------


def _git_rev() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=Path(__file__).parent,
        )
        rev = out.stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True, timeout=5, cwd=Path(__file__).parent
        ).stdout.strip()
        return f"{rev}{'-dirty' if dirty else ''}" if rev else "unknown"
    except Exception:
        return "unknown"


def environment() -> dict:
    return {
        "python": sys.version.split()[0],
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "git": _git_rev(),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }


def _series(name: str) -> str:
    """Reduce a series name to one safe path component.

    Branch names carry slashes, and '@' is the separator between series and
    timestamp, so both have to go. Applied on save and on load alike, or a
    lookup would miss the file it just wrote.
    """
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-.")
    if not slug:
        raise ValueError(f"series name {name!r} has no usable characters")
    return slug


def _stamp() -> str:
    """UTC, lexicographically sortable, milliseconds to survive two runs a second apart."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y%m%dT%H%M%S") + f"{now.microsecond // 1000:03d}Z"


def _latest(name: str) -> Path | None:
    """Newest recording in a series. Sortable stamps make this a max(), not a stat() loop."""
    recordings = sorted(BASELINE_DIR.glob(f"{_series(name)}@*.json"))
    return recordings[-1] if recordings else None


def save_baseline(name: str, results: Sequence[Result]) -> Path:
    """Write a new recording. Never overwrites: every run is kept."""
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    path = BASELINE_DIR / f"{_series(name)}@{_stamp()}.json"
    payload = {"environment": environment(), "results": [asdict(r) for r in results]}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def load_baseline(name: str) -> tuple[dict, dict[str, Result]]:
    """Most recent recording in the series, or empty if there is none."""
    path = _latest(name)
    if path is None:
        return {}, {}
    payload = json.loads(path.read_text())
    results = {}
    for raw in payload.get("results", []):
        raw.setdefault("meta", {})
        results[raw["name"]] = Result(**raw)
    return payload.get("environment", {}), results


def merge_into_baseline(name: str, results: Sequence[Result]) -> Path:
    """Write ``results`` into a baseline, keeping entries this run did not touch.

    A filtered run, or a throughput-only run, should not silently delete the
    benchmarks it skipped: the next full run would then report every one of
    them as new and the comparison would be lost.
    """
    _, existing = load_baseline(name)
    existing.update({r.name: r for r in results})
    return save_baseline(name, list(existing.values()))


def compare(current: Sequence[Result], previous: dict[str, Result]) -> list[Comparison]:
    return [Comparison(name=r.name, current=r, previous=previous.get(r.name)) for r in current]


# -- reporting ------------------------------------------------------------

_VERDICT_MARK = {"faster": "-", "slower": "+", "same": "=", "noisy": "?", "new": "*"}


def _fmt_time(ns: float) -> str:
    if ns < 1_000:
        return f"{ns:,.0f} ns"
    if ns < 1_000_000:
        return f"{ns / 1_000:,.2f} us"
    return f"{ns / 1_000_000:,.2f} ms"


def _fmt_rate(ops: float) -> str:
    if ops >= 1e6:
        return f"{ops / 1e6:,.2f}M/s"
    if ops >= 1e3:
        return f"{ops / 1e3:,.1f}k/s"
    return f"{ops:,.0f}/s"


def report(comparisons: Sequence[Comparison], baseline_name: str | None, *, show_bytes: bool = True) -> None:
    if not comparisons:
        print("no benchmarks matched")
        return

    name_w = max(len(c.name) for c in comparisons) + 2
    has_bytes = show_bytes and any(c.current.bytes_per_op for c in comparisons)

    header = f"{'benchmark':<{name_w}}{'median':>12}{'rate':>12}"
    if has_bytes:
        header += f"{'throughput':>16}"
    header += f"{'vs ' + (baseline_name or 'n/a'):>16}"
    print()
    print(header)
    print("-" * len(header))

    for c in comparisons:
        row = f"{c.name:<{name_w}}{_fmt_time(c.current.median_ns):>12}{_fmt_rate(c.current.ops_per_sec):>12}"
        if has_bytes:
            mib = f"{c.current.mib_per_sec:,.1f} MiB/s" if c.current.bytes_per_op else ""
            row += f"{mib:>16}"
        delta = c.delta
        change = "new" if delta is None else f"{_VERDICT_MARK[c.verdict]}{abs(delta) * 100:5.1f}% {c.verdict}"
        row += f"{change:>16}"
        print(row)
    print()


def report_env(env: dict, previous_env: dict | None = None) -> None:
    print(f"env: {env['implementation']} {env['python']} on {env['machine']}, git {env['git']}")
    if previous_env and previous_env.get("timestamp"):
        print(f"baseline recorded at git {previous_env.get('git', '?')} on {previous_env['timestamp']}")
    if previous_env and previous_env.get("python") and previous_env["python"] != env["python"]:
        print(
            f"WARNING: baseline ran on Python {previous_env['python']}, this run is {env['python']}. "
            "Cross-version deltas are not attributable to your code."
        )


def markdown_table(comparisons: Sequence[Comparison]) -> str:
    """Render results as markdown, for pasting into the README."""
    has_bytes = any(c.current.bytes_per_op for c in comparisons)
    header = "| benchmark | median | rate |" + (" throughput |" if has_bytes else "")
    rule = "| --- | ---: | ---: |" + (" ---: |" if has_bytes else "")
    rows = [header, rule]
    for c in comparisons:
        row = f"| `{c.name}` | {_fmt_time(c.current.median_ns)} | {_fmt_rate(c.current.ops_per_sec)} |"
        if has_bytes:
            row += f" {c.current.mib_per_sec:,.1f} MiB/s |" if c.current.bytes_per_op else " |"
        rows.append(row)
    return "\n".join(rows) + "\n"
