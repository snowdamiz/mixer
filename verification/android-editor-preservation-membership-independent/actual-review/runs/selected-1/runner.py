from pathlib import Path
import os,signal,subprocess,time,json,hashlib,shutil,tempfile,datetime
D=Path(__file__).resolve().parent;E=D/'runs/selected-1';E.mkdir();J=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
def ident(p):b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
scratch=Path(tempfile.mkdtemp(prefix='owned-selected-',dir=E));temp=scratch/'tmp';temp.mkdir();classes=scratch/'classes';classes.mkdir();empty=scratch/'empty';empty.mkdir();commands=[]
env=dict(os.environ)
for k in ('_JAVA_OPTIONS','JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','CLASSPATH','JAVA_OPTS','JAVA_OPTIONS','JDK_JAVAC_OPTIONS'):env.pop(k,None)
env.update(TMPDIR=str(temp),TMP=str(temp),TEMP=str(temp))
def run(name,argv):
 start=time.monotonic();timed=False
 with (E/(name+'.stdout')).open('wb') as out,(E/(name+'.stderr')).open('wb') as err:
  c=subprocess.Popen([str(a) for a in argv],cwd=D,env=env,stdout=out,stderr=err,start_new_session=True)
  try:code=c.wait(timeout=60)
  except BaseException:timed=True;os.killpg(c.pid,signal.SIGKILL);code=c.wait(timeout=5);raise
 row={'name':name,'argv':[str(a) for a in argv],'exit':code,'timeout_seconds':60,'timed_out':timed,'reaped':True,'elapsed_seconds':time.monotonic()-start,'stdout':ident(E/(name+'.stdout')),'stderr':ident(E/(name+'.stderr'))};commands.append(row);save(E/'commands.json',commands);print(name,'exit',code,flush=True)
 if code:raise RuntimeError(name)
try:
 shutil.copytree(D/'selected-controls',E/'inputs');save(E/'input-map.json',{str(p.relative_to(E/'inputs')):ident(p) for p in sorted((E/'inputs').rglob('*')) if p.is_file()})
 host=D/'runs/host-1/classes';frozen=D/'runs/host-1/independent-classes';cp=str(frozen)+os.pathsep+str(host)
 run('compile',[J/'bin/javac','-J-Djava.io.tmpdir='+str(temp),'--release','17','-Xlint:all','-Werror','-proc:none','-classpath',cp,'-sourcepath',empty,'-d',classes,*sorted((E/'inputs').glob('*.java'))]);shutil.copytree(classes,E/'classes');save(E/'class-map.json',{str(p.relative_to(classes)):ident(p) for p in sorted(classes.rglob('*.class'))})
 java=[J/'bin/java','-Djava.io.tmpdir='+str(temp),'-ea','-Xmx256m','-cp',str(classes)+os.pathsep+cp];desc=D/'frozen/descriptor.json'
 run('selected-identity-matrix',java+['dev.mixer.android.SelectedIdentityMembershipReviewControls','identity-matrix',desc])
 for case in ('native','commit'):run('selected-own-forward-'+case,java+['dev.mixer.android.IndependentOwnForwardControls',case,desc])
finally:
 shutil.rmtree(scratch);save(E/'receipt.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Root exact forward amendment only; other original identity assertions unchanged; own forward isolated native/commit and restored-boolean replay','status':'passed-selected-controls' if len(commands)==4 and all(c['exit']==0 for c in commands) else 'failed-selected-controls','commands':len(commands),'cleanup':{'children_reaped':all(c['reaped'] for c in commands),'scratch_removed':not scratch.exists(),'native_UI_capture_process_inventory':False}})
