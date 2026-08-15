#!/usr/bin/env bash

set -euo pipefail

# Overwrites the gif the README embeds. cast.sh removes an existing output
# file before recording, so re-running is the whole update procedure.
bash scripts/demos/cast.sh .github/assets/cli_demo.gif scripts/demo.sh
