#!/usr/bin/env python3
"""Read-only inspection of the failed remote framing artifact; no execution."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import zipfile

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
sha = lambda raw: hashlib.sha256(raw).hexdigest()
download = json.loads((BASE / 'download-receipt.json').read_bytes())
commit = download['commit']
assert sha((BASE / 'artifact.zip').read_bytes()) == download['archive_sha256']
with zipfile.ZipFile(BASE / 'artifact.zip') as archive:
    names = archive.namelist()
    assert len(names) == len(set(names)) == 57
    assert all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in names)
    receipt = json.loads(archive.read('receipt.json'))
    assert receipt['result'] == 'failed'
    assert receipt['revision_before'] == receipt['revision_after'] == commit
    assert receipt['frozen_tree_sha256'] == receipt['frozen_after_tree_sha256']
    assert receipt['frozen_packets_unchanged']
    assert not receipt['fullReplayAccepted'] and not receipt['storedPrefixValidated']
    assert len(receipt['selected_closure']) == 38
    expected = {'receipt.json', 'ownership.json', 'source/collector.py', receipt['test_only_appended_source']['path']}
    for source, row in receipt['selected_closure'].items():
        raw = archive.read(row['snapshot'])
        assert len(raw) == row['bytes'] and sha(raw) == row['sha256']
        assert sha(subprocess.check_output(['git', 'show', commit + ':' + source], cwd=ROOT)) == row['sha256']
        expected.add(row['snapshot'])
    assert sha(archive.read('source/collector.py')) == receipt['collector_sha256'] == sha(subprocess.check_output(['git', 'show', commit + ':scripts/ci/check-analyzer-framing.py'], cwd=ROOT))
    assert sha(archive.read(receipt['test_only_appended_source']['path'])) == receipt['test_only_appended_source']['sha256'] == '7d49836d83db32854172a0f399aa1b4fe9409b724c80abb4b531d8a930eb7747'
    failures = []
    for row in receipt['commands']:
        assert row['child_returned'] and not row['timed_out']
        command_path = 'commands/' + row['name'] + '.json'
        expected.add(command_path)
        assert json.loads(archive.read(command_path)) == row
        for stream in ('stdout', 'stderr'):
            raw = archive.read(row[stream]['path'])
            assert len(raw) == row[stream]['bytes'] and sha(raw) == row[stream]['sha256']
            expected.add(row[stream]['path'])
        if row['exit'] != 0:
            failures.append(row['name'])
    assert failures == ['library-compile'] and receipt.get('passed_methods', 0) == 0
    assert receipt['cleanup']['removed'] and receipt['cleanup']['children_returned_before_cleanup']
    assert receipt['cleanup']['retained_test_files'] == {}
    assert set(names) == expected
    assert receipt['rustc']['path'].endswith('/rustup-init')
    assert receipt['rustc']['version_verbose'].startswith('rustup-init ')
    for row in receipt['historical_sidecars']:
        assert row['historical_sidecar'] == {'status': 'invalid', 'failure': 15}
print(json.dumps({
    'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
    'command': ['python3', '-B', str(Path(__file__).relative_to(ROOT))],
    'python': platform.python_version(), 'script_sha256': sha(Path(__file__).read_bytes()),
    'commit': commit, 'run': 40244180264, 'archive_sha256': download['archive_sha256'],
    'artifact_members_verified': 57, 'selected_sources_verified_against_commit': 38,
    'recorded_command_outputs_verified': len(receipt['commands']),
    'historical_sidecars_unchanged': 17, 'failed_command': 'library-compile',
    'rust_methods_executed': 0, 'remote_cleanup_reported': receipt['cleanup'],
    'root_artifact_extracted_or_executed': False,
    'storedPrefixValidated': False, 'fullReplayAccepted': False,
}, indent=2))
