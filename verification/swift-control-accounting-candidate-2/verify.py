#!/usr/bin/env python3
"""Offline source, metadata, positive-field, boundary and scope verifier."""
from pathlib import Path
import gzip,hashlib,json,sys,tarfile,io
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=HERE/json.loads((HERE/'qualifying.json').read_text())['resultDirectory']
enc=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode();digest=lambda x:hashlib.sha256(enc(x)).hexdigest()
def raw(p):return p.read_bytes() if p.exists() else gzip.decompress(Path(str(p)+'.gz').read_bytes())
def js(p):return json.loads(raw(p))
def checksha(p,expected):assert hashlib.sha256(raw(p)).hexdigest()==expected,str(p)
seal=js(HERE/'seal.json')
for name,h in seal['files'].items():checksha(HERE/name,h)
for name,h in seal['externalBindings'].items():checksha(ROOT/name,h)
r=js(OUT/'receipt.json');assert r['status'].startswith('passed-actual-source-metadata-preflight')
assert r['liveVMUnchanged'] and not any(r[k] for k in ['controlMethodsExecuted','sc01Through12Passed','accountingAccepted','implementationAccepted','nativeRuntime','physicalRuntime','gaAcceptance'])
assert r['baselineTreeSHA256']=='4f16367b0985d924564b80b00b556f799cb42e3426a9b08fd8aca53b2a0015a4'
assert r['candidateTreeSHA256']=='e1b88be22eb683c40bfe53cd32f5b48d391b475b6097bab233aaf00b5303453d'
assert len(r['commands'])==41 and len(r['mirInventory'])==8
for rec in [r,js(OUT/'privacy-receipt.json'),js(OUT/'nested-layout-receipt.json')]:
 for cmd in rec['commands']:
  for stream in ['stdout','stderr']:checksha(OUT/cmd[stream],cmd[stream+'SHA256'])
for label in ['baseline','candidate','baseline-metadata','candidate-metadata']:
 manifest=js(OUT/(label+'-manifest.json'));assert len(manifest)==(119 if label=='baseline' else 120 if label=='candidate' else 120 if label=='baseline-metadata' else 121)
 with tarfile.open(OUT/(label+'-source.tar.gz')) as tar:
  actual={str(Path(member.name).relative_to('vm')):hashlib.sha256(tar.extractfile(member).read()).hexdigest() for member in tar.getmembers() if member.isfile()}
 assert actual==manifest,label
assert digest(js(OUT/'candidate-manifest.json'))==r['candidateTreeSHA256']
base=js(OUT/'baseline-manifest.json');candidate=js(OUT/'candidate-manifest.json');changed=js(HERE/'changed-files.json')
assert sorted(name for name in candidate if base.get(name)!=candidate[name])==sorted(changed)
for name in changed:checksha(HERE/'overlay'/name,candidate[name])
assert len(changed)==6 and len(base)==119 and len(candidate)==120
identity=js(OUT/'frozen-identity.json');assert set(identity)=={'pop32','close_control','branch','run'} and all(v['identical'] for v in identity.values())
b=js(OUT/'baseline-frozen-bodies.json');c=js(OUT/'candidate-frozen-bodies.json');assert b==c
for name,body in c.items():assert hashlib.sha256(body.encode()).hexdigest()==identity[name]['sha256']
rows=js(OUT/'bound-inventory-schema.json');assert len(rows)==7640 and len({r['field'] for r in rows})==7640 and all(r.get('sourceSpans') for r in rows)
assert sum(r['config']=='production' for r in rows)==3760 and sum(r['config']=='unit' for r in rows)==3760 and sum(r['config']=='source' for r in rows)==120
for config in ['production','unit']:
 actual=next(x for x in r['mirInventory'] if x['config']=='swift' and x['profile']=='debug' and x['unit']==(config=='unit'))
 for row in rows:
  if row['config']==config:assert row['qualifyingMIRSHA256']==actual['sha256'] and row['sourceTreeSHA256']==r['candidateTreeSHA256']
for item in r['mirInventory']:
 checksha(OUT/item['path'],item['sha256']);assert item['functions']==38 and item['rows']==(3752 if item['profile']=='debug' else 5604)
layouts=js(OUT/'layouts.json');assert len(layouts)==16
nested=js(OUT/'nested-layout-receipt.json');assert nested['status'].startswith('passed') and len(nested['layouts'])==8 and not nested['controlMethodsExecuted']
for layout in layouts:
 assert layout['types']['Controlled']['bytes']==1096
 if layout['config']=='all':assert layout['totals']['frozen_header']==2912
 if layout['label']!='candidate':continue
 selected=[x for x in rows if layout['unit'] or x['config']!='unit'];assert set(layout['fields'])=={x['field'] for x in selected}
 # Add the separately typed private inventory as one real nested component in
 # ActivePositions; its own fields remain in their separate private class.
 n=next(x for x in nested['layouts'] if (x['config'],x['profile'],x['unit'])==(layout['config'],layout['profile'],layout['unit']))
 assert n['activeBytes']==layout['classes']['ActivePositions']['bytes']
 occupied={}
 for row in selected:
  f=layout['fields'][row['field']];cls=row['ownerClass'];assert f['offset']%f['alignment']==0 and f['offset']+f['bytes']<=layout['classes'][cls]['bytes']
  if f['bytes']:occupied.setdefault(cls,[]).append((f['offset'],f['offset']+f['bytes'],row['field']))
 occupied.setdefault('ActivePositions',[]).append((n['offset'],n['offset']+n['bytes'],'private_scalar_transfers'))
 for cls,intervals in occupied.items():
  last=0
  for start,end,name in sorted(intervals):assert start>=last,(cls,name);last=end
 assert layout['totals']['new_permanent']==layout['classes']['PermanentPositions']['bytes'] and layout['totals']['new_active']==layout['classes']['ActivePositions']['bytes']
 assert layout['totals']['frame_bound']==layout['totals']['frame_active']+119576+layout['totals']['new_active']
comparisons=js(OUT/'corrected-boundary-comparisons.json');assert len(comparisons)==8
for row in comparisons:
 unit=row['unit'];assert row['newPermanent']==(105312 if unit else 105280) and row['newActive']==(2325032 if unit else 1162520)
 assert row['exactHeader']==(2392040 if unit else 1514504) and row['exactFrameBound']==(3949904 if unit else 2211968)
 measured=next(x for x in layouts if x['label']=='candidate' and (x['config'],x['profile'],x['unit'])==(row['config'],row['profile'],unit))['totals']
 assert row['newPermanent']==measured['new_permanent'] and row['newActive']==measured['new_active']
 assert row['exactHeader']==measured['header'] and row['exactFrameBound']==measured['frame_bound']
 assert row['headerDelta']==row['existingPermanentDelta']+row['newPermanent']
 assert row['phaseBoundaryAt']==row['exactFrameBound'] and row['phaseBoundaryBelow']+1==row['phaseBoundaryAt'] and row['phasePreviousBound']==0
 assert row['headerBoundaryBelow']+1==row['exactHeader'] and row['ceilingUnchanged']
 assert row['headerPlusFrameBound']==row['exactHeader']+row['exactFrameBound']
fields=js(OUT/'all-enlarged-containing-positions.json');flat=sum(fields.values(),[]);assert len(flat)==44 and sum(not x['unitOnly'] for x in flat)==28
assert js(OUT/'privacy-receipt.json')['status']=='passed-actual-sibling-callability-and-original-privacy'
assert [x['exitCode'] for x in js(OUT/'privacy-receipt.json')['commands']]==[0,101,0,1]
for name in ['cleanup.json','privacy-cleanup.json','nested-layout-cleanup.json']:
 cleanup=js(OUT/name);assert cleanup.get('removed') and (cleanup.get('buildRemoved',cleanup.get('removed') is True)) and not cleanup['nativeInstancesStarted']
# Audit live source against the accepted closure; no mutation is performed.
actual={}
for name in base:actual[name]=hashlib.sha256((ROOT/'vm'/name).read_bytes()).hexdigest()
assert actual==base,'live accepted VM drift'
# Original authority packets are bound and remain historical; no finding is overwritten.
inputs=js(OUT/'inputs.json')
for name,h in inputs['files'].items():checksha(ROOT/name,h)
assert inputs['candidate2TreeSHA256']==r['candidateTreeSHA256']
assert not inputs['producerAndReviewerEvidenceModified']
patch=js(OUT/'patch-reproduction.json');assert patch['all120FilesExact'] and patch['candidateTreeSHA256']==r['candidateTreeSHA256'];checksha(HERE/'source.patch',patch['sourcePatchSHA256'])
assert js(OUT/'patch-cleanup.json')['removed']
review=js(OUT/'source-review.json');assert review['newWrapperCanonicalRows']==136 and review['originalValuePrimitiveUnchanged'] and not review['behaviorExecuted'] and not review['faultInjectionExecuted'] and review['rootReviewRequired']
control=(HERE/'overlay/src/experimental_swift_reactor/control_operations.rs').read_text()
wrapper=control.split('    fn control_pop_value(',1)[1].split('    /// No borrowed frame/pin',1)[0]
assert wrapper.count('self.phase.pop_value()')==1 and wrapper.count('self.cleanup.live_unreconciled = true;')==1
assert 'result.is_err() && self.phase.parts.values.len() != previous_length' in wrapper
assert not any(token in wrapper for token in ['remove_live','work(','.invariant(','.fail(','?'])
assert '$s.control_pop_value()' in control and '$s.phase.pop_value()' not in control
for config in ['production','unit']:
 part=[x for x in rows if x['config']==config and x.get('mirFunction','').endswith('::control_pop_value')]
 assert len(part)==68 and all(x['envelope']=='active' for x in part)
 # Independently enumerate actual canonical MIR declarations and direct aliases.
 import re
 text=raw(OUT/('swift-debug-'+config+'.mir')).decode()
 m=re.search(r'^fn (control_operations::[^\n]*::control_pop_value)\((.*?)\) -> (.+?) \{\n(.*?)^\}',text,re.M|re.S);assert m
 name,params,ret,body=m.groups();bindings=set(re.findall(r'let (?:mut )?(_\d+): ',body))|set(re.findall(r'(_\d+): ',params))
 for binding in bindings:assert {x['position'] for x in part if x['binding']==binding}=={'source','argument','returned','caller'}
 for alias,binding in re.findall(r'debug (\w+) => (_\d+);',body):assert {x['position'] for x in part if x['binding']==alias}=={'source','argument','returned','caller'}
# Exhaustive independently partitioned canonical authored ownership census.
for config in ['production','unit']:
 text=raw(OUT/('swift-debug-'+config+'.mir')).decode();functions=[]
 for m in re.finditer(r'^fn (.+?)\((.*?)\) -> (.+?) \{\n(.*?)^\}',text,re.M|re.S):
  name,params,ret,body=m.groups()
  if not (name.startswith('control_operations::') or (name.startswith('experimental::execution::') and name.rsplit('::',1)[-1] in {'result','height','start','end','is_loop','is_function','is_if','clear_result','decoded'})):continue
  selected=[x for x in rows if x['config']==config and x.get('mirFunction')==name];assert selected,name
  bindings=set(re.findall(r'let (?:mut )?(_\d+): ',body))|set(re.findall(r'(_\d+): ',params))
  for binding in bindings:assert {x['position'] for x in selected if x['binding']==binding}=={'source','argument','returned','caller'},(config,name,binding)
  for alias,binding in re.findall(r'debug (\w+) => (_\d+);',body):assert {x['position'] for x in selected if x['binding']==alias}=={'source','argument','returned','caller'},(config,name,alias)
  functions.append(name)
 assert len(functions)==38,(config,len(functions))
assert js(OUT/'inventory-delta.json')['netAdditionalFields']==120
summary=js(HERE/'receipt.json');assert summary['candidateTreeSHA256']==r['candidateTreeSHA256'] and summary['wrapperPositiveFields']==136 and summary['obsoleteDirectReborrowFields']==16
assert not any(summary[k] for k in ['controlMethodsExecuted','faultBehaviorExecuted','controlExecutionAuthorized','accountingAccepted','implementationAccepted','gaAcceptance'])
for name,item in js(HERE/'compression-index.json').items():
 checksha(HERE/item['gzipPath'],item['storedSHA256']);checksha(HERE/name,item['uncompressedSHA256'])
for rec in [js(OUT/'postprocess-receipt.json')]:
 for cmd in rec['commands']:
  for stream in ['stdout','stderr']:checksha(OUT/cmd[stream],cmd[stream+'SHA256'])
print('passed: candidate2 exact Frozen identity; 7640 positive source-bound roles including 136 wrapper roles; 16 full plus 8 nested layouts; original privacy; exact patch reproduction; no control execution or acceptance')
