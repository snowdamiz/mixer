#!/usr/bin/env python3
"""Read-only frozen independent review checker; never builds or runs subprocesses."""
from pathlib import Path
import argparse, collections, gzip, hashlib, json, re, tarfile
from review import HERE, ROOT, read, sha, digest, manifest
from audit import P, source, inspect
from reuse_audit import audit as reused_audit
from finish import parse_layout

parser=argparse.ArgumentParser();parser.add_argument('--live-baseline',action='store_true');args=parser.parse_args()
receipt=read('receipt.json');seal=read('seal.json')
assert sha(HERE/'receipt.json')==seal['receiptSHA256']
assert receipt['verdict']==seal['verdict']=='accepted-scoped-correction'
assert receipt['independentReviewAccepted'] and not receipt['rootAcceptance'] and not receipt['gaAcceptance']
assert not any(receipt[k] for k in ['liveVMEdited','nativeRuntime','physicalRuntime','UI','simulatorOrEmulatorRuntime','committed','pushed','fullSwiftQualified','publicInvocationQualified'])
assert len(receipt['bindings'])==receipt['boundEvidenceFiles']
for name,h in receipt['bindings'].items():assert sha(HERE/name)==h,name
assert sha(ROOT/'docs/swift-memory-promoted-review.md')==receipt['documentationSHA256']
producer=read('inputs/producer/receipt.json')
assert sha(P/'receipt.json')==receipt['producerReceiptSHA256']=='e261cb8e2f30a013db7803baaf057c10d66bef02155c77b79b9ea37985d5ee16'
assert len(producer['bindings'])==563
for name,h in producer['bindings'].items():assert sha(P/name)==h,name
sources={};manifests={}
for label in ['baseline','behavior','candidate']:
 sources[label],manifests[label]=source(label)
 assert digest(manifests[label])==receipt['sourceArchives'][label]['closure'] and len(manifests[label])==receipt['sourceArchives'][label]['files']
candidate=receipt['candidateSourceClosure'];assert candidate==digest(manifests['candidate'])=='a01da340253ad086e69c060a041d8d15b3f9bb7a63f8c11465af704ce01ef65b'
assert receipt['baselineSourceClosure']=='241f7a6037100d29a4d277e1ec176fec55c0380b4283c17120bb8ace045318d5'
schema=read('inputs/producer/inventory-schema.json');old=read('inputs/producer/inputs/behavior-inventory-schema.json');byname={r['field']:r for r in schema}
assert len(schema)==len(byname)==4800 and len(old)==4792 and all(byname[r['field']]==r for r in old)
oldnames={r['field'] for r in old};added=[r for r in schema if r['field'] not in oldnames];assert len(added)==8
for binding in ['_0','_1']:assert collections.Counter(r['position'] for r in added if r['binding']==binding)==dict(source=1,argument=1,returned=1,caller=1)
assert all(r['config']=='unit' and r['mirFunction']=='memory_pinned_step::promoted[0]' for r in added)
path='src/experimental_swift_reactor/memory_operations.rs';assert [n for n in manifests['candidate'] if manifests['candidate'][n]!=manifests['behavior'][n]]==[path]
before=sources['behavior'][path].decode();after=sources['candidate'][path].decode();stripped=after
for r in added:
 d='    #[cfg(test)]\n    '+r['field']+': '+r['rustType']+',\n';assert stripped.count(d)==1;stripped=stripped.replace(d,'',1)
assert stripped==before and before.split('// ACCOUNTING_START')[0]==after.split('// ACCOUNTING_START')[0]
for label in ['probe-behavior','probe-candidate']:
 with tarfile.open(HERE/(label+'-source.tar.gz')) as t:
  members=t.getmembers();assert all(m.isfile() and m.name.startswith('vm/') and '..' not in Path(m.name).parts for m in members)
  m={x.name[3:]:hashlib.sha256(t.extractfile(x).read()).hexdigest() for x in members}
 assert m==read(label+'-source-manifest.json') and digest(m)==receipt['sourceArchives'][label]['closure']
assert read('source-review.json')['exactAddedRows']==added
mirrows=read('mir-review.json');assert len(mirrows)==5
for row in mirrows:
 p=HERE/'fresh-swift-unit.mir.gz' if row['fresh'] else P/('canonical-'+row['feature']+'-'+row['config']+'.mir.gz')
 raw=gzip.decompress(p.read_bytes());actual=inspect(raw.decode(),row['config'],schema)
 for key,value in actual.items():assert json.loads(json.dumps(value))==row[key],key
 assert sha(p)==row['mirSHA256'] and hashlib.sha256(raw).hexdigest()==row['uncompressedSHA256'] and row['sourceClosure']==candidate
assert reused_audit()==read('reused-evidence-review.json')
fresh=read('fresh-results.json');assert parse_layout('fresh-layout-behavior')==fresh['typedPairedUnitLayouts']['behavior'] and parse_layout('fresh-layout-candidate')==fresh['typedPairedUnitLayouts']['candidate']
assert fresh['additionalNamedUnitBytes']==fresh['activeDelta']==fresh['frameDelta']==64 and fresh['permanentDelta']==0
assert len(fresh['affectedBoundSelections'])==12
commands=read('command-index.json');assert len({c['name'] for c in commands})==len(commands)
assert {c['name'] for c in commands if c['exitCode']!=0}=={'reuse-audit-draft-v1','optional-live-checker-draft-v1','cleanup-lsof'}
for row in commands:
 directory=HERE/'commands'/row['name'];c=json.loads((directory/'receipt.json').read_text());assert c['sourceUnchanged'] and c['sourceClosure']==row['sourceClosure'] and c['exitCode']==row['exitCode']
 if c['sourceClosure'] is not None:
  m=json.loads((directory/'source-manifest.json').read_text());assert digest(m)==c['sourceClosure'] and c['sourceClosure'] in {d['closure'] for d in receipt['sourceArchives'].values()}
 for stream in ['stdout','stderr']:assert hashlib.sha256(gzip.decompress((directory/(stream+'.gz')).read_bytes())).hexdigest()==c[stream+'SHA256']
for row in fresh['affectedBoundSelections']:
 directory=HERE/'commands'/row['command'];c=json.loads((directory/'receipt.json').read_text());out=gzip.decompress((directory/'stdout.gz').read_bytes()).decode()
 assert c['sourceClosure']==candidate and c['exitCode']==0 and c['executables'] and '--exact' in c['argv'] and '1 passed; 0 failed; 0 ignored' in out
 if row['test']=='af22':assert 'frame=5092888' in out and 'frame_admitted=false' in out
assert read('commands/fresh-canonical-swift-unit/receipt.json')['sourceClosure']==candidate
for label in ['behavior','candidate']:assert read('commands/fresh-layout-'+label+'/receipt.json')['sourceClosure']==receipt['sourceArchives']['probe-'+label]['closure']
collector=gzip.decompress((HERE/'commands/collector-regression/stderr.gz').read_bytes()).decode();assert 'Ran 3 tests' in collector and 'OK' in collector
checker=json.loads(gzip.decompress((HERE/'commands/producer-checker/stdout.gz').read_bytes()).decode());assert checker['verified'] and checker['bindings']==563 and checker['liveBaselineChecked']
assert read('findings.json')['verdict']=='accepted-scoped-correction' and read('findings.json')['blockingFindings']==[]
notes=read('integration-notes.json')['trailingWhitespace'];assert [(n['path'],n['line'],n['inheritedFromBehavior']) for n in notes]==[('src/experimental/execution/mod.rs',1139,True),('src/experimental/execution/mod.rs',1140,True)]
cleanup=read('cleanup.json');assert cleanup['ownedScratchRemoved'] and cleanup['lsofObservedNoOpenFiles'] and not cleanup['otherProjectDataTouched'] and not cleanup['processesTerminated'] and cleanup['deviceInstancesCreated']==0
assert not Path(cleanup['scratch']).exists()
assert read('failed-attempts.json')['qualificationCompilerOrRuntimeFailures']==[]
if args.live_baseline:
 vm=ROOT/'vm';paths=[vm/'Cargo.toml',vm/'Cargo.lock']
 for directory in ['src','tests','include']:paths+=sorted(p for p in (vm/directory).rglob('*') if p.is_file())
 live={str(p.relative_to(vm)):sha(p) for p in paths};assert live==manifests['baseline'] and digest(live)==receipt['baselineSourceClosure']
print(json.dumps(dict(verified=True,verdict=receipt['verdict'],candidateSourceClosure=candidate,bindings=receipt['boundEvidenceFiles'],producerBindings=563,positiveFields=4800,oldRowsRetainedExactly=4792,newUnitFields=8,freshMeasuredUnitBytes=64,freshMIRConfigurations=1,frozenMIRConfigurations=4,freshTypedLayoutExecutions=2,freshFocusedSelections=12,reusedMemorySelections=64,reusedPriorSelections=184,reusedFrozenPairs=56,reusedFrozenIntegrationRuns=4,blockingFindings=[],integrationNotes=['IN01'],liveBaselineChecked=args.live_baseline,rootAcceptance=False,gaAcceptance=False),sort_keys=True))
