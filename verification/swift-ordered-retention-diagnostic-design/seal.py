"""Seal only this owned packet and its one owned document."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DOC = ROOT / 'docs/swift-ordered-retention-diagnostic-design.md'
EXCLUDED = {'seal.json', 'seal.sha256'}


def describe(path):
    data = path.read_bytes()
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def main():
    members = {}
    for path in sorted(HERE.rglob('*')):
        if path.is_symlink():
            raise ValueError('symlink in owned packet')
        if path.is_file() and path.name not in EXCLUDED:
            members[str(path.relative_to(ROOT))] = describe(path)
    members[str(DOC.relative_to(ROOT))] = describe(DOC)
    value = dict(schema=1, disposition='proposal-only-pending-independent-review',
                 scope='finite Python synthetic codec/state evidence; no Rust/target/native execution',
                 baselineNamedClosure='16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd',
                 sourceRevisionContext='d1ca165659c72db17c5573d992002635d569c1f1',
                 members=members)
    data = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    (HERE / 'seal.json').write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    (HERE / 'seal.sha256').write_text(digest + '  seal.json\n')
    print(json.dumps(dict(members=len(members), sealSHA256=digest), sort_keys=True))


if __name__ == '__main__':
    main()
