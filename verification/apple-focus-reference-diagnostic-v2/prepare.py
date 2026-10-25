"""Read-only adapter to frozen v1 source/archive helpers; all test scratch is v2-owned."""
import hashlib
import importlib.util
import json
from pathlib import Path
import stat

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
SOURCES_BASE = ROOT / 'verification/apple-focus-reference-diagnostic-v1'
REVIEW = ROOT / 'verification/apple-focus-reference-diagnostic-v1-independent-review'
V1_HANDOFF_SHA = '9f066db167168e8ab0c78b2147f857ba3980d965a69b681e566e5e185f6a0d3c'
REVIEW_HANDOFF_SHA = 'd70da20d45323be52138a6efdbd2d53c74efbd521620584b228bf9f03e3eedbb'


def require(value, message):
    if not value: raise ValueError(message)


def sha(value): return hashlib.sha256(value).hexdigest()


def stable(value): return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()


def row(path):
    info = path.lstat()
    require(path.resolve() == path and stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
            'Canonical regular input required: ' + str(path))
    value = path.read_bytes()
    return {'kind': 'file', 'bytes': len(value), 'mode': stat.S_IMODE(info.st_mode), 'sha256': sha(value)}


def verify_history():
    history = {}
    for base, expected in [(SOURCES_BASE, V1_HANDOFF_SHA), (REVIEW, REVIEW_HANDOFF_SHA)]:
        handoff_path = base / 'handoff.json'
        require(row(handoff_path)['sha256'] == expected, 'Frozen history identity changed')
        handoff = json.loads(handoff_path.read_bytes())
        require(all(row(ROOT / name) == item for name, item in handoff['members'].items()), 'Frozen history member changed')
        require(sha(stable(handoff['members'])) == handoff['memberTreeSHA256'], 'Frozen history member digest changed')
        history[str(handoff_path.relative_to(ROOT))] = row(handoff_path)
    return history


# This inspected module contains source/archive transforms only. No preparation
# action, compiler, runtime orchestration, authority, or catalog is imported.
verify_history()
spec = importlib.util.spec_from_file_location('reference_v1_frozen_source_data_helpers', SOURCES_BASE / 'prepare.py')
v1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v1)
for name in ['OLD', 'BUILD', 'PACKET_SHA', 'APP', 'RUNNER', 'ORACLES', 'inputs', 'render', 'once',
             'manifest', 'generated', 'archive', 'write_archive', 'verify']:
    globals()[name] = getattr(v1, name)


if __name__ == '__main__':
    print(json.dumps({'history': verify_history(), 'source': verify(), 'nativeExecuted': False, 'compileRerun': False}, sort_keys=True))
