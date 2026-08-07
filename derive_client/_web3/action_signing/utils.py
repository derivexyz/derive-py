import time
from datetime import datetime, timezone
from decimal import Decimal

from eth_account.messages import encode_defunct
from web3 import AsyncWeb3, Web3

MAX_INT_256 = 2**255 - 1
MIN_INT_256 = -(2**255)
MAX_INT_32 = 2**31 - 1


def decimal_to_big_int(value: Decimal) -> int:
    result_value = int(value * Decimal(10**18))
    if result_value < MIN_INT_256 or result_value > MAX_INT_256:
        raise ValueError(f"resulting integer value must be between {MIN_INT_256} and {MAX_INT_256}")
    return result_value


def get_action_nonce() -> int:
    """UTC timestamp in nanoseconds.

    v3 rejects millisecond- and microsecond-scale nonces. Withdraw, transfer,
    session-key, whitelist and liquidation actions additionally require the
    nonce to strictly increase per subaccount; orders and RFQs do not.
    """
    return time.time_ns()


def utc_now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def sign_rest_auth_header(
    web3_client: Web3 | AsyncWeb3,
    smart_contract_wallet: str,
    session_key_or_wallet_private_key: str,
) -> dict[str, str]:
    timestamp = str(int(time.time() * 1000))
    signature = web3_client.eth.account.sign_message(
        encode_defunct(text=timestamp),
        private_key=session_key_or_wallet_private_key,
    ).signature.hex()
    return {
        "X-DeriveWallet": smart_contract_wallet,
        "X-DeriveTimestamp": timestamp,
        "X-DeriveSignature": signature,
    }


def sign_ws_login(web3_client: Web3, smart_contract_wallet: str, session_key_or_wallet_private_key: str):
    timestamp = str(utc_now_ms())
    signature = web3_client.eth.account.sign_message(
        encode_defunct(text=timestamp), private_key=session_key_or_wallet_private_key
    ).signature.hex()
    return {
        "wallet": smart_contract_wallet,
        "timestamp": str(timestamp),
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


def assert_e12_precision(scaled: int, field: str) -> None:
    """The exchange runs at 1e12; sub-1e12 precision in an e18 word is rejected,
    not truncated, so such a signature can never validate."""
    if scaled % 1_000_000 != 0:
        raise ValueError(f"{field} has more than 12 decimal places")
