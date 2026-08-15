# derive-py

[![PyPI](https://img.shields.io/pypi/v/derive-py)](https://pypi.org/project/derive-py/)
[![CI](https://github.com/derivexyz/derive-py/actions/workflows/common_check.yaml/badge.svg)](https://github.com/derivexyz/derive-py/actions/workflows/common_check.yaml)
[![Licence](https://img.shields.io/pypi/l/derive-py)](https://github.com/derivexyz/derive-py/blob/main/LICENSE)

Python client for the [Derive](https://derive.xyz) v3 exchange API: market data,
orders, RFQs, transfers, withdrawals, deposits, vaults and session keys over HTTP
or WebSocket, synchronously or asynchronously, plus a `drv` command line tool.

## Documentation

Protocol semantics are documented by Derive and are not repeated here. Read them
first, then come back for the Python bindings.

- [Derive v3 documentation](https://v3.docs.derive.xyz/)
- [Quickstart](https://v3.docs.derive.xyz/getting-started/quickstart) and [depositing](https://v3.docs.derive.xyz/getting-started/depositing)
- [Action signing](https://v3.docs.derive.xyz/authentication/action-signing), [session keys](https://v3.docs.derive.xyz/authentication/session-keys) and [access scopes](https://v3.docs.derive.xyz/authentication/access-scopes)
- [Migrating from v2](https://v3.docs.derive.xyz/migrating/breaking-changes), written to double as a `SKILL.md` for a coding agent
- [llms.txt](https://v3.docs.derive.xyz/llms.txt), an index of every page for agents
- Machine readable specs, which this client is generated from:
  [openapi.json](https://v3.docs.derive.xyz/openapi.json),
  [websocket.asyncapi.json](https://v3.docs.derive.xyz/websocket.asyncapi.json),
  [subscriptions.asyncapi.json](https://v3.docs.derive.xyz/subscriptions.asyncapi.json)

Sibling SDKs: [derive-ts](https://github.com/derivexyz/derive-ts),
[derive-rs](https://github.com/derivexyz/derive-rs).

## Install

```bash
pip install derive-py
```

Python 3.11 or newer.

## Configure

Credentials come from the environment, or from a `.env` file in the working
directory (default), or from a custom path.

| Variable | Required | Notes |
| --- | --- | --- |
| `DERIVE_WALLET` | yes | The owner wallet, your own EOA or multisig |
| `DERIVE_SESSION_KEY` | yes | Private key of the signer, a session key or the owner |
| `DERIVE_SUBACCOUNT_ID` | yes | Subaccount the client acts on by default |
| `DERIVE_ENV` | no | `TEST` or `PROD`, defaults to `TEST` |
| `ETH_RPC_ENDPOINTS` | no | Comma separated L1 RPC URLs, only used by the deposit flows |

`from_env()` takes a `session_key_path` if you would rather keep the key in a
file than in the environment, and an `env_file` to point at a `.env` elsewhere.

`.env.template` holds working testnet credentials. They are published on purpose
so the examples run with no setup, and they are worthless: never reuse that key
for anything else.

## Quickstart

```python
from derive_py import HTTPClient
from derive_py.data_types import D, Direction, OrderType

client = HTTPClient.from_env()

# Public market data needs no credentials and no connect().
ticker = client.markets.get_ticker(instrument_name="ETH-PERP")

# connect() validates the credentials and warms the instrument cache.
# Anything touching subaccount state needs it.
client.connect()

order = client.orders.create(
    instrument_name="ETH-PERP",
    amount=D("0.1"),
    limit_price=D("1000"),
    direction=Direction.buy,
    order_type=OrderType.limit,
)

client.disconnect()
```

`D` builds a `Decimal`. Pass decimals, never floats: amounts and prices are
quantized to the instrument's `amount_step` and `tick_size`, and the protocol
rejects rather than truncates excess precision.

## Clients

| Client | Transport | Concurrency |
| --- | --- | --- |
| `HTTPClient` | JSON-RPC over HTTP | Blocking. Not thread safe, use one client per thread |
| `AsyncHTTPClient` | JSON-RPC over HTTP | Safe for concurrent tasks on a single event loop, not safe to share between threads |
| `WebSocketClient` | JSON-RPC over WebSocket | Safe for concurrent tasks on a single event loop, not safe to share between threads |

Only `WebSocketClient` carries subscriptions. It also holds one connection open
rather than paying setup on every call, so it is the one to reach for when
latency matters. Its `connect()` is mandatory, since there is no transport
before it. Both HTTP clients open their session lazily on first use, so they
need `connect()` only for credential validation and cached state.

All three expose the same operations:

| Attribute | What it does |
| --- | --- |
| `client.markets` | Currencies, instruments, tickers, risk universes. Public |
| `client.system` | Server time, rate limits, operation lookup by uuid. Public |
| `client.account` | The wallet: session keys, whitelisted recipients, subaccounts, portfolios |
| `client.orders` | Create, replace, cancel, query |
| `client.positions` | Open positions and position transfers |
| `client.collateral` | Balances, margin, withdrawals, spot transfers |
| `client.rfq` | Taker and maker RFQ flows |
| `client.history` | Trades, orders, deposits, withdrawals, funding, interest |
| `client.mmp` | Market maker protection config and reset |
| `client.vaults` | Shareholder and curator operations |
| `client.active_subaccount` | The subaccount the above act on, with `cached_subaccounts` for the rest |
| `client.plan_deposit_to_new_subaccount` | On-chain deposit that creates a subaccount as it funds it |

`WebSocketClient` adds `public_channels`, `private_channels`, `subscriptions`,
`connection_state` and `on_state_change`. Every operation is also reachable per
subaccount, `subaccount.orders` and so on, when one client drives several.

Anything not wrapped is reachable through `client.public_api` and
`client.private_api`, which are generated from the specs above and cover the
whole RPC surface.

## Examples

Runnable and heavily commented, ordered by the v3 onboarding flow: your first
deposit creates the account, then session keys, then the rest.

```bash
git clone git@github.com:derivexyz/derive-py.git
cd derive-py
pip install -e .
cp .env.template .env
python examples/03-market-data.py
```

<!-- examples:start -->
| Example | What it covers |
| --- | --- |
| [`01-deposit.py`](https://github.com/derivexyz/derive-py/blob/main/examples/01-deposit.py) | Deposit: the only way an account or subaccount comes into existence |
| [`02-session-keys.py`](https://github.com/derivexyz/derive-py/blob/main/examples/02-session-keys.py) | Session keys: register a scoped, expiring key, edit it, retire it |
| [`03-market-data.py`](https://github.com/derivexyz/derive-py/blob/main/examples/03-market-data.py) | Public market data: currencies, instruments, tickers |
| [`04-subscribe.py`](https://github.com/derivexyz/derive-py/blob/main/examples/04-subscribe.py) | Websocket subscriptions: two public channels over one socket |
| [`05-place-order.py`](https://github.com/derivexyz/derive-py/blob/main/examples/05-place-order.py) | Order lifecycle: place, inspect, cancel |
| [`06-rfq-taker.py`](https://github.com/derivexyz/derive-py/blob/main/examples/06-rfq-taker.py) | RFQ taker: request quotes for a package, execute the best one |
| [`07-rfq-maker.py`](https://github.com/derivexyz/derive-py/blob/main/examples/07-rfq-maker.py) | RFQ maker: a bounded quoting loop |
| [`08-transfers.py`](https://github.com/derivexyz/derive-py/blob/main/examples/08-transfers.py) | Spot transfers: between your own subaccounts, and out to another owner |
| [`09-withdraw.py`](https://github.com/derivexyz/derive-py/blob/main/examples/09-withdraw.py) | Withdraw collateral to L1 |
| [`10-vaults.py`](https://github.com/derivexyz/derive-py/blob/main/examples/10-vaults.py) | Vaults: browse, queue a deposit, cancel it |
| [`11-position-transfer.py`](https://github.com/derivexyz/derive-py/blob/main/examples/11-position-transfer.py) | Position transfers: moving part of an open position between two subaccounts owned by the same wallet |
<!-- examples:end -->

`01-deposit.py` is the only one needing a funded L1 key and an RPC endpoint. The
rest run against testnet with the credentials in `.env.template`.

## CLI

```bash
drv --help          # every command
drv tree            # the tree below, from your installed version
drv market ticker ETH-PERP
```

![CLI demo](https://raw.githubusercontent.com/derivexyz/derive-py/main/.github/assets/cli_demo.gif)

<!-- cli-tree:start -->
```
drv
├── account.......... Account details.
│   ├── get.......... Account details.
│   └── portfolios... Get all portfolios of a wallet.
├── collateral....... Manage collateral.
│   └── get.......... Get subaccount collaterals.
├── market........... Query market data: currencies, instruments, tickers.
│   ├── currency..... Get currency details.
│   ├── instrument... Get instrument details.
│   ├── ticker....... Get ticker details.
│   └── universe..... List risk universes, their managers and accepted collaterals.
├── mmp.............. Market maker protection configuration.
│   ├── get-config... Get the current mmp config for a subaccount (optionally filtered by currency).
│   ├── reset........ Resets (unfreezes) the mmp state for a subaccount (optionally filtered by currency).
│   └── set-config... Set the mmp config for the subaccount and currency.
├── order............ Create, view, list, and cancel orders.
│   ├── cancel....... Cancel a single order.
│   ├── cancel-all... Cancel all orders.
│   ├── create....... Create a new order.
│   ├── get.......... Get state of an order by order id.
│   └── list-open.... List all open orders of a subaccount.
├── position......... Inspect and transfer positions across subaccounts.
│   ├── list......... List active positions of a subaccount.
│   └── transfer..... Transfer part of a position to another subaccount of the same wallet.
├── system........... Query system-level information.
│   ├── rate-limits.. Get the caller's current rate limits.
│   ├── time......... Get the current system time.
│   └── transaction.. Get a transaction by its operation UUID.
└── tree............. Print the command tree structure.
```
<!-- cli-tree:end -->

## Development

```bash
git clone git@github.com:derivexyz/derive-py.git
cd derive-py
make install            # dependencies and git hooks
```

```bash
make fmt lint typecheck # while working
make tests              # hits the live testnet API
make all                # everything CI runs, in the order CI runs it
```

`make all` regenerates the client from the published specs, the API reference
and the generated blocks in this README, then formats, lints, type checks and
tests. CI runs the same targets and fails on a dirty tree, so run it before
pushing and commit whatever it regenerates.

```bash
make codegen-all        # regenerate models, API and tests from the specs
make docs               # regenerate the README blocks and build the site
make demo               # re-record the CLI gif, needs cowsay, gum, asciinema, agg
```

`shell.nix` provides all of it, recording tools included.

### Releasing

```bash
poetry run tbump 0.1.1
```

Tagging triggers the release workflow, which builds, creates a GitHub release
and publishes to PyPI.

## Contributors

<!-- readme: contributors -start -->
<table>
	<tbody>
		<tr>
            <td align="center">
                <a href="https://github.com/Karrenbelt">
                    <img src="https://avatars.githubusercontent.com/u/16686216?v=4" width="100;" alt="Karrenbelt"/>
                    <br />
                    <sub><b>Zarathustra</b></sub>
                </a>
            </td>
            <td align="center">
                <a href="https://github.com/8ball030">
                    <img src="https://avatars.githubusercontent.com/u/35799987?v=4" width="100;" alt="8ball030"/>
                    <br />
                    <sub><b>8ball030</b></sub>
                </a>
            </td>
            <td align="center">
                <a href="https://github.com/Aviksaikat">
                    <img src="https://avatars.githubusercontent.com/u/31238298?v=4" width="100;" alt="Aviksaikat"/>
                    <br />
                    <sub><b>Saikat K</b></sub>
                </a>
            </td>
            <td align="center">
                <a href="https://github.com/andreiaugustin">
                    <img src="https://avatars.githubusercontent.com/u/36695484?v=4" width="100;" alt="andreiaugustin"/>
                    <br />
                    <sub><b>Andrei Augustin</b></sub>
                </a>
            </td>
            <td align="center">
                <a href="https://github.com/0xdomrom">
                    <img src="https://avatars.githubusercontent.com/u/11264336?v=4" width="100;" alt="0xdomrom"/>
                    <br />
                    <sub><b>DomRom</b></sub>
                </a>
            </td>
            <td align="center">
                <a href="https://github.com/DeBelg">
                    <img src="https://avatars.githubusercontent.com/u/38403795?v=4" width="100;" alt="DeBelg"/>
                    <br />
                    <sub><b>Mf</b></sub>
                </a>
            </td>
		</tr>
	<tbody>
</table>
<!-- readme: contributors -end -->

This client library is developed with support from Derive, who host it under their
organization. Requests include default `referral_code` and `client` identifiers.
All code is open source and auditable.

## Licence

MIT, see [LICENSE](https://github.com/derivexyz/derive-py/blob/main/LICENSE).
