"""Remove five synthetic EOF blank-line hunks from the checksummed port snapshot."""
import hashlib
import re
import sys
from pathlib import Path

source, target = map(Path, sys.argv[1:])
data = source.read_bytes()
assert hashlib.sha256(data).hexdigest() == 'fc7146670825efae5158d8506db99c6898fbd828c025364d58eff5aa60f6dbc7'
expected = {'src/mapgen/mapgen.cpp', 'src/mapgen/mapgen.h', 'src/overmap/omdata.h',
            'src/overmap/overmap.h', 'src/savegame.cpp'}
removed = set()
blocks = re.split(r'(?=^diff --git )', data.decode('utf-8'), flags=re.M)
result = []
for block in blocks:
    if not block:
        continue
    path = block.splitlines()[0].split(' b/')[1]
    pieces = re.split(r'(?=^@@ )', block, flags=re.M)
    kept = [pieces[0]]
    for hunk in pieces[1:]:
        changes = [line for line in hunk.splitlines()[1:] if line.startswith(('+', '-'))]
        if path in expected and changes == ['-']:
            removed.add(path)
        else:
            kept.append(hunk)
    result.append(''.join(kept))
assert removed == expected, removed
target.write_bytes(''.join(result).encode('utf-8'))
print('Removed five EOF-only blank-line hunks; all functional changes preserved')
