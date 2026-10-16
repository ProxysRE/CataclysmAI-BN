#!/usr/bin/env python3
"""Ensure the recorded successful native checkpoint matches current artifacts."""
import hashlib
import json
from pathlib import Path
root=Path(__file__).resolve().parent
record=json.loads((root/'lighthouse/VALIDATION.json').read_text())
for relative,key in [('artisan_engine.patch','native_patch_sha256'),('native/dda_lighthouse_community.json','native_community_sha256')]:
    actual=hashlib.sha256((root/relative).read_bytes()).hexdigest()
    if actual!=record[key]:
        raise SystemExit(f'{relative} changed since validated run; native validation must be repeated')
print(f"PASS: artifacts match successful run {record['checkpoint']['run_id']}; full campaign release remains pending")
