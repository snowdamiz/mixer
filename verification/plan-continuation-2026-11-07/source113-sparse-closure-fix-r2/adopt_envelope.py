#!/usr/bin/env python3
"""Prospective job binding; delegate the unchanged sealed compiler/fixture policy."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
HISTORICAL = ROOT / 'verification/envelope-rust-1991-default-ci-adoption'
WORKFLOW = ROOT / '.github/workflows/verify.yml'
CALLER_BEFORE = '          swift test --package-path cli\n'
CALLER_AFTER = ('          swift build --package-path cli --product mixer -j 2\n'
    '          MIXER_STORE_CLI_BIN_DIR="$(swift build --package-path cli --product mixer -j 2 --show-bin-path)"\n'
    '          test -x "$MIXER_STORE_CLI_BIN_DIR/mixer"\n'
    '          MIXER_STORE_TEST_CLI="$MIXER_STORE_CLI_BIN_DIR/mixer" swift test --package-path cli\n')


def load():
    spec = importlib.util.spec_from_file_location('sealed_envelope_caller_base', HISTORICAL / 'adopt_envelope.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def bind():
    base = load()
    historical_verify = base.verify

    def verify(installed=False):
        proof = historical_verify(False)
        seal = json.loads(base.regular(HERE / 'seal.json').read_bytes(), object_pairs_hook=base.unique_object)
        base.check_rows(HERE, seal['members'])
        base.need(seal['member_count'] == len(seal['members']) and
                  seal['tree_sha256'] == base.tree(seal['members']), 'Successor seal differs')
        history = json.loads(base.regular(HERE / 'historical-closure.json').read_bytes(),
                             object_pairs_hook=base.unique_object)
        base.check_rows(ROOT, history)
        previous = HERE.parent / 'envelope-output-ownership-fix-r2'
        old_seal = json.loads(base.regular(previous / 'seal.json').read_bytes(),
                              object_pairs_hook=base.unique_object)
        base.check_rows(previous, old_seal['members'])
        base.need(old_seal['member_count'] == len(old_seal['members']) and
                  old_seal['tree_sha256'] == base.tree(old_seal['members']), 'R2 history seal differs')
        frozen = json.loads(base.regular(HERE / 'source-inputs.json').read_bytes(),
                            object_pairs_hook=base.unique_object)
        base.check_rows(ROOT, [dict(path=p, **row) for p, row in sorted(frozen.items())])
        owner = base.module_at('profile10_source_closure', ROOT / 'scripts/ci/check-android-generated-java.py')
        profile = owner.load_profile(ROOT)
        actual = owner.source_inputs(profile)
        base.need(actual == frozen, 'Current owning source closure differs')
        binding = json.loads(base.regular(HERE / 'binding.json').read_bytes(), object_pairs_hook=base.unique_object)
        digest = owner.source_digest(frozen)
        base.need(len(frozen) == 113 and digest == 'c92cd273b5a9b11846375784f9763a3da82d5df9ed15c2efd3fb589007e1d5c1'
                  and binding['source']['count'] == len(frozen) and binding['source']['sha256'] == digest,
                  'Accepted source closure differs')
        base.need(binding['profile'] == {
            'id': profile['id'], 'sdk_count': len(profile['sdk_files']),
            'sdk_sha256': profile['sdk_compatibility_sha256'],
            'adapter_count': len(profile['adapter_files']),
            'adapter_sha256': profile['adapter_compatibility_sha256'],
            'java_sources': len(owner.java_roster(profile))}, 'Accepted profile binding differs')
        old = base.regular(HISTORICAL / 'workflow/swift-job.yml').read_text()
        base.need(old.count(CALLER_BEFORE) == 1, 'Original CLI caller preimage differs')
        expected = old.replace(CALLER_BEFORE, CALLER_AFTER)
        for change in json.loads(base.regular(previous / 'job-changes.json').read_bytes(),
                                 object_pairs_hook=base.unique_object):
            base.need(expected.count(change['before']) == change['count'], 'R2 edit preimage differs')
            expected = expected.replace(change['before'], change['after'])
        current = base.regular(HERE / 'current-swift-job.yml').read_text()
        base.need(expected == current, 'Current job differs from sealed R2 derivation')
        changes = json.loads(base.regular(HERE / 'job-changes.json').read_bytes(), object_pairs_hook=base.unique_object)
        for change in changes:
            base.need(expected.count(change['before']) == change['count'], 'Successor edit preimage differs')
            expected = expected.replace(change['before'], change['after'])
        base.need(expected == base.regular(HERE / 'swift-job.yml').read_text(), 'Successor job derivation differs')
        if installed:
            base.need(base.job_text(base.regular(WORKFLOW).read_text()) == expected,
                      'Installed ordinary Swift job differs from successor candidate')
        return {**proof, 'historical_workflow_job_sha256': proof['workflow_job_sha256'],
                'workflow_job_sha256': hashlib.sha256(expected.encode()).hexdigest(),
                'installed_job_verified': installed, 'caller_binding_seal_sha256': base.sha(HERE / 'seal.json'),
                'source_count': len(frozen), 'source_sha256': digest, 'profile': binding['profile'],
                'historical_closure_sha256': base.sha(HERE / 'historical-closure.json')}

    base.verify = verify
    return base


class FreshOutput:
    """Observe successful historical admission; never infer it from an existing path."""
    def __init__(self, base):
        self.base = base
        self.fd = None
        self.runner = None
        self.restores = []

    def observe(self, runner):
        fresh = runner.fresh_output
        def admitted(*args, **kwargs):
            out = fresh(*args, **kwargs)
            self.base.need(self.fd is None, 'Duplicate fresh output admission')
            runner.no_symlinks(out)
            identity = runner.scratch_identity(out)
            ancestors = [(p, (p.stat().st_dev, p.stat().st_ino)) for p in out.parents]
            marker = self.base.regular(out / 'output-ownership.json')
            marker_bytes = marker.read_bytes()
            marker_identity = (marker.stat().st_dev, marker.stat().st_ino)
            fd = os.open(out, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                stat = os.fstat(fd)
                self.base.need([stat.st_dev, stat.st_ino, stat.st_uid] == identity,
                               'Admitted output identity changed')
                self.out, self.identity = out, identity
                self.ancestors = ancestors
                self.marker_bytes, self.marker_identity = marker_bytes, marker_identity
                self.runner, self.fd = runner, fd
                self.validate()
            except BaseException:
                self.fd = None
                os.close(fd)
                raise
            return out
        runner.fresh_output = admitted
        self.restores.append((runner, fresh))

    def validate(self):
        self.base.need(self.fd is not None, 'No positive fresh output admission')
        self.base.need(self.runner.scratch_identity(self.out) == self.identity,
                       'Admitted output identity changed')
        for parent, identity in self.ancestors:
            self.base.need((parent.stat().st_dev, parent.stat().st_ino) == identity,
                           'Admitted output ancestry changed')
        marker = self.base.regular(self.out / 'output-ownership.json')
        self.base.need((marker.stat().st_dev, marker.stat().st_ino) == self.marker_identity
                       and marker.read_bytes() == self.marker_bytes, 'Admitted output marker changed')

    def persist(self, files):
        self.validate()
        for name in files:
            self.base.need(not os.path.lexists(self.out / name), 'Successor evidence collision')
        for name, data in files.items():
            self.validate()
            # The descriptor remains bound to the admitted inode even if a path
            # is replaced between validation and the exclusive file creation.
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o666, dir_fd=self.fd)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data)

    def close(self):
        for runner, fresh in reversed(self.restores):
            runner.fresh_output = fresh
        if self.fd is not None:
            os.close(self.fd)


def run_fixture(base, output, rustc):
    proof = base.verify(True)
    snapshots = {p: base.regular(HERE / p).read_bytes() for p in
                 ('adopt_envelope.py', 'seal.json', 'swift-job.yml', 'job-changes.json', 'source-inputs.json', 'binding.json', 'historical-closure.json')}
    status = None
    # Original runner retains original snapshots and complete failure evidence;
    # retain this prospective authority separately, including on fixture failure.
    errors = []
    ownership = FreshOutput(base)
    load_runner = base.load_runner
    def observed_runner():
        runner, ordinary, runner_proof = load_runner()
        ownership.observe(runner)
        return runner, ordinary, runner_proof
    base.load_runner = observed_runner
    try:
        status = base.run_fixture(output, rustc)
    except BaseException as error:
        errors.append({'phase': 'historical-fixture', 'type': type(error).__name__, 'message': str(error)})
    finally:
        base.load_runner = load_runner
    try:
        base.verify(True)
        for name, data in snapshots.items():
            base.need(base.regular(HERE / name).read_bytes() == data, 'Successor source changed: ' + name)
    except BaseException as error:
        errors.append({'type': type(error).__name__, 'message': str(error)})
    result = {
        'proof': proof, 'fixture_return_status': status, 'errors': errors,
        'source_snapshots': {name: hashlib.sha256(data).hexdigest() for name, data in snapshots.items()},
        'scope': 'Prospective job binding only; original compiler, commands, limits and terminal replay unchanged'
    }
    try:
        files = {'executed-caller-binding-' + name: data for name, data in snapshots.items()}
        files['caller-binding-result.json'] = (json.dumps(result, indent=2) + '\n').encode()
        ownership.persist(files)
    except BaseException as error:
        errors.append({'phase': 'successor-evidence', 'type': type(error).__name__, 'message': str(error)})
        print(json.dumps(result, sort_keys=True), file=sys.stderr)
    finally:
        ownership.close()
    return status if not errors and status is not None else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    verify = sub.add_parser('verify')
    verify.add_argument('--workflow-installed', action='store_true')
    run = sub.add_parser('run')
    run.add_argument('--out', type=Path, required=True)
    run.add_argument('--rustc', required=True)
    args = parser.parse_args()
    base = bind()
    if args.command == 'verify':
        print(json.dumps(base.verify(args.workflow_installed), sort_keys=True))
        return 0
    return run_fixture(base, args.out, args.rustc)


if __name__ == '__main__':
    sys.exit(main())
