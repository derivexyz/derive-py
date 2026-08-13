"""Deterministic synthetic instances for any msgspec Struct.

Derive's testnet carries no dense order flow, so benchmark payloads are
generated from the schema rather than recorded. This walks the type tree with
``msgspec.inspect`` and fabricates a plausible value for every leaf, seeded so
two runs on the same commit produce byte-identical frames. That property is
what makes run-to-run comparison meaningful: a change in measured time is a
change in the code, not in the data.

Values are plausible, not valid. Numbers land in sane ranges and strings look
like the identifiers Derive uses, but nothing here honours cross-field
invariants. Do not feed the output to anything that validates.
"""

from __future__ import annotations

import random
import string
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

import msgspec
import msgspec.inspect as mi

NODEFAULT = msgspec.NODEFAULT

#: Realistic-looking values for field names that show up across the spec. Keyed
#: on the Python field name, matched before the type-driven fallback, so a
#: generated frame compresses and decodes like a real one rather than like
#: random noise.
FIELD_HINTS: dict[str, tuple[str, ...]] = {
    "instrument_name": ("BTC-PERP", "ETH-PERP", "BTC-20260828-80000-C", "ETH-20260828-4000-P"),
    "currency": ("BTC", "ETH", "USDC", "SOL"),
    "wallet": ("0x9135BA0f495244dc0A5F029b25CDE95157Db89AD",),
    "signer": ("0x1f3E1BbC0eb1b2C3D4b56789aBCdEf0123456789",),
    "tx_hash": ("0x" + "ab" * 32,),
    "status": ("filled", "open", "cancelled"),
    "asset_name": ("USDC", "ETH", "BTC"),
}

_PRICE_FIELDS = frozenset(
    {
        "price",
        "trade_price",
        "mark_price",
        "index_price",
        "min_price",
        "max_price",
        "best_bid_price",
        "best_ask_price",
        "limit_price",
    }
)
_AMOUNT_FIELDS = frozenset(
    {
        "amount",
        "trade_amount",
        "best_bid_amount",
        "best_ask_amount",
        "filled_amount",
        "remaining_amount",
    }
)


@dataclass
class SynthConfig:
    """Knobs for the generator.

    ``list_len`` drives payload size, which is the single most important
    variable in the receive-path benchmarks: decode cost is dominated by
    element count, not by frame count.
    """

    seed: int = 0
    list_len: int = 8
    dict_len: int = 4
    max_depth: int = 6
    #: Probability that an optional field with no default (i.e. one that
    #: defaults to UNSET) is populated rather than omitted. Derive's responses
    #: populate most of them, so the default leans high.
    optional_fill: float = 0.8
    #: Probability that a nullable field is emitted as None rather than a value.
    null_rate: float = 0.05


class Synth:
    """Generates instances of msgspec types.

    One instance holds one RNG. Reusing it across calls keeps successive
    payloads different from each other while keeping the whole sequence
    reproducible from the seed.
    """

    def __init__(self, config: SynthConfig | None = None) -> None:
        self.config = config or SynthConfig()
        self.rng = random.Random(self.config.seed)

    def reset(self) -> None:
        self.rng.seed(self.config.seed)

    def build(self, type_: Any, *, field_name: str | None = None) -> Any:
        """Build one instance of ``type_``."""
        return self._value(mi.type_info(type_), 0, field_name)

    def build_many(self, type_: Any, count: int) -> list[Any]:
        info = mi.type_info(type_)
        return [self._value(info, 0, None) for _ in range(count)]

    # -- dispatch ---------------------------------------------------------

    def _value(self, t: mi.Type, depth: int, name: str | None) -> Any:  # noqa: C901
        rng = self.rng

        if isinstance(t, mi.UnionType):
            return self._union(t, depth, name)
        if isinstance(t, mi.StructType):
            return self._struct(t, depth)
        if isinstance(t, mi.EnumType):
            return rng.choice(list(t.cls))
        if isinstance(t, mi.LiteralType):
            return rng.choice(list(t.values))
        if isinstance(t, mi.NoneType):
            return None
        if isinstance(t, mi.BoolType):
            return rng.random() < 0.5
        if isinstance(t, mi.IntType):
            return self._int(t, name)
        if isinstance(t, mi.FloatType):
            return round(rng.uniform(0.0, 1000.0), 6)
        if isinstance(t, mi.DecimalType):
            return self._decimal(name)
        if isinstance(t, mi.StrType):
            return self._str(t, name)
        if isinstance(t, (mi.BytesType, mi.ByteArrayType, mi.MemoryViewType)):
            return rng.randbytes(16)
        if isinstance(t, mi.DateTimeType):
            return datetime.now(timezone.utc) - timedelta(seconds=rng.randint(0, 86_400))
        if isinstance(t, mi.DateType):
            return date.today()
        if isinstance(t, mi.TimeType):
            return time(rng.randrange(24), rng.randrange(60), rng.randrange(60), tzinfo=timezone.utc)
        if isinstance(t, mi.TimeDeltaType):
            return timedelta(seconds=rng.randint(0, 3600))
        if isinstance(t, mi.UUIDType):
            return UUID(int=rng.getrandbits(128), version=4)
        if isinstance(t, mi.RawType):
            return msgspec.Raw(b"{}")
        if isinstance(t, (mi.ListType, mi.SetType, mi.FrozenSetType, mi.VarTupleType)):
            return self._collection(t, depth)
        if isinstance(t, mi.TupleType):
            return tuple(self._value(item, depth + 1, name) for item in t.item_types)
        if isinstance(t, mi.DictType):
            return self._dict(t, depth)
        if isinstance(t, (mi.TypedDictType, mi.NamedTupleType, mi.DataclassType)):
            return self._object_like(t, depth)
        if isinstance(t, mi.AnyType):
            return {"k": self._token(8)}
        if isinstance(t, mi.CustomType):
            raise TypeError(
                f"No synthetic generator for custom type {t.cls!r}. Add a hook rather than "
                "letting the benchmark silently measure a placeholder."
            )
        raise TypeError(f"Unhandled msgspec type in synth: {type(t).__name__}")

    # -- composites -------------------------------------------------------

    def _union(self, t: mi.UnionType, depth: int, name: str | None) -> Any:
        members = [m for m in t.types if not isinstance(m, mi.NoneType)]
        nullable = len(members) != len(t.types)
        if not members:
            return None
        if nullable and self.rng.random() < self.config.null_rate:
            return None
        # Prefer the first non-null member: unions in the generated models are
        # almost always `T | None`, and picking randomly across a genuine
        # multi-member union would make payload size unstable between runs.
        return self._value(members[0], depth + 1, name)

    def _struct(self, t: mi.StructType, depth: int) -> Any:
        kwargs: dict[str, Any] = {}
        for f in t.fields:
            if f.required:
                kwargs[f.name] = self._value(f.type, depth + 1, f.name)
                continue
            if depth >= self.config.max_depth:
                continue
            if f.default is not NODEFAULT or f.default_factory is not NODEFAULT:
                # Field has a real default (including the spec's own defaults and
                # the pinned referral_code/client constants). Leave it alone so
                # the benchmark exercises what the client actually sends.
                continue
            if self.rng.random() < self.config.optional_fill:
                kwargs[f.name] = self._value(f.type, depth + 1, f.name)
        return t.cls(**kwargs)

    def _object_like(self, t: Any, depth: int) -> Any:
        kwargs = {
            f.name: self._value(f.type, depth + 1, f.name)
            for f in t.fields
            if f.required or self.rng.random() < self.config.optional_fill
        }
        return t.cls(**kwargs)

    def _collection(self, t: Any, depth: int) -> Any:
        n = 0 if depth >= self.config.max_depth else self.config.list_len
        items = [self._value(t.item_type, depth + 1, None) for _ in range(n)]
        if isinstance(t, mi.SetType):
            return set(items)
        if isinstance(t, mi.FrozenSetType):
            return frozenset(items)
        if isinstance(t, mi.VarTupleType):
            return tuple(items)
        return items

    def _dict(self, t: mi.DictType, depth: int) -> dict:
        n = 0 if depth >= self.config.max_depth else self.config.dict_len
        out = {}
        for _ in range(n):
            key = self._value(t.key_type, depth + 1, None)
            out[key] = self._value(t.value_type, depth + 1, None)
        return out

    # -- leaves -----------------------------------------------------------

    def _int(self, t: mi.IntType, name: str | None) -> int:
        if name and ("timestamp" in name or name.endswith("_sec") or name.endswith("_ms")):
            return self.rng.randrange(1_750_000_000_000, 1_760_000_000_000)
        lo = t.ge if t.ge is not None else (t.gt + 1 if t.gt is not None else 0)
        hi = t.le if t.le is not None else (t.lt - 1 if t.lt is not None else 1_000_000)
        if lo > hi:
            lo, hi = hi, lo
        return self.rng.randrange(lo, hi + 1)

    def _decimal(self, name: str | None) -> Decimal:
        if name in _PRICE_FIELDS:
            return Decimal(f"{self.rng.uniform(100, 120_000):.2f}")
        if name in _AMOUNT_FIELDS:
            return Decimal(f"{self.rng.uniform(0.001, 50):.4f}")
        return Decimal(f"{self.rng.uniform(-500, 500):.6f}")

    def _str(self, t: mi.StrType, name: str | None) -> str:
        if name:
            if name in FIELD_HINTS:
                return self.rng.choice(FIELD_HINTS[name])
            if name in _PRICE_FIELDS:
                return f"{self.rng.uniform(100, 120_000):.2f}"
            if name in _AMOUNT_FIELDS:
                return f"{self.rng.uniform(0.001, 50):.4f}"
            if name.endswith("_id") or name == "nonce":
                return str(self.rng.randrange(10**17, 10**18))
            if "uuid" in name:
                return str(UUID(int=self.rng.getrandbits(128), version=4))
            if "address" in name or name.endswith("_hash") or "signature" in name:
                return "0x" + "".join(self.rng.choices("0123456789abcdef", k=40))
        n = t.min_length or 12
        if t.max_length is not None:
            n = min(n, t.max_length)
        return self._token(n)

    def _token(self, n: int) -> str:
        return "".join(self.rng.choices(string.ascii_lowercase + string.digits, k=n))
