"""
Replaces merge-websocket-channels.py.

The old pipeline merged hand-maintained per-channel JSON Schema files from
specs/channels/*.json. Derive now publishes two official AsyncAPI 3.0 specs
(subscriptions.asyncapi.json for pub/sub channels, websocket.asyncapi.json for
WS-only RPC methods like login and set_cancel_on_disconnect) — this script
extracts the equivalent JSON-Schema-shaped bundle from those instead, and
feeds it into the *same* downstream pipeline (generate_models.py's existing
InputFileType.JsonSchema call, then deduplicate_channel_models()).

Approach:
  1. Seed with schema names that are genuinely new (not already produced by
     generated_models.py from the REST spec): every schema in
     subscriptions.asyncapi.json's components.schemas not also present in
     openapi-spec.json, plus LoginRequest/SetCancelOnDisconnectRequest from
     websocket.asyncapi.json.
  2. Transitively follow $ref across all three documents (REST spec included,
     since a subs-only schema may reference a REST-overlap schema like
     Direction or RPCError) and collect full definitions for everything
     reached.
  3. Write one merged {"definitions": {...}} bundle, same shape
     merge-websocket-channels.py produced.

Overlap with generated_models.py (e.g. a subs-only schema referencing
Direction, which is already generated from the REST spec) is intentional,
not a bug to avoid: generate_models.py's existing deduplicate_channel_models()
step is exactly the mechanism designed to reconcile that, same as it already
did for the old per-channel-file pipeline. Don't try to cleverly exclude
REST-overlap refs here — include the full transitive closure and let dedup
do its job downstream.

Deliberately excluded: JsonRpcId, SubscribeParams, SubscribeResult,
UnsubscribeParams, UnsubscribeResult, SetCancelOnDisconnectResponse.
The first five are protocol-envelope types already hand-implemented in
session.py (JSONRPCEnvelope, Subscribe), not per-channel payload types —
same reason the old script excluded subscribe.json/unsubscribe.json.
SetCancelOnDisconnectResponse is a singleton string enum (["ok"]); per the
existing resolve_response_type() convention in generate-api.py, singleton
enums resolve to a plain `str` return type inline rather than being
generated as an importable class, since datamodel-code-generator emits no
usable symbol for a single-value enum anyway.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from patch_spec import patch_split_enums  # noqa: E402

EXCLUDED_SCHEMAS = {
    "JsonRpcId",
    "SubscribeParams",
    "SubscribeResult",
    "UnsubscribeParams",
    "UnsubscribeResult",
    "SetCancelOnDisconnectResponse",
}

WEBSOCKET_ONLY_RPC_SEEDS = {"LoginRequest", "SetCancelOnDisconnectRequest"}


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def find_refs(node: Any) -> set[str]:
    """Recursively collect every '#/components/schemas/X' ref target name in node."""
    refs: set[str] = set()
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
            refs.add(ref.rsplit("/", 1)[-1])
        for v in node.values():
            refs |= find_refs(v)
    elif isinstance(node, list):
        for item in node:
            refs |= find_refs(item)
    return refs


def build_schema_index(*docs: dict) -> dict[str, dict]:
    """Merge components.schemas across multiple spec documents into one lookup.

    Later docs win on name collision; in practice REST/subscriptions/websocket
    specs shouldn't define the same name with different shapes, but this
    makes the precedence explicit rather than accidental dict-merge order.
    """
    index: dict[str, dict] = {}
    for doc in docs:
        index.update(doc.get("components", {}).get("schemas", {}))
    return index


def rewrite_refs(node: Any) -> Any:
    """
    Rewrite '#/components/schemas/X' -> '#/definitions/X' throughout node.

    The extracted schema bodies are copied verbatim from AsyncAPI/OpenAPI
    documents, where $ref points at '#/components/schemas/...'. The output
    document here uses JSON-Schema-draft-07's top-level 'definitions' key
    instead (matching what the old merge-websocket-channels.py produced, and
    what datamodel-code-generator's JsonSchema input mode expects) — without
    this rewrite every $ref would point at a path that doesn't exist in the
    output document at all.
    """
    if isinstance(node, dict):
        if isinstance(node.get("$ref"), str) and node["$ref"].startswith("#/components/schemas/"):
            name = node["$ref"].rsplit("/", 1)[-1]
            return {**node, "$ref": f"#/definitions/{name}"}
        return {k: rewrite_refs(v) for k, v in node.items()}
    if isinstance(node, list):
        return [rewrite_refs(item) for item in node]
    return node


def transitive_closure(seeds: set[str], schema_index: dict[str, dict]) -> dict[str, dict]:
    """BFS outward from seed schema names, following $ref, collecting full definitions."""
    collected: dict[str, dict] = {}
    frontier = set(seeds) - EXCLUDED_SCHEMAS
    while frontier:
        name = frontier.pop()
        if name in collected:
            continue
        schema = schema_index.get(name)
        if schema is None:
            print(f"  ⚠ referenced schema '{name}' not found in any spec — skipping", file=sys.stderr)
            continue
        collected[name] = rewrite_refs(schema)
        for ref_name in find_refs(schema) - EXCLUDED_SCHEMAS:
            if ref_name not in collected:
                frontier.add(ref_name)
    return collected


def main() -> None:
    repo_root = Path(__file__).parent.parent
    specs_dir = repo_root / "specs"

    # patched, not raw: generated_models.py is built from the patched spec
    # (erc20_details fix, split-enum collapse — see patch_spec.py), so any
    # REST-overlap schema pulled in here needs to match byte-for-byte or the
    # downstream deduplicate_channel_models() dedup-by-content-hash step
    # won't recognize it as the same class and will incorrectly keep both.
    raw_openapi = specs_dir / "openapi-spec.json"
    openapi_path = raw_openapi.with_name(f"{raw_openapi.stem}.patched{raw_openapi.suffix}")
    subs_path = specs_dir / "subscriptions.asyncapi.json"
    ws_path = specs_dir / "websocket.asyncapi.json"
    out_path = specs_dir / "websocket-channels.json"

    for p in (openapi_path, subs_path, ws_path):
        if not p.exists():
            print(f"Error: {p} not found", file=sys.stderr)
            if p == openapi_path:
                print("  (run `make generate-models`'s patch_spec.py step first)", file=sys.stderr)
            raise SystemExit(1)

    openapi_spec = load(openapi_path)
    subs_spec = load(subs_path)
    ws_spec = load(ws_path)

    schema_index = build_schema_index(openapi_spec, subs_spec, ws_spec)

    rest_schema_names = set(openapi_spec["components"]["schemas"].keys())
    subs_schema_names = set(subs_spec.get("components", {}).get("schemas", {}).keys())

    seeds = (subs_schema_names - rest_schema_names) | WEBSOCKET_ONLY_RPC_SEEDS
    print(f"Seed schemas ({len(seeds)}): {sorted(seeds)}", file=sys.stderr)

    definitions = transitive_closure(seeds, schema_index)
    print(f"Transitive closure: {len(definitions)} total definitions", file=sys.stderr)
    overlap_pulled_in = sorted(set(definitions) & rest_schema_names)
    if overlap_pulled_in:
        print(
            f"  → {len(overlap_pulled_in)} of these also exist in generated_models.py "
            f"(expected — deduplicate_channel_models() reconciles this): {overlap_pulled_in}",
            file=sys.stderr,
        )

    definitions, collapsed_count = patch_split_enums(definitions)
    if collapsed_count:
        print(f"  → collapsed {collapsed_count} split-enum schema(s) (e.g. TxStatus)", file=sys.stderr)

    merged = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Derive WebSocket Channel Schemas",
        "description": "Extracted from subscriptions.asyncapi.json and websocket.asyncapi.json (v3).",
        "definitions": definitions,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(merged, indent=2))
    print(f"\n✓ Written to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
