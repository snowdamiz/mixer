#!/usr/bin/env python3
"""Read-only sealed-source/evidence audit. No compiler, guest, live VM or network."""
from pathlib import Path
import difflib,hashlib,json,re,subprocess,tarfile
H=Path(__file__).resolve().parent;R=H.parent.parent;P=H.parent/'swift-plan-cache-remaining-work-diagnosis'
load=lambda p:json.loads(Path(p).read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
seal=load(H/'seal.json')
files={str(p.relative_to(H)) for p in H.rglob('*') if p.is_file() and p.name!='seal.json'}
assert files==set(seal['files'])
for n,d in seal['files'].items():assert sha(H/n)==d,n
for n,d in seal['externalFiles'].items():assert sha(R/n)==d,n
binding=load(H/'input-bindings.json');assert sha(P/'seal.json')==binding['acceptedParentSealSHA256']=='3a52d3f20cf852da7521fc3345a177ef6f8a7f157ebf2da7e3e63d01bc725b3d'
parent=load(P/'seal.json');assert len(parent['files'])==46
for n,d in parent['files'].items():assert sha(P/n)==d,n
for n,d in binding['contextArchives'].items():assert sha(H/'context'/n)==d,n
base=load(H/'baseline-manifest.json');modified=load(H/'copied-source-manifest.json')
assert sha(H/'baseline-manifest.json')==binding['sourceClosure']=='16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd'
assert len(base)==len(modified)==132 and set(base)==set(modified)
changed=[n for n in base if base[n]!=modified[n]]
assert changed==['src/experimental/cache/borrowed.rs','src/experimental_swift_reactor/cache.rs','src/experimental_swift_reactor/cache_tests.rs']
with tarfile.open(H/'isolated-source.tar.gz','r:gz') as t:
 assert len(t.getmembers())==132 and sorted(t.getnames())==sorted(modified)
 assert all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in t.getmembers())
 source={n:t.extractfile(n).read() for n in modified}
assert {n:hashlib.sha256(v).hexdigest() for n,v in source.items()}==modified
original={n:(P/'originals'/n).read_bytes() for n in changed}
for n in changed:assert hashlib.sha256(original[n]).hexdigest()==base[n]
patch=''.join(''.join(difflib.unified_diff(original[n].decode().splitlines(True),source[n].decode().splitlines(True),fromfile='accepted/'+n,tofile='isolated/'+n)) for n in changed)
assert patch==(H/'instrumentation.patch').read_text()
assert source[changed[2]]==original[changed[2]]+b'\n'+(H/'observer-and-controls.rs').read_bytes()
with tarfile.open(P/'isolated-source.tar.gz','r:gz') as t:
 expected={n:t.extractfile(n).read().decode() for n in changed[:2]}
def replace(n,old,new):
 assert expected[n].count(old)==1;expected[n]=expected[n].replace(old,new)
replace(changed[0],'fn diagnostic_completed(&mut self) {}','fn diagnostic_completed(&mut self, _: u32) {}')
replace(changed[0],'meter.diagnostic_completed();','meter.diagnostic_completed(function);')
replace(changed[1],'super::cache_tests::remaining_plan_work(n, result.is_ok());','super::cache_tests::remaining_plan_work(n, self.cursor, result.as_ref().err());')
replace(changed[1],'fn diagnostic_completed(&mut self) { super::cache_tests::remaining_plan_completed(); }','fn diagnostic_completed(&mut self, function: u32) { super::cache_tests::remaining_plan_completed(function); }')
replace(changed[1],'        SwiftMeter { operation, usage }','        #[cfg(test)] super::cache_tests::remaining_plan_begin(function);\n        SwiftMeter { operation, usage }')
for n in changed[:2]:assert source[n].decode()==expected[n]
# Check the exact earlier finite revisions without retaining redundant source archives.
def reverse_patch(after,patch):
 lines=after.splitlines(True);out=[];cursor=0;active=False
 for line in patch.splitlines(True):
  if line.startswith('--- ') or line.startswith('+++ '):continue
  if line.startswith('@@ '):
   m=re.match(r'@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@',line);assert m,line
   start=int(m[1])-1;assert start>=cursor;out.extend(lines[cursor:start]);cursor=start;active=True;continue
  assert active
  if line.startswith(' '):assert lines[cursor]==line[1:];out.append(line[1:]);cursor+=1
  elif line.startswith('+'):assert lines[cursor]==line[1:];cursor+=1
  elif line.startswith('-'):out.append(line[1:])
  else:assert line.startswith('\\ No newline')
 out.extend(lines[cursor:]);return ''.join(out)
hook=(H/'observer-and-controls.rs').read_text();attempts=[]
for index in [3,2,1]:
 A=H/f'attempt-{index}';hook=reverse_patch(hook,(A/'correction.patch').read_text())
 before=load(A/'copied-source-manifest.json')
 assert set(before)==set(modified)
 for n in modified:
  if n==changed[2]:assert before[n]==hashlib.sha256(original[n]+b'\n'+hook.encode()).hexdigest()
  else:assert before[n]==modified[n]
 c=load(A/'command.json');assert c['sourceManifestSHA256']==sha(A/'copied-source-manifest.json')
 assert c['exitCode']==101 and not c['timedOut'] and not c['signalsSent']
 assert c['stdoutSHA256']==sha(A/'finite.stdout') and c['stderrSHA256']==sha(A/'finite.stderr')
 attempts.append(c)
command=load(H/'command.json');assert command['sourceManifestSHA256']==sha(H/'copied-source-manifest.json')
assert command['exitCode']==0 and not command['timedOut'] and not command['signalsSent']
assert command['stdoutSHA256']==sha(H/'finite.stdout') and command['stderrSHA256']==sha(H/'finite.stderr')
assert command['argv'][1:]==['test','--lib','--locked','--offline','--no-default-features','--features','experimental-swift-reactor','--release','experimental_swift_reactor::cache_tests::current_attribution_','--','--nocapture','--test-threads=1']
for c in attempts+[command]:assert c['argv']==command['argv'] and c['environment']['CARGO_NET_OFFLINE']=='true'
stdout=(H/'finite.stdout').read_text();assert '4 passed; 0 failed; 0 ignored; 0 measured; 386 filtered out' in stdout
assert 'guest_instructions=0 initializes=0 invokes=0 cleanup_zero=true' in stdout
observed=load(H/'finite-observations.json');rows=[]
markers={'ATTR_CASE ':'observations','ATTR_BOUNDARY ':'boundary','ATTR_PREFIX ':'prefixes','ATTR_LAYOUT ':'layout','ATTR_MAX_SNAPSHOT ':'maxSnapshot'}
for line in stdout.splitlines():
 for marker,key in markers.items():
  if marker in line:
   value=json.loads(line.split(marker,1)[1])
   if key=='observations':rows.append(value)
   else:assert value==observed[key]
assert rows==observed['observations'] and len(rows)==13
old=load(P/'finite-observations.json')['observations']
for a,b in zip(rows,old):
 for k in ['case','work','credits','calls','plans','completed','hits','misses','decodes','evictions']:assert a[k]==b[k]
 assert sum(a['credits'])==a['work'] and a['completed']==a['distinct']+a['repeated']
 assert sum(a['scan_credits'])==a['credits'][6] and sum(a['scan_calls'])==a['calls'][6]
 assert sum(a['build_credits'])==a['credits'][13] and sum(a['build_calls'])==a['calls'][13]
 assert sum(a['scan_published'])==a['plans'][3]
by={a['case']:a for a in rows}
assert by['65_cycle_twice']['distinct']==by['65_cycle_twice']['repeated']==65
assert by['65_cycle_twice']['build_credits']==[329,329]
assert by['evicted_IR_plan_hit']['build_credits']==[0,5] and by['evicted_IR_plan_hit']['scan_credits']==[0,0]
assert by['plan_conflict_546']['scan_credits']==[4,0] and by['plan_conflict_34']['scan_credits']==[0,4]
assert observed['prefixes']['work_prefixes']==409 and observed['prefixes']['cancellation_prefixes']==173
assert all(v is True for k,v in observed['prefixes'].items() if k not in ('work_prefixes','cancellation_prefixes'))
assert observed['boundary']['upper_actual_cache_index']==79999 and observed['boundary']['index_80000_original_validator_rejected']
assert observed['boundary']['out_of_range_invalidates_only_observer'] and observed['boundary']['overflow_preserves_original_results']
layout=observed['layout'];assert layout['observer_bytes']==10504 and layout['observer_alignment']==8
assert layout['bitmap_bytes']==10000 and layout['formatter_bytes']==4112 and layout['output_capacity']==4096
assert layout['max_snapshot_bytes']==1602 and layout['max_snapshot_bytes']<layout['output_capacity']
max_line=[line.split('ATTR_MAX_SNAPSHOT ',1)[1] for line in stdout.splitlines() if 'ATTR_MAX_SNAPSHOT ' in line];assert len(max_line)==1 and len(max_line[0].encode())==1602
cleanup=load(H/'cleanup.json');pre=load(H/'cleanup-preflight.json')
assert cleanup['ownedPathsAbsent'] and cleanup['allOwnedProcessGroupsAbsent'] and cleanup['holderChecksEmpty'] and cleanup['deviceInodeChecksPassed']
assert not cleanup['signalsSent'] and not cleanup['liveVmQueried'] and not cleanup['nativeInstancesUsed'] and not cleanup['otherProjectsTouched']
assert not any(pre['ownedProcessGroups'].values())
assert all(v['exitCode']==1 and not v['stdout'] and not v['stderr'] for v in pre['holders'].values())
assert all(not (H/n).exists() for n in ['owned-source','owned-target','owned-tmp'])
ps=subprocess.check_output(['/bin/ps','-axo','pid=,pgid=,comm='],text=True,timeout=10)
owned={c['processGroup'] for c in attempts+[command]}
assert not [r for r in ps.splitlines() if len(r.split())>=2 and int(r.split()[1]) in owned]
receipt=load(H/'receipt.json');contract=load(H/'observer-contract.json')
assert receipt['finiteTestsPassed']==4 and receipt['fullTargetAttempts']==0 and receipt['guestInstructions']==0 and receipt['guestInitializeCalls']==0 and receipt['guestInvokeCalls']==0
assert not receipt['productionSourceChanged'] and not receipt['productionAlgorithmImplemented'] and not receipt['gaAccepted']
assert contract['bitmapBytes']==10000 and contract['bitmapAbsoluteIndices']==80000
print(json.dumps({'integrityVerified':True,'sealedMembers':len(files),'acceptedParentMembers':46,'sourceFiles':132,'copiedChangedFiles':3,'finiteTestsPassed':4,'finiteObservations':13,'workPrefixes':409,'cancellationPrefixes':173,'observerBytes':10504,'bitmapBytes':10000,'maxPayloadBytes':1602,'fullTargetAttempts':0,'cleanupComplete':True,'gaAccepted':False},sort_keys=True))
