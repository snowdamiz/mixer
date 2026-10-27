"""Prepare the accepted five-phase data-only audit; execute no audit phase."""
import ast
import datetime
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PARENT = REPO / 'verification/github-delivery-loader-host-and-field-observations/terminal-artifact-audit'
FIXTURE = REPO / 'verification/github-delivery-ci-deadline-readiness/fixture-artifact-audit'
SHA = '606c42876855897c315ee279dcd38fabaeb561ad'
TREE = '6e7ef189ea796effb2099eff927436bd407a080b'
RUN = 40447941540
OLD_SHA = 'da558f826e6ca5c753861b4c992414d531fae027'
OLD_TREE = '9266a1db1fe6a3a8cb2fc6b561ebfcf0dd99e122'
OLD_RUN = 40441050306
assert __debug__ and not (HERE / 'preparation.json').exists()

def digest(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def save(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2) + '\n')

def verify_packet(root, expected, count):
    raw = (root / 'seal.json').read_bytes()
    assert digest(raw)['sha256'] == expected
    seal = json.loads(raw)
    assert len(seal['members']) == seal['member_count'] == count
    assert len({r['path'] for r in seal['members']}) == count
    for row in seal['members']:
        p = Path(row['path'])
        assert not p.is_absolute() and '..' not in p.parts and str(p) == row['path']
        source = root / p
        assert source.is_file() and not source.is_symlink()
        assert digest(source.read_bytes()) == {k: row[k] for k in ('bytes', 'sha256')}
    assert sum(r['bytes'] for r in seal['members']) == seal['total_bytes']
    return raw, seal

parent_raw, parent = verify_packet(PARENT, '7f746de5e3c058509ac511b1f1f67b5725b33e8bfb0c2e5159f6322ba236ab59', 73)
fixture_raw, fixture = verify_packet(FIXTURE, 'e681cda4c2140aeee119d4c7b6ac223859df822e2671a80d90ed030102386c3f', 347)
fixture_acceptance_raw = (FIXTURE / 'acceptance.json').read_bytes()
assert digest(fixture_acceptance_raw)['sha256'] == fixture['acceptance_sha256'] == '2e9935e38029160b779761c94946805fcb8d71563c6929aa65ceecc56885c59e'
accepted_fixture = json.loads(fixture_acceptance_raw)
assert accepted_fixture['source_revision'] == SHA and accepted_fixture['source_tree'] == TREE and accepted_fixture['run_id'] == RUN
amended = accepted_fixture['source_amendment']
assert amended['historical_selection_members'] == 90 and amended['unchanged_historical_members'] == 89
assert amended['explicit_root_amended_members'] == amended['additional_README_members'] == 1 and amended['committed_canonical_paths'] == 91
assert not amended['historical_selection_rewritten'] and not amended['new_test_source_executed_by_audit']

calls = []
def git(*args):
    argv = ['git', *args]
    result = subprocess.run(argv, cwd=REPO, capture_output=True, timeout=60)
    calls.append({'argv': argv, 'cwd': str(REPO), 'exit_code': result.returncode, 'stdout': digest(result.stdout), 'stderr': digest(result.stderr), 'scope': 'Read-only committed source tree/blob identity; no source import or execution'})
    result.check_returncode()
    assert not result.stderr
    return result.stdout

assert git('rev-parse', SHA + '^{tree}').decode().strip() == TREE
source_sets = {}
all_sources = {}
for name, path, count in [('core-jvm', 'source-blobs.json', 203), ('capability', 'capability/source-blobs.json', 313)]:
    raw = (PARENT / path).read_bytes()
    rows = json.loads(raw)
    assert len(rows) == count
    for source, row in rows.items():
        p = Path(source)
        assert not p.is_absolute() and '..' not in p.parts and str(p) == source
        assert not any(s in source.lower() for s in ('hostedcatalog', 'hosted-catalog', 'authority-driver', 'rejectedworker', 'hosted-harness', 'stopped-android', 'android-v5', 'androidv5'))
        assert source not in all_sources or all_sources[source] == row
        all_sources[source] = row
    source_sets[name] = {'path': str((PARENT / path).relative_to(REPO)), **digest(raw), 'members': count}
paths = sorted(all_sources)
tree_data = git('ls-tree', '-r', SHA, '--', *paths)
current = {}
for line in tree_data.decode().splitlines():
    properties, path = line.split('\t', 1)
    mode, kind, blob = properties.split(' ')
    assert mode in ('100644', '100755') and kind == 'blob' and path not in current
    current[path] = blob
assert set(current) == set(all_sources)
assert all(current[path] == row['git_blob'] for path, row in all_sources.items())
assert git('diff', '--name-status', OLD_SHA, SHA, '--', *paths) == b''
workflow = git('show', SHA + ':.github/workflows/verify.yml')
assert digest(workflow)['sha256'] == '7f3ab7ef5ec94379a969c91e9f2348cecd2e80908c8a7330aef845f133f38e62'
assert git('diff', '--name-status', OLD_SHA, SHA, '--', '.github/workflows/verify.yml') == b''

scripts = []
adaptations = []
for name in ('audit.py', 'capability_review.py', 'phases.py', 'run-reviewed.py', 'freeze.py'):
    original = (PARENT / name).read_text()
    text = original.replace(OLD_SHA, SHA).replace(OLD_TREE, TREE).replace(str(OLD_RUN), str(RUN))
    if name == 'phases.py':
        replacements = {
            'verification/github-delivery-loader-host-and-field-observations/fixture-artifact-audit': 'verification/github-delivery-ci-deadline-readiness/fixture-artifact-audit',
            '8a157f70fab4dfdfb3cb295ff62a136eeaf16909517577abd2debf73c105f91b': '2e9935e38029160b779761c94946805fcb8d71563c6929aa65ceecc56885c59e',
            'dd2b3f0ec9fa01b38a762ef8ccf8bfb9017e5b506adbcf40e2fd79e778cdc750': 'e681cda4c2140aeee119d4c7b6ac223859df822e2671a80d90ed030102386c3f',
        }
        for old, new in replacements.items():
            assert text.count(old) == 1
            text = text.replace(old, new)
    if name in ('capability_review.py', 'run-reviewed.py'):
        assert text == original
    ast.parse(text, filename=name)
    assert not (HERE / name).exists()
    (HERE / name).write_text(text)
    diff = ''.join(difflib.unified_diff(original.splitlines(True), text.splitlines(True), fromfile='parent/' + name, tofile='current/' + name))
    (HERE / (name + '.diff')).write_text(diff)
    scripts.append({'path': name, 'digest': digest(text.encode())})
    adaptations.append({'parent': str((PARENT / name).relative_to(REPO)), 'parent_digest': digest(original.encode()), 'target': name, 'adapted_digest': digest(text.encode()), 'diff_file': name + '.diff', 'diff_sha256': digest(diff.encode())['sha256']})
prior_failure = (PARENT / 'prior-failure.json').read_bytes()
assert digest(prior_failure)['sha256'] == '4c48fcb57adf45de7fa6365d958b00f59e4aa9c0b2bcf0778541832a8974b230'
assert json.loads(prior_failure)['descendant_reaping_verified'] is False
(HERE / 'prior-failure.json').write_bytes(prior_failure)
save('source-binding-preparation.json', {'source_revision': SHA, 'source_tree': TREE, 'prior_revision': OLD_SHA, 'parent_source_manifests':source_sets, 'unchanged_unique_source_paths':len(all_sources), 'source_blobs':all_sources, 'current_git_blob_identity_verified':True, 'selected_source_path_content_or_mode_changes':0, 'workflow':digest(workflow), 'commands':calls, 'scope':'Prior accepted exact-source hashes and Git blob identities remain unchanged at new commit; tree and diff verification only; no source import/execution or audit phase'})
save('fixture-binding-preparation.json', {'path':str(FIXTURE.relative_to(REPO)), 'source_revision':SHA, 'source_tree':TREE, 'run_id':RUN, 'seal':digest(fixture_raw), 'acceptance':digest(fixture_acceptance_raw), 'sealed_members_verified':347, 'sealed_bytes_verified':fixture['total_bytes'], 'source_amendment':amended, 'scope':'Current separately frozen fixture packet data verified without modification or rerun'})
save('script-sha256.json', scripts)
save('preparation.json', {'schema':3,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':sys.argv,'python':sys.version,'source_revision':SHA,'source_tree':TREE,'run_id':RUN,'run_attempt':1,'parent_seal':digest(parent_raw),'closed_parent_members_verified':73,'closed_parent_bytes_verified':parent['total_bytes'],'execution_scripts':scripts,'adaptations':adaptations,'static_data':[{'path':'prior-failure.json','digest':digest(prior_failure),'copied_unchanged':True}],'source_binding_preparation':digest((HERE/'source-binding-preparation.json').read_bytes()),'fixture_binding_preparation':digest((HERE/'fixture-binding-preparation.json').read_bytes()),'preparer':digest(Path(__file__).read_bytes()),'bounds':'Five independently bounded 60 second phases; own child process group reaping; no broad inventory','selection':'Accepted core/JVM/capability and historical failure logic unchanged; only exact source commit/tree/run and separate fixture constants adapted','syntax_validation':'ast.parse only; prepared scripts not imported or executed','prohibited_activity':'No artifact execution/import/extraction; no native/UI/capture/process inventories; no production, forbidden hosted/stopped harness, Git changes or CI retries','execution_status':'Awaiting explicit root exact-script release and confirmed six passing jobs / 64 passing steps','current_execution_or_terminal_acceptance':False})
print(json.dumps({'prepared':True,'parent_members_verified':73,'fixture_members_verified':347,'source_manifests':{'core_jvm':203,'capability':313},'unique_source_paths_unchanged':len(all_sources),'scripts':scripts,'execution_authorized':False}))
