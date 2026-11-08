#!/usr/bin/env python3
"""Proposed exact compiler admission; reuse the sealed 103-command fixture."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OLD = ROOT / 'verification/shared-fixture-clock-controls-correction'
WORKFLOW = ROOT / '.github/workflows/verify.yml'
COMPILER_SHA256 = '1ba7bb8e273bd64125f4048d2ecce530e0a6470e565ab1b3aecf0b82b532f7b1'
IDENTITY = {'binary': 'rustc', 'commit-hash': '58cf8f9c35b355199727627d07ae34a4e2846d67',
            'commit-date': '2026-10-13', 'host': 'aarch64-apple-darwin',
            'release': '1.99.1', 'LLVM version': '23.1.1'}
VERBOSE = ('rustc 1.99.1 (58cf8f9c3 2026-10-13)\n'
           + ''.join(f'{key}: {value}\n' for key, value in IDENTITY.items()))
SHIPPING = ('README.md', 'adopt_fixture.py', 'compiler-selection.json',
            'offline_guard.py', 'test_selection.py', 'workflow.diff',
            'workflow/swift-cache-state-fixture.yml')


def need(value, message):
    if not value:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def regular(path):
    need(path.is_file() and not any(p.is_symlink() for p in [path, *path.parents]),
         'Regular source without symlinks required: ' + str(path))
    return path


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            need(key not in result, 'Duplicate JSON key')
            result[key] = value
        return result
    return json.loads(regular(path).read_bytes(), object_pairs_hook=unique)


def baseline():
    need(sha(regular(OLD / 'adopt_fixture.py')) ==
         '7e3fafa25d2b6ee2ac61f8bb23a0799304139b66684e3d5faf95f57c853634e3',
         'Historical adapter changed')
    need(sha(regular(OLD / 'seal.json')) ==
         '2c4b7f295d275694b5541113f17f0e9216a073a864b01b95b0078632d4145d71',
         'Historical adoption seal changed')
    spec = importlib.util.spec_from_file_location('cache_fixture_historical_adoption', OLD / 'adopt_fixture.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify(installed=False):
    old = baseline()
    historical = old.verify(False)
    manifest = read_json(HERE / 'sources.json')
    need([row['path'] for row in manifest['members']] == list(SHIPPING), 'Shipping roster differs')
    old.check_rows(HERE, manifest['members'])
    need(manifest['tree_sha256'] == old.tree(manifest['members']), 'Shipping tree differs')
    selection = read_json(HERE / 'compiler-selection.json')
    need(selection['status'] == 'proposed-for-root-review-not-qualified'
         and selection['qualified'] is False
         and selection['profile'] == {'identity': IDENTITY, 'compiler_sha256': COMPILER_SHA256},
         'Exact prospective selection differs')
    expected = regular(HERE / 'workflow/swift-cache-state-fixture.yml').read_text()
    if installed:
        need(old.job_text(regular(WORKFLOW).read_text()) == expected,
             'Installed job differs from exact prospective proposal')
    return {'schema': 1, 'historical_adoption': historical,
            'sources_sha256': sha(HERE / 'sources.json'),
            'selection_sha256': sha(HERE / 'compiler-selection.json'),
            'workflow_job_sha256': hashlib.sha256(expected.encode()).hexdigest(),
            'installed_job_verified': installed, 'compiler_qualified': False,
            'scope': 'Exact prospective shared-fixture proposal; no envelope qualification inherited'}


def select_identity(text, evidence, runner):
    need(text == VERBOSE, 'Exact prospective compiler verbose identity differs')
    compiler = Path(evidence['path'])
    need(compiler.is_absolute() and evidence['sha256'] == COMPILER_SHA256
         and runner.sha(regular(compiler)) == COMPILER_SHA256,
         'Exact prospective compiler binary fingerprint differs')
    return dict(IDENTITY)


def load_runner(output):
    old = baseline()
    runner, ordinary, _ = old.load_runner()
    need((runner.CHILD_SECONDS, runner.ACTIVE_SECONDS, runner.CLEANUP_SECONDS, runner.OUTPUT_CAP)
         == (60, 600, 60, 8388608), 'Historical finite limits differ')
    # execute() saves the resolved path/hash before calling this hook and before
    # any Rust compilation. Its original resolver, commands and postflights run.
    def selected(text):
        evidence = read_json(output / 'receipt.json')['rustc']
        return select_identity(text, evidence, runner)
    runner.rust_identity = selected
    return runner


def run_fixture(output, rustc):
    need(os.environ.get('RUSTUP_AUTO_INSTALL') == '0', 'Automatic compiler installation forbidden')
    proof = verify(installed=True)
    runner = load_runner(output)
    output = runner.fresh_output(output)
    snapshots = output / 'compiler-selection-sources'
    snapshots.mkdir()
    for name in (*SHIPPING, 'sources.json'):
        target = snapshots / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(regular(HERE / name), target)
    runner.save(output / 'selection-start.json', {**proof, 'requested_rustc': rustc,
                'fixture_invocations_admitted': 1, 'compiler_qualified': False})
    status, errors = None, []
    try:
        status = runner.execute(output, rustc)
    except BaseException as error:
        errors.append({'phase': 'fixture', 'type': type(error).__name__, 'message': str(error)})
    finally:
        try:
            need(verify(installed=True) == proof, 'Source selection changed during fixture')
            for name in (*SHIPPING, 'sources.json'):
                need(sha(regular(snapshots / name)) == sha(regular(HERE / name)),
                     'Retained selection source changed: ' + name)
            if status == 0:
                receipt = read_json(output / 'receipt.json')
                need(receipt['status'] == 'passed-host-fixture-check'
                     and receipt['active_checks_completed'] is True and not receipt['errors']
                     and len(receipt['commands']) == 103, 'Complete 103-command success required')
                actual = receipt['rustc']
                need(actual['identity'] == select_identity(actual['version_verbose'], actual, runner),
                     'Terminal compiler selection differs')
                need(regular(output / 'commands/compiler-identity.stdout').read_text() == VERBOSE,
                     'Retained verbose identity differs')
        except BaseException as error:
            errors.append({'phase': 'selection-postflight', 'type': type(error).__name__, 'message': str(error)})
        runner.save(output / 'selection-result.json', {
            'schema': 1, 'fixture_return_status': status, 'errors': errors,
            'selection_sha256': proof['selection_sha256'], 'compiler_qualified': False,
            'scope': 'Full matching fixture and independent actual review required; no GA/native/release authority'})
    return 0 if status == 0 and not errors else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    check = commands.add_parser('verify')
    check.add_argument('--workflow-installed', action='store_true')
    run = commands.add_parser('run')
    run.add_argument('--out', type=Path, required=True)
    run.add_argument('--rustc', required=True)
    args = parser.parse_args()
    if args.command == 'verify':
        print(json.dumps(verify(args.workflow_installed), sort_keys=True))
        return 0
    return run_fixture(args.out, args.rustc)


if __name__ == '__main__':
    sys.exit(main())
