#!/usr/bin/env python3
"""Compile/run the actual private Android consumer against only an explicit emulator."""
import argparse, datetime, hashlib, json, os, re, shutil, subprocess, sys, zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SDK=Path('/opt/homebrew/share/android-commandlinetools')
JDK=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
BT=SDK/'build-tools/37.0.0'
JAR=SDK/'platforms/android-37.0/android.jar'
PACKAGE='dev.mixer.android.nativeappearancev2'
PRODUCT=[f'native/android/app/src/dev/mixer/android/{name}.java' for name in ['Json','UiPacket','AppearanceDescriptorV2','AppearanceGeometryV2','AppearanceResolverV2','AppearanceNativePathsV2','NativeEnvironmentV2','InstalledAppearanceV2','NativeAppearanceViewsV2','NativeRenderer']]
TESTS=[f'native/android/tests/NativeAppearanceV2{name}.java' for name in ['Activity','Instrumentation']]
INPUTS=PRODUCT+TESTS+['AGENTS.md','mixer-product-plan.md','docs/ui-measured-appearance-v2-contract.md','docs/native-appearance-v2-staging.md','docs/native-appearance-v2-implementation-boundary.md','docs/android-native-appearance-v2.md','verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json','verification/android-native-appearance-v2/qualify.py','verification/android-native-appearance-v2/AndroidManifest.xml','verification/android-native-appearance-v2/emulator-session.json','verification/apple-native-appearance-v2/shared-fixture/native-packet-v1.bin','verification/apple-native-appearance-v2/shared-fixture/descriptor.json']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);p.add_argument('--emulator',required=True);p.add_argument('--paired-viewport',action='store_true');args=p.parse_args()
 if not re.fullmatch(r'candidate-[0-9]+',args.output) or not re.fullmatch(r'emulator-[0-9]{4,5}',args.emulator):p.error('bounded candidate-N and explicit emulator-N required')
 out=HERE/args.output;out.mkdir();build=HERE/'build'/args.output;build.mkdir(parents=True)
 env=dict(os.environ,JAVA_HOME=str(JDK),PATH=str(JDK/'bin')+os.pathsep+os.environ['PATH']);commands=[];manifest={};status='failed';error=None;target={};native={}
 revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 tree=subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=ROOT,text=True).strip()
 initial=subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True)
 for name in INPUTS:
  dest=out/'inputs'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,dest);manifest[name]=sha(dest)
 def run(name,argv,binary=False,timeout=120):
  command=list(map(str,argv));completed=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,timeout=timeout)
  log=out/(name+('.png' if binary else '.log'));log.write_bytes(completed.stdout if binary else completed.stdout+completed.stderr)
  commands.append(dict(name=name,argv=command,cwd=str(ROOT),exitCode=completed.returncode,output=str(log.relative_to(ROOT)),sha256=sha(log)))
  print(name,completed.returncode,flush=True)
  if completed.returncode:raise RuntimeError(name+': '+(completed.stdout+completed.stderr).decode(errors='replace')[-7000:])
  return completed.stdout if binary else completed.stdout.decode()
 try:
  for name,argv in [('python-version',[sys.executable,'--version']),('java-version',[JDK/'bin/java','--version']),('javac-version',[JDK/'bin/javac','--version']),('d8-version',[BT/'d8','--version']),('aapt2-version',[BT/'aapt2','version']),('apksigner-version',[BT/'apksigner','version']),('adb-version',[SDK/'platform-tools/adb','version']),('emulator-version',[SDK/'emulator/emulator','-version'])]:run(name,argv)
  production=build/'production';production.mkdir();sources=[out/'inputs'/x for x in PRODUCT+TESTS]
  run('production-java-compile',[JDK/'bin/javac','--release','17','-Xlint:all','-Werror','-classpath',JAR,'-d',production,*sources[:len(PRODUCT)]])
  pdex=build/'production-dex';pdex.mkdir();run('production-dex-min28',[BT/'d8','--min-api','28','--lib',JAR,'--output',pdex,*sorted(production.rglob('*.class'))])
  classes=build/'classes';classes.mkdir();run('instrumentation-java-compile',[JDK/'bin/javac','--release','17','-Xlint:all','-Werror','-classpath',JAR,'-d',classes,*sources])
  dex=build/'dex';dex.mkdir();run('instrumentation-dex-min36',[BT/'d8','--min-api','36','--lib',JAR,'--output',dex,*sorted(classes.rglob('*.class'))])
  unsigned=build/'unsigned.apk';run('package-manifest',[BT/'aapt2','link','-I',JAR,'--manifest',out/'inputs/verification/android-native-appearance-v2/AndroidManifest.xml','--min-sdk-version','36','--target-sdk-version','37','-o',unsigned])
  descriptor=out/'inputs/verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json'
  with zipfile.ZipFile(unsigned,'a',compression=zipfile.ZIP_DEFLATED) as apk:
   for f in sorted(dex.glob('*.dex')):apk.write(f,f.name)
   apk.write(descriptor,'assets/MixerAppearanceV2/descriptor.json')
   apk.write(out/'inputs/verification/apple-native-appearance-v2/shared-fixture/native-packet-v1.bin','assets/NativeAppearanceV2/paired-packet.bin')
  aligned=build/'aligned.apk';run('align-apk',[BT/'zipalign','-f','-p','4',unsigned,aligned])
  key=HERE/'build/test-only.keystore'
  if not key.exists():run('generate-test-only-key',[JDK/'bin/keytool','-genkeypair','-keystore',key,'-storepass','android','-keypass','android','-alias','test','-keyalg','RSA','-keysize','2048','-validity','365','-dname','CN=Mixer Native Consumer Local Test'])
  apk=build/'test.apk';run('sign-test-apk',[BT/'apksigner','sign','--ks',key,'--ks-pass','pass:android','--key-pass','pass:android','--out',apk,aligned]);run('verify-test-signature',[BT/'apksigner','verify','--verbose',apk])
  adb=[SDK/'platform-tools/adb','-s',args.emulator]
  qemu=run('target-emulator-property',adb+['shell','getprop','ro.kernel.qemu']).strip()
  if qemu!='1':raise RuntimeError('refuse non-emulator target')
  target={'serial':args.emulator,'ro.kernel.qemu':qemu}
  for prop in ['ro.product.model','ro.build.version.sdk','ro.build.fingerprint','ro.boot.qemu.avd_name','sys.boot_completed']:target[prop]=run('target-'+prop.replace('.','-'),adb+['shell','getprop',prop]).strip()
  if int(target['ro.build.version.sdk'])<36 or target['sys.boot_completed']!='1':raise RuntimeError('API36+ booted emulator required for faithful public preference capture')
  session=json.loads((out/'inputs/verification/android-native-appearance-v2/emulator-session.json').read_text())
  if session['serial']!=args.emulator:raise RuntimeError('target is not the owned dedicated test emulator')
  process=run('owned-emulator-process',['ps','-p',str(session['pid']),'-o','pid=,command='])
  if '-port '+args.emulator.split('-')[1]not in process:raise RuntimeError('dedicated emulator PID/port identity changed')
  if args.paired_viewport:
   run('owned-emulator-display-size',adb+['shell','wm','size','1206x2622'])
   run('owned-emulator-display-density',adb+['shell','wm','density','480'])
  # Actual packaged negative installations; canonical mutations are test inputs only.
  canonical=json.loads(descriptor.read_bytes());variants=[]
  variants.append(('noncanonical',descriptor.read_bytes()+b' ', 'noncanonical'))
  variants.append(('oversized',b'x'*65537,'byteLimit'))
  icon=dict(id='unused',kind='iconPNG',path='unused.png',sha256='0'*64,bytes=1,provenance='rejection-only fixture; no image bundled',scale=1,locale='und',direction='neutral')
  resources=dict(canonical);resources['resources']=[icon]
  variants.append(('unselected-resource',json.dumps(resources,sort_keys=True,separators=(',',':')).encode()+b'\n','unsupportedNativeOperation'))
  font=dict(icon);font.update(id='font',kind='fontSFNT',path='font.ttf')
  ios=json.loads(json.dumps(canonical['theme']));ios['typography']['font']=dict(kind='bundled',fallback='none',faces=[dict(resourceID='font',postScriptName='RejectOnly',weight=w,style='normal')for w in [400,600,700]])
  unselected=dict(format=canonical['format'],id=canonical['id'],mode='platformSpecific',resources=[font],iOS=ios,android=canonical['theme'],reason='actual complete unselected-font rejection fixture')
  variants.append(('unselected-font',json.dumps(unselected,sort_keys=True,separators=(',',':')).encode()+b'\n','unsupportedNativeOperation'))
  bad=json.loads(json.dumps(unselected));bad['iOS']['typography']['profiles']['l']['body']['size64']=1
  variants.append(('invalid-unselected-theme',json.dumps(bad,sort_keys=True,separators=(',',':')).encode()+b'\n','unsupportedProfile'))
  for name,data,expected in variants:
   corpus=out/'corpus';corpus.mkdir(exist_ok=True);(corpus/(name+'.json')).write_bytes(data)
   variantUnsigned=build/(name+'-unsigned.apk')
   with zipfile.ZipFile(unsigned)as original,zipfile.ZipFile(variantUnsigned,'w',compression=zipfile.ZIP_DEFLATED)as changed:
    for info in original.infolist():
     if info.filename!='assets/MixerAppearanceV2/descriptor.json':changed.writestr(info,original.read(info.filename))
    changed.writestr('assets/MixerAppearanceV2/descriptor.json',data)
   variantAligned=build/(name+'-aligned.apk');run(name+'-align',[BT/'zipalign','-f','-p','4',variantUnsigned,variantAligned])
   variantAPK=build/(name+'.apk');run(name+'-sign',[BT/'apksigner','sign','--ks',key,'--ks-pass','pass:android','--key-pass','pass:android','--out',variantAPK,variantAligned])
   run(name+'-install',adb+['install','-r','--no-incremental',variantAPK]);variantPath=run(name+'-package-path',adb+['shell','pm','path',PACKAGE]).strip()[8:]
   if run(name+'-installed-hash',adb+['shell','sha256sum',variantPath]).split()[0]!=sha(variantAPK):raise RuntimeError('negative installed APK hash differs')
   rejected=run(name+'-native-capture',adb+['shell','am','instrument','-w','-e','captureRejection',expected,PACKAGE+'/dev.mixer.android.NativeAppearanceV2Instrumentation'])
   if 'INSTRUMENTATION_RESULT: status=passed'not in rejected or 'INSTRUMENTATION_CODE: 0'not in rejected:raise RuntimeError(rejected)
  run('install-test-apk',adb+['install','-r','--no-incremental',apk]);path=run('installed-package-path',adb+['shell','pm','path',PACKAGE]).strip()
  if not path.startswith('package:/data/app/')or not path.endswith('/base.apk'):raise RuntimeError('unexpected package location')
  digest=run('installed-apk-sha256',adb+['shell','sha256sum',path[8:]]).split()[0]
  if digest!=sha(apk):raise RuntimeError('installed test APK differs')
  target['installedAPK_SHA256']=digest
  result=run('native-instrumentation',adb+['shell','am','instrument','-w',PACKAGE+'/dev.mixer.android.NativeAppearanceV2Instrumentation'],timeout=240)
  if 'INSTRUMENTATION_RESULT: status=passed'not in result or 'INSTRUMENTATION_CODE: 0'not in result:raise RuntimeError(result)
  match=re.search(r'INSTRUMENTATION_RESULT: checks=(\d+)',result)
  if not match or int(match[1])<=0:raise RuntimeError('missing native assertion count')
  native={'status':'passed','checks':int(match[1]),'scope':'actual private renderer on API37 emulator, real Activity/AssetManager/native Views and IME InputConnection; no engine/JNI join'}
  for name in ['all-ten-software','all-ten-compositor','editing-software','paired-software','paired-compositor','compact-software','pressed-focus-software']:run(name,adb+['exec-out','run-as',PACKAGE,'cat','files/'+name+'.png'],binary=True)
  for name in ['all-ten-map.json','paired-map.json','all-ten-packet.json','paired-packet.bin','appearance-descriptor.json']:
   data=run('export-'+name.replace('.','-'),adb+['exec-out','run-as',PACKAGE,'cat','files/'+name]);(out/name).write_text(data)
  for profile in ['xs','s','m','l','xl','xxl','xxxl','a1','a2','a3','a4','a5']:
   for suffix in ['-map.json','-software.png']:
    name='profile-'+profile+suffix;data=run('export-'+name.replace('.','-'),adb+['exec-out','run-as',PACKAGE,'cat','files/'+name],binary=suffix.endswith('png'))
    if suffix.endswith('json'):(out/name).write_text(data)
  (out/'preference-corpus.json').write_text(run('preference-corpus',adb+['exec-out','run-as',PACKAGE,'cat','files/preference-corpus.json']))
  status='passed-compile-and-native-emulator'
 except Exception as failure:error=repr(failure);raise
 finally:
  unchanged=all(sha(ROOT/n)==h for n,h in manifest.items())
  tools={str(x):sha(x) for x in [JAR,BT/'lib/d8.jar',BT/'aapt2',BT/'zipalign',BT/'lib/apksigner.jar',JDK/'bin/java',JDK/'bin/javac',SDK/'platform-tools/adb',SDK/'emulator/emulator']}
  receipt=dict(status=status if unchanged else 'failed-source-changed',observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),sourceRevision=revision,sourceTree=tree,sourceClosureSHA256=hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest(),sourceManifest=manifest,sourceUnchanged=unchanged,workingTreeStatusAtStart=initial,commands=commands,toolSHA256=tools,target=target,native=native,error=error,artifacts={str(x.relative_to(HERE)):sha(x) for suffix in ['*.class','*.dex','*.apk']for x in build.rglob(suffix)},scope='Development consumer slice only. Minimum28 DEX compile is not API28 support. Actual capture requires API36 public high-contrast observation; runtime exercised API37 only. Physical phones, cross-platform design review, signed V2, ordinary engine/JNI atomic join, public bootstrap, font/resources, published FieldLog, stores/customers/operations/GA pending.')
  (out/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n');(out/'artifact-seal.json').write_text(json.dumps({str(x.relative_to(out)):sha(x)for x in sorted(out.rglob('*'))if x.is_file()},indent=2,sort_keys=True)+'\n')
  if not unchanged and error is None:raise RuntimeError('source closure changed during verification')
 print(status)
if __name__=='__main__':main()
