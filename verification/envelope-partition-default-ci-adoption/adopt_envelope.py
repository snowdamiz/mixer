#!/usr/bin/env python3
"""Thin ordinary-CI adoption of the exact reviewed envelope partition source."""
import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT / 'verification/envelope-producer-timeout-experiment'
BASE_RUNNER = ROOT / 'scripts/ci/check-analyzer-envelope.py'
JOB = 'swift'
WORKFLOW = ROOT / '.github/workflows/verify.yml'
POLICY_FUNCTIONS = ('rustc_identity', 'select_compiler', 'select_host_target')


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
    need(len(starts) == 1, 'Exactly one ordinary Swift job required')
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
    expected_job = regular(HERE / 'workflow/swift-job.yml').read_text()
    if installed:
        need(job_text(regular(WORKFLOW).read_text()) == expected_job,
             'Installed ordinary Swift job differs from sealed candidate')
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
    base = module_at('ordinary_envelope_policy', BASE_RUNNER)
    runner = module_at('reviewed_envelope_partition', PRODUCER / 'candidate_runner.py')
    def definitions(source):
        text = regular(source).read_text()
        return {node.name: ast.get_source_segment(text, node) for node in ast.parse(text).body
                if isinstance(node, ast.FunctionDef)}
    original, candidate = definitions(BASE_RUNNER), definitions(PRODUCER / 'candidate_runner.py')
    for name in POLICY_FUNCTIONS:
        need(original[name] == candidate[name], 'Compiler policy source differs: ' + name)
        # Reuse exact hash-bound ordinary functions with their original globals.
        setattr(runner, name, getattr(base, name))
        need(getattr(runner, name) is getattr(base, name), 'Ordinary function not reused: ' + name)
    need((runner.OUTPUT_CAP, runner.TOTAL_OUTPUT_CAP) == (8388608, 67108864),
         'Reviewed stream limits differ')
    runner.verify_pack(ROOT / runner.PACK)
    return runner, base, proof


def run_fixture(output, rustc):
    need(os.environ.get('RUSTUP_AUTO_INSTALL') == '0', 'Automatic compiler installation forbidden')
    revision = os.environ.get('GITHUB_SHA', '')
    need(len(revision) == 40 and all(c in '0123456789abcdef' for c in revision),
         'Exact ordinary CI source revision required')
    proof = verify(installed=True)
    runner, base, _ = load_runner()
    replay = module_at('envelope_adoption_terminal_replay', HERE / 'terminal_replay.py')
    output = runner.fresh_output(output)
    snapshots = {
        'executed-adapter.py': Path(__file__).resolve(),
        'executed-ordinary-policy.py': BASE_RUNNER,
        'executed-terminal-replay.py': HERE / 'terminal_replay.py',
        'executed-dependencies.json': HERE / 'dependencies.json',
        'executed-adoption-seal.json': HERE / 'seal.json',
    }
    identities = {name: sha(regular(source)) for name, source in snapshots.items()}
    for name, source in snapshots.items():
        shutil.copyfile(source, output / name)
    runner.write_json(output / 'adapter-start.json', {
        **proof, 'requested_rustc': rustc, 'revision': revision,
        'fixture_invocations_admitted': 1, 'source_snapshots': identities,
        'identity_validator_source': str(BASE_RUNNER),
        'ordinary_functions_reused_exactly': {
            name: getattr(runner, name) is getattr(base, name) for name in POLICY_FUNCTIONS}})
    status, failure, postflight, terminal, receipt = None, None, None, None, {}
    errors = []
    try:
        status = runner.execute(output, rustc)
    except BaseException as error:
        failure = {'type': type(error).__name__, 'message': str(error)}
    finally:
        # Source postflight must run even if invocation raises or reports failure.
        try:
            postflight = verify(installed=True)
            for name, source in snapshots.items():
                need(sha(regular(source)) == identities[name]
                     and sha(regular(output / name)) == identities[name],
                     'Executed source identity differs: ' + name)
        except BaseException as error:
            errors.append({'phase': 'source-postflight', 'type': type(error).__name__, 'message': str(error)})
        try:
            if (output / 'receipt.json').is_file():
                receipt = json.loads(regular(output / 'receipt.json').read_bytes())
            if status == 0 and failure is None:
                actual = receipt['rustc']
                terminal = replay.replay(output, {
                    'revision': revision, 'compiler': actual['path'],
                    'compiler_sha256': actual['sha256']}, runner)
        except BaseException as error:
            errors.append({'phase': 'terminal-replay', 'type': type(error).__name__, 'message': str(error)})
        runner.write_json(output / 'adapter-result.json', {
            'schema': 1, 'fixture_return_status': status, 'adapter_exception': failure,
            'source_postflight': postflight, 'errors': errors, 'terminal_replay': terminal,
            'actual_compiler': receipt.get('rustc'), 'fixture_status': receipt.get('status'),
            'scope': 'Exact reviewed partition source; unchanged ordinary compiler policy; '
                     'one invocation, no installation/retry/fallback; host fixture evidence only.'})
    return 0 if status == 0 and failure is None and not errors else 1


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


