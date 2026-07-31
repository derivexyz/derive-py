"""Tests for MMP module."""

from derive_client.data_types.generated_models import (
    MmpConfigResult,
    SetMmpConfigResponse,
)


def test_mmp_get_config(client_owner_wallet):
    currency = None
    mmp_configs = client_owner_wallet.mmp.get_config(currency=currency)
    assert isinstance(mmp_configs, list)
    assert all(isinstance(item, MmpConfigResult) for item in mmp_configs)


def test_mmp_set_config(client_owner_wallet):
    currency = "BTC"
    mmp_frozen_time = 1
    mmp_interval = 1
    mmp_amount_limit = 0
    mmp_delta_limit = 0
    set_mmp_config = client_owner_wallet.mmp.set_config(
        currency=currency,
        mmp_frozen_time=mmp_frozen_time,
        mmp_interval=mmp_interval,
        mmp_amount_limit=mmp_amount_limit,
        mmp_delta_limit=mmp_delta_limit,
    )
    assert isinstance(set_mmp_config, SetMmpConfigResponse)


def test_mmp_reset(client_owner_wallet):
    currency = "ETH"
    result = client_owner_wallet.mmp.reset(currency=currency)
    assert isinstance(result, str)
