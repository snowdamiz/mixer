#!/usr/bin/env python3
from pathlib import Path
import hashlib,importlib.util,json,os,signal,shutil,subprocess,sys,time
sys.dont_write_bytecode=True
D=Path(__file__).resolve().parent;R=D.parent;P=R/'derivative-v3-review/input/inputs';JDK=Path(json.loads((R/'preaccess/tool-context-jdk17/provenance.json').read_bytes())['JDK_home'])
def identity(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
runroot=D/'run-1';runroot.mkdir();scratch=runroot/'scratch';scratch.mkdir();classes=scratch/'classes';classes.mkdir();empty=scratch/'empty';empty.mkdir();commands=[]
environment=dict(os.environ)
for k in ('_JAVA_OPTIONS','JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','CLASSPATH','JAVA_OPTS','JDK_JAVAC_OPTIONS'):environment.pop(k,None)
def run(name,argv):
 start=time.monotonic();out=runroot/(name+'.stdout');err=runroot/(name+'.stderr')
 with out.open('wb') as stdout,err.open('wb') as stderr:
  child=subprocess.Popen([str(x) for x in argv],cwd=D,stdout=stdout,stderr=stderr,env=environment,start_new_session=True);timeout=False
  try:child.wait(timeout=60)
  except subprocess.TimeoutExpired:timeout=True;os.killpg(child.pid,signal.SIGKILL);child.wait()
 row={'name':name,'argv':[str(x) for x in argv],'exit':child.returncode,'timeout':timeout,'reaped':True,'elapsed':time.monotonic()-start,'stdout':identity(out),'stderr':identity(err)};commands.append(row);save(runroot/'commands.json',commands);print(name,child.returncode,flush=True);assert child.returncode==0 and not timeout,row
try:
 sources=sorted((P/'source').glob('*.java'))+sorted((P/'host-leaves').rglob('*.java'))+[D/'inputs/NativeOwnerV2ConcreteHostTests.java',D/'V1PositiveWitness.java']
 save(runroot/'source-and-tools.json',{'sources':[{'path':str(p),**identity(p)} for p in sources],'runner':identity(Path(__file__)),'tools':{name:identity(JDK/name) for name in ('bin/java','bin/javac','bin/javap','lib/modules','lib/server/libjvm.dylib')}})
 run('java-version',[JDK/'bin/java','-version']);run('javac-version',[JDK/'bin/javac','-version'])
 run('compile',[JDK/'bin/javac','--release','17','-Xlint:all','-Werror','-proc:none','-sourcepath',empty,'-classpath',empty,'-d',classes,*sources]);shutil.copytree(classes,runroot/'classes')
 run('unchanged-original-v1-assertions',[JDK/'bin/java','-ea','-Xmx256m','-cp',classes,'dev.mixer.android.NativeOwnerV2ConcreteHostTests',D/'inputs/descriptor.json','unused','--section','v1'])
 run('exact-five-v1-witness',[JDK/'bin/java','-ea','-Xmx256m','-cp',classes,'dev.mixer.android.V1PositiveWitness',runroot/'actual-five-v1.json'])
 spec=importlib.util.spec_from_file_location('v1_actual_classfile',R/'preaccess/interface-v3/classfile.py');cf=importlib.util.module_from_spec(spec);spec.loader.exec_module(cf)
 reference=json.loads((R/'preaccess/interface-v3/reference-obligations.json').read_bytes())['exact16_source_map'];assert {p.name:identity(p) for p in (P/'source').glob('*.java')}==reference
 products={p.relative_to(classes).as_posix():identity(p) for p in classes.rglob('*.class') if cf.parse(p.read_bytes())['source_file'] in reference};context=hashlib.sha256(json.dumps({'source_map':reference,'class_map':products},sort_keys=True,separators=(',',':')).encode()).hexdigest();assert len(products)==209 and context=='1b71af17048675296435ca74af284d54f93f2506b9c406517a452a3ce816dbdd'
 c=cf.parse((classes/'dev/mixer/android/NativeRenderer.class').read_bytes());m=next(m for m in c['methods'] if m['name']=='children');assert not m['exceptions'];cert=json.loads((runroot/'actual-five-v1.json').read_bytes())
 for row in cert['rows']:
  i=next(i for i in m['instructions'] if i['bci']==row['bci']);assert i['mnemonic']=='invokevirtual';row['caller']={'class':c['class'],'class_sha256':products[c['class']+'.class']['sha256'],'source_sha256':reference['NativeRenderer.java']['sha256'],'method':'children','descriptor':m['descriptor'],'bci':i['bci'],'opcode':i['mnemonic'],'callee':i['target']}
 cert.update(context_id=context,exact_product_classes=209,product_class_map=products,product_sources=reference,original_assertions_source=identity(D/'inputs/NativeOwnerV2ConcreteHostTests.java'),original_v1_method_body=identity(D/'inputs/unchanged-v1Baselines.java.txt'))
 save(runroot/'bound-five-v1-proposal.json',cert);print(json.dumps({'five_v1_actual_positive_witnesses':len(cert['rows']),'context':context,'complete_matrix_accepted':False}))
finally:
 shutil.rmtree(scratch);save(runroot/'cleanup.json',{'all_children_reaped':all(c['reaped'] for c in commands),'scratch_removed':not scratch.exists(),'native_UI_capture_or_process_inventory':False})
