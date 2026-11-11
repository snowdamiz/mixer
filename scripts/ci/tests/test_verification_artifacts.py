"""Exercise verification retention policy through a real Git index."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


CHECK = Path(__file__).resolve().parents[2] / 'check-verification-artifacts.py'
POLICY = 'scripts/verification-artifact-policy.json'


class VerificationArtifactTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='mixer-verification-policy-')
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name)
        self.git('init', '--quiet')
        self.git('config', 'user.name', 'Mixer policy tests')
        self.git('config', 'user.email', 'tests@example.invalid')
        self.policy = {
            'schema_version': 1,
            'max_total_bytes': 24,
            'max_files': 4,
            'max_file_bytes': 12,
            'large_files': {},
            'generated_files': {},
        }
        self.stage_policy()

    def git(self, *args, repo=None):
        return subprocess.run(['git', *args], cwd=repo or self.repo, check=True,
                              capture_output=True, text=True, timeout=15).stdout.strip()

    def stage(self, member, content):
        destination = self.repo / member
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        self.git('add', '--force', '--', member)
        return self.git('rev-parse', f':{member}')

    def stage_policy(self):
        self.stage(POLICY, json.dumps(self.policy).encode())

    def check(self, expected, *diagnostics, repo=None, fetch_remote=None):
        command = [sys.executable, str(CHECK), '--repo', str(repo or self.repo)]
        if fetch_remote:
            command.extend(('--fetch-missing-from', fetch_remote))
        result = subprocess.run(command, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        for diagnostic in diagnostics:
            self.assertIn(diagnostic, result.stdout + result.stderr)

    def test_uses_staged_fixture_and_policy_bytes(self):
        member = 'verification/fixtures/oracle.bin'
        self.stage(member, b'\x00\xff')
        self.stage('verification/receipts/summary.json', b'{}')
        (self.repo / member).write_bytes(b'x' * 100)
        (self.repo / POLICY).write_text('not JSON')
        self.check(0)

    def test_force_added_generated_output_is_rejected_when_sparse(self):
        member = 'verification/campaign/replica.apk'
        self.stage('.gitignore', b'*.apk\n')
        self.stage(member, b'APK')
        self.git('commit', '--quiet', '-m', 'Seed tracked output')
        self.git('sparse-checkout', 'set', '--no-cone', '/scripts/')
        self.assertFalse((self.repo / member).exists())
        self.check(1, member, 'generated output')

    def test_partial_clone_reads_sizes_without_materializing_fixtures(self):
        member = 'verification/fixtures/oracle.bin'
        self.stage(member, b'\x00\xff')
        self.git('commit', '--quiet', '-m', 'Seed fixture')
        self.git('config', 'uploadpack.allowFilter', 'true')
        self.git('config', 'uploadpack.allowAnySHA1InWant', 'true')
        with tempfile.TemporaryDirectory(prefix='mixer-verification-policy-clone-') as clone:
            self.git('clone', '--filter=blob:none', '--no-checkout', self.repo.as_uri(), clone)
            self.git('sparse-checkout', 'set', '--no-cone', '/scripts/', repo=clone)
            self.git('checkout', '--quiet', repo=clone)
            self.check(1, '1 staged verification blobs are unavailable locally', repo=clone)
            self.check(0, '2 bytes', repo=clone, fetch_remote='origin')
            self.assertFalse((Path(clone) / member).exists())

    def test_build_directory_is_rejected(self):
        member = 'verification/campaign/node_modules/tree/fixture.json'
        self.stage(member, b'{}')
        self.check(1, member, 'generated output')

    def test_rejects_non_regular_index_modes(self):
        member = 'verification/fixture'
        (self.repo / 'verification').mkdir()
        (self.repo / member).symlink_to('../scripts/verification-artifact-policy.json')
        self.git('add', '--', member)
        self.check(1, member, 'mode 120000')
        self.git('rm', '--force', '--', member)
        self.git('commit', '--quiet', '-m', 'Seed Gitlink target')
        self.git('update-index', '--add', '--cacheinfo', f'160000,{self.git("rev-parse", "HEAD")},{member}')
        self.check(1, member, 'mode 160000')

    def test_checks_file_size_against_staged_bytes(self):
        member = 'verification/fixtures/large.bin'
        self.stage(member, b'x' * 13)
        (self.repo / member).write_bytes(b'x')
        self.check(1, member, 'max_file_bytes')

    def test_counts_every_path_against_total_size_even_for_duplicate_blobs(self):
        for name in ('left', 'right', 'center'):
            self.stage(f'verification/{name}.bin', b'x' * 9)
        self.check(1, '27', 'max_total_bytes')

    def test_checks_total_file_count(self):
        for number in range(5):
            self.stage(f'verification/receipt-{number}.json', b'{}')
        self.check(1, '5', 'max_files')

    def test_canonical_exceptions_are_bound_to_staged_blob_and_size(self):
        generated = 'verification/fixtures/known.wasm.gz'
        large = 'verification/fixtures/oracle.bin'
        self.policy['generated_files'][generated] = {
            'oid': self.stage(generated, b'wasm'), 'size': 4, 'reason': 'Pinned corpus',
        }
        self.policy['large_files'][large] = {
            'oid': self.stage(large, b'x' * 13), 'size': 13, 'reason': 'Pinned oracle',
        }
        self.stage_policy()
        self.check(0)
        self.stage(large, b'y' * 13)
        self.check(1, large, 'max_file_bytes')
        self.stage(large, b'x' * 13)
        self.stage(generated, b'other')
        self.check(1, generated, 'generated output')


if __name__ == '__main__':
    unittest.main()
