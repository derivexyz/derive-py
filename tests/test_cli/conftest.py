"""Shared fixtures for CLI tests."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from derive_py.cli import cli as drv
from tests.conftest import ENV_TEMPLATE


@pytest.fixture(scope="session")
def runner():
    """Create a Click CliRunner and run tests inside an isolated filesystem."""

    runner = CliRunner()

    with runner.isolated_filesystem() as tmp_dir:
        env_path = Path(tmp_dir) / ".env"
        env_path.write_text(ENV_TEMPLATE.read_text())
        yield runner
        runner.invoke(drv, ["order", "cancel-all"])
