"""Prepare five exact-source data-only terminal audit scripts; run no phase."""
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
PARENT = REPO / 'verification/github-delivery-ci-deadline-readiness/terminal-artifact-audit'
FIXTURE = REPO / 'verification/github-delivery-selected-adoption-descriptor-review/fixture-artifact-audit'
SHA = '43cbfb9c925e2ee7de43afd92bd588edb7ff60b6'
TREE = '93cc6868f445fa98c170acf771db73e50d90b4e2'
RUN = 40450561458
OLD_SHA = '606c42876855897c315ee279dcd38fabaeb561ad'
OLD_TREE = '6e7ef189ea796effb2099eff927436bd407a080b'
OLD_RUN = 40447941540
FIXTURE_ACCEPTANCE = '3d8ed9afce6751cb05e0f2b89927ddbea3738dd5da102926dee6818fb321732c'
FIXTURE_SEAL = '179c574f004a4bf0e48d36bab3cb929e9fde6bb145769fe97031125e9cbc0ed7'
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
        path = Path(row['path'])
        assert not path.is_absolute() and '..' not in path.parts and str(path) == row['path']
        source = root / path
        assert source.is_file() and not source.is_symlink()
        assert digest(source.read_bytes()) == {k: row[k] for k in ('bytes', 'sha256')}
    assert sum(r['bytes'] for r in seal['members']) == seal['total_bytes']
    assert {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()} == {r['path'] for r in seal['members']} | {'seal.json'}
    return raw, seal


parent_raw, parent = verify_packet(PARENT, '5ada08b6afd006aeb8abd2d23084f44cb6da74903416ee6809375cc9bdcc0911', 120)
assert digest((PARENT / 'acceptance.json').read_bytes())['sha256'] == '88c17ab82007dea7376eea869929a592f390121c440bbea42fb8176be09c1961'
fixture_raw, fixture = verify_packet(FIXTURE, FIXTURE_SEAL, 344)
fixture_acceptance_raw = (FIXTURE / 'acceptance.json').read_bytes()
assert digest(fixture_acceptance_raw)['sha256'] == fixture['acceptance_sha256'] == FIXTURE_ACCEPTANCE
accepted_fixture = json.loads(fixture_acceptance_raw)
assert accepted_fixture['source_revision'] == SHA and accepted_fixture['source_tree'] == TREE and accepted_fixture['run_id'] == RUN
amended = accepted_fixture['source_amendment']
assert amended['historical_selection_members'] == 90 and amended['unchanged_historical_members'] == 89
assert amended['explicit_root_amended_members'] == amended['additional_README_members'] == 1 and amended['committed_canonical_paths'] == 91
assert not amended['historical_selection_rewritten'] and not amended['new_test_source_executed_by_audit']

calls = []


def git(*args, input_bytes=None, retain_text=False):
    argv = ['git', *args]
    child = subprocess.Popen(argv, cwd=REPO, stdin=subprocess.PIPE if input_bytes is not None else subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    timed_out = False
    try:
        stdout, stderr = child.communicate(input=input_bytes, timeout=55)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(child.pid, signal.SIGKILL)
        stdout, stderr = child.communicate(timeout=4)
    group_gone = False
    try:
        os.killpg(child.pid, 0)
    except ProcessLookupError:
        group_gone = True
    row = {'argv': argv, 'cwd': str(REPO), 'exit_code': child.returncode, 'timed_out': timed_out,
           'pid': child.pid, 'pgid': child.pid, 'new_session': True, 'child_reaped': child.poll() is not None,
           'owned_group_gone': group_gone, 'child_limit_seconds': 55, 'stdout': digest(stdout), 'stderr': digest(stderr),
           'scope': 'Read-only Git object data and identity; no source import or execution'}
    if input_bytes is not None:
        row['stdin'] = digest(input_bytes)
    if retain_text:
        row['stdout_text'] = stdout.decode()
    calls.append(row)
    assert not timed_out and child.returncode == 0 and not stderr and group_gone, row
    return stdout


git_version = git('--version', retain_text=True).decode().strip()
assert git('rev-parse', SHA + '^{tree}', retain_text=True).decode().strip() == TREE
source_sets = {}
all_sources = {}
for name, path, count in [('core-jvm', 'source-blobs.json', 203), ('capability', 'capability/source-blobs.json', 313)]:
    raw = (PARENT / path).read_bytes()
    rows = json.loads(raw)
    assert len(rows) == count
    for source, row in rows.items():
        path_item = Path(source)
        assert not path_item.is_absolute() and '..' not in path_item.parts and str(path_item) == source
        assert not any(s in source.lower() for s in ('hostedcatalog', 'hosted-catalog', 'authority-driver', 'rejectedworker', 'hosted-harness', 'stopped-android', 'android-v5', 'androidv5'))
        assert source not in all_sources or all_sources[source] == row
        all_sources[source] = row
    source_sets[name] = {'path': str((PARENT / path).relative_to(REPO)), **digest(raw), 'members': count}
paths = sorted(all_sources)
tree_data = git('ls-tree', '-r', '-z', SHA, '--', *paths, retain_text=True)
current = {}
for item in tree_data.split(b'\0'):
    if not item:
        continue
    properties, path_item = item.split(b'\t', 1)
    mode, kind, blob = properties.decode().split()
    path = path_item.decode()
    assert mode in ('100644', '100755') and kind == 'blob' and path not in current
    current[path] = {'git_blob': blob, 'git_mode': mode}
assert set(current) == set(all_sources)
assert all(current[path]['git_blob'] == row['git_blob'] for path, row in all_sources.items())
assert git('diff', '--name-status', OLD_SHA, SHA, '--', *paths, retain_text=True) == b''
batch_request = ''.join(current[path]['git_blob'] + '\n' for path in paths).encode()
batch = git('cat-file', '--batch', input_bytes=batch_request)
offset = 0
for path in paths:
    end = batch.index(b'\n', offset)
    blob, kind, size = batch[offset:end].decode().split()
    assert blob == current[path]['git_blob'] and kind == 'blob'
    offset = end + 1
    payload = batch[offset:offset + int(size)]
    assert len(payload) == int(size) and batch[offset + int(size):offset + int(size) + 1] == b'\n'
    offset += int(size) + 1
    assert hashlib.sha1(b'blob ' + str(len(payload)).encode() + b'\0' + payload).hexdigest() == blob
    assert digest(payload) == {k: all_sources[path][k] for k in ('bytes', 'sha256')}
assert offset == len(batch)
workflow = git('show', SHA + ':.github/workflows/verify.yml')
assert digest(workflow)['sha256'] == '7f3ab7ef5ec94379a969c91e9f2348cecd2e80908c8a7330aef845f133f38e62'
assert git('diff', '--name-status', OLD_SHA, SHA, '--', '.github/workflows/verify.yml', retain_text=True) == b''

scripts = []
adaptations = []
for name in ('audit.py', 'capability_review.py', 'phases.py', 'run-reviewed.py', 'freeze.py'):
    original = (PARENT / name).read_text()
    text = original.replace(OLD_SHA, SHA).replace(OLD_TREE, TREE).replace(str(OLD_RUN), str(RUN))
    if name == 'phases.py':
        replacements = {
            'verification/github-delivery-ci-deadline-readiness/fixture-artifact-audit': str(FIXTURE.relative_to(REPO)),
            '2e9935e38029160b779761c94946805fcb8d71563c6929aa65ceecc56885c59e': FIXTURE_ACCEPTANCE,
            'e681cda4c2140aeee119d4c7b6ac223859df822e2671a80d90ed030102386c3f': FIXTURE_SEAL,
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
polling_raw = (PARENT / 'polling-diagnostic-limits.json').read_bytes()
polling = json.loads(polling_raw)
assert digest(polling_raw)['sha256'] == '29853dda8c7d1165d5e8f52b78aca449e4411a3de2da34a62ce7b6d8b26b6bd9'
assert polling['failed_poll_evaluators'] == 1 and not polling['failure_is_CI_failure']
save('historical-context.json', {'parent_terminal_packet': str(PARENT.relative_to(REPO)), 'parent_seal': digest(parent_raw), 'historical_collector': {'copied_path': 'prior-failure.json', 'digest': digest(prior_failure), 'descendant_reaping_verified': False, 'replayed': False}, 'historical_poll_evaluator': {'parent_limits_path': str((PARENT / 'polling-diagnostic-limits.json').relative_to(REPO)), 'parent_limits': digest(polling_raw), 'failed_count': 1, 'failed_evaluator': polling['failed_evaluator'], 'historical_only': True, 'current_run_failure': False, 'copied_or_replayed_poller': False, 'accepted_terminal_or_phase_provenance': False}, 'scope': 'Historical parent diagnostics retained separately from this fresh run; root owns current CI polling; no polling tool is copied or executed'})
save('source-binding-preparation.json', {'source_revision': SHA, 'source_tree': TREE, 'prior_revision': OLD_SHA, 'parent_source_manifests': source_sets, 'unchanged_unique_source_paths': len(all_sources), 'source_blobs': all_sources, 'current_git_modes_and_blobs': current, 'current_git_blob_identity_verified': True, 'current_git_blob_bytes_sha1_sha256_verified': len(paths), 'selected_source_path_content_or_mode_changes': 0, 'workflow': digest(workflow), 'commands': calls, 'scope': 'Each selected canonical source blob read with git cat-file and rehashed; prior bytes and blob identities unchanged at exact new commit; no source import/execution or audit phase'})
save('fixture-binding-preparation.json', {'path': str(FIXTURE.relative_to(REPO)), 'source_revision': SHA, 'source_tree': TREE, 'run_id': RUN, 'seal': digest(fixture_raw), 'acceptance': digest(fixture_acceptance_raw), 'sealed_members_verified': 344, 'sealed_bytes_verified': fixture['total_bytes'], 'source_amendment': amended, 'scope': 'Current separately frozen fixture packet verified without modification or rerun'})
save('script-sha256.json', scripts)
save('preparation.json', {'schema': 3, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'argv': sys.argv, 'python': sys.version, 'git_version': git_version, 'source_revision': SHA, 'source_tree': TREE, 'run_id': RUN, 'run_attempt': 1, 'parent_seal': digest(parent_raw), 'closed_parent_members_verified': 120, 'closed_parent_bytes_verified': parent['total_bytes'], 'execution_scripts': scripts, 'adaptations': adaptations, 'static_data': [{'path': 'prior-failure.json', 'digest': digest(prior_failure), 'copied_unchanged': True}, {'path': 'historical-context.json', 'digest': digest((HERE / 'historical-context.json').read_bytes()), 'historical_only': True}], 'source_binding_preparation': digest((HERE / 'source-binding-preparation.json').read_bytes()), 'fixture_binding_preparation': digest((HERE / 'fixture-binding-preparation.json').read_bytes()), 'preparer': digest(Path(__file__).read_bytes()), 'bounds': 'Five independently bounded 60 second phases; own child process group reaping; no broad inventory', 'selection': 'Accepted five execution scripts unchanged except exact source commit/tree/run and separately frozen current fixture constants; historical failure truth retained', 'syntax_validation': 'ast.parse only; prepared scripts not imported or executed', 'prohibited_activity': 'No artifact execution/import/extraction; no native/UI/capture/process inventories; no forbidden hosted/stopped harness, Git changes or CI retries', 'execution_status': 'Awaiting explicit root exact-script release and confirmed six passing jobs / 64 passing steps', 'current_execution_or_terminal_acceptance': False})
print(json.dumps({'prepared': True, 'parent_members_verified': 120, 'fixture_members_verified': 344, 'source_manifests': {'core_jvm': 203, 'capability': 313}, 'unique_source_blob_bytes_verified': len(all_sources), 'scripts': scripts, 'execution_authorized': False}))
