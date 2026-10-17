#!/usr/bin/env python3
"""Reproduce the Windows cp1252 failure while preserving actual UTF-8 map bytes."""
from pathlib import Path
from unittest.mock import patch

from prepare_location_expansion import ROOT, prepare
from prepare_community_layers import ROOT as LAYERS, read_bundle


def check():
    original = Path.write_text

    def windows_write(path, data, encoding=None, errors=None, newline=None):
        return original(path, data, encoding=encoding or 'cp1252', errors=errors, newline=newline)

    with patch.object(Path, 'write_text', windows_write):
        result = prepare()
    files = read_bundle(LAYERS)
    for name in result['hub']['candidate_source_files']:
        output = ROOT / 'hub_candidate' / Path(name).name
        assert output.read_bytes() == files['dda/' + name].encode('utf-8')
    print('PASS: Hub source maps retain exact UTF-8 bytes under emulated Windows cp1252 defaults')


if __name__ == '__main__':
    check()
