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
    ('android-editor-source-pair5-host-integration',
     'c356544da794b1ae630ec2bb4522f8a9ed93fe1aedb9958676dc84f27188733a',
     'manifest.json', 'source-pair5-host-candidate-custody.json'),
    ('android-editor-source-pair5-cli-integration',
     '87cd2e4e14d0c444d308397dbd59dbe271419261f5d7fa2cd7201af35db18ecf',
     None, 'source-pair5-cli-candidate-custody.json'),
    ('android-editor-membership-compiled-boundary-qualification/interface-v2',
     'cf0b1ffc29297ed5d0a26f6c59c2aaf7cc9c929ebfb308ef22d9d4f28d05e3cd',
     None, 'source-pair5-interface-v2-custody.json'),
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
    if 'member_count' in manifest and (len(members) != manifest['member_count'] or total != manifest['member_bytes']):
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
