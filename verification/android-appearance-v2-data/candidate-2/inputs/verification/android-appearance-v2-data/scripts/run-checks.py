#!/usr/bin/env python3
"""Reproducible frozen-source Java/Swift differential data verification."""
from pathlib import Path
import datetime, gzip, hashlib, json, os, shutil, subprocess, sys, time
HERE=Path(__file__).resolve().parents[1];ROOT=HERE.parents[1]
CANDIDATE=HERE/sys.argv[1];CANDIDATE.mkdir(exist_ok=False)
INPUT=CANDIDATE/'inputs';INPUT.mkdir();LOG=CANDIDATE/'logs';LOG.mkdir()
BUILD=HERE/'build'/sys.argv[1];BUILD.mkdir(parents=True,exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
paths=['AGENTS.md','mixer-product-plan.md','docs/ui-measured-appearance-v2-contract.md',
 'verification/ui-measured-appearance-v2-contract/descriptor-schema.json',
 'verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json',
 'verification/ui-measured-appearance-v2-contract/shape-definitions.json',
 'verification/ui-measured-appearance-v2-root-review/acceptance.json',
 'verification/ui-appearance-descriptor-v2/candidate-1/receipt.json',
 'verification/ui-appearance-geometry-v2/candidate-3/receipt.json',
 'verification/ui-shared-appearance-contract/v2/mixer-default-appearance-v1.json',
 'native/android/app/src/dev/mixer/android/AppearanceDescriptorV1.java',
 'native/android/app/src/dev/mixer/android/AppearanceDescriptorV2.java',
 'native/android/app/src/dev/mixer/android/AppearanceGeometryV2.java',
 'native/android/tests/AppearanceDescriptorTests.java',
 'native/android/tests/AppearanceDescriptorV2Tests.java',
 'native/android/tests/AppearanceGeometryV2Tests.java',
 'verification/android-appearance-descriptor/candidate-2/cases.tsv.gz',
 'verification/android-appearance-v2-data/SwiftDataProbe.swift',
 'verification/android-appearance-v2-data/scripts/make-corpus.py',
 'verification/android-appearance-v2-data/scripts/run-checks.py']
paths += ['sdk/Sources/MixerUI/'+p+'.swift' for p in ['AppearanceValuesV1','AppearanceDefaultV1','AppearanceDescriptorV1','AppearanceMetricMathV1',
 'SharedTextProfilesV1','AppearanceGeometryV2','AppearanceValuesV2','AppearanceDefaultV2','AppearanceDescriptorV2']]
manifest={}
for relative in paths:
 p=ROOT/relative;dst=INPUT/relative;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(p.read_bytes());manifest[relative]=sha(dst)
# Bind the exact actual sources to the already-sealed Swift implementation.
sealed=json.loads((ROOT/'verification/ui-appearance-descriptor-v2/candidate-1/receipt.json').read_text())
for p,h in manifest.items():
 if p.startswith('sdk/Sources/MixerUI/'):
  assert sealed['inputManifest'][p]==h,('Swift seal drift',p)
commands=[];artifacts={}
receipt={'format':'mixer.android-appearance-v2-data-receipt.1','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'sourceRevision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
 'sourceGitTree':subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=ROOT,text=True).strip(),
 'inputManifest':manifest,'inputTreeSHA256':hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
 'commands':commands,'artifacts':artifacts,'status':'not-run',
 'scope':'Package-private immutable typed Java V2 descriptor reader and closed paths/conversions, independent host Swift/Java differential data checks; no Android framework or native operation execution.',
 'limitations':['Synthetic resource/font metadata is not actual bytes, identity, glyph coverage, installation or resource loading.',
 'No V2 native consumers, resolver, host bootstrap, JNI, packet, signing, supported-operation, display-health or OTA authority supplied by this data slice.',
 'Host JVM default and -Xint modes and host Swift Debug/Release are data checks, not native iOS/Android receipts.',
 'Phones disconnected; physical parity, raster, measurement, accessibility, interactions and configuration/preference handling remain pending.',
 'Published separate-repository FieldLog, compiler, signing, store, customer, operational and all GA gates remain pending.']}
(CANDIDATE/'input-lock.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
env=dict(os.environ,DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer')
def run(name,args,cwd=INPUT):
 argv=[str(a) for a in args];start=time.monotonic()
 result=subprocess.run(argv,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=300)
 stdout=LOG/(name+'.stdout');stderr=LOG/(name+'.stderr');stdout.write_bytes(result.stdout);stderr.write_bytes(result.stderr)
 commands.append({'name':name,'argv':argv,'cwd':str(cwd),'environment':{'DEVELOPER_DIR':env['DEVELOPER_DIR']},
  'exit':result.returncode,'seconds':time.monotonic()-start,'stdout':str(stdout.relative_to(ROOT)),
  'stdoutSHA256':sha(stdout),'stderr':str(stderr.relative_to(ROOT)),'stderrSHA256':sha(stderr)})
 print(name,result.returncode,flush=True)
 if result.returncode:raise RuntimeError((result.stdout+result.stderr).decode(errors='replace')[-6000:])
 return result.stdout
java=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home/bin/java');javac=java.with_name('javac')
try:
 run('java-version',[java,'-version']);run('javac-version',[javac,'-version']);run('swift-version',['xcrun','swiftc','--version']);run('python-version',[sys.executable,'--version']);run('xcode-version',['xcodebuild','-version'])
 corpus=CANDIDATE/'corpus'
 run('make-corpus',[sys.executable,INPUT/'verification/android-appearance-v2-data/scripts/make-corpus.py',corpus])
 descriptors=BUILD/'descriptors.tsv';descriptors.write_bytes(gzip.decompress((corpus/'descriptors.tsv.gz').read_bytes()))
 v1cases=BUILD/'v1-cases.tsv';v1cases.write_bytes(gzip.decompress((INPUT/'verification/android-appearance-descriptor/candidate-2/cases.tsv.gz').read_bytes()))
 geometry=corpus/'geometry.tsv';v1=INPUT/'verification/ui-shared-appearance-contract/v2/mixer-default-appearance-v1.json';golden=INPUT/'verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json'
 javafiles=[INPUT/p for p in paths if p.endswith('.java')]
 classes=BUILD/'classes';classes.mkdir()
 run('javac',[javac,'--release','17','-Xlint:all','-Werror','-d',classes,*javafiles])
 outputs={}
 for mode,flags in [('default',[]),('interpreted',['-Xint'])]:
  outputs[('java',mode,'descriptor')]=run('java-'+mode+'-descriptor',[java,*flags,'-cp',classes,'dev.mixer.android.AppearanceDescriptorV2Tests',descriptors,v1])
  outputs[('java',mode,'geometry')]=run('java-'+mode+'-geometry',[java,*flags,'-cp',classes,'dev.mixer.android.AppearanceGeometryV2Tests',geometry])
  run('java-'+mode+'-v1-regression',[java,*flags,'-cp',classes,'dev.mixer.android.AppearanceDescriptorTests',v1cases])
 sources=[INPUT/p for p in paths if p.startswith('sdk/') and p.endswith('.swift')]
 for mode,flag in [('debug','-Onone'),('release','-O')]:
  binary=BUILD/('swift-'+mode)
  run('swift-compile-'+mode,['xcrun','swiftc','-swift-version','6','-warnings-as-errors',flag,'-module-cache-path',BUILD/('cache-'+mode),*sources,INPUT/'verification/android-appearance-v2-data/SwiftDataProbe.swift','-o',binary])
  outputs[('swift',mode,'descriptor')]=run('swift-'+mode+'-descriptor',[binary,'descriptor',descriptors,v1,golden])
  outputs[('swift',mode,'geometry')]=run('swift-'+mode+'-geometry',[binary,'geometry',geometry])
 for domain in ['descriptor','geometry']:
  values=[v for k,v in outputs.items() if k[-1]==domain]
  assert len(values)==4 and len(set(values))==1,'product output differs:'+domain
 # Independently check exact fixed paths against the frozen shape definitions.
 lines=outputs[('java','default','geometry')].decode().splitlines();shapes=json.loads((INPUT/'verification/ui-measured-appearance-v2-contract/shape-definitions.json').read_text())['fixedPaths']
 for index,name in [(0,'track63x28Continuous2'),(1,'thumb37x24Continuous2')]:
  s=shapes[name];expected=name+'|'+str(s['width64'])+','+str(s['height64'])
  for c in s['commands']:expected+='|'+c['op']+''.join(':'+str(p[0])+','+str(p[1]) for p in c['points64'])
  assert lines[index].split('\t')[1]==expected,'frozen fixed path differs'
 # V1 product source/golden must remain identical to the parent revision.
 preserved={}
 for p,h in manifest.items():
  if (p.startswith('sdk/Sources/') and p.endswith('V1.swift')) or p in ['native/android/app/src/dev/mixer/android/AppearanceDescriptorV1.java','verification/ui-shared-appearance-contract/v2/mixer-default-appearance-v1.json']:
   assert subprocess.check_output(['git','show',receipt['sourceRevision']+':'+p],cwd=ROOT)==(INPUT/p).read_bytes(),('V1 changed',p)
   preserved[p]=h
 receipt['unchangedV1Bindings']=preserved
 receipt['descriptorCases']=len(descriptors.read_text().splitlines());receipt['geometryCases']=len(geometry.read_text().splitlines())
 receipt['comparedOutputs']={domain:hashlib.sha256(outputs[('java','default',domain)]).hexdigest() for domain in ['descriptor','geometry']}
 receipt['status']='passed-data-only'
finally:
 for folder in [BUILD,CANDIDATE/'corpus',LOG]:
  if folder.exists():
   for p in sorted(folder.rglob('*')):
    if p.is_file():artifacts[str(p.relative_to(ROOT))]=sha(p)
 receipt['liveInputChangesSinceSnapshot']=[p for p,h in manifest.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h]
 (CANDIDATE/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print('PASS exact Swift Debug/Release and JVM default/interpreted descriptor+geometry outputs; V1 regression; no native parity claim',flush=True)
