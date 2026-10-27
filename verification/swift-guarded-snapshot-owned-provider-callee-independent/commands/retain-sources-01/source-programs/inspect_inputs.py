import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
C = ROOT / 'verification/swift-guarded-snapshot-owned-provider-callee-interfaces'

def main():
    mode = sys.argv[1]
    if mode == 'nodes':
        d = json.loads((C / 'source-ledger.json').read_text())
        for n in d['nodes']:
            print('\nNODE', n['id'], 'CALLS', n['calls'], 'SAFE', n['safe_context'])
            path = C / n['source']
            if not path.is_file():
                path = ROOT / n['source']
            body = path.read_bytes()
            print('SOURCE', str(path.relative_to(ROOT)), hashlib.sha256(body).hexdigest())
            print(''.join(f'{i}:{line}' for i, line in enumerate(body.decode().splitlines(keepends=True), 1) if n['first'] <= i <= n['last']), end='')
            print('ROLES', [(r['id'], r['type'], r['bytes'], r['align'], r['leaves'], r['pointee'], r['body']) for r in n['roles']])
            for r in n['rows']:
                print('ROW', r['line'], r['code'], r['mentions'], r['constants'], 'LOOP', r['body_iterations'])
        print('TYPES', json.dumps(d['types'], indent=2))
    elif mode == 'contracts':
        for name in ['model.py', 'phase-reservations.json', 'final-validation.json', 'analysis.json', 'root-contract.json']:
            print('\nFILE', name)
            print((C / name).read_text())
    elif mode == 'inherited':
        for packet in ['swift-guarded-snapshot-owned-provider-work-storage', 'swift-guarded-snapshot-owned-provider-work-storage-independent']:
            p = ROOT / 'verification' / packet
            for name in ['README.md', 'proposal.json', 'review.json']:
                if (p / name).is_file():
                    print('\nFILE', str((p/name).relative_to(ROOT)))
                    print((p / name).read_text())
    elif mode == 'compiler':
        d = json.loads((C / 'LLVM-correspondence.json').read_text())
        print(json.dumps(d, indent=2))
        print((C / 'native-ABI-boundaries.json').read_text())
    else:
        raise ValueError(mode)

if __name__ == '__main__':
    main()
