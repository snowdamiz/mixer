#!/usr/bin/env python3
"""Offline artifact/source review only. Never imports or executes the runner."""
import hashlib
import json
import pathlib
import shutil
import stat
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timezone

BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[2]
COMMIT = '0b99469dfbeb06ac53ad0223bd070a35f2a6a700'
TREE = '1ec7b776bd1a910ad07a6f141acd6433b26799fa'
ZIP_SHA = '6d6edf35c709025b769144bffa94e83040d82321b5d818c97ffd64a58666b85b'
PREFIX = 'verification/swift-cache-state-ci/'
SELECTED = {
    'check_cache_state.py', 'test_runner.py', 'README.md', 'pack/manifest.json',
    'logs/host.stdout', 'logs/host.stderr',
    'logs/runner-controls.stdout', 'logs/runner-controls.stderr',
    'logs/deadline-postflight-control.json', 'logs/deadline-retention-control.json',
    'runs/host-resource-ci-repair-root-1/receipt.json',
}

def require(value, message):
    if not value:
        raise RuntimeError(message)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def write_json(name, value):
    with (BASE / name).open('x') as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True) + '\n')

def git(*args):
    result = subprocess.run(['git', '-c', 'gc.auto=0', *args], cwd=ROOT,
                            capture_output=True, timeout=10, check=True)
    return result.stdout

def main():
    started = time.monotonic()
    archive = BASE / 'artifact.zip'
    require(archive.stat().st_size == 1429194 <= 8 * 1024 * 1024, 'ZIP size binding/cap')
    require(digest(archive.read_bytes()) == ZIP_SHA, 'ZIP SHA binding')
    destination = BASE / 'selected'
    destination.mkdir()
    inventory, seen, folded, total = [], set(), set(), 0
    with zipfile.ZipFile(archive) as source:
        entries = source.infolist()
        require(len(entries) == 738 <= 1024, 'ZIP count binding/cap')
        require(sum(row.file_size for row in entries) <= 64 * 1024 * 1024,
                'Declared expanded bytes cap')
        for row in entries:
            name = row.filename
            path = pathlib.PurePosixPath(name)
            require(name and name == str(path) and not path.is_absolute()
                    and all(part not in {'.', '..', '.git'} for part in path.parts)
                    and '\\' not in name and '\x00' not in name,
                    'Unsafe ZIP path')
            require(name not in seen and name.casefold() not in folded, 'Duplicate ZIP path')
            seen.add(name)
            folded.add(name.casefold())
            mode = row.external_attr >> 16
            require(stat.S_IFMT(mode) in {0, stat.S_IFREG}, 'Nonregular ZIP entry')
            require(not row.is_dir() and not row.flag_bits & 1, 'Directory/encrypted ZIP entry')
            count, sha, retained = 0, hashlib.sha256(), []
            with source.open(row) as stream:
                while chunk := stream.read(1024 * 1024):
                    count += len(chunk)
                    total += len(chunk)
                    require(count <= row.file_size and total <= 64 * 1024 * 1024,
                            'Actual expanded bytes cap')
                    sha.update(chunk)
                    if name in SELECTED:
                        retained.append(chunk)
            require(count == row.file_size, 'ZIP expanded byte count differs')
            inventory.append({'path': name, 'bytes': count, 'sha256': sha.hexdigest(),
                              'crc32': f'{row.CRC:08x}', 'zip_datetime': list(row.date_time),
                              'classification': 'current-control-output' if name.startswith('logs/')
                              else 'copied-historical-run' if name.startswith('runs/')
                              else 'fixture-source-at-run'})
            if name in SELECTED:
                target = destination.joinpath(*path.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('xb') as stream:
                    stream.write(b''.join(retained))
        require(SELECTED <= seen, 'Selected evidence missing')
    require(git('rev-parse', COMMIT + '^{tree}').decode().strip() == TREE, 'Commit tree binding')
    bindings = []
    for name in ['check_cache_state.py', 'test_runner.py', 'README.md', 'pack/manifest.json',
                 'runs/host-resource-ci-repair-root-1/receipt.json']:
        committed = git('cat-file', 'blob', COMMIT + ':' + PREFIX + name)
        retained = (destination / name).read_bytes()
        require(committed == retained, 'Artifact/commit source binding: ' + name)
        local = ROOT / PREFIX / name
        bindings.append({'path': PREFIX + name, 'commit': COMMIT,
                         'bytes': len(committed), 'sha256': digest(committed),
                         'artifact_matches_commit': True,
                         'working_tree_matches_commit_at_review': local.read_bytes() == committed})
    workflow = git('cat-file', 'blob', COMMIT + ':.github/workflows/verify.yml')
    (BASE / 'workflow-at-run.yml').write_bytes(workflow)
    bindings.append({'path': '.github/workflows/verify.yml', 'commit': COMMIT,
                     'bytes': len(workflow), 'sha256': digest(workflow)})
    for name in ['cache-job.log', 'engine-jobs-1.json']:
        shutil.copyfile(BASE.parent / name, BASE / name)
    historical = json.loads((destination / 'runs/host-resource-ci-repair-root-1/receipt.json').read_bytes())
    write_json('zip-manifest.json', {'entries': inventory, 'entry_count': len(inventory),
                                  'expanded_bytes': total, 'archive_sha256': ZIP_SHA,
                                  'all_entries_streamed_for_crc_size_and_sha256': True,
                                  'selected_only_extracted': sorted(SELECTED),
                                  'zip_cap_bytes': 8 * 1024 * 1024,
                                  'expanded_cap_bytes': 64 * 1024 * 1024})
    write_json('source-bindings.json', {'commit': COMMIT, 'tree': TREE, 'bindings': bindings,
                                      'observed_head_at_review': git('rev-parse', 'HEAD').decode().strip()})
    write_json('review.json', {
        'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
        'run_id': 40730444182, 'job_id': 122964999431, 'artifact_id': 12834358283,
        'commit': COMMIT, 'tree': TREE,
        'decision': 'failure-confirmed-primary-cleanup-exception-not-retained-no-pass',
        'current_failure': {'command': 'python3 -B verification/swift-cache-state-ci/test_runner.py -v',
                            'method': 'RunnerControls.test_owned_descendant_group_is_stopped',
                            'exception': "KeyError: 'owned_group_gone'", 'source_line': 85,
                            'tests_run': 29, 'reported_ok': 28, 'reported_errors': 1,
                            'elapsed_seconds_from_current_stderr': 2.264,
                            'actual_fixture_compiler_step': 'skipped'},
        'source_cause': [
            'RunnerControls.bad accepts RuntimeError/OSError/ValueError and discards the caught exception.',
            'Commands.run initial row omits owned_group_gone; Commands.stop assigns it only after group signal/wait/probe operations.',
            'Commands.run finally can exit from stream closure or stop before terminal row hashing/save. Any accepted exception there can be swallowed by bad, followed by the observed missing-key error.',
            'The preceding timed_out assertion completed, but the actual primary exception/syscall and descendant cleanup outcome are not in retained current output. They must not be invented.',
        ],
        'historical_run': {'artifact_prefix': 'runs/host-resource-ci-repair-root-1/',
                           'started_utc': historical['started_utc'],
                           'source_revision': historical['source_revision'],
                           'source_tree': historical['source_tree'],
                           'status': historical['status'], 'commands': len(historical['commands']),
                           'current_run_evidence': False},
        'current_negative_deadline_controls': {
            'members': ['logs/deadline-postflight-control.json', 'logs/deadline-retention-control.json'],
            'expected_failed_receipts': True, 'child_commands_each': 0,
            'both_methods_report_ok': True, 'cause_of_current_suite_failure': False},
        'cleanup': {'reviewer_started_native_or_test_processes': False,
                    'reviewer_ran_held_tests_or_process_group_probes': False,
                    'current_failed_CI_descendant_cleanup_verified': False,
                    'reason': 'Current failing control uses TemporaryDirectory; per-command receipt is not uploaded and tearDown does not establish group custody.'},
        'minimal_safe_correction_proposal': [
            'First preserve the original unexpected exception and full descendant control row in a current logs/descendant-control.json before assertions/temporary-directory cleanup. Preserve failure if cleanup is unknown.',
            'Make command finalization record cleanup exception type/message/errno, child-return and group-disposition uncertainty, and retain/hash command output even if stop fails. Do not assign owned_group_gone=true without its existing positive observation.',
            'Keep the same timeout, signal, group identity, output cap and success predicates. Avoid replacing the missing-key access with a silent false/default as the entire correction.',
            'If owned child/group cleanup remains unresolved, preserve scratch and a custody hold; do not erase recovery evidence or clear an active group merely because an exception was captured.',
        ],
        'testing_proposal_not_executed': [
            'Root chooses a bounded mock-only control with fake owned process and injected signal/probe/wait error. It must execute no real child, killpg or process inventory and prove original error plus conservative cleanup fields survive terminal receipt/output retention.',
            'A separate mock-only happy cleanup control must retain existing success behavior; timeout and output-cap controls must still fail closed.',
            'After review, root may authorize a fresh CI job for exact-source real descendant cleanup. No local custody replay, alternate equivalent test or compiler run is authorized by this review.',
        ],
        'review_execution': {'command': 'python3 -B ' + str(BASE / 'review.py'),
                             'python': sys.version, 'git': git('--version').decode().strip(),
                             'elapsed_seconds': round(time.monotonic() - started, 6),
                             'runner_imported_or_executed': False,
                             'allowed_mutation_scope': str(BASE)},
        'all_native_runtime_UI_Docker_Postgres_hosted_and_local_custody_holds_preserved': True,
    })
    print(json.dumps({'decision': 'failure-confirmed-primary-cleanup-exception-not-retained-no-pass',
                      'entries': len(inventory), 'expanded_bytes': total,
                      'sources_bound_to_failed_commit': len(bindings),
                      'no_runner_or_compiler_execution': True}, sort_keys=True))

if __name__ == '__main__':
    main()
