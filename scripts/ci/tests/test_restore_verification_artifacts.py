import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
import zlib


HELPER = Path(__file__).resolve().parents[2] / 'restore-verification-artifacts.py'
TAG = 'refs/tags/verification-archive/2026-11-10-204428'


class RestoreVerificationArtifactsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.workspace = Path(temporary.name).resolve()
        self.repo = self.workspace / 'repo'
        self.repo.mkdir()
        self.output = self.workspace / 'restored'
        self.env = {
            **os.environ,
            'GIT_CONFIG_NOSYSTEM': '1',
            'GIT_CONFIG_GLOBAL': os.devnull,
        }
        self.git('init', '-q', '--object-format=sha1')
        campaign = self.repo / 'verification/campaign'
        campaign.mkdir(parents=True)
        self.binary = bytes(range(256))
        (campaign / 'data[1].bin').write_bytes(self.binary)
        (campaign / 'run.sh').write_bytes(b'#!/bin/sh\nexit 0\n')
        (campaign / 'run.sh').chmod(0o755)
        unsafe = self.repo / 'verification/unsafe'
        unsafe.mkdir()
        (unsafe / 'regular').write_text('regular file')
        (unsafe / 'link').symlink_to('regular')
        self.git('add', '.')
        self.git('commit', '-qm', 'Archived verification')
        self.archive = self.git('rev-parse', 'HEAD').strip().decode()
        self.git('rm', '-qr', 'verification')
        self.metadata = self.repo / 'verification/archive.json'
        self.metadata.parent.mkdir()
        self.write_metadata(self.archive)
        self.git('add', '.')
        self.git('commit', '-qm', 'Archive bulky verification')

    def git(self, *args, repo=None):
        return subprocess.check_output(
            ['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
             '-c', 'commit.gpgsign=false', '-C', str(repo or self.repo), *args],
            env=self.env, timeout=15,
        )

    def write_metadata(self, commit):
        self.metadata.write_text(json.dumps({
            'schema_version': 1, 'archive_commit': commit, 'archive_ref': TAG,
        }))

    def invoke(self, path, output=None, repo=None, fetch_remote=None):
        command = [sys.executable, '-B', str(HELPER), '--repo', str(repo or self.repo),
                   '--output', str(output or self.output), path]
        if fetch_remote:
            command.extend(('--fetch-missing-from', fetch_remote))
        return subprocess.run(
            command, text=True, capture_output=True, env=self.env, timeout=15,
        )

    def test_restores_binary_bytes_and_git_modes_from_the_archive(self):
        result = self.invoke('verification/campaign/')
        self.assertEqual(result.returncode, 0, result.stderr)
        root = self.output / 'verification/campaign'
        self.assertEqual((root / 'data[1].bin').read_bytes(), self.binary)
        self.assertEqual(stat.S_IMODE((root / 'data[1].bin').stat().st_mode), 0o644)
        self.assertEqual((root / 'run.sh').read_bytes(), b'#!/bin/sh\nexit 0\n')
        self.assertEqual(stat.S_IMODE((root / 'run.sh').stat().st_mode), 0o755)
        self.assertFalse((self.repo / 'verification/campaign').exists())

    def test_restores_one_literal_path_into_repo_scratch(self):
        output = self.repo / 'verification/local'
        result = self.invoke('verification/campaign/data[1].bin', output)
        self.assertEqual(result.returncode, 0, result.stderr)
        root = output / 'verification/campaign'
        self.assertEqual(sorted(path.name for path in root.iterdir()), ['data[1].bin'])

    def test_refuses_overwrite(self):
        self.output.mkdir()
        (self.output / 'keep').write_text('original')
        result = self.invoke('verification/campaign')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(sorted(path.name for path in self.output.iterdir()), ['keep'])
        self.assertEqual((self.output / 'keep').read_text(), 'original')

    def test_rejects_path_traversal_and_source_destination(self):
        for path, output in (
            ('verification/../verification/campaign', self.output),
            ('verification/campaign', self.repo / 'verification/restored'),
        ):
            with self.subTest(path=path, output=output):
                result = self.invoke(path, output)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(output.exists())

    def test_rejects_archived_symlinks_before_creating_output(self):
        result = self.invoke('verification/unsafe')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('verification/unsafe/link', result.stderr)
        self.assertFalse(self.output.exists())

    def test_rejects_symlink_output_ancestors(self):
        alias = self.workspace / 'alias'
        real = self.workspace / 'real'
        real.mkdir()
        alias.symlink_to(real, target_is_directory=True)
        result = self.invoke('verification/campaign', alias / 'restored')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((real / 'restored').exists())

    def test_reports_fetch_command_for_missing_archive(self):
        self.write_metadata('1' * 40)
        result = self.invoke('verification/campaign')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f'git fetch --filter=blob:none origin {TAG}', result.stderr)
        self.assertFalse(self.output.exists())

    def test_partial_clone_fetches_only_the_requested_blob_when_enabled(self):
        selected = 'verification/campaign/data[1].bin'
        other = 'verification/campaign/run.sh'
        selected_oid = self.git('rev-parse', f'{self.archive}:{selected}').strip().decode()
        other_oid = self.git('rev-parse', f'{self.archive}:{other}').strip().decode()
        self.git('config', 'uploadpack.allowFilter', 'true')
        self.git('config', 'uploadpack.allowAnySHA1InWant', 'true')
        self.git('tag', TAG.removeprefix('refs/tags/'), self.archive)
        clone = self.workspace / 'partial'
        self.git('clone', '--quiet', '--depth=1', '--filter=blob:none', '--no-tags',
                 self.repo.as_uri(), str(clone))
        self.git('fetch', '--quiet', '--filter=blob:none', 'origin', TAG, repo=clone)

        def object_exists(oid):
            return subprocess.run(
                ['git', '-C', str(clone), 'cat-file', '-e', oid], capture_output=True,
                env={**self.env, 'GIT_NO_LAZY_FETCH': '1'}, timeout=15,
            ).returncode == 0

        self.assertFalse(object_exists(selected_oid))
        result = self.invoke(selected, repo=clone)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('--fetch-missing-from REMOTE', result.stderr)
        self.assertFalse(object_exists(selected_oid))
        self.assertFalse(self.output.exists())

        result = self.invoke(selected, repo=clone, fetch_remote='origin')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.output / selected).read_bytes(), self.binary)
        self.assertTrue(object_exists(selected_oid))
        self.assertFalse(object_exists(other_oid))
        self.assertFalse((clone / selected).exists())

    def test_rejects_corrupt_blob_and_removes_partial_output(self):
        oid = self.git('rev-parse', f'{self.archive}:verification/campaign/run.sh').strip().decode()
        object_path = self.repo / '.git/objects' / oid[:2] / oid[2:]
        object_path.chmod(0o600)
        object_path.write_bytes(zlib.compress(b'blob 17\0#!/bin/sh\nexit 1\n'))
        result = self.invoke('verification/campaign')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('hash verification', result.stderr)
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
