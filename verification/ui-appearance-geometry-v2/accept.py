from pathlib import Path
import datetime,hashlib,json,re,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];SNAP=HERE/'candidate-3/inputs'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=HERE/'candidate-3/receipt.json';r=json.loads(p.read_text());bindings={}
if r['status']!='passed-host-and-module-geometry':raise RuntimeError('qualification incomplete')
for path,h in r['inputBindings'].items():
 for item in [ROOT/path,SNAP/path]:
  if sha(item)!=h:raise RuntimeError('input mismatch '+str(item))
  bindings[str(item.relative_to(ROOT))]=h
for command in r['commands']:
 path=ROOT/command['log']
 if command['exit']!=0 or sha(path)!=command['sha256']:raise RuntimeError('command mismatch')
 bindings[str(path.relative_to(ROOT))]=sha(path)
for mode in ['debug','release']:
 log=(HERE/f'candidate-3/sdk-{mode}.log').read_text()
 if not re.search(r'Executed 8 tests, with 0 failures',log):raise RuntimeError('XCTest absent')
 for count in [74,10,2]:
  if not re.search(r'Test run with '+str(count)+r' tests .* passed',log):raise RuntimeError('SwiftTesting absent '+str(count))
if r['publicOutputCountsPerMode']!={'group':980,'fixed':2,'thumbOrigin':4,'pixel':72}:raise RuntimeError('comparison coverage')
for path in [p,HERE/'accept.py',ROOT/'docs/ui-appearance-geometry-v2.md']:
 bindings[str(path.relative_to(ROOT))]=sha(path)
out={'status':'accepted-pure-authored-geometry','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sourceRevision':r['sourceRevision'],'reviewer':'root','bindings':bindings,'testsPerHostMode':94,'publicComparisonCountsPerMode':r['publicOutputCountsPerMode'],'scope':r['scope'],'independentSourceReview':{'reviewer':'/root/measured_appearance_v2_sdk','scope':'Read-only source review against frozen contract and literal path definitions; all18track and18thumb commands, group expansion/reflections, clamp/rounding/UInt64 limits, raw density bounds, fractional pixel coordinates and RTL origin inspected. No issue found. Native shaping must impose any positive-measurement requirement separately; geometry admits zero extents.'},'retainedFailures':{'candidate-1':'New test literal member syntax error; fixed before candidate2.','candidate-2':'Full frozen SDK test closure omitted two V1 fixture files; geometry tests passed, complete suite failed. Candidate3 adds fixtures; product geometry unchanged.'},'limits':['No renderer adoption, native pixels, native preference conversion, signed authority or physical design-parity evidence.','Closed authored paths intentionally retain documented differences from platform-private reference rasters.','All GA and immutable published FieldLog gates remain pending.']}
(HERE/'acceptance.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print('ACCEPT',len(bindings),'bindings;94SDKtests/profile;1058publiccomparisons/profile')
