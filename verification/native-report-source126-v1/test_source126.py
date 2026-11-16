#!/usr/bin/env python3
import copy
import importlib.util
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('typed126_subject',HERE/'adopt_envelope.py')
A=importlib.util.module_from_spec(spec);spec.loader.exec_module(A)

class Source126Controls(unittest.TestCase):
    def setUp(self):
        self.b=A.load_json(HERE/'binding.json')
        self.s=A.load_json(HERE/'current-source-inputs.json')

    def test_actual126_and_immutable121_119_guards(self):
        p=A.verify(True)
        self.assertEqual(p['source_count'],126)
        self.assertEqual(p['historical121']['source_count'],121)
        self.assertEqual(p['historical121']['historical119']['source_count'],119)

    def test_exact121_inverse_and_unaffected_rows(self):
        p=A.inverse126(self.b,self.s)
        self.assertEqual(len(p),121)
        self.assertEqual(len(set(self.s)-set(p)),5)
        for name in set(p)-A.PRODUCTS:self.assertEqual(p[name],self.s[name])

    def test_one_replaced_and_five_added(self):
        c=self.b['report_transition']['changes']
        self.assertEqual(sum(v['before'] is None for v in c.values()),5)
        self.assertIsNotNone(c['cli/Sources/MixerBuild/NativeBuildOutput.swift']['before'])

    def test_no_test_production_row(self):
        self.assertFalse(any('/Tests/' in p for p in self.s))
        self.assertNotIn(self.b['ordinary_test']['path'],self.s)

    def test_row_partition_is_exact(self):
        from collections import Counter
        self.assertEqual(dict(Counter(p.split('/')[0] for p in self.s)),
                         {'cli':31,'native':27,'scripts':2,'sdk':53,'updates':13})

    def test_corrected_snapshot_only(self):
        self.assertEqual(self.s['cli/Sources/MixerBuild/BuildInputSnapshot.swift']['sha256'],
                         '997550082eb2816caefcbe68dc960ee7f2afe1bea8d055e41cca5b5eac37bf51')

    def test_schema_number_alias_unknown_and_downgrade_refuse(self):
        for key,v in [('schema',True),('sourceCountBefore',True),('sourceCountAfter',True),
                      ('sourceCountAfter',121),('qualification',0),('type','CLI121'),('extra',False)]:
            b=copy.deepcopy(self.b);b['report_transition'][key]=v
            with self.subTest(key=key),self.assertRaises(RuntimeError):A.inverse126(b,self.s)

    def test_selected_mutation_missing_extra_refuse(self):
        name=next(iter(self.s));bad=[]
        s=copy.deepcopy(self.s);s[name]['sha256']='0'*64;bad.append(s)
        s=dict(self.s);s.pop(name);bad.append(s)
        s=dict(self.s);s['cli/Sources/MixerBuild/Extra.swift']=self.s[name];bad.append(s)
        for s in bad:
            with self.assertRaises(RuntimeError):A.inverse126(self.b,s)

    def test_every_partial_inverse_refuses(self):
        for name in A.PRODUCTS:
            b=copy.deepcopy(self.b);b['report_transition']['changes'][name]['before']={'bytes':1,'sha256':'0'*64}
            with self.assertRaises(RuntimeError):A.inverse126(b,self.s)

    def test_original121_authority_and_seal_unchanged(self):
        p=A.ROOT/A.PREVIOUS
        A.check_rows(p,self.b['predecessor_authority'])
        seal=A.load_json(p/'seal.json')
        self.assertEqual(A.digest(seal['members']),seal['tree_sha256'])
        self.assertEqual(seal['tree_sha256'],'9744a3d5885b023f589fd46b1eca760e7d439055ce14f2c0ddcc5ff63db85773')

    def test_corrected_ordinary_and_helper_exclusion(self):
        t=self.b['ordinary_test']
        self.assertEqual((t['original_cases'],t['added_unit_cases']),(18,6))
        self.assertEqual(A.row(A.read(A.ROOT/t['path'])),t['identity'])
        self.assertEqual(self.b['frozen_composition']['map']['sha256'],'d4ff1aa82f4822c51362265d06033fe69d129271ad1a8bad6e6d20688b2bc6d8')
        self.assertIs(self.b['frozen_composition']['private_helper_and_package_excluded'],True)

    def test_all_gates_false(self):
        self.assertEqual(set(self.b['root_gates']),A.GATES)
        for v in self.b['root_gates'].values():self.assertIs(v,False)
        for k in ('adoption','activation','aggregate','GA'):self.assertIs(self.b[k],False)

    def test_pair21_exact(self):
        old=A.load_json(A.ROOT/A.PREVIOUS/'binding.json')
        self.assertEqual(self.b['profile'],old['profile'])
        self.assertEqual(self.b['renderer_pair21_transition'],old['renderer_pair21_transition'])

    def test_duplicate_keys_and_escapes_refuse(self):
        with self.assertRaises(RuntimeError):A.unique([('schema',1),('schema',1)])
        for p in ('../bad','/bad','x/../bad','x\\bad','.git/HEAD','x\0bad'):
            with self.assertRaises(RuntimeError):A.relative(p)


class SourceBoundaryControls(unittest.TestCase):
    def test_derived_python_cache_rows_refuse_before_any_read(self):
        from unittest.mock import patch
        paths = [
            'native/android/tests/__pycache__/private_owner_cleanup_control.cpython-314.pyc',
            'native/android/tests/__pycache__/private_owner_commands.cpython-314.pyc',
            'pkg/__pycache__/source.py', 'pkg/generated.pyc', 'pkg/generated.pyo',
            'pkg/generated.PYC']
        for name in paths:
            with self.subTest(path=name), patch.object(A, 'read', side_effect=AssertionError('must not read')):
                with self.assertRaisesRegex(RuntimeError, 'Derived Python cache'):
                    A.check_rows(A.ROOT, {name: {'bytes': 1, 'sha256': '0' * 64}})
    def test_valid_original_source_is_accepted(self):
        name = 'native/android/tests/private_owner_cleanup_control.py'
        self.assertEqual(A.source_input_path(name), Path(name))
        A.check_rows(A.ROOT, {name: A.row(A.read(A.ROOT / name))})

if __name__=='__main__':unittest.main(verbosity=2)
