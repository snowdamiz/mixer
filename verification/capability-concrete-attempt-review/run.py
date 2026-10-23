#!/usr/bin/env python3
"""Read-only independent concrete retirement probes; reuse frozen owner products."""
import hashlib,json,os,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
BASE=ROOT/'capability-activation/.build/concrete-2026-10-23-candidate-4'
DEPS=ROOT/'capability-activation/.build/transitions-qualified-2026-10-23-candidate-2'
sha=lambda b:hashlib.sha256(b).hexdigest()
def need(ok,why):
 if not ok:raise RuntimeError(why)
def main():
 out=HERE/'2026-10-23-final-2';out.mkdir(exist_ok=False)
 work=ROOT/'capability-activation/.build/concrete-independent-final-review-2';work.mkdir(exist_ok=False)
 pins={'capability-activation/Sources/MixerCapabilityActivation/CapabilityConcreteAttempt.swift':'039e789a763cd99b2e6eb0295984ab44ac3d11d25def26b1ba48f294132cdbbc','capability-activation/Sources/MixerCapabilityActivation/CapabilityConcreteRetirement.swift':'e143c347eae335e2b6dd53abd56d0da24dc9729efa72e5a185b79abc2510b8cc'}
 for p,d in pins.items():need(sha((BASE/'source'/p).read_bytes())==d and sha((ROOT/p).read_bytes())==d,p)
 owner=json.loads((ROOT/'verification/capability-concrete-attempt/2026-10-23-candidate-4/receipt.json').read_bytes())
 need(owner['source_manifest_sha256']=='1841b66af21862254655cd11255d4208ee48f463bb84ef7bd2789a14b9615fa1','frozen source manifest')
 for p,d in owner['source_files'].items():need(sha((BASE/'source'/p).read_bytes())==d,'export '+p)
 commands=[];artifacts={};env=dict(os.environ,DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer')
 framework='/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/Library/Frameworks'
 overlay='/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/usr/lib'
 def run(name,cmd,environment=env):
  began=time.monotonic();q=subprocess.run(cmd,cwd=ROOT,env=environment,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=60)
  p=out/(name+'.log');p.write_bytes(q.stdout);commands.append({'name':name,'argv':cmd,'cwd':str(ROOT),'exit_code':q.returncode,'seconds':time.monotonic()-began,'log':str(p.relative_to(ROOT)),'sha256':sha(q.stdout),'environment':{k:environment[k] for k in ['DEVELOPER_DIR','DYLD_LIBRARY_PATH','DYLD_FRAMEWORK_PATH'] if k in environment}})
  need(q.returncode==0,name+' '+str(q.returncode));return q.stdout
 run('swift-version',['swiftc','--version'])
 for mode in ['debug','release','tsan']:
  products=BASE/mode/'products';deps=DEPS/('retained-'+('debug' if mode=='tsan' else mode))
  dylib=products/'libMixerCapabilityActivationConcrete.dylib';pin=sha(dylib.read_bytes());module=products/'MixerCapabilityActivation.swiftmodule'
  modules={str(p):sha(p.read_bytes()) for p in products.glob('MixerCapabilityActivation.*') if p.is_file()}
  cmd=['swiftc','-parse-as-library','-swift-version','6','-warnings-as-errors','-I',str(products),'-I',str(deps/'products'),'-I',overlay,'-F',framework]
  for m in ['CMixerVMCapability','MixerCapabilityDurableIO','MixerCapabilityIO','MixerDurableIO']:cmd+=['-Xcc','-fmodule-map-file='+str(deps/'modulemaps'/(m+'.modulemap'))]
  cmd+=['-Xcc','-I'+str(DEPS/'native/include')]
  if mode=='release':cmd+=['-O']
  if mode=='tsan':cmd+=['-sanitize=thread']
  for probe in ['RetirementProbe','DeinitProbe']:
   exe=work/(probe+'-'+mode)
   command=cmd+[str(HERE/(probe+'.swift')),'-L',str(products),'-lMixerCapabilityActivationConcrete','-Xlinker','-rpath','-Xlinker',str(products),'-Xlinker','-rpath','-Xlinker',framework,'-o',str(exe)]
   run('compile-'+probe+'-'+mode,command)
   e=dict(env,DYLD_LIBRARY_PATH=str(products)+':'+overlay,DYLD_FRAMEWORK_PATH=framework)
   args=[str(exe)]
   if probe=='DeinitProbe':args+=[str(BASE/'source/capability-activation/Tests/MixerCapabilityActivationTests/Fixtures')]
   raw=run('run-'+probe+'-'+mode,args,e);need(b'PASS ' in raw,'probe output')
   artifacts[probe+'-'+mode]={'executable':str(exe),'executable_sha256':sha(exe.read_bytes())}
  need(sha(dylib.read_bytes())==pin,'library changed');need(all(sha(Path(p).read_bytes())==d for p,d in modules.items()),'module changed')
  artifacts[mode]={'library':str(dylib),'library_sha256':pin,'module_files':modules,'executable':str(exe),'executable_sha256':sha(exe.read_bytes())}
 r={'scope':'Independent original metadata retirement scheduling probes against exact unmodified frozen concrete module; no new SwiftPM/Rust builds or device work. TSan framework/Rust instrumentation limits remain.','production_inputs':pins,'owner_manifest_sha256':owner['source_manifest_sha256'],'commands':commands,'artifacts':artifacts,'probes':{p:sha((HERE/p).read_bytes()) for p in ['RetirementProbe.swift','DeinitProbe.swift']},'driver_sha256':sha(Path(__file__).read_bytes()),'cases_per_mode':'6 join permutations +128 concurrent joins +2 cancellation orders +128 cancel/finish races +8 actual signed/native construct/startup/drop cycles','status':'passed'}
 (out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(sha((out/'receipt.json').read_bytes()))
if __name__=='__main__':main()
