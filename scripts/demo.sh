#!/usr/bin/env bash

set -euo pipefail

SLEEP_TIME=4

clear
cowsay "derive-py is a Python library and CLI for the Derive v3 API."
sleep $SLEEP_TIME
clear

cowsay "The client can be installed from pip:"
echo "pip install derive-py"
sleep $SLEEP_TIME
clear

cowsay "Once installed, we can interact with Derive programmatically via the CLI."
echo drv --help
drv --help
sleep $SLEEP_TIME
clear

# Account
cowsay "Let's start by querying our account details."
echo drv account get
drv account get
sleep $SLEEP_TIME
clear

cowsay "We can also view our subaccount portfolios."
echo drv account portfolios
drv account portfolios
sleep $SLEEP_TIME
clear

# Markets
cowsay "Next, let's explore market data. We can list all, but for the sake of this demo we'll have a look at ETH..."
echo drv market currency ETH
drv market currency ETH
sleep $SLEEP_TIME
clear

cowsay "...query instruments by currency and type..."
echo drv market instrument -c ETH -t option -n 20
drv market instrument -c ETH -t option -n 20
sleep $SLEEP_TIME
clear

cowsay "...and check real-time ticker data."
echo drv market ticker ETH-PERP
drv market ticker ETH-PERP
sleep $SLEEP_TIME
clear

# Positions
cowsay "Before trading anything, let's see what we are holding."
echo drv position list
drv position list
sleep $SLEEP_TIME
clear

cowsay "Short a fair amount of ETH on a shared test account. Someone has been busy. Let's start digging our way out."
sleep $SLEEP_TIME
clear

# Orders
cowsay "A reduce-only market buy. The price is the worst fill we are willing to accept, not the price we expect."
echo drv order create ETH-PERP buy -a 0.1 -p 10000 --type market --reduce-only
drv order create ETH-PERP buy -a 0.1 -p 10000 --type market --reduce-only
sleep $SLEEP_TIME
clear

cowsay "0.1 down. Only the rest to go."
sleep $SLEEP_TIME
clear

cowsay "Limit orders work too. ETH-PERP at \$100 seems fair."
echo drv order create ETH-PERP buy -a 0.1 -p 100
drv order create ETH-PERP buy -a 0.1 -p 100
sleep $SLEEP_TIME
clear

cowsay "Let's see if anyone is desperate enough to sell at that price."
echo drv order list-open
drv order list-open
sleep $SLEEP_TIME
clear

cowsay "Thought so. Cancel the pipe dream."
echo drv order cancel-all
drv order cancel-all
sleep $SLEEP_TIME
clear

cowsay "And that is only part of the CLI. The library adds RFQs, vaults, deposits and websocket subscriptions."
sleep $SLEEP_TIME
clear
