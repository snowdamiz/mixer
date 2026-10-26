from pathlib import Path
import subprocess,os,signal,time,hashlib,json,shutil,datetime,tempfile
D=Path(__file__).resolve().parent;assert not (D/'review-seal.json').exists();E=D/'runs/controls-1';E.mkdir();JDK=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
def ident(p):b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
classes=D/'runs/host-1/classes';independent=D/'runs/host-1/independent-classes'
for rel in ('classes','independent-classes','independent-controls'):
 p=D/'runs/host-1'/rel;save(E/(rel+'-inputs.json'),{str(q.relative_to(p)):ident(q) for q in sorted(p.rglob('*')) if q.is_file()})
scratch=Path(tempfile.mkdtemp(prefix='owned-controls-',dir=E));temp=scratch/'tmp';temp.mkdir();commands=[]
env=dict(os.environ)
for k in ('_JAVA_OPTIONS','JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','CLASSPATH','JAVA_OPTS','JAVA_OPTIONS','JDK_JAVAC_OPTIONS'):env.pop(k,None)
env.update(TMPDIR=str(temp),TMP=str(temp),TEMP=str(temp))
def run(name,argv):
 start=time.monotonic();timed=False
 with (E/(name+'.stdout')).open('wb') as out,(E/(name+'.stderr')).open('wb') as err:
  child=subprocess.Popen([str(x) for x in argv],cwd=D,env=env,stdout=out,stderr=err,start_new_session=True)
  try:code=child.wait(timeout=60)
  except BaseException:timed=True;os.killpg(child.pid,signal.SIGKILL);code=child.wait(timeout=5);raise
 row={'name':name,'argv':[str(x) for x in argv],'exit':code,'timeout_seconds':60,'timed_out':timed,'reaped':True,'elapsed_seconds':time.monotonic()-start,'stdout':ident(E/(name+'.stdout')),'stderr':ident(E/(name+'.stderr'))};commands.append(row);save(E/'commands.json',commands);print(name,'exit',code,flush=True)
 return code
try:
 cp=str(independent)+os.pathsep+str(classes);java=[JDK/'bin/java','-Djava.io.tmpdir='+str(temp),'-ea','-Xmx256m','-cp',cp];desc=D/'frozen/descriptor.json'
 for case in ('getter-suffix-matrix','journal-membership'):
  run('frozen-independent-'+case,java+['dev.mixer.android.IndependentPreservationCompletionControls',case,desc])
 for case in ('healthy','captured-substitution','duplicate','swap','null','foreign','size-short','size-long','size-negative','scope-null','scope-clone','forward-clear','no-scope-duplicate','no-scope-swap','no-scope-size-short','reporter-reentry'):
  run('prepared-independent-'+case,java+['dev.mixer.android.IndependentMembershipControls',case,desc])
 run('completion-bytecode',[JDK/'bin/javap','-p','-c','-classpath',classes,'dev.mixer.android.NativeRenderer','dev.mixer.android.NativeRenderer$2','dev.mixer.android.NativeAppearanceViewsV2$FieldPreservation','dev.mixer.android.NativeRenderer$AttachmentJournal','dev.mixer.android.NativeRenderer$NativeState','dev.mixer.android.NativeRenderer$PreservationMembership'])
 run('adapter-bytecode',[JDK/'bin/javap','-p','-s','-c','-classpath',classes,*[f'dev.mixer.android.NativeEditorConnectionV2${n}' for n in ('Base','Api31','Api33','Api34')]])
finally:
 shutil.rmtree(scratch);save(E/'receipt.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Unchanged frozen controls against exact independently compiled host1 product; the full original identity matrix raw failure remains retained separately','status':'passed-controls-only' if commands and all(c['exit']==0 for c in commands) else 'failed-controls','commands':len(commands),'cleanup':{'children_reaped':all(c['reaped'] for c in commands),'scratch_removed':not scratch.exists(),'native_UI_capture_or_process_inventory':False}})
