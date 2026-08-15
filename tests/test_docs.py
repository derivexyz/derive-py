"""Every link the README publishes has to resolve.

The README is the only documentation this repo owns and most of it points
outward, so a page moving on docs.derive.xyz is a broken README here that
nobody notices by reading it.

Three kinds of link, three checks:

    local paths        the file exists
    our own repo URLs  mapped back to a local path, so a renamed asset fails on
                       the branch that renames it rather than after merge, when
                       the raw.githubusercontent URL would finally 404
    everything else    an HTTP request, marked live

Note what the last one cannot do: docs.derive.xyz answers 403 to every
non-browser client, real page or not, so those links pass on reachability of the
host alone. Treat a green run as "nothing has 404ed", not as proof the anchor
still exists.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import requests

REPO_ROOT = Path(__file__).parent.parent
MARKDOWN_FILES = [REPO_ROOT / "README.md", *sorted((REPO_ROOT / "docs").glob("*.md"))]

LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)\)")

OWN_REPO_PREFIXES = (
    "https://raw.githubusercontent.com/derivexyz/derive-py/main/",
    "https://github.com/derivexyz/derive-py/blob/main/",
)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; derive-py link check)"}

# 403, 405 and 429 mean "not going to answer a robot", not "gone".
OK_STATUSES = frozenset({200, 201, 202, 203, 204, 206, 301, 302, 303, 307, 308, 403, 405, 429})


def _targets() -> list[str]:
    found: list[str] = []
    for path in MARKDOWN_FILES:
        if path.exists():
            found.extend(LINK.findall(path.read_text()))
    return found


TARGETS = _targets()
LOCAL = sorted({t for t in TARGETS if not t.startswith(("http://", "https://", "#", "mailto:"))})
OWN = sorted({t for t in TARGETS if t.startswith(OWN_REPO_PREFIXES)})
EXTERNAL = sorted({t for t in TARGETS if t.startswith(("http://", "https://")) and not t.startswith(OWN_REPO_PREFIXES)})


def test_links_were_found():
    """A regex that matched nothing would make every other test here vacuous."""

    assert LOCAL and OWN and EXTERNAL


@pytest.mark.parametrize("target", LOCAL)
def test_local_link_resolves(target: str):
    path = REPO_ROOT / target.lstrip("./").split("#")[0]
    assert path.exists(), f"{target} does not exist"


@pytest.mark.parametrize("target", OWN)
def test_own_repo_link_resolves(target: str):
    for prefix in OWN_REPO_PREFIXES:
        target = target.removeprefix(prefix)
    assert (REPO_ROOT / target).exists(), f"{target} does not exist in this checkout"


@pytest.mark.live
@pytest.mark.parametrize("target", EXTERNAL)
def test_external_link_resolves(target: str):
    try:
        response = requests.head(target, headers=HEADERS, timeout=20, allow_redirects=True)
        if response.status_code not in OK_STATUSES:
            response = requests.get(target, headers=HEADERS, timeout=20, allow_redirects=True)
    except requests.RequestException as exc:
        pytest.fail(f"{target} could not be reached: {exc}")

    assert response.status_code in OK_STATUSES, f"{target} returned {response.status_code}"
