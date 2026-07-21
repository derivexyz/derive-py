"""Unified API generation script for REST and WebSocket clients"""

import json
import re
import sys
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import libcst as cst
from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, str(Path(__file__).parent))
import paths  # noqa: E402

# Paths — sourced from paths.py (single source of truth across the codegen
# pipeline); see that module's docstring for why. OPENAPI_SPEC points at the
# *patched* spec, not the raw one — generated_models.py is built from the
# patched version (erc20_details fix, split-enum collapse), so classifying
# rest_schema_names against the raw spec instead would be inconsistent with
# what's actually importable from generated_models.py.
PACKAGE_DIR = paths.DERIVE_CLIENT_DIR
OPENAPI_SPEC = paths.OPENAPI_SPEC_PATCHED
CHANNELS_DIR = Path("specs") / "channels"  # legacy path, superseded by the two specs below
SUBSCRIPTIONS_ASYNCAPI = paths.SUBSCRIPTIONS_ASYNCAPI
WEBSOCKET_ASYNCAPI = paths.WEBSOCKET_ASYNCAPI
TEMPLATES_DIR = PACKAGE_DIR / "data" / "templates"
OUTPUT_DIR = PACKAGE_DIR / "_clients"
GENERATED_MODELS_PATH = paths.GENERATED_MODELS
CHANNEL_MODELS_PATH = paths.CHANNEL_MODELS

# Channel classifications from docs
PUBLIC_CHANNELS = {
    "orderbook.instrument_name.group.depth",
    "ticker_slim.instrument_name.interval",
    "spot_feed.currency",
    "trades.instrument_name",
    "trades.instrument_type.currency",
    "trades.instrument_type.currency.tx_status",
    "margin.watch",
    "auctions.watch",
}

PRIVATE_CHANNELS = {
    "subaccount_id.best.quotes",
    "subaccount_id.quotes",
    "subaccount_id.trades.tx_status",
    "wallet.rfqs",
    "subaccount_id.balances",
    "subaccount_id.orders",
    "subaccount_id.trades",
}


@dataclass
class MethodInfo:
    name: str
    path: str
    request_type: str
    response_type: str
    result_type: str
    description: str


@dataclass
class ParamInfo:
    name: str
    type_annotation: str
    is_enum: bool = False


@dataclass
class ChannelInfo:
    name: str  # Python method name
    channel_pattern: str  # e.g., "{subaccount_id}.best.quotes"
    params_type: str  # ChannelParamsSchema
    notification_type: str  # NotificationSchema
    notification_data_type: str = "Any"  # Actual data payload type
    description: str = ""
    params: list[ParamInfo] = field(default_factory=list)


class ResponseSchemaParser(cst.CSTVisitor):
    """Parse generated_models.py to extract actual result field types from ResponseSchema classes."""

    def __init__(self):
        self.result_types: dict[str, str] = {}
        self.class_bases: dict[str, list[str]] = {}
        self.class_fields: dict[str, dict[str, str]] = {}
        self.current_class: Optional[str] = None

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        class_name = node.name.value
        self.current_class = class_name
        self.class_fields.setdefault(class_name, {})

        bases = []
        for base in node.bases:
            try:
                base_name = self._annotation_to_string(base.value)
            except Exception:
                base_name = ""
            base_name = base_name.split("[", 1)[0].strip()
            if base_name:
                if "." in base_name:
                    base_name = base_name.rsplit(".", 1)[-1]
                bases.append(base_name)
        self.class_bases[class_name] = bases

    def leave_ClassDef(self, node: cst.ClassDef) -> None:
        self.current_class = None

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        if not self.current_class:
            return

        target = node.target
        field_name = target.value if isinstance(target, cst.Name) else self._annotation_to_string(target)

        annotation_node = getattr(node, "annotation", None)
        if not annotation_node:
            return

        annot_expr = annotation_node.annotation
        field_type = self._annotation_to_string(annot_expr).strip()

        if (field_type.startswith("'") and field_type.endswith("'")) or (
            field_type.startswith('"') and field_type.endswith('"')
        ):
            field_type = field_type[1:-1]

        self.class_fields.setdefault(self.current_class, {})[field_name] = field_type

    def _annotation_to_string(self, node: cst.BaseExpression) -> str:
        try:
            text = cst.Module([]).code_for_node(node)
            return text.strip()
        except Exception:
            return repr(node)

    def get_result_type(self, response_schema_name: str) -> str:
        if response_schema_name in self.result_types:
            return self.result_types[response_schema_name]

        result_type = self._find_result_field(response_schema_name)
        if not result_type:
            # No {result: ...} envelope in the current spec anymore,
            # the response schema already IS the payload.
            result_type = response_schema_name

        self.result_types[response_schema_name] = result_type
        return result_type

    def _find_result_field(self, class_name: str, visited: Optional[set] = None) -> Optional[str]:
        if visited is None:
            visited = set()
        if class_name in visited:
            return None
        visited.add(class_name)

        fields = self.class_fields.get(class_name, {})
        if "result" in fields:
            return fields["result"]

        for base in self.class_bases.get(class_name, []):
            if base in {"Struct", "object"}:
                continue
            result_type = self._find_result_field(base, visited)
            if result_type:
                return result_type
        return None


class ChannelModelParser(cst.CSTVisitor):
    """Parse generated channel model files to extract schema and enum types."""

    def __init__(self):
        self.schemas: dict[str, dict[str, str]] = {}  # class_name -> {field_name: type}
        self.enums: set[str] = set()
        self.current_class: Optional[str] = None
        self.current_file_enums: set[str] = set()  # Track enums in current file

    def visit_Module(self, node: cst.Module) -> None:
        """Reset file-level enum tracking for each module."""
        self.current_file_enums = set()

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        class_name = node.name.value
        self.current_class = class_name

        # Check if it's an Enum
        for base in node.bases:
            try:
                base_name = self._annotation_to_string(base.value)
                if "Enum" in base_name:
                    self.enums.add(class_name)
                    self.current_file_enums.add(class_name)
                    return
            except Exception:
                continue

        # It's a Struct schema - initialize with empty dict
        self.schemas.setdefault(class_name, {})

        # Check for inheritance from other schema classes
        for base in node.bases:
            try:
                base_name = self._annotation_to_string(base.value)
                # Skip base classes like Struct, Enum, or standard Python classes
                if base_name not in ("Struct", "Enum") and base_name in self.schemas:
                    # Copy parent fields to child
                    self.schemas[class_name] = self.schemas[base_name].copy()
                    break  # Assuming single inheritance for schemas
            except Exception:
                continue

    def leave_ClassDef(self, node: cst.ClassDef) -> None:
        self.current_class = None

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        if not self.current_class or self.current_class in self.enums:
            return

        target = node.target
        field_name = target.value if isinstance(target, cst.Name) else self._annotation_to_string(target)

        annotation_node = getattr(node, "annotation", None)
        if not annotation_node:
            return

        annot_expr = annotation_node.annotation
        field_type = self._annotation_to_string(annot_expr).strip()

        if (field_type.startswith("'") and field_type.endswith("'")) or (
            field_type.startswith('"') and field_type.endswith('"')
        ):
            field_type = field_type[1:-1]

        self.schemas[self.current_class][field_name] = field_type

    def _annotation_to_string(self, node: cst.BaseExpression) -> str:
        try:
            text = cst.Module([]).code_for_node(node)
            return text.strip()
        except Exception:
            return repr(node)


def detect_import_conflicts(
    rpc_schema_imports: set[str],
    channel_schema_imports: set[str],
) -> tuple[dict[str, str], dict[str, str]]:
    """Detect naming conflicts between RPC and channel schemas.

    Returns:
        tuple: (rpc_aliases, channel_aliases) where keys are original names
               and values are aliased names
    """
    conflicts = rpc_schema_imports & channel_schema_imports

    rpc_aliases = {}
    channel_aliases = {}

    for name in conflicts:
        # Use suffixes to distinguish between RPC and Channel versions
        rpc_aliases[name] = f"{name}RPC"
        channel_aliases[name] = f"{name}Channel"

    return rpc_aliases, channel_aliases


def parse_channel_models(channels_models_path: Path) -> tuple[dict[str, dict[str, str]], set[str]]:
    """Parse all generated channel model files to extract schemas and enums."""

    parser = ChannelModelParser()
    source = channels_models_path.read_text()
    tree = cst.parse_module(source)
    tree.visit(parser)

    return parser.schemas, parser.enums


def extract_schema_names_from_type(type_annotation: str) -> set[str]:
    """Extract actual schema class names from type annotation, filtering out generics and builtins."""

    BUILTINS = {
        "str",
        "int",
        "float",
        "bool",
        "bytes",
        "None",
        "Any",
        "dict",
        "list",
        "set",
        "tuple",
        "frozenset",
    }
    GENERICS = {
        "List",
        "Dict",
        "Set",
        "Tuple",
        "FrozenSet",
        "Union",
        "Optional",
        "Literal",
        "Annotated",
        "Sequence",
        "Mapping",
        "Iterable",
    }

    pattern = r'\b([A-Z][a-zA-Z0-9_]*)\b'
    matches = re.findall(pattern, type_annotation)

    schema_names = set()
    for match in matches:
        if match not in GENERICS and match not in BUILTINS:
            schema_names.add(match)

    return schema_names


def resolve_response_type(schema: dict, parser: "ResponseSchemaParser", schemas: dict) -> str:
    """
    Resolve a 200-response schema to the Python type the generated SDK
    method should return. Handles:
      - {"$ref": ".../X"}                              -> X (via get_result_type)
      - singleton string enum ({"enum": ["ok"]})        -> Literal["ok"]
                                                            (datamodel-code-generator
                                                            emits no importable symbol
                                                            for these, inline instead)
      - {"type": "array", "items": {"$ref": ".../X"}}  -> list[X]
      - bare primitive ({"type": "integer"}, etc.)     -> matching builtin
    """
    if "$ref" in schema:
        name = schema["$ref"].split("/")[-1]
        target = schemas.get(name, {})
        enum_values = target.get("enum")
        if target.get("type") == "string" and enum_values and len(enum_values) == 1:
            return "str"
        return parser.get_result_type(name)

    if schema.get("type") == "array":
        items = schema.get("items", {})
        item_type = resolve_response_type(items, parser, schemas) if items else "Any"
        return f"list[{item_type}]"

    PRIMITIVES = {"integer": "int", "number": "float", "string": "str", "boolean": "bool"}
    t = schema.get("type")
    if isinstance(t, list):
        t = next((x for x in t if x != "null"), None)
    return PRIMITIVES.get(t, "dict")


def parse_openapi_for_rpc(spec_path: Path, parser: ResponseSchemaParser):
    """Parse OpenAPI spec for RPC methods."""

    data = json.loads(spec_path.read_text())

    public_methods = []
    private_methods = []
    schema_imports = set()

    for path, spec in data["paths"].items():
        post_spec = spec["post"]
        request_ref = post_spec["requestBody"]["content"]["application/json"]["schema"]["$ref"]
        response_schema = post_spec["responses"]["200"]["content"]["application/json"]["schema"]

        name = path.split("/")[-1]
        request_type = request_ref.split("/")[-1]
        result_type = result_type = resolve_response_type(response_schema, parser, data["components"]["schemas"])
        response_type = response_schema.get("$ref", "").split("/")[-1] or result_type
        description = post_spec.get("description") or post_spec.get("summary", "")

        schema_imports.add(request_type)
        schema_imports.update(extract_schema_names_from_type(result_type))

        method = MethodInfo(
            name=name,
            path=path,
            request_type=request_type,
            response_type=response_type,
            result_type=result_type,
            description=description,
        )

        if path.startswith("/public"):
            public_methods.append(method)
        else:
            private_methods.append(method)

    return public_methods, private_methods, schema_imports


def parse_channel_name(filename: str) -> tuple[str, list[str]]:
    """Parse channel filename to extract channel pattern and parameters."""

    name = filename.replace("channel.", "").replace(".json", "")
    params = []
    parts = name.split(".")

    param_patterns = {
        "wallet",
        "subaccount_id",
        "instrument_name",
        "instrument_type",
        "currency",
        "group",
        "depth",
        "interval",
        "tx_status",
    }

    for part in parts:
        if part in param_patterns:
            params.append(part)

    return name, params


def to_python_method_name(channel_name: str) -> str:
    """Convert channel name to Python method name with disambiguation."""

    parts = channel_name.split(".")
    param_indicators = {"instrument_name", "instrument_type", "currency", "subaccount_id", "wallet"}

    method_parts = []
    found_params = []

    for part in parts:
        if part in param_indicators:
            found_params.append(part)
        else:
            method_parts.append(part)

    base_name = "_".join(method_parts)

    if found_params:
        suffix = f"by_{found_params[0]}"
        return f"{base_name}_{suffix}"

    return base_name


def extract_schema_types(schema_data: dict) -> tuple[str, str]:
    """Extract channel params and notification schema types from JSON schema."""

    definitions = schema_data.get("definitions", {})

    pubsub_schema = None
    for name, defn in definitions.items():
        if "PubSubSchema" in name:
            pubsub_schema = defn
            break

    if not pubsub_schema:
        return "dict", "dict"

    props = pubsub_schema.get("properties", {})

    params_ref = props.get("channel_params", {}).get("$ref", "")
    params_type = params_ref.split("/")[-1] if params_ref else "dict"

    notification_ref = props.get("notification", {}).get("$ref", "")
    notification_type = notification_ref.split("/")[-1] if notification_ref else "dict"

    return params_type, notification_type


def get_notification_data_type(
    notification_schema_name: str,
    channel_schemas: dict[str, dict[str, str]],
) -> str:
    """Extract the actual data type from notification.params.data path."""

    # Navigate: NotificationSchema -> params field -> NotificationParamsSchema -> data field
    if notification_schema_name not in channel_schemas:
        raise ValueError(f"Notification schema {notification_schema_name} not found in channel_schemas")

    # Get the params field type from NotificationSchema
    notification_fields = channel_schemas[notification_schema_name]
    params_type = notification_fields.get("params", "")

    if (params_type := notification_fields.get("params")) not in channel_schemas:
        raise ValueError(f"Params type {params_type} not found in channel_schemas")

    # Get the data field type from NotificationParamsSchema
    params_fields = channel_schemas[params_type]
    data_type = params_fields.get("data", "")

    if not data_type:  # TODO: should never occur
        return "Any"

    return data_type


def get_param_type_annotation(
    param_name: str, params_schema_name: str, channel_schemas: dict[str, dict[str, str]], channel_enums: set[str]
) -> tuple[str, bool]:
    """Get the type annotation for a channel parameter from the generated schema.

    Returns:
        tuple: (type_annotation, is_enum)
    """

    # Check if we have a schema for the params
    if params_schema_name in channel_schemas:
        param_fields = channel_schemas[params_schema_name]
        if param_name in param_fields:
            type_str = param_fields[param_name]

            # Extract all type names from the annotation (handles Optional, Union, etc.)
            type_names = extract_schema_names_from_type(type_str)

            # Check if any of the types is an enum
            for type_name in type_names:
                if type_name in channel_enums:
                    # Return the actual type annotation with the enum
                    return type_str, True

            # Not an enum
            return type_str, False

    # Fallback to str for unknown types
    return "str", False


def collect_all_channel_imports(
    params_type: str,
    notification_type: str,
    params: list[ParamInfo],
    notification_data_type: str,
    channel_schemas: dict[str, dict[str, str]],
    channel_enums: set[str],
) -> set[str]:
    """Collect all necessary imports for a channel, including nested types."""

    imports = set()

    # Add the main schemas
    if params_type != "dict":
        imports.add(params_type)

    if notification_type != "dict":
        imports.add(notification_type)

    # Add the notification params schema (intermediate type)
    if notification_type in channel_schemas:
        params_field = channel_schemas[notification_type].get("params", "")
        if params_field and params_field != "dict":
            imports.add(params_field)

    # Add the actual data type from notification
    if notification_data_type != "Any":
        imports.update(extract_schema_names_from_type(notification_data_type))

    # Add enum types from parameters
    for param in params:
        param_types = extract_schema_names_from_type(param.type_annotation)
        # Add all extracted types (this includes enums)
        imports.update(param_types)

    return imports


def parse_channel_schemas(channels_dir: Path, channel_schemas: dict[str, dict[str, str]], channel_enums: set[str]):
    """Parse all channel JSON schemas."""

    public_channels = []
    private_channels = []
    schema_imports = set()

    for schema_file in sorted(channels_dir.glob("channel.*.json")):
        filename = schema_file.name

        if filename in {"subscribe.json", "unsubscribe.json"}:
            continue

        channel_name, param_names = parse_channel_name(filename)
        method_name = to_python_method_name(channel_name)

        channel_pattern = channel_name
        for param in param_names:
            channel_pattern = channel_pattern.replace(param, f"{{{param}}}")

        schema_data = json.loads(schema_file.read_text())
        params_type, notification_type = extract_schema_types(schema_data)

        # Build params list with proper type annotations
        params = []
        for param_name in param_names:
            type_annotation, is_enum = get_param_type_annotation(
                param_name,
                params_type,
                channel_schemas,
                channel_enums,
            )
            params.append(ParamInfo(name=param_name, type_annotation=type_annotation, is_enum=is_enum))

        # Get the actual notification data type
        notification_data_type = get_notification_data_type(notification_type, channel_schemas)

        # Collect all imports for this channel
        channel_imports = collect_all_channel_imports(
            params_type,
            notification_type,
            params,
            notification_data_type,
            channel_schemas,
            channel_enums,
        )
        schema_imports.update(channel_imports)

        description = schema_data.get("description", "")

        channel = ChannelInfo(
            name=method_name,
            channel_pattern=channel_pattern,
            params_type=params_type,
            notification_type=notification_type,
            notification_data_type=notification_data_type,
            description=description,
            params=params,
        )

        if channel_name in PUBLIC_CHANNELS:
            public_channels.append(channel)
        elif channel_name in PRIVATE_CHANNELS:
            private_channels.append(channel)
        else:
            print(f"⚠️  Unknown channel classification: {channel_name}")
            private_channels.append(channel)

    return public_channels, private_channels, schema_imports


# ============================================================================
# v3: AsyncAPI-spec-driven parsing, replacing the CHANNELS_DIR/openapi-derived
# equivalents above for WS-only RPC methods and pub/sub channels. The
# functions above are kept only as reference during the transition; remove
# once the AsyncAPI path is confirmed against a real generation run and
# specs/channels/ is deleted.
# ============================================================================

# Channels handled natively by session.py's subscribe()/unsubscribe(), not
# generated as per-method RPC wrappers.
SKIP_RPC_CHANNELS = {"subscribe", "unsubscribe"}

CHANNEL_NAME_RE = re.compile(r"Channel name: `([^`]+)`\.")

# No structured parameter typing exists in either AsyncAPI spec (channel
# addresses are templated in prose, not AsyncAPI's `parameters` object) —
# carried forward from the same implicit table the old per-file parser
# relied on, cross-checked against the current, hand-verified api.py method
# signatures rather than re-guessed.
#
# group/depth/interval are NOT string enums, despite the old api.py importing
# Group/Depth/Interval classes for them — those classes don't exist anywhere
# in subscriptions.asyncapi.json's schemas (confirmed: absent), so that was
# already stale before this migration. The real valid values are documented
# directly in the orderbook/tickerSlim channel descriptions:
#   "{group} is the price-level aggregation size (1, 10, or 100)"
#   "{depth} is the number of levels returned per side (1, 10, 20, or 100)"
#   "{interval} is the update cadence in milliseconds (100 or 1000)"
# Literal[...] matches this exactly and needs no import (api_py.jinja already
# imports Literal unconditionally).
CHANNEL_PARAM_TYPES: dict[str, tuple[str, bool]] = {
    # name: (type_annotation, is_enum)
    "wallet": ("str", False),
    "subaccount_id": ("str", False),
    "instrument_name": ("str", False),
    "instrument_type": ("AssetType", True),
    "currency": ("str", False),
    "group": ("Literal[1, 10, 100]", False),
    "depth": ("Literal[1, 10, 20, 100]", False),
    "interval": ("Literal[100, 1000]", False),
    "tx_status": ("TxStatus", True),
}


def _resolve_ref_name(node: dict) -> Optional[str]:
    ref = node.get("$ref")
    if isinstance(ref, str):
        return ref.rsplit("/", 1)[-1]
    return None


def parse_websocket_only_rpc(ws_asyncapi_path: Path, schema_index: dict[str, dict]):
    """
    Parse websocket.asyncapi.json for WS-only RPC methods (login,
    set_cancel_on_disconnect, and anything else Derive adds here later) —
    methods that exist only over the WebSocket transport and never appear in
    openapi-spec.json, so parse_openapi_for_rpc() never sees them.

    Returns (public_methods, private_methods, schema_imports) in the same
    shape as parse_openapi_for_rpc(). Merge the result into the
    websockets/api.py-specific method lists only — REST http/async_http
    generation should not see these.
    """
    spec = json.loads(ws_asyncapi_path.read_text())
    channels = spec.get("channels", {})
    messages = spec.get("components", {}).get("messages", {})

    public_methods = []
    private_methods = []
    schema_imports = set()

    for channel_name, channel in channels.items():
        if channel_name in SKIP_RPC_CHANNELS:
            continue

        request_msg = messages.get(f"{channel_name}Request")
        response_msg = messages.get(f"{channel_name}Response")
        if request_msg is None or response_msg is None:
            print(f"  ⚠ {channel_name}: missing Request/Response message, skipping")
            continue

        req_payload = request_msg["payload"]
        method_const = req_payload["properties"]["method"]["const"]
        params_schema = req_payload["properties"].get("params", {})
        request_type = _resolve_ref_name(params_schema) or "EmptyRequest"

        # Response payload is `anyOf: [{result: ...}, {error: ...}]`; pull the result branch.
        resp_payload = response_msg["payload"]
        result_schema = None
        for branch in resp_payload.get("anyOf", []):
            if "result" in branch.get("properties", {}):
                result_schema = branch["properties"]["result"]
                break

        if result_schema is None:
            print(f"  ⚠ {channel_name}: no result branch found in response, defaulting to Any")
            result_type = "Any"
        else:
            result_type = resolve_response_type(result_schema, None, schema_index)

        if "/" not in method_const:
            print(f"  ⚠ {channel_name}: method const '{method_const}' has no public/private prefix, skipping")
            continue
        visibility, name = method_const.split("/", 1)

        method = MethodInfo(
            name=name,
            path=f"/{method_const}",
            request_type=request_type,
            response_type=result_type,
            result_type=result_type,
            description=channel.get("description", ""),
        )

        schema_imports.add(request_type)
        schema_imports.update(extract_schema_names_from_type(result_type))

        if visibility == "public":
            public_methods.append(method)
        elif visibility == "private":
            private_methods.append(method)
        else:
            print(f"  ⚠ {channel_name}: unrecognized visibility '{visibility}', treating as private")
            private_methods.append(method)

    return public_methods, private_methods, schema_imports


def parse_subscriptions_asyncapi_channels(subs_path: Path):
    """
    Parse subscriptions.asyncapi.json for pub/sub channels, replacing
    parse_channel_schemas(CHANNELS_DIR, ...).

    Much shallower than the old per-file pipeline: each channel's
    notification message payload is a direct $ref (or array of $ref) to the
    actual data type — no PubSubSchema -> NotificationSchema ->
    NotificationParamsSchema -> data indirection to walk.

    Returns (public_channels, private_channels, schema_imports). Caller
    decides, per notification_data_type/import name, whether to import it
    from generated_models (if also in openapi-spec.json) or channel_models
    (if only in this spec) — same schema_imports bookkeeping already used
    downstream for that.
    """
    spec = json.loads(subs_path.read_text())
    channels = spec.get("channels", {})
    messages = spec.get("components", {}).get("messages", {})

    public_channels = []
    private_channels = []
    schema_imports = set()

    for channel_key, channel in channels.items():
        description = channel.get("description", "")

        match = CHANNEL_NAME_RE.search(description)
        if not match:
            print(f"  ⚠ {channel_key}: no 'Channel name: `...`.' pattern in description, skipping")
            continue
        channel_pattern = match.group(1)  # e.g. "{subaccount_id}.trades.{tx_status}"

        param_names = re.findall(r"\{(\w+)\}", channel_pattern)
        raw_channel_name = re.sub(r"\{(\w+)\}", r"\1", channel_pattern)  # for method-name derivation
        method_name = to_python_method_name(raw_channel_name)

        params = []
        for pname in param_names:
            type_annotation, is_enum = CHANNEL_PARAM_TYPES.get(pname, ("str", False))
            if pname not in CHANNEL_PARAM_TYPES:
                print(f"  ⚠ {channel_key}: no known type for param '{pname}', defaulting to str — verify")
            params.append(ParamInfo(name=pname, type_annotation=type_annotation, is_enum=is_enum))

        # Notification message: the one message on this channel that isn't
        # subscribeRequest/unsubscribeRequest.
        notification_msg = None
        for msg_key, msg_ref in channel.get("messages", {}).items():
            if msg_key in ("subscribeRequest", "unsubscribeRequest"):
                continue
            ref_name = _resolve_ref_name(msg_ref)
            notification_msg = messages.get(ref_name) if ref_name else None
            break
        if notification_msg is None:
            print(f"  ⚠ {channel_key}: no notification message found, skipping")
            continue

        payload = notification_msg["payload"]
        # The spec never expresses "pushed as an array" structurally (payload
        # is always a bare $ref, even for array-pushed channels) — it's only
        # signaled via this summary convention. Verified against all 15
        # channels: 12 say "Pushed as a JSON array", 3 (orderbook, spot_feed,
        # ticker_slim — snapshot-style channels) don't and push a single object.
        is_array = "JSON array" in notification_msg.get("summary", "")
        if payload.get("type") == "array":
            # Defensive: handle it structurally too, in case a future spec
            # revision starts expressing this properly instead of via prose.
            item_ref = _resolve_ref_name(payload.get("items", {})) or "Any"
            notification_data_type = f"list[{item_ref}]"
            notification_import = item_ref
        else:
            ref_name = _resolve_ref_name(payload) or "Any"
            notification_import = ref_name
            notification_data_type = f"list[{ref_name}]" if is_array and ref_name != "Any" else ref_name

        if notification_import != "Any":
            schema_imports.add(notification_import)
        for p in params:
            if p.is_enum:
                schema_imports.add(p.type_annotation)

        channel_info = ChannelInfo(
            name=method_name,
            channel_pattern=channel_pattern,
            params_type="dict",  # no structured params schema in this spec; kept for dataclass compat
            notification_type=notification_data_type,
            notification_data_type=notification_data_type,
            description=description,
            params=params,
        )

        if "Private channel" in description:
            private_channels.append(channel_info)
        elif "Public channel" in description:
            public_channels.append(channel_info)
        else:
            print(f"  ⚠ {channel_key}: description doesn't say Public/Private channel, defaulting to private")
            private_channels.append(channel_info)

    return public_channels, private_channels, schema_imports


def format_docstring(text: str, width: int = 88) -> str:
    """Format text as a proper Python docstring."""

    if not text:
        return ""

    text = text.replace("<br />", "\n").replace("<br/>", "\n")
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

    wrapped = []
    for para in paragraphs:
        wrapped.extend(textwrap.wrap(para, width=width - 8))
        wrapped.append("")

    if wrapped and not wrapped[-1]:
        wrapped.pop()

    return "\n        ".join(wrapped)


def generate_api_file(
    template_name: str,
    output_path: Path,
    public_methods: list[MethodInfo],
    private_methods: list[MethodInfo],
    rpc_schema_imports: set[str],
    is_async: bool = False,
    api_prefix: str = "",
    client_type: str = "http",
    public_channels: list[ChannelInfo] = None,
    private_channels: list[ChannelInfo] = None,
    channel_schema_imports: set[str] = None,
    rpc_import_aliases: dict[str, str] = None,
    channel_import_aliases: dict[str, str] = None,
):
    """Generate a single API file from unified template."""

    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    env.filters['format_docstring'] = format_docstring

    template = env.get_template(template_name)

    output = template.render(
        public_rpc_methods=public_methods,
        private_rpc_methods=private_methods,
        rpc_schema_imports=sorted(rpc_schema_imports),
        is_async=is_async,
        api_prefix=api_prefix,
        client_type=client_type,
        public_channels=public_channels or [],
        private_channels=private_channels or [],
        channel_schema_imports=sorted(channel_schema_imports or set()),
        rpc_import_aliases=rpc_import_aliases or {},
        channel_import_aliases=channel_import_aliases or {},
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output)


def apply_type_aliases(type_str: str, aliases: dict[str, str]) -> str:
    """Apply import aliases to type annotations.

    For example, if type_str is "List[AuctionResultSchema]" and
    aliases is {"AuctionResultSchema": "AuctionResultSchemaRPC"},
    returns "List[AuctionResultSchemaRPC]"
    """
    if not aliases:
        return type_str

    result = type_str
    # Sort by length descending to handle longer names first
    for original, aliased in sorted(aliases.items(), key=lambda x: len(x[0]), reverse=True):
        # Use word boundaries to avoid partial replacements
        result = re.sub(rf'\b{re.escape(original)}\b', aliased, result)

    return result


def generate_all_files():
    """Generate all API files (REST and WebSocket) from unified template."""

    # Parse generated models
    print("Parsing generated_models.py...")
    if not GENERATED_MODELS_PATH.exists():
        raise FileNotFoundError(f"Generated models not found at {GENERATED_MODELS_PATH}")

    source_code = GENERATED_MODELS_PATH.read_text()
    tree = cst.parse_module(source_code)
    parser = ResponseSchemaParser()
    tree.visit(parser)
    print(f"  → Found {len(parser.class_fields)} classes")

    # Parse OpenAPI spec
    print("\nParsing OpenAPI spec...")
    public_methods, private_methods, rpc_schema_imports = parse_openapi_for_rpc(OPENAPI_SPEC, parser)
    print(f"  → {len(public_methods)} public methods")
    print(f"  → {len(private_methods)} private methods")
    print(f"  → {len(rpc_schema_imports)} RPC schema imports")

    # Generate REST endpoints
    print("\nGenerating endpoints.py...")
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    template = env.get_template("endpoints.py.jinja")
    output = template.render(
        public_methods=public_methods,
        private_methods=private_methods,
    )
    endpoints_path = OUTPUT_DIR / "rest" / "endpoints.py"
    endpoints_path.write_text(output)
    print(f"  → {endpoints_path}")

    # Generate REST HTTP API (sync)
    print("\nGenerating rest/http/api.py...")
    generate_api_file(
        template_name="api.py.jinja",
        output_path=OUTPUT_DIR / "rest" / "http" / "api.py",
        public_methods=public_methods,
        private_methods=private_methods,
        rpc_schema_imports=rpc_schema_imports,
        is_async=False,
        api_prefix="",
        client_type="http",
    )

    # Generate REST HTTP API (async)
    print("Generating rest/async_http/api.py...")
    generate_api_file(
        template_name="api.py.jinja",
        output_path=OUTPUT_DIR / "rest" / "async_http" / "api.py",
        public_methods=public_methods,
        private_methods=private_methods,
        rpc_schema_imports=rpc_schema_imports,
        is_async=True,
        api_prefix="Async",
        client_type="http",
    )

    # Parse channels + WS-only RPC methods for WebSocket, from the official AsyncAPI specs
    if SUBSCRIPTIONS_ASYNCAPI.exists() and WEBSOCKET_ASYNCAPI.exists():
        print("\nParsing subscriptions.asyncapi.json for channels...")
        public_channels, private_channels, channel_schema_imports = parse_subscriptions_asyncapi_channels(
            SUBSCRIPTIONS_ASYNCAPI
        )
        print(f"  → {len(public_channels)} public channels")
        print(f"  → {len(private_channels)} private channels")
        print(f"  → {len(channel_schema_imports)} channel schema imports")

        print("\nParsing websocket.asyncapi.json for WS-only RPC methods...")
        # Build a schema index across all three specs so resolve_response_type()
        # can look up singleton-enum-as-str cases regardless of which spec a
        # referenced schema actually lives in.
        ws_asyncapi_data = json.loads(WEBSOCKET_ASYNCAPI.read_text())
        subs_asyncapi_data = json.loads(SUBSCRIPTIONS_ASYNCAPI.read_text())
        openapi_data = json.loads(OPENAPI_SPEC.read_text())
        schema_index = {}
        schema_index.update(openapi_data["components"]["schemas"])
        schema_index.update(subs_asyncapi_data.get("components", {}).get("schemas", {}))
        schema_index.update(ws_asyncapi_data.get("components", {}).get("schemas", {}))

        ws_only_public, ws_only_private, ws_only_schema_imports = parse_websocket_only_rpc(
            WEBSOCKET_ASYNCAPI, schema_index
        )
        print(f"  → {len(ws_only_public)} WS-only public methods: {[m.name for m in ws_only_public]}")
        print(f"  → {len(ws_only_private)} WS-only private methods: {[m.name for m in ws_only_private]}")

        # WS-only RPC methods (login, set_cancel_on_disconnect, ...) don't exist
        # over REST — merge them into WEBSOCKET-SPECIFIC method lists only.
        # public_methods/private_methods (REST-derived, used above for
        # endpoints.py and both REST api.py files) are intentionally left
        # untouched.
        ws_public_methods = public_methods + ws_only_public
        ws_private_methods = private_methods + ws_only_private

        # Reclassify every schema name found by the AsyncAPI-driven parsers
        # against rest_schema_names — the actual ground truth for which file
        # (generated_models.py vs channel_models.py) will contain the class,
        # since datamodel-code-generator only produces one copy per REST
        # schema and deduplicate_channel_models() (in generate_models.py)
        # removes any channel_models.py duplicate of it, rewriting references
        # to import from generated_models instead.
        #
        # Previously this bucketing was decided by "which parser found the
        # name" (parse_openapi_for_rpc -> rpc_schema_imports,
        # parse_websocket_only_rpc/parse_subscriptions_asyncapi_channels ->
        # treated as needing their own bucket) rather than by checking
        # rest_schema_names directly. That produced two symmetric bugs:
        #   - REST-overlap names (Order, Trade, SettledTrade, AssetType,
        #     PublicRfq, Depth, Group, Interval) landed in both buckets,
        #     which detect_import_conflicts() then "resolved" by aliasing
        #     both sides — assuming two separate classes exist. Only one
        #     does, post-dedup; the channel_models-aliased import is for a
        #     symbol that was already removed.
        #   - LoginRequest/SetCancelOnDisconnectRequest (genuinely
        #     channel_models-only — confirmed absent from the REST spec)
        #     were dumped into the RPC bucket unconditionally by
        #     parse_websocket_only_rpc(), importing from generated_models
        #     where they were never generated at all.
        # Checking rest_schema_names directly for every name, regardless of
        # which parser found it, fixes both at the source instead of papering
        # over the symptom with more aliasing.
        rest_schema_names = set(openapi_data["components"]["schemas"].keys())

        all_ws_only_names = ws_only_schema_imports | channel_schema_imports
        ws_rpc_schema_imports = rpc_schema_imports | {n for n in all_ws_only_names if n in rest_schema_names}
        channel_schema_imports = {n for n in all_ws_only_names if n not in rest_schema_names}

        # Detect and resolve any *remaining* import conflicts — should be
        # empty now for every case rest_schema_names already resolved; kept
        # as a safety net for genuine ambiguity this reclassification doesn't
        # cover (e.g. a channel-only schema whose name happens to collide
        # with an unrelated REST-only schema name).
        print("\nDetecting import conflicts...")
        rpc_aliases, channel_aliases = detect_import_conflicts(ws_rpc_schema_imports, channel_schema_imports)
        if rpc_aliases:
            print(f"  → Found {len(rpc_aliases)} conflicts: {', '.join(rpc_aliases.keys())}")

            for method in ws_public_methods + ws_private_methods:
                method.result_type = apply_type_aliases(method.result_type, rpc_aliases)
                method.request_type = rpc_aliases.get(method.request_type, method.request_type)

            for channel in public_channels + private_channels:
                channel.notification_data_type = apply_type_aliases(channel.notification_data_type, channel_aliases)

        # Generate WebSocket API
        print("\nGenerating websockets/api.py...")
        generate_api_file(
            template_name="api.py.jinja",
            output_path=OUTPUT_DIR / "websockets" / "api.py",
            public_methods=ws_public_methods,
            private_methods=ws_private_methods,
            rpc_schema_imports=ws_rpc_schema_imports,
            is_async=True,
            api_prefix="",
            client_type="websocket",
            public_channels=public_channels,
            private_channels=private_channels,
            channel_schema_imports=channel_schema_imports,
            rpc_import_aliases=rpc_aliases,
            channel_import_aliases=channel_aliases,
        )
    else:
        missing = [p for p in (SUBSCRIPTIONS_ASYNCAPI, WEBSOCKET_ASYNCAPI) if not p.exists()]
        print(f"\n⚠️  AsyncAPI spec(s) not found: {missing}")
        print("  Skipping WebSocket generation")

    print("\n✓ All API generation complete!")


if __name__ == "__main__":
    if not OPENAPI_SPEC.exists():
        raise FileNotFoundError(f"OpenAPI spec not found at {OPENAPI_SPEC}")

    generate_all_files()
