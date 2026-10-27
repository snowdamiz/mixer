"""Prepare exact-source data-only fixture audit scripts; never execute them."""
import ast
import datetime
import difflib
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PARENT = REPO / 'verification/github-delivery-ci-deadline-readiness/fixture-artifact-audit'
SHA = '43cbfb9c925e2ee7de43afd92bd588edb7ff60b6'
TREE = '93cc6868f445fa98c170acf771db73e50d90b4e2'
RUN = 40450561458
OLD_SHA = '606c42876855897c315ee279dcd38fabaeb561ad'
OLD_TREE = '6e7ef189ea796effb2099eff927436bd407a080b'
OLD_RUN = 40447941540
PARENT_SEAL = 'e681cda4c2140aeee119d4c7b6ac223859df822e2671a80d90ed030102386c3f'
PARENT_ACCEPTANCE = '2e9935e38029160b779761c94946805fcb8d71563c6929aa65ceecc56885c59e'
SELECTION_SHA = '6d089a590c2b1d3a0332141ef53995c2c83b51b334ca6dba1285f91cd4b87adc'
TEST_SHA = 'c754ea8c8cb40d0090c676de61263939e6e58b140f9902e97901126a4287e9ab'
RUNNER_SHA = 'e531311facb7b38967d3b904b26e92ff3f6c4dc7444c856cd799b70a1d91373b'
assert __debug__ and not (HERE / 'preparation.json').exists()


def digest(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def save(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2) + '\n')


calls = []


def git(*args, retain_text=False):
    argv = ['git', *args]
    proc = subprocess.Popen(argv, cwd=REPO, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, start_new_session=True)
    timed_out = False
    try:
        stdout, stderr = proc.communicate(timeout=55)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(proc.pid, signal.SIGKILL)
        stdout, stderr = proc.communicate(timeout=4)
    group_gone = False
    try:
        os.killpg(proc.pid, 0)
    except ProcessLookupError:
        group_gone = True
    record = {'argv': argv, 'cwd': str(REPO), 'exit_code': proc.returncode,
              'timed_out': timed_out, 'pid': proc.pid, 'pgid': proc.pid,
              'new_session': True, 'child_reaped': proc.poll() is not None,
              'owned_group_gone': group_gone, 'child_limit_seconds': 55,
              'stdout': digest(stdout), 'stderr': digest(stderr)}
    if retain_text:
        record['stdout_text'] = stdout.decode()
    calls.append(record)
    assert not timed_out and proc.returncode == 0 and not stderr and group_gone, record
    return stdout


def committed(path):
    raw = git('show', SHA + ':' + path)
    blob = git('rev-parse', SHA + ':' + path).decode().strip()
    assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == blob
    return raw, blob


seal_raw = (PARENT / 'seal.json').read_bytes()
assert digest(seal_raw)['sha256'] == PARENT_SEAL
assert digest((PARENT / 'acceptance.json').read_bytes())['sha256'] == PARENT_ACCEPTANCE
seal = json.loads(seal_raw)
assert seal['member_count'] == len(seal['members']) == 347
names = set()
for row in seal['members']:
    path = Path(row['path'])
    assert not path.is_absolute() and '..' not in path.parts and str(path) == row['path']
    assert row['path'] not in names
    names.add(row['path'])
    source = PARENT / path
    assert source.is_file() and not source.is_symlink()
    assert digest(source.read_bytes()) == {k: row[k] for k in ('bytes', 'sha256')}
assert {str(p.relative_to(PARENT)) for p in PARENT.rglob('*') if p.is_file()} == names | {'seal.json'}
git_version = git('--version', retain_text=True).decode().strip()
assert git('rev-parse', SHA + '^{tree}', retain_text=True).decode().strip() == TREE
selection_raw, selection_blob = committed('verification/swift-cache-state-ci-workflow-root-review/selection.json')
assert digest(selection_raw)['sha256'] == SELECTION_SHA
assert selection_raw == (PARENT / 'source-selection.stdout').read_bytes()
selection = json.loads(selection_raw)
tree_raw = git('ls-tree', '-r', '-z', SHA, '--', 'verification/swift-cache-state-ci', retain_text=True)
tree_rows = {}
for entry in tree_raw.split(b'\0'):
    if not entry:
        continue
    header, path = entry.split(b'\t', 1)
    mode, kind, blob = header.decode().split()
    assert mode in ('100644', '100755') and kind == 'blob'
    assert path.decode() not in tree_rows
    tree_rows[path.decode()] = {'git_blob': blob, 'git_mode': mode}
assert len(tree_rows) == 91
rows = []
for path, item in tree_rows.items():
    raw, blob = committed(path)
    assert blob == item['git_blob']
    rows.append({'path': path, **digest(raw), **item})
by_path = {r['path']: {k: r[k] for k in ('path', 'bytes', 'sha256')} for r in rows}
historical = {r['path']: r for r in selection['canonical_source_members']}
test_path = 'verification/swift-cache-state-ci/test_runner.py'
assert len(historical) == 90
assert historical[test_path]['sha256'] == '3ea419bc5d4a4440f2d6e14855d12213cd37bbbbd9a7b69966e4ab0eddf07ace'
assert set(by_path) - set(historical) == {'verification/swift-cache-state-ci/README.md'}
assert not (set(historical) - set(by_path))
assert [p for p in historical if historical[p] != by_path[p]] == [test_path]
assert by_path[test_path] == {'path': test_path, 'bytes': 17857, 'sha256': TEST_SHA}
assert by_path['verification/swift-cache-state-ci/check_cache_state.py']['sha256'] == RUNNER_SHA
root_path = 'verification/github-delivery-ci-deadline-readiness/root-acceptance.json'
root_raw, root_blob = committed(root_path)
assert digest(root_raw)['sha256'] == 'f2952ea37193d0717bc44298d00928ae527c7043064432bc66fec25d6e80fe1e'
root = json.loads(root_raw)
assert root['status'] == 'accepted-test-only-stage-readiness-correction'
assert root['canonical_test_source'] == by_path[test_path]
assert root['production_runner'] == by_path['verification/swift-cache-state-ci/check_cache_state.py']
references = []
for key, expected, count in [
    ('producer_seal', '6e9f2ea669c9653e9ac5829243d95d5cf7216a922bd5672524dfcb8ed5b94849', 384),
    ('independent_packet', '95538d31b8d3d88310cd9eb5271a1a549efd3cdf7407ad4b735f3d7fcf71ce40', 31),
    ('independent_decision', 'f9f60dcfd839766837e6b366fcd7b073b0a7abb069d86bec2cc20d88609c0c90', None),
]:
    item = root[key]
    raw, blob = committed(item['path'])
    assert digest(raw) == {k: item[k] for k in ('bytes', 'sha256')} and item['sha256'] == expected
    value = json.loads(raw)
    if count is not None:
        assert value['member_count'] == len(value['members']) == count
    references.append({'role': key, **item, 'git_blob': blob, 'manifest_or_decision_only': True})
workflow_raw, workflow_blob = committed('.github/workflows/verify.yml')
assert digest(workflow_raw)['sha256'] == selection['workflow_sha256']
assert by_path['verification/swift-cache-state-ci/pack/manifest.json']['sha256'] == selection['pack_manifest_sha256']
assert selection['canonical_runner_sha256'] == RUNNER_SHA
comparison_raw, comparison_blob = committed('verification/swift-cache-state-ci-independent/corrected-review/final-decision.json')
assert comparison_raw == (PARENT / 'comparison-final-decision.json').read_bytes()

script_rows = []
for name in ('capture.py', 'collect.py', 'audit-content.py', 'finalize.py'):
    before = (PARENT / name).read_text()
    after = before
    if name in ('collect.py', 'audit-content.py'):
        assert all(old in after for old in (OLD_SHA, OLD_TREE, str(OLD_RUN)))
        after = after.replace(OLD_SHA, SHA).replace(OLD_TREE, TREE).replace(str(OLD_RUN), str(RUN))
    ast.parse(after, filename=name)
    assert not (HERE / name).exists()
    diff = ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile='parent/' + name, tofile='current/' + name))
    (HERE / name).write_text(after)
    (HERE / (name + '.diff')).write_text(diff)
    script_rows.append({'source': str((PARENT / name).relative_to(REPO)), 'source_digest': digest(before.encode()), 'target': str((HERE / name).relative_to(REPO)), 'adapted_digest': digest(after.encode()), 'diff_file': name + '.diff', 'diff_sha256': digest(diff.encode())['sha256']})

save('source-closure-preparation.json', {'source_revision': SHA, 'source_tree': TREE, 'canonical_paths': rows, 'canonical_git_blobs_verified': 91, 'historical_selection_sha256': SELECTION_SHA, 'historical_selection_git_blob': selection_blob, 'historical_selection_members': 90, 'unchanged_historical_members': 89, 'explicit_root_amended_members': 1, 'additional_README_members': 1, 'old_test_source': historical[test_path], 'new_test_source': by_path[test_path], 'root_acceptance': {'path': root_path, **digest(root_raw), 'git_blob': root_blob}, 'root_references': references, 'workflow': {**digest(workflow_raw), 'git_blob': workflow_blob}, 'comparison_decision': {**digest(comparison_raw), 'git_blob': comparison_blob}, 'historical_selection_rewritten': False, 'commands': calls, 'scope': 'Git object data read and hash only; no artifact fetch, extraction, import or execution; no CI polling, native/UI/capture/process inventory'})
save('script-sha256.json', script_rows)
save('preparation.json', {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'argv': sys.argv, 'python': sys.version, 'git_version': git_version, 'source_revision': SHA, 'source_tree': TREE, 'run_id': RUN, 'run_attempt': 1, 'run_url': f'https://github.com/snowdamiz/mixer/actions/runs/{RUN}', 'closed_parent_members_verified': 347, 'parent_seal': digest(seal_raw), 'parent_acceptance_sha256': PARENT_ACCEPTANCE, 'scripts': script_rows, 'source_closure': digest((HERE / 'source-closure-preparation.json').read_bytes()), 'preparer': digest(Path(__file__).read_bytes()), 'syntax_validation': 'ast.parse only; no prepared scripts imported or executed', 'execution_status': 'awaiting root exact-hash review and release; fixture job success required by collector', 'scope': 'Fresh exact-source data-only fixture audit preparation; parent historical selection and explicit test amendment preserved; no current collection or audit executed'})
print(json.dumps({'prepared': True, 'canonical_git_blobs_verified': 91, 'historical_unchanged': 89, 'explicit_test_amendments': 1, 'additional_README': 1, 'scripts': [{'name': Path(r['target']).name, **r['adapted_digest']} for r in script_rows], 'execution_authorized': False}))
