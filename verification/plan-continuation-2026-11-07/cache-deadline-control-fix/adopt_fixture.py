#!/usr/bin/env python3
"""Prospective exact deadline-control adoption; preserve all prior source/identity seals."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from local_support import HERE, ROOT, load

PREVIOUS = ROOT / 'verification/plan-continuation-2026-11-07/cache-fix'
WORKFLOW = ROOT / '.github/workflows/verify.yml'
SHIPPING = sorted(['adopt_fixture.py', 'control_source.py', 'deadline_control.py',
    'local_support.py', 'runner-controls.py', 'test_runner.py', 'test_contracts.py',
    'controls.diff', 'workflow.diff', 'workflow/previous-job.yml',
    'workflow/swift-cache-state-fixture.yml'])


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def regular(path):
    need(path.is_file() and not any(p.is_symlink() for p in [path, *path.parents]),
         'Regular non-symlink source required: ' + str(path))
    return path


def sha(path):
    return hashlib.sha256(regular(path).read_bytes()).hexdigest()


def previous():
    need(sha(PREVIOUS / 'adopt_fixture.py') == '10f70a7bd80806c10799a973db81dc1ffad8386d7705a1fa4bed140bc78a5e60',
         'Previous compiler adapter changed')
    need(sha(PREVIOUS / 'sources.json') == '7581e2b8b6200e227655d62f1011493c24aa62ef80e2e223cf7ec06b4203cc3b',
         'Previous compiler source seal changed')
    return load('deadline_previous_selection', PREVIOUS / 'adopt_fixture.py')


def verify(installed=False):
    old = previous()
    historical = old.verify(False)
    seal = old.read_json(HERE / 'sources.json')
    need([row['path'] for row in seal['members']] == SHIPPING, 'Exact correction shipping roster required')
    binding = old.baseline()
    binding.check_rows(HERE, seal['members'])
    need(seal['tree_sha256'] == binding.tree(seal['members']) and
         seal['member_count'] == len(SHIPPING), 'Correction source tree differs')
    from control_source import control_source
    derivative = control_source()
    before = regular(HERE / 'workflow/previous-job.yml').read_text()
    need(before == regular(PREVIOUS / 'workflow/swift-cache-state-fixture.yml').read_text(),
         'Historical prospective job preimage changed')
    expected = regular(HERE / 'workflow/swift-cache-state-fixture.yml').read_text()
    if installed:
        need(binding.job_text(regular(WORKFLOW).read_text()) == expected,
             'Installed job differs from exact deadline-control proposal')
    return {'schema': 1, 'previous_adoption': historical,
        'correction_sources_sha256': sha(HERE / 'sources.json'),
        'control_derivative_sha256': hashlib.sha256(derivative).hexdigest(),
        'workflow_job_sha256': hashlib.sha256(expected.encode()).hexdigest(),
        'installed_job_verified': installed, 'compiler_qualified': False,
        'scope': 'Exact prospective controls and job binding; all previous seals, 103 commands, compiler profile and finite fixture limits preserved.'}


def run_fixture(output, rustc):
    proof = verify(installed=True)
    old = previous()
    original_verify = old.verify
    def adopted_verify(installed=False):
        # Only the workflow comparison changes, to the new fully pinned job.
        # Original verify(False) still checks every old source/seal/profile byte.
        result = original_verify(False)
        current = verify(installed=installed)
        result.update(deadline_controls=current,
                      installed_job_verified=installed,
                      workflow_job_sha256=current['workflow_job_sha256'])
        return result
    old.verify = adopted_verify
    try:
        return old.run_fixture(output, rustc)
    finally:
        need(verify(installed=True) == proof, 'Deadline-control adoption changed during fixture')


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
