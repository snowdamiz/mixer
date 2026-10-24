"""Synthetic host controls only; no native compiler/process is started."""
import hashlib
import io
import os
import pathlib
import tarfile
import tempfile
import unittest
from unittest import mock
import build_runner as b


class RecorderControls(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix='host-control-', dir=b.BASE)
        self.base = pathlib.Path(self.scratch.name)
        self.addCleanup(self.scratch.cleanup)

    def fixture(self):
        folder = self.base / 'products'
        folder.mkdir(mode=0o750)
        (folder / 'runner').write_bytes(b'\x00executable\xff')
        (folder / 'runner').chmod(0o751)
        (folder / 'sub').mkdir(mode=0o700)
        (folder / 'sub/data').write_bytes(b'payload')
        (folder / 'sub/data').chmod(0o640)
        (folder / 'link').symlink_to('sub/data')
        return folder

    def test_selected_seals_inputs_and_tools_revalidate_without_process(self):
        with mock.patch.object(b.subprocess, 'Popen', side_effect=AssertionError('No process permitted')):
            observed = b.revalidate()
            tools = b.tool_metadata()
        self.assertEqual([len(observed[k]) for k in ['producer', 'review', 'inputBindings']], [80, 117, 2537])
        self.assertEqual(tools['XcodeVersion'], '26.6')
        self.assertEqual(tools['SDKVersion'], '26.5')

    def test_existing_empty_destination_refused(self):
        folder = self.base / 'existing'
        folder.mkdir()
        with self.assertRaisesRegex(ValueError, 'Fresh absent'):
            b.absent_canonical(folder)

    def test_broken_symlink_destination_refused(self):
        destination = self.base / 'link'
        destination.symlink_to('missing')
        with self.assertRaisesRegex(ValueError, 'Fresh absent'):
            b.absent_canonical(destination)
        self.assertTrue(destination.is_symlink())

    def test_spent_attempt_refuses_before_preflight_or_process(self):
        (self.base / 'attempt-started.json').write_text('{}')
        with mock.patch.object(b, 'BASE', self.base), mock.patch.object(b, 'revalidate', side_effect=AssertionError('No retry')):
            with self.assertRaisesRegex(ValueError, 'already spent'):
                b.compile_once()

    def test_input_mutation_rejects(self):
        file = self.base / 'input'
        file.write_bytes(b'first')
        binding = {str(file): b.sha(file)}
        file.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'Bound file changed'):
            b.bound_files(binding)

    def test_tree_captures_modes_empty_directories_and_links(self):
        folder = self.fixture()
        (folder / 'empty').mkdir(mode=0o711)
        manifest = b.tree(folder)
        self.assertEqual(manifest['runner']['mode'], 0o751)
        self.assertEqual(manifest['empty'], {'kind': 'directory', 'mode': 0o711})
        self.assertEqual(manifest['link'], {'kind': 'symlink', 'mode': 0o755, 'target': 'sub/data'})

    def test_escaping_symlink_is_rejected_and_preserved(self):
        folder = self.fixture()
        (folder / 'escape').symlink_to('../outside')
        with self.assertRaisesRegex(ValueError, 'Escaping'):
            b.tree(folder)
        self.assertTrue((folder / 'escape').is_symlink())

    def test_archive_verifies_binary_bytes_modes_and_links(self):
        folder = self.fixture()
        manifest = b.tree(folder)
        archive = self.base / 'archive.tar.gz'
        b.archive_tree(folder, manifest, archive)
        self.assertEqual(b.verify_archive(archive, manifest), manifest)

    def test_archive_mode_corruption_fails(self):
        folder = self.fixture()
        manifest = b.tree(folder)
        archive = self.base / 'archive.tar.gz'
        b.archive_tree(folder, manifest, archive)
        expected = {k: dict(v) for k, v in manifest.items()}
        expected['runner']['mode'] = 0o755
        with self.assertRaisesRegex(ValueError, 'Archive bytes, modes'):
            b.verify_archive(archive, expected)

    def test_archive_payload_corruption_fails(self):
        folder = self.fixture()
        manifest = b.tree(folder)
        archive = self.base / 'archive.tar.gz'
        b.archive_tree(folder, manifest, archive)
        expected = {k: dict(v) for k, v in manifest.items()}
        expected['runner']['sha256'] = hashlib.sha256(b'wrong').hexdigest()
        with self.assertRaisesRegex(ValueError, 'Archive bytes, modes'):
            b.verify_archive(archive, expected)

    def test_archive_duplicate_member_refused(self):
        archive = self.base / 'duplicate.tar.gz'
        with tarfile.open(archive, 'w:gz') as stream:
            for _ in range(2):
                info = tarfile.TarInfo('same')
                info.size = 1
                stream.addfile(info, io.BytesIO(b'a'))
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            b.verify_archive(archive, {})

    def test_changed_tree_refuses_archive_creation(self):
        folder = self.fixture()
        manifest = b.tree(folder)
        (folder / 'runner').chmod(0o700)
        archive = self.base / 'archive.tar.gz'
        with self.assertRaisesRegex(ValueError, 'changed before archive'):
            b.archive_tree(folder, manifest, archive)
        self.assertFalse(archive.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
