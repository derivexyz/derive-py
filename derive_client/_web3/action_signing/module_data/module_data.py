"""
Base class for all module data classes
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar


@dataclass
class ModuleData(ABC):
    """Abstract Base class for all module data classes"""

    #: Wallet-scoped actions (session key, whitelisted recipients) carry
    #: `wallet` in the request instead of `subaccount_id`, even though the
    #: action itself is still signed against subaccount 0.
    WALLET_SCOPED: ClassVar[bool] = False

    @abstractmethod
    def to_abi_encoded(self) -> bytes:
        """Return the data in ABI encoded format"""
        raise NotImplementedError

    @abstractmethod
    def to_json(self) -> dict:
        """Return the data in JSON format"""
        raise NotImplementedError
