"""Contract addresses and environment configurations."""

from __future__ import annotations

from derive_py.data_types import Chain, ChainConfig, ChecksumAddress, DeriveContractAddresses

# V3_MODULE_ADDRESSES
TRADE_MODULE = ChecksumAddress("0xB8D20c2B7a1Ad2EE33Bc50eF10876eD3035b5e7b")
TRANSFER_MODULE = ChecksumAddress("0x01259207A40925b794C8ac320456F7F6c8FE2636")
WITHDRAW_MODULE = ChecksumAddress("0x9d0E8f5b25384C7310CB8C6aE32C8fbeb645d083")
RFQ_MODULE = ChecksumAddress("0x9371352CCef6f5b36EfDFE90942fFE622Ab77F1D")
EXTERNAL_TRANSFER_MODULE = ChecksumAddress("0x8F9B8f12ddA05FB1F0DDDDe8f5af8cECF54f8aC9")
WHITELISTED_RECIPIENT_MODULE = ChecksumAddress("0xB86D6DE1b76c9839e4BA860848CD98A1dABd6B54")
VAULT_MODULE = ChecksumAddress("0x2885c174ebf5524aED9c721d60c12b1537685186")
LIQUIDATION_MODULE = ChecksumAddress("0x66d23e59DaEEF13904eFA2D4B8658aeD05f59a92")
CREATE_SESSION_KEY_MODULE = ChecksumAddress("0xe330CF64ff6EbF41699aad344Cb21d78db1D2bb6")

# V3 settlement contracts (Sepolia), per https://docs.derive.xyz/getting-started/contracts
# derive_py/data/abis/sepolia/ is generated FROM these by scripts/download-abis.py.
ACTION_MANAGER = ChecksumAddress("0xd3625eCf97E5554C62A48Ac1c9284C9dCeFceB68")
VAPP = ChecksumAddress("0x1573bde26338A9E6AA358638679A796c81E33246")
WITHDRAWAL_OUTBOX = ChecksumAddress("0xFbB62CE2BbFdFdc8a60DDC22115aC29cf91B4566")
SPOT_VAULT = ChecksumAddress("0x3FB79aafCD401CDD19e3d729241545955DDE0D48")


CONFIGS: dict[Chain, ChainConfig] = {
    Chain.SEPOLIA: ChainConfig(
        base_url="https://testnet.api.derive.xyz/v3",
        ws_address="wss://testnet.api.derive.xyz/v3/ws",
        ACTION_TYPEHASH="0x4d7a9f27c403ff9c0f19bce61d76d82f9aa29f8d6d4b0c5474607d9770d1af17",
        DOMAIN_SEPARATOR="0x24d674cd5f2b9d564691c51e9d88f649b99246a2244dd74ce27b96578d773e85",
        contracts=DeriveContractAddresses(
            TRADE_MODULE=TRADE_MODULE,
            TRANSFER_MODULE=TRANSFER_MODULE,
            WITHDRAW_MODULE=WITHDRAW_MODULE,
            RFQ_MODULE=RFQ_MODULE,
            EXTERNAL_TRANSFER_MODULE=EXTERNAL_TRANSFER_MODULE,
            WHITELISTED_RECIPIENT_MODULE=WHITELISTED_RECIPIENT_MODULE,
            VAULT_MODULE=VAULT_MODULE,
            LIQUIDATION_MODULE=LIQUIDATION_MODULE,
            CREATE_SESSION_KEY_MODULE=CREATE_SESSION_KEY_MODULE,
            ACTION_MANAGER=ACTION_MANAGER,
            VAPP=VAPP,
            WITHDRAWAL_OUTBOX=WITHDRAWAL_OUTBOX,
            SPOT_VAULT=SPOT_VAULT,
        ),
    ),
    Chain.ETHEREUM: ChainConfig(  # TODO: verify these addresses against the mainnet
        base_url="https://api.derive.xyz/v3",
        ws_address="wss://api.derive.xyz/v3/ws",
        ACTION_TYPEHASH="0x4d7a9f27c403ff9c0f19bce61d76d82f9aa29f8d6d4b0c5474607d9770d1af17",
        DOMAIN_SEPARATOR="0xda616dfabb88681b08e1592820a41d55ddc62d68de110e327ae99d734506fe19",
        contracts=DeriveContractAddresses(
            TRADE_MODULE=TRADE_MODULE,
            TRANSFER_MODULE=TRANSFER_MODULE,
            WITHDRAW_MODULE=WITHDRAW_MODULE,
            RFQ_MODULE=RFQ_MODULE,
            EXTERNAL_TRANSFER_MODULE=EXTERNAL_TRANSFER_MODULE,
            WHITELISTED_RECIPIENT_MODULE=WHITELISTED_RECIPIENT_MODULE,
            VAULT_MODULE=VAULT_MODULE,
            LIQUIDATION_MODULE=LIQUIDATION_MODULE,
            CREATE_SESSION_KEY_MODULE=CREATE_SESSION_KEY_MODULE,
            ACTION_MANAGER=ACTION_MANAGER,
            VAPP=VAPP,
            WITHDRAWAL_OUTBOX=WITHDRAWAL_OUTBOX,
            SPOT_VAULT=SPOT_VAULT,
        ),
    ),
}
