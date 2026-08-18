# WebSocket client benchmarks

How many messages per second the WebSocket client takes off a socket, decodes
and hands to a callback. Measurement, not assertion: nothing here fails a build.

```sh
make bench                  # messages/second, the headline number
make bench-decode           # decode costs, the denominator for the above
python -m benchmarks list   # names, for --channel and --filter
```

Scope is the WebSocket transport. REST is not covered, and neither is action
signing, which costs more than everything measured here put together and would
drown the signal.

## What runs

Everything goes through the surface a user touches: `WebSocketSession` and the
generated methods on `PublicChannels` and the RPC classes. Nothing reaches into
internals, so a rewrite of the receive path leaves old recordings comparable.

| benchmark | measures |
| --- | --- |
| `ws/notify/<channel>/async` | one notification, `async def` callback |
| `ws/notify/<channel>/sync` | the same with a plain callback |
| `ws/notify/<channel>/control` | raw `recv` loop: no session, no decode |
| `ws/rpc/<method>/c<N>` | one round trip, N requests in flight |
| `ws/rpc/<method>/control_c<N>` | the same with hand-rolled frames |
| `decode/envelope/<channel>` | first-pass JSON-RPC decode |
| `decode/payload/<channel>` | one typed decode of the payload bytes |
| `decode/utf8/<channel>` | `bytes.decode` on the frame |

**Read the control rows first.** They contain no library code, so they measure
the machine and the harness. If a client rate sits near its control, the
harness is the bottleneck and the client number is a floor, not a measurement.

`decode/payload` is the hard lower bound on the receive path: the payload has
to be decoded whatever else changes.

## Why synthetic traffic

A live feed answers a different question. Subscription rates are capped by the
exchange's publish intervals, testnet carries no order flow, and RPC volume
hits the account rate limit long before it hits the client. The feeder here
writes pre-framed bytes as fast as loopback accepts them, which is faster than
any exchange — that is the point, since the number wanted is the client's
ceiling.

`synth.py` walks a msgspec type with `msgspec.inspect` and fabricates a
plausible value per leaf, seeded, so two runs on one commit produce identical
frames. A change in measured time is then a change in the code, not the data.
Values are plausible but not valid: nothing honours cross-field invariants.

Payload types come from `channel_models`, so a spec regeneration that changes a
channel changes the benchmark. That is the correct failure mode.

## Comparing two runs

Recordings live in `benchmarks/.baselines/<series>@<utc-stamp>.json`,
gitignored. Nothing is overwritten; a comparison resolves to the newest
recording in the series, and each run merges into it rather than replacing it,
so a filtered run does not drop the rows it skipped.

```sh
git switch main
python -m benchmarks ws --save-baseline main    # record the reference

git switch my-branch
python -m benchmarks ws --baseline main         # compare; this run files under local
```

`--baseline` is what you measure against, `--save-baseline` is where the run is
filed. They default apart so comparing against a reference cannot pollute it.

A change reads `faster` or `slower` only if it exceeds 5% *and* the
interquartile ranges are disjoint. On a laptop with a scaling governor, take
more samples (`--repeats` for `ws`, `--samples` for `decode`) or raise
`NOISE_THRESHOLD` in `harness.py`.

## Attributing changes to commits

`history` compares a whole branch instead of two runs.

```sh
python -m benchmarks history --base main
python -m benchmarks history --base main --markdown /tmp/bench.md   # table for a PR
python -m benchmarks history --base main --filter decode/           # per-benchmark grid
```

It keeps results measured at a clean tree on a commit in `<base>..HEAD`, takes
the newest per commit, and prints one row per commit in commit order. Results
from a dirty tree are discarded and counted, since they belong to no commit. It
aborts if the runs disagree on Python version, interpreter, machine or platform.

Two things it adds beyond the raw median:

- `floor` is that run's `control`; `client` is `total - floor`, the part the
  library controls.
- Medians are **corrected for machine speed**. Every run contains benchmarks no
  library change can affect, so the run's speed relative to the others is
  measurable from its own data and divided back out. The correction is printed
  per commit — mains versus battery is a 30% effect and shows up there.

The header prints a **resolution**: how far the corrected controls still
disagree, which is the method's own error. Nothing smaller than that is a
claim. Seeing a few percent on a benchmark the commit could not have touched is
the normal way to watch this work.

To get a row for the branch point, record one in a worktree:

```sh
git worktree add /tmp/base <base-commit>
cd /tmp/base
poetry run python -m benchmarks ws --save-baseline branch-base
poetry run python -m benchmarks decode --save-baseline branch-base
cp benchmarks/.baselines/branch-base@*.json <main-worktree>/benchmarks/.baselines/
cd - && git worktree remove /tmp/base
```

The commit must contain the benchmark suite, and the corpus must not have
changed since, or the frames are not the same frames.

> **TODO.** The table is only as dense as the commits that happened to get
> benchmarked, so a real change can be charged to the next commit with a run.
> Walking every commit in the range in a worktree would give full attribution,
> at a few minutes each. Until then, read a large step as belonging to the range
> since the previous row, and name the change in that range that explains it.

## Before quoting a number

- Loopback, no TLS, one publisher, one subscriber, one machine.
- The handler does nothing. This is a library; the handler is the user's.
- Payloads are synthetic. Real frames branch and compress differently.
- `python -m benchmarks baselines` lists every recording with its series,
  timestamp and commit.
