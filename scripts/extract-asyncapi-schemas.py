from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
import paths  # noqa: E402
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
    for p in (paths.OPENAPI_SPEC_PATCHED, paths.SUBSCRIPTIONS_ASYNCAPI, paths.WEBSOCKET_ASYNCAPI):
        if not p.exists():
            print(f"Error: {p} not found", file=sys.stderr)
            if p == paths.OPENAPI_SPEC_PATCHED:
                print("  (run `make generate-models`'s patch_spec.py step first)", file=sys.stderr)
            raise SystemExit(1)

    openapi_spec = load(paths.OPENAPI_SPEC_PATCHED)
    subs_spec = load(paths.SUBSCRIPTIONS_ASYNCAPI)
    ws_spec = load(paths.WEBSOCKET_ASYNCAPI)

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
        "description": "Extracted from subscriptions.json and websocket.json (v3).",
        "definitions": definitions,
    }

    paths.WEBSOCKET_CHANNELS.parent.mkdir(parents=True, exist_ok=True)
    paths.WEBSOCKET_CHANNELS.write_text(json.dumps(merged, indent=2))
    print(f"\n✓ Written to {paths.WEBSOCKET_CHANNELS}", file=sys.stderr)


if __name__ == "__main__":
    main()
