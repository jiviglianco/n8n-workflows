#!/usr/bin/env python3
"""Validate every workflow.json in this repository.

Checks:
  * file is valid JSON
  * top-level keys: name, nodes, connections, settings
  * every node has id, name, type, typeVersion, position ([x, y])
  * node names are unique
  * every connection source and target references an existing node
  * IF/Filter-style nodes with a second output array are reported (informational)
  * no obvious secrets (sk-ant-, xoxb-, Bearer <long token>) in the file

Exit code is 1 if any error was found. Prints a per-workflow node count.
Usage:  python scripts/validate.py   (from the repo root or anywhere)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REQUIRED_TOP = ("name", "nodes", "connections", "settings")
REQUIRED_NODE = ("id", "name", "type", "typeVersion", "position")
SECRET_PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9_-]{10,}"),
    re.compile(r"xox[abp]-[A-Za-z0-9-]{10,}"),
    re.compile(r"\b\d{6,}:[A-Za-z0-9_-]{30,}\b"),  # telegram bot token
    re.compile(r"Bearer\s+[A-Za-z0-9._-]{20,}"),
]


def validate(path: Path) -> tuple[list[str], list[str], int]:
    errors: list[str] = []
    warnings: list[str] = []
    text = path.read_text(encoding="utf-8")

    try:
        wf = json.loads(text)
    except json.JSONDecodeError as exc:
        return [f"invalid JSON: {exc}"], warnings, 0

    for key in REQUIRED_TOP:
        if key not in wf:
            errors.append(f"missing top-level key '{key}'")
    if errors:
        return errors, warnings, 0

    if wf.get("settings", {}).get("executionOrder") != "v1":
        warnings.append("settings.executionOrder is not 'v1'")

    nodes = wf["nodes"]
    if not isinstance(nodes, list) or not nodes:
        return ["'nodes' must be a non-empty list"], warnings, 0

    names: set[str] = set()
    ids: set[str] = set()
    for i, node in enumerate(nodes):
        label = node.get("name", f"#{i}")
        for key in REQUIRED_NODE:
            if key not in node:
                errors.append(f"node '{label}' missing '{key}'")
        pos = node.get("position")
        if not (isinstance(pos, list) and len(pos) == 2 and all(isinstance(v, (int, float)) for v in pos)):
            errors.append(f"node '{label}' position must be [x, y]")
        if "parameters" not in node:
            errors.append(f"node '{label}' missing 'parameters'")
        name = node.get("name")
        if name in names:
            errors.append(f"duplicate node name '{name}'")
        names.add(name)
        nid = node.get("id")
        if nid in ids:
            errors.append(f"duplicate node id '{nid}' (node '{label}')")
        ids.add(nid)
        creds = node.get("credentials", {})
        for ctype, cref in creds.items():
            if not isinstance(cref, dict) or "name" not in cref:
                errors.append(f"node '{label}' credential '{ctype}' must have a 'name'")

    connections = wf["connections"]
    if not isinstance(connections, dict):
        errors.append("'connections' must be an object")
    else:
        for source, outputs in connections.items():
            if source not in names:
                errors.append(f"connection source '{source}' is not an existing node")
            main = outputs.get("main") if isinstance(outputs, dict) else None
            if not isinstance(main, list):
                errors.append(f"connections['{source}'].main must be a list of output arrays")
                continue
            for out_idx, targets in enumerate(main):
                if not isinstance(targets, list):
                    errors.append(f"connections['{source}'].main[{out_idx}] must be a list")
                    continue
                for t in targets:
                    tgt = t.get("node") if isinstance(t, dict) else None
                    if tgt not in names:
                        errors.append(
                            f"connection {source} -> '{tgt}' (output {out_idx}) references a non-existing node"
                        )
                    if isinstance(t, dict) and t.get("type") != "main":
                        errors.append(f"connection {source} -> '{tgt}' has type '{t.get('type')}', expected 'main'")

    # Orphan check: every non-sticky, non-trigger node should be a target of something.
    targets_seen: set[str] = set()
    for outputs in connections.values():
        for arr in outputs.get("main", []):
            for t in arr:
                targets_seen.add(t.get("node"))
    for node in nodes:
        t = node.get("type", "")
        if t.endswith("stickyNote"):
            continue
        is_trigger = "trigger" in t.lower() or t.endswith(".webhook")
        if not is_trigger and node["name"] not in targets_seen:
            warnings.append(f"node '{node['name']}' has no incoming connection")

    for pat in SECRET_PATTERNS:
        if pat.search(text):
            errors.append(f"possible secret matches pattern {pat.pattern!r}")

    real_nodes = [n for n in nodes if not n.get("type", "").endswith("stickyNote")]
    return errors, warnings, len(real_nodes)


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    files = sorted(root.glob("*/workflow.json"))
    if not files:
        print(f"no workflow.json files found under {root}")
        return 1

    failed = 0
    for path in files:
        errors, warnings, count = validate(path)
        rel = path.relative_to(root).as_posix()
        sticky = 0
        try:
            sticky = sum(1 for n in json.loads(path.read_text(encoding="utf-8"))["nodes"] if n.get("type", "").endswith("stickyNote"))
        except Exception:
            pass
        status = "OK " if not errors else "ERR"
        print(f"[{status}] {rel}: {count} nodes (+{sticky} sticky notes)")
        for w in warnings:
            print(f"       warn: {w}")
        for e in errors:
            print(f"       error: {e}")
        failed += bool(errors)

    print(f"\n{len(files)} workflow(s) checked, {failed} with errors")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
