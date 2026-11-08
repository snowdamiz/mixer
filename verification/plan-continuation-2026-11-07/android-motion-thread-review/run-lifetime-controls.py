import hashlib,json,os,shutil,signal,subprocess,time
from pathlib import Path
out=Path(__file__).resolve().parent
inputs=out/'targeted-inputs'
jdk=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home').resolve()
def identity(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
mapping=json.loads((out/'targeted-source-map.json').read_text())
assert all(identity(inputs/p)==v for p,v in mapping.items())
env=dict(os.environ)
for k in ('JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','JDK_JAVA_OPTIONS','JDK_JAVAC_OPTIONS','CLASSPATH','JAVA_OPTS'):env.pop(k,None)
records=[];scratch=out/'lifetime-scratch';scratch.mkdir();classes=scratch/'classes';classes.mkdir();empty=scratch/'empty';empty.mkdir()
def run(label,args,limit):
 stdout=out/(label+'.stdout');stderr=out/(label+'.stderr');start=time.monotonic();stop=None
 with stdout.open('wb') as o,stderr.open('wb') as e:
  child=subprocess.Popen([str(x) for x in args],cwd=out,env=env,stdout=o,stderr=e,start_new_session=True)
  try:
   while child.poll() is None:
    if time.monotonic()-start>limit:stop='timeout'
    if max(stdout.stat().st_size,stderr.stat().st_size)>2_000_000:stop='output-limit'
    if stop:os.killpg(child.pid,signal.SIGKILL);break
    time.sleep(.05)
  finally:
   if child.poll() is None:os.killpg(child.pid,signal.SIGKILL)
   child.wait()
 try:os.killpg(child.pid,0);absent=False
 except ProcessLookupError:absent=True
 if not absent:os.killpg(child.pid,signal.SIGKILL)
 records.append({'label':label,'argv':[str(x) for x in args],'cwd':str(out),'exit':child.returncode,'seconds':time.monotonic()-start,'timeoutSeconds':limit,'outputLimitPerStream':2_000_000,'stop':stop,'ownedPidAndPgid':child.pid,'childReaped':True,'ownedGroupAbsentAfterReap':absent,'stdout':identity(stdout),'stderr':identity(stderr)})
 (out/'lifetime-commands.json').write_text(json.dumps(records,indent=2)+'\n')
 assert child.returncode==0 and stop is None,(label,stderr.read_text()[:2000])
try:
 run('lifetime-compile',[jdk/'bin/javac','--release','17','-Xlint:all','-Werror','-proc:none','-classpath',empty,'-sourcepath',empty,'-d',classes,*[inputs/p for p in mapping if p.endswith('.java')],out/'MotionLifetimeControlProbe.java'],60)
 run('lifetime-control',[jdk/'bin/java','-ea','-Xmx256m','-cp',classes,'dev.mixer.android.MotionLifetimeControlProbe',inputs/'verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json'],20)
 print((out/'lifetime-control.stdout').read_text())
finally:
 shutil.rmtree(scratch)
 (out/'lifetime-cleanup.json').write_text(json.dumps({'ownedScratchRemoved':not scratch.exists(),'commandsReaped':all(r['childReaped'] for r in records),'tools':{str(jdk/'bin'/n):identity(jdk/'bin'/n) for n in ('java','javac')},'toolVersions':'same resolved JDK/hashes as targeted-java-version.stderr and targeted-javac-version.stdout','sourceMap':'targeted-source-map.json','nativeDeviceOrHeldProcessActivity':False},indent=2)+'\n')
