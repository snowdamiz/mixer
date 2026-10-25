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
BASE = ROOT / 'verification/swift-ordered-retention-analyzer-framing-ci'
EXPECTED = '2175ba4d989c42261ae18352305e267c7dd3d7538fb5c8fdb844ea5a6f484ed6'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(path, row):
    assert path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(ROOT)
    assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], str(path)


assert sha(BASE / 'seal.json') == EXPECTED
assert (BASE / 'seal.sha256').read_text().strip() == EXPECTED
seal = json.loads((BASE / 'seal.json').read_bytes())
assert len(seal['members']) == len({r['path'] for r in seal['members']}) == 108
assert sum(r['bytes'] for r in seal['members']) == 5_905_147
for row in seal['members']:
    check(ROOT / row['path'], row)
handoff = json.loads((BASE / 'handoff.json').read_bytes())
for name, row in handoff['source_files'].items():
    check(ROOT / name, row)
    check(ROOT / row['snapshot'], row)
local = BASE / 'local-darwin-1'
receipt = json.loads((local / 'receipt.json').read_bytes())
assert sha(local / 'receipt.json') == handoff['local_selected_closure']['receipt_sha256']
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
for name in ('runner-tests-2', 'workflow-yaml', 'additive-integrity', 'diff-check'):
    folder = BASE / 'commands' / name
    result = json.loads((folder / 'result.json').read_bytes())
    assert result['exit'] == 0
    for stream in ('stdout', 'stderr'):
        assert sha(folder / stream) == result[stream + '_sha256']
assert 'Ran 13 tests' in (BASE / 'commands/runner-tests-2/stderr').read_text()
workflow = (ROOT / '.github/workflows/verify.yml').read_text()
start = workflow.index('      - name: Accepted standalone analyzer fixture framing\n')
end = workflow.index('      - name: Generated capability schema and host lifecycle\n', start)
base = subprocess.check_output(['git', 'show', handoff['revision'] + ':.github/workflows/verify.yml'], cwd=ROOT, text=True)
assert workflow[:start] + workflow[end:] == base
for name in ('scripts/ci/check-analyzer-framing.py', 'scripts/ci/tests/test_analyzer_framing_runner.py'):
    ast.parse((ROOT / name).read_text(), filename=name)
print(json.dumps({
    'at': datetime.now(timezone.utc).isoformat(), 'schema': 1,
    'command': ['python3', '-B', str(Path(__file__).relative_to(ROOT))],
    'python': platform.python_version(), 'script_sha256': sha(Path(__file__)),
    'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'seal_sha256': EXPECTED, 'members_verified': 108, 'bytes_verified': 5905147,
    'frozen_members_unchanged': total, 'selected_sources_verified': 38,
    'recorded_methods': 44, 'focused_runner_controls': 13,
    'existing_workflow_unchanged': True, 'cleanup_verified': True,
    'product_execution_by_root': False, 'scope': 'Root source and evidence review for narrow Darwin host CI wiring',
    'verdict': 'accepted-for-authorized-delivery-remote-ci-pending',
    'storedPrefixValidated': False, 'fullReplayAccepted': False,
    'linux_qualified': False, 'ga_gates_promoted': 0,
}, indent=2))
