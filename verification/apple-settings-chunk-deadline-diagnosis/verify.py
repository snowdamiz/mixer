"""Read-only sealed packet verification. No producer/compiler/runtime import."""
import hashlib
import json
import pathlib
import stat

BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[1]


def verify():
    handoff_path = BASE / 'handoff.json'
    expected = (BASE / 'handoff.sha256').read_text().split()[0]
    assert hashlib.sha256(handoff_path.read_bytes()).hexdigest() == expected
    packet = json.loads(handoff_path.read_bytes())
    for name, row in packet['members'].items():
        path = ROOT / name
        assert path.is_file() and not path.is_symlink() and path.resolve() == path
        raw = path.read_bytes()
        assert len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256']
        assert stat.S_IMODE(path.stat().st_mode) == row['mode']
    actual = {str(p.relative_to(ROOT)) for p in BASE.rglob('*') if p.is_file() and p.name not in ['handoff.json', 'handoff.sha256']}
    assert actual == {name for name in packet['members'] if name.startswith(str(BASE.relative_to(ROOT)) + '/')}
    native = ROOT / 'verification/apple-settings-instrumented-native/handoff.json'
    assert hashlib.sha256(native.read_bytes()).hexdigest() == packet['nativeHandoffSHA256']
    assert not (BASE / 'owned-host-scratch').exists()
    assert packet['implementationSelected'] is False and packet['nativeAccepted'] is False
    print(json.dumps({'passed': True, 'membersVerified': len(packet['members']), 'handoffSHA256': expected,
        'nativeAccepted': False, 'implementationSelected': False, 'scope': 'read-only packet hash and scratch checks'}))


if __name__ == '__main__':
    verify()
