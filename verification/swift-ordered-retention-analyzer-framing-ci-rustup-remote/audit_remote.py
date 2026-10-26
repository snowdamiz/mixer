"""Audit one exact framing artifact as data; never import or execute its source."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import platform
import stat
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent
COMMIT = '05c1ebf0378fb479ba8595d71cde577f447d0025'
BASELINE = '4af8b7e1e451077aefc5ffbb213f84bf1b3d02e2'
PRODUCER = 'verification/swift-ordered-retention-analyzer-library'
REVIEW = 'verification/swift-ordered-retention-analyzer-library-review'


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def tree_digest(value):
    return digest(json.dumps(value, sort_keys=True, separators=(',', ':')).encode())


def main():
    download = json.loads((OWN / 'download-receipt.json').read_text())
    require(download['commit'] == COMMIT and download['run'] == 40247799000, 'Wrong artifact selection')
    archive = OWN / 'artifact.zip'
    require(digest(archive.read_bytes()) == download['archive_sha256']
            == 'a67d36f65202dea55318beedeb0ee873e7b79de1b32f2df859cfdea99d263c92', 'Archive digest differs')
    expected_root = OWN / 'expected-git'
    expected_root.mkdir()
    git_commands, git_cache = [], {}

    def git_blob(path, revision=COMMIT):
        key = revision + ':' + path
        if key in git_cache:
            return git_cache[key]
        argv = ['git', 'show', key]
        result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=15)
        require(result.returncode == 0, 'Git blob unavailable: ' + key)
        row = {'argv': argv, 'cwd': str(ROOT), 'exit': result.returncode,
               'stdout_bytes': len(result.stdout), 'stdout_sha256': digest(result.stdout),
               'stderr_sha256': digest(result.stderr)}
        git_commands.append(row)
        if revision == COMMIT:
            destination = expected_root / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(result.stdout)
        git_cache[key] = result.stdout
        return result.stdout

    with zipfile.ZipFile(archive) as zipped:
        entries = zipped.infolist()
        names = [entry.filename for entry in entries]
        require(len(names) == len(set(names)) == 78, 'Unexpected artifact member inventory')
        require(sum(entry.file_size for entry in entries) < 8 * 1024 * 1024, 'Artifact exceeds scoped byte bound')
        artifact_members = []
        for entry in entries:
            path = PurePosixPath(entry.filename)
            require(not path.is_absolute() and '..' not in path.parts and not any(part.startswith('.') for part in path.parts),
                    'Unsafe or hidden member: ' + entry.filename)
            require(not entry.is_dir() and not stat.S_ISLNK(entry.external_attr >> 16), 'Unexpected directory or link member')
            raw = zipped.read(entry)
            artifact_members.append({'path': entry.filename, 'bytes': len(raw), 'sha256': digest(raw)})
        receipt_bytes = zipped.read('receipt.json')
        receipt = json.loads(receipt_bytes)
        require(receipt['revision_before'] == receipt['revision_after'] == COMMIT, 'Remote revision differs')
        require(receipt['result'] == 'passed' and receipt['passed_methods'] == 44 and receipt['errors'] == [], 'Remote check did not pass')
        require(receipt['storedPrefixValidated'] is False and receipt['fullReplayAccepted'] is False,
                'Remote receipt grants unsupported acceptance')
        require(receipt['system'] == 'Darwin' and receipt['machine'] == 'arm64', 'Unexpected remote host')
        require(receipt['native_capture_or_device_execution'] is False, 'Unexpected native scope')
        selection = receipt['selected_closure']
        require(len(selection) == 38, 'Selected source count differs')
        sources = []
        for source, row in sorted(selection.items()):
            raw = zipped.read(row['snapshot'])
            expected = git_blob(source)
            require(raw == expected == git_blob(source, BASELINE), 'Selected source changed: ' + source)
            require(len(raw) == row['bytes'] and digest(raw) == row['sha256'], 'Selected source receipt differs')
            sources.append({'source': source, **row, 'matches_commit': COMMIT, 'unchanged_from': BASELINE})
        require(tree_digest(selection) == receipt['selected_tree_sha256'], 'Selected tree digest differs')
        collector = git_blob('scripts/ci/check-analyzer-framing.py')
        require(zipped.read('source/collector.py') == collector and digest(collector) == receipt['collector_sha256']
                == '8e51065e0666c71260d947ad1168c87f036de0e392191555b3faba8f1d6cb837', 'Executed collector differs')
        append = git_blob(PRODUCER + '/src/analyzer.rs') + b'\n' + git_blob(REVIEW + '/private_io_tests.rs')
        require(zipped.read('source/inputs/framing.rs') == append
                == git_blob(REVIEW + '/commands/run-2/inputs/framing.rs'), 'Appended private suite differs')
        require(digest(append) == receipt['test_only_appended_source']['sha256']
                == '7d49836d83db32854172a0f399aa1b4fe9409b724c80abb4b531d8a930eb7747', 'Appended suite hash differs')
        frozen_before = receipt['frozen_before']
        for packet, seal_digest, count in [(PRODUCER, '777e0a1b7a10d483bacb81475ad6c7af9a4d40fff64dd5ff2f3d893e1cd0fe63', 270),
                                           (REVIEW, 'a5e21463c820277e1857a7eebcecdc7e45f40857b9c1dd39e8741f9b06a1bd4e', 624)]:
            seal = git_blob(packet + '/seal.json')
            rows = json.loads(seal)['members']
            require(digest(seal) == seal_digest and len(rows) == count, 'Frozen seal differs')
            recorded = frozen_before[packet]
            require(recorded['seal_sha256'] == seal_digest
                    and recorded['members'] == {row['path']: {'bytes': row['bytes'], 'sha256': row['sha256']} for row in rows}
                    and recorded['seal_sidecar_sha256'] == digest(git_blob(packet + '/seal.sha256')),
                    'Remote frozen-member inventory differs from commit')
        require(receipt['frozen_packets_unchanged'] and tree_digest(frozen_before)
                == receipt['frozen_tree_sha256'] == receipt['frozen_after_tree_sha256'], 'Frozen before/after receipt differs')
        sidecars = []
        historical = [name for name in names if name.startswith('inputs/historical/') and name.endswith('.sidecar.json')]
        require(len(historical) == 17, 'Historical sidecar count differs')
        for name in sorted(historical):
            sidecar = json.loads(zipped.read(name))
            stream = zipped.read(name[:-13] + '.bin')
            require(sidecar['status'] == 'invalid' and sidecar['failure'] == 15
                    and sidecar['stream_sha256'] == digest(stream) and sidecar['stream_bytes'] == len(stream),
                    'Historical classification or join differs')
            sidecars.append({'path': name, 'status': 'invalid', 'failure': 15, 'stream_sha256': digest(stream)})
        commands = receipt['commands']
        require([row['name'] for row in commands] == ['revision-before', 'rustc-sysroot', 'rust-version', 'python-version',
                                                     'library-compile', 'test-compile', 'test-list', 'test-execute', 'revision-after'],
                'Unexpected command closure')
        for row in commands:
            require(row['exit'] == 0 and row['child_returned'] and not row['timed_out'], 'Remote command failed')
            require(json.loads(zipped.read('commands/' + row['name'] + '.json')) == row, 'Per-command receipt differs')
            for stream in ['stdout', 'stderr']:
                raw = zipped.read(row[stream]['path'])
                require(len(raw) == row[stream]['bytes'] and digest(raw) == row[stream]['sha256'], 'Command output differs')
        command_map = {row['name']: row for row in commands}
        launcher, compiler = receipt['rustc_launcher'], receipt['rustc']
        query = command_map['rustc-sysroot']
        require(launcher['original_invocation_path_preserved']
                and launcher['path'] == '/Users/runner/.cargo/bin/rustc'
                and launcher['resolved_path'] == '/opt/homebrew/Cellar/rustup/1.29.0/bin/rustup-init'
                and launcher['sha256'] == 'b54b2b2cdbf23377fd840d95be5fcea540b1f5c5529db0d0ee6afa96c861ff52'
                and query['argv'] == [launcher['path'], '--print', 'sysroot']
                and query['environment_overrides'] == {'RUSTUP_AUTO_INSTALL': '0'}, 'Unexpected launcher resolution')
        require(zipped.read(query['stdout']['path']).decode().strip() == compiler['sysroot']
                and compiler['path'] == compiler['sysroot'] + '/bin/rustc'
                and compiler['requested'] == 'rustc', 'Actual compiler selection differs')
        version = zipped.read('commands/rust-version.stdout').decode()
        require(version == compiler['version_verbose'] and version.startswith('rustc 1.98.1 ')
                and compiler['identity']['host'] == 'aarch64-apple-darwin'
                and compiler['identity']['release'] == '1.98.1'
                and 'binary: rustc\n' in version and '\nrelease: 1.98.1\n' in version, 'Actual rustc identity differs')
        for name in ['rust-version', 'library-compile', 'test-compile']:
            require(command_map[name]['argv'][0] == compiler['path'], 'Installer invoked as compiler')
        require('-Dwarnings' in command_map['library-compile']['argv']
                and '-Dwarnings' in command_map['test-compile']['argv'], 'Warnings gate changed')
        frozen_output = git_blob(REVIEW + '/commands/run-2/execute.stdout').decode()
        expected_names = [line[5:].split(' ... ')[0] for line in frozen_output.splitlines()
                          if line.startswith('test ') and ' ... ' in line]
        listing = zipped.read('commands/test-list.stdout').decode()
        listed = [line[:-6] for line in listing.splitlines() if line.endswith(': test')]
        output = zipped.read('commands/test-execute.stdout').decode()
        executed = [line[5:].split(' ... ')[0] for line in output.splitlines()
                    if line.startswith('test ') and ' ... ' in line]
        require(len(expected_names) == len(set(expected_names)) == len(listed) == len(executed) == 44
                and set(expected_names) == set(listed) == set(executed) == set(receipt['methods']), '44-method names differ')
        require('test result: ok. 44 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out;' in output
                and 'HISTORICAL_SIDECARS_INVALID=17 FOOTER_GRAMMAR_REFUSED=7 FOOTER_ONLY_OBSERVED=10' in output,
                'Exact pass or historical observation summary absent')
        cleanup = receipt['cleanup']
        require(cleanup['removed'] and cleanup['children_returned_before_cleanup']
                and not cleanup['other_processes_or_instances_queried']
                and cleanup['marker'] == json.loads(zipped.read('ownership.json')),
                'Cleanup receipt differs')
        retained = cleanup['retained_test_files']
        require(len(retained) == 9, 'Unexpected retained test file count')
        for row in retained.values():
            raw = zipped.read(row['path'])
            require(row['encoding'] == 'identity' and len(raw) == row['bytes'] == row['uncompressed_bytes']
                    and digest(raw) == row['sha256'] == row['uncompressed_sha256'], 'Retained output differs')
        expected_members = {'receipt.json', 'ownership.json', 'source/collector.py', 'source/inputs/framing.rs'}
        expected_members.update(row['snapshot'] for row in selection.values())
        expected_members.update('commands/' + row['name'] + '.json' for row in commands)
        expected_members.update(row[stream]['path'] for row in commands for stream in ['stdout', 'stderr'])
        expected_members.update(row['path'] for row in retained.values())
        require(set(names) == expected_members, 'Unexpected or missing artifact member')
    (OWN / 'remote-receipt.json').write_bytes(receipt_bytes)
    audit = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'argv': sys.argv,
             'auditor_sha256': digest(Path(__file__).read_bytes()), 'python': platform.python_version(),
             'run': 40247799000, 'commit': COMMIT, 'verdict': 'scoped-remote-Darwin-framing-CI-pass',
             'archive_sha256': download['archive_sha256'], 'artifact_members': artifact_members,
             'selected_source_count': 38, 'selected_sources': sources, 'selected_sources_unchanged_from': BASELINE,
             'collector_sha256': digest(collector), 'appended_suite_sha256': digest(append),
             'recorded_frozen_members_matching_commit_seals': 894,
             'frozen_members_before_after_unchanged_reported_by_remote_runner': True,
             'historical_sidecars': sidecars, 'expected_methods': sorted(expected_names), 'passed_methods': 44,
             'ignored_methods': 0, 'filtered_methods': 0, 'system': receipt['system'], 'machine': receipt['machine'],
             'remote_python': receipt['python'], 'launcher': launcher, 'compiler': compiler,
             'executable_hashes_are_remote_receipt_observations_not_downloaded_binary_rehashes': True,
             'command_count': len(commands), 'command_logs_hash_verified': True,
             'retained_test_files_hash_verified': 9, 'owned_scratch_removed_after_children_returned': True,
             'artifact_sources_imported_or_executed': False, 'local_product_runs': 0,
             'native_capture_or_process_discovery': False,
             'overall_workflow_acceptance': 'Root tracks separately; only framing and its artifact upload inspected',
             'storedPrefixValidated': False, 'fullReplayAccepted': False,
             'pending': ['Linux remains unselected/unqualified', 'All previously withheld semantic/adapter/custody/target/native/device/signing/store/customer/operations/published-package FieldLog/GA gates'],
             'git_commands': git_commands}
    (OWN / 'audit.json').write_text(json.dumps(audit, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'verdict': audit['verdict'], 'members': len(entries), 'selected_sources': 38,
                      'methods': 44, 'rustc': compiler['identity'], 'python': receipt['python'],
                      'cleanup': True, 'acceptance_flags': False}))


if __name__ == '__main__':
    main()
