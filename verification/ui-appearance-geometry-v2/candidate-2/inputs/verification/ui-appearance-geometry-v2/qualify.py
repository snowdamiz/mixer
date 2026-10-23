from pathlib import Path
import datetime,hashlib,importlib.util,json,os,shutil,subprocess,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
candidate='candidate-2'
OUT=HERE/candidate;OUT.mkdir(exist_ok=False)
SNAP=OUT/'inputs';SNAP.mkdir()
BUILD=HERE/'build'/candidate;BUILD.mkdir(parents=True,exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
paths=[ROOT/'sdk/Package.swift',HERE/'PublicConsumer.swift',HERE/'qualify.py']
paths += [p for base in ['sdk/Sources','sdk/Tests'] for p in (ROOT/base).rglob('*') if p.is_file()]
contract=ROOT/'verification/ui-measured-appearance-v2-contract'
paths += [contract/'shape-definitions.json',contract/'descriptor-schema.json',contract/'mixer-measured-default-v2.json',contract/'scripts/check-contract.py',contract/'inputs/verification/apple-appearance-font-profile/type-profiles.json',ROOT/'docs/ui-measured-appearance-v2-contract.md',ROOT/'verification/ui-measured-appearance-v2-root-review/acceptance.json']
manifest={str(p.relative_to(ROOT)):sha(p) for p in sorted(set(paths))}
for p in paths:
 dest=SNAP/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
commands=[];artifacts={};status='failed';counts={}
def run(name,args,env=None):
 argv=[str(x) for x in args]
 p=subprocess.run(argv,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=600)
 log=OUT/(name+'.log');log.write_bytes(p.stdout)
 commands.append({'name':name,'argv':argv,'exit':p.returncode,'environment':{k:env[k] for k in ['DEVELOPER_DIR'] if env and k in env},'log':str(log.relative_to(ROOT)),'sha256':sha(log)})
 print(name,p.returncode,flush=True)
 if p.returncode:raise RuntimeError(p.stdout.decode(errors='replace')[-5000:])
 return p.stdout.decode()
apple=dict(os.environ,DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer',PYTHONDONTWRITEBYTECODE='1')
android=dict(os.environ,DEVELOPER_DIR='/Applications/Xcode_26.6.app/Contents/Developer')
official=Path('/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swiftc')
asdk=Path('/Users/andreyyurlov/Library/org.swift.swiftpm/swift-sdks/swift-6.3.3-RELEASE_android.artifactbundle/swift-android')
try:
 run('python-version',[sys.executable,'--version'])
 run('apple-swift-version',['xcrun','swiftc','--version'],apple)
 run('xcode-version',['xcodebuild','-version'],apple)
 run('android-swift-version',[official,'--version'],android)
 ios=run('ios-sdk',['xcrun','--sdk','iphoneos','--show-sdk-path'],apple).strip()
 for mode in ['debug','release']:
  run('sdk-'+mode,['swift','test','--package-path',SNAP/'sdk','--scratch-path',BUILD/'sdk','-c',mode],apple)
 outputs=[]
 for platform,compiler,flags,env in [('host-debug','swiftc',['-Onone'],apple),('host-release','swiftc',['-O'],apple),('ios','swiftc',['-target','arm64-apple-ios17.0','-sdk',ios],apple),('android',official,['-target','aarch64-unknown-linux-android30','-sdk',asdk/'ndk-sysroot','-resource-dir',asdk/'swift-resources/usr/lib/swift-aarch64'],android)]:
  folder=BUILD/platform;folder.mkdir();host=platform.startswith('host')
  common=['-swift-version','6','-warnings-as-errors','-module-cache-path',folder/'cache','-I',folder,*flags]
  for module in ['MixerCore','MixerUI']:
   output=folder/(module+'.swiftmodule')
   args=[compiler,*common,'-parse-as-library','-emit-module','-module-name',module,'-emit-module-path',output]
   if host:args+=['-emit-library','-o',folder/('lib'+module+'.dylib')]
   if host and module=='MixerUI':args+=['-L',folder,'-lMixerCore','-Xlinker','-rpath','-Xlinker',folder]
   run(platform+'-'+module,args+sorted((SNAP/'sdk/Sources'/module).glob('*.swift')),env)
   artifacts[str(output.relative_to(ROOT))]=sha(output)
  consumer=SNAP/'verification/ui-appearance-geometry-v2/PublicConsumer.swift'
  if host:
   exe=folder/'consumer'
   run(platform+'-consumer',[compiler,*common,consumer,'-L',folder,'-lMixerUI','-lMixerCore','-Xlinker','-rpath','-Xlinker',folder,'-o',exe],env)
   artifacts[str(exe.relative_to(ROOT))]=sha(exe)
   outputs.append(run(platform+'-run',[exe],env))
  else:run(platform+'-consumer',[compiler,*common,'-typecheck',consumer],env)
 if outputs[0]!=outputs[1]:raise RuntimeError('Debug/Release diverged')
 sys.dont_write_bytecode=True
 spec=importlib.util.spec_from_file_location('contract',SNAP/'verification/ui-measured-appearance-v2-contract/scripts/check-contract.py');model=importlib.util.module_from_spec(spec);spec.loader.exec_module(model)
 for line in outputs[0].splitlines():
  row=json.loads(line);kind=row['kind'];counts[kind]=counts.get(kind,0)+1
  if kind=='group':expected=model.group_path(row['w'],row['h'],row['r']);actual=row['commands']
  elif kind=='fixed':
   v=model.SHAPES['fixedPaths'][row['name']];expected=[v['width64'],v['height64'],v['commands']];actual=[row['w'],row['h'],row['commands']]
  elif kind=='thumbOrigin':expected=[1536 if row['checked']!=row['rtl'] else 128,128];actual=[row['x'],row['y']]
  elif kind=='pixel':expected=[(row['c']*row['d']+32768)//65536,row['c']*row['d']/65536];actual=[row['edge'],row['continuous']]
  else:raise RuntimeError('unknown output')
  if expected!=actual:raise RuntimeError('contract mismatch '+str(row))
 if counts!={'group':980,'fixed':2,'thumbOrigin':4,'pixel':72}:raise RuntimeError('missing outputs')
 for p,h in manifest.items():
  if sha(ROOT/p)!=h or sha(SNAP/p)!=h:raise RuntimeError('input changed '+p)
 status='passed-host-and-module-geometry'
finally:
 receipt={'status':status,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sourceRevision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'sourceGitTree':subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=ROOT,text=True).strip(),'inputBindings':manifest,'inputTreeSHA256':hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'commands':commands,'derivedArtifacts':artifacts,'publicOutputCountsPerMode':counts,'scope':'Closed V2 authored geometry, exact frozen contract output and bounded conversion; complete frozen SDK host tests and iOS/officialAndroid public module compilation. No native toolkit drawing, default renderer change, display/health, physical design parity or release authority.'}
 (OUT/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print('PASS',counts)
