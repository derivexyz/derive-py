# WebSocket client benchmarks

How many messages per second `WebSocketClient` can take off a socket, decode
and hand to a callback. Measurement, not assertion. Nothing here fails a build.

```
make bench                  # messages/second, the headline number
make bench-decode           # decode costs, the denominator for the above
python -m benchmarks list   # names, for --channel and --filter
```

Scope is the WebSocket transport only. The REST and async-HTTP clients are not
covered, and neither are the signing wrappers: action signing costs more than
everything measured here put together, which would drown the signal without
telling you anything about the transport.

## What runs

Every measurement goes through the surface a user touches: `WebSocketSession`
plus the generated subscription methods on `PublicChannels`, and the generated
RPC methods for the request path. Nothing reaches into the client's internals,
so a rewrite of the receive path leaves these benchmarks and their recorded
baselines directly comparable.

| suite | question |
| --- | --- |
| `ws/notify/<channel>/async` | messages/second with an `async def` callback |
| `ws/notify/<channel>/sync` | the same with a plain callback, which the session hands to a thread pool |
| `ws/notify/<channel>/control` | ceiling: raw `recv` loop, no session, no decode |
| `ws/rpc/<method>/c<N>` | round trips/second with N requests in flight |
| `ws/rpc/<method>/control_c<N>` | ceiling for the same, hand-rolled frames |
| `decode/envelope/<channel>` | first-pass JSON-RPC decode, `Raw` payload |
| `decode/payload/<channel>` | floor: one typed decode of the payload bytes |
| `decode/utf8/<channel>` | what `recv()` costs without `decode=False` |

Read the control rows first. If a client rate sits close to its control, the
harness is the bottleneck and the client number is a floor rather than a
measurement.

`decode/envelope` plus `decode/payload` is the two-pass structure the routing
design requires: the channel is not known until the envelope is parsed, and the
payload type is not known until the channel is. Both passes scan the payload
bytes. `decode/payload` alone is the hard floor, and no arrangement of the
receive path beats it.

## Why synthetic traffic

A live feed cannot answer the question. Subscription rates are bounded by the
exchange's publish intervals and by whatever the market is doing, so a live run
measures Derive rather than the client, and testnet carries no order flow to
measure at all. RPC volume runs into the account's rate limit long before it
runs into the client. The feeder here writes pre-framed bytes as fast as
loopback accepts them, which is faster than any exchange. That is the point:
the number wanted is the client's ceiling.

`synth.py` walks any msgspec type with `msgspec.inspect` and fabricates a
plausible value per leaf, seeded, so two runs on one commit produce
byte-identical frames. That is what makes run-to-run comparison meaningful: a
change in measured time is a change in the code, not in the data. Values are
plausible, not valid; nothing honours cross-field invariants, and nothing here
should be fed to anything that validates.

Payload types come from `channel_models`, not from copies. A spec regeneration
that changes a channel changes the benchmark, which is the correct failure
mode. To check the corpus against reality, record a few frames from a mainnet
public channel (no auth, no rate limit worth worrying about) and compare frame
sizes and field population against `Channel.raw`.

## Comparing runs without keeping old code

Runs are recorded as `benchmarks/.baselines/<series>@<utc-stamp>.json`,
gitignored. Nothing is ever overwritten; a comparison resolves to the newest
recording in the series. Each run merges into that recording rather than
replacing it, so a filtered run does not drop the rows it skipped.

```sh
git switch main
python -m benchmarks ws --save-baseline main    # record the reference

git switch feature/ws-serialisation
python -m benchmarks ws --baseline main         # compare; this run files under local
```

`--baseline` chooses what to measure against, `--save-baseline` chooses where
this run is filed. They default apart on purpose: comparing against a reference
series should not write into it.

A change reads `faster` or `slower` only if it exceeds 5% *and* the
interquartile ranges of the two runs are disjoint. Anything else reads `same`
or `noisy`. On a laptop with a scaling governor, or on a shared VM, raise
`NOISE_THRESHOLD` in `harness.py`, or take more samples: `--repeats` for `ws`,
`--samples` for `decode`. 7% swings between identical runs are normal there.

## Caveats before quoting a number

- Loopback, no TLS, one publisher, one subscriber, one machine.
- The handler does nothing. This is a library; the handler is the user's.
- Payloads are synthetic. Real frames branch and compress differently.
- `python -m benchmarks baselines` lists every recording with its series,
  timestamp and git revision. A delta across two Python versions is not a delta
  in your code.
