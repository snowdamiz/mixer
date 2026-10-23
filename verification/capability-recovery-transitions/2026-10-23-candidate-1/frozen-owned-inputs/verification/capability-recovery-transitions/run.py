#!/usr/bin/env python3
"""Freeze private recovery transitions on reviewed dependencies; no coordinator/device work."""
import argparse,datetime,hashlib,json,os,re,shutil,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE='bf5021e2ce920dae78f0c778511040617f65082c'
OWNED=[
 'capability-activation/Sources/MixerCapabilityActivation/CapabilityRecoveryModels.swift',
 'capability-activation/Sources/MixerCapabilityActivation/CapabilityRecoveryStore.swift',
 'capability-activation/Sources/MixerCapabilityActivation/CapabilityRecoverySelection.swift',
 'capability-activation/Tests/MixerCapabilityActivationTests/CapabilityRecoveryTransitionTests.swift']
NATIVE=ROOT/'capability-activation/.build/store-qualified-2026-10-23-candidate-2/native'
OFFICIAL='/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift'
def sha(b):return hashlib.sha256(b).hexdigest()
def need(ok,msg):
 if not ok:raise RuntimeError(msg)
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--label',required=True);a=ap.parse_args()
 need(re.fullmatch('[a-z0-9-]+',a.label),'fresh simple label')
 out=HERE/a.label;out.mkdir(exist_ok=False)
 work=ROOT/'capability-activation/.build'/('transitions-qualified-'+a.label);work.mkdir(exist_ok=False)
 source=work/'source';source.mkdir()
 files={};baseline={}
 paths=subprocess.check_output(['git','ls-tree','-r','--name-only',BASE,'--','sdk','updates','runtime-identity','experimental-capability-runtime','capability-activation'],cwd=ROOT,text=True).splitlines()
 for p in paths:
  rest='/'.join(p.split('/')[1:])
  if rest.startswith(('Sources/','Tests/')) or rest in ['Package.swift','Package.resolved']:
   raw=subprocess.check_output(['git','show',BASE+':'+p],cwd=ROOT);baseline[p]=sha(raw)
   dest=source/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw);files[p]=sha(raw)
 overlays=OWNED+[str(Path(__file__).relative_to(ROOT))]
 overlays += [str(p.relative_to(ROOT)) for p in (HERE/'CompileNegative').glob('*.swift')]
 for p in overlays:
  raw=(ROOT/p).read_bytes();dest=source/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw);files[p]=sha(raw)
 public='verification/capability-installed-material/PublicClient/main.swift'
 raw=subprocess.check_output(['git','show',BASE+':'+public],cwd=ROOT);dest=source/public;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw);files[public]=sha(raw);baseline[public]=sha(raw)
 native=work/'native';native.mkdir();nativefiles={}
 for p in ['receipt.json','include/mixer_vm.h','include/mixer_vm_capability.h','lib/libmixer_vm_capability_experimental.a']:
  raw=(NATIVE/p).read_bytes();dest=native/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw);nativefiles[p]=sha(raw)
 n=json.loads((native/'receipt.json').read_bytes());need(n['source_revision']=='b25e3b7de2391a80d12e7fd75e60903495bec120' and n['feature']=='experimental-capability-native','frozen native source/feature')
 manifest=''.join(d+'  '+p+'\n' for p,d in sorted(files.items())).encode();(out/'source-manifest.sha256').write_bytes(manifest)
 r={'status':'running','started_at':utc(),'dependency_revision':BASE,'source_files':files,'source_manifest_sha256':sha(manifest),'owned_files':{p:files[p] for p in OWNED},'baseline_files':baseline,'export':str(source),'native_origin':str(NATIVE),'native_copy':str(native),'native_files':nativefiles,'commands':[],'driver_sha256':sha(Path(__file__).read_bytes()),'retained_products':{},'scope':'Internal private durable selection/attempt/effects-intent/health/failure transitions only. Original signed Wasm with real frozen native validate-only and startup/invocation tests. No public coordinator, concrete adapter ownership composition, device, published-package, FieldLog or GA authority.'}
 def save():(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
 def unchanged():
  for p,d in files.items():need(sha((source/p).read_bytes())==d,'export changed '+p)
  for p in OWNED:need(sha((ROOT/p).read_bytes())==files[p],'owned changed '+p)
  for p,d in nativefiles.items():need(sha((native/p).read_bytes())==d,'native changed '+p)
 env=dict(os.environ,DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer')
 def run(name,cmd,scope,expected=0,count=None,fragment=None,environment=env,timeout=300):
  unchanged();began=time.monotonic()
  try:q=subprocess.run(cmd,cwd=source,env=environment,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout);raw,code=q.stdout,q.returncode
  except subprocess.TimeoutExpired as e:raw,code=(e.stdout or b'')+b'\nQualification timeout\n',124
  log=out/(name+'.log');log.write_bytes(raw)
  row=dict(name=name,argv=cmd,cwd=str(source),environment={'DEVELOPER_DIR':environment['DEVELOPER_DIR']},exit_code=code,expected_exit=expected,seconds=time.monotonic()-began,log=str(log.relative_to(ROOT)),sha256=sha(raw),scope=scope)
  if count is not None:
   counts=[int(v) for v in re.findall(rb"Test Suite 'All tests' passed[^\n]*\n\s*Executed (\d+) tests",raw)]
   if not counts:counts=[int(v) for v in re.findall(rb"Test Suite 'Selected tests' passed[^\n]*\n\s*Executed (\d+) tests",raw)]
   row.update(expected_tests=count,observed_tests=counts)
  if fragment:row['required_fragment']=fragment
  r['commands'].append(row);save();unchanged();print(name,code,flush=True)
  need(code==expected,name+' result '+str(code))
  if count is not None:need(counts==[count],name+' count')
  if fragment:need(fragment.encode() in raw,name+' rejection')
  return raw
 def retain(mode):
  products=work/'host/out/Products'/mode.capitalize();dest=work/('retained-'+mode);dest.mkdir()
  shutil.copytree(products,dest/'products');maps=work/'host/out/Intermediates.noindex/GeneratedModuleMaps';shutil.copytree(maps,dest/'modulemaps')
  outputs={str(p.relative_to(dest)):sha(p.read_bytes()) for p in sorted(dest.rglob('*')) if p.is_file() and not p.is_symlink()}
  r['retained_products'][mode]={'directory':str(dest),'files':outputs};save();return dest
 save()
 try:
  run('swift-version',['swift','--version'],'Observed compiler');run('xcode-version',['xcodebuild','-version'],'Observed Xcode');run('host-version',['uname','-a'],'Observed host');run('disk',['df','-h','/System/Volumes/Data'],'Disk capacity observation')
  common=['-Xcc','-I'+str(native/'include'),'-Xlinker','-L'+str(native/'lib'),'-Xswiftc','-warnings-as-errors']
  test=['swift','test','--package-path',str(source/'capability-activation'),'--scratch-path',str(work/'host')]+common
  for mode in ['debug','release']:
   run('all-'+mode,test+['-c',mode],'54 unchanged baseline functions plus20new transition functions; original signed Wasm and actual frozen native validation/startup/invocation',count=74)
   retain(mode)
  retained=work/'retained-debug';products=retained/'products'
  c=['swiftc','-swift-version','6','-warnings-as-errors','-I',str(products),'-Xcc','-I'+str(native/'include')]
  for m in ['CMixerVMCapability','MixerCapabilityDurableIO','MixerCapabilityIO','MixerDurableIO']:c+=['-Xcc','-fmodule-map-file='+str(retained/'modulemaps'/(m+'.modulemap'))]
  publicexe=work/'public-material-consumer'
  run('public-client-link',c+['-L',str(products),'-lMixerCapabilityActivation','-L',str(native/'lib'),'-lmixer_vm_capability_experimental',str(source/public),'-o',str(publicexe)],'Unchanged external material-only public API client; one experimental Rust archive')
  run('public-client-run',[str(publicexe),str(source/'capability-activation/Tests/MixerCapabilityActivationTests/Fixtures')],'Public material constructor remains material-only')
  for name in ['selection','consumed','transitions']:
   run('reject-public-'+name,c+['-typecheck',str(source/'verification/capability-recovery-transitions/CompileNegative'/(name+'.swift'))],'Private selection/consumed/store cannot be named by a public module consumer',expected=1,fragment='cannot find')
  run('new-tsan',test+['--sanitize','thread','--filter','CapabilityRecoveryTransitionTests'],'20new transition functions under owned Swift/C-shim TSan; Rust and framework internals uninstrumented',count=20)
  apple=run('iphoneos-sdk',['xcrun','--sdk','iphoneos','--show-sdk-path'],'Official SDK path').decode().strip()
  run('ios-module',['swift','build','--package-path',str(source/'capability-activation'),'--scratch-path',str(work/'ios'),'--triple','arm64-apple-ios17.0','--sdk',apple,'-c','release','--target','MixerCapabilityActivation']+common,'Official iOS module/object compile, no app link or platform run')
  official=dict(os.environ,DEVELOPER_DIR='/Applications/Xcode_26.6.app/Contents/Developer')
  run('official-swift-version',[OFFICIAL,'--version'],'Official Android cross compiler',environment=official)
  run('android-module',[OFFICIAL,'build','--package-path',str(source/'capability-activation'),'--scratch-path',str(work/'android'),'--swift-sdks-path','/Users/andreyyurlov/.swiftpm/swift-sdks','--swift-sdk','aarch64-unknown-linux-android28','-c','release','--target','MixerCapabilityActivation']+common,'Official Android module/object compile, no app link or platform run',environment=official)
  artifacts={}
  for target in ['ios','android']:
   modules=[p for p in (work/target).rglob('*.swiftmodule') if p.is_file() and (p.name=='MixerCapabilityActivation.swiftmodule' or p.parent.name=='MixerCapabilityActivation.swiftmodule')]
   objects=[p for p in (work/target).rglob('*.o') if p.name in ['MixerCapabilityActivation.o','CapabilityRecoveryStore.o','CapabilityRecoveryStore.swift.o','CapabilityRecoverySelection.o','CapabilityRecoverySelection.swift.o']]
   need(modules and objects,target+' actual outputs')
   artifacts[target]=[dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in sorted(set(modules+objects))]
  artifacts['public-client']=[dict(path=str(publicexe),bytes=publicexe.stat().st_size,sha256=sha(publicexe.read_bytes()))]
  unchanged();r.update(status='scoped private transitions passed; independent review pending',completed_at=utc(),source_unchanged=True,artifacts=artifacts,
   limitations=['Private store transitions only; no public coordinator, concrete adapter lifecycle composition, public updater, real UI or FieldLog health qualification.', 'Counter/requested payload bounds are not totalRSS/OOM-recovery promises.', 'Intentional claimed-drop/abandoned-store tests permanently pin slots and descriptors until process exit; never reset for passing tests.', 'TSan covers owned Swift/C shims, not Rust/platform framework internals.', 'Cross SDK objects are not device execution/app linkage/signing evidence.'])
 except BaseException as e:r.update(status='failed qualification preserved',problem=str(e),completed_at=utc());save();raise
 save();print(json.dumps({'receipt_sha256':sha((out/'receipt.json').read_bytes()),'source_manifest_sha256':sha(manifest)}))
if __name__=='__main__':main()
