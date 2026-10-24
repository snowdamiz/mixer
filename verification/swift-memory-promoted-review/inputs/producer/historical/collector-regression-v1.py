#!/usr/bin/env python3
"""Regression over actual compiler MIR, never a release authorization."""
from pathlib import Path
import collections,gzip,json,unittest
import inventory
HERE=Path(__file__).resolve().parent

class CollectorRegression(unittest.TestCase):
 def test_standalone_caller_promotion_has_eight_positions(self):
  rows,defs,_=inventory.canonical(HERE/'canonical-unit.mir.gz','unit')
  found=[r for r in rows if r['mirFunction']=='memory_pinned_step::promoted[0]']
  self.assertEqual(len(found),8)
  self.assertEqual({r['binding'] for r in found},{'_0','_1'})
  for binding in ['_0','_1']:
   self.assertEqual(collections.Counter(r['position'] for r in found if r['binding']==binding),dict(source=1,argument=1,returned=1,caller=1))
  self.assertEqual(len([d for d in defs if d['function']=='memory_pinned_step::promoted[0]']),1)

 def test_actual_test_module_promotions_are_excluded(self):
  text=gzip.decompress((HERE/'canonical-unit.mir.gz').read_bytes()).decode()
  actual=[line for line in text.splitlines() if line.startswith('const ') and '::promoted[' in line and '::tests::' in line]
  self.assertGreater(len(actual),0)
  self.assertTrue(all(not inventory.selected(line[6:].split(': &',1)[0]) for line in actual))
  _,defs,_=inventory.canonical(HERE/'canonical-unit.mir.gz','unit')
  self.assertFalse(any('::tests::' in d['function'] for d in defs))

 def test_all_original_rows_are_retained(self):
  old=json.loads((HERE/'inputs/behavior-inventory-schema.json').read_text())
  new=json.loads((HERE/'inventory-schema.json').read_text())
  by_field={r['field']:r for r in new}
  self.assertEqual(len(old),4792)
  for row in old:self.assertEqual(by_field[row['field']],row)
  added=[r for r in new if r['field'] not in {x['field'] for x in old}]
  self.assertEqual(len(added),8)
  self.assertTrue(all(r['config']=='unit' and r['mirFunction']=='memory_pinned_step::promoted[0]' for r in added))

if __name__=='__main__':unittest.main(verbosity=2)
