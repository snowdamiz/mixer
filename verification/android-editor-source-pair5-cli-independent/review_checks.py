#!/usr/bin/env python3
"""Fresh independent entrypoint tests; all project fixtures are owned and reaped."""
import datetime,hashlib,importlib.util,json,os,pathlib,shutil,signal,stat,subprocess,sys,tempfile,time,traceback
R=pathlib.Path(__file__).resolve().parents[2]; O=pathlib.Path(__file__).resolve().parent; P=R/'verification/android-editor-source-pair5-cli-integration'
S=O/'scratch'; S.mkdir(exist_ok=False);E=O/'evidence';E.mkdir(exist_ok=True)
H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=[];assertions=[];errors=[]
def require(value,label):
 assertions.append({'label':label,'passed':bool(value)})
 if not value:raise AssertionError(label)
def run(label,argv,expect=None,code=None,env=None,cwd=None,timeout=10):
 argv=list(map(str,argv));t=time.monotonic();timed=False
 with (E/(label+'.log')).open('wb') as out:
  proc=subprocess.Popen(argv,cwd=cwd or R,env=env or os.environ.copy(),stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
  try:proc.wait(timeout=timeout)
  except subprocess.TimeoutExpired:
   timed=True;os.killpg(proc.pid,signal.SIGTERM)
   try:proc.wait(timeout=2)
   except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=2)
 exe=pathlib.Path(argv[0]);exe=exe if exe.is_absolute() else pathlib.Path(shutil.which(argv[0],path=(env or os.environ).get('PATH')))
 output=(E/(label+'.log')).read_text(errors='replace')
 row={'label':label,'argv':argv,'cwd':str(cwd or R),'returncode':proc.returncode,'timed_out':timed,'elapsed_seconds':time.monotonic()-t,'timeout_seconds':timeout,'owned_child_reaped':True,'executable':str(exe),'executable_sha256':H(exe.resolve()),'output_sha256':H(E/(label+'.log')),'output_bytes':(E/(label+'.log')).stat().st_size,'expected':expect,'expected_code':code}
 rows.append(row)
 require(not timed,label+' bounded')
 if code is not None:require(proc.returncode==code,label+' exit')
 if expect is not None:require(expect in output,label+' diagnostic')
 return output
skip={'.build','.git','.swiftpm','node_modules','.gradle','.mixer','target','.DS_Store'}
def tree(root):
 files=[]
 for base,dirs,names in os.walk(root,followlinks=False):
  dirs[:]=[d for d in dirs if d not in skip]
  for name in names:
   p=pathlib.Path(base)/name
   if name in skip or name=='.env' or (name.startswith('.env.') and name!='.env.example') or p.suffix.lower() in {'.pem','.key','.p12','.pfx','.mobileprovision','.keystore','.jks'}:continue
   require(not p.is_symlink(),'fixture hash ordinary');files.append(p)
 return hashlib.sha256(''.join(p.relative_to(root).as_posix()+'\0'+H(p)+'\n' for p in sorted(files)).encode()).hexdigest()
def lock(root):
 j=json.loads((root/'mixer.lock').read_text());j['sdkDigest']=tree(root/'Generated/MixerSDK');j['android']['adapterDigest']=tree(root/'Generated/MixerAndroid');(root/'mixer.lock').write_text(json.dumps(j));return j
def clone(name):
 p=S/name;shutil.copytree(P/'consumers/PairFiveConsumer',p);return p
def clean(*paths):
 for p in paths:
  if p.exists():shutil.rmtree(p)
def load(p,n):
 spec=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
profile=json.loads((P/'inputs/profile5.json').read_text());raw=P/'source/cli/Sources/MixerBuild/Resources/android-build.py';template=raw.read_text();marker='__MIXER_ANDROID_SOURCE_PROFILE_HEX__'
debug=P/'artifacts/cli/mixer-debug';release=P/'artifacts/cli/mixer-release';old=P/'artifacts/cli/mixer-old4-debug'
tools=S/'tools';tools.mkdir();sentinel=S/'TOOL-REACHED';env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1';env['PATH']=str(tools)+os.pathsep+env['PATH'];env['MIXER_SWIFT']=str(tools/'swift')
for name in ['swift','python3']:
 f=tools/name;f.write_text('#!/bin/sh\nprintf invoked >> "'+str(sentinel)+'"\nexit 93\n');f.chmod(0o755)
def no_output(root,*outputs):
 require(not sentinel.exists(),'tool sentinel unreached');require(not (root/'.mixer').exists(),'no .mixer output')
 for p in outputs:require(not p.exists(),'no created/export output')
 require(not any(p.name.startswith('.mixer-create-') for p in S.iterdir()),'no create staging residue')
def copied_checks(label,root,expected='android.sdk-compatibility',direct='source compatibility rejected'):
 exported=S/(label+'-export')
 run(label+'-debug-host',[debug,'build','--directory',root,'--platform','host'],expected,1,env)
 run(label+'-release-export',[release,'export',exported,'--directory',root],expected,1,env)
 run(label+'-direct',[sys.executable,'-B',root/'Generated/MixerAndroid/android-build.py','build',root],direct,1,env)
 no_output(root,exported)
def mutate(p,kind):
 b=p.read_bytes();p.unlink()
 if kind=='same-size':p.write_bytes(b' '*len(b))
 elif kind=='append':p.write_bytes(b+b' ')
 elif kind=='rename':p.with_name(p.name+'.renamed').write_bytes(b)
 elif kind=='case':p.with_name(p.name.lower()).write_bytes(b)
 elif kind=='symlink':p.symlink_to(p.parent/'missing')
 elif kind=='fifo':os.mkfifo(p)
 elif kind=='directory':p.mkdir()
 elif kind=='extra':p.write_bytes(b);p.with_name('unexpected.txt').write_bytes(b'')
 elif kind=='oversized':p.write_bytes(b' '*2000000)
try:
 run('python-version',[sys.executable,'--version'],code=0)
 # Exact copied tests: no producer helper or one-shot runner is imported.
 copied=S/'source';shutil.copytree(P/'source',copied)
 testenv=os.environ.copy();testenv['PYTHONDONTWRITEBYTECODE']='1'
 run('python33',[sys.executable,'-B','-m','unittest','discover','-s',str(copied/'cli/build-tests'),'-p','test_android_*.py','-v'],'Ran 33 tests',0,testenv,timeout=56)
 require('OK' in (E/'python33.log').read_text(),'all original Python33 pass')
 # Positive relocated export verifies admission without tool discovery.
 root=clone('positive');base_lock=json.loads((root/'mixer.lock').read_text());require(tree(root/'Generated/MixerSDK')==base_lock['sdkDigest'],'independent SDK generic hash matches');require(tree(root/'Generated/MixerAndroid')==base_lock['android']['adapterDigest'],'independent adapter generic hash matches')
 for binary,tag in [(debug,'debug'),(release,'release')]:
  output=S/('positive-'+tag+'-export');run('positive-'+tag+'-export',[binary,'export',output,'--directory',root],code=0,env=testenv)
  for relative,v in profile['adapter_files'].items():require(H(output/'Generated/MixerAndroid'/relative)==v['sha256'],'export selected adapter '+tag+' '+relative)
  for relative,v in profile['sdk_files'].items():require(H(output/'Generated/MixerSDK'/relative)==v['sha256'],'export selected SDK '+tag+' '+relative)
  require(len(list((output/'Generated/MixerAndroid/app/src').rglob('*.java')))==18,'positive export Java18 '+tag)
  clean(output)
 clean(root)
 names=['NativeEditorConnectionV2.java','NativeAppearanceViewsV2.java','NativeRenderer.java','NativeCoordinatorV2.java']; kinds=['same-size','append','remove','rename','case','symlink','fifo','directory','extra','oversized']
 for i,name in enumerate(names):
  for kind in kinds:
   label=str(i)+'-'+kind;root=clone(label);adapter=S/(label+'-adapter');shutil.copytree(P/'source/native/android',adapter)
   mutate(root/'Generated/MixerAndroid/app/src/dev/mixer/android'/name,kind);mutate(adapter/'app/src/dev/mixer/android'/name,kind)
   if kind not in ['symlink','fifo','directory']:lock(root)
   (root/'Generated/MixerSDK/GenericHasherSentinel').symlink_to(S/'missing')
   copied_checks(label,root)
   created=S/(label+'-created');run(label+'-create',[debug,'create','Created','--directory',created,'--platform','android','--sdk-path',P/'source/sdk','--android-adapter-path',adapter],'create.android-sdk-compatibility',1,env)
   no_output(root,created);clean(root,adapter)
  print('completed source matrix '+name,flush=True)
 # Optional canonical-only files are forbidden on all copied paths.
 optional=['AppearanceDescriptorV1.java','AppearanceResolutionV1.java','AdapterInstrumentation.java']
 for i,name in enumerate(optional):
  root=clone('optional-'+str(i));shutil.copyfile(P/'source/native/android/app/src/dev/mixer/android'/name,root/'Generated/MixerAndroid/app/src/dev/mixer/android'/name);lock(root);(root/'Generated/MixerSDK/GenericHasherSentinel').symlink_to(S/'missing');copied_checks('optional-'+str(i),root);clean(root)
 # Combined hostile observations demonstrate complete layout precedes content.
 root=clone('phase');a=root/'Generated/MixerAndroid/app/src/dev/mixer/android';(a/'NativeEditorConnectionV2.java').write_bytes(b' '*2000000);sdkfile=root/'Generated/MixerSDK/Sources/MixerCore/Lifecycle.swift';sdkfile.write_bytes(b' '*sdkfile.stat().st_size);lock(root)
 out=run('phase-cli',[debug,'build','--directory',root,'--platform','android'],'Expected ordinary pinned-size file app/src/dev/mixer/android/NativeEditorConnectionV2.java',1,env)
 run('phase-direct',[sys.executable,'-B',root/'Generated/MixerAndroid/android-build.py','build',root],'NativeEditorConnectionV2.java: expected ordinary pinned-size file',1,env);no_output(root);clean(root)
 # A .4 driver plus recomputed adapter lock must be rejected by new CLI before tools.
 root=clone('stale-driver');driver=root/'Generated/MixerAndroid/android-build.py';oldprofile=json.loads((P/'inputs/profile4.json').read_text());driver.write_text((P/'inputs/old4-android-build.py').read_text().replace(marker,json.dumps(oldprofile).encode().hex()));lock(root);(root/'Generated/MixerSDK/GenericHasherSentinel').symlink_to(S/'missing')
 for platform in ['host','ios','android']:run('stale-driver-'+platform,[debug,'build','--directory',root,'--platform',platform],'android.sdk-compatibility',1,env)
 run('stale-driver-release',[release,'export',S/'stale-export','--directory',root],'android.sdk-compatibility',1,env)
 run('stale-driver-direct',[sys.executable,'-B',driver,'build',root],'android.sdk-profile-mismatch',1,env);no_output(root,S/'stale-export');clean(root)
 # Recompute locks cannot make old4/new5 and prior unaccepted mixtures authoritative.
 root=clone('old-lock');j=json.loads((root/'mixer.lock').read_text());j['android']['profile']['id']='mixer.android-source-pair.4';(root/'mixer.lock').write_text(json.dumps(j));copied_checks('old-lock',root,'android.sdk-profile-mismatch','android.sdk-profile-mismatch');clean(root)
 for name in ['NativeAppearanceViewsV2.java','NativeRenderer.java']:
  root=clone('unaccepted-'+name);shutil.copyfile(P/('inputs/unaccepted-'+name),root/'Generated/MixerAndroid/app/src/dev/mixer/android'/name);lock(root);(root/'Generated/MixerSDK/GenericHasherSentinel').symlink_to(S/'missing');copied_checks('unaccepted-'+name,root);clean(root)
 for binary,adapter,tag in [(old,P/'source/native/android','oldCLI-newSources'),(debug,P/'inputs/old-adapter','newCLI-oldSources')]:
  created=S/(tag+'-created');run(tag,[binary,'create','Created','--directory',created,'--platform','android','--sdk-path',P/'source/sdk','--android-adapter-path',adapter],'create.android-sdk-compatibility',1,env);require(not created.exists(),tag+' no output');require(not sentinel.exists(),tag+' no tools')
 # Raw marker decode remains build-only; replacing probe stops inspect before tools.
 rawmodule=load(copied/'cli/Sources/MixerBuild/Resources/android-build.py','independent_raw');rawmodule.probe=lambda *args: (_ for _ in ()).throw(RuntimeError('RAW-INSPECT-SENTINEL'))
 try:rawmodule.inspect();raise AssertionError('raw inspect did not reach tool boundary')
 except RuntimeError as e:require(str(e)=='RAW-INSPECT-SENTINEL','raw inspect independent of marker')
 root=clone('raw');run('raw-build-marker',[sys.executable,'-B',raw,'build',root],'not rendered or supported',1,env);no_output(root);clean(root)
except Exception as error:
 errors.append({'error':str(error),'traceback':traceback.format_exc()});print(traceback.format_exc(),flush=True)
finally:
 shutil.rmtree(S)
 report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,*sys.argv],'python_version':sys.version,'source_projection':'6ba31109183443ab62ef8ae9e36ae3e968ec3da383c67c4cc93aa6a2a9a5131a','candidate_seal_sha256':H(P/'seal.json'),'rows':rows,'assertions':assertions,'errors':errors,'passed':not errors,'cleanup':{'scratch_removed':not S.exists(),'all_owned_children_reaped':all(x['owned_child_reaped'] for x in rows),'native_UI_capture_process_inventory_started':False,'python_suites_temporary_fixtures':'Original suite-owned /tmp fixtures cleaned by unittest addCleanup; no native processes.'}}
 (O/'behavior.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'passed':not errors,'commands':len(rows),'assertions':len(assertions),'errors':errors,'cleanup':report['cleanup']},indent=2))
sys.exit(bool(errors))
