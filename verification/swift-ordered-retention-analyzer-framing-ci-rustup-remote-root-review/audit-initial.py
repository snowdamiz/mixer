#!/usr/bin/env python3
"""Read-only root review of the repaired remote framing evidence."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / 'verification/swift-ordered-retention-analyzer-framing-ci-rustup-remote'
COMMIT = '05c1ebf0378fb479ba8595d71cde577f447d0025'
SEAL = '1d5639409f05e22446f20fa022d024dd303fd56cba1646242bf790a16b1eba3c'
APPEND = '7d49836d83db32854172a0f399aa1b4fe9409b724c80abb4b531d8a930eb7747'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(value, label):
    if not value:
        raise ValueError(label)


def git(path):
    return subprocess.check_output(['git', 'show', COMMIT + ':' + path], cwd=ROOT)


seal_raw = (PACKET / 'seal.json').read_bytes()
require(sha(seal_raw) == SEAL, 'seal digest')
seal = json.loads(seal_raw)
require(len(seal['members']) == 81 and sum(x['bytes'] for x in seal['members']) == 1020397, 'seal totals')
for row in seal['members']:
    path = ROOT / row['path']
    require(not path.is_symlink() and path.is_file(), 'sealed member type')
    raw = path.read_bytes()
    require(len(raw) == row['bytes'] and sha(raw) == row['sha256'], row['path'])
download = json.loads((PACKET / 'download-receipt.json').read_bytes())
archive_raw = (PACKET / 'artifact.zip').read_bytes()
require(sha(archive_raw) == download['archive_sha256'], 'archive digest')
require(download['artifact']['digest'] == 'sha256:' + sha(archive_raw), 'API archive digest')
require(download['artifact']['workflow_run']['head_sha'] == COMMIT, 'API commit')
require(download['artifact']['workflow_run']['id'] == 40247799000, 'API run')
with zipfile.ZipFile(PACKET / 'artifact.zip') as archive:
    names = archive.namelist()
    require(len(names) == len(set(names)) == 78, 'unique artifact members')
    require(all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in names), 'artifact paths')
    receipt_raw = archive.read('receipt.json')
    require(receipt_raw == (PACKET / 'remote-receipt.json').read_bytes(), 'receipt copy')
    receipt = json.loads(receipt_raw)
    require(receipt['result'] == 'passed' and not receipt['errors'], 'remote result')
    require(receipt['revision_before'] == receipt['revision_after'] == COMMIT, 'revisions')
    require(not receipt['fullReplayAccepted'] and not receipt['storedPrefixValidated'], 'withheld authority')
    require(receipt['frozen_packets_unchanged'] and receipt['frozen_tree_sha256'] == receipt['frozen_after_tree_sha256'], 'frozen observation')
    require(len(receipt['selected_closure']) == 38, 'source closure count')
    expected = {'receipt.json', 'ownership.json', 'source/collector.py', receipt['test_only_appended_source']['path']}
    for source, row in receipt['selected_closure'].items():
        raw = archive.read(row['snapshot'])
        require(len(raw) == row['bytes'] and sha(raw) == row['sha256'] and raw == git(source), 'selected source ' + source)
        expected.add(row['snapshot'])
    require(archive.read('source/collector.py') == git('scripts/ci/check-analyzer-framing.py'), 'executed collector')
    require(sha(archive.read('source/collector.py')) == receipt['collector_sha256'], 'collector digest')
    require(sha(archive.read(receipt['test_only_appended_source']['path'])) == receipt['test_only_appended_source']['sha256'] == APPEND, 'exact appended suite')
    commands = receipt['commands']
    require([r['name'] for r in commands] == ['revision-before', 'rustc-sysroot', 'rust-version', 'python-version', 'library-compile', 'test-compile', 'test-list', 'test-execute', 'revision-after'], 'command closure')
    for row in commands:
        require(row['exit'] == 0 and row['child_returned'] and not row['timed_out'], 'command result')
        path = 'commands/' + row['name'] + '.json'
        require(json.loads(archive.read(path)) == row, 'command receipt')
        expected.add(path)
        for stream in ('stdout', 'stderr'):
            raw = archive.read(row[stream]['path'])
            require(len(raw) == row[stream]['bytes'] and sha(raw) == row[stream]['sha256'], 'command output')
            expected.add(row[stream]['path'])
    by_name = {r['name']: r for r in commands}
    launcher, compiler = receipt['rustc_launcher'], receipt['rustc']
    require(by_name['rustc-sysroot']['argv'] == [launcher['path'], '--print', 'sysroot'], 'lexical launcher invocation')
    require(by_name['rustc-sysroot']['environment_overrides'] == {'RUSTUP_AUTO_INSTALL': '0'}, 'no toolchain install')
    require(launcher['path'] == '/Users/runner/.cargo/bin/rustc' and launcher['resolved_path'] == '/opt/homebrew/Cellar/rustup/1.29.0/bin/rustup-init', 'actual remote launcher chain')
    require(archive.read('commands/rustc-sysroot.stdout').decode().strip() == compiler['sysroot'], 'sysroot output')
    require(compiler['path'] == compiler['sysroot'] + '/bin/rustc', 'actual compiler selection')
    version = archive.read('commands/rust-version.stdout').decode()
    require(version == compiler['version_verbose'] and version.startswith('rustc 1.98.1 ') and '\nbinary: rustc\n' in version and '\nhost: aarch64-apple-darwin\n' in version, 'actual compiler identity')
    for name in ('rust-version', 'library-compile', 'test-compile'):
        require(by_name[name]['argv'][0] == compiler['path'], 'resolved compiler invocation')
    for name in ('library-compile', 'test-compile'):
        require('-Dwarnings' in by_name[name]['argv'], 'warnings gate')
    frozen = git('verification/swift-ordered-retention-analyzer-library-review/commands/run-2/execute.stdout').decode()
    expected_names = [line[5:].split(' ... ')[0] for line in frozen.splitlines() if line.startswith('test ') and ' ... ' in line]
    actual = archive.read('commands/test-execute.stdout').decode()
    actual_names = [line[5:].split(' ... ')[0] for line in actual.splitlines() if line.startswith('test ') and line.endswith(' ... ok')]
    listed = [line[:-6] for line in archive.read('commands/test-list.stdout').decode().splitlines() if line.endswith(': test')]
    require(len(expected_names) == len(actual_names) == len(listed) == len(set(actual_names)) == 44, '44 executed names')
    require(set(expected_names) == set(actual_names) == set(listed) == set(receipt['methods']), 'unchanged named suite')
    require('test result: ok. 44 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out;' in actual and receipt['passed_methods'] == 44, 'test summary')
    require(len(receipt['historical_sidecars']) == 17, 'sidecar count')
    for row in receipt['historical_sidecars']:
        require(row['historical_sidecar'] == {'status': 'invalid', 'failure': 15}, 'unchanged sidecar meaning')
    cleanup = receipt['cleanup']
    require(cleanup['removed'] and cleanup['children_returned_before_cleanup'] and not cleanup['other_processes_or_instances_queried'], 'owned cleanup')
    require(cleanup['marker'] == json.loads(archive.read('ownership.json')), 'ownership marker')
    require(len(cleanup['retained_test_files']) == 9, 'retained output count')
    for row in cleanup['retained_test_files'].values():
        raw = archive.read(row['path'])
        require(row['encoding'] == 'identity' and len(raw) == row['bytes'] == row['uncompressed_bytes'] and sha(raw) == row['sha256'] == row['uncompressed_sha256'], 'retained output')
        expected.add(row['path'])
    require(expected == set(names), 'complete member closure')
print(json.dumps({'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'python': platform.python_version(), 'script_sha256': sha(Path(__file__).read_bytes()), 'revision': COMMIT, 'command': ['python3', '-B', str(Path(__file__).relative_to(ROOT))], 'sealed_members_verified': 81, 'sealed_bytes': 1020397, 'artifact_members_verified': 78, 'artifact_sha256': sha(archive_raw), 'selected_sources_verified_against_git': 38, 'command_outputs_verified': 9, 'retained_outputs_verified': 9, 'historical_sidecars_unchanged': 17, 'passed_methods': 44, 'ignored_or_filtered': 0, 'remote_rustc': compiler['identity'], 'remote_python': receipt['python'], 'remote_cleanup_reported': True, 'artifact_extracted_or_executed': False, 'product_executed_by_root': False, 'overall_CI_qualified': False, 'storedPrefixValidated': False, 'fullReplayAccepted': False}, indent=2))
