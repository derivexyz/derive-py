"""Tests for MMP module."""

import pytest

from derive_client.data_types.generated_models import (
    MmpConfigResult,
    SetMmpConfigResponse,
)


@pytest.mark.asyncio
async def test_mmp_get_config(client_admin_wallet):
    currency = None
    mmp_configs = await client_admin_wallet.mmp.get_config(currency=currency)
    assert isinstance(mmp_configs, list)
    assert all(isinstance(item, MmpConfigResult) for item in mmp_configs)


@pytest.mark.asyncio
async def test_mmp_set_config(client_admin_wallet):
    currency = "BTC"
    mmp_frozen_time = 1
    mmp_interval = 1
    mmp_amount_limit = 0
    mmp_delta_limit = 0
    set_mmp_config = await client_admin_wallet.mmp.set_config(
        currency=currency,
        mmp_frozen_time=mmp_frozen_time,
        mmp_interval=mmp_interval,
        mmp_amount_limit=mmp_amount_limit,
        mmp_delta_limit=mmp_delta_limit,
    )
    assert isinstance(set_mmp_config, SetMmpConfigResponse)


@pytest.mark.asyncio
async def test_mmp_reset(client_admin_wallet):
    currency = "ETH"
    result = await client_admin_wallet.mmp.reset(currency=currency)
    assert isinstance(result, str)
