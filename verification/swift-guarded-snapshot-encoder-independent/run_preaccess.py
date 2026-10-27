"""Run only the independently authored finite Python controls; freeze separately."""
from pathlib import Path
import datetime
import hashlib
import json
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent
OUT = OWN / 'controls'
SOURCE = ROOT / 'verification/swift-guarded-snapshot-export-preparation/inputs/accepted-source/vm'
MANIFEST = ROOT / 'verification/swift-guarded-snapshot-export-preparation/inputs/source-manifest.json'


def digest(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest()}


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def command(name, args):
    run = subprocess.run(args, cwd=ROOT, capture_output=True)
    (OUT / (name + '.stdout')).write_bytes(run.stdout)
    (OUT / (name + '.stderr')).write_bytes(run.stderr)
    receipt = {'argv': args, 'cwd': str(ROOT), 'exit': run.returncode,
               'stdout': digest(OUT / (name + '.stdout')),
               'stderr': digest(OUT / (name + '.stderr'))}
    dump(OUT / (name + '.json'), receipt)
    return run


OUT.mkdir(exist_ok=True)
pins = {
 'verification/swift-semantic-adapter-root-review/guarded-snapshot-encoder-component-selection.json': 'c1dda5391c60f3b3bb145eefa27dcf934918cdfc53df6273eaebead807e0d5ff',
 'verification/swift-semantic-adapter-root-review/guarded-snapshot-export-contract-host-acceptance.json': '02f8feb30c9a4ab84c31cfcb2c2b1bdcb4518b55d75770426d587f31b4e241cc',
 'verification/swift-guarded-snapshot-export-contract-correction/seal.json': 'e1e5fd13eb421131e8b610ec2cdca7a494cc9f6d3554a48764d37984a9082667',
 'verification/swift-guarded-snapshot-export-contract-correction-independent/seal.json': '8d1da9664d6d6f5359f4007603f2b8248b298102ffe8b5a3f430311f658f29fe',
}
manifest = json.loads(MANIFEST.read_text())
assert manifest['member_count'] == 144
assert manifest['tree_sha256'] == '9fbdabbc5122f71809483b3b0a0e95a71b9813def61572f366bcebc8ac6d08fb'
assert hashlib.sha256(json.dumps(manifest['members'], sort_keys=True,
    separators=(',', ':')).encode()).hexdigest() == manifest['tree_sha256']
actual_paths = sorted(str(path.relative_to(SOURCE)) for path in SOURCE.rglob('*') if path.is_file())
assert actual_paths == sorted(member['path'] for member in manifest['members'])
assert not any(path.is_symlink() for path in SOURCE.rglob('*'))
checked = []
for member in manifest['members']:
    actual = digest(SOURCE / member['path'])
    assert actual['bytes'] == member['bytes'] and actual['sha256'] == member['sha256']
    checked.append(actual)
for path, expected in pins.items():
    assert digest(ROOT / path)['sha256'] == expected
inputs = [digest(ROOT / path) for path in pins]
inputs += [digest(MANIFEST)]
for name in ('contract.md', 'equality-table.json', 'source-roster.json', 'source-equation-evidence.json'):
    inputs.append(digest(ROOT / 'verification/swift-guarded-snapshot-export-contract-correction' / name))
before = {'inputs': inputs, 'accepted_source_members': checked}
dump(OUT / 'input-custody-before.json', before)
revision = command('source-revision', ['git', 'rev-parse', 'HEAD'])
version = command('python-version', [sys.executable, '--version'])
controls = command('preaccess', [sys.executable, '-B', str(OWN / 'test_preaccess.py')])
assert controls.returncode == 0, controls.stderr.decode()
for item in inputs + checked:
    assert digest(ROOT / item['path']) == item
dump(OUT / 'input-custody-after.json', before)
summary = json.loads(controls.stdout.decode().splitlines()[-1])
dump(OUT / 'receipt.json', {
    'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'status': 'pre-access-controls-passed-candidate-unread', 'result': summary,
    'root_revision': revision.stdout.decode().strip(),
    'python': version.stdout.decode().strip(), 'python_executable': sys.executable,
    'platform': platform.platform(), 'rustc_on_initial_shell_path': shutil.which('rustc'),
    'accepted_source_tree': manifest['tree_sha256'], 'actual_members_rehashed': len(checked),
    'independent_sources': [digest(OWN / name) for name in
        ('wire_oracle.py', 'test_preaccess.py', 'run_preaccess.py', 'review-plan.md')],
    'scope': 'finite synthetic oracle and independent review criteria; no compiler/candidate/operational acceptance',
    'cleanup': {'python_child_reaped': True, 'native_UI_capture_started': False,
                'process_inventory_run': False, 'compiler_started': False,
                'pycache_present_in_owned_directory': bool(list(OWN.rglob('__pycache__'))),
                'frozen_inputs_unchanged': True},
})
print(json.dumps(summary, sort_keys=True))
