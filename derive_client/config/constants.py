"""Pure constants without dependencies."""

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

GAS_FEE_BUFFER = 1.1  # buffer multiplier to pad maxFeePerGas
GAS_LIMIT_BUFFER = 1.1  # buffer multiplier to pad gas limit
MIN_PRIORITY_FEE = 10_000

ETHEREUM_MAINNET_CHAIN_ID = 1
SEPOLIA_CHAIN_ID = 11155111

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
