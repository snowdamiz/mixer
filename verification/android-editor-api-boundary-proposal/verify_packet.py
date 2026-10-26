#!/usr/bin/env python3
"""Read-only verification of this exact proposal packet; does not execute it."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent


def main():
    manifest_path = HERE / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    actual_paths = {str(p.relative_to(HERE)) for p in HERE.rglob('*') if p.is_file() and p != manifest_path}
    assert actual_paths == set(manifest['files']), 'packet path roster changed'
    total = 0
    for relative, expected in manifest['files'].items():
        path = HERE / relative
        assert not path.is_symlink() and path.resolve().is_relative_to(HERE), relative
        data = path.read_bytes()
        assert {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()} == expected, relative
        total += len(data)
    print(json.dumps({'scope': 'Exact bytes only; no implementation/platform authority',
                      'manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                      'members_verified': len(actual_paths), 'bytes': total}, indent=2))


if __name__ == '__main__':
    main()
