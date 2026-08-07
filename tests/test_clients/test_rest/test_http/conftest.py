import time

import pytest

from derive_client._clients.rest.http.client import HTTPClient
from derive_client.data_types import Environment
from derive_client.data_types.generated_models import Vault
from tests.conftest import ADMIN_TEST_WALLET, OWNER_TEST_WALLET, SESSION_KEY_PRIVATE_KEY, SUBACCOUNT_ID_75723


@pytest.fixture(autouse=True)
def slow_down_every_test(request):
    time.sleep(1)


@pytest.fixture(scope="session")
def client_owner_wallet():
    """
    Client connected to a wallet where the session key is the owner.
    Full authority over the wallet is available, allowing owner-level operations.
    """
    subaccount_id = SUBACCOUNT_ID_75723
    client = HTTPClient(
        wallet=OWNER_TEST_WALLET,
        session_key=SESSION_KEY_PRIVATE_KEY,
        subaccount_id=subaccount_id,
        env=Environment.TEST,
    )
    client.connect()
    yield client
    client.orders.cancel_all()
    client.rfq.cancel_batch_rfqs()
    client.rfq.cancel_batch_quotes()
    client.disconnect()


@pytest.fixture(scope="session")
def client_admin_wallet():
    """
    Client connected to a wallet where the session key is registered as admin.
    This wallet is NOT owned by the session key, so only admin-level operations are allowed.
    """
    subaccount_id = SUBACCOUNT_ID_75723
    client = HTTPClient(
        wallet=ADMIN_TEST_WALLET,
        session_key=SESSION_KEY_PRIVATE_KEY,
        subaccount_id=subaccount_id,
        env=Environment.TEST,
    )

    client.connect()
    yield client
    client.orders.cancel_all()
    client.rfq.cancel_batch_rfqs()
    client.rfq.cancel_batch_quotes()
    client.disconnect()


@pytest.fixture
def any_vault(client_admin_wallet) -> Vault:
    """Any open vault on the exchange, curated by this wallet or not.

    Prefers one we curate: a curator may also hold shares in their own vault,
    so one fixture covers both roles. Skips rather than fails on an exchange
    with no vaults, so a clean environment does not look like a broken client.
    """

    curated = client_admin_wallet.vaults.list_curated().subaccount_ids
    if curated:
        return client_admin_wallet.vaults.get(vault_subaccount_id=curated[0])

    listed = client_admin_wallet.vaults.list_all(page=1, page_size=50).vaults
    for vault in listed:
        if not vault.whitelist_only and not vault.protocol.closed:
            return vault
    pytest.skip(f"no open vault on this environment ({len(listed)} listed)")


@pytest.fixture
def curated_vault(client_admin_wallet) -> int:
    """A vault this wallet curates.

    Required for the settle-queue reads and for anything acting as the vault
    subaccount. Creating one is irreversible, one-shot, and costs the seed
    deposit plus the creation fee, so this skips instead.
    """

    curated = client_admin_wallet.vaults.list_curated().subaccount_ids
    if not curated:
        pytest.skip("this wallet curates no vault; create one with --create-vault on the capture script")
    return curated[0]
