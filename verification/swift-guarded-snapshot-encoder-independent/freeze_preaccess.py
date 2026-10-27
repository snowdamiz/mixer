"""Seal this pre-access packet; later candidate review uses a separate subtree."""
from pathlib import Path
import datetime
import hashlib
import json
import sys

OWN = Path(__file__).resolve().parent
SEAL = OWN / 'preaccess-seal.json'


def member(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(OWN)), 'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest()}


if sys.argv[1:] == ['--verify']:
    seal = json.loads(SEAL.read_text())
    for expected in seal['members']:
        assert member(OWN / expected['path']) == expected
    assert hashlib.sha256(json.dumps(seal['members'], sort_keys=True,
        separators=(',', ':')).encode()).hexdigest() == seal['tree_sha256']
    print(json.dumps({'members_verified': len(seal['members']),
        'seal_sha256': hashlib.sha256(SEAL.read_bytes()).hexdigest(),
        'tree_sha256': seal['tree_sha256'], 'candidate_accessed': False}, sort_keys=True))
else:
    assert not sys.argv[1:] and not SEAL.exists()
    assert not list(OWN.rglob('__pycache__'))
    files = sorted(path for path in OWN.rglob('*') if path.is_file())
    assert not any(path.is_symlink() for path in OWN.rglob('*'))
    members = [member(path) for path in files]
    seal = {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status': 'independent-pre-access-packet-frozen-awaiting-exact-root-candidate-release',
        'command': [sys.executable, '-B', str(Path(__file__).resolve())],
        'tool_version': sys.version, 'members': members, 'member_count': len(members),
        'bytes': sum(item['bytes'] for item in members),
        'tree_sha256': hashlib.sha256(json.dumps(members, sort_keys=True,
            separators=(',', ':')).encode()).hexdigest(),
        'candidate_accessed': False, 'compiler_run': False,
        'root_selection_sha256': 'c1dda5391c60f3b3bb145eefa27dcf934918cdfc53df6273eaebead807e0d5ff',
        'accepted_source_tree_sha256': '9fbdabbc5122f71809483b3b0a0e95a71b9813def61572f366bcebc8ac6d08fb',
        'scope': 'synthetic finite oracle and frozen candidate review criteria; no encoder acceptance',
        'cleanup': 'Python children reaped; no compiler/native/UI/capture/process inventory; no owned bytecode; frozen inputs rehashed unchanged',
        'further_writes': 'Only new candidate-review/** after exact root release; these members remain frozen'}
    SEAL.write_text(json.dumps(seal, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'seal_sha256': hashlib.sha256(SEAL.read_bytes()).hexdigest(),
        'members': len(members), 'bytes': seal['bytes'], 'tree_sha256': seal['tree_sha256']}, sort_keys=True))
