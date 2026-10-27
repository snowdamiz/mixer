#!/usr/bin/env python3
from pathlib import Path
import hashlib,importlib.util,json,os,shutil,signal,subprocess,sys,time
sys.dont_write_bytecode=True
D=Path(__file__).resolve().parent;P=D/'input';R=D.parent
def identity(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
jdk=Path(json.loads((R/'preaccess/tool-context-jdk17/provenance.json').read_bytes())['JDK_home'])
scratch=D/'scratch';scratch.mkdir();classes=scratch/'classes';classes.mkdir();empty=scratch/'empty';empty.mkdir();commands=[]
environment=dict(os.environ)
for k in ('_JAVA_OPTIONS','JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','CLASSPATH','JAVA_OPTS','JDK_JAVAC_OPTIONS'):environment.pop(k,None)
def run(name,argv):
 start=time.monotonic();out=D/(name+'.stdout');err=D/(name+'.stderr')
 with out.open('wb') as stdout,err.open('wb') as stderr:
  child=subprocess.Popen([str(x) for x in argv],cwd=D,stdout=stdout,stderr=stderr,env=environment,start_new_session=True);timeout=False
  try:child.wait(timeout=60)
  except subprocess.TimeoutExpired:timeout=True;os.killpg(child.pid,signal.SIGKILL);child.wait()
 record={'name':name,'argv':[str(x) for x in argv],'exit':child.returncode,'timeout':timeout,'reaped':True,'elapsed_seconds':time.monotonic()-start,'stdout':identity(out),'stderr':identity(err)};commands.append(record);save(D/'commands.json',commands);assert child.returncode==0 and not timeout,record
 return out.read_text()
try:
 sources=sorted((P/'inputs/source').glob('*.java'))+sorted((P/'inputs/host-leaves').rglob('*.java'))+[D/'AdditionalReturnControls.java']
 save(D/'source-and-tools.json',{'sources':[{'path':str(p),**identity(p)} for p in sources],'runner':identity(Path(__file__)),'tools':{name:identity(jdk/name) for name in ('bin/java','bin/javac','bin/javap','lib/modules','lib/server/libjvm.dylib')}})
 run('java-version',[jdk/'bin/java','-version']);run('javac-version',[jdk/'bin/javac','-version'])
 run('compile',[jdk/'bin/javac','--release','17','-Xlint:all','-Werror','-proc:none','-sourcepath',empty,'-classpath',empty,'-d',classes,*sources]);shutil.copytree(classes,D/'classes')
 print(run('additional-return-controls',[jdk/'bin/java','-ea','-Xmx256m','-cp',classes,'dev.mixer.android.AdditionalReturnControls']),end='')
 spec=importlib.util.spec_from_file_location('v3_return_classfile',R/'preaccess/interface-v3/classfile.py');cf=importlib.util.module_from_spec(spec);spec.loader.exec_module(cf)
 reference=json.loads((R/'preaccess/interface-v3/reference-obligations.json').read_bytes())['exact16_source_map'];assert {p.name:identity(p) for p in (P/'inputs/source').glob('*.java')}==reference
 products={p.relative_to(classes).as_posix():identity(p) for p in classes.rglob('*.class') if cf.parse(p.read_bytes())['source_file'] in reference};context=hashlib.sha256(json.dumps({'source_map':reference,'class_map':products},sort_keys=True,separators=(',',':')).encode()).hexdigest();assert len(products)==209 and context=='1b71af17048675296435ca74af284d54f93f2506b9c406517a452a3ce816dbdd'
 leaf=cf.parse((classes/'android/view/inputmethod/BaseInputConnection.class').read_bytes());witnesses=[]
 for name,descriptor in [('getHandler','()Landroid/os/Handler;'),('requestCursorUpdates','(II)Z')]:
  method=next(m for m in leaf['methods'] if m['name']==name and m['descriptor']==descriptor);calls=[i for i in method['instructions'] if i.get('target',{}).get('owner')=='dev/mixer/android/NativeOutcomeProbe' and i['target']['name']=='returned'];assert len(calls)==1;witnesses.append(method)
 save(D/'compiled-audit.json',{'exact_product209_context':context,'class_map':products,'two_actual_emitted_methods':witnesses,'full_matrix_or_native_accepted':False})
finally:
 shutil.rmtree(scratch);save(D/'cleanup.json',{'scratch_removed':not scratch.exists(),'all_children_reaped':all(c['reaped'] for c in commands),'native_UI_capture_or_process_inventory':False})
