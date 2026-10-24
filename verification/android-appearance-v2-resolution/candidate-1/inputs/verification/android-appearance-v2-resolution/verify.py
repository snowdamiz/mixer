#!/usr/bin/env python3
"""Freeze actual product bytes and independently compile every host variant.
This runner never discovers, attaches, compiles for or operates physical devices."""
from pathlib import Path
import base64, datetime, gzip, hashlib, json, os, shutil, subprocess, sys, time
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
label=sys.argv[1] if len(sys.argv)==2 else 'candidate-1'
if not label or '/' in label or label in ('.','..'):raise ValueError('new single candidate label required')
OUT=HERE/label;OUT.mkdir(exist_ok=False)
INPUT=OUT/'inputs';INPUT.mkdir(); BUILD=HERE/'.build'/label;BUILD.mkdir(parents=True,exist_ok=False)
sha=lambda data:hashlib.sha256(data).hexdigest()
paths=['AGENTS.md','mixer-product-plan.md','docs/ui-measured-appearance-v2-contract.md','docs/ui-appearance-resolution-v2.md','docs/android-appearance-v2-resolution.md',
 'verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json',
 'verification/ui-measured-appearance-v2-contract/descriptor-schema.json','verification/ui-measured-appearance-v2-contract/shape-definitions.json',
 'verification/android-appearance-v2-root-review/acceptance.json',
 'native/android/app/src/dev/mixer/android/Json.java','native/android/app/src/dev/mixer/android/UiPacket.java',
 'native/android/app/src/dev/mixer/android/AppearanceDescriptorV2.java','native/android/app/src/dev/mixer/android/AppearanceGeometryV2.java',
 'native/android/app/src/dev/mixer/android/AppearanceResolverV2.java','native/android/tests/AppearanceResolverV2Tests.java',
 'verification/android-appearance-v2-resolution/verify.py','verification/android-appearance-v2-resolution/make_corpus.py',
 'verification/android-appearance-v2-resolution/SwiftResolutionProbe.swift']
paths += [str(p.relative_to(ROOT)) for module in ['MixerCore','MixerUI'] for p in sorted((ROOT/'sdk/Sources'/module).glob('*.swift'))]
manifest={}
for relative in paths:
 data=(ROOT/relative).read_bytes();target=INPUT/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);manifest[relative]=sha(data)
receipt=dict(format='mixer.android-appearance-v2-resolution.1',status='running',startedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 sourceRevision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
 sourceGitTree=subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=ROOT,text=True).strip(),
 inputManifest=manifest,inputTreeSHA256=sha(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()),commands=[],artifacts={},
 scope='Pure immutable Java V2 data resolution through unchanged actual UiPacket; actual frozen Swift Debug/Release resolver and packet output compared with fresh JDK25 release17 JVM default/-Xint variants.',
 limits=['No Android framework/native resources/fonts/preference capture/build support/widget/layout/attachment/display/health/signed/OTA authority.',
 'Explicit first/last baseline properties and nested lists remain rejected by the unchanged existing V1 UiPacket profile; theme-default baseline is untrusted data only.',
 'No physical two-platform parity, immutable published separate-repository FieldLog, store/customer/operational or GA qualification.'],
 physicalDevices=dict(discovered=False,used=False,reconnectionRequested=False))
def save(): (OUT/'receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
def artifact(path):receipt['artifacts'][str(path.relative_to(ROOT))]=dict(bytes=path.stat().st_size,sha256=sha(path.read_bytes()))
def run(name,args,cwd=INPUT,expected=False):
 start=time.monotonic();argv=list(map(str,args));env=dict(os.environ,DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer')
 completed=subprocess.run(argv,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=600)
 record=dict(name=name,argv=argv,cwd=str(cwd),exitCode=completed.returncode,expectedFailure=expected,seconds=time.monotonic()-start,
  environmentOverrides=dict(DEVELOPER_DIR=env['DEVELOPER_DIR']))
 for stream,data in [('stdout',completed.stdout),('stderr',completed.stderr)]:
  target=OUT/(name+'.'+stream+('.gz' if len(data)>100000 else '.log'))
  target.write_bytes(gzip.compress(data,mtime=0) if target.suffix=='.gz' else data)
  record[stream]=dict(path=str(target.relative_to(ROOT)),bytes=len(data),sha256=sha(data),storedSHA256=sha(target.read_bytes()))
 receipt['commands'].append(record);save();print(name,completed.returncode,flush=True)
 if (completed.returncode==0)==expected:raise RuntimeError(name+'\n'+(completed.stdout+completed.stderr).decode(errors='replace')[-5000:])
 return completed.stdout
java=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home/bin/java');javac=java.with_name('javac')
try:
 save();run('java-version',[java,'-version']);run('javac-version',[javac,'-version']);run('swift-version',['xcrun','swiftc','--version']);run('xcode-version',['xcodebuild','-version']);run('python-version',[sys.executable,'--version'])
 run('make-corpus',[sys.executable,INPUT/'verification/android-appearance-v2-resolution/make_corpus.py',INPUT,OUT/'corpus'])
 corpus=OUT/'corpus/cases.tsv';swift_outputs=[]
 for mode,flag in [('debug','-Onone'),('release','-O')]:
  work=BUILD/('swift-'+mode);sources=work/'inputs';sources.mkdir(parents=True)
  for relative in paths:
   if relative.endswith('.swift'):
    target=sources/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((INPUT/relative).read_bytes())
  common=['-swift-version','6','-warnings-as-errors','-parse-as-library',flag,'-module-cache-path',work/'cache','-I',work]
  for module in ['MixerCore','MixerUI']:
   args=['xcrun','swiftc',*common,'-module-name',module,'-emit-module','-emit-module-path',work/(module+'.swiftmodule'),'-emit-library','-o',work/('lib'+module+'.dylib')]
   if module=='MixerUI':args += ['-L',work,'-lMixerCore','-Xlinker','-rpath','-Xlinker',work]
   run('swift-'+mode+'-'+module,[*args,*sorted((sources/'sdk/Sources'/module).glob('*.swift'))],cwd=sources)
  binary=work/'swift-probe'
  run('swift-'+mode+'-probe-compile',['xcrun','swiftc',*common,sources/'verification/android-appearance-v2-resolution/SwiftResolutionProbe.swift','-L',work,'-lMixerUI','-lMixerCore','-Xlinker','-rpath','-Xlinker',work,'-o',binary],cwd=sources)
  output=run('swift-'+mode+'-probe',[binary,corpus],cwd=sources);swift_outputs.append(output)
 if swift_outputs[0]!=swift_outputs[1]:raise RuntimeError('actual Swift Debug/Release output mismatch')
 packet_input=BUILD/'actual-swift-packets.tsv';packet_input.write_bytes(swift_outputs[0]);artifact(packet_input)
 cases={}
 for line in swift_outputs[0].decode().splitlines():
  f=line.split('\t');raw=base64.b64decode(f[5]);cases[f[0]]=raw.decode() if raw.startswith(b'error:') else json.loads(raw)
 (OUT/'actual-swift-packets.tsv.gz').write_bytes(gzip.compress(swift_outputs[0],mtime=0))
 summaries=[]
 for mode,flags in [('default',[]),('interpreted',['-Xint'])]:
  work=BUILD/('java-'+mode);sources=work/'inputs';classes=work/'classes';sources.mkdir(parents=True);classes.mkdir()
  javafiles=[]
  for relative in paths:
   if relative.endswith('.java'):
    target=sources/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((INPUT/relative).read_bytes());javafiles.append(target)
  run('javac-'+mode,[javac,'--release','17','-Xlint:all','-Werror','-d',classes,*javafiles],cwd=sources)
  output=run('java-'+mode,[java,*flags,'-cp',classes,'dev.mixer.android.AppearanceResolverV2Tests',packet_input],cwd=sources)
  actual={}
  for line in output.decode().splitlines():
   name,encoded=line.split('\t');raw=base64.b64decode(encoded);actual[name]=raw.decode() if raw.startswith(b'error:') else json.loads(raw)
  mismatch=[]
  for name,value in cases.items():
   if actual.get(name)!=value:mismatch.append(name)
  (OUT/('mismatches-'+mode+'.json')).write_text(json.dumps(mismatch,indent=2)+'\n')
  if mismatch:raise RuntimeError('Java/Swift output mismatch '+str(mismatch[:10]))
  if len(actual)!=len(cases):raise RuntimeError('missing/extra actual output')
  summaries.append(dict(mode=mode,cases=len(actual),accepted=sum(isinstance(v,dict) for v in actual.values()),rejected=sum(isinstance(v,str) for v in actual.values())))
  for file in classes.rglob('*.class'):artifact(file)
 for file in BUILD.rglob('*'):
  if file.is_file() and (file.suffix in ('.dylib','.swiftmodule') or file.name=='swift-probe'):artifact(file)
 receipt['differentialModes']=summaries;receipt['unchangedV1Inputs']={}
 for relative in ['native/android/app/src/dev/mixer/android/UiPacket.java','native/android/app/src/dev/mixer/android/Json.java']:
  committed=subprocess.check_output(['git','show',receipt['sourceRevision']+':'+relative],cwd=ROOT)
  if committed!=(INPUT/relative).read_bytes():raise RuntimeError('retained V1 input differs '+relative)
  receipt['unchangedV1Inputs'][relative]=sha(committed)
 receipt['status']='passed-pure-data-only-awaiting-independent-review'
except Exception as error:
 receipt.update(status='failed',error=str(error));raise
finally:
 receipt['completedUTC']=datetime.datetime.now(datetime.timezone.utc).isoformat()
 receipt['liveInputChangesSinceSnapshot']=[p for p,h in manifest.items() if not (ROOT/p).is_file() or sha((ROOT/p).read_bytes())!=h]
 for folder in [OUT/'corpus']:
  for file in folder.rglob('*') if folder.exists() else []:
   if file.is_file():artifact(file)
 save()
print('PASS actual frozen Swift D/R and fresh JVM default/-Xint complete plan/state equality; host data only')
