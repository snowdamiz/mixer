"""One-shot root review of released checkout repair and frontend contract."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE = 'b231f3d405c06bfb348f193d46a348af0529bd84'

def row(path):
    assert path.is_file() and not path.is_symlink()
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def save(name, value):
    with (OUT / name).open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, timeout=10)

assert not (OUT / 'acceptance.json').exists(), 'One shot; do not replay'
assert git('rev-parse', 'HEAD').decode().strip() == BASE
packet = ROOT / 'verification/ci-console-sparse-checkout'
manifest = json.loads((packet / 'input-manifest.json').read_bytes())
assert manifest['file_count'] == len(manifest['files']) == 55
assert manifest['total_input_bytes'] == sum(item['size_bytes'] for item in manifest['files']) == 380569
material = ''.join(f"{item['sha256']}  {item['path']}\n" for item in manifest['files'])
assert hashlib.sha256(material.encode()).hexdigest() == manifest['selected_tree_sha256']
for item in manifest['files']:
    # Compare the frozen checkout to committed bytes, not the active session lane.
    data = git('show', BASE + ':' + item['path'])
    assert len(data) == item['size_bytes'] and hashlib.sha256(data).hexdigest() == item['sha256']
    assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == item['git_blob_sha1']
before = git('show', BASE + ':.github/workflows/console.yml')
after = (ROOT / '.github/workflows/console.yml').read_bytes()
insertion = b'        with:\n          sparse-checkout-cone-mode: false\n          sparse-checkout: |\n' + b''.join(b'            ' + pattern.encode() + b'\n' for pattern in manifest['patterns'])
anchor = b'      - uses: actions/checkout@v4\n'
assert before.count(anchor) == 1 and after == before.replace(anchor, anchor + insertion)
assert after == (packet / 'console.yml.after').read_bytes()
validation = json.loads((packet / 'validation.json').read_bytes())
assert validation['workflow_sha256'] == hashlib.sha256(after).hexdigest()
assert set(validation['checks'].values()) == {'passed'}
assert validation['source_files_parsed'] == 38
runner = json.loads((packet / 'runner-receipt.json').read_bytes())
assert runner['exit_code'] == 0 and not runner['timed_out'] and runner['cleanup']['removed']
assert not Path(runner['cleanup']['scratch']).exists()
for name, sha in validation['verification_source_sha256'].items():
    assert row(packet / name)['sha256'] == sha
selection = ROOT / 'verification/console-session-integration-selection'
contract = json.loads((selection / 'frontend-contract.json').read_bytes())
assert contract['canonical_backend_revision'] == BASE
assert contract['ownership']['existing_product_files_allowed_to_change'] == ['console/src/main.tsx']
checks = json.loads((selection / 'source-checks.json').read_bytes())
assert len(checks) == 14 and all(value is True for value in checks.values())
source_receipt = json.loads((selection / 'receipt.json').read_bytes())
assert source_receipt['source_check_count'] == source_receipt['source_check_passed'] == 14
assert not source_receipt['source_checks_are_runtime_or_authentication_acceptance']
for item in json.loads((selection / 'inputs.json').read_bytes()):
    if item['authority'] == 'canonical-git-revision':
        data = git('show', BASE + ':' + item['path'])
        assert len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256']
custody = []
for folder in [packet, selection]:
    members = [row(path) for path in sorted(folder.rglob('*')) if path.is_file()]
    assert all(not path.is_symlink() for path in folder.rglob('*'))
    custody.append({'directory': str(folder.relative_to(ROOT)), 'members': members})
acceptance = {
    'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'revision': BASE,
    'command': [sys.executable, '-B', str(Path(__file__).relative_to(ROOT))],
    'python': sys.version, 'git': git('--version').decode().strip(),
    'checkout_repair': {'status': 'accepted-offline-input-closure-for-remote-validation',
        'workflow': row(ROOT / '.github/workflows/console.yml'), 'input_manifest': row(packet / 'input-manifest.json'),
        'selected_files': 55, 'selected_bytes': 380569, 'exact_checkout_only_diff': True,
        'manual_review': 'Package scripts, computed website asset loop, standalone Scope helper, generated TS/Vite test inputs, declared imports and ancestor configuration closure reviewed.',
        'runtime_pins_commands_timeout_unchanged': True, 'remote_runtime_passed': False},
    'session_selection': {'status': 'closed-frontend-contract-selected-implementation-active',
        'contract': row(selection / 'frontend-contract.json'), 'source_checks_passed': 14,
        'owner': '/root/console_browser_session_consumer', 'ownership': contract['ownership'],
        'backend_session_and_cookie_routes_exist': False, 'authenticated_workspace_accepted': False,
        'stopped_callback_review_replayed': False},
    'packets': custody, 'test_or_compiler_replay': False,
    'native_browser_capture_processes_started': False, 'GA_gates_verified': 0}
save('acceptance.json', acceptance)
w = json.loads((ROOT / 'work-graph.json').read_bytes())
g = json.loads((ROOT / 'gates/ga.json').read_bytes())
assert w['packages'][7]['fixtureCacheStateContractCandidate'] == g['gates'][1]['fixtureCacheStateContractCandidate']
assert w['packages'][4]['privateOwnerEffectContractCandidate'] == g['gates'][4]['privateOwnerEffectContractCandidate']
checkout = copy.deepcopy(w['packages'][13]['ConsoleSparseCheckout'])
checkout.update({'status': acceptance['checkout_repair']['status'], 'accepted': True,
    'root_acceptance': row(OUT / 'acceptance.json'), 'remote_passed': False})
session = copy.deepcopy(acceptance['session_selection'])
session['root_selection'] = row(OUT / 'acceptance.json')
for target in [w['packages'][13], g['gates'][21]]:
    target['ConsoleSparseCheckout'] = copy.deepcopy(checkout)
    target['browserSessionConsumer'] = copy.deepcopy(session)
w['packages'][13]['nextImplementation'] = 'Deliver the accepted checkout-only CI repair; implement and review the selected strict frontend browser-session consumer. Canonical session/cookie endpoints, backend lifecycle/provider admission and stopped callback independent acceptance remain pending.'
for name, value in [('work-graph.json', w), ('gates/ga.json', g)]:
    (ROOT / name).write_text(json.dumps(value, indent=2) + '\n')
for name in ['PLAN.md', 'STATUS.md']:
    path = ROOT / name
    text = path.read_text()
    old = 'A separate sparse checkout repair is selected. Phoenix and Engine workflows remain pending.'
    new = 'The checkout-only sparse repair has root acceptance after exact verification of all 55 committed input files; remote validation awaits delivery. Phoenix and Engine workflows remain pending. The strict frontend session consumer is selected and implementation is active; current missing server endpoints must continue producing unavailable state.'
    assert text.count(old) == 1
    path.write_text(text.replace(old, new))
subprocess.run(['git', 'diff', '--check', '--', '.github/workflows/console.yml', 'PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json'], cwd=ROOT, timeout=10, check=True)
assert len(w['packages']) == 18 and len(g['gates']) == 38
assert sum(item['status'] == 'running' for item in g['gates']) == 8
assert sum(item['status'] == 'planned' for item in g['gates']) == 30
save('metadata-validation.json', {'passed': True, 'metadata_files': [row(ROOT / p) for p in ['PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json']], 'script': row(Path(__file__).resolve()), 'GA_verified': 0})
print(json.dumps({'checkout_accepted_offline': True, 'selected_inputs': 55, 'session_contract_selected': True, 'runtime_or_GA_acceptance': False}))
