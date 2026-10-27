"""Select a closed, unexposed ordinary workspace composition source slice."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PACKET = ROOT / 'verification/console-fixed-workspace-dispatcher-selection'
DEST = OUT / 'fixed-dispatcher-selection.json'
assert not DEST.exists(), 'One-shot; do not replay'

def row(path):
    assert path.is_file() and not path.is_symlink()
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

seal = json.loads((PACKET / 'freeze.json').read_bytes())
assert seal['manifest_sha256'] == '96f97fb53b129e23dc2477e17406a8153226fc05f140f724c719fd18fbe741ec'
assert len(seal['files']) == 42
for item in seal['files']:
    actual = row(PACKET / item['path'])
    assert actual['bytes'] == item['bytes'] and actual['sha256'] == item['sha256']
inputs = json.loads((PACKET / 'inputs.json').read_bytes())
for item in inputs:
    actual = row(ROOT / item['path'])
    assert actual['bytes'] == item['bytes'] and actual['sha256'] == item['sha256']
contract = json.loads((PACKET / 'dispatcher-contract.json').read_bytes())
value = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
    'command': [sys.executable, '-B', str(Path(__file__).relative_to(ROOT))],
    'status': 'selected-private-fixed-dispatcher-source-and-bounded-host-slice',
    'contract': row(PACKET / 'dispatcher-contract.json'), 'seal': row(PACKET / 'freeze.json'),
    'packet_members_verified': 42, 'current_inputs_verified': len(inputs),
    'selected_product_files': contract['new_product_files'], 'selected_test_files': contract['new_test_files'],
    'producer_ownership': 'verification/console-fixed-workspace-dispatcher',
    'source_work_authorized': True, 'compiler_or_host_execution_released': False,
    'execution_next': 'Prepare exact explicit ordinary source/dependency closure and bounded compiler/host roster for root review before launch. No shared ambiguous application BEAMs, broad Mix/application boot, PostgreSQL or network.',
    'root_review': 'Same-process local capture preserves canonical current identity/storage/context guards, refuses preselected dynamic Repo and returns only bounded status/headers/body. Fixed defaults and exact atom controller init preserve ordinary authority. No callback or active session lifecycle is introduced.',
    'authority_limit': 'Component carries no production caller, route, startup or cookie authority. Token and request-id provenance are future trusted caller obligations; tests cannot establish authenticated sessions.',
    'no_new_dependency_or_canonical_existing_source_changes': True,
    'stopped_callback_review_or_PG16_harness_replayed': False,
    'pending': contract['pending'], 'implementation_accepted': False, 'GA_verified': 0}
with DEST.open('x') as stream:
    json.dump(value, stream, indent=2); stream.write('\n')
w = json.loads((ROOT / 'work-graph.json').read_bytes()); g = json.loads((ROOT / 'gates/ga.json').read_bytes())
for target in [w['packages'][13], g['gates'][21]]:
    target['fixedWorkspaceDispatcher'] = {'status': value['status'], 'root_selection': row(DEST),
        'implementation_accepted': False, 'ownership': value['producer_ownership'],
        'compiler_or_host_execution_released': False, 'actual_default_Repo_success_accepted': False,
        'session_or_cookie_authority_accepted': False, 'stopped_callback_review_replayed': False}
for name, data in [('work-graph.json', w), ('gates/ga.json', g)]:
    (ROOT / name).write_text(json.dumps(data, indent=2) + '\n')
for name in ['PLAN.md', 'STATUS.md']:
    path = ROOT / name; text = path.read_text()
    old = 'Production session admission, connected builds/releases, browser/provider operation and G22 acceptance remain pending.'
    new = 'A private same-process dispatcher is selected to reuse the fixed ordinary bearer/workspace pipeline and safely project its response; source work is authorized, while its exact host command closure awaits root review. It adds no cookie route or session authority. ' + old
    assert text.count(old) == 1
    path.write_text(text.replace(old, new))
print(json.dumps({'selected': value['status'], 'packet_members_verified': 42, 'inputs_verified': len(inputs), 'execution_released': False}))
