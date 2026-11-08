"""Prospective custody derivative; frozen fixture and compiler adapter stay intact."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OLD = ROOT / 'verification/plan-continuation-2026-11-07/cache-deadline-control-fix'
WORKFLOW = ROOT / '.github/workflows/verify.yml'
SOURCE = ROOT / 'verification/cache-fixture-shared-input-candidate-v2/check_cache_state.py'


def need(value, message):
    if not value:
        raise RuntimeError(message)


def sha(path):
    need(path.is_file() and not any(p.is_symlink() for p in [path, *path.parents]),
         'Regular source required: ' + str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def previous():
    inputs = json.loads((HERE / 'inputs-before.json').read_bytes())
    for row in inputs['members']:
        if row['path'] == '.github/workflows/verify.yml':
            continue
        need(sha(ROOT / row['path']) == row['sha256'], 'Historical input changed: ' + row['path'])
    sys.path.insert(0, str(OLD))
    try:
        support = sys.modules.get('local_support')
        need(support is None or Path(support.__file__).resolve() == OLD / 'local_support.py',
             'Conflicting historical support module')
        for name in ['control_source', 'deadline_control']:
            existing = sys.modules.get(name)
            need(existing is None or Path(existing.__file__).resolve() == OLD / (name + '.py'),
                 'Conflicting historical helper')
            if existing is None:
                sys.modules[name] = load(name, OLD / (name + '.py'))
        return load('custody_previous', OLD / 'adopt_fixture.py')
    finally:
        need(sys.path.pop(0) == str(OLD), 'Import path changed')


def verify(installed=False):
    old = previous()
    proof = old.verify(False)
    seal = json.loads((HERE / 'sources.json').read_bytes())
    binding = old.previous().baseline()
    binding.check_rows(HERE, seal['members'])
    need(seal['tree_sha256'] == binding.tree(seal['members']), 'Derivative source tree differs')
    source = SOURCE.read_text()
    original = source[source.index('class Commands:'):source.index('\ndef rust_identity')]
    need(original == (HERE / 'original-commands.py').read_text(), 'Original class preimage differs')
    if installed:
        need(binding.job_text(WORKFLOW.read_text()) == (HERE / 'workflow-job.yml').read_text(),
             'Installed job differs from custody proposal')
    return {'previous': proof, 'sources_sha256': sha(HERE / 'sources.json'),
            'commands_sha256': sha(HERE / 'commands.py'), 'installed': installed,
            'compiler_qualified': False, 'descendant_permission_cause_resolved': False}


def install(runner):
    need(sha(Path(runner.__file__)) == sha(SOURCE), 'Frozen runner identity differs')
    need((runner.ACTIVE_SECONDS, runner.CLEANUP_SECONDS, runner.CHILD_SECONDS, runner.OUTPUT_CAP)
         == (600, 60, 60, 8388608), 'Fixture budgets differ')
    # Only Commands is replaced, in the original globals. execute(), all command
    # construction, all validators, compiler selection and cleanup stay frozen.
    exec(compile((HERE / 'commands.py').read_bytes(), str(HERE / 'commands.py'), 'exec'), runner.__dict__)
    return runner


def run_fixture(output, rustc):
    proof = verify(True)
    compiler = previous().previous()
    old_verify, old_load = compiler.verify, compiler.load_runner

    def selected_verify(installed=False):
        result = old_verify(False)
        result['custody_derivative'] = verify(installed)
        result['installed_job_verified'] = installed
        return result

    def selected_load(out):
        runner = install(old_load(out))
        execute = runner.execute

        def observed_execute(destination, requested):
            snapshots = destination / 'custody-sources'
            snapshots.mkdir()
            seal = json.loads((HERE / 'sources.json').read_bytes())
            for row in seal['members']:
                target = snapshots / row['path']
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((HERE / row['path']).read_bytes())
            (snapshots / 'sources.json').write_bytes((HERE / 'sources.json').read_bytes())
            runner.save(destination / 'custody-start.json', proof)
            try:
                return execute(destination, requested)
            finally:
                need(verify(True) == proof, 'Custody derivative changed during fixture')
                for row in seal['members']:
                    need(sha(snapshots / row['path']) == row['sha256'], 'Retained custody source differs')
                runner.save(destination / 'custody-postflight.json', proof)
        runner.execute = observed_execute
        return runner

    compiler.verify, compiler.load_runner = selected_verify, selected_load
    try:
        return compiler.run_fixture(output, rustc)
    finally:
        compiler.verify, compiler.load_runner = old_verify, old_load
        need(verify(True) == proof, 'Custody proposal changed')


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
