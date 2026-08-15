#!/usr/bin/env bash

# Exit on errors, uninitialized variables, or pipe failures
set -euo pipefail

# Check if gum is installed
if ! command -v gum &>/dev/null; then
  echo "Error: 'gum' is not installed. Install it from https://github.com/charmbracelet/gum"
  exit 1
fi
# check if asciinema is installed
if ! command -v asciinema &>/dev/null; then
  echo "Error: 'asciinema' is not installed. Install it from https://asciinema.org/docs/installation"
  exit 1
fi


# Check for required arguments
if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <output_file> <demo_script>"
  echo "Example: $0 demo.cast ./scripts/demo.sh"
  exit 1
fi

# Variables
OUTPUT_FILE=$1
DEMO_SCRIPT=$2

# Ensure the demo script exists and is executable
if [ ! -f "$DEMO_SCRIPT" ] || [ ! -x "$DEMO_SCRIPT" ]; then
  echo "Error: Demo script '$DEMO_SCRIPT' does not exist or is not executable."
  exit 1
fi


# ensure output file does not exist
if [ -f "$OUTPUT_FILE" ]; then
  echo "Output file '$OUTPUT_FILE' exists, replacing it."
  rm -f "$OUTPUT_FILE"
fi


export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

# agg will not create the directory it writes into, and tmp.cast must not be
# left behind when a recording fails.
mkdir -p "$(dirname "$OUTPUT_FILE")"
trap 'rm -f tmp.cast' EXIT

# Record the session using asciinema
echo "Recording demo to $OUTPUT_FILE..."
stty cols 120 rows 45
asciinema rec -c "$DEMO_SCRIPT" tmp.cast --overwrite
stty sane

# We now convert to a gif
echo "Converting demo to gif..."
agg tmp.cast "$OUTPUT_FILE"

# Notify completion
gum format "Recording complete! Demo saved to $OUTPUT_FILE."
