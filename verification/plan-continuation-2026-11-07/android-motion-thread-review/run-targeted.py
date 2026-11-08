import hashlib,json,os,shutil,signal,subprocess,sys,time
from pathlib import Path
OUT=Path(__file__).resolve().parent
CAND=Path('/Users/andreyyurlov/.t3/worktrees/mixer/t3-9ff4db6c')
FROZEN=CAND/'verification/plan-continuation-2026-11-07/android-motion-thread-fix/concrete-focused-2'
JDK=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home').resolve()
def identity(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(name,value):(OUT/name).write_text(json.dumps(value,indent=2)+'\n')
env=dict(os.environ)
for k in ('JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','JDK_JAVA_OPTIONS','JDK_JAVAC_OPTIONS','CLASSPATH','JAVA_OPTS'):env.pop(k,None)
records=[]
def run(label,argv,limit=60):
 out=OUT/(label+'.stdout');err=OUT/(label+'.stderr');start=time.monotonic();stop=None
 with out.open('wb') as o,err.open('wb') as e:
  child=subprocess.Popen([str(x) for x in argv],cwd=OUT,env=env,stdout=o,stderr=e,start_new_session=True)
  try:
   while child.poll() is None:
    if time.monotonic()-start>limit:stop='timeout'
    if max(out.stat().st_size,err.stat().st_size)>2_000_000:stop='output-limit'
    if stop:os.killpg(child.pid,signal.SIGKILL);break
    time.sleep(.05)
  finally:
   if child.poll() is None:os.killpg(child.pid,signal.SIGKILL)
   child.wait()
 try:os.killpg(child.pid,0);absent=False
 except ProcessLookupError:absent=True
 if not absent:os.killpg(child.pid,signal.SIGKILL)
 records.append({'label':label,'argv':[str(x) for x in argv],'cwd':str(OUT),'exit':child.returncode,'seconds':time.monotonic()-start,'timeoutSeconds':limit,'outputLimitPerStream':2_000_000,'stop':stop,'ownedPidAndPgid':child.pid,'childReaped':True,'ownedGroupAbsentAfterReap':absent,'stdout':identity(out),'stderr':identity(err)})
 save('targeted-commands.json',records)
 assert child.returncode==0 and stop is None,(label,err.read_text()[:2000])
mapping=json.loads((FROZEN/'source-map.json').read_text())
for p,v in mapping.items():assert identity(FROZEN/'inputs'/p)==v==identity(CAND/p),p
inputs=OUT/'targeted-inputs';inputs.mkdir()
for p in mapping:
 target=inputs/p;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(FROZEN/'inputs'/p,target)
save('targeted-source-map.json',mapping)
scratch=OUT/'targeted-scratch';scratch.mkdir();classes=scratch/'classes';classes.mkdir();empty=scratch/'empty';empty.mkdir()
try:
 run('targeted-java-version',[JDK/'bin/java','-version'])
 run('targeted-javac-version',[JDK/'bin/javac','-version'])
 sources=[inputs/p for p in mapping if p.endswith('.java')]
 run('targeted-compile',[JDK/'bin/javac','--release','17','-Xlint:all','-Werror','-proc:none','-classpath',empty,'-sourcepath',empty,'-d',classes,*sources,OUT/'MotionOrderingProbe.java'])
 save('targeted-class-map.json',{str(p.relative_to(classes)):identity(p) for p in sorted(classes.rglob('*.class'))})
 run('targeted-ordering',[JDK/'bin/java','-ea','-Xmx256m','-cp',classes,'dev.mixer.android.MotionOrderingProbe',inputs/'verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json'],20)
 save('targeted-result.json',{'status':'PASS counterexample and control','tools':{str(JDK/'bin'/n):identity(JDK/'bin'/n) for n in ('java','javac')},'sourceBytesEqualCandidateAndFrozen':True,'fullBMatrixRun':False,'scope':'actual candidate product owner/observer/coordinator/renderer with frozen controlled Android/JNI leaves; independent two callback schedules only; no native execution'})
 print((OUT/'targeted-ordering.stdout').read_text())
finally:
 shutil.rmtree(scratch);save('targeted-cleanup.json',{'ownedScratchRemoved':not scratch.exists(),'commandsReaped':all(r['childReaped'] for r in records),'nativeDeviceOrHeldProcessActivity':False})
