#!/usr/bin/env python3
"""Reproducible exact-source, bounded Java/SDK compilation plus unmodified host controls."""
from pathlib import Path
import os,sys,subprocess,hashlib,json,shutil,tempfile,datetime,time,signal
D=Path(__file__).resolve().parent;R=D.parents[1];C=R/'verification/android-editor-preservation-membership-correction';P=R/'verification/android-editor-integration-protocol'
def ident(p):b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+'\n')
def verify_seal(folder,name,expected):
 p=folder/name;assert ident(p)['sha256']==expected,(p,'seal mismatch');j=json.loads(p.read_bytes());total=0
 for m in j['members']:
  f=folder/m['path'];assert f.is_file() and not f.is_symlink() and ident(f)=={'bytes':m['bytes'],'sha256':m['sha256']},f;total+=m['bytes']
 return {'seal':str(p.relative_to(R)),**ident(p),'members':len(j['members']),'member_bytes':total}
def prepare():
 assert not (D/'inputs').exists(),'closed copied inputs already present'
 seals=[verify_seal(C,'seal.json','620bfefe8cde4b63c2101db76af991fcc1933276f9c1e8d8d1aa1e3db8f0bf0e'),verify_seal(R/'verification/android-editor-preservation-membership-independent/actual-review','review-seal.json','8d51b0e6d04b152621e9e6f9ad3b6c46b3301853ed5d0c545fd4781a66c36c6d'),verify_seal(P,'seal.json','2338ce170833c7a33d797d46a6d51d50e3b24398ed05b2b8b2129dafb35eb89f')]
 acceptance=R/'verification/android-editor-boundary-root-review/preservation-membership-acceptance.json';assert ident(acceptance)['sha256']=='2d7d9515ef7a6dd4ceeb7c5d61b951d06b4720c1fffdfd5988938d5e47b34e75'
 for folder in ('source','host-leaves','tests','cross-source'):shutil.copytree(C/folder,D/'inputs/accepted'/folder)
 shutil.copy2(C/'runs/host-2/commands.json',D/'selected-original-command-roster.json')
 for name in ('descriptor.json','source-verification.json'):shutil.copy2(C/name,D/'inputs/accepted'/name)
 frozen=['compiled-boundary-qualification.md','integration-contract.md','test-migration.md','source-lists.json','family-migration.json']
 for name in frozen:shutil.copy2(P/name,D/'inputs/protocol'/name) if (D/'inputs/protocol').exists() else ((D/'inputs/protocol').mkdir(parents=True),shutil.copy2(P/name,D/'inputs/protocol'/name))
 for name in ['barrier-map.json','NativeOwnerV2ConcreteHostTests.java']:
  f=P/('inputs/repo/verification/android-private-owner-integration-implementation/'+name if name.endswith('.json') else 'inputs/repo/native/android/tests/'+name);shutil.copy2(f,D/'inputs/protocol'/name)
 src=json.loads((C/'source-verification.json').read_bytes())['source_map'];assert src=={p.name:ident(p) for p in sorted((D/'inputs/accepted/source').glob('*.java'))}
 roster=json.loads((P/'source-lists.json').read_bytes())['closures']['B-concrete-renderer-views']['proposed_explicit_product_sources'];assert {Path(v).name for v in roster}==set(src)
 probe=D/'inputs/accepted/host-leaves/dev/mixer/android/ConcreteHostProbe.java';body=probe.read_text();assert body.count('case "NativeOwnerV2",')==1
 amended=body.replace('case "NativeOwnerV2",','case "NativeEditorConnectionV2","NativeOwnerV2",').replace('public static BiConsumer<String,String> hook;','public static BiConsumer<String,String> hook;\n    public static java.util.function.Consumer<Event> auditSink;').replace('history.add(new Event(method,phase,receiver,sites));String key=method+"/"+phase;','Event event=new Event(method,phase,receiver,sites);history.add(event);\n        if(auditSink!=null)auditSink.accept(event);String key=method+"/"+phase;')
 derivative=D/'inputs/instrumentation/ConcreteHostProbe.java';derivative.parent.mkdir();derivative.write_text(amended)
 save(D/'input-custody.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'verified_seals':seals,'root_acceptance':{'path':str(acceptance.relative_to(R)),**ident(acceptance)},'product_tree':json.loads((C/'source-verification.json').read_bytes())['product_tree'],'exact16_roster_matches_protocol_B':True,'original_probe':ident(probe),'distinct_probe_derivative':ident(derivative),'derivative_scope':'Adds only direct-editor frame allowlist plus passive sink retained across resets; product source and original test bodies/assertions unchanged','native_UI_capture_or_process_inventory':False})
 save(D/'input-manifest.json',{str(p.relative_to(D/'inputs')):ident(p) for p in sorted((D/'inputs').rglob('*')) if p.is_file()})

def execute(mode):
 runs=D/'runs';runs.mkdir(exist_ok=True);idx=1
 while (runs/f'{mode}-{idx}').exists():idx+=1
 E=runs/f'{mode}-{idx}';E.mkdir();commands=[];status='failed';env=dict(os.environ)
 for k in ('_JAVA_OPTIONS','JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','CLASSPATH','JAVA_OPTS','JDK_JAVAC_OPTIONS'):env.pop(k,None)
 jdk=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home');sdk=Path('/opt/homebrew/share/android-commandlinetools');jar=sdk/'platforms/android-37.0/android.jar';d8=sdk/'build-tools/37.0.0/d8';env['JAVA_HOME']=str(jdk);env['PATH']=str(jdk/'bin')+os.pathsep+env.get('PATH','')
 scratch=Path(tempfile.mkdtemp(prefix='owned-qualification-',dir=E));temp=scratch/'tmp';temp.mkdir();env.update({'TMPDIR':str(temp),'TMP':str(temp),'TEMP':str(temp)});classes=scratch/'classes';classes.mkdir();empty=scratch/'empty';empty.mkdir()
 def run(name,argv,allow_failure=False):
  start=time.monotonic()
  with (E/(name+'.stdout')).open('wb') as out,(E/(name+'.stderr')).open('wb') as err:
   p=subprocess.Popen([str(a) for a in argv],cwd=R,env=env,stdout=out,stderr=err,start_new_session=True);timedout=False
   try:p.wait(timeout=60)
   except subprocess.TimeoutExpired:timedout=True;os.killpg(p.pid,signal.SIGKILL);p.wait()
  commands.append({'name':name,'argv':[str(a) for a in argv],'exit':p.returncode,'timeout':timedout,'elapsed_seconds':time.monotonic()-start,'stdout':ident(E/(name+'.stdout')),'stderr':ident(E/(name+'.stderr')),'reaped':True});save(E/'commands.json',commands)
  print(name+': exit'+str(p.returncode),flush=True)
  if (p.returncode or timedout) and not allow_failure:raise RuntimeError(name+' failed: '+str(E/(name+'.stderr')))
  return p.returncode
 try:
  manifest=json.loads((D/'input-manifest.json').read_bytes());assert manifest=={str(p.relative_to(D/'inputs')):ident(p) for p in sorted((D/'inputs').rglob('*')) if p.is_file()}
  shutil.copy2(D/'run.py',E/'runner.py')
  save(E/'source-freeze.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'input_manifest':ident(D/'input-manifest.json'),'runner':ident(D/'run.py'),'trace_runner':ident(D/'TraceRunner.java'),'explicit_frozen_before_compile':True})
  files=sorted((D/'inputs/accepted/source').glob('*.java'))
  if mode=='cross':files.append(D/'inputs/accepted/cross-source/NativeBridge.java')
  else:
   files += [p for p in sorted((D/'inputs/accepted/host-leaves').rglob('*.java')) if p.name!='ConcreteHostProbe.java']
   files += sorted((D/'inputs/accepted/tests').glob('*.java'))+[D/'inputs/instrumentation/ConcreteHostProbe.java',D/'TraceRunner.java',D/'inputs/protocol/NativeOwnerV2ConcreteHostTests.java']
  save(E/'explicit-source-list.json',[{'path':str(p.relative_to(R)),**ident(p)} for p in files])
  run('javac-version',[jdk/'bin/javac','-version']);run('java-version',[jdk/'bin/java','-version'])
  run('compile',[jdk/'bin/javac','-J-Djava.io.tmpdir='+str(temp),'--release','17','-g','-Xlint:all','-Werror','-proc:none','-classpath',jar if mode=='cross' else empty,'-sourcepath',empty,'-d',classes,*files])
  shutil.copytree(classes,E/'classes');save(E/'class-map.json',{str(p.relative_to(classes)):ident(p) for p in sorted(classes.rglob('*.class'))})
  if mode=='cross':
   run('d8-version',[d8,'--version']);run('sdk-descriptors',[jdk/'bin/javap','-p','-s','-classpath',jar,'android.view.inputmethod.InputConnection']);dex=scratch/'dex';dex.mkdir();run('dex',[d8,'--min-api','28','--lib',jar,'--output',dex,*sorted(classes.rglob('*.class'))]);shutil.copytree(dex,E/'dex')
  else:
   original=json.loads((D/'selected-original-command-roster.json').read_bytes());selected=[]
   for c in original:
    args=c['argv']
    if '-cp' in args and (c['name'] in ('producer-52','descriptors-38') or c['name'].startswith(('prepared-','independent-','focus-','actual-','audit-','completion-','membership-'))):
     cp=args.index('-cp');main=args[cp+2];tail=args[cp+3:];tail=[str(D/'inputs/accepted/descriptor.json') if x.endswith('/inputs/descriptor.json') else x for x in tail];selected.append((c['name'],main,tail))
   selected.append(('v1-original-five','dev.mixer.android.NativeOwnerV2ConcreteHostTests',['--v1-original']))
   for name,main,tail in selected:run(name,[jdk/'bin/java','-Djava.io.tmpdir='+str(temp),'-ea','-Xmx512m','-cp',classes,'dev.mixer.android.TraceRunner',E/(name+'.events.jsonl'),main,*tail])
  targetnames=[p.relative_to(classes).as_posix()[:-6].replace('/','.') for p in classes.glob('dev/mixer/android/*.class') if p.name.split('$')[0][:-6] in {p.stem for p in (D/'inputs/accepted/source').glob('*.java')}] # full inventory is independently read from classfiles
  run('javap-selected',[jdk/'bin/javap','-p','-c','-s','-l','-classpath',classes,'dev.mixer.android.NativeRenderer','dev.mixer.android.NativeAppearanceViewsV2$NativeField','dev.mixer.android.NativeEditorConnectionV2$Base','dev.mixer.android.NativeEditorConnectionV2$Api31','dev.mixer.android.NativeEditorConnectionV2$Api33','dev.mixer.android.NativeEditorConnectionV2$Api34'])
  assert manifest=={str(p.relative_to(D/'inputs')):ident(p) for p in sorted((D/'inputs').rglob('*')) if p.is_file()};status='passed-'+mode+'-scope'
 finally:
  shutil.rmtree(scratch);save(E/'receipt.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':status,'mode':mode,'compiler_runtime':'actual OpenJDK25 binary, --release17 output; not JDK17 execution','commands':len(commands),'source_freeze':ident(E/'source-freeze.json') if (E/'source-freeze.json').exists() else None,'tools':{str(p):ident(p.resolve()) for p in (jdk/'bin/javac',jdk/'bin/java',jdk/'bin/javap',jdk/'lib/modules',jdk/'lib/server/libjvm.dylib',jar,d8,d8.parent/'lib/d8.jar')},'cleanup':{'scratch_removed':not scratch.exists(),'all_children_reaped':all(c['reaped'] for c in commands),'native_UI_capture_or_process_inventory':False}})
 print(status,E.name,flush=True)
if __name__=='__main__':
 if sys.argv[1]=='prepare':prepare()
 else:execute(sys.argv[1])
