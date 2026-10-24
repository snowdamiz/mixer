#!/usr/bin/env python3
"""Standalone read-only checker: no build, subprocess, device or source writes."""
from pathlib import Path
import argparse,collections,difflib,gzip,hashlib,json,re,sys,tarfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
enc=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
digest=lambda x:hashlib.sha256(enc(x)).hexdigest()
read=lambda n:json.loads((HERE/n).read_text())
parser=argparse.ArgumentParser();parser.add_argument('--live-baseline',action='store_true');args=parser.parse_args()
receipt=read('receipt.json');seal=read('seal.json');assert sha(HERE/'receipt.json')==seal['receiptSHA256']
assert receipt['independentReviewAccepted'] is False and receipt['rootAcceptance'] is False and receipt['gaAcceptance'] is False
assert not receipt['liveVMEdited'] and not receipt['nativeRuntime'] and not receipt['physicalRuntime'] and not receipt['committed'] and not receipt['pushed']
for name,value in receipt['bindings'].items():assert sha(HERE/name)==value,name
assert len(receipt['bindings'])==receipt['boundEvidenceFiles']
assert sha(ROOT/'docs/swift-memory-promoted-correction.md')==receipt['documentationSHA256']

def archive(path):
 with tarfile.open(path) as t:
  members=t.getmembers();assert all(m.isfile() and m.name.startswith('vm/') and '..' not in Path(m.name).parts for m in members)
  source={m.name.removeprefix('vm/'):t.extractfile(m).read() for m in members};assert len(source)==len(members)
 return source

sources={};manifests={}
for label,definition in receipt['sourceArchives'].items():
 data=archive(HERE/(label+'-source.tar.gz'));m={n:hashlib.sha256(v).hexdigest() for n,v in data.items()}
 assert m==read(label+'-source-manifest.json') and digest(m)==definition['closure'] and len(m)==definition['files'] and sha(HERE/(label+'-source.tar.gz'))==definition['archiveSHA256']
 sources[label]=data;manifests[label]=m
source=receipt['candidateSourceClosure'];assert source==digest(manifests['candidate'])
assert receipt['behaviorSourceClosure']=='6046a5fa8ba3800ec168b7ae6a80cb82bad5ba39b8701cb23a5db720d998bb62'==digest(manifests['behavior'])
assert receipt['baselineSourceClosure']=='241f7a6037100d29a4d277e1ec176fec55c0380b4283c17120bb8ace045318d5'==digest(manifests['baseline'])
old_receipt=read('inputs/behavior-receipt.json');old_seal=read('inputs/behavior-seal.json');assert old_seal['receiptSHA256']==sha(HERE/'inputs/behavior-receipt.json')
for name in ['inventory-schema.json','function-manifest.json','layouts.json','frozen-identity.json','frozen-runtime-parity.json','canonical-production.mir.gz','canonical-unit.mir.gz']:
 assert sha(HERE/'inputs'/('behavior-'+name))==old_receipt['bindings'][name]
review=read('inputs/review-receipt.json');assert read('inputs/review-seal.json')['receiptSHA256']==sha(HERE/'inputs/review-receipt.json')
assert review['verdict']=='request-changes' and review['blockingFindings']==['MR01'] and review['missingUnitFields']==8 and review['missingNamedUnitBytes']==64
assert sha(HERE/'inputs/review.md')==review['documentationSHA256']

schema=read('inventory-schema.json');old_schema=read('inputs/behavior-inventory-schema.json');fields={r['field']:r for r in schema};old_fields={r['field']:r for r in old_schema}
assert len(fields)==len(schema)==4800 and len(old_fields)==4792 and all(fields[n]==r for n,r in old_fields.items())
added=[r for r in schema if r['field'] not in old_fields];assert len(added)==8
for binding in ['_0','_1']:
 rows=[r for r in added if r['binding']==binding];assert len(rows)==4 and {r['position'] for r in rows}=={'source','argument','returned','caller'}
assert all(r['config']=='unit' and r['mirFunction']=='memory_pinned_step::promoted[0]' for r in added)
assert collections.Counter(r['config'] for r in schema)=={'production':2104,'unit':2164,'source':532}
delta=read('source-delta.json');changed=[n for n in set(manifests['behavior'])|set(manifests['candidate']) if manifests['behavior'].get(n)!=manifests['candidate'].get(n)]
path='src/experimental_swift_reactor/memory_operations.rs';assert changed==delta['changedFiles']==[path]
before=sources['behavior'][path].decode();after=sources['candidate'][path].decode();assert before.split('// ACCOUNTING_START')[0]==after.split('// ACCOUNTING_START')[0]
stripped=after
for row in added:
 declaration='    #[cfg(test)]\n    '+row['field']+': '+row['rustType']+',\n';assert stripped.count(declaration)==1;stripped=stripped.replace(declaration,'',1)
assert stripped==before
assert (HERE/'correction.patch').read_text()==''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/vm/'+path,tofile='b/vm/'+path))

allowed={v['closure'] for v in receipt['sourceArchives'].values()};commands=read('command-index.json');assert len({c['name'] for c in commands})==len(commands)
assert {c['name'] for c in commands if c['exitCode']!=0}=={'collector-regression'}
for record in commands:
 directory=HERE/'commands'/record['name'];c=json.loads((directory/'receipt.json').read_text());assert c['sourceUnchanged'] and c['sourceTreeSHA256'] in allowed|{None}
 assert c['exitCode']==record['exitCode'] and c['sourceTreeSHA256']==record['sourceClosure']
 for stream in ['stdout','stderr']:assert hashlib.sha256(gzip.decompress((directory/(stream+'.gz')).read_bytes())).hexdigest()==c[stream+'SHA256']
 if c['sourceTreeSHA256'] is not None:assert digest(json.loads((directory/'source-manifest.json').read_text()))==c['sourceTreeSHA256']
for name in receipt['qualifyingCommands']:assert read('commands/'+name+'/receipt.json')['exitCode']==0
for binary in read('executable-manifest.json'):
 c=read('commands/'+binary['command']+'/receipt.json');assert dict(path=binary['path'],sha256=binary['sha256'],bytes=binary['bytes']) in c['executables'] and binary['sourceClosure']==c['sourceTreeSHA256']
matrix=read('matrix-results.json');spec=read('acceptance-matrix.json');assert len(matrix)==64
assert {(r['id'],r['configuration']) for r in matrix}=={(r['id'],config) for r in spec['cases'] for config in spec['configurations']}
for row in matrix:
 c=read('commands/'+row['command']+'/receipt.json');assert c['sourceTreeSHA256']==source and c['exitCode']==0 and row['sourceClosure']==source and row['status']=='passed'
 out=gzip.decompress((HERE/'commands'/row['command']/'stdout.gz').read_bytes()).decode();assert '1 passed; 0 failed; 0 ignored' in out
 assert row['boundedRealOwnerCount']<=64 and row['observedCountedHelperAttempts']<=4096
 assert re.search(r'MM_BOUND fixtures=\d+ totalSteps=\d+ maxStepsPerFixture=64 maxFrames=3 realPages=584',out)
 assert c['executables']
 if row['id']=='mm14_frozen_parity':assert ('feature absent' in out)==row['configuration'].startswith('swift-')
 if row['id']=='mm06_cancel_prefix':assert 'MM06_CALLER_CANCEL afterInstruction=true instructionDelta=1 fuelDelta=1 workDelta=0 pcDelta=0 valueDelta=0 memoryChanged=false pinsChanged=false outerPublication=Ok stored=Cancelled terminal=true draining=true' in out
regressions=read('regression-results.json');assert len(regressions)==8
for row in regressions:
 c=read('commands/'+row['command']+'/receipt.json');assert c['sourceTreeSHA256']==source and c['exitCode']==0
 out=gzip.decompress((HERE/'commands'/row['command']/'stdout.gz').read_bytes()).decode();assert str(34 if row['command'].endswith('frame-control') else 12)+' passed; 0 failed; 0 ignored' in out
assert read('commands/collector-regression-final/receipt.json')['exitCode']==0
collector_out=gzip.decompress((HERE/'commands/collector-regression-final/stderr.gz').read_bytes()).decode();assert 'Ran 3 tests' in collector_out and 'OK' in collector_out

sys.path.insert(0,str(HERE));import inventory,canonical_probe
audits=read('canonical-audit.json');assert len(audits)==4 and {(r['feature'],r['config']) for r in audits}=={(f,c) for f in ['swift','all'] for c in ['production','unit']}
for audit in audits:
 path=HERE/('canonical-'+audit['feature']+'-'+audit['config']+'.mir.gz');assert audit['sourceClosure']==source and sha(path)==audit['mirSHA256']
 assert hashlib.sha256(gzip.decompress(path.read_bytes())).hexdigest()==audit['uncompressedMirSHA256']
 actual=canonical_probe.validate(path,audit['config'],schema)
 for key in ['canonicalBodies','positiveCanonicalFields','definitions','captures','exactPositiveRoles']:assert json.loads(json.dumps(actual[key]))==audit[key],key
 if audit['config']=='unit':
  rows,_,_=inventory.canonical(path,'unit');promotion=[r for r in rows if r['mirFunction']=='memory_pinned_step::promoted[0]'];assert len(promotion)==8
  text=gzip.decompress(path.read_bytes()).decode();fixture_promotions=[line[6:].split(': &',1)[0] for line in text.splitlines() if line.startswith('const ') and '::promoted[' in line and '::tests::' in line];assert fixture_promotions and all(not inventory.selected(name) for name in fixture_promotions)

layouts=read('layouts.json');old_layouts=read('inputs/behavior-layouts.json');assert len(layouts)==16
assert {(r['label'],r['features'],r['profile'],r['unit']) for r in layouts}=={(l,f,p,u) for l in ['baseline','candidate'] for f in ['swift','all'] for p in ['debug','release'] for u in [False,True]}
import metadata
for layout in layouts:
 name='layout-binary-'+layout['label']+'-'+layout['features']+'-'+layout['profile']+('-unit' if layout['unit'] else '-production')
 c=read('commands/'+name+'/receipt.json');assert c['sourceTreeSHA256']==receipt['sourceArchives']['metadata-'+layout['label']]['closure'] and c['executables']
 out=gzip.decompress((HERE/'commands'/name/'stdout.gz').read_bytes()).decode();parsed=metadata.parse(out);assert all(parsed[k]==layout[k] for k in parsed)
for layout in [r for r in layouts if r['label']=='candidate']:
 baseline=next(r for r in layouts if r['label']=='baseline' and all(r[k]==layout[k] for k in ['features','profile','unit']))
 old=next(r for r in old_layouts if r['label']=='candidate' and all(r[k]==layout[k] for k in ['features','profile','unit']))
 assert layout['types']==baseline['types']==old['types'] and layout['owners']==baseline['owners']==old['owners']
 rows=[r for r in schema if layout['unit'] or r['config']!='unit'];assert set(layout['fields'])=={r['field'] for r in rows};ends={}
 for row in sorted(rows,key=lambda r:(r['ownerClass'],layout['fields'][r['field']]['offset'])):
  field=layout['fields'][row['field']];cls=row['ownerClass'];assert field['offset']>=ends.get(cls,0) and field['offset']%field['alignment']==0;ends[cls]=field['offset']+field['bytes'];assert ends[cls]<=layout['classes'][cls]['bytes']
 totals=layout['totals'];differences={n:totals[n]-old['totals'][n] for n in old['totals']};assert {n:v for n,v in differences.items() if v}==({'memory_active':64,'frame':64} if layout['unit'] else {})
 if layout['unit']:
  assert sum(layout['fields'][r['field']]['bytes'] for r in added)==64 and all(layout['fields'][r['field']]['bytes']==layout['fields'][r['field']]['alignment']==8 for r in added)
 assert totals['memory_permanent']==121856 and totals['memory_active']==(1142760 if layout['unit'] else 624544)
 assert totals['header']==baseline['totals']['header']+totals['memory_permanent'] and totals['frame']==baseline['totals']['frame']+totals['memory_active']
 assert totals['frame']==totals['frame_active']+totals['value']+totals['control_active']+totals['memory_active'] and totals['state_limit']==134217728 and totals['combined_limit']==268435456
 if layout['features']=='all':assert totals['frozen_header']==2912

identity=read('frozen-identity.json');assert identity['count']==39 and len(identity['containingOwners'])==14 and identity['reservationBytes']==2912
assert identity['methods']==read('inputs/behavior-frozen-identity.json')['methods'] and identity['containingOwners']==read('inputs/behavior-frozen-identity.json')['containingOwners']
import build_overlay
for label in ['baseline','candidate']:
 full=gzip.decompress((HERE/'commands'/('corrected-expanded-'+label)/'stdout.gz').read_bytes()).decode();span=full[full.index('impl SpanInstance {'):];at=span.index('{')+1;depth=1
 while depth:depth+=(span[at]=='{')-(span[at]=='}');at+=1
 span=span[:at];names=re.findall(r'^\s+(?:pub )?fn (\w+)\(',span,re.M);assert {n:hashlib.sha256(build_overlay.method(span,n).encode()).hexdigest() for n in names}==identity['methods']
reuse=read('frozen-runtime-reuse.json');assert reuse['reexecutedInCorrection'] is False and reuse['observationPairs']==56 and reuse['integrationRuns']==4 and reuse['correctionSourceClosure']==source
assert sha(HERE/'reused-frozen/behavior-receipt.json')==sha(HERE/'inputs/behavior-receipt.json')
reused_sources={}
for label in ['baseline','candidate']:
 data=archive(HERE/'reused-frozen'/('parity-'+label+'-source.tar.gz'));m={n:hashlib.sha256(v).hexdigest() for n,v in data.items()};assert m==read('reused-frozen/parity-'+label+'-source-manifest.json');reused_sources[digest(m)]=m
for name in reuse['reusedCommandNames']:
 directory=HERE/'reused-frozen/commands'/name;c=json.loads((directory/'receipt.json').read_text());assert c['exitCode']==0 and c['sourceUnchanged']
 assert sha(directory/'receipt.json')==old_receipt['bindings']['commands/'+name+'/receipt.json']
 assert digest(json.loads((directory/'source-manifest.json').read_text()))==c['sourceTreeSHA256'] and c['sourceTreeSHA256'] in set(reused_sources)|{receipt['baselineSourceClosure'],receipt['behaviorSourceClosure']}
 for stream in ['stdout','stderr']:
  assert sha(directory/(stream+'.gz'))==old_receipt['bindings']['commands/'+name+'/'+stream+'.gz'];assert hashlib.sha256(gzip.decompress((directory/(stream+'.gz')).read_bytes())).hexdigest()==c[stream+'SHA256']
 if 'integration' in name:assert '16 passed; 0 failed; 0 ignored' in gzip.decompress((directory/'stdout.gz').read_bytes()).decode()
for observation in read('reused-frozen/frozen-runtime-parity.json'):
 outputs=[]
 for label in ['baseline','candidate']:
  out=gzip.decompress((HERE/'reused-frozen/commands'/('final2-frozen-snapshot-'+label+'-'+observation['profile'])/'stdout.gz').read_bytes()).decode();lines=[line[line.index('FROZEN_SNAPSHOT '):] for line in out.splitlines() if 'FROZEN_SNAPSHOT ' in line];assert len(lines)==28;outputs.append(lines)
 assert outputs[0]==outputs[1] and digest(outputs[0])==observation['sha256']
assert receipt['cleanup']['ownedScratchRemoved'] and receipt['cleanup']['lsofObservedNoOpenFiles'] and not receipt['cleanup']['otherProjectDataTouched']
assert receipt['G08']=='pending-preserved-absent-cursor-Cleanup-diagnostic'
if args.live_baseline:
 vm=ROOT/'vm';assert digest(build_overlay.manifest(vm))==receipt['baselineSourceClosure']
print(json.dumps(dict(verified=True,bindings=receipt['boundEvidenceFiles'],candidateSourceClosure=source,positiveFields=4800,oldRowsRetainedExactly=4792,additionalUnitFields=8,measuredAdditionalUnitBytes=64,actualMIRConfigurations=4,pairedLayouts=16,memoryTestsExecuted=64,reusedFrozenObservationPairs=56,independentReviewAccepted=False,rootAcceptance=False,gaAcceptance=False,liveBaselineChecked=args.live_baseline),sort_keys=True))
