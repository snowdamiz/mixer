#!/usr/bin/env python3
"""Public API privacy and target-only compilation against frozen integration."""
import argparse, hashlib, json, os, re, subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--name',required=True);a=p.parse_args()
assert re.fullmatch('[a-z0-9-]+',a.name)
out=HERE/a.name;out.mkdir(exist_ok=False);work=HERE/'.build'/a.name;work.mkdir(exist_ok=False)
proof=HERE/'candidate-4/receipt.json';candidate=json.loads(proof.read_text());source=Path(candidate['source'])
assert candidate['status']=='Snapshot integration tests passed for debug, release, tsan'
base=ROOT/'capability-activation/.build/transitions-qualified-2026-10-23-candidate-3'
native=ROOT/'experimental-capability-runtime/build-verification/local/guest-ui-1adb25c-v2'
record={'status':'running','candidate_receipt':{'path':str(proof),'sha256':sha(proof)},'source_files':candidate['source_files'],'driver_sha256':sha(Path(__file__)),'inputs':{},'commands':[],'artifacts':{},'scope':'Ordinary-import public UI consumer host link/run and privacy negatives; rebuilt UI/Guest/Apple/bridge/full activation official iOS and Android module+object compilation using frozen unchanged foundational dependencies. No mobile app link, simulator/device execution or native display qualification.'}
def save():(out/'receipt.json').write_text(json.dumps(record,indent=2)+'\n')
def bind(path):
 path=Path(path)
 if path.is_file():record['inputs'][str(path)]=sha(path)
 elif path.is_dir():
  for child in path.rglob('*'):
   if child.is_file():record['inputs'][str(child)]=sha(child)
def run(name,command,expected=0,developer='/Applications/Xcode.app/Contents/Developer'):
 r=subprocess.run(command,cwd=ROOT,env=os.environ|{'DEVELOPER_DIR':developer},stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
 log=out/(name+'.log');log.write_bytes(r.stdout)
 record['commands'].append({'name':name,'command':command,'developer':developer,'exit_code':r.returncode,'expected_exit':expected,'log':str(log.relative_to(ROOT)),'log_sha256':sha(log)});save();print(name+': '+str(r.returncode),flush=True)
 assert r.returncode==expected,name
 return r.stdout
try:
 bind(proof);bind(HERE/'PublicConsumer.swift')
 for mode in ['debug','release']:
  current=Path(candidate['artifacts'][mode]['dylib']['path']).parent
  maps=current.parent/'modulemaps';borrowed=base/('retained-'+mode)/'products'
  bind(current);bind(maps)
  flags=['swiftc','-parse-as-library','-swift-version','6','-warnings-as-errors','-I',str(current),'-I',str(borrowed)]
  for mp in sorted(maps.glob('*.modulemap')):flags+=['-Xcc','-fmodule-map-file='+str(mp)]
  flags+=['-Xcc','-I'+str(native/'host/include')]
  if mode=='release':flags+=['-O']
  exe=work/(mode+'-public')
  run(mode+'-public-link',flags+[str(HERE/'PublicConsumer.swift'),'-L',str(current),'-lMixerCapabilityActivationGuestUI','-Xlinker','-rpath','-Xlinker',str(current),'-o',str(exe)])
  private=work/(mode+'-private');private.mkdir()
  run(mode+'-public-run',[str(exe),str(ROOT/'capability-activation/Tests/MixerCapabilityActivationTests/Fixtures'),str(private)])
  record['artifacts'][mode]={'path':str(exe),'sha256':sha(exe)}
  for name,statement,diagnostic in [
   ('host','_ = p.renderHost',b'inaccessible'),
   ('construct','_ = GuestUIPresentation()',b'inaccessible'),
   ('mutate','p.state = .stopped',b'inaccessible'),
   ('input','_ = p.claimNativeAttachment()',b'inaccessible'),
   ('milestone','try await r.reportMilestone("first_screen")',b'no member'),
   ('invoke','_ = try await r.invoke("run")',b'no member'),
   ('exchange','_ = try GuestUIExchangeV1(generation:1)',b'cannot find')]:
   f=out/(name+'.swift')
   f.write_text('import MixerCapabilityActivation\nimport MixerGuest\n@MainActor func probe(_ p: GuestUIPresentation, _ r: CapabilityGuestUIRuntime) async throws { '+statement+' }\n')
   raw=run(mode+'-private-'+name,flags+['-typecheck',str(f)],expected=1);assert diagnostic in raw,name
 cross=json.loads((ROOT/'verification/capability-cold-start-runtime/2026-10-23-supplemental-final/receipt.json').read_text())
 for platform in ['ios','android']:
  target=work/platform;target.mkdir()
  old=next(c['command'] for c in cross['commands'] if c['name']==platform+'-module-object')
  flags=old[:old.index('-module-name')]
  # Keep platform compiler options and immutable C/dependency paths; replace
  # only the native shim with the new separate UI header and rebuilt modules.
  modulemap=target/'CMixerVMCapability.modulemap'
  modulemap.write_text('module CMixerVMCapability { umbrella "'+str(source/'experimental-capability-runtime/Sources/CMixerVMCapability/include')+'" export * }\n')
  flags=[('-fmodule-map-file='+str(modulemap)) if x.startswith('-fmodule-map-file=') and 'CMixerVMCapability' in x else x for x in flags]
  flags=[x.replace(str(base/'native/include'),str(native/platform/'include')) for x in flags]
  if platform=='ios':
   flags[flags.index('-sdk')+1]=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
   modules=base/'ios/out/Products/Release-iphoneos'
  else:
   modules=base/'android/aarch64-unknown-linux-android28/release/Modules'
   if '-module-cache-path' in flags:flags[flags.index('-module-cache-path')+1]=str(target/'cache')
  flags=flags[:1]+['-I',str(target)]+flags[1:]+['-I',str(modules),'-Xcc','-I'+str(native/platform/'include')]
  bind(modules)
  for option in flags:
   if option.startswith('-fmodule-map-file='):bind(option.split('=',1)[1])
  developer='/Applications/Xcode_26.6.app/Contents/Developer' if platform=='android' else '/Applications/Xcode.app/Contents/Developer'
  run(platform+'-swift-version',[flags[0],'--version'],developer=developer)
  layers=[('MixerUI','sdk/Sources/MixerUI'),('MixerGuest','sdk/Sources/MixerGuest')]
  if platform=='ios':layers+=[('MixerApple','sdk/Sources/MixerApple')]
  layers += [('MixerExperimentalCapabilityRuntime','experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime'),('MixerCapabilityActivation','capability-activation/Sources/MixerCapabilityActivation')]
  for name,folder in layers:
   output=target/(name+'.swiftmodule');obj=target/(name+'.o')
   run(platform+'-'+name,flags+['-module-name',name,'-emit-module','-emit-module-path',str(output),'-emit-object','-o',str(obj)]+[str(x) for x in sorted((source/folder).glob('*.swift'))],developer=developer)
   record['artifacts'][platform+'-'+name]={'module_sha256':sha(output),'object_sha256':sha(obj)}
 for name,digest in candidate['source_files'].items():assert sha(source/name)==digest,name
 for name,digest in record['inputs'].items():assert sha(Path(name))==digest,name
 record['status']='public consumer privacy and full target-only mobile compilation passed'
except BaseException as error:record['status']='failed';record['failure']=repr(error);raise
finally:save()
print('RECEIPT '+sha(out/'receipt.json'))
