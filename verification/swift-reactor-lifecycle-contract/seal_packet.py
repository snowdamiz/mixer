#!/usr/bin/env python3
"""Seal saved contract bytes only. This is never a contract-selection action."""
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent

def main():
    assert not (HERE / 'seal.json').exists(), 'preserve the original seal'
    files = {str(path.relative_to(HERE)): hashlib.sha256(path.read_bytes()).hexdigest()
             for path in sorted(HERE.rglob('*')) if path.is_file() and path != HERE / 'seal.json'}
    result = {'schema': 'mixer.swift-lifecycle.contract-seal.1',
              'observedUTC': datetime.now(timezone.utc).isoformat(),
              'selected': False, 'runtime': False, 'files': files}
    (HERE / 'seal.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'sealedFiles': len(files), 'selected': False, 'runtime': False}))

if __name__ == '__main__':
    main()
