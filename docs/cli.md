# CLI Reference

The `drv` command-line tool provides access to Derive functionality from your terminal.

## Getting Help

Run any command with `--help` to see detailed usage:

```bash
drv --help              # Show all commands
```

## Command Tree

```
Derive Client
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
│   └── list-open.... List all open orders of a subacccount.
├── position......... Inspect and transfer positions across subaccounts.
│   ├── list......... List active positions of a subaccount.
│   └── transfer..... Transfer part of a position to another subaccount of the same wallet.
├── system........... Query system-level information.
│   ├── rate-limits.. Get the caller's current rate limits.
│   ├── time......... Get the current system time.
│   └── transaction.. Get a transaction by its operation UUID.
└── tree............. Print the command tree structure.
```

## Demo

![CLI Demo](cli_demo.gif)

