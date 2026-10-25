"""Seal only the bounded independent review lane; root overlays are excluded."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DOC = ROOT/'docs/swift-ordered-retention-diagnostic-design-review.md'


def digest(path):
    h = hashlib.sha256()
    total = 0
    with path.open('rb') as stream:
        while block := stream.read(65536):
            h.update(block); total += len(block)
    return dict(bytes=total, sha256=h.hexdigest())


def member_paths():
    return [p for p in HERE.rglob('*') if p.is_file() and p not in {HERE/'seal.json', HERE/'seal.sha256'}
            and not any(part.startswith('root-') for part in p.relative_to(HERE).parts)] + [DOC]


def main():
    members = {}
    for path in sorted(member_paths()):
        if path.is_symlink():
            raise ValueError('symlink member')
        members[str(path.relative_to(ROOT))] = digest(path)
    seal = dict(schema=1, scope='Independent design and finite Python model review only; no Rust/target/native execution',
                disposition='design-only-accepted-with-explicit-unimplemented-gates',
                excluded='seal.json, seal.sha256, any root-* overlay path; no other exclusions',
                baselineNamedClosure='16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd',
                members=members)
    path = HERE/'seal.json'
    path.write_text(json.dumps(seal,indent=2,sort_keys=True)+'\n')
    (HERE/'seal.sha256').write_text(digest(path)['sha256']+'  seal.json\n')
    print(json.dumps(dict(members=len(members),sealSHA256=digest(path)['sha256']),sort_keys=True))


if __name__ == '__main__':
    main()
