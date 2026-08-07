import time
from datetime import datetime, timezone
from decimal import Decimal

from eth_account.messages import encode_defunct
from web3 import AsyncWeb3, Web3

MAX_INT_256 = 2**255 - 1
MIN_INT_256 = -(2**255)


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
