import time
from datetime import datetime, timezone
from decimal import Decimal

from eth_account.messages import encode_defunct
from web3 import AsyncWeb3, Web3

MAX_INT_256 = 2**255 - 1
MIN_INT_256 = -(2**255)

#: The protocol holds decimals at 1e12 but takes them at 1e18 on the wire. It
#: REJECTS, rather than truncates, an e18 word carrying sub-1e12 precision, so
#: more than 12 decimal places can never produce a valid vault signature.
#: Confirmed against derive-ts signing/encoding.ts assertE12Precision.
VAULT_PRECISION_DECIMALS = 12


def decimal_to_big_int(value: Decimal) -> int:
    result_value = int(value * Decimal(10**18))
    if result_value < MIN_INT_256 or result_value > MAX_INT_256:
        raise ValueError(f"resulting integer value must be between {MIN_INT_256} and {MAX_INT_256}")
    return result_value


def get_action_nonce() -> int:
    """UTC timestamp in nanoseconds.

    v3 rejects millisecond- and microsecond-scale nonces. Withdraw, transfer,
    session-key, whitelist, liquidation and vault actions additionally require
    the nonce to strictly increase per subaccount; orders and RFQs do not.
    Vault nonces are accepted from 60 days before to 1 hour after the server
    clock, a wider window than the +/- 1 hour the other increasing actions get.
    """
    return time.time_ns()


def utc_now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def sign_rest_auth_header(
    web3_client: Web3 | AsyncWeb3,
    derive_wallet: str,
    session_key_or_wallet_private_key: str,
) -> dict[str, str]:
    timestamp = str(int(time.time() * 1000))
    signature = web3_client.eth.account.sign_message(
        encode_defunct(text=timestamp),
        private_key=session_key_or_wallet_private_key,
    ).signature.hex()
    return {
        "X-DeriveWallet": derive_wallet,
        "X-DeriveTimestamp": timestamp,
        "X-DeriveSignature": signature,
    }


def sign_ws_login(
    web3_client: Web3,
    derive_wallet: str,
    session_key_or_wallet_private_key: str,
) -> dict[str, str | int]:
    timestamp = utc_now_ms()
    signature = web3_client.eth.account.sign_message(
        encode_defunct(text=str(timestamp)), private_key=session_key_or_wallet_private_key
    ).signature.hex()
    return {
        "wallet": derive_wallet,
        "timestamp": timestamp,
        "signature": signature,
    }


def scale_amount(value: Decimal, decimals: int = 18) -> int:
    scaled = value * Decimal(10) ** decimals
    if scaled != scaled.to_integral_value():
        raise ValueError(f"{value} exceeds the precision of {decimals} decimals")
    result = int(scaled)
    if result < 0:
        raise ValueError(f"must not be negative, got {value}")
    return result


def scale_exact(value: Decimal, decimals: int) -> int:
    """Scale a Decimal by 10**decimals, rejecting anything not exactly integral.

    Works from the exact integer ratio rather than through Decimal arithmetic.
    `value * Decimal(10) ** decimals` runs under the default 28-significant-digit
    context: given an input carrying more than 28 significant digits it returns a
    ROUNDED result that is still integral, so scale_amount's own
    `scaled != scaled.to_integral_value()` guard does not fire and the caller
    signs a word that is quietly wrong in its low digits. Reachable only with
    absurd inputs, which is why it has never bitten; not fixed in scale_amount
    here because doing so would change bytes every other module already signs.
    """

    try:
        numerator, denominator = value.as_integer_ratio()
    except (OverflowError, ValueError) as e:
        raise ValueError(f"{value!r} is not a finite decimal") from e

    scaled = numerator * 10**decimals
    if scaled % denominator:
        raise ValueError(f"{value} exceeds the precision of {decimals} decimals")
    return scaled // denominator


def scale_vault_amount(value: Decimal, name: str, *, strictly_positive: bool = False) -> int:
    """Scale a vault field to its e18 wire word.

    Rejects negatives and sub-1e12 precision, and optionally requires a strictly
    positive value. Mirrors derive-ts unsignedE18 / positiveE18 exactly: only
    deposit amounts and share counts must be non-zero, while prices and fee caps
    may be zero, and validating more strictly than the reference would refuse
    payloads the exchange accepts.

    Not scale_amount: that truncates rather than rejects below the 1e12 floor
    the vault protocol enforces, so `Decimal("0.0000000000001")` would silently
    become a word the exchange refuses to verify.
    """

    scaled = scale_exact(value, 18)
    if strictly_positive and scaled <= 0:
        raise ValueError(f"{name} must be strictly positive, got {value}")
    if scaled < 0:
        raise ValueError(f"{name} must not be negative, got {value}")
    if scaled % 10 ** (18 - VAULT_PRECISION_DECIMALS):
        raise ValueError(
            f"{name} has more than {VAULT_PRECISION_DECIMALS} decimal places: {value}. "
            f"The protocol runs at 1e{VAULT_PRECISION_DECIMALS} precision and rejects the word."
        )
    return scaled


def format_units(scaled: int, decimals: int = 18) -> str:
    """Render a scaled integer back as a plain decimal string.

    The wire decimal and the signed word must describe the same value, so both
    are derived from the same integer rather than from the caller's Decimal.
    str(Decimal) is not usable: it emits scientific notation for values like
    Decimal("1E+3"), which the API rejects.
    """

    sign = "-" if scaled < 0 else ""
    whole, fraction = divmod(abs(scaled), 10**decimals)
    if not fraction:
        return f"{sign}{whole}"
    return f"{sign}{whole}." + f"{fraction:0{decimals}d}".rstrip("0")


def to_uint(value: int, name: str, *, bits: int = 256) -> int:
    """Validate a plain (unscaled) integer field before ABI encoding.

    eth-abi rejects an out-of-range value anyway, but with a message that names
    neither the field nor the unit mistake behind it. bool is excluded
    explicitly: it is an int subclass and would encode as 0 or 1.
    """

    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer, got {value!r}")
    if not 0 <= value < 2**bits:
        raise ValueError(f"{name} must fit an unsigned {bits}-bit integer, got {value}")
    return value


def to_bytes32(value: str, name: str) -> bytes:
    """Parse a 0x-prefixed (or bare) 32-byte hex string.

    SignedAction has its own copy for DOMAIN_SEPARATOR/ACTION_TYPEHASH, whose
    error text points at the Protocol Constants table; it cannot import this one
    without a cycle through module_data.
    """

    raw = value[2:] if value.startswith("0x") else value
    try:
        result = bytes.fromhex(raw)
    except (ValueError, TypeError) as e:
        raise ValueError(f"{name} is not valid hex: {value!r}") from e
    if len(result) != 32:
        raise ValueError(f"{name} must be 32 bytes, got {len(result)}: {value!r}")
    return result
