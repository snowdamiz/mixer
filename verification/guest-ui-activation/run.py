#!/usr/bin/env python3
"""Snapshot current UI integration; rebuild changed layers, reuse frozen core deps."""
import argparse, hashlib, json, os, plistlib, re, shutil, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; HERE=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--name',required=True);parser.add_argument('--modes',nargs='+',default=['debug','release','tsan']);args=parser.parse_args()
assert re.fullmatch('[a-z0-9-]+',args.name)
out=HERE/args.name;out.mkdir(exist_ok=False)
work=HERE/'.build'/args.name;work.mkdir(parents=True,exist_ok=False);source=work/'source'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
ownerpath=ROOT/'verification/capability-cold-start-runtime/2026-10-23-candidate-1/receipt.json';owner=json.loads(ownerpath.read_text())
native=ROOT/'experimental-capability-runtime/build-verification/local/guest-ui-1adb25c-v2/host'
assert sha(native/'lib/libmixer_vm_capability_experimental.a')=='4d3b6dc36ea034d5604299752d560cbbc0615002b6b5ef4e5c25bbb3cb7c6120'
paths=[]
for folder in ['sdk/Sources/MixerUI','sdk/Sources/MixerGuest','sdk/Sources/MixerApple','experimental-capability-runtime/Sources','capability-activation/Sources']:
 paths += [p for p in (ROOT/folder).rglob('*') if p.is_file()]
tests=sorted(p for p in (ROOT/'capability-activation/Tests/MixerCapabilityActivationTests').glob('*.swift') if not p.name.startswith('GuestUIPresentation'))
paths+=tests+[ROOT/'verification/capability-cold-start-runtime/Bundle.swift']
inputs={str(p.relative_to(ROOT)):sha(p) for p in sorted(set(paths))}
for name,digest in inputs.items():
 dest=source/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest);assert sha(dest)==digest
record={'status':'running','head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'runner_sha256':sha(Path(__file__)),'owner_receipt_sha256':sha(ownerpath),'source':str(source),'source_files':inputs,'borrowed_files':{},'commands':[],'artifacts':{},'scope':'Integrated SDK/UI/bridge/activation source snapshot with one immutable native-only UI archive. Frozen unchanged core/capability/crypto/updates/identity/C dependencies reused. Existing activation plus new signed UI/signal tests, excluding independently owned presentation tests. No physical device or full visible window qualification.'}
def save(): (out/'receipt.json').write_text(json.dumps(record,indent=2)+'\n')
def run(name,command,extra=None,timeout=180):
 env=os.environ|{'DEVELOPER_DIR':'/Applications/Xcode.app/Contents/Developer'}|(extra or {})
 try:
  p=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,timeout=timeout);data=p.stdout+p.stderr;code=p.returncode
 except subprocess.TimeoutExpired as e:data=(e.stdout or b'')+(e.stderr or b'');code=124
 path=out/(name+'.log');path.write_bytes(data)
 record['commands'].append({'name':name,'command':command,'environment':{'DEVELOPER_DIR':env['DEVELOPER_DIR']}|(extra or {}),'exit_code':code,'log':str(path.relative_to(ROOT)),'log_sha256':sha(path)});save()
 print(name+': '+str(code),flush=True)
 if code: raise RuntimeError(name+' failed; log retained')
 return data.decode(errors='replace')
try:
 run('swift-version',['swift','--version'])
 for mode in args.modes:
  assert mode in ['debug','release','tsan']
  oldproducts=Path(owner['export']).parent/mode/'products';products=work/mode/'products';products.mkdir(parents=True)
  borrowed=ROOT/'capability-activation/.build/transitions-qualified-2026-10-23-candidate-3'/('retained-'+mode)/'products'
  maps=work/mode/'modulemaps';maps.mkdir()
  originals=borrowed.parent/'modulemaps'
  for p in originals.glob('*.modulemap'):
   if p.name=='CMixerVMCapability.modulemap':
    (maps/p.name).write_text('module CMixerVMCapability { umbrella "'+str(source/'experimental-capability-runtime/Sources/CMixerVMCapability/include')+'" export * }\n')
   else:shutil.copyfile(p,maps/p.name)
  flags=['-parse-as-library','-swift-version','6','-warnings-as-errors','-enable-testing','-I',str(products),'-I',str(borrowed),'-F','/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/Library/Frameworks']
  for p in sorted(maps.glob('*.modulemap')):flags+=['-Xcc','-fmodule-map-file='+str(p)]
  flags+=['-Xcc','-I'+str(native/'include')]
  if mode=='release':flags+=['-O']
  if mode=='tsan':flags+=['-sanitize=thread']
  for name,folder in [('MixerUI','sdk/Sources/MixerUI'),('MixerGuest','sdk/Sources/MixerGuest'),('MixerApple','sdk/Sources/MixerApple'),('MixerExperimentalCapabilityRuntime','experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime')]:
   command=['swiftc',*flags,'-whole-module-optimization','-emit-object','-emit-module','-module-name',name,'-emit-module-path',str(products/(name+'.swiftmodule')),*map(str,sorted((source/folder).glob('*.swift'))),'-o',str(products/(name+'.o'))]
   run(mode+'-'+name,command)
  borrowed_names=['Crypto','MixerCapabilities','MixerCore','MixerRuntimeIdentity','MixerUpdates','CMixerVMCapability','MixerCapabilityDurableIO','MixerCapabilityIO','MixerDurableIO']
  objects=[borrowed/(name+'.o') for name in borrowed_names]+[products/(name+'.o') for name in ['MixerUI','MixerGuest','MixerApple','MixerExperimentalCapabilityRuntime']]
  for name in borrowed_names:
   for ext in ['.o','.swiftmodule']:
    p=borrowed/(name+ext)
    if p.is_file():record['borrowed_files'][str(p)]=sha(p)
    elif p.is_dir():
     for member in sorted(p.rglob('*')):
      if member.is_file():record['borrowed_files'][str(member)]=sha(member)
  for p in [native/'lib/libmixer_vm_capability_experimental.a',native/'receipt.json',*sorted((native/'include').glob('*.h'))]:record['borrowed_files'][str(p)]=sha(p)
  dylib=products/'libMixerCapabilityActivationGuestUI.dylib'
  command=['swiftc',*flags,'-emit-library','-emit-module','-module-name','MixerCapabilityActivation','-emit-module-path',str(products/'MixerCapabilityActivation.swiftmodule'),*map(str,sorted((source/'capability-activation/Sources/MixerCapabilityActivation').glob('*.swift'))),*map(str,objects),'-L',str(native/'lib'),'-lmixer_vm_capability_experimental','-Xlinker','-install_name','-Xlinker','@rpath/'+dylib.name,'-o',str(dylib)]
  run(mode+'-activation',command)
  bundle=work/mode/'GuestUIActivationTests.xctest';binary=bundle/'Contents/MacOS/GuestUIActivationTests';binary.parent.mkdir(parents=True)
  (bundle/'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleExecutable':binary.name,'CFBundleIdentifier':'org.mixer.ui.activation.tests','CFBundlePackageType':'BNDL','CFBundleVersion':'1'}))
  command=list(next(c['command'] for c in owner['commands'] if c['name']==mode+'-test-link'))
  command=[s.replace(str(oldproducts),str(products)).replace('libMixerCapabilityActivationColdStart','libMixerCapabilityActivationGuestUI').replace('-lMixerCapabilityActivationColdStart','-lMixerCapabilityActivationGuestUI').replace(str(originals),str(maps)).replace(str(borrowed.parent.parent/'native/include'),str(native/'include')) for s in command if not s.endswith('.swift')]
  command[command.index('-o')+1]=str(binary)
  command += [str(source/p.relative_to(ROOT)) for p in tests]+[str(source/'verification/capability-cold-start-runtime/Bundle.swift')]
  run(mode+'-test-link',command,timeout=240)
  oldtest=next(c for c in owner['commands'] if c['name']==mode+'-tests')
  output=run(mode+'-tests',[oldtest['command'][0],str(bundle)],oldtest['environment'],timeout=240)
  counts=re.findall(r'Executed (\d+) tests?, with (\d+) failures',output);assert counts and counts[-1][1]=='0',counts
  symbols=run(mode+'-native-symbols',['nm','-gU',str(dylib)])
  for name in ['mixer_vm_capability_session_create_v1','mixer_vm_capability_guest_ui_validate_v1']:
   assert len(re.findall(r'\b_'+name+r'$',symbols,re.M))==1,name
  symbols=run(mode+'-test-symbols',['nm','-gU',str(binary)]);assert not re.search(r'\b_mixer_vm_\w+$',symbols,re.M)
  record['artifacts'][mode]={'tests':int(counts[-1][0]),'dylib':{'path':str(dylib),'sha256':sha(dylib)},'bundle_binary':{'path':str(binary),'sha256':sha(binary)}};save()
 for name,digest in inputs.items():assert sha(source/name)==digest
 for name,digest in record['borrowed_files'].items():assert sha(Path(name))==digest
 record['working_tree_changes_after_snapshot']=[name for name,digest in inputs.items() if sha(ROOT/name)!=digest]
 record['status']='Snapshot integration tests passed for '+', '.join(args.modes)
except BaseException as error:
 record['status']='failed';record['failure']=repr(error);raise
finally:save()
print(json.dumps({'receipt':str(out/'receipt.json'),'sha256':sha(out/'receipt.json'),'status':record['status']}))
