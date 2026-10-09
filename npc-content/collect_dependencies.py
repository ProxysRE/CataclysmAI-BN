#!/usr/bin/env python3
"""Preserve transitive DDA definition candidates absent from BN.

The index is intentionally conservative: matching strings are candidates, not
proof of references. Same-named BN definitions still require semantic review.
"""
import argparse
import base64
import collections
import gzip
import hashlib
import json
from pathlib import Path


def identifiers(entry):
    value = entry.get("id", entry.get("abstract", entry.get("nested_mapgen_id",
                      entry.get("update_mapgen_id", []))))
    return [value] if isinstance(value, str) else value if isinstance(value, list) else []


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, entry in value.items():
            if key not in {"//", "description", "dynamic_line", "text", "name", "name_unique"}:
                yield from strings(entry)
    elif isinstance(value, list):
        for entry in value:
            yield from strings(entry)


def index(root):
    result = collections.defaultdict(list)
    for path in sorted(root.rglob("*.json")):
        try:
            entries = json.loads(path.read_text())
        except (ValueError, UnicodeError):
            continue
        if not isinstance(entries, list):
            continue
        for position, entry in enumerate(entries):
            if not isinstance(entry, dict):
                continue
            for identifier in identifiers(entry):
                result[identifier].append((str(path.relative_to(root)), position, entry))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dda-json", type=Path, required=True)
    parser.add_argument("--bn-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    source = json.loads(gzip.decompress(base64.b64decode(
        (root / "isolated_road_source.json.gz.base64").read_text())))
    dda, bn = index(args.dda_json), index(args.bn_json)
    own = {identifier for entries in source.values() for entry in entries for identifier in identifiers(entry)}
    pending = collections.deque({value for entries in source.values() for value in strings(entries)})
    visited, selected, overlaps = set(), {}, set()
    while pending:
        identifier = pending.popleft()
        if identifier in visited:
            continue
        visited.add(identifier)
        if identifier in own:
            continue
        if identifier in bn:
            if identifier in dda:
                overlaps.add(identifier)
            continue
        for filename, position, entry in dda.get(identifier, []):
            key = (filename, position)
            if key not in selected:
                selected[key] = entry
                pending.extend(strings(entry))
    files = collections.defaultdict(list)
    for (filename, position), entry in sorted(selected.items()):
        files[filename].append(entry)
    raw = json.dumps(files, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "dependencies.json.gz.base64").write_text(
        base64.b64encode(gzip.compress(raw, mtime=0)).decode() + "\n")
    report = {"definitions": len(selected), "files": len(files),
              "types": dict(collections.Counter(entry.get("type") for entry in selected.values())),
              "payload_sha256": hashlib.sha256(raw).hexdigest(),
              "existing_BN_candidates_for_semantic_review": sorted(overlaps),
              "candidate_ids": sorted({i for e in selected.values() for i in identifiers(e)}),
              "warning": "Conservative source closure only; not runtime validated or ready to install."}
    (args.output / "DEPENDENCIES.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"Preserved {len(selected)} candidate definitions from {len(files)} files")


if __name__ == "__main__":
    main()
