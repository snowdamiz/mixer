#!/usr/bin/env python3
"""Adopt the frozen shared-input runner with the ordinary compiler identity policy."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
V2 = ROOT / 'verification/cache-fixture-shared-input-candidate-v2'
BASE_RUNNER = ROOT / 'verification/swift-cache-state-ci/check_cache_state.py'
JOB = 'swift-cache-state-fixture'
WORKFLOW = ROOT / '.github/workflows/verify.yml'


def need(value, message):
    if not value:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def regular(path):
    for parent in [*reversed(path.parents), path]:
        need(not parent.is_symlink(), 'Symlink forbidden: ' + str(parent))
    need(path.is_file(), 'Regular source required: ' + str(path))
    return path


def row_path(base, row):
    name = row['path']
    part = Path(name)
    need(isinstance(name, str) and part.as_posix() == name and not part.is_absolute()
         and name not in {'', '.'} and not any(p in {'.', '..', '.git'} for p in part.parts)
         and '\\' not in name and '\x00' not in name, 'Noncanonical source path')
    return regular(base / part)


def check_rows(base, rows):
    need(rows == sorted(rows, key=lambda row: row['path'])
         and len(rows) == len({row['path'] for row in rows}), 'Unsorted/duplicate source rows')
    for row in rows:
        source = row_path(base, row)
        need(set(row) == {'path', 'bytes', 'sha256'} and type(row['bytes']) is int
             and source.stat().st_size == row['bytes'] and sha(source) == row['sha256'],
             'Pinned source differs: ' + row['path'])


def job_text(text):
    lines = text.splitlines(keepends=True)
    marker = '  ' + JOB + ':\n'
    starts = [index for index, line in enumerate(lines) if line == marker]
    need(len(starts) == 1, 'Exactly one ordinary fixture job required')
    start = starts[0]
    end = next((index for index in range(start + 1, len(lines))
                if lines[index].startswith('  ') and not lines[index].startswith('   ')
                and lines[index].rstrip().endswith(':')), len(lines))
    return ''.join(lines[start:end])


def verify(installed=False):
    seal = json.loads(regular(HERE / 'seal.json').read_bytes())
    check_rows(HERE, seal['members'])
    need(seal['member_count'] == len(seal['members'])
         and seal['tree_sha256'] == tree(seal['members']), 'Adoption seal count/tree differs')
    rows = seal['members']
    observed = []
    for source in HERE.rglob('*'):
        relative = source.relative_to(HERE)
        if relative.parts[0] in {'logs', 'control-scratch', '__pycache__'}:
            continue
        need(not source.is_symlink(), 'Adoption symlink forbidden')
        if source.is_file() and relative.as_posix() != 'seal.json':
            observed.append(relative.as_posix())
    need(sorted(observed) == [row['path'] for row in rows], 'Adoption shipping closure differs')
    bindings = json.loads(regular(HERE / 'dependencies.json').read_bytes())
    check_rows(ROOT, bindings['members'])
    need(bindings['member_count'] == len(bindings['members'])
         and bindings['tree_sha256'] == tree(bindings['members']), 'Dependency count/tree differs')
    expected_job = regular(HERE / 'workflow/swift-cache-state-fixture.yml').read_text()
    if installed:
        need(job_text(regular(WORKFLOW).read_text()) == expected_job,
             'Installed ordinary fixture job differs from sealed candidate')
    return {'schema': 1, 'adoption_seal_sha256': sha(HERE / 'seal.json'),
            'adoption_tree_sha256': seal['tree_sha256'],
            'dependencies_sha256': sha(HERE / 'dependencies.json'),
            'workflow_job_sha256': hashlib.sha256(expected_job.encode()).hexdigest(),
            'installed_job_verified': installed,
            'compiler_policy': bindings['compiler_policy'],
            'fixture_source': bindings['fixture_source']}


def module_at(name, source):
    specification = importlib.util.spec_from_file_location(name, source)
    need(specification is not None and specification.loader is not None, 'Python source loader missing')
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def load_runner():
    proof = verify()
    sibling = str(V2)
    sys.path.insert(0, sibling)
    try:
        existing = sys.modules.get('materialize_pack')
        need(existing is None or Path(existing.__file__).resolve() == V2 / 'materialize_pack.py',
             'Different materializer already imported')
        base = module_at('mixer_ordinary_identity_source', BASE_RUNNER)
        runner = module_at('mixer_shared_input_v2', V2 / 'check_cache_state.py')
    finally:
        need(sys.path.pop(0) == sibling, 'Import search path changed')
    # Reuse the exact hash-bound ordinary validator and its own globals. No copied
    # validator, dynamic compiler selection, installation, retry or fallback.
    runner.rust_identity = base.rust_identity
    need(runner.rust_identity is base.rust_identity, 'Ordinary validator not reused')
    need((runner.CHILD_SECONDS, runner.ACTIVE_SECONDS, runner.CLEANUP_SECONDS, runner.OUTPUT_CAP)
         == (60, 600, 60, 8 * 1024 * 1024), 'Frozen fixture limits differ')
    runner.overlay.verify_inputs()
    return runner, base, proof


def run_fixture(output, rustc):
    need(os.environ.get('RUSTUP_AUTO_INSTALL') == '0', 'Automatic compiler installation forbidden')
    proof = verify(installed=True)
    runner, base, _ = load_runner()
    output = runner.fresh_output(output)
    adapter_hash = sha(regular(Path(__file__).resolve()))
    shutil.copyfile(Path(__file__).resolve(), output / 'executed-adapter.py')
    runner.save(output / 'adapter-start.json', {
        **proof, 'adapter_sha256': adapter_hash, 'requested_rustc': rustc,
        'fixture_invocations_admitted': 1,
        'identity_validator_source': str(BASE_RUNNER),
        'identity_validator_reused_exact_function': runner.rust_identity is base.rust_identity})
    status = None
    failure = None
    postflight = None
    try:
        status = runner.execute(output, rustc)
    except BaseException as error:
        failure = {'type': type(error).__name__, 'message': str(error)}
    finally:
        try:
            postflight = verify(installed=True)
            need(sha(regular(Path(__file__).resolve())) == adapter_hash
                 and sha(regular(output / 'executed-adapter.py')) == adapter_hash,
                 'Adapter identity changed')
        except BaseException as error:
            postflight = {'failed': {'type': type(error).__name__, 'message': str(error)}}
            status = 1
        receipt = json.loads((output / 'receipt.json').read_bytes()) if (output / 'receipt.json').is_file() else {}
        runner.save(output / 'adapter-result.json', {
            'schema': 1, 'fixture_return_status': status, 'adapter_exception': failure,
            'source_postflight': postflight, 'adapter_sha256': adapter_hash,
            'actual_compiler': receipt.get('rustc'),
            'fixture_status': receipt.get('status'),
            'scope': 'Existing compiler selected by unchanged ordinary allowlist; no install/retry/fallback. '
                     'Only the frozen runner receipt establishes fixture commands, assertions and cleanup.'})
    if failure:
        raise RuntimeError('Frozen fixture invocation raised: ' + str(failure))
    return 0 if status == 0 else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    verification = commands.add_parser('verify')
    verification.add_argument('--workflow-installed', action='store_true')
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
