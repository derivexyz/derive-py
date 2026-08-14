"""Pure constants without dependencies."""

import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Final

INT32_MAX: Final[int] = (1 << 31) - 1
UINT32_MAX: Final[int] = (1 << 32) - 1
INT64_MAX: Final[int] = (1 << 63) - 1
UINT64_MAX: Final[int] = (1 << 64) - 1

MAX_INT_256: Final[int] = (1 << 255) - 1
MIN_INT_256: Final[int] = -(1 << 255)

#: The protocol holds decimals at 1e12 but takes them at 1e18 on the wire. It
#: REJECTS, rather than truncates, an e18 word carrying sub-1e12 precision, so
#: more than 12 decimal places can never produce a valid vault signature.
#: Confirmed against derive-ts signing/encoding.ts assertE12Precision.
VAULT_PRECISION_DECIMALS = 12

PKG_ROOT = Path(__file__).parent.parent
DATA_DIR = PKG_ROOT / "data"
ABI_DATA_DIR = DATA_DIR / "abis"

PUBLIC_HEADERS = {"accept": "application/json", "content-type": "application/json"}

#: EIP-1559 caps base fee growth at 12.5% per block.
#: 6 blocks is ~72s on L1, and 1.125**6 ≈ 2.03, which is what web3.py's uses
BASE_FEE_MAX_GROWTH_PER_BLOCK: Final[float] = 1.125
BASE_FEE_LOOKAHEAD_BLOCKS: Final[int] = 6
GAS_FEE_BUFFER: Final[float] = BASE_FEE_MAX_GROWTH_PER_BLOCK**BASE_FEE_LOOKAHEAD_BLOCKS
MIN_PRIORITY_FEE: Final[int] = 10_000

ETHEREUM_MAINNET_CHAIN_ID = 1
SEPOLIA_CHAIN_ID = 11155111

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

DIST_NAME = "derive-py"

try:
    _VERSION = version(DIST_NAME)
except PackageNotFoundError:  # source checkout without an install
    _VERSION = "unknown"

_PY_VERSION = ".".join(str(part) for part in sys.version_info[:3])

USER_AGENT = f"{DIST_NAME}/{_VERSION} (Python {_PY_VERSION}; {sys.platform})"
