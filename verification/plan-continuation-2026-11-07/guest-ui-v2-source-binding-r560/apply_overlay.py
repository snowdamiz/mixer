"""Apply this exact packet only after every target preimage matches; root runs it."""
from pathlib import Path
import argparse
import hashlib
import json

OUT = Path(__file__).resolve().parent

def identity(path):
    data = path.read_bytes()
    return {'bytes':len(data), 'sha256':hashlib.sha256(data).hexdigest()}

def apply(target):
    target = Path(target).resolve(strict=True)
    rows = json.loads((OUT/'application-map.json').read_text())
    prepared = []
    for row in rows:
        rel = Path(row['path'])
        if rel.is_absolute() or '..' in rel.parts:
            raise RuntimeError('Invalid selected path')
        path = target/rel
        if any(p.is_symlink() for p in [path, *path.parents] if p != target.parent):
            raise RuntimeError('Symlink in selected path: '+str(rel))
        observed = identity(path) if path.exists() else None
        if observed != row['before']:
            raise RuntimeError('Preimage differs; no writes performed: '+str(rel))
        after = OUT/row['afterimage']
        if identity(after) != row['after']:
            raise RuntimeError('Packet afterimage differs; no writes performed: '+str(rel))
        prepared.append((path, after.read_bytes()))
    for path, data in prepared:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return len(prepared)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps({'applied':apply(args.target)}))
