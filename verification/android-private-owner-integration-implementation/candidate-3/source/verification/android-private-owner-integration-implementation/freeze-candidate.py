#!/usr/bin/env python3
"""One-shot immutable proposal snapshot; never changes compiled admission policy or a lock."""
from pathlib import Path
import datetime,hashlib,json,shutil,subprocess
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT/'verification/android-private-owner-integration-implementation';OUT=BASE/'candidate-3'
def ident(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,value):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
assert not OUT.exists();OUT.mkdir();sources={}
finals=['scope-repair-A-final-1','scope-repair-B-final-1','scope-repair-crosscompile-final-1','observer-final-1','core-regression/attempts/exact-final-1']
for label in finals:
 run=BASE/label;receipt=json.loads((run/'receipt.json').read_text());assert receipt['status'] in ('passed-host-only','passed-crosscompile-only','pass')
 if 'source_stable' in receipt:assert receipt['source_stable']
 for source in (run/'inputs').rglob('*'):
  if source.is_file():
   relative=source.relative_to(run/'inputs').as_posix();data=source.read_bytes()
   # Observer/core snapshots may use their own historical input layout; only canonical source paths enter the union.
   if not relative.startswith(('native/','sdk/','verification/')):continue
   assert (ROOT/relative).read_bytes()==data,relative
   assert relative not in sources or sources[relative]==data,relative;sources[relative]=data
 # Retain exact receipts/streams/class bytes, without redundant copied inputs.
 evidence=OUT/'evidence'/label;evidence.mkdir(parents=True)
 for source in run.iterdir():
  if source.name=='inputs':continue
  if source.is_file():shutil.copy2(source,evidence/source.name)
  elif source.name in ('classes','dex'):shutil.copytree(source,evidence/source.name)
# The unchanged engine/SDK source identities from the full successful Swift/JNI build must match.
swift=BASE/'crosscompile-final-1';swiftmap=json.loads((swift/'source-map.json').read_text());swiftinputs={k:v for k,v in swiftmap.items() if k.startswith(('sdk/','native/android/engine/','native/android/bridge/'))}
for relative,identity in swiftinputs.items():assert ident((ROOT/relative).read_bytes())==identity,relative
for source in swift.iterdir():
 if source.name in ('inputs','classes','dex'):continue
 target=OUT/'evidence/swift-jni-final-1'/source.name
 if source.is_file():target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
 elif source.name=='native-products':shutil.copytree(source,target)
extra=['AGENTS.md','native/android/tests/OwnerLifecycleV2HostTests.java','docs/android-private-owner-integration-implementation.md','native/android/tests/NativeCoordinatorV2HostTests.java','native/android/tests/run-owner-core-host.py','native/android/tests/run-environment-observer-host.py','verification/android-private-owner-effect-roster-amendment/required-host-roster.json','verification/android-private-owner-integration-implementation/map-barriers.py','verification/android-private-owner-integration-implementation/map-legacy-vectors.py','verification/android-private-owner-integration-implementation/freeze-candidate.py','verification/android-private-owner-integration-implementation/profile-proposal.json','verification/android-private-owner-integration-implementation/legacy-vector-map.json','verification/android-private-owner-integration-implementation/source-and-boundary-proof.json']
extra+=['docs/'+name for name in ('android-private-owner-effect-integration-proposal.md','android-private-owner-effect-integration-correction.md','android-private-owner-effect-roster-amendment.md','android-private-owner-dirty-transaction-disposition.md')]
extra+=['verification/android-private-owner-integration-implementation/'+name for name in ('prepare-final-proof.py','freeze-history.json','candidate-2-correction-disposition.json')]
for label in ('ledger-repair-control','focus-repair-control-final'):
 run=BASE/label;receipt=json.loads((run/'receipt.json').read_text());assert receipt['status'] in ('expected-old-candidate2-rejection-and-repaired-pass','passed-controlled-before-failure-and-after-success-host-only')
 shutil.copytree(run,OUT/'evidence'/label)
 for source in run.iterdir():
  if source.suffix in ('.java','.py'):extra.append(source.relative_to(ROOT).as_posix())
for relative in extra:sources[relative]=(ROOT/relative).read_bytes()
profile=json.loads((BASE/'profile-proposal.json').read_text())
for relative in profile['adapter_files']:
 path='native/android/'+('engine/'+relative if relative.startswith('Sources/') else relative);sources[path]=(ROOT/path).read_bytes()
for relative in profile['sdk_files']:path='sdk/'+relative;sources[path]=(ROOT/path).read_bytes()
assert not (ROOT/'native/android/owner-core/src/dev/mixer/android/OwnerLifecycleV2.java').exists()
assert ident(sources['native/android/app/src/dev/mixer/android/OwnerLifecycleV2.java'])=={'bytes':12473,'sha256':'4282e8284212fb042a139f597d9f34f061f6f27673e918a52f1f784e6fe9ebb6'}
leaf=json.loads((BASE/'leaf-candidate-3/manifest.json').read_text());assert all(ident(sources[k])==v for k,v in leaf['files'].items())
for relative,data in sorted(sources.items()):target=OUT/'source'/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
save(OUT/'source-map.json',{k:ident(v) for k,v in sorted(sources.items())})
save(OUT/'profile-proposal.json',profile)
save(OUT/'receipt.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'revision_context':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'status':'frozen-producer-candidate-awaiting-independent-review-and-root-literal-selection','scope':'private native/test source candidate, explicit mechanical host controls and unsigned cross-compilation only','source_members':len(sources),'core_move_exact':True,'leaf3_exact74':True,'adapter_members':len(profile['adapter_files']),'SDK_members':len(profile['sdk_files']),'adapter_projection_sha256':profile['adapter_compatibility_sha256'],'sdk_projection_sha256':profile['sdk_compatibility_sha256'],'profile_id':profile['id'],'compiled_profile_literals_changed':False,'CLI_consumer_qualification_run':False,'final_evidence':finals,'Swift_JNI_unchanged_input_members':len(swiftinputs),'native_runtime_or_capture_or_process_discovery':False,'pending':['Independent actual product source/behavior review','Root exact profile3 literal selection','Separately coordinated CLI/common/driver/preaccess/copied export consumer qualification','Android/native framework/JNI/IME/draw/lifecycle runtime tests paused','Physical phone matrix and release/GA gates','Literal VM allocation exhaustion was not induced; controlled actual-core-boundary fatal and post-coordinator-return completion faults have narrower scope']})
# Closed membership of this one-shot packet, excluding only its own manifest.
files={p.relative_to(OUT).as_posix():ident(p.read_bytes()) for p in sorted(OUT.rglob('*')) if p.is_file()}
save(OUT/'manifest.json',{'schema':1,'files':files,'members':len(files),'bytes':sum(v['bytes'] for v in files.values())})
print(json.dumps({'candidate':str(OUT.relative_to(ROOT)),'manifest':ident((OUT/'manifest.json').read_bytes()),'members':len(files),'bytes':sum(v['bytes'] for v in files.values()),'source_members':len(sources),'profile':ident((OUT/'profile-proposal.json').read_bytes()),'adapter_projection':profile['adapter_compatibility_sha256'],'sdk_projection':profile['sdk_compatibility_sha256']},indent=2))
