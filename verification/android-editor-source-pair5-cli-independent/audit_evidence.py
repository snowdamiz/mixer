#!/usr/bin/env python3
"""Independent receipt/APK audit plus SDK37 javac/D8 and offline ELF reinspection."""
import datetime,hashlib,json,os,pathlib,re,shutil,signal,subprocess,sys,time,zipfile
R=pathlib.Path(__file__).resolve().parents[2];O=pathlib.Path(__file__).resolve().parent;P=R/'verification/android-editor-source-pair5-cli-integration';E=O/'evidence';E.mkdir(exist_ok=True)
H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();checks=[];rows=[];errors=[]
def ck(ok,label):
 checks.append({'label':label,'passed':bool(ok)})
 if not ok:raise AssertionError(label)
def run(label,args,env=None,timeout=56):
 args=list(map(str,args));t=time.monotonic();timed=False;f=E/(label+'.log')
 with f.open('wb') as log:
  p=subprocess.Popen(args,env=env or os.environ.copy(),stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  try:p.wait(timeout=timeout)
  except subprocess.TimeoutExpired:
   timed=True;os.killpg(p.pid,signal.SIGTERM)
   try:p.wait(timeout=2)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=2)
 exe=pathlib.Path(args[0]);exe=exe if exe.is_absolute() else pathlib.Path(shutil.which(args[0]));rows.append({'label':label,'argv':args,'cwd':str(R),'returncode':p.returncode,'timed_out':timed,'elapsed_seconds':time.monotonic()-t,'timeout_seconds':timeout,'executable':str(exe),'executable_sha256':H(exe.resolve()),'owned_child_reaped':True,'output_sha256':H(f),'output_bytes':f.stat().st_size,'source_projection':'6ba31109183443ab62ef8ae9e36ae3e968ec3da383c67c4cc93aa6a2a9a5131a'})
 ck(p.returncode==0 and not timed,label+' exit');return f.read_text(errors='replace')
try:
 idx=json.loads((P/'command-index.json').read_text());required=idx['required_final_rows'];by={e['label']:e for e in idx['commands']}
 for label in required:
  r=json.loads((P/by[label]['receipt']).read_text());log=P/'evidence'/(label+'.log');ck(r['returncode']==0 and not r['timed_out'] and r['owned_child_reaped'],'producer final '+label);ck(H(log)==r['output_sha256'] and log.stat().st_size==r['output_bytes'],'exact log '+label)
 for label in ['cli-debug-tests-driver-guard','cli-release-original-context-final']:
  r=json.loads((P/'evidence'/(label+'.json')).read_text());log=(P/'evidence'/(label+'.log')).read_text();ck(r['source_tree_sha256']=='6ba31109183443ab62ef8ae9e36ae3e968ec3da383c67c4cc93aa6a2a9a5131a','final42 source '+label);ck('run with 42 tests' in log and 'failed' not in log.split('Test run started.')[-1].lower(),'final42 count '+label)
 r=json.loads((P/'evidence/cli-release-original-context-final.json').read_text());ck(r['deadline_seconds']==180 and r['execution_timeout_seconds']==176,'cold external command budget only');ck(H(P/'inputs/integration-cold-build-command-budget-amendment.md')=='8cef0df4db8ddaf9b9fefdc5b5a1b29298b3107f0243cb22867cd335e822f266','selected cold command amendment')
 apk=P/'artifacts/unsigned-consumer/PairFiveConsumer-unsigned.apk';receipt=json.loads((P/'artifacts/unsigned-consumer/build-receipt.json').read_text());ck(H(apk)==receipt['apk_sha256']=='b52e60b07583ba095eab2c211a87fb64b87aa93641cd14cd74cfb8d73f2b1fe3','APK exact identity');ck(apk.stat().st_size==receipt['apk_bytes']==28094174,'APK bytes');ck(len(receipt['commands'])==47 and all(c['exit_code']==0 for c in receipt['commands']),'47 driver commands');ck(receipt['source_tree_sha256']==receipt['source_tree_after_sha256'],'producer before-after equality')
 with zipfile.ZipFile(apk) as archive:
  names=archive.namelist();ck(len(names)==len(set(names))==22,'closed22 archive');actual={n:hashlib.sha256(archive.read(n)).hexdigest() for n in sorted(names)};ck(actual==receipt['apk_entries'],'all APK member hashes');ck(not any(n.startswith('META-INF/') for n in names),'unsigned archive');ck(actual['assets/MixerAppearanceV2/descriptor.json']=='1aeab75c457c21e5c801ab8b446490971d510021c945d0841252360becd8ead3','exact descriptor archive')
 profile=json.loads((P/'inputs/profile5.json').read_text())
 for name in ['PairFiveConsumer','FreshConsumer','RelocatedConsumer','ExportedConsumer','RoundTripConsumer']:
  c=P/'consumers'/name
  if not c.exists():continue
  for kind,root in [('sdk',c/'Generated/MixerSDK'),('adapter',c/'Generated/MixerAndroid')]:
   for k,v in profile[kind+'_files'].items():ck(H(root/k)==v['sha256'] and (root/k).stat().st_size==v['bytes'],'consumer '+name+' '+k)
  ck(len(list((c/'Generated/MixerAndroid/app/src').rglob('*.java')))==18,'consumer product18 '+name)
 tools=receipt['toolchain']['tools'];java_home=pathlib.Path(tools['javac']['path']).parent.parent;env=os.environ.copy();env['JAVA_HOME']=str(java_home);env['PATH']=str(java_home/'bin')+os.pathsep+env['PATH']
 for name in ['javac','java','d8','readelf','nm']:
  ck(H(pathlib.Path(tools[name]['path']).resolve())==tools[name]['sha256'],'exact installed tool '+name)
 versions={}
 for name,arg in [('javac','--version'),('java','--version'),('readelf','--version'),('nm','--version')]:versions[name]=run('independent-'+name+'-version',[tools[name]['path'],arg],env)
 jar=pathlib.Path('/opt/homebrew/share/android-commandlinetools/platforms/android-37.0/android.jar');support=json.loads((P/'compiler-support-identities.json').read_text())['identities'];jid=next(x for x in support if x['path'].endswith('/android.jar'));ck(H(jar)==jid['sha256'],'pinned SDK37 jar')
 out=O/'compiled';out.mkdir(exist_ok=False);classes=out/'classes';classes.mkdir();dex=out/'dex';dex.mkdir()
 sources=[P/'consumers/PairFiveConsumer/Generated/MixerAndroid'/k for k in sorted(profile['adapter_files']) if k.endswith('.java')];ck(len(sources)==18,'explicit product18 source set')
 run('independent-product18-sdk37-javac',[tools['javac']['path'],'--release','17','-Xlint:all','-Werror','-proc:none','-sourcepath','','-classpath',jar,'-d',classes,*sources],env)
 emitted=sorted(classes.rglob('*.class'));ck(len(emitted)==212,'emitted212 exact product classes');ck(not any(x.stem.startswith(('AdapterInstrumentation','AppearanceDescriptorV1','AppearanceResolutionV1')) for x in emitted),'no canonical-only classes')
 run('independent-product18-min28-D8',[tools['d8']['path'],'--min-api','28','--lib',jar,'--output',dex,*emitted],env);ck((dex/'classes.dex').is_file(),'D8 classes.dex')
 for context in ['generated','relocated']:
  for config in ['debug','release']:
   for name in ['libAppAndroid.so','libmixer_android_jni.so']:
    lib=P/'artifacts'/context/config/name
    if context=='generated' and name=='libmixer_android_jni.so':lib=P/'artifacts'/config/name
    prefix='independent-'+context+'-'+config+'-'+name
    head=run(prefix+'-header',[tools['readelf']['path'],'-h',lib],env);ck('ELF64' in head and 'AArch64' in head,'ELF64 AArch64 '+prefix)
    dynamic=run(prefix+'-dynamic',[tools['readelf']['path'],'-d',lib],env);needed=re.findall(r'\(NEEDED\).*\[([^\]]+)\]',dynamic);ck(bool(needed),'ELF dependencies '+prefix)
    symbols=run(prefix+'-symbols',[tools['nm']['path'],'-D','--defined-only',lib],env)
    required_symbols=(['mixer_android_create','mixer_android_exchange','mixer_android_destroy','mixer_android_prepare_v2','mixer_android_commit_v2','mixer_android_abort_v2'] if name=='libAppAndroid.so' else ['Java_dev_mixer_android_NativeBridge_create','Java_dev_mixer_android_NativeBridge_exchange','Java_dev_mixer_android_NativeBridge_destroy'])
    ck(all(x in symbols for x in required_symbols),'required ABI symbols '+prefix)
except Exception as error:
 import traceback;errors.append({'error':str(error),'traceback':traceback.format_exc()});print(traceback.format_exc())
report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,*sys.argv],'python_version':sys.version,'source_projection':'6ba31109183443ab62ef8ae9e36ae3e968ec3da383c67c4cc93aa6a2a9a5131a','candidate_seal_sha256':H(P/'seal.json'),'checks':checks,'commands':rows,'errors':errors,'passed':not errors,'scope':'Offline retained receipt/APK audit; fresh Java18 compile and D8, eight retained ELF inspections. No repeated Swift crosscompile/full packaging, no native execution/UI/capture/process inventory.'}
(O/'evidence-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'passed':not errors,'checks':len(checks),'commands':len(rows),'errors':errors},indent=2));sys.exit(bool(errors))
