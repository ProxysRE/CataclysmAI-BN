#!/usr/bin/env python3
"""Extract the preserved DDA package and prepare BN map data for review.

This produces a staging directory, not an installable mod. Dialogue and
dependency closure must pass native BN loading before release.
"""
import argparse
import base64
import copy
import gzip
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / "SOURCE_MANIFEST.json").read_text())
    raw = gzip.decompress(base64.b64decode(
        (root / "isolated_road_source.json.gz.base64").read_text()))
    if hashlib.sha256(raw).hexdigest() != manifest["source_payload_sha256"]:
        raise SystemExit("Source payload checksum mismatch")
    files = json.loads(raw)
    for name, entries in files.items():
        original = args.output / "upstream" / name
        original.parent.mkdir(parents=True, exist_ok=True)
        original.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n")
        if not name.startswith(("mapgen/", "overmap/")):
            continue
        adapted = []
        for entry in entries:
            entry = copy.deepcopy(entry)
            if entry.get("type") == "mapgen":
                entry["method"] = "json"
            if entry.get("type") == "overmap_terrain":
                entry.pop("vision_levels", None)
                if isinstance(entry.get("see_cost"), str):
                    entry["see_cost"] = {"none": 0, "high": 5}[entry["see_cost"]]
                identifiers = entry.get("id")
                if isinstance(identifiers, list):
                    for identifier in identifiers:
                        variant = copy.deepcopy(entry)
                        variant["id"] = identifier
                        adapted.append(variant)
                    continue
            adapted.append(entry)
        target = args.output / "bn_staging" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(adapted, ensure_ascii=False, indent=2) + "\n")
    print(f"Extracted {len(files)} source files; BN map data staged, not release-ready")


if __name__ == "__main__":
    main()
