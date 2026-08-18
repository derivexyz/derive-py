import pytest
import pytest_asyncio

from derive_py._clients.rest.async_http.client import AsyncHTTPClient
from derive_py.data_types.generated_models import Vault
from tests.conftest import ENV_TEMPLATE


@pytest_asyncio.fixture(scope="session")
async def client_admin_wallet():
    """
    Client connected to a wallet where the session key is the owner.
    Full authority over the wallet is available, allowing owner-level operations.
    """
    client = AsyncHTTPClient.from_env(env_file=ENV_TEMPLATE)
    await client.connect()
    yield client
    await client.orders.cancel_all()
    await client.rfq.cancel_batch_rfqs()
    await client.rfq.cancel_batch_quotes()
    await client.disconnect()


@pytest_asyncio.fixture(scope="session")
async def any_vault(client_admin_wallet) -> Vault:
    """Any open vault on the exchange, curated by this wallet or not.

    Prefers one we curate: a curator may also hold shares in their own vault,
    so one fixture covers both roles. Skips rather than fails on an exchange
    with no vaults, so a clean environment does not look like a broken client.
    """

    curated = (await client_admin_wallet.vaults.list_curated()).subaccount_ids
    if curated:
        return await client_admin_wallet.vaults.get(vault_subaccount_id=curated[0])

    listed = (await client_admin_wallet.vaults.list_all(page=1, page_size=50)).vaults
    for vault in listed:
        if not vault.whitelist_only and not vault.protocol.closed:
            return vault
    pytest.skip(f"no open vault on this environment ({len(listed)} listed)")


@pytest_asyncio.fixture(scope="session")
async def curated_vault(client_admin_wallet) -> int:
    """A vault this wallet curates.

    Required for the settle-queue reads and for anything acting as the vault
    subaccount. Creating one is irreversible, one-shot, and costs the seed
    deposit plus the creation fee, so this skips instead.
    """

    curated = (await client_admin_wallet.vaults.list_curated()).subaccount_ids
    if not curated:
        pytest.skip("this wallet curates no vault; create one with --create-vault on the capture script")
    return curated[0]


@pytest.fixture(params=["subaccount", "wallet"])
def history_scope(request, client_admin_wallet):
    """Owner of a HistoryOperations namespace: the active Subaccount
    (subaccount-scoped history) or the LightAccount (wallet-scoped history)."""

    if request.param == "wallet":
        return client_admin_wallet.account
    return client_admin_wallet.active_subaccount
