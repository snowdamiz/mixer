#!/usr/bin/env python3
"""Read-only root audit of the exact framing CI handoff; no product execution."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'verification/swift-ordered-retention-analyzer-framing-ci-rustup'
EXPECTED = '34439af3a4ffaad630ff51409dcedc30942f0ec29cacd72e20241a44f8776d78'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(path, row):
    assert path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(ROOT)
    assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], str(path)


assert sha(BASE / 'seal.json') == EXPECTED
assert (BASE / 'seal.sha256').read_text().split()[0] == EXPECTED
seal = json.loads((BASE / 'seal.json').read_bytes())
assert len(seal['members']) == len({r['path'] for r in seal['members']}) == 186
assert sum(r['bytes'] for r in seal['members']) == 6_889_318
for row in seal['members']:
    check(ROOT / row['path'], row)
handoff = json.loads((BASE / 'handoff.json').read_bytes())
for name, row in handoff['source_files'].items():
    check(ROOT / name, row)
    check(ROOT / row['snapshot'], row)
local = BASE / 'local-default-darwin-2'
receipt = json.loads((local / 'receipt.json').read_bytes())
assert sha(local / 'receipt.json') == handoff['actual_selected_execution']['receipt_sha256']
assert receipt['result'] == 'passed' and receipt['errors'] == []
assert receipt['passed_methods'] == len(set(receipt['methods'])) == 44
assert receipt['system'] == 'Darwin' and receipt['machine'] == 'arm64'
assert receipt['frozen_packets_unchanged'] is True
assert receipt['frozen_tree_sha256'] == receipt['frozen_after_tree_sha256']
assert receipt['storedPrefixValidated'] is False and receipt['fullReplayAccepted'] is False
assert receipt['native_capture_or_device_execution'] is False
total = 0
for packet, state in receipt['frozen_before'].items():
    assert sha(ROOT / packet / 'seal.json') == state['seal_sha256']
    assert sha(ROOT / packet / 'seal.sha256') == state['seal_sidecar_sha256']
    for name, row in state['members'].items():
        check(ROOT / name, row)
        total += 1
assert total == 894
assert len(receipt['selected_closure']) == 38
for source, row in receipt['selected_closure'].items():
    check(ROOT / source, row)
    check(local / row['snapshot'], row)
append = receipt['test_only_appended_source']
assert sha(local / append['path']) == append['sha256'] == '7d49836d83db32854172a0f399aa1b4fe9409b724c80abb4b531d8a930eb7747'
assert (local / append['path']).read_bytes() == (local / 'source/original/analyzer.rs').read_bytes() + b'\n' + (local / 'source/original/private_io_tests.rs').read_bytes()
for command in receipt['commands']:
    assert command['exit'] == 0 and command['child_returned'] and not command['timed_out']
    for stream in ('stdout', 'stderr'):
        check(local / command[stream]['path'], command[stream])
assert '44 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out' in (local / 'commands/test-execute.stdout').read_text()
assert sha(Path(receipt['rustc']['path'])) == receipt['rustc']['sha256']
cleanup = receipt['cleanup']
assert cleanup['removed'] and cleanup['children_returned_before_cleanup']
assert not Path(cleanup['path']).exists()
for row in cleanup['retained_test_files'].values():
    check(local / row['path'], row)
assert len(receipt['historical_sidecars']) == 17
for row in receipt['historical_sidecars']:
    assert row['historical_sidecar'] == {'status': 'invalid', 'failure': 15}
for name in ('runner-tests-1', 'workflow-unchanged', 'history-postflight-and-syntax', 'diff-check', 'local-default-closure-2'):
    folder = BASE / 'commands' / name
    result = json.loads((folder / 'result.json').read_bytes())
    assert result['exit'] == 0
    for stream in ('stdout', 'stderr'):
        assert sha(folder / stream) == result[stream + '_sha256']
assert 'Ran 16 tests' in (BASE / 'commands/runner-tests-1/stderr').read_text()
assert (ROOT / '.github/workflows/verify.yml').read_bytes() == subprocess.check_output(['git', 'show', handoff['revision'] + ':.github/workflows/verify.yml'], cwd=ROOT)
old_base = ROOT / 'verification/swift-ordered-retention-analyzer-framing-ci'
assert sha(old_base / 'seal.json') == '2175ba4d989c42261ae18352305e267c7dd3d7538fb5c8fdb844ea5a6f484ed6'
old_rows = json.loads((old_base / 'seal.json').read_bytes())['members']
assert len(old_rows) == 108
for row in old_rows:
    path = ROOT / row['path']
    if path.is_relative_to(old_base):
        check(path, row)
    else:
        raw = subprocess.check_output(['git', 'show', handoff['revision'] + ':' + row['path']], cwd=ROOT)
        assert len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256']
actual = json.loads((BASE / 'commands/local-default-closure-2/result.json').read_bytes())
assert '--rustc' not in actual['argv'] and actual['exit'] == 0 and actual['child_returned']
assert actual['owned_shim_cleanup']['removed'] and actual['owned_shim_cleanup']['only_exact_owned_tree']
assert not Path(actual['owned_shim_chain']['ownership']['path']).exists()
assert actual['owned_shim_chain']['source_sha256'] == actual['owned_shim_chain']['copied_sha256']
assert sha(Path(actual['owned_shim_chain']['source_binary'])) == actual['owned_shim_chain']['source_sha256']
assert receipt['rustc_launcher']['original_invocation_path_preserved']
assert receipt['rustc_launcher']['resolved_path'].endswith('/rustup-init')
query = next(c for c in receipt['commands'] if c['name'] == 'rustc-sysroot')
assert query['argv'] == [receipt['rustc_launcher']['path'], '--print', 'sysroot']
assert query['environment_overrides']['RUSTUP_AUTO_INSTALL'] == '0'
assert receipt['rustc']['identity']['host'] == 'aarch64-apple-darwin'
first = json.loads((BASE / 'local-default-darwin-1/receipt.json').read_bytes())
assert first['result'] == 'failed' and first.get('passed_methods', 0) == 0
assert not first['cleanup']['created']
assert not (BASE / 'owned-shim-scratch-1').exists()
assert sha(BASE / 'first-ci/artifact.zip') == handoff['first_remote_framing_run']['artifact_sha256'] == '165c0071c73c1fa5c9607a8d7995eabf1833578f3924f005c988806884fc82d3'
for name in ('scripts/ci/check-analyzer-framing.py', 'scripts/ci/tests/test_analyzer_framing_runner.py'):
    ast.parse((ROOT / name).read_text(), filename=name)
print(json.dumps({
    'at': datetime.now(timezone.utc).isoformat(), 'schema': 1,
    'command': ['python3', '-B', str(Path(__file__).relative_to(ROOT))],
    'python': platform.python_version(), 'script_sha256': sha(Path(__file__)),
    'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'seal_sha256': EXPECTED, 'members_verified': 186, 'bytes_verified': 6889318,
    'frozen_members_unchanged': total, 'selected_sources_verified': 38,
    'recorded_methods': 44, 'focused_runner_controls': 16,
    'existing_workflow_unchanged': True, 'cleanup_verified': True, 'historical_108_members_verified': True, 'first_remote_and_local_failures_preserved': True,
    'product_execution_by_root': False, 'scope': 'Root source and evidence review for rustup launcher dispatch repair',
    'verdict': 'accepted-for-authorized-delivery-remote-ci-pending',
    'storedPrefixValidated': False, 'fullReplayAccepted': False,
    'linux_qualified': False, 'ga_gates_promoted': 0,
}, indent=2))
