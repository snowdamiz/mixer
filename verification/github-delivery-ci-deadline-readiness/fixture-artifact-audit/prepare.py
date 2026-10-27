"""Prepare only: adapt the accepted data-only fixture auditor without running it."""
import ast
import datetime
import difflib
import hashlib
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
PARENT = REPO / 'verification/github-delivery-loader-host-and-field-observations/fixture-artifact-audit'
SHA = '606c42876855897c315ee279dcd38fabaeb561ad'
TREE = '6e7ef189ea796effb2099eff927436bd407a080b'
RUN = 40447941540
OLD_SHA = 'da558f826e6ca5c753861b4c992414d531fae027'
OLD_TREE = '9266a1db1fe6a3a8cb2fc6b561ebfcf0dd99e122'
OLD_RUN = 40441050306
OLD_TEST = '3ea419bc5d4a4440f2d6e14855d12213cd37bbbbd9a7b69966e4ab0eddf07ace'
NEW_TEST = 'c754ea8c8cb40d0090c676de61263939e6e58b140f9902e97901126a4287e9ab'
ROOT_ACCEPTANCE = 'f2952ea37193d0717bc44298d00928ae527c7043064432bc66fec25d6e80fe1e'
SELECTION_SHA = '6d089a590c2b1d3a0332141ef53995c2c83b51b334ca6dba1285f91cd4b87adc'
assert __debug__ and not (HERE / 'preparation.json').exists()

def digest(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def save(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2) + '\n')

calls = []
def git(*args):
    argv = ['git', *args]
    result = subprocess.run(argv, cwd=REPO, capture_output=True, timeout=60)
    calls.append({'argv': argv, 'exit_code': result.returncode, 'stdout': digest(result.stdout), 'stderr': digest(result.stderr)})
    result.check_returncode()
    assert not result.stderr
    return result.stdout

def committed(path):
    return git('show', SHA + ':' + path)

seal_raw = (PARENT / 'seal.json').read_bytes()
assert digest(seal_raw)['sha256'] == 'dd2b3f0ec9fa01b38a762ef8ccf8bfb9017e5b506adbcf40e2fd79e778cdc750'
seal = json.loads(seal_raw)
assert len(seal['members']) == seal['member_count'] == 321
for row in seal['members']:
    p = pathlib.Path(row['path'])
    assert not p.is_absolute() and '..' not in p.parts and str(p) == row['path']
    source = PARENT / p
    assert source.is_file() and not source.is_symlink()
    assert digest(source.read_bytes()) == {k: row[k] for k in ('bytes', 'sha256')}
assert git('rev-parse', SHA + '^{tree}').decode().strip() == TREE
selection_raw = committed('verification/swift-cache-state-ci-workflow-root-review/selection.json')
assert digest(selection_raw)['sha256'] == SELECTION_SHA
assert selection_raw == (PARENT / 'source-selection.stdout').read_bytes()
selection = json.loads(selection_raw)
paths = git('ls-tree', '-r', '--name-only', SHA, '--', 'verification/swift-cache-state-ci').decode().splitlines()
assert len(paths) == len(set(paths)) == 91
rows = [{'path': p, **digest(committed(p))} for p in paths]
by_path = {r['path']: r for r in rows}
selected = {r['path']: r for r in selection['canonical_source_members']}
test_path = 'verification/swift-cache-state-ci/test_runner.py'
assert len(selected) == 90 and selected[test_path]['sha256'] == OLD_TEST
assert set(by_path) - set(selected) == {'verification/swift-cache-state-ci/README.md'}
assert set(selected) - set(by_path) == set()
changed = [p for p in selected if selected[p] != by_path[p]]
assert changed == [test_path] and by_path[test_path] == {'path': test_path, 'bytes': 17857, 'sha256': NEW_TEST}
root_raw = committed('verification/github-delivery-ci-deadline-readiness/root-acceptance.json')
assert digest(root_raw)['sha256'] == ROOT_ACCEPTANCE
root = json.loads(root_raw)
assert root['status'] == 'accepted-test-only-stage-readiness-correction'
assert root['canonical_test_source'] == by_path[test_path]
assert root['production_runner'] == by_path['verification/swift-cache-state-ci/check_cache_state.py']
amendment = []
for key, expected, count in [
    ('producer_seal', '6e9f2ea669c9653e9ac5829243d95d5cf7216a922bd5672524dfcb8ed5b94849', 384),
    ('independent_packet', '95538d31b8d3d88310cd9eb5271a1a549efd3cdf7407ad4b735f3d7fcf71ce40', 31),
    ('independent_decision', 'f9f60dcfd839766837e6b366fcd7b073b0a7abb069d86bec2cc20d88609c0c90', None),
]:
    item = root[key]
    data = committed(item['path'])
    assert digest(data) == {k: item[k] for k in ('bytes', 'sha256')} and item['sha256'] == expected
    value = json.loads(data)
    if count is not None:
        assert value['member_count'] == len(value['members']) == count
    amendment.append({'role': key, **item, 'manifest_only': True})
workflow_raw = committed('.github/workflows/verify.yml')
assert digest(workflow_raw)['sha256'] == selection['workflow_sha256']
assert by_path['verification/swift-cache-state-ci/check_cache_state.py']['sha256'] == selection['canonical_runner_sha256'] == 'e531311facb7b38967d3b904b26e92ff3f6c4dc7444c856cd799b70a1d91373b'
assert by_path['verification/swift-cache-state-ci/pack/manifest.json']['sha256'] == selection['pack_manifest_sha256']

scripts = {name: (PARENT / name).read_text() for name in ('capture.py', 'collect.py', 'audit-content.py', 'finalize.py')}
before = dict(scripts)
def replace(name, old, new):
    assert scripts[name].count(old) == 1, (name, old)
    scripts[name] = scripts[name].replace(old, new)

for name in ('collect.py', 'audit-content.py'):
    scripts[name] = scripts[name].replace(OLD_SHA, SHA).replace(OLD_TREE, TREE).replace(str(OLD_RUN), str(RUN))
replace('collect.py', "capture('source-workflow',", "capture('source-amendment-root', ['git', 'show', SHA + ':verification/github-delivery-ci-deadline-readiness/root-acceptance.json'])\nfor role, path in [('producer-seal', 'verification/swift-cache-state-ci-deadline-readiness/seal.json'), ('independent-packet', 'verification/swift-cache-state-ci-deadline-readiness-independent/packet-files.json'), ('independent-decision', 'verification/swift-cache-state-ci-deadline-readiness-independent/final-decision.json')]:\n    capture('source-amendment-' + role, ['git', 'show', SHA + ':' + path])\ncapture('source-workflow',")
replace('audit-content.py', 'DATA = {}', 'DATA = {}\nSOURCE_AMENDMENT = {}')
replace('audit-content.py', 'def validate_archive():', '''def validate_source_amendment(committed, selection):
    global SOURCE_AMENDMENT
    historical = (HERE / 'source-selection.stdout').read_bytes()
    assert hashlib.sha256(historical).hexdigest() == '6d089a590c2b1d3a0332141ef53995c2c83b51b334ca6dba1285f91cd4b87adc'
    original = {r['path']: r for r in selection['canonical_source_members']}
    assert len(original) == len(selection['canonical_source_members']) == 90
    path = 'verification/swift-cache-state-ci/test_runner.py'
    assert original[path] == {'path':path,'bytes':16386,'sha256':'3ea419bc5d4a4440f2d6e14855d12213cd37bbbbd9a7b69966e4ab0eddf07ace'}
    root_raw = (HERE / 'source-amendment-root.stdout').read_bytes()
    assert hashlib.sha256(root_raw).hexdigest() == 'f2952ea37193d0717bc44298d00928ae527c7043064432bc66fec25d6e80fe1e'
    root = strict(root_raw)
    assert root['status'] == 'accepted-test-only-stage-readiness-correction' and not root['CI_pass_claimed']
    assert root['canonical_test_source'] == {'path':path,'bytes':17857,'sha256':'c754ea8c8cb40d0090c676de61263939e6e58b140f9902e97901126a4287e9ab'}
    assert root['production_runner'] == {'path':'verification/swift-cache-state-ci/check_cache_state.py','bytes':29248,'sha256':EXPECTED_RUNNER}
    assert root['root_verified_independent_members'] == 31 and root['root_verified_independent_bytes'] == 278726
    assert root['root_focused_passed'] == root['independent_focused_passed'] == 29 and root['independent_negative_cases_passed'] == 6
    references = []
    for role, key, expected, count in [
        ('producer-seal','producer_seal','6e9f2ea669c9653e9ac5829243d95d5cf7216a922bd5672524dfcb8ed5b94849',384),
        ('independent-packet','independent_packet','95538d31b8d3d88310cd9eb5271a1a549efd3cdf7407ad4b735f3d7fcf71ce40',31),
        ('independent-decision','independent_decision','f9f60dcfd839766837e6b366fcd7b073b0a7abb069d86bec2cc20d88609c0c90',None)]:
        raw = (HERE / ('source-amendment-' + role + '.stdout')).read_bytes()
        ref = root[key]
        assert len(raw) == ref['bytes'] and hashlib.sha256(raw).hexdigest() == ref['sha256'] == expected
        value = strict(raw)
        if count is not None:
            assert len(value['members']) == value['member_count'] == count
        else:
            assert value['decision'] == 'accept-narrow-test-only-correction' and value['frozen'] and not value['actionable_findings']
            assert value['candidate_test_sha256'] == root['canonical_test_source']['sha256'] and value['unchanged_runner_sha256'] == EXPECTED_RUNNER
        references.append({'role':role,**ref,'manifest_or_decision_only':True})
    effective = dict(original)
    effective[path] = root['canonical_test_source']
    assert all({k:committed[p][k] for k in ('path','bytes','sha256')} == row for p,row in effective.items())
    assert sum(original[p] == effective[p] for p in original) == 89
    assert set(committed) - set(effective) == {'verification/swift-cache-state-ci/README.md'}
    SOURCE_AMENDMENT = {'historical_selection_sha256':hashlib.sha256(historical).hexdigest(),'historical_selection_members':90,'unchanged_historical_members':89,'explicit_root_amended_members':1,'additional_README_members':1,'committed_canonical_paths':91,'root_acceptance_sha256':hashlib.sha256(root_raw).hexdigest(),'old_test_source':original[path],'committed_test_source':effective[path],'references':references,'historical_selection_rewritten':False,'new_test_source_executed_by_audit':False}

def validate_archive():''')
replace('audit-content.py', "    assert custody['source_revision'] == EXPECTED_REVISION", "    assert custody['source_revision'] == EXPECTED_REVISION and custody['source_tree'] == EXPECTED_TREE")
replace('audit-content.py', "    assert all({k:committed[r['path']][k] for k in ('path','bytes','sha256')} == r for r in selection['canonical_source_members'])", "    validate_source_amendment(committed, selection)")
replace('audit-content.py', "        receipt = record['receipt']", "        assert record['scope'] == 'Actual runner handler and registered real timer with test-only stage readiness and 50ms logical cleanup allowance; deliberately slow hook and missing compiler, zero child commands. Preceding postflight wall time is excluded from this injected-stage control.'\n        assert record['state']['stage_timer_started'] is True\n        receipt = record['receipt']")
replace('audit-content.py', "'cleanup_seconds':receipt['cleanup_elapsed_seconds']", "'cleanup_seconds':receipt['cleanup_elapsed_seconds'],'cleanup_seconds_clock':'Adjusted test logical cleanup time; preceding postflight wall time excluded','stage_timer_started':True,'whole_cleanup_wall_time_qualified':False")
replace('audit-content.py', "'source_revision': EXPECTED_REVISION, 'source_tree': receipt['source_tree'],", "'source_revision': EXPECTED_REVISION, 'source_tree': receipt['source_tree'], 'source_amendment':SOURCE_AMENDMENT,")
replace('audit-content.py', "            'Global workflow status is recorded at audit snapshot only; no global CI success claim',", "            'Global workflow status is recorded at audit snapshot only; no global CI success claim',\n            'Deadline controls use stage-ready real timers with adjusted test logical cleanup time that excludes preceding postflight wall time; no whole-cleanup wall-time qualification',")
replace('finalize.py', "    'normal_full_invocations': 1,", "    'source_amendment': report['source_amendment'],\n    'normal_full_invocations': 1,")

script_rows = []
for name, text in scripts.items():
    ast.parse(text, filename=name)
    assert not (HERE / name).exists()
    diff = ''.join(difflib.unified_diff(before[name].splitlines(True), text.splitlines(True), fromfile='parent/' + name, tofile='current/' + name))
    (HERE / name).write_text(text)
    (HERE / (name + '.diff')).write_text(diff)
    script_rows.append({'source': str((PARENT / name).relative_to(REPO)), 'source_digest': digest(before[name].encode()), 'target': str((HERE / name).relative_to(REPO)), 'adapted_digest': digest(text.encode()), 'diff_file': name + '.diff', 'diff_sha256': digest(diff.encode())['sha256']})

save('source-closure-preparation.json', {'source_revision': SHA, 'source_tree': TREE, 'historical_selection_sha256':SELECTION_SHA, 'historical_selection_members':90, 'unchanged_historical_members':89, 'explicit_root_amended_members':1, 'additional_README_members':1, 'canonical_paths':rows, 'old_test_source':selected[test_path], 'new_test_source':by_path[test_path], 'root_acceptance': {'path':'verification/github-delivery-ci-deadline-readiness/root-acceptance.json', **digest(root_raw)}, 'root_references':amendment, 'workflow':digest(workflow_raw), 'historical_selection_rewritten':False, 'commands':calls, 'scope':'Git object data only; no source import or execution, no artifact fetch, inspection, extraction or execution; reference manifests counted and hashed only'})
save('script-sha256.json', script_rows)
save('preparation.json', {'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':sys.argv,'python':sys.version,'source_revision':SHA,'source_tree':TREE,'run_id':RUN,'run_attempt':1,'run_url':f'https://github.com/snowdamiz/mixer/actions/runs/{RUN}','closed_parent_members_verified':321,'parent_seal':digest(seal_raw),'scripts':script_rows,'source_closure':digest((HERE/'source-closure-preparation.json').read_bytes()),'preparer':digest(pathlib.Path(__file__).read_bytes()),'syntax_validation':'ast.parse only; no prepared scripts imported or executed','execution_status':'awaiting root review and explicit release; fixture job success required by collector','scope':'Data-only exact fixture audit preparation with historical selection plus one explicit root test amendment; no artifact fetch or code execution; no run polling, native/UI/capture/process inventory'})
print(json.dumps({'prepared':True,'scripts':[{ 'name':pathlib.Path(r['target']).name, **r['adapted_digest']} for r in script_rows],'canonical_paths':91,'historical_unchanged':89,'explicit_root_test_amendments':1,'README':1,'execution_authorized':False}))
