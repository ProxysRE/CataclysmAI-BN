#!/usr/bin/env python3
"""Rebuild the native patch against the pinned, unmodified BN files."""
import argparse
import difflib
import hashlib
import re
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--bn-source", type=Path,
                    help="Pinned BN checkout; restore staging before rebuilding")
args = parser.parse_args()
if args.bn_source:
    actual = subprocess.check_output(["git", "-C", str(args.bn_source), "rev-parse", "HEAD"], text=True).strip()
    if actual != "c621aaf42fa182473aad10feea2b55647704dcf1":
        raise ValueError("BN source is not the pinned base")
    for name in ("condition.cpp", "npctalk.cpp"):
        relative = Path("src") / name
        for directory in ("pinned", "engine_staging"):
            target = root / directory / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            # Read the pinned commit, never a possibly modified working tree.
            content = subprocess.check_output(["git", "-C", str(args.bn_source), "show", "HEAD:" + relative.as_posix()])
            target.write_bytes(content)
    for directory in ("src", "tests"):
        target = root / "engine_staging" / directory
        target.mkdir(parents=True, exist_ok=True)
    for name in ("artisan_expression.h", "artisan_bn_bridge.h", "artisan_items.h"):
        (root / "engine_staging/src" / name).unlink(missing_ok=True)
    (root / "engine_staging/tests/dda_artisan_dialogue_test.cpp").unlink(missing_ok=True)
    subprocess.run(["git", "apply", "--directory=engine_staging", str(root / "artisan_engine.patch")], cwd=root, check=True)
parts = []
for name in ("condition.cpp", "npctalk.cpp"):
    path = "src/" + name
    old = (root / "pinned" / path).read_text().splitlines(keepends=True)
    new = (root / "engine_staging" / path).read_text().splitlines(keepends=True)
    parts.extend(difflib.unified_diff(old, new, "a/" + path, "b/" + path))
for name in ("artisan_expression.h", "artisan_bn_bridge.h", "artisan_items.h",
             "dda_artisan_dialogue_test.cpp"):
    path = ("tests/" if name.endswith("_test.cpp") else "src/") + name
    new = (root / "native" / name).read_text().splitlines(keepends=True)
    parts.extend(difflib.unified_diff([], new, "/dev/null", "b/" + path))
payload = "".join(parts).encode()
(root / "artisan_engine.patch").write_bytes(payload)
digest = hashlib.sha256(payload).hexdigest()
workflow = root / "build-dda-npc-engine.yml"
text = workflow.read_text()
text, replacements = re.subn(r'(Get-FileHash \$patch -Algorithm SHA256\)\.Hash\.ToLower\(\) -ne ")[a-f0-9]{64}',
                            lambda match: match[1] + digest, text)
assert replacements == 1, "Expected exactly one native patch checksum"
text = text.replace('"src/artisan_bn_bridge.h", "tests/',
                    '"src/artisan_bn_bridge.h", "src/artisan_items.h", "tests/')
workflow.write_text(text)
print(digest)
