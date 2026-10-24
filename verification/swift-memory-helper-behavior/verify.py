#!/usr/bin/env python3
"""Offline frozen candidate checker; no build, native process or source mutation."""
from pathlib import Path
import hashlib,json,gzip,tarfile,argparse,sys,re
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
enc=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
digest=lambda x:hashlib.sha256(enc(x)).hexdigest()
parser=argparse.ArgumentParser();parser.add_argument('--live-baseline',action='store_true');args=parser.parse_args()
receipt=json.loads((HERE/'receipt.json').read_text());seal=json.loads((HERE/'seal.json').read_text());assert sha(HERE/'receipt.json')==seal['receiptSHA256']
for path,expected in receipt['bindings'].items():assert sha(HERE/path)==expected,path
assert len(receipt['bindings'])==receipt['boundEvidenceFiles'];assert receipt['independentReviewAccepted']is False and receipt['rootAcceptance']is False
assert sha(ROOT/'docs/swift-memory-helper-behavior.md')==receipt['documentationSHA256']
def archive_manifest(path):
 with tarfile.open(path)as t:
  members=t.getmembers();assert all(m.isfile()and m.name.startswith('vm/')and'..'not in Path(m.name).parts for m in members)
  result={m.name.removeprefix('vm/'):hashlib.sha256(t.extractfile(m).read()).hexdigest()for m in members};assert len(result)==len(members);return result
for label,definition in receipt['sourceArchives'].items():
 actual=archive_manifest(HERE/(label+'-source.tar.gz'));expected=json.loads((HERE/(label+'-source-manifest.json')).read_text());assert actual==expected;assert len(actual)==definition['files'];assert digest(actual)==definition['closure']
source=receipt['candidateSourceClosure'];assert source=='6046a5fa8ba3800ec168b7ae6a80cb82bad5ba39b8701cb23a5db720d998bb62'
allowed={v['closure']for v in receipt['sourceArchives'].values()}
for name in receipt['qualifyingCommands']:
 directory=HERE/'commands'/name;command=json.loads((directory/'receipt.json').read_text());assert command['exitCode']==0 and command['sourceUnchanged'];assert command['sourceTreeSHA256']is None or command['sourceTreeSHA256']in allowed,(name,command['sourceTreeSHA256'])
 for stream in ['stdout','stderr']:assert hashlib.sha256(gzip.decompress((directory/(stream+'.gz')).read_bytes())).hexdigest()==command[stream+'SHA256']
 if command['sourceTreeSHA256']is not None:assert digest(json.loads((directory/'source-manifest.json').read_text()))==command['sourceTreeSHA256']
matrix=json.loads((HERE/'matrix-results.json').read_text());spec=json.loads((HERE/'acceptance-matrix.json').read_text());expected={(x['id'],config)for x in spec['cases']for config in spec['configurations']};assert {(x['id'],x['configuration'])for x in matrix}==expected and len(matrix)==64
for x in matrix:
 assert x['status']=='passed'and x['sourceClosure']==source and x['boundedRealOwnerCount']<=64 and x['observedCountedHelperAttempts']<=4096
 output=gzip.decompress((HERE/'commands'/x['command']/'stdout.gz').read_bytes()).decode();assert '1 passed; 0 failed; 0 ignored'in output
 if x['id']=='mm14_frozen_parity':assert ('feature absent' in output)==x['configuration'].startswith('swift-')
 if x['id']=='mm06_cancel_prefix':assert 'MM06_CALLER_CANCEL afterInstruction=true instructionDelta=1 fuelDelta=1 workDelta=0 pcDelta=0 valueDelta=0 memoryChanged=false pinsChanged=false outerPublication=Ok stored=Cancelled terminal=true draining=true'in output
regressions=json.loads((HERE/'regression-results.json').read_text());assert len(regressions)==8
for x in regressions:
 c=json.loads((HERE/'commands'/x['command']/'receipt.json').read_text());assert c['sourceTreeSHA256']==source and c['exitCode']==0
# Reproduce final positive roles from compiler MIR; includes promoted backing,
# qualified width, aliases/literals/capture payload and four separate positions.
sys.path.insert(0,str(HERE));import inventory
audits={x['config']:x for x in json.loads((HERE/'canonical-audit.json').read_text())}
schema=json.loads((HERE/'inventory-schema.json').read_text());assert len(schema)==4792 and len({r['field']for r in schema})==4792
keys=['envelope','window','field','rustType','binding','sourceNames','position','config','kind','mirType']
for config in ['production','unit']:
 assert audits[config]['sourceClosure']==source
 assert hashlib.sha256(gzip.decompress((HERE/('canonical-'+config+'.mir.gz')).read_bytes())).hexdigest()==audits[config]['mirSHA256']
 rows,defs,captures=inventory.canonical(HERE/('canonical-'+config+'.mir.gz'),config);old=[r for r in schema if r['config']==config];assert [{k:r[k]for k in keys}for r in rows]==[{k:r[k]for k in keys}for r in old];assert len(defs)==21
assert sum(x['config']=='production'for x in schema)==2104;assert sum(x['config']=='unit'for x in schema)==2156
layouts=json.loads((HERE/'layouts.json').read_text());assert len(layouts)==16
for layout in [x for x in layouts if x['label']=='candidate']:
 old=next(x for x in layouts if x['label']=='baseline'and all(x[k]==layout[k]for k in ['unit','features','profile']));assert old['types']==layout['types']and old['owners']==layout['owners'];totals=layout['totals'];assert totals['memory_permanent']==121856;assert totals['memory_active']==(1142696 if layout['unit']else 624544)
 assert totals['header']==old['totals']['header']+totals['memory_permanent'];assert totals['frame']==old['totals']['frame']+totals['memory_active'];assert totals['frame']==totals['frame_active']+totals['value']+totals['control_active']+totals['memory_active'];assert totals['state_limit']==134217728 and totals['combined_limit']==268435456
 rows=[r for r in schema if layout['unit']or r['config']!='unit'];assert set(layout['fields'])=={r['field']for r in rows};ends={}
 for r in sorted(rows,key=lambda r:(r['ownerClass'],layout['fields'][r['field']]['offset'])):
  field=layout['fields'][r['field']];cls=r['ownerClass'];assert field['offset']>=ends.get(cls,0)and field['offset']%field['alignment']==0;ends[cls]=field['offset']+field['bytes'];assert ends[cls]<=layout['classes'][cls]['bytes']
 if layout['features']=='all':assert totals['frozen_header']==2912
frozen=json.loads((HERE/'frozen-identity.json').read_text());assert frozen['count']==39 and len(frozen['containingOwners'])==14 and frozen['reservationBytes']==2912
import build_overlay
expanded=[]
for label in ['baseline','candidate']:
 full=gzip.decompress((HERE/'commands'/('final2-expanded-'+label)/'stdout.gz').read_bytes()).decode();span=full[full.index('impl SpanInstance {'):];at=span.index('{')+1;depth=1
 while depth:depth+=(span[at]=='{')-(span[at]=='}');at+=1
 span=span[:at];names=re.findall(r'^\s+(?:pub )?fn (\w+)\(',span,re.M);expanded.append({n:hashlib.sha256(build_overlay.method(span,n).encode()).hexdigest()for n in names})
assert expanded[0]==expanded[1]==frozen['methods']and len(expanded[0])==39
assert frozen['unchangedAcceptedSourceFiles']==115
parity=json.loads((HERE/'frozen-runtime-parity.json').read_text());assert len(parity)==2
for x in parity:
 profile=x['profile'];observations=[]
 for label in ['baseline','candidate']:
  output=gzip.decompress((HERE/'commands'/('final2-frozen-snapshot-'+label+'-'+profile)/'stdout.gz').read_bytes()).decode();lines=[line[line.index('FROZEN_SNAPSHOT '):]for line in output.splitlines()if'FROZEN_SNAPSHOT 'in line];assert len(lines)==28;observations.append(lines)
 assert observations[0]==observations[1]and digest(observations[0])==x['sha256']
for attempt in json.loads((HERE/'historical-failed-source-reconstruction.json').read_text()):
 assert attempt['exactSourceReconstructed'];actual=archive_manifest(HERE/'historical-failed-sources'/(attempt['command']+'-source.tar.gz'));assert actual==json.loads((HERE/'commands'/attempt['command']/'source-manifest.json').read_text());assert digest(actual)==attempt['expectedSourceClosure']
assert receipt['cleanup']['ownedScratchRemoved']and receipt['cleanup']['lsofObservedNoOpenFiles']and not receipt['liveVMEdited']and not receipt['gaAcceptance']
if args.live_baseline:
 vm=ROOT/'vm';paths=[vm/'Cargo.toml',vm/'Cargo.lock']
 for d in ['src','tests','include']:paths+=sorted(p for p in (vm/d).rglob('*')if p.is_file())
 assert digest({str(p.relative_to(vm)):sha(p)for p in paths})==receipt['baselineSourceClosure']
print(json.dumps(dict(verified=True,bindings=receipt['boundEvidenceFiles'],candidateSourceClosure=source,memoryTestsExecuted=64,positiveFields=4792,frozenObservationPairs=56,independentReviewAccepted=False,liveBaselineChecked=args.live_baseline)))
