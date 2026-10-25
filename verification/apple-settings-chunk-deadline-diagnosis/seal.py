"""Seal only this bounded diagnosis lane; no native selection authority."""
import datetime
import hashlib
import json
import pathlib
import stat

BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[1]


def row(path):
    assert path.resolve() == path and path.is_file() and not path.is_symlink()
    raw = path.read_bytes()
    return {'kind': 'file', 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'mode': stat.S_IMODE(path.stat().st_mode)}


def main():
    assert not (BASE / 'owned-host-scratch').exists()
    receipt = json.loads((BASE / 'receipt.json').read_bytes())
    assert receipt['implementationSelected'] is False and receipt['nativeAccepted'] is False
    assert json.loads((BASE / 'host-command-receipt.json').read_bytes())['passed'] is True
    assert json.loads((BASE / 'audit-command-receipt.json').read_bytes())['exitCode'] == 0
    paths = [ROOT / 'docs/apple-settings-chunk-deadline-diagnosis.md']
    paths += [p for p in sorted(BASE.rglob('*')) if p.is_file() and p.name not in ['handoff.json', 'handoff.sha256']]
    assert all('__pycache__' not in p.parts for p in paths)
    packet = {'schema': 1, 'scope': 'Bound selected Settings chunk/deadline diagnosis; fixed4992 design candidate only',
        'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'nativeHandoffSHA256': receipt['nativeHandoffSHA256'],
        'members': {str(p.relative_to(ROOT)): row(p) for p in paths},
        'implementationSelected': False, 'nativeAccepted': False, 'gaAccepted': False,
        'physicalPhones': 'disconnected-deferred'}
    raw = (json.dumps(packet, indent=2, sort_keys=True) + '\n').encode()
    (BASE / 'handoff.json').write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    (BASE / 'handoff.sha256').write_text(digest + '  handoff.json\n')
    print(json.dumps({'members': len(packet['members']), 'handoffSHA256': digest, 'implementationSelected': False}))


if __name__ == '__main__':
    main()
