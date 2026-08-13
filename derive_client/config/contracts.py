"""Contract addresses and environment configurations."""

from __future__ import annotations

from derive_client.data_types import ChecksumAddress, DeriveContractAddresses, EnvConfig, Environment

from .constants import ETHEREUM_MAINNET_CHAIN_ID, SEPOLIA_CHAIN_ID

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

# V3 contract addresses, verified against derive_client/data/abis/sepolia/contracts.json
ACTION_MANAGER = ChecksumAddress("0x1b4f369b585D40a27F66775844FC265151f278A4")
VAPP = ChecksumAddress("0x806A2f83d5E01a5526629c1A5FB4A4AAc60bc393")
WITHDRAWAL_OUTBOX = ChecksumAddress("0x55B1A897E2ecbb4489218E961C64f3E6b1F0f988")
SPOT_VAULT = ChecksumAddress("0xB20790d63f648feA1A23948CDF1B8769DF78a173")


CONFIGS: dict[Environment, EnvConfig] = {
    Environment.TEST: EnvConfig(
        base_url="https://testnet.api.derive.xyz/v3",
        ws_address="wss://testnet.api.derive.xyz/v3/ws",
        chain_id=SEPOLIA_CHAIN_ID,
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
    Environment.PROD: EnvConfig(  # TODO: verify these addresses against the mainnet
        base_url="https://api.derive.xyz/v3",
        ws_address="wss://api.derive.xyz/v3/ws",
        chain_id=ETHEREUM_MAINNET_CHAIN_ID,
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
