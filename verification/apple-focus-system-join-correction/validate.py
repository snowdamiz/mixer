#!/usr/bin/env python3
"""Read-only host validation of this isolated correction and its sealed parents."""
import difflib
import hashlib
import json
import pathlib
import stat
import sys
import tarfile
import traceback
import unittest

sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent
ROOT=H.parents[1]
import observation as o
import test_join_correction as correction

sha=lambda b:hashlib.sha256(b).hexdigest()
checks=[]
def check(name,ok,detail=None):
 checks.append({'name':name,'passed':ok is True,'detail':detail})
 if ok is not True:raise AssertionError(name)
def write(path,value):path.write_bytes(o.encoded(value)+b'\n')

def seals(stage):
 totals={}
 for name,expected,count in [
  ('apple-focus-system-observation','5d88cd0069f7e83e73b95903ecf0e9e6b721a73328193653e8e1da8903c81427',177),
  ('apple-focus-system-observation-review','e66d1f5710d5614fc668bec3fc6759fb6080a91002516f13d43994dca2ab35a4',51),
 ]:
  raw=(ROOT/'verification'/name/'handoff.json').read_bytes()
  check(stage+' exact sealed handoff '+name,sha(raw)==expected)
  members=json.loads(raw)['members']
  check(stage+' exact member count '+name,len(members)==count)
  for relative,entry in members.items():
   path=ROOT/relative;data=path.read_bytes()
   check(stage+' sealed member '+relative,len(data)==entry['bytes'] and sha(data)==entry['sha256'] and stat.S_IMODE(path.stat().st_mode)==entry['mode'])
  totals[name]=len(members)
 return totals

def run(output):
 totals=seals('before')
 bindings=json.loads((H/'input-bindings.json').read_bytes())
 for relative,entry in bindings['files'].items():
  raw=(H/relative).read_bytes()
  check('copied exact input '+relative,len(raw)==entry['bytes'] and sha(raw)==entry['sha256'])
 check('selected raw input hashes independently fixed',o.RAW_INPUTS=={
  'before':(16451,'82581f55bd299fb623d85a39fa726ee072bb54fb065164da6618fec63c2c9c3d'),
  'after':(21153,'160f124cb50b74006b7f6791c0aab6a683dab65a9ad9c193604569efcf2a7a9b'),
  'witness':(1816,'388655651136e672499be043e1188733ca6dd549af67f755185332a77b90d70e')})
 source=H/'inputs/source.tar.gz'
 check('exact unchanged accepted source archive',sha(source.read_bytes())=='d1262c1e16a4decdca0ecbfdc278b7eaa1282f47d68776bfdede235157019cda')
 with tarfile.open(source) as archive:
  members=archive.getmembers()
  check('exact40 unique regular source members',len(members)==40 and len({m.name for m in members})==40 and all(m.isfile() for m in members))
  source_members={m.name:{'bytes':m.size,'sha256':sha(archive.extractfile(m).read())} for m in members}
 write(output/'source-members.json',{'archiveSHA256':sha(source.read_bytes()),'members':source_members,'changedSwiftMembers':[]})
 for original,modified,diff in [('inputs/observation.py','observation.py','observation.diff'),('inputs/test_observation.py','test_observation.py','test-fixture.diff')]:
  (output/diff).write_text(''.join(difflib.unified_diff((H/original).read_text().splitlines(True),(H/modified).read_text().splitlines(True),fromfile=original,tofile=modified)))
 suite=unittest.defaultTestLoader.discover(str(H),pattern='test_*.py')
 result=unittest.TextTestRunner(stream=sys.stderr,verbosity=2).run(suite)
 write(output/'focused-controls.json',{'schema':1,'scope':'Frozen V7 originals with synthetic diagnostic rows only','controls':correction.CONTROLS,'nativePass':False})
 seals('after')
 check('all original and corrected host controls',result.wasSuccessful(),{'testMethods':result.testsRun,'failures':len(result.failures),'errors':len(result.errors)})
 check('owned Python caches absent',not list(H.rglob('__pycache__')))
 write(output/'validation.json',{'schema':1,'passed':True,'scope':'Host-adapter-only frozen V7 replay correction; no native selection','hostTestMethods':result.testsRun,'focusedControls':len(correction.CONTROLS),'checksPassed':len(checks),'parentSealsExact':totals,'candidateArchiveSHA256':sha(source.read_bytes()),'candidateSourceMembers':40,'changedSwiftMembers':[],'originalOraclePassed':False,'originalFailingPredicates':['actualNativeFocusTraversal'],'originalVerdictUnchanged':True,'nativePass':False,'sourceHostAccepted':False,'nativeAccepted':False,'gaAccepted':False,'physicalPhones':'disconnected-deferred','compilerInvocations':0,'nativeQueries':0,'nativeAttempts':0,'appProducts':0,'needsFreshIndependentReview':True})

if __name__=='__main__':
 output=pathlib.Path(sys.argv[1]).resolve()
 try:run(output)
 except Exception as error:
  write(output/'failure.json',{'error':str(error),'type':type(error).__name__,'traceback':traceback.format_exc(),'checks':checks})
  raise
 finally:write(output/'checks.json',checks)
 print(json.dumps({'passed':True,'checksPassed':len(checks),'focusedControls':len(correction.CONTROLS),'nativeAccepted':False},sort_keys=True))
