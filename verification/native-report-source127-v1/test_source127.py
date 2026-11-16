#!/usr/bin/env python3
import copy, importlib.util, json, shutil, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('typed127_subject',HERE/'adopt_envelope.py')
A=importlib.util.module_from_spec(spec);spec.loader.exec_module(A)
def control_scratch():
 scratch = HERE/'control-scratch'
 try:
  scratch.mkdir(mode=0o700)
 except FileExistsError:
  pass
 if scratch.is_symlink() or not scratch.is_dir():
  raise RuntimeError('control-scratch must be an owned directory')
 return scratch

class Source127Controls(unittest.TestCase):
 def setUp(self):
  self.b=A.load_json(HERE/'binding.json');self.s=A.load_json(HERE/'current-source-inputs.json')
 def test_actual127_and_all_historical_guards(self):
  v=A.verify(True);self.assertEqual(v['source_count'],127)
  self.assertEqual(v['historical126']['source_count'],126)
  self.assertEqual(v['historical126']['historical121']['historical119']['source_count'],119)
 def test_full126_inverse(self):
  self.assertEqual(A.inverse127(self.b,self.s),A.load_json(A.ROOT/A.PREVIOUS/'current-source-inputs.json'))
 def test_all_other126_rows_unchanged(self):
  p=A.inverse127(self.b,self.s)
  for n in set(p)-A.PRODUCTS:self.assertEqual(p[n],self.s[n])
 def test_one_added_one_replaced(self):
  c=self.b['report_transition']['changes']
  self.assertIsNone(c['cli/Sources/MixerBuild/SameBuildPublicReport.swift']['before'])
  self.assertIsNotNone(c['cli/Sources/MixerCLI/main.swift']['before'])
 def test_adapter_exact_reviewed_bytes(self):
  self.assertEqual(self.s['cli/Sources/MixerBuild/SameBuildPublicReport.swift']['sha256'],'b71e954c3c03334e6ced0eec9b0b3291fe3461a9d8c0273afff3bd085535dd35')
 def test_ordinary24_plus6_excluded_from_production(self):
  t=self.b['ordinary_test'];self.assertEqual((t['original_cases'],t['added_unit_cases']),(24,6));self.assertNotIn(t['path'],self.s)
 def test_private_package_never_adopted(self):
  self.assertTrue(self.b['frozen_composition']['private_helper_and_package_excluded'])
  p='cli/Package.swift';self.assertEqual(self.s[p],A.load_json(HERE/'predecessor-source-inputs.json')[p])
 def test_numeric_aliases_refuse(self):
  for k in ['schema','sourceCountBefore','sourceCountAfter']:
   b=copy.deepcopy(self.b);b['report_transition'][k]=True
   with self.assertRaises(RuntimeError):A.inverse127(b,self.s)
 def test_downgrade_and_type_refuse(self):
  for k,v in [('type','source126'),('sourceCountAfter',126),('qualification',0),('extra',False)]:
   b=copy.deepcopy(self.b);b['report_transition'][k]=v
   with self.assertRaises(RuntimeError):A.inverse127(b,self.s)
 def test_missing_and_extra_production_refuse(self):
  for n in ['cli/Sources/MixerBuild/SameBuildPublicReport.swift',next(iter(self.s))]:
   s=dict(self.s);s.pop(n)
   with self.assertRaises(RuntimeError):A.inverse127(self.b,s)
  s=dict(self.s);s['cli/Sources/Unexpected.swift']=next(iter(s.values()))
  with self.assertRaises(RuntimeError):A.inverse127(self.b,s)
 def test_mutated_row_refuses(self):
  s=copy.deepcopy(self.s);s[next(iter(s))]['sha256']='0'*64
  with self.assertRaises(RuntimeError):A.inverse127(self.b,s)
 def test_every_partial_inverse_refuses(self):
  for n in A.PRODUCTS:
   b=copy.deepcopy(self.b);b['report_transition']['changes'][n]['before']={'bytes':1,'sha256':'0'*64}
   with self.assertRaises(RuntimeError):A.inverse127(b,self.s)
 def test_current126_authority_exact(self):
  A.closed_members(A.ROOT/A.PREVIOUS,self.b['predecessor_authority']);A.check_rows(A.ROOT/A.PREVIOUS,self.b['predecessor_authority'])
 def test_current126_seal_exact(self):
  self.assertEqual(A.row(A.read(A.ROOT/A.PREVIOUS/'seal.json')),self.b['predecessor_seal'])
 def test_pair21_byte_identity(self):
  p=A.load_json(A.ROOT/A.PREVIOUS/'binding.json')
  for k in ['profile','renderer_pair21_transition']:self.assertEqual(self.b[k],p[k])
 def test_all_root_gates_false(self):
  self.assertEqual(set(self.b['root_gates']),A.GATES)
  for v in self.b['root_gates'].values():self.assertIs(v,False)
  for k in ['adoption','activation','aggregate','GA','holdsReleased']:self.assertIs(self.b[k],False)
 def test_cache_paths_rejected_before_reads(self):
  for n in ['x/__pycache__/a.py','x/a.pyc','x/a.pyo','x/a.PYC']:
   with patch.object(A,'read',side_effect=AssertionError('read forbidden')):
    with self.assertRaises(RuntimeError):A.check_rows(A.ROOT,{n:{'bytes':1,'sha256':'0'*64}})
 def test_extra_authority_member_refuses_in_isolated_copy(self):
  with tempfile.TemporaryDirectory(dir=control_scratch()) as d:
   p=Path(d)/'authority';shutil.copytree(HERE,p,ignore=shutil.ignore_patterns('control-scratch'))
   (p/'unsealed.json').write_text('{}')
   with self.assertRaises(RuntimeError):A.closed_members(p,{*A.load_json(HERE/'seal.json')['members'],'seal.json'})
 def test_cache_authority_member_refuses_in_isolated_copy(self):
  with tempfile.TemporaryDirectory(dir=control_scratch()) as d:
   p=Path(d)/'authority';shutil.copytree(HERE,p,ignore=shutil.ignore_patterns('control-scratch'))
   (p/'__pycache__').mkdir()
   with self.assertRaises(RuntimeError):A.closed_members(p,{*A.load_json(HERE/'seal.json')['members'],'seal.json'})
 def test_path_escapes_and_duplicate_keys_refuse(self):
  with self.assertRaises(RuntimeError):A.unique([('x',1),('x',2)])
  for p in ['../bad','/bad','x/../bad','x\\bad','.git/HEAD','x\0bad']:
   with self.assertRaises(RuntimeError):A.relative(p)
if __name__=='__main__':unittest.main(verbosity=2)
