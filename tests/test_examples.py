import os
import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"
SCRIPTS = sorted(EXAMPLES_DIR.glob("*.py"))
TIMEOUT = 120

# Examples carry realistic settlement waits. Here we only need them to reach
# the wait and carry on, not to sit through one.
ENV = {**os.environ, "DERIVE_EXAMPLE_TIMEOUT_SEC": "5"}


@pytest.mark.live
@pytest.mark.parametrize("script", SCRIPTS, ids=[p.name for p in SCRIPTS])
def test_script_runs(script: Path):
    # DEVNULL, or the child inherits pytest's terminal, isatty() is true, and
    # the example blocks on its confirmation prompt until the timeout.
    result = subprocess.run(
        [sys.executable, script], capture_output=True, text=True, timeout=TIMEOUT, stdin=subprocess.DEVNULL, env=ENV
    )

    err_msg = f"Script failed with exit code {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    assert result.returncode == 0, err_msg
