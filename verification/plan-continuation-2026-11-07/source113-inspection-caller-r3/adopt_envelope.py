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
CALLER_BEFORE = "          swift test --package-path cli\n"
CALLER_AFTER = "          MIXER_CLI_HOST_ROOT=\"$RUNNER_TEMP/cli-host-${{ github.job }}-${{ github.run_id }}-${{ github.run_attempt }}\"\n          python3 -I -B -S scripts/ci/prepare-cli-host-tests.py \\\n            --toolchain-receipt \"$RUNNER_TEMP/apple-toolchain.json\" \\\n            --output \"$MIXER_CLI_HOST_ROOT\"\n          (\n            source \"$MIXER_CLI_HOST_ROOT/environment.sh\"\n            swift build --package-path cli --product mixer -j 2\n            MIXER_STORE_CLI_BIN_DIR=\"$(swift build --package-path cli --product mixer -j 2 --show-bin-path)\"\n            test -x \"$MIXER_STORE_CLI_BIN_DIR/mixer\"\n            MIXER_STORE_TEST_CLI=\"$MIXER_STORE_CLI_BIN_DIR/mixer\" swift test --package-path cli -j 2\n          )\n"

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
        base.need(seal['member_count'] == len(seal['members']) and seal['tree_sha256'] == base.tree(seal['members']), 'Successor seal differs')
        ignored = {'control-scratch', '__pycache__'}
        base.need(not any(p.is_symlink() for p in HERE.rglob('*') if p.relative_to(HERE).parts[0] not in ignored), 'Successor shipping symlink forbidden')
        observed = sorted(p.relative_to(HERE).as_posix() for p in HERE.rglob('*') if p.is_file() and p.relative_to(HERE).parts[0] not in ignored and p.relative_to(HERE).as_posix() != 'seal.json')
        base.need(observed == [r['path'] for r in seal['members']], 'Successor shipping closure differs')
        history = json.loads(base.regular(HERE / 'historical-closure.json').read_bytes(), object_pairs_hook=base.unique_object)
        base.check_rows(ROOT, history)
        prior = HERE.parent / 'source113-sparse-closure-fix-r2'
        prior_seal = json.loads(base.regular(prior / 'seal.json').read_bytes(), object_pairs_hook=base.unique_object)
        base.check_rows(prior, prior_seal['members'])
        base.need(prior_seal['member_count'] == 18 and prior_seal['tree_sha256'] == base.tree(prior_seal['members']), 'Historical source113 seal differs')
        frozen = json.loads(base.regular(HERE / 'source-inputs.json').read_bytes(), object_pairs_hook=base.unique_object)
        base.check_rows(ROOT, [dict(path=p, **r) for p,r in sorted(frozen.items())])
        owner = base.module_at('combined_source113_owner', ROOT / 'scripts/ci/check-android-generated-java.py')
        profile = owner.load_profile(ROOT)
        actual = owner.source_inputs(profile)
        base.need(actual == frozen, 'Current owning source closure differs')
        binding = json.loads(base.regular(HERE / 'binding.json').read_bytes(), object_pairs_hook=base.unique_object)
        digest = owner.source_digest(actual)
        raw_review = base.regular(HERE / 'inspection-review.json').read_bytes()
        base.need(hashlib.sha256(raw_review).hexdigest() == '6b51eafe93f29e05c9bf527a5d39625e8a2cffbcdfd1fbb4799ac80adb7a3de6', 'Accepted R3 raw review hash differs')
        review = json.loads(raw_review, object_pairs_hook=base.unique_object)
        accepted = review.get('candidate', {})
        base.need(review.get('verdict') == 'ACCEPT' and accepted.get('source113Proposed') == digest
                  and accepted.get('patchSHA256') == 'da94deb88a987e294c7ac830ecae32dd060e2a25035001ae92977e2a91236b04'
                  and accepted.get('checkerSHA256') == '6103a13c065181ccd5dd76d6c6ee7d827dd091354b1aed3eea11887895bc2822'
                  and base.sha(ROOT / 'scripts/ci/check-android-generated-java.py') == accepted.get('checkerSHA256'), 'Accepted R3 inspection identity differs')
        base.need(binding.get('upstream_inspection') == {'member':'inspection-review.json', 'sha256':hashlib.sha256(raw_review).hexdigest(), 'source113':digest, 'patchSHA256':accepted['patchSHA256'], 'checkerSHA256':accepted['checkerSHA256'], 'scope':'accepted R5 real-tool temporary-directory source protocol only; no qualification transfer'}, 'Upstream inspection binding differs')
        base.need(binding.get('fixture_dispatch') == {'host_rust_fixture_after_exact_checks':True, 'scope':'host fixture only; installed source/job/seal/raw accepted R5 checks precede dispatch', 'combinedAccepted':False, 'runtime':False, 'GA':False, 'exactWindow':False}, 'Host-only fixture dispatch contract differs')
        base.need(binding.get('adoption') == {'allowed':False, 'status':'CANDIDATE_PENDING_COMBINED_REVIEW', 'canonicalAdopted':False}
                  and not any(binding['qualification'].values()), 'Candidate authority must remain pending')
        base.need(len(actual) == 113 and digest == '524e7e2934c34501ff23dae13e448cc13ae53a874d78e86fefeba556e2a65292' and binding['source']['count'] == 113 and binding['source']['sha256'] == digest, 'Bound source closure differs')
        base.need(binding['profile'] == {'id':profile['id'], 'sdk_count':len(profile['sdk_files']), 'sdk_sha256':profile['sdk_compatibility_sha256'], 'adapter_count':len(profile['adapter_files']), 'adapter_sha256':profile['adapter_compatibility_sha256'], 'java_sources':len(owner.java_roster(profile))}, 'Accepted profile binding differs')
        callers = json.loads(base.regular(HERE / 'caller-inputs.json').read_bytes(), object_pairs_hook=base.unique_object)
        base.check_rows(ROOT, callers)
        expected = base.regular(HERE / 'current-swift-job.yml').read_text()
        base.need(expected == base.regular(prior / 'swift-job.yml').read_text(), 'Historical predecessor job differs')
        accepted = base.regular(HERE / 'accepted-swift-job.yml').read_text()
        base.need(hashlib.sha256(accepted.encode()).hexdigest() == binding['accepted_caller_job_sha256'], 'Accepted caller whole-job differs')
        for change in json.loads(base.regular(HERE / 'job-changes.json').read_bytes(), object_pairs_hook=base.unique_object):
            base.need(expected.count(change['before']) == change['count'], 'Successor edit preimage differs')
            expected = expected.replace(change['before'], change['after'])
        base.need(expected == base.regular(HERE / 'swift-job.yml').read_text(), 'Successor job derivation differs')
        base.need(CALLER_AFTER in expected and 'scripts/ci/prepare-cli-host-tests.py' in expected, 'Accepted caller missing')
        if installed:
            base.need(base.job_text(base.regular(WORKFLOW).read_text()) == expected, 'Installed ordinary Swift job differs from successor candidate')
        return {**proof, 'historical_workflow_job_sha256':proof['workflow_job_sha256'], 'workflow_job_sha256':hashlib.sha256(expected.encode()).hexdigest(), 'installed_job_verified':installed, 'caller_binding_seal_sha256':base.sha(HERE / 'seal.json'), 'source_count':len(actual), 'source_sha256':digest, 'profile':binding['profile'], 'historical_closure_sha256':base.sha(HERE / 'historical-closure.json')}
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
    # Verify every installed authority before resource acquisition or fixture dispatch.
    base.verify(True)
    admission = json.loads(base.regular(HERE / 'binding.json').read_bytes())['fixture_dispatch']
    base.need(admission['host_rust_fixture_after_exact_checks'] is True, 'Host fixture dispatch disabled')
    return run_fixture(base, args.out, args.rustc)


if __name__ == '__main__':
    sys.exit(main())
