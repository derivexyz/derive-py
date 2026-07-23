"""Network and chain configurations."""

from enum import Enum, IntEnum

from derive_client.data_types import ChecksumAddress


class LayerZeroChainIDv2(IntEnum):
    # https://docs.layerzero.network/v2/deployments/deployed-contracts
    ETH = 30101
    ARBITRUM = 30110
    OPTIMISM = 30111
    BASE = 30184
    DERIVE = 30311


class SocketAddress(Enum):
    ETH = ChecksumAddress("0x943ac2775928318653e91d350574436a1b9b16f9")
    ARBITRUM = ChecksumAddress("0x37cc674582049b579571e2ffd890a4d99355f6ba")
    OPTIMISM = ChecksumAddress("0x301bD265F0b3C16A58CbDb886Ad87842E3A1c0a4")
    BASE = ChecksumAddress("0x12E6e58864cE4402cF2B4B8a8E9c75eAD7280156")
    DERIVE = ChecksumAddress("0x565810cbfa3Cf1390963E5aFa2fB953795686339")


class DeriveTokenAddress(Enum):
    # https://www.coingecko.com/en/coins/derive

    # impl: 0x4909ad99441ea5311b90a94650c394cea4a881b8 (Derive)
    ETH = ChecksumAddress("0xb1d1eae60eea9525032a6dcb4c1ce336a1de71be")

    # impl: 0x1eda1f6e04ae37255067c064ae783349cf10bdc5 (DeriveL2)
    OPTIMISM = ChecksumAddress("0x33800de7e817a70a694f31476313a7c572bba100")

    # impl: 0x01259207a40925b794c8ac320456f7f6c8fe2636 (DeriveL2)
    BASE = ChecksumAddress("0x9d0e8f5b25384c7310cb8c6ae32c8fbeb645d083")

    # impl: 0x5d22b63d83a9be5e054df0e3882592ceffcef097 (DeriveL2)
    ARBITRUM = ChecksumAddress("0x77b7787a09818502305c95d68a2571f090abb135")

    # impl: 0x340B51Cb46DBF63B55deD80a78a40aa75Dd4ceDF (DeriveL2)
    DERIVE = ChecksumAddress("0x2EE0fd70756EDC663AcC9676658A1497C247693A")
