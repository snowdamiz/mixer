#!/usr/bin/env python3
"""Complete input-closure and ordinary-file controls; no child or compiler needed."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock
import materialize_pack as m

HERE = Path(__file__).resolve().parent


class MaterializerControls(unittest.TestCase):
    def setUp(self):
        scratch = HERE / 'control-scratch'
        scratch.mkdir(exist_ok=True)
        self.base = Path(tempfile.mkdtemp(prefix='materializer-', dir=scratch)).resolve()
        self.frozen = self.base / 'frozen'
        self.overlay = self.base / 'pack-overlay'
        self.manifest = self.base / 'overlay-manifest.json'
        shutil.copytree(m.BASE, self.frozen)
        shutil.copytree(m.OVERLAY, self.overlay)
        shutil.copyfile(m.OVERLAY_MANIFEST, self.manifest)
        self.patches = [mock.patch.object(m, name, value) for name, value in {
            'HERE': self.base, 'BASE': self.frozen, 'OVERLAY': self.overlay,
            'OVERLAY_MANIFEST': self.manifest, 'MATERIALIZED': self.base / 'materialized',
        }.items()]
        for patch in self.patches:
            patch.start()

    def tearDown(self):
        for patch in reversed(self.patches):
            patch.stop()
        shutil.rmtree(self.base)
        scratch = HERE / 'control-scratch'
        if scratch.exists() and not any(scratch.iterdir()):
            scratch.rmdir()

    def bad(self, fn, *args):
        with self.assertRaises((RuntimeError, OSError, ValueError, KeyError)):
            fn(*args)

    def repin_overlay(self, change):
        manifest = m.load(self.manifest)
        change(manifest)
        m.save(self.manifest, manifest)
        return mock.patch.object(m, 'OVERLAY_SHA256', m.sha(self.manifest))

    def test_exact_materialization_ordinary_files_and_postflight(self):
        observed = m.materialize()
        self.assertEqual(observed['status'], 'passed-exact-materialization')
        self.assertEqual(len(observed['copies']), 87)
        self.assertEqual(sum(row['source'] == 'frozen-base' for row in observed['copies']), 83)
        self.assertEqual(m.verify_materialized(), observed['inputs'])
        for row in observed['copies']:
            source = (self.overlay if row['source'] == 'overlay' else self.frozen) / row['path']
            target = m.MATERIALIZED / 'pack' / row['path']
            self.assertEqual(m.sha(source), m.sha(target))
            self.assertNotEqual((source.stat().st_dev, source.stat().st_ino),
                                (target.stat().st_dev, target.stat().st_ino))
        self.bad(m.materialize)

    def test_mutated_missing_extra_base_and_manifest_rejected(self):
        path = self.frozen / 'api/loan.rs'
        data = path.read_bytes()
        path.write_bytes(data + b'x')
        self.bad(m.verify_inputs)
        path.unlink()
        self.bad(m.verify_inputs)
        path.write_bytes(data)
        extra = self.frozen / 'extra'
        extra.write_bytes(b'x')
        self.bad(m.verify_inputs)
        extra.unlink()
        extra.mkdir()
        self.bad(m.verify_inputs)
        extra.rmdir()
        path = self.frozen / 'manifest.json'
        path.write_bytes(path.read_bytes() + b' ')
        self.bad(m.verify_inputs)

    def test_mutated_missing_extra_overlay_replacement_rejected(self):
        path = self.overlay / 'source/regression/independent_tests.rs'
        data = path.read_bytes()
        path.write_bytes(data + b'x')
        self.bad(m.verify_inputs)
        path.unlink()
        self.bad(m.verify_inputs)
        path.write_bytes(data)
        extra = self.overlay / 'extra'
        extra.write_bytes(b'x')
        self.bad(m.verify_inputs)
        extra.unlink()
        extra.mkdir()
        self.bad(m.verify_inputs)

    def test_mutated_missing_overlay_manifest_rejected(self):
        self.manifest.write_bytes(self.manifest.read_bytes() + b' ')
        self.bad(m.verify_inputs)
        self.manifest.unlink()
        self.bad(m.verify_inputs)

    def test_duplicate_traversal_and_symlink_overlay_rejected(self):
        for bad_path in ['../escape', '/escape', 'a/../escape', 'a//escape', '.git/x', 'a\\b']:
            with self.subTest(path=bad_path):
                with self.repin_overlay(lambda manifest: manifest['replacements'][0].update(path=bad_path)):
                    self.bad(m.verify_inputs)
                shutil.copyfile(HERE / 'overlay-manifest.json', self.manifest)
        with self.repin_overlay(lambda manifest: manifest['replacements'].append(copy.deepcopy(manifest['replacements'][0]))):
            self.bad(m.verify_inputs)
        shutil.copyfile(HERE / 'overlay-manifest.json', self.manifest)
        path = self.overlay / 'source/regression/independent_tests.rs'
        path.unlink()
        path.symlink_to(self.frozen / 'source/regression/independent_tests.rs')
        self.bad(m.verify_inputs)

    def test_wrong_original_source_preimage_even_with_repinned_manifest(self):
        # Deliberately repin all mutable manifest fields, leaving the immutable
        # accepted preimage constant to reject a different original harness.
        path = self.frozen / 'source/regression/independent_tests.rs'
        path.write_bytes(path.read_bytes() + b'wrong-preimage')
        base = m.load(self.frozen / 'manifest.json')
        for row in base['members']:
            if row['path'] == 'source/regression/independent_tests.rs':
                row.update(bytes=path.stat().st_size, sha256=m.sha(path))
        base['total_bytes'] = sum(row['bytes'] for row in base['members'])
        base['tree_sha256'] = m.tree(base['members'])
        m.save(self.frozen / 'manifest.json', base)
        base_hash = m.sha(self.frozen / 'manifest.json')
        def change(manifest):
            manifest['base'].update(manifest_sha256=base_hash, tree_sha256=base['tree_sha256'])
        with self.repin_overlay(change), mock.patch.object(m, 'BASE_MANIFEST_SHA256', base_hash), mock.patch.object(m, 'BASE_TREE_SHA256', base['tree_sha256']):
            self.bad(m.verify_inputs)

    def test_mutated_missing_extra_and_symlink_candidate_member_rejected(self):
        m.materialize()
        path = m.MATERIALIZED / 'pack/api/loan.rs'
        data = path.read_bytes()
        path.write_bytes(data + b'x')
        self.bad(m.verify_materialized)
        path.unlink()
        self.bad(m.verify_materialized)
        path.symlink_to(self.frozen / 'api/loan.rs')
        self.bad(m.verify_materialized)
        path.unlink()
        path.write_bytes(data)
        (m.MATERIALIZED / 'pack/extra').write_bytes(b'x')
        self.bad(m.verify_materialized)

    def test_ownership_change_and_wrong_output_path_rejected(self):
        m.materialize()
        marker = m.load(m.MATERIALIZED / 'ownership.json')
        marker['identity'][1] += 1
        m.save(m.MATERIALIZED / 'ownership.json', marker)
        self.bad(m.verify_materialized)
        with mock.patch.object(m, 'MATERIALIZED', self.base / 'other'):
            self.bad(m.materialize)

    def test_failed_copy_retains_owned_scratch_and_receipt(self):
        with mock.patch.object(m.shutil, 'copyfileobj', side_effect=OSError(5, 'injected copy failure')):
            self.bad(m.materialize)
        self.assertTrue((m.MATERIALIZED / 'ownership.json').is_file())
        receipt = m.load(m.MATERIALIZED / 'materialization.json')
        self.assertEqual(receipt['status'], 'failed-preserved-owned-materialization')
        self.assertEqual(receipt['error']['message'], '[Errno 5] injected copy failure')


if __name__ == '__main__':
    unittest.main(verbosity=2)
