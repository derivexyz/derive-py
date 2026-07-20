"""Contract addresses and environment configurations."""

from derive_client.data_types import ChecksumAddress, DeriveContractAddresses, EnvConfig, Environment

from .constants import ABI_DATA_DIR

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


CONFIGS: dict[Environment, EnvConfig] = {
    Environment.TEST: EnvConfig(
        base_url="https://testnet.api.derive.xyz/v3",
        ws_address="wss://testnet.api.derive.xyz/v3/ws",
        rpc_endpoint="https://testnet-rpc.derive.xyz",
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
        ),
    ),
    Environment.PROD: EnvConfig(
        base_url="https://api.derive.xyz/v3",
        ws_address="wss://api.derive.xyz/v3/ws",
        rpc_endpoint="https://957.rpc.thirdweb.com/",
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
        ),
    ),
}


NEW_VAULT_ABI_PATH = ABI_DATA_DIR / "socket_superbridge_vault.json"
OLD_VAULT_ABI_PATH = ABI_DATA_DIR / "socket_superbridge_vault_old.json"
DEPOSIT_HELPER_ABI_PATH = ABI_DATA_DIR / "deposit_helper.json"
CONTROLLER_ABI_PATH = ABI_DATA_DIR / "controller.json"
CONTROLLER_V0_ABI_PATH = ABI_DATA_DIR / "controller_v0.json"
DEPOSIT_HOOK_ABI_PATH = ABI_DATA_DIR / "deposit_hook.json"
LIGHT_ACCOUNT_ABI_PATH = ABI_DATA_DIR / "light_account.json"
L1_CHUG_SPLASH_PROXY_ABI_PATH = ABI_DATA_DIR / "l1_chug_splash_proxy.json"
L1_STANDARD_BRIDGE_ABI_PATH = ABI_DATA_DIR / "l1_standard_bridge.json"
L1_CROSS_DOMAIN_MESSENGER_ABI_PATH = ABI_DATA_DIR / "l1_cross_domain_messenger.json"
L2_STANDARD_BRIDGE_ABI_PATH = ABI_DATA_DIR / "l2_standard_bridge.json"
L2_CROSS_DOMAIN_MESSENGER_ABI_PATH = ABI_DATA_DIR / "l2_cross_domain_messenger.json"
WITHDRAW_WRAPPER_V2_ABI_PATH = ABI_DATA_DIR / "withdraw_wrapper_v2.json"
DERIVE_ABI_PATH = ABI_DATA_DIR / "Derive.json"
DERIVE_L2_ABI_PATH = ABI_DATA_DIR / "DeriveL2.json"
LYRA_OFT_WITHDRAW_WRAPPER_ABI_PATH = ABI_DATA_DIR / "LyraOFTWithdrawWrapper.json"
ERC20_ABI_PATH = ABI_DATA_DIR / "erc20.json"
SOCKET_ABI_PATH = ABI_DATA_DIR / "Socket.json"
CONNECTOR_PLUG = ABI_DATA_DIR / "ConnectorPlug.json"


# ===========================
# Bridge Contract Addresses
# ===========================
LYRA_OFT_WITHDRAW_WRAPPER = ChecksumAddress("0x9400cc156dad38a716047a67c897973A29A06710")
L1_CHUG_SPLASH_PROXY = ChecksumAddress("0x61e44dc0dae6888b5a301887732217d5725b0bff")
RESOLVED_DELEGATE_PROXY = ChecksumAddress("0x5456f02c08e9A018E42C39b351328E5AA864174A")
L2_STANDARD_BRIDGE_PROXY = ChecksumAddress("0x4200000000000000000000000000000000000010")
L2_CROSS_DOMAIN_MESSENGER_PROXY = ChecksumAddress("0x4200000000000000000000000000000000000007")
WITHDRAW_WRAPPER_V2 = ChecksumAddress("0xea8E683D8C46ff05B871822a00461995F93df800")
ETH_DEPOSIT_WRAPPER = ChecksumAddress("0x46e75B6983126896227a5717f2484efb04A0c151")
BASE_DEPOSIT_WRAPPER = ChecksumAddress("0x9628bba16db41ea7fe1fd84f9ce53bc27c63f59b")
ARBITRUM_DEPOSIT_WRAPPER = ChecksumAddress("0x076BB6117750e80AD570D98891B68da86C203A88")
OPTIMISM_DEPOSIT_WRAPPER = ChecksumAddress("0xC65005131Cfdf06622b99E8E17f72Cf694b586cC")
