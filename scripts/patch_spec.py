#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from typing import Any, Tuple

TARGET_TITLE = "erc20_details"
ANYOF_PAYLOAD = [{"type": "string"}, {"type": "integer"}]


def patch_node(node: Any) -> Tuple[Any, int]:
    """
    Recursively patch:
      additionalProperties: { title: "erc20_details", type: "string", ... }
    -> additionalProperties: { title: "erc20_details", anyOf: [...], ... }
    Returns (possibly-modified node, patches_applied)
    """
    changed = 0

    if isinstance(node, dict):
        # Patch additionalProperties blocks with the target title
        ap = node.get("additionalProperties")
        if (
            isinstance(ap, dict)
            and ap.get("title") == TARGET_TITLE
            and (ap.get("type") == "string" or "anyOf" not in ap)
        ):
            ap.pop("type", None)
            ap["anyOf"] = ANYOF_PAYLOAD
            node["additionalProperties"] = ap
            changed += 1

        # Recurse into dict values
        for k, v in list(node.items()):
            new_v, c = patch_node(v)
            if c:
                node[k] = new_v
            changed += c

    elif isinstance(node, list):
        for i, item in enumerate(list(node)):
            new_item, c = patch_node(item)
            if c:
                node[i] = new_item
            changed += c

    return node, changed


def is_split_enum(schema: Any) -> bool:
    """
    True if `schema` is a `oneOf` whose every branch is a bare
    `type: string, enum: [...]`, i.e. the spec author split one flat
    enum into several branches purely to attach a per-value description,
    not to express a real discriminated union.

    datamodel-code-generator treats each branch as a distinct type and
    unions them; msgspec then refuses to decode the union, since a
    tagged union may contain at most one str-enum member. Collapsing
    these back into a single enum before codegen avoids the issue
    entirely, rather than patching the generated Python after the fact.
    """
    if not isinstance(schema, dict):
        return False
    branches = schema.get("oneOf")
    if not isinstance(branches, list) or not branches:
        return False
    return all(isinstance(b, dict) and b.get("type") == "string" and isinstance(b.get("enum"), list) for b in branches)


def collapse_split_enum(schema: dict) -> dict:
    """Merge a split-enum `oneOf` schema into one flat `type: string, enum: [...]`."""
    branches = schema["oneOf"]

    values: list[str] = []
    value_docs: list[str] = []
    for branch in branches:
        for v in branch["enum"]:
            values.append(v)
            desc = branch.get("description")
            if desc:
                value_docs.append(f"- `{v}`: {desc}")

    merged: dict[str, Any] = {"type": "string", "enum": values}

    doc_lines = []
    if schema.get("description"):
        doc_lines.append(schema["description"])
    doc_lines.extend(value_docs)
    if doc_lines:
        merged["description"] = "\n".join(doc_lines)

    return merged


def patch_split_enums(node: Any) -> Tuple[Any, int]:
    """Recursively collapse split-enum `oneOf` schemas anywhere in the document."""
    changed = 0

    if isinstance(node, dict):
        if is_split_enum(node):
            return collapse_split_enum(node), 1

        for k, v in list(node.items()):
            new_v, c = patch_split_enums(v)
            if c:
                node[k] = new_v
            changed += c

    elif isinstance(node, list):
        for i, item in enumerate(list(node)):
            new_item, c = patch_split_enums(item)
            if c:
                node[i] = new_item
            changed += c

    return node, changed


def main():
    p = argparse.ArgumentParser(description="Patch openapi-spec.json (erc20_details, split-enum oneOf) before codegen.")
    p.add_argument("json_path", type=Path, help="Path to openapi-spec.json")
    p.add_argument(
        "-o",
        "--out",
        type=Path,
        help="Output path (default: <name>.patched.json next to input — original spec is never modified)",
    )
    args = p.parse_args()

    src = args.json_path
    out = args.out or src.with_name(f"{src.stem}.patched{src.suffix}")

    if not src.exists():
        print(f"Error: {src} not found", file=sys.stderr)
        sys.exit(1)

    with src.open("r", encoding="utf-8") as f:
        data = json.load(f)

    data, erc20_count = patch_node(data)
    data, enum_count = patch_split_enums(data)

    with out.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Patched erc20_details occurrences: {erc20_count}")
    print(f"Collapsed split-enum schemas: {enum_count}")
    print(f"Source spec (untouched): {src}")
    print(f"Patched spec written to: {out}")


if __name__ == "__main__":
    main()
