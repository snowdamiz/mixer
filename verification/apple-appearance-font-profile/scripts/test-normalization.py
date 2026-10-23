#!/usr/bin/env python3
from pathlib import Path
import json,unittest
from analyze import choose_profile
ROOT=Path(__file__).resolve().parents[1]
PROFILES=json.loads((ROOT/'type-profiles.json').read_text())['profiles']
class NormalizationTests(unittest.TestCase):
 def test_every_anchor_selects_its_whole_profile(self):
  for p in PROFILES:
   self.assertEqual(choose_profile(round(p['fonts']['body']['pointSize']*1024/17),PROFILES),p['normalizedProfileID'])
 def test_exact_midpoint_prefers_larger_profile(self):
  self.assertEqual(choose_profile(1535,PROFILES),'xxxl');self.assertEqual(choose_profile(1536,PROFILES),'a1')
 def test_monotone_and_clamped(self):
  ids=[p['normalizedProfileID'] for p in PROFILES];last=0
  for scalar in range(1,4097):
   index=ids.index(choose_profile(scalar,PROFILES));self.assertGreaterEqual(index,last);last=index
  self.assertEqual(choose_profile(1,PROFILES),'xs');self.assertEqual(choose_profile(0xffffffff,PROFILES),'a5')
 def test_invalid_preferences_reject(self):
  for value in [0,-1,1.0,True,None,0x100000000]:
   with self.subTest(value=value),self.assertRaises(ValueError):choose_profile(value,PROFILES)
 def test_one_multiplier_cannot_preserve_accessibility_roles(self):
  base=next(p for p in PROFILES if p['normalizedProfileID']=='l')['fonts'];large=next(p for p in PROFILES if p['normalizedProfileID']=='a1')['fonts']
  bodyScale=large['body']['pointSize']/base['body']['pointSize']
  self.assertNotEqual(base['title']['pointSize']*bodyScale,large['title']['pointSize'])
  self.assertNotEqual(base['caption']['pointSize']*bodyScale,large['caption']['pointSize'])
if __name__=='__main__':unittest.main()
