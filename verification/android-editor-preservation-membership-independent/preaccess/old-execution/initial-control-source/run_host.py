#!/usr/bin/env python3
"""Bounded isolated copied-source JVM harness. No generators or hosted harnesses."""
from pathlib import Path
import os,hashlib,json,subprocess,time,signal,shutil,sys,datetime
BASE=Path(__file__).resolve().parent
JDK=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
OUT=BASE/'old-execution'
SCRATCH=OUT/'owned-scratch'
TOOLS=[JDK/'bin/java',JDK/'bin/javac',JDK/'lib/modules',JDK/'lib/server/libjvm.dylib']
def bind(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def main():
 assert not OUT.exists(), 'retain every attempt; choose a new output directory before another run'
 OUT.mkdir();(SCRATCH/'tmp').mkdir(parents=True);(SCRATCH/'empty-source').mkdir();(SCRATCH/'classes').mkdir()
 env=dict(os.environ)
 for k in ('JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','_JAVA_OPTIONS','CLASSPATH','JAVA_OPTIONS'):env.pop(k,None)
 env.update(TMPDIR=str(SCRATCH/'tmp'),TMP=str(SCRATCH/'tmp'),TEMP=str(SCRATCH/'tmp'))
 records=[]
 def run(name,argv,expected=None):
  start=time.monotonic(); timed=False
  with (OUT/(name+'.stdout')).open('wb') as stdout,(OUT/(name+'.stderr')).open('wb') as stderr:
   child=subprocess.Popen(argv,cwd=BASE,stdout=stdout,stderr=stderr,env=env,start_new_session=True)
   try:code=child.wait(timeout=60)
   except subprocess.TimeoutExpired:
    timed=True;os.killpg(child.pid,signal.SIGKILL);code=child.wait(timeout=5)
  row={'name':name,'argv':[str(x) for x in argv],'timeout_seconds':60,'expected_exit':expected,'exit':code,'timed_out':timed,'elapsed_seconds':time.monotonic()-start,'reaped':True,'stdout':bind(OUT/(name+'.stdout')),'stderr':bind(OUT/(name+'.stderr'))};records.append(row)
  (OUT/'commands.json').write_text(json.dumps(records,indent=2)+'\n')
  print(name,'exit',code,'expected',expected,flush=True)
  return code
 try:
  for tool in ('java','javac'):assert run(tool+'-version',[JDK/'bin'/tool,'-version'],0)==0
  src=sorted((BASE/'old-source/source').glob('*.java'))+sorted((BASE/'old-source/host-leaves').rglob('*.java'))+sorted((BASE/'old-source/tests').glob('*.java'))+sorted((BASE/'controls').glob('*.java'))
  (OUT/'input-map.json').write_text(json.dumps([{'path':str(p.relative_to(BASE)),**bind(p)} for p in src],indent=2)+'\n')
  compile=[JDK/'bin/javac','-J-Djava.io.tmpdir='+str(SCRATCH/'tmp'),'--release','17','-Xlint:all','-Werror','-proc:none','-sourcepath',SCRATCH/'empty-source','-classpath',SCRATCH/'empty-source','-d',SCRATCH/'classes',*src]
  if run('compile',compile,0)!=0:raise RuntimeError('compile failed')
  java=[JDK/'bin/java','-Djava.io.tmpdir='+str(SCRATCH/'tmp'),'-ea','-Xmx256m','-cp',SCRATCH/'classes']
  descriptor=BASE/'old-source/descriptor.json'
  old='dev.mixer.android.IndependentPreservationCompletionControls'
  # The original PC-C16 assertion is byte-for-byte unchanged and must fail on old source.
  assert run('unchanged-PC-C16',java+[old,'journal-membership',descriptor],1)==1
  for selected in ('three-success','no-scope','captured-A-refusal','partial-A-entered-C-refusal','constructor-before-registration','foreign-replay','fatal-chronology'):
   assert run('unchanged-'+selected,java+[old,selected,descriptor],0)==0
  for selected in ('duplicate','swap','null','foreign','size-short','size-long','size-negative','scope-null','scope-clone','forward-clear','no-scope-duplicate','no-scope-swap','no-scope-size-short','reporter-reentry'):
   run('prepared-'+selected,java+['dev.mixer.android.IndependentMembershipControls',selected,descriptor])
  classes=[{'path':str(p.relative_to(SCRATCH/'classes')),**bind(p)} for p in sorted((SCRATCH/'classes').rglob('*.class'))]
  (OUT/'class-map.json').write_text(json.dumps(classes,indent=2)+'\n')
 finally:
  shutil.rmtree(SCRATCH)
  receipt={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Old frozen sixteen-file product and unchanged host leaves; prepared preaccess controls only. Candidate review pending.','python':sys.version,'commands':records,'tools':{str(p):bind(p) for p in TOOLS},'cleanup':{'all_children_reaped':all(r['reaped'] for r in records),'owned_scratch_removed':not SCRATCH.exists(),'classes_deliberately_removed_after_class_map':True,'native_UI_capture_process_inventory':False}}
  (OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()
