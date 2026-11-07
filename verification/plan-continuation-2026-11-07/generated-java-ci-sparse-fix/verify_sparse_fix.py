#!/usr/bin/env python3
"""Reproduce P1 evidence using selected-file copies, fake children and read-only Git."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CANDIDATE = HERE.parent / 'generated-java-ci-integration'
REVIEW = HERE.parent / 'generated-java-ci-integration-review'
COMMANDS = []


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def identity(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def inventory(root):
    return {p.relative_to(root).as_posix(): identity(p) for p in sorted(root.rglob('*')) if p.is_file()}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def run(label, argv, expected_tests=None):
    result = subprocess.run(list(map(str, argv)), cwd=ROOT, capture_output=True, timeout=45)
    (HERE / (label + '.stdout')).write_bytes(result.stdout)
    (HERE / (label + '.stderr')).write_bytes(result.stderr)
    record = {'label': label, 'argv': list(map(str, argv)), 'cwd': str(ROOT), 'timeout_seconds': 45,
              'exit_code': result.returncode, 'stdout': identity(HERE / (label + '.stdout')),
              'stderr': identity(HERE / (label + '.stderr'))}
    COMMANDS.append(record)
    save(HERE / 'commands.json', COMMANDS)
    require(result.returncode == 0, 'Command failed: ' + label)
    if expected_tests:
        require(('Ran ' + str(expected_tests) + ' tests') in result.stderr.decode() and
                result.stderr.decode().rstrip().endswith('OK'), 'Unexpected test outcome: ' + label)
        record['passed_tests'] = expected_tests
    return result.stdout


def main():
    before = json.loads((HERE / 'before.json').read_text())
    require(inventory(REVIEW) == before['sealed_review'], 'Sealed review changed')
    source = load('sparse_evidence_controls', CANDIDATE / 'test_sparse_checkout.py')
    patterns = source.proposal_patterns((CANDIDATE / 'workflow-proposal.yml').read_text())
    a = source.B.canonical()
    inputs = source.B.admit_source_inputs(a, a.load_profile())
    roots = [pattern.strip('/') for pattern in patterns]
    selected = run('tracked-selection', ['git', 'ls-tree', '-rl', '-z', before['revision'], '--', *roots])
    tracked = {}
    for record in selected.rstrip(b'\0').split(b'\0'):
        metadata, path = record.split(b'\t', 1)
        mode, kind, oid, size = metadata.split()
        require(kind == b'blob' and mode in (b'100644', b'100755'), 'Unexpected selected entry')
        tracked[path.decode()] = {'bytes': int(size), 'git_blob': oid.decode(), 'mode': mode.decode()}
    require(len(tracked) <= 10000 and sum(v['bytes'] for v in tracked.values()) < 10_000_000,
            'Selected tree exceeds bounded projection budget')
    candidate = inventory(CANDIDATE)
    candidate_rel = CANDIDATE.relative_to(ROOT)
    required_paths = sorted(set(tracked) | {str(candidate_rel / path) for path in candidate})
    selected_paths = source.git_selected(required_paths, patterns)
    source.require_coverage(required_paths, selected_paths)
    source.require_coverage(inputs, selected_paths)
    save(HERE / 'git-rule-commands.json', source.GIT_COMMANDS)
    save(HERE / 'selected-tracked-inputs.json', tracked)
    save(HERE / 'canonical-owning-inputs.json', inputs)
    projected_inventory = {}
    with tempfile.TemporaryDirectory(prefix='selected-only-', dir=HERE) as td:
        projection = Path(td)
        for relative in required_paths:
            original = ROOT / relative
            require(original.is_file() and not original.is_symlink(), 'Selected source missing/nonregular: ' + relative)
            target = projection / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original, target)
            projected_inventory[relative] = identity(target)
            require(projected_inventory[relative] == identity(original), 'Selected copy mismatch')
        projected = load('projected_bootstrap', projection / candidate_rel / 'bootstrap.py')
        projected_authority = projected.canonical()
        projected_inputs = projected.admit_source_inputs(projected_authority, projected_authority.load_profile())
        require(projected_inputs == inputs, 'Selected-only canonical source differs')
        omissions = []
        for relative in ('cli/Package.swift', 'scripts/ci/check-android-binding.py'):
            target = projection / relative
            original = target.read_bytes()
            target.unlink()
            try:
                projected.admit_source_inputs(projected_authority, projected_authority.load_profile())
                raise RuntimeError('Missing input was admitted')
            except RuntimeError as error:
                require('owning inputs differ' in str(error) or 'Expected regular file' in str(error),
                        'Unexpected omission refusal: ' + str(error))
                omissions.append({'path': relative, 'refused': True, 'error': str(error)})
            except FileNotFoundError as error:
                omissions.append({'path': relative, 'refused': True, 'error': str(error)})
            finally:
                target.write_bytes(original)
        tampered = projection / 'cli/Package.swift'
        pristine = tampered.read_bytes()
        tampered.write_bytes(pristine + b'\n// sparse digest negative control\n')
        try:
            projected.admit_source_inputs(projected_authority, projected_authority.load_profile())
            raise RuntimeError('Changed input was admitted')
        except RuntimeError as error:
            require('owning inputs differ' in str(error), 'Unexpected changed-input refusal')
            omissions.append({'path': 'cli/Package.swift', 'changed_bytes_refused': True, 'error': str(error)})
        finally:
            tampered.write_bytes(pristine)
        test = projection / candidate_rel / 'test_bootstrap.py'
        for suffix, options in (('normal', []), ('optimized', ['-O'])):
            run('projected-original22-' + suffix, [sys.executable, '-I', '-B', '-S', *options, test, '-v'], 22)
        require(projected.admit_source_inputs(projected_authority, projected_authority.load_profile()) == inputs,
                'Projected postflight differs')
        projection_removed_path = str(projection)
    require(not Path(projection_removed_path).exists(), 'Selected-only disposable projection was not removed')
    save(HERE / 'selected-projection.json', {'scope': 'Only selected tracked files and candidate copied; no full checkout, no blob fetch, no native tools',
        'files': projected_inventory, 'files_count': len(projected_inventory),
        'bytes': sum(v['bytes'] for v in projected_inventory.values()),
        'canonical_inputs': len(projected_inputs), 'canonical_sha256': projected_authority.source_digest(projected_inputs),
        'negative_controls': omissions, 'owned_projection_removed': True})
    # Copy the sealed reviewer test verbatim before replay so its HERE-owned
    # receipts and fake scratch live exclusively in this evidence namespace.
    failure_test = HERE / 'test_failure_paths.py'
    failure_test.write_bytes((REVIEW / 'test_failure_paths.py').read_bytes())
    for suffix, options in (('normal', []), ('optimized', ['-O'])):
        run('sparse-' + suffix, [sys.executable, '-I', '-B', '-S', *options, CANDIDATE / 'test_sparse_checkout.py', '-v'], 12)
        run('failure-' + suffix, [sys.executable, '-I', '-B', '-S', *options, failure_test, '-v'], 2)
    require(inventory(REVIEW) == before['sealed_review'], 'Sealed review changed during replay')
    now_candidate = inventory(CANDIDATE)
    changed = {path: {'before': before['candidate'].get(path), 'after': now_candidate.get(path)}
               for path in sorted(set(before['candidate']) | set(now_candidate))
               if before['candidate'].get(path) != now_candidate.get(path)}
    require(set(changed) == {'bootstrap.py', 'workflow-proposal.yml', 'test_sparse_checkout.py'},
            'Unexpected candidate changed paths')
    save(HERE / 'candidate-changes.json', changed)
    save(HERE / 'candidate-final-inventory.json', now_candidate)
    save(HERE / 'sealed-review-final-inventory.json', inventory(REVIEW))
    save(HERE / 'coverage.json', {'patterns': patterns, 'cone_mode': False,
        'official_action': 'actions/checkout@v4', 'filter_override': None,
        'partial_fetch_policy': 'Official checkout v4 sparse configuration selects blob:none; no fetch performed here',
        'tracked_selected_files': len(tracked), 'tracked_selected_bytes': sum(v['bytes'] for v in tracked.values()),
        'candidate_bytes': sum(v['bytes'] for v in candidate.values()),
        'all_selected_dependencies_covered': selected_paths == set(required_paths),
        'owning_inputs': len(inputs), 'owning_source_sha256': a.source_digest(inputs),
        'uncovered_owning_inputs': sorted(set(inputs) - selected_paths),
        'closure': 'All tracked cli/sdk/updates Sources, Tests, Fixtures, Resources, Package.*; native/android; scripts/ci dependency verifier; complete candidate controls and retained metadata. CLI local packages are sdk and updates. Remote SwiftPM dependencies remain fetched at runtime using included lockfiles and canonical dependency_checkouts; no vendoring or external-download claim.',
        'original22_control_source_unchanged': now_candidate['test_bootstrap.py'] == before['candidate']['test_bootstrap.py']})
    save(HERE / 'commands.json', COMMANDS)
    print(json.dumps({'status': 'PASS_P1_PROPOSAL_ONLY', 'tests': {'original22': 'normal and -O, selected-only projection',
          'sparse12': 'normal and -O', 'reviewer_failure2': 'normal and -O'},
          'owning_inputs': len(inputs), 'digest': a.source_digest(inputs), 'sealed_review_unchanged': True,
          'candidate_changed_paths': list(changed)}, indent=2))


if __name__ == '__main__':
    main()
