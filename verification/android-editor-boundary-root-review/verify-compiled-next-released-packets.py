"""One-shot root custody of released immutable integration packets, no imports."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PACKETS = (
 ('android-editor-membership-compiled-boundary-qualification/interface-v4', 'ad4e44ab575b0dccf0c438594203bced8bc1530644c71ec62359eab8edfbe60b', None, 'source-pair5-interface-v4-custody.json'),
 ('android-editor-membership-qualification-independent/semantic-applicability', '2de23db19e5643ad9d18bf164c1dfa2221b589947661fcfcf4ac53dfe0a0a566', None, 'compiled-semantic-applicability-custody.json'),
 ('android-editor-membership-compiled-boundary-qualification/state-replay-candidate-v1', 'a2a7cf3e833fd9aa5c446d090559418f40f19e3fa58a12279efae458f68506b7', None, 'compiled-state-replay-v1-custody.json'),
 ('android-editor-membership-compiled-boundary-qualification/passive-return-probe-v3', '04b282dbe16898d0a417286303c87a587b97da1153a3efaf3b564a895a16d8b7', None, 'passive-return-probe-v3-custody.json'),
)


def identity(path):
    if not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError('not a regular file: ' + str(path))
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
for name, expected_seal, manifest_name, result_name in PACKETS:
    folder = ROOT / 'verification' / name
    seal_identity = identity(folder / 'seal.json')
    if seal_identity['sha256'] != expected_seal:
        raise ValueError('wrong frozen seal: ' + name)
    seal = json.loads((folder / 'seal.json').read_bytes())
    excluded = {'seal.json'}
    if manifest_name:
        if identity(folder / manifest_name) != seal['manifest']:
            raise ValueError('wrong frozen manifest: ' + name)
        manifest = json.loads((folder / manifest_name).read_bytes())
        excluded.add(manifest_name)
    else:
        manifest = seal
    members = manifest['members']
    paths = []
    for row in members:
        path = PurePosixPath(row['path'])
        if path.is_absolute() or str(path) != row['path'] or '..' in path.parts or not path.parts:
            raise ValueError('invalid relative member')
        paths.append(str(path))
        if identity(folder / str(path)) != {'bytes': row['bytes'], 'sha256': row['sha256']}:
            raise ValueError('member identity mismatch: ' + name + '/' + str(path))
    if len(paths) != len(set(paths)):
        raise ValueError('duplicate manifest member')
    actual = set()
    for base, directories, files in os.walk(folder, followlinks=False):
        for child in directories + files:
            p = Path(base) / child
            if p.is_symlink():
                raise ValueError('symlink in frozen packet')
        actual.update(str((Path(base) / file).relative_to(folder)) for file in files)
    if actual != set(paths) | excluded:
        raise ValueError('closed frozen packet path set mismatch')
    total = sum(row['bytes'] for row in members)
    if 'member_count' in manifest and (len(members) != manifest['member_count'] or total != manifest.get('member_bytes',total)):
        raise ValueError('declared count/size mismatch')
    receipt = {
        'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
        'command': [sys.executable, '-B', str(Path(__file__).relative_to(ROOT))],
        'python': platform.python_version(), 'head_context_only': head,
        'packet': str(folder.relative_to(ROOT)), 'seal': seal_identity,
        'member_count': len(members), 'member_bytes': total,
        'exact_closed_members_verified': True, 'symlinks_present': False,
        'source_executed': False, 'scope': 'root byte custody only; independent behavior acceptance pending',
    }
    with (OUT / result_name).open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(name, len(members), total, 'custody passed')
