#!/usr/bin/env python3
"""Read-only sealed producer audit; executes no guest and grants no acceptance."""
from pathlib import Path
import json,hashlib,gzip,tarfile,re,collections
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();enc=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
seal=json.loads((HERE/'seal.json').read_text())
for name,digest in seal['files'].items():assert sha(HERE/name)==digest,('packet binding',name)
assert sha(ROOT/'docs/swift-control-behavior-implementation.md')==seal['documentSHA256']
r=json.loads((HERE/'receipt.json').read_text());assert not r['implementationAccepted'] and not r['gaAcceptance'] and not r['nativeRuntime'] and not r['physicalRuntime']
base=json.loads((HERE/'baseline-manifest.json').read_text());accepted=json.loads((HERE/'starting-candidate-manifest.json').read_text());source=json.loads((HERE/'source-manifest.json').read_text())
assert len(base)==119 and len(accepted)==120 and len(source)==121
for manifest,key in [(base,'baselineVMClosure'),(accepted,'acceptedCandidate2Closure'),(source,'implementationVMClosure')]:assert hashlib.sha256(enc(manifest)).hexdigest()==r[key]
for label,expected in [('baseline',base),('implementation',source)]:
 with tarfile.open(HERE/(label+'-source.tar.gz')) as archive:
  actual={}
  for member in archive.getmembers():
   assert member.isfile() and member.name.startswith('vm/') and '..' not in Path(member.name).parts
   actual[member.name[3:]]=hashlib.sha256(archive.extractfile(member).read()).hexdigest()
  assert actual==expected,label
for path,digest in source.items():
 p=HERE/'overlay'/path
 if p.exists():assert sha(p)==digest
 else:assert base[path]==digest
assert len(list((HERE/'overlay').rglob('*.rs')))==9
cases=json.loads((HERE/'cases.json').read_text());assert [x['id'] for x in cases['groups']]==[f'SC{i:02d}' for i in range(1,13)]
tests=(HERE/'overlay/src/experimental_swift_reactor/control_operations_tests.rs').read_text();assert set(re.findall(r'#\[test\]\s*fn (sc\d\d_\w+)',tests))=={x['test'] for x in cases['groups']}
qualified=r['qualifyingCommands'];assert len(qualified)==17
for q in qualified:
 receipt_path=HERE/q['receipt'];command=json.loads(receipt_path.read_text());assert command['exitCode']==0 and command['sourceTreeSHA256']==r['implementationVMClosure'];assert sha(receipt_path.parent/command['stdout'])==q['stdoutSHA256'];assert sha(receipt_path.parent/command['stderr'])==q['stderrSHA256']
assert len([q for q in qualified if q.get('passedTests')==46 and q.get('scGroups')==12])==4
assert len([q for q in qualified if q.get('passedTests')==6])==4
for binary in json.loads((HERE/'executable-manifest.json').read_text()):
 data=gzip.decompress((HERE/binary['path']).read_bytes());assert len(data)==binary['uncompressedBytes'] and hashlib.sha256(data).hexdigest()==binary['uncompressedSHA256'];assert binary['sourceTreeSHA256']==r['implementationVMClosure']
layout=json.loads((HERE/r['metadataDirectory']/'layouts.json').read_text());assert len(layout)==8
for x in layout:
 expected=r['unit' if x['unit'] else 'production'];assert (x['totals']['header'],x['totals']['frame_bound'],x['totals']['new_permanent'],x['totals']['new_active'])==(expected['header'],expected['frame'],expected['controlPermanent'],expected['controlActive']);assert x['types']['FrameOperationStorage']['bytes']==6232
 for cls in ['ControlHookPermanentPositions','ControlHookActivePositions'] if x['unit'] else []:
  names=[row['field'] for row in json.loads((HERE/'unit-hook-inventory.json').read_text()) if (row['envelope']=='permanent')==(cls=='ControlHookPermanentPositions')];last=0
  for name in sorted(names,key=lambda name:(x['fields'][name]['offset'],x['fields'][name]['bytes'])):
   f=x['fields'][name];assert f['offset']%f['alignment']==0 and f['offset']>=last;last=f['offset']+f['bytes'];assert last<=x['classes'][cls]['bytes']
rows=json.loads((HERE/'unit-hook-inventory.json').read_text());assert len(rows)==r['positiveHookFields']==400;typed=(HERE/'overlay/src/experimental_swift_reactor/frame_operations_tests.rs').read_text();flat=re.sub(r'\s+','',typed)
for row in rows:assert re.sub(r'\s+','',row['field']+':'+row['rustType']+',') in flat
assert json.loads((HERE/'unit-hook-final-audit.json').read_text())['positiveFields']==400
canonical=json.loads((HERE/'canonical-accounting-audit.json').read_text());assert canonical['status']=='exact-accepted-candidate-2-canonical-roles-preserved';assert len(canonical['results'])==2 and all(x['functions']==38 for x in canonical['results'])
check=HERE/r['sourceChecksDirectory'];identity=json.loads((check/'frozen-identity.json').read_text());assert set(identity)=={'pop32','close_control','branch','run'} and all(x['identical'] and x['reservationBytes']==2912 for x in identity.values())
clippy=json.loads((check/'clippy-comparison.json').read_text());norm=lambda rows:collections.Counter(json.dumps({k:v for k,v in row.items() if k!='line'},sort_keys=True) for row in rows);assert len(clippy['baseline'])==len(clippy['candidate'])==26 and norm(clippy['baseline'])==norm(clippy['candidate'])
cleanup=json.loads((HERE/'cleanup.json').read_text());assert cleanup['removed'] and cleanup['nativeInstancesStarted']==0 and cleanup['physicalRuns']==0 and cleanup['liveVMUnchanged']
assert json.loads((HERE/'patch-reproduction.json').read_text())['exact']
print('passed: frozen private Swift SC01-SC12 behavior packet; 4 x46 frame/value/control and 4 x6 Frozen tests, 8 layouts, exact 400-field hook supplement/canonical roles, Frozen identity, same 26 Clippy limits; no integration or acceptance')
