#!/usr/bin/env python3
"""Pure successor selector and full-manifest controls; no compilers/resources."""
import copy, importlib.util, sys, unittest
from pathlib import Path
sys.dont_write_bytecode = True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('sdk141_admission',HERE/'adopt_sdk.py')
A=importlib.util.module_from_spec(spec);spec.loader.exec_module(A)
class Source141Controls(unittest.TestCase):
    def test_actual_owner_and_current_selector(self):
        result=A.verify(True)
        self.assertEqual(result['source_count'],141)
        self.assertEqual(result['profile']['id'],'mixer.android-source-pair.22')
        self.assertEqual(result['profile']['sdk_count'],26)
        self.assertFalse(result['GA'])
    def test_full127_inverse(self):
        b,s,p=A.admit()
        self.assertEqual(A.inverse(b,s),A.load(HERE/'predecessor-source-inputs.json'))
        self.assertEqual(len(p),127)
    def test_incomplete_source_transition_refuses(self):
        b,s,p=A.admit()
        bad=copy.deepcopy(b)
        bad['sdk_transition']['changes'].pop(next(iter(bad['sdk_transition']['changes'])))
        with self.assertRaises(RuntimeError):
            A.inverse(bad,s)
if __name__=='__main__':unittest.main(verbosity=2)
