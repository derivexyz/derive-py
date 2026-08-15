"""Regenerate the generated blocks in README.md.

Two blocks, each delimited by HTML comments so the rest of the file is never
touched (the contributors action owns a third block of its own):

    <!-- examples:start -->   the example list, from each script's docstring
    <!-- cli-tree:start -->   the drv command tree, from the click app

Run via `make docs`. CI runs the same target and then `make check_diff`, so a
drifted README fails the build rather than rotting.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from derive_py.cli import cli
from derive_py.cli._tree import command_tree

REPO_ROOT = Path(__file__).parent.parent
README = REPO_ROOT / "README.md"
EXAMPLES_DIR = REPO_ROOT / "examples"
BLOB_URL = "https://github.com/derivexyz/derive-py/blob/main/examples"


def _block(name: str) -> tuple[str, str]:
    return f"<!-- {name}:start -->", f"<!-- {name}:end -->"


def replace_block(text: str, name: str, body: str) -> str:
    """Replace the content between a block's start and end markers."""

    start, end = _block(name)
    pattern = re.compile(f"{re.escape(start)}.*?{re.escape(end)}", re.DOTALL)
    if not pattern.search(text):
        raise SystemExit(f"README.md is missing the {start} ... {end} markers")
    return pattern.sub(f"{start}\n{body}\n{end}", text)


def example_rows() -> str:
    """One table row per example, titled by the first line of its docstring.

    Every example opens with `NN - Title: summary.`, so the docstring is the
    single source of truth and this never needs hand-editing.
    """

    rows = ["| Example | What it covers |", "| --- | --- |"]
    for path in sorted(EXAMPLES_DIR.glob("[0-9]*.py")):
        docstring = ast_docstring(path)
        if docstring is None:
            raise SystemExit(f"{path.name} has no module docstring")

        rows.append(f"| [`{path.name}`]({BLOB_URL}/{path.name}) | {summarise(docstring)} |")

    return "\n".join(rows)


def summarise(docstring: str) -> str:
    """First sentence of the docstring, minus the `NN - ` ordinal prefix.

    The opening sentence wraps across lines in some examples, so the first
    paragraph is unwrapped before it is cut, not the first line.
    """

    paragraph = " ".join(line.strip() for line in docstring.strip().split("\n\n")[0].splitlines())
    _, _, summary = paragraph.partition(" - ")
    sentence, _, _ = summary.partition(". ")
    return sentence.rstrip(".")


def ast_docstring(path: Path) -> str | None:
    """Read the module docstring without importing the example."""

    return ast.get_docstring(ast.parse(path.read_text()))


def cli_tree() -> str:
    lines = command_tree(cli, verbose=True, use_rich=False)
    return "\n".join(["```", *lines, "```"])


def main() -> None:
    text = README.read_text()
    text = replace_block(text, "examples", example_rows())
    text = replace_block(text, "cli-tree", cli_tree())
    README.write_text(text)


if __name__ == "__main__":
    main()
