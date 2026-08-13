"""Summarise how the benchmarks moved across the commits on this branch.

Answers one question: which commit bought which improvement. Reads every
recording in ``.baselines``, keeps only results measured at a clean tree on a
commit in the branch range, and lines them up in commit order.

Two problems have to be handled or the output lies.

Dirty trees. A result measured with uncommitted changes cannot be attributed
to any commit, so it is discarded rather than charged to whatever HEAD
happened to be.

Machine drift. Wall-clock medians recorded hours apart on a laptop are not
comparable: a governor change alone moves everything 30%. Every run carries
benchmarks that no library change can affect (the raw-recv controls and the
bare UTF-8 decodes), so the run's speed relative to the others is measurable
from its own data and divided back out. The correction is reported, not hidden;
a run needing more than a few percent should make you read the adjusted column
only.
"""

from __future__ import annotations

import json
import re
import statistics
import subprocess
from dataclasses import dataclass
from pathlib import Path

from benchmarks.harness import BASELINE_DIR, Result, _fmt_time

#: Benchmarks that measure the machine rather than the library: a bare recv
#: loop with no session, and bytes.decode on a fixed buffer. Their movement
#: between runs is drift by definition.
CONTROL_PATTERNS = (
    re.compile(r"^ws/notify/.+/control$"),
    re.compile(r"^ws/rpc/.+/control(_c\d+)?$"),
    re.compile(r"^decode/utf8/.+$"),
)

#: Above this, absolute numbers should not be compared across runs at all.
DRIFT_WARN = 0.10


def is_control(name: str) -> bool:
    return any(p.match(name) for p in CONTROL_PATTERNS)


@dataclass
class Run:
    """One recording, reduced to what the comparison needs."""

    git: str
    stamp: str
    results: dict[str, Result]
    environment: dict
    #: How much slower this run's machine was than the median across runs.
    #: 1.0 is the reference speed; 1.2 means everything took 20% longer.
    drift: float = 1.0

    def adjusted(self, name: str) -> float | None:
        result = self.results.get(name)
        return result.median_ns / self.drift if result else None


# -- git ------------------------------------------------------------------


def _git(*args: str) -> str:
    out = subprocess.run(
        ["git", *args], capture_output=True, text=True, timeout=10, cwd=Path(__file__).parent, check=False
    )
    if out.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed: {out.stderr.strip()}")
    return out.stdout.strip()


def branch_commits(base: str) -> list[tuple[str, str]]:
    """(short sha, subject) for the branch range, oldest first."""
    merge_base = _git("merge-base", "HEAD", base)
    log = _git("log", "--format=%h%x09%s", f"{merge_base}..HEAD")
    rows = [(sha, subject) for sha, _, subject in (line.partition("\t") for line in log.splitlines() if line)]
    return list(reversed(rows))


# -- loading --------------------------------------------------------------


def load_runs(commits: set[str]) -> tuple[list[Run], dict[str, int]]:
    """Every recording whose results belong to a clean commit in ``commits``.

    Results are filtered individually rather than by file: merge_into_baseline
    carries untouched entries forward, so one recording can hold results from
    several commits.
    """
    runs: list[Run] = []
    discarded: dict[str, int] = {}

    for path in sorted(BASELINE_DIR.glob("*@*.json")):
        payload = json.loads(path.read_text())
        environment = payload.get("environment", {})
        stamp = path.stem.partition("@")[2]

        by_commit: dict[str, dict[str, Result]] = {}
        for raw in payload.get("results", []):
            raw.setdefault("meta", {})
            raw.setdefault("git", environment.get("git", ""))
            git = raw["git"]
            if git.endswith("-dirty") or git not in commits:
                discarded[git or "unknown"] = discarded.get(git or "unknown", 0) + 1
                continue
            by_commit.setdefault(git, {})[raw["name"]] = Result(**raw)

        for git, results in by_commit.items():
            runs.append(Run(git=git, stamp=stamp, results=results, environment=environment))

    return runs, discarded


def latest_per_commit(runs: list[Run], commits: list[tuple[str, str]]) -> list[Run]:
    """One run per commit, newest kept, in commit order rather than clock order.

    A run recorded later may belong to an earlier commit; the branch's history
    is the axis worth plotting against.
    """
    newest: dict[str, Run] = {}
    for run in sorted(runs, key=lambda r: r.stamp):
        if run.git in newest:
            # Merge rather than replace: a `decode` run and a `ws` run at the
            # same commit are two recordings covering different benchmarks.
            newest[run.git].results.update(run.results)
            newest[run.git].stamp = run.stamp
            newest[run.git].environment = run.environment
        else:
            newest[run.git] = run
    return [newest[sha] for sha, _ in commits if sha in newest]


# -- drift ----------------------------------------------------------------


def apply_drift(runs: list[Run]) -> list[str]:
    """Set ``Run.drift`` from the control benchmarks. Returns any warnings."""
    control_names = sorted({n for run in runs for n in run.results if is_control(n)})
    if not control_names or len(runs) < 2:
        return []

    reference = {
        name: statistics.median([run.results[name].median_ns for run in runs if name in run.results])
        for name in control_names
    }

    warnings = []
    for run in runs:
        ratios = [
            run.results[name].median_ns / reference[name]
            for name in control_names
            if name in run.results and reference[name]
        ]
        if not ratios:
            warnings.append(f"{run.git}: no control benchmarks, absolute numbers not comparable")
            continue
        run.drift = statistics.median(ratios)

    spread = max(r.drift for r in runs) / min(r.drift for r in runs) - 1
    if spread > DRIFT_WARN:
        warnings.append(
            f"machine speed varied {spread * 100:.0f}% across runs; the adjusted column "
            "divides it out, the raw column does not"
        )

    resolution = _resolution(runs, control_names)
    if resolution:
        warnings.append(f"resolution after correction: +/-{resolution * 100:.0f}%; smaller changes are not claims")
    return warnings


def _resolution(runs: list[Run], control_names: list[str]) -> float:
    """How far the corrected controls still disagree between runs.

    A control measures the machine, not the library, so after correction its
    value should be identical everywhere. Whatever spread survives is the
    method's error, and no reported change smaller than it means anything.
    Better than a fixed threshold: it is derived from the same runs being
    compared, so a quiet machine earns a tighter bound.
    """
    spreads = []
    for name in control_names:
        values = [v for v in (run.adjusted(name) for run in runs) if v]
        if len(values) > 1 and min(values):
            spreads.append(max(values) / min(values) - 1)
    return statistics.median(spreads) if spreads else 0.0


# -- reporting ------------------------------------------------------------


def channel_rows(runs: list[Run]) -> list[str]:
    """Per-channel table: what one notification costs, and how much is ours."""
    channels = sorted(
        {
            name.split("/")[2]
            for run in runs
            for name in run.results
            if name.startswith("ws/notify/") and name.endswith("/async")
        }
    )

    lines = []
    for channel in channels:
        lines.append("")
        lines.append(channel)
        lines.append(f"  {'commit':<9}{'total':>10}{'floor':>10}{'client':>10}{'vs prev':>10}  subject")

        previous = None
        for run in runs:
            total = run.adjusted(f"ws/notify/{channel}/async")
            floor = run.adjusted(f"ws/notify/{channel}/control")
            if total is None or floor is None:
                continue
            client = total - floor
            change = "-" if previous is None else f"{(client - previous) / previous * 100:+.1f}%"
            previous = client
            subject = run.environment.get("subject", "")
            lines.append(
                f"  {run.git:<9}{_fmt_time(total):>10}{_fmt_time(floor):>10}"
                f"{_fmt_time(client):>10}{change:>10}  {subject}"
            )
    return lines


def benchmark_rows(runs: list[Run], pattern: str) -> list[str]:
    """Every non-control benchmark matching ``pattern``, one row per benchmark."""
    names = sorted({n for run in runs for n in run.results if not is_control(n) and pattern in n})
    if not names:
        return []

    width = max(len(n) for n in names) + 2
    lines = ["", f"  {'benchmark':<{width}}" + "".join(f"{run.git:>11}" for run in runs) + f"{'total':>10}"]
    for name in names:
        values = [run.adjusted(name) for run in runs]
        cells = "".join(f"{_fmt_time(v) if v else '-':>11}" for v in values)
        seen = [v for v in values if v]
        total = f"{(seen[-1] - seen[0]) / seen[0] * 100:+.1f}%" if len(seen) > 1 else "-"
        lines.append(f"  {name:<{width}}{cells}{total:>10}")
    return lines


def report_history(base: str, pattern: str | None = None, markdown: str | None = None) -> int:
    commits = branch_commits(base)
    commit_subjects = dict(commits)
    runs, discarded = load_runs(set(commit_subjects))

    if not runs:
        print("No clean results for any commit on this branch.")
        if discarded:
            print("Discarded:", ", ".join(f"{k} ({v})" for k, v in sorted(discarded.items())))
        return 1

    runs = latest_per_commit(runs, commits)
    for run in runs:
        run.environment = {**run.environment, "subject": commit_subjects[run.git]}

    fields = ("python", "implementation", "machine", "platform")
    for field_name in fields:
        values = {run.environment.get(field_name) for run in runs}
        if len(values) > 1:
            print(f"ABORT: runs differ in {field_name}: {sorted(map(str, values))}")
            print("Results recorded on different interpreters or hosts cannot be compared.")
            return 1

    first = runs[0].environment
    print(f"Benchmark history against {base}")
    print(f"{len(commits)} commits in range, {len(runs)} with clean results")
    print(f"env: {first.get('implementation')} {first.get('python')} on {first.get('machine')}")
    if discarded:
        print("discarded: " + ", ".join(f"{k} ({v} results)" for k, v in sorted(discarded.items())))

    for warning in apply_drift(runs):
        print(f"! {warning}")

    corrections = ", ".join(f"{run.git} {run.drift:.2f}x" for run in runs)
    print(f"drift correction: {corrections}")

    for line in channel_rows(runs):
        print(line)
    if pattern:
        for line in benchmark_rows(runs, pattern):
            print(line)
    print()

    if markdown:
        Path(markdown).write_text(markdown_history(runs))
        print(f"markdown written to {markdown}")
    return 0


def markdown_history(runs: list[Run]) -> str:
    """Per-channel markdown, for pasting into a pull request."""
    channels = sorted(
        {
            name.split("/")[2]
            for run in runs
            for name in run.results
            if name.startswith("ws/notify/") and name.endswith("/async")
        }
    )

    out = []
    for channel in channels:
        out.append(f"**`{channel}`**\n")
        out.append("| commit | subject | total | floor | client | vs prev |")
        out.append("| --- | --- | ---: | ---: | ---: | ---: |")
        previous = None
        for run in runs:
            total = run.adjusted(f"ws/notify/{channel}/async")
            floor = run.adjusted(f"ws/notify/{channel}/control")
            if total is None or floor is None:
                continue
            client = total - floor
            change = "-" if previous is None else f"{(client - previous) / previous * 100:+.1f}%"
            previous = client
            subject = run.environment.get("subject", "")
            out.append(
                f"| `{run.git}` | {subject} | {_fmt_time(total)} | {_fmt_time(floor)} "
                f"| {_fmt_time(client)} | {change} |"
            )
        out.append("")
    out.append(
        "`floor` is a raw recv loop with no session, measured in the same run; `client` is "
        "`total - floor`, i.e. envelope decode, payload decode and dispatch. Medians are "
        "corrected for machine speed using the run's own control benchmarks. Loopback, no TLS, "
        "no-op handler, synthetic payloads."
    )
    return "\n".join(out) + "\n"
