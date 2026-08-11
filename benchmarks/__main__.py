"""Benchmarks for the Derive WebSocket client. ``python -m benchmarks --help``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from benchmarks import bench_decode
from benchmarks.corpus import DEFAULT_THROUGHPUT_CHANNELS
from benchmarks.harness import (
    BASELINE_DIR,
    compare,
    environment,
    load_baseline,
    markdown_table,
    merge_into_baseline,
    report,
    report_env,
    run_all,
)

DEFAULT_SERIES = "local"
SUITES = {"decode": bench_decode.benches}


def _collect(seed: int, pattern: str | None):
    benches = [b for suite in SUITES.values() for b in suite(seed=seed)]
    return [b for b in benches if pattern in b.name] if pattern else benches


def _finish(args, results, previous) -> None:
    comparisons = compare(results, previous)
    report(comparisons, args.baseline if previous else None)
    if args.markdown:
        Path(args.markdown).write_text(markdown_table(comparisons))
    if not args.no_save:
        print(f"baseline written to {merge_into_baseline(args.save_baseline or DEFAULT_SERIES, results)}")


def cmd_list(args) -> int:
    from benchmarks.bench_throughput import channels, rpc_cases

    for bench in _collect(args.seed, args.filter):
        print(bench.name)
    for name in channels(args.seed):
        print(f"ws/notify/{name}/{{async,sync,control}}")
    for name in rpc_cases(args.seed):
        print(f"ws/rpc/{name}")
    return 0


def cmd_decode(args) -> int:
    benches = _collect(args.seed, args.filter)
    if not benches:
        print("no benchmarks matched", file=sys.stderr)
        return 1

    env = environment()
    prev_env, previous = load_baseline(args.baseline)
    report_env(env, prev_env)
    print(f"{len(benches)} benchmarks, {args.samples} samples each")

    results = run_all(benches, samples=args.samples, min_time_ms=args.min_time_ms)
    _finish(args, results, previous)
    return 0


def cmd_ws(args) -> int:
    from benchmarks.bench_throughput import channels, rpc_cases, run_notifications, run_rpc

    env = environment()
    prev_env, previous = load_baseline(args.baseline)
    report_env(env, prev_env)

    available = channels(args.seed)
    results = []
    for name in args.channel:
        if name not in available:
            print(f"unknown channel {name!r}, try: {', '.join(available)}", file=sys.stderr)
            return 1
        for mode in args.mode:
            print(f"  running ws/notify/{name}/{mode} ...", end="", flush=True)
            result = run_notifications(
                available[name],
                messages=args.messages,
                warmup=args.warmup,
                repeats=args.repeats,
                mode=mode,
            )
            print(f" {result.ops_per_sec:,.0f} msg/s")
            results.append(result)

    if args.rpc:
        cases = rpc_cases(args.seed)
        for name in args.rpc:
            if name not in cases:
                print(f"unknown rpc case {name!r}, try: {', '.join(cases)}", file=sys.stderr)
                return 1
            for concurrency in args.concurrency:
                for control in (False, True):
                    label = "control" if control else f"c{concurrency}"
                    print(f"  running ws/rpc/{name}/{label} ...", end="", flush=True)
                    result = run_rpc(
                        cases[name],
                        requests=args.requests,
                        repeats=args.repeats,
                        concurrency=concurrency,
                        control=control,
                    )
                    print(f" {result.ops_per_sec:,.0f} req/s")
                    results.append(result)

    _finish(args, results, previous)
    for result in results:
        if "peak_rss_mib" in result.meta:
            print(f"{result.name}: peak RSS {result.meta['peak_rss_mib']} MiB")
    return 0


def cmd_history(args) -> int:
    from benchmarks.history import report_history

    return report_history(args.base, pattern=args.filter, markdown=args.markdown)


def cmd_baselines(args) -> int:
    import json

    if not BASELINE_DIR.exists():
        print("no baselines recorded")
        return 0
    for path in sorted(BASELINE_DIR.glob("*.json")):
        payload = json.loads(path.read_text())
        env = payload.get("environment", {})
        series, _, stamp = path.stem.partition("@")
        print(f"{series:<16} {stamp:<20} {env.get('git', '?'):<20} {len(payload['results'])} results")
    return 0


def main(argv: list[str] | None = None) -> int:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--seed", type=int, default=0, help="synthetic data seed (default: 0)")
    common.add_argument("--filter", help="substring match on benchmark name")
    common.add_argument("--baseline", default=DEFAULT_SERIES, help="series to compare against (default: local)")
    common.add_argument("--save-baseline", help="series to file this run under (default: local)")
    common.add_argument("--no-save", action="store_true", help="compare only, leave the baseline untouched")
    common.add_argument("--markdown", help="write a markdown table here, for the README")

    parser = argparse.ArgumentParser(prog="python -m benchmarks", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_ws = sub.add_parser("ws", parents=[common], help="messages/second over a real WebSocket connection")
    p_ws.add_argument("--channel", action="append", help="corpus channel (repeatable)")
    p_ws.add_argument("--mode", action="append", choices=["async", "sync", "control"])
    p_ws.add_argument("--messages", type=int, default=20_000)
    p_ws.add_argument("--warmup", type=int, default=2_000)
    p_ws.add_argument("--repeats", type=int, default=5)
    p_ws.add_argument("--rpc", action="append", help="also run an RPC case (repeatable)")
    p_ws.add_argument("--requests", type=int, default=2_000)
    p_ws.add_argument("--concurrency", action="append", type=int)
    p_ws.set_defaults(func=cmd_ws)

    p_dec = sub.add_parser("decode", parents=[common], help="decode costs, the denominator for ws numbers")
    p_dec.add_argument("--samples", type=int, default=20)
    p_dec.add_argument("--min-time-ms", type=float, default=50.0)
    p_dec.set_defaults(func=cmd_decode)

    p_list = sub.add_parser("list", parents=[common], help="list benchmark names")
    p_list.set_defaults(func=cmd_list)

    p_hist = sub.add_parser("history", parents=[common], help="how the benchmarks moved across this branch")
    p_hist.add_argument("--base", default="main", help="branch to diff against (default: main)")
    p_hist.set_defaults(func=cmd_history)

    p_base = sub.add_parser("baselines", parents=[common], help="show recorded baselines")
    p_base.set_defaults(func=cmd_baselines)

    raw = list(sys.argv[1:] if argv is None else argv)
    if not raw or raw[0].startswith("-"):
        raw = ["ws", *raw]  # bare invocation answers the headline question

    args = parser.parse_args(raw)
    if args.command == "ws":
        args.channel = args.channel or list(DEFAULT_THROUGHPUT_CHANNELS)
        args.mode = args.mode or ["async", "control"]
        args.concurrency = args.concurrency or [1, 32]
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
