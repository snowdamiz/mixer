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
 ('android-editor-membership-compiled-boundary-qualification/passive-return-probe-v2', '6f0f76afa6b7ba4ff4bb80552d69db16ecdc9eb9e210dfb24a43fe62e06c05e1', None, 'passive-return-probe-v2-custody.json'),
 ('android-editor-membership-compiled-boundary-qualification/passive-return-probe-v2-provenance-addendum', 'ee2e8ec503f2ba4ef00470ce39513f33b60e4ac4cee9237f5982ba0594d4e5c5', None, 'passive-return-probe-v2-provenance-custody.json'),
 ('android-editor-membership-qualification-independent/derivative-review', '66be37223cd48a57d1fc327c2c25c1c76ef153eb876a90dc97c4a8daa0484ddd', None, 'passive-return-probe-independent-custody.json'),
 ('android-editor-membership-qualification-independent/semantic-review', '811afc2e3625cf8070aeae7888cefb159196b8c17ce33ad78be82881c6f2852d', None, 'compiled-semantic-identity-custody.json'),
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
