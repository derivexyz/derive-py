# """Fixtures for action-signing tests.

# Every test here signs locally and compares against the server's signing-preview
# (`*_debug`) endpoints, which rebuild the Action and return the encoded data and
# hashes. That comparison is the only thing that establishes correctness; a
# signature that merely parses proves nothing.
# """

# import time

# import pytest
# import requests
# from web3 import Account, Web3

# from derive_client.config.constants import PUBLIC_HEADERS
# from derive_client.config.contracts import CONFIGS
# from derive_client.data_types import Environment
# from tests.conftest import OWNER_TEST_WALLET, SESSION_KEY_PRIVATE_KEY, SUBACCOUNT_ID_75723


# @pytest.fixture(scope="session")
# def env_config():
#     return CONFIGS[Environment.TEST]


# @pytest.fixture(scope="session")
# def base_url(env_config):
#     return env_config.base_url


# @pytest.fixture(scope="session")
# def domain_separator(env_config):
#     return env_config.DOMAIN_SEPARATOR


# @pytest.fixture(scope="session")
# def action_typehash(env_config):
#     return env_config.ACTION_TYPEHASH


# @pytest.fixture(scope="session")
# def contracts(env_config):
#     return env_config.contracts


# @pytest.fixture(scope="session")
# def web3_client():
#     return Web3()


# @pytest.fixture(scope="session")
# def session_key(web3_client):
#     return web3_client.eth.account.from_key(SESSION_KEY_PRIVATE_KEY)


# @pytest.fixture
# def random_session_key():
#     return Account.create()


# @pytest.fixture(scope="session")
# def owner():
#     return OWNER_TEST_WALLET


# @pytest.fixture(scope="session")
# def subaccount_id():
#     return SUBACCOUNT_ID_75723


# @pytest.fixture
# def expiry() -> int:
#     """One hour out.

#     Inside every documented window: orders need >=10s and <=120 days,
#     position transfers >=60s, RFQ quotes <=1 day, vault actions <=30 days.
#     Not valid for MMP orders, which cap at 15 minutes.
#     """
#     return int(time.time()) + 3600


# @pytest.fixture(scope="session")
# def post(base_url):
#     def _post(path: str, payload: dict, headers: dict | None = None) -> dict:
#         response = requests.post(
#             f"{base_url}/{path}",
#             json=payload,
#             headers={**PUBLIC_HEADERS, **(headers or {})},
#             timeout=30,
#         )
#         body = response.json()
#         if "result" not in body:
#             raise AssertionError(f"{path} returned no result: {body}")
#         return body["result"]

#     return _post


# def assert_signing_matches(action, results: dict) -> None:
#     """Byte-compare each stage of the local encoding against the server's."""

#     assert action.module_data.to_abi_encoded().hex() == results["encoded_data"].removeprefix("0x")
#     assert action._get_action_hash().to_0x_hex() == results["action_hash"]
#     assert action._to_typed_data_hash().to_0x_hex() == results["typed_data_hash"]
#     action.validate_signature()


# @pytest.fixture(scope="session")
# def live_options(post) -> list[dict]:
#     """Two live ETH options, for multi-leg RFQ cases.

#     UNVERIFIED: v2's public/get_instruments was removed. This uses
#     get_all_instruments, whose response is paginated. Confirm the envelope key
#     and the asset-address field names against openapi.json.
#     """
#     result = post(
#         "public/get_all_instruments",
#         {
#             "instrument_type": "option",
#             "currency": "ETH",
#             "expired": False,
#             "page": 1,
#             "page_size": 100,
#         },
#     )
#     instruments = result["instruments"] if isinstance(result, dict) else result
#     live = [i for i in instruments if i["is_active"]]
#     if len(live) < 2:
#         pytest.skip("Need two live ETH options on testnet")
#     return live[:2]
