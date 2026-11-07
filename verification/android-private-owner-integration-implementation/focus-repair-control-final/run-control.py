#!/usr/bin/env python3
"""Bounded immutable-before/current-after actual subject witness; no platform or profile mutation."""
from pathlib import Path
import datetime,hashlib,json,os,shutil,signal,subprocess,tempfile,time
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;BASE=HERE.parent
def ident(data):return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def save(path,value):path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
assert not (HERE/'receipt.json').exists()
env=dict(os.environ)
for key in ('_JAVA_OPTIONS','JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','CLASSPATH','JAVA_OPTS','JDK_JAVAC_OPTIONS'):env.pop(key,None)
jdk=Path('/opt/homebrew/opt/openjdk/libexec/openjdk.jdk/Contents/Home').resolve();commands=[];scratch=Path(tempfile.mkdtemp(prefix='focus-witness-',dir=HERE));receipt={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'same witness and exact real fourteen-subject class bytes, selected mechanical Android/JNI substitutes; no native runtime','status':'failed'}
def run(label,argv):
 start=time.monotonic()
 with (HERE/(label+'.stdout')).open('wb') as out,(HERE/(label+'.stderr')).open('wb') as err:
  child=subprocess.Popen([str(v) for v in argv],cwd=ROOT,env=env,stdout=out,stderr=err,start_new_session=True)
  try:child.wait(timeout=30)
  except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait();raise
  finally:
   if child.poll() is None:os.killpg(child.pid,signal.SIGKILL);child.wait()
 commands.append({'label':label,'argv':[str(v) for v in argv],'exit':child.returncode,'seconds':time.monotonic()-start,'child_reaped':True,'stdout':ident((HERE/(label+'.stdout')).read_bytes()),'stderr':ident((HERE/(label+'.stderr')).read_bytes())});save(HERE/'commands.json',commands);return child.returncode
try:
 empty=scratch/'empty';empty.mkdir();assert run('javac-version',[jdk/'bin/javac','-version'])==0;assert run('java-version',[jdk/'bin/java','-version'])==0;assert run('revision',['git','rev-parse','HEAD'])==0
 receipt['tools']={str(jdk/'bin'/name):ident((jdk/'bin'/name).read_bytes()) for name in ('java','javac')};receipt['witness']=ident((HERE/'FocusStateWitness.java').read_bytes());receipt['candidate2_manifest']=ident((BASE/'candidate-2/manifest.json').read_bytes());receipt['classes']={}
 for label,runpath in [('candidate2',BASE/'candidate-2/evidence/concrete-final-3'),('repaired',BASE/'scope-repair-B-final-1')]:
  classes=runpath/'classes';output=scratch/label;output.mkdir();receipt['classes'][label]={'path':str(classes.relative_to(ROOT)),'class_map':ident((runpath/'class-map.json').read_bytes()),'source_map':ident((runpath/'source-map.json').read_bytes())}
  assert run(label+'-compile',[jdk/'bin/javac','--release','17','-Xlint:all','-Werror','-proc:none','-sourcepath',empty,'-classpath',classes,'-d',output,HERE/'FocusStateWitness.java'])==0
  shutil.copytree(output,HERE/(label+'-witness-classes'))
  for mode in ('input','effect'):
   result=run(label+'-'+mode,[jdk/'bin/java','-ea','-Xmx128m','-cp',str(output)+os.pathsep+str(classes),'dev.mixer.android.FocusStateWitness',ROOT/'verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json',mode]);assert result==(1 if label=='candidate2' else 0),(label,mode,result)
 receipt['status']='passed-controlled-before-failure-and-after-success-host-only'
finally:
 shutil.rmtree(scratch);receipt['cleanup']={'scratch_removed':not scratch.exists(),'children_reaped':all(value['child_reaped'] for value in commands),'native_or_capture_instances_created_or_queried':False};save(HERE/'receipt.json',receipt)
print(receipt['status'])
