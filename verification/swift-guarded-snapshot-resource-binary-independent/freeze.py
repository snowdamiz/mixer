"""Seal own review directory; verification is read-only."""
import hashlib
import json
from pathlib import Path
import sys

D = Path(__file__).resolve().parent


def main():
    rows = []
    for p in sorted(D.rglob('*')):
        assert not p.is_symlink()
        assert '__pycache__' not in p.parts
        if p.is_file() and p != D / 'seal.json':
            data = p.read_bytes()
            rows.append(dict(path=str(p.relative_to(D)), bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
    result = dict(schema=1, member_count=len(rows), total_bytes=sum(r['bytes'] for r in rows),
                  members=rows,
                  scope='Independent bounded frozen resource binary correspondence; helper findings preserved; no whole caller/runtime/GA acceptance')
    if '--verify' in sys.argv:
        assert json.loads((D / 'seal.json').read_bytes()) == result
    else:
        assert not (D / 'seal.json').exists()
        (D / 'seal.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    print(json.dumps(dict(status='passed', seal_sha256=hashlib.sha256((D / 'seal.json').read_bytes()).hexdigest(),
                          members=len(rows), bytes=result['total_bytes'])))


if __name__ == '__main__':
    main()
