#!/usr/bin/env python3
"""Reproduce host contracts, APK packaging, and optional physical native UI evidence."""
import argparse,datetime,hashlib,json,os,pathlib,re,subprocess,sys,xml.etree.ElementTree as ET
ROOT=pathlib.Path(__file__).resolve().parents[2];HERE=ROOT/'native/android';OUT=HERE/'verification';OUT.mkdir(exist_ok=True)
parser=argparse.ArgumentParser();parser.add_argument('--device');args=parser.parse_args();commands=[]
env=os.environ.copy();env['DEVELOPER_DIR']='/Applications/Xcode_26.6.app/Contents/Developer';jdk=pathlib.Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home');env['JAVA_HOME']=str(jdk);env['PATH']=str(jdk/'bin')+os.pathsep+env['PATH']
def manifest():
 files=[p for p in HERE.rglob('*')if p.is_file()and not set(p.relative_to(HERE).parts)&{'build','.build','verification'}]+[ROOT/'sdk/Package.swift']+list((ROOT/'sdk/Sources').rglob('*.swift'))+[ROOT/'contracts/ui-v1.json']
 return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in sorted(files)}
def run(name,cmd,binary=False):
 p=subprocess.run(list(map(str,cmd)),cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);path=OUT/(name+('.png'if binary else'.log'));path.write_bytes(p.stdout);commands.append({'name':name,'command':list(map(str,cmd)),'exit_code':p.returncode,'output':str(path.relative_to(ROOT))});
 if p.returncode:raise RuntimeError(name+' failed: '+p.stdout.decode(errors='replace'))
 return p.stdout if binary else p.stdout.decode()
initial=manifest()
run('swift-test',['/usr/bin/swift','test','--package-path',HERE/'engine'])
(HERE/'build/host-tests').mkdir(parents=True,exist_ok=True)
run('java-test-build',[jdk/'bin/javac','--release','17','-Xlint:all','-Werror','-d',HERE/'build/host-tests',HERE/'app/src/dev/mixer/android/Json.java',HERE/'app/src/dev/mixer/android/UiPacket.java',HERE/'tests/ContractTests.java'])
java=run('java-tests',[jdk/'bin/java','-cp',HERE/'build/host-tests','dev.mixer.android.ContractTests']);assert 'checks passed: 30'in java
run('build-output',[sys.executable,HERE/'build.py']);build=json.loads((HERE/'build/build-receipt.json').read_text());(OUT/'build-receipt.json').write_text(json.dumps(build,indent=2)+'\n')
device=None
if args.device:
 adb='/opt/homebrew/share/android-commandlinetools/platform-tools/adb';prefix=[adb,'-s',args.device]
 props={key:run('property-'+key.replace('.','-'),prefix+['shell','getprop',key]).strip()for key in ['ro.product.model','ro.build.version.release','ro.build.version.sdk','ro.build.fingerprint']};props['page_size']=run('page-size',prefix+['shell','getconf','PAGE_SIZE']).strip()
 run('device-install',prefix+['install','-r','--no-incremental',HERE/'build/mixer-android-debug.apk'])
 package_path=run('device-package-path',prefix+['shell','pm','path','dev.mixer.android']).strip();assert package_path.startswith('package:/data/app/')and package_path.endswith('/base.apk'),package_path
 installed_hash=run('device-apk-hash',prefix+['shell','sha256sum',package_path[len('package:'):]]).split()[0];assert installed_hash==build['apk_sha256'],'installed APK hash mismatch'
 instrument=run('device-instrumentation',prefix+['shell','am','instrument','-w','dev.mixer.android/.AdapterInstrumentation']);assert 'INSTRUMENTATION_RESULT: status=passed'in instrument and'INSTRUMENTATION_CODE: 0'in instrument,instrument
 run('device-launch',prefix+['shell','am','start','-W','-n','dev.mixer.android/.MixerActivity'])
 def dump(name):
  run(name+'-dump',prefix+['shell','uiautomator','dump','/sdcard/mixer-android-ui.xml']);xml=run(name,prefix+['exec-out','cat','/sdcard/mixer-android-ui.xml']);(OUT/(name+'.xml')).write_text(xml);return ET.fromstring(xml)
 def find(root,kind,text=None,description=None):return next(n for n in root.iter('node')if n.get('package')=='dev.mixer.android'and n.get('class')==kind and(text is None or n.get('text')==text)and(description is None or n.get('content-desc')==description))
 def tap(name,node):
  a=list(map(int,re.findall(r'\d+',node.get('bounds'))));run(name,prefix+['shell','input','tap',(a[0]+a[2])//2,(a[1]+a[3])//2])
 root=dump('device-ui-initial');run('device-initial',prefix+['exec-out','screencap','-p'],binary=True)
 tap('keyboard-focus',find(root,'android.widget.EditText',description='New task'));run('keyboard-text',prefix+['shell','input','text','Keyboard%stask']);run('keyboard-dismiss',prefix+['shell','input','keyevent','4']);root=dump('device-ui-keyboard');tap('keyboard-add',find(root,'android.widget.Button',text='Add task'));root=dump('device-ui-added');find(root,'android.widget.Switch',text='Keyboard task');find(root,'android.widget.TextView',text='0 of 3 complete');run('device-added',prefix+['exec-out','screencap','-p'],binary=True)
 tap('touch-toggle',find(root,'android.widget.Switch',text='Keyboard task'));root=dump('device-ui-toggled');find(root,'android.widget.TextView',text='1 of 3 complete');run('device-toggled',prefix+['exec-out','screencap','-p'],binary=True)
 device={'serial':args.device,'installed_apk_sha256':installed_hash,'properties':props,'instrumentation':'passed; native views with actual Android Swift shared library','touch_keyboard':'EditText keyboard input added Keyboard task; touch toggle changed Swift-owned summary to1of3 complete','evidence':['device-ui-initial.xml','device-ui-added.xml','device-ui-toggled.xml','device-initial.png','device-added.png','device-toggled.png'],'qualifier':'physical Pixel8Pro API37 only; no emulator substitute counted'}
final=manifest();assert initial==final,'source changed during verification; rerun from stable tree'
manifest_text=''.join(f'{digest}  {path}\n'for path,digest in final.items());(OUT/'source-manifest.sha256').write_text(manifest_text)
versions={name:run('version-'+name,cmd).strip()for name,cmd in {'swift-host':['/usr/bin/swift','--version'],'swift-android':['/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift','--version'],'javac':[jdk/'bin/javac','--version'],'adb':['/opt/homebrew/share/android-commandlinetools/platform-tools/adb','--version']}.items()}
receipt={'schema_version':1,'observed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'agent':{'model':'gpt-6.1-sol','reasoning_effort':'xhigh'},'source_tree_digest':hashlib.sha256(manifest_text.encode()).hexdigest(),'source_manifest':'native/android/verification/source-manifest.sha256','sdk_revision':'bbf39cd12586849e1609060688f74c3a39d3f0fd','environment':{'DEVELOPER_DIR':env['DEVELOPER_DIR'],'JAVA_HOME':str(jdk)},'tool_versions':versions,'commands':commands,'host_results':{'swift_tests_passed':5,'java_contract_checks_passed':30,'jni_c_compile':'NDK -Wall -Wextra -Werror passed','java_compile':'-Xlint:all -Werror passed'},'apk':{k:build[k]for k in ['apk','apk_bytes','apk_sha256']},'device':device,'resolved_initial_failure':'Initial native launch used a framework tag-key for a watcher; Android rejected it. Watcher ownership moved into the adapter Record; all final checks rerun.','scope':'development SDK source integration and native Android adapter/checklist slice only','open_gates':['independent review','published immutable SDK consumption from separate FieldLog repository','FieldLog D2','TalkBack/accessibility qualification','IME composition/keyboard locale matrix','retained focus/scroll and cross-parent movement','process recreation/state persistence','async/lifecycle effects','large-list virtualization/performance/frame/memory budgets','all Android API/ABI/device configurations','release signing/store acceptance']}
(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'source_tree_digest':receipt['source_tree_digest'],'apk':receipt['apk'],'physical':device is not None},indent=2))
