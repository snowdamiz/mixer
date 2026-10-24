#!/usr/bin/env python3
"""Offline evidence checker: validates request-changes, never invokes an engine."""
from pathlib import Path
import argparse,collections,gzip,hashlib,json,re,sys,tarfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRODUCER=HERE.parent/'swift-memory-helper-behavior'
enc=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
digest=lambda x:hashlib.sha256(enc(x)).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--live-baseline',action='store_true');args=p.parse_args()
r=json.loads((HERE/'receipt.json').read_text());seal=json.loads((HERE/'seal.json').read_text());assert sha(HERE/'receipt.json')==seal['receiptSHA256']
assert r['verdict']=='request-changes' and r['blockingFindings']==['MR01'] and not r['independentReviewAccepted'] and not r['rootAcceptance']
for path,expected in r['bindings'].items():assert sha(HERE/path)==expected,path
assert len(r['bindings'])==r['boundEvidenceFiles'];assert sha(ROOT/'docs/swift-memory-helper-behavior-review.md')==r['documentationSHA256']
for path,expected in r['inputs'].items():assert sha(ROOT/path)==expected,path
producer=json.loads((PRODUCER/'receipt.json').read_text());assert len(producer['bindings'])==1451
for path,expected in producer['bindings'].items():assert sha(PRODUCER/path)==expected,path
assert producer['candidateSourceClosure']==r['candidateSourceClosure']=='6046a5fa8ba3800ec168b7ae6a80cb82bad5ba39b8701cb23a5db720d998bb62'
assert producer['baselineSourceClosure']==r['baselineSourceClosure']=='241f7a6037100d29a4d277e1ec176fec55c0380b4283c17120bb8ace045318d5'
def archive(path):
 with tarfile.open(path) as t:
  members=t.getmembers();assert all(m.isfile() and m.name.startswith('vm/') and '..' not in Path(m.name).parts for m in members)
  out={m.name.removeprefix('vm/'):hashlib.sha256(t.extractfile(m).read()).hexdigest() for m in members};assert len(out)==len(members);return out
for label in ['baseline','candidate','metadata-baseline','metadata-candidate','parity-baseline','parity-candidate']:
 assert archive(PRODUCER/(label+'-source.tar.gz'))==json.loads((PRODUCER/(label+'-source-manifest.json')).read_text())
for label in ['adversarial','historical-adversarial-v1']:
 assert archive(HERE/(label+'-source.tar.gz'))==json.loads((HERE/(label+'-source-manifest.json')).read_text())
commands=[]
for directory in sorted((HERE/'commands').iterdir()):
 c=json.loads((directory/'receipt.json').read_text());assert c['sourceUnchanged'];assert c['exitCode']==(101 if directory.name=='adversarial-swift-debug' else 1 if directory.name=='cleanup-lsof' else 0)
 for stream in ['stdout','stderr']:assert hashlib.sha256(gzip.decompress((directory/(stream+'.gz')).read_bytes())).hexdigest()==c[stream+'SHA256']
 if c['sourceClosure'] is not None:assert digest(json.loads((directory/'source-manifest.json').read_text()))==c['sourceClosure']
 commands.append(directory.name)
assert len(commands)==r['recordedCommands']==116
matrix=json.loads((HERE/'matrix-results.json').read_text());spec=json.loads((PRODUCER/'acceptance-matrix.json').read_text());assert len(matrix)==64 and {(x['case'],x['feature'],x['profile']) for x in matrix}=={(c['id'],f,p) for c in spec['cases'] for f in ['swift','all'] for p in ['debug','release']}
for x in matrix:
 output=gzip.decompress((HERE/'commands'/('matrix-'+x['feature']+'-'+x['profile']+'-'+x['case'])/'stdout.gz').read_bytes()).decode();assert '1 passed; 0 failed; 0 ignored' in output and x['exitCode']==0 and x['fixtures']<=64 and x['steps']<=4096
 if x['case']=='mm14_frozen_parity':assert ('feature absent' in output)==(x['feature']=='swift')
 if x['case']=='mm13_no_alloc_warm':assert x['fixtures']==58
 if x['case']=='mm06_cancel_prefix':assert 'MM06_CALLER_CANCEL afterInstruction=true instructionDelta=1 fuelDelta=1 workDelta=0 pcDelta=0 valueDelta=0 memoryChanged=false pinsChanged=false outerPublication=Ok stored=Cancelled terminal=true draining=true' in output
for feature in ['swift','all']:
 for profile in ['debug','release']:
  for label,n in [('frame-control',34),('value',12)]:assert f'{n} passed; 0 failed; 0 ignored' in gzip.decompress((HERE/'commands'/('regression-'+feature+'-'+profile+'-'+label)/'stdout.gz').read_bytes()).decode()
  output=gzip.decompress((HERE/'commands'/('adversarial-v2-'+feature+'-'+profile)/'stdout.gz').read_bytes()).decode();assert '6 passed; 0 failed; 0 ignored' in output
  bounds=re.findall(r'MM_BOUND fixtures=(\d+) totalSteps=(\d+)',output);assert len(bounds)==6 and max(int(x[0]) for x in bounds)==46
layouts=json.loads((HERE/'layouts.json').read_text());assert len(layouts)==16
for x in [x for x in layouts if x['label']=='candidate']:
 old=next(y for y in layouts if y['label']=='baseline' and all(x[k]==y[k] for k in ['feature','release','unit']))
 assert x['actual']['types']==old['actual']['types'] and x['actual']['owners']==old['actual']['owners']
 assert len(x['actual']['fields'])==(4792 if x['unit'] else 2636)
structural=json.loads((HERE/'structural-results.json').read_text());assert len(structural['frozenMethods'])==39 and len(structural['ownerDeclarations'])==14 and structural['frozenReservationBytes']==2912
for x in json.loads((HERE/'frozen-parity-results.json').read_text()):
 observed=[]
 for label in ['baseline','candidate']:
  output=gzip.decompress((HERE/'commands'/('frozen-snapshot-'+label+'-'+x['profile'])/'stdout.gz').read_bytes()).decode();observed.append([line[line.index('FROZEN_SNAPSHOT '):] for line in output.splitlines() if 'FROZEN_SNAPSHOT ' in line])
 assert len(observed[0])==28 and observed[0]==observed[1]==x['observations'] and digest(observed[0])==x['sha256']
# Replay the independent full MIR audit from frozen text. Expected findings are
# positive evidence of a known accounting gap; no filtered candidate parser is used.
sys.path.insert(0,str(HERE));import mir_audit
mir=json.loads((HERE/'mir-results.json').read_text());assert len(mir)==4
for x in mir:
 text=gzip.decompress((HERE/('mir-'+x['feature']+'-'+x['config']+'.mir.gz')).read_bytes()).decode();assert hashlib.sha256(text.encode()).hexdigest()==x['mirSHA256'];actual=mir_audit.inspect(text,x['config'])
 assert all(actual[k]==x[k] for k in actual)
 assert actual['fields']==(2164 if x['config']=='unit' else 2104)
 assert actual['exactInventory']==(x['config']=='production')
 if x['config']=='unit':assert len(actual['missingPositiveRoles'])==2 and {a['binding'] for a in actual['missingPositiveRoles']}=={'_0','_1'}
assert 'required_extra_unit_bytes=64' in gzip.decompress((HERE/'commands/promotion-type-layout/stdout.gz').read_bytes()).decode()
cleanup=json.loads((HERE/'cleanup.json').read_text());assert cleanup['ownedScratchRemoved'] and cleanup['lsofObservedNoOpenFiles'] and not cleanup['otherProjectDataTouched'] and not cleanup['simulatorOrEmulatorStarted']
if args.live_baseline:
 vm=ROOT/'vm';paths=[vm/'Cargo.toml',vm/'Cargo.lock']
 for d in ['src','tests','include']:paths+=sorted(p for p in (vm/d).rglob('*') if p.is_file())
 assert digest({str(p.relative_to(vm)):sha(p) for p in paths})==r['baselineSourceClosure']
print(json.dumps(dict(verified=True,verdict='request-changes',blockingFindings=['MR01'],producerBindings=1451,reviewBindings=r['boundEvidenceFiles'],exactMemorySelections=64,independentAdversarialSelections=24,freshMIRConfigurations=4,missingUnitFields=8,missingNamedUnitBytes=64,inventoryComplete=False,rootAcceptance=False,liveBaselineChecked=args.live_baseline)))
