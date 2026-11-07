#!/usr/bin/env python3
"""Closed explicit-source host closures; selected source hashes are evidence, never admission policy."""
import argparse, datetime, hashlib, json, os, shutil, signal, subprocess, sys, tempfile, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
ROSTER_SOURCE='native/android/tests/private-owner-host-roster.json'
ROSTER=ROOT/ROSTER_SOURCE
STRIP=('_JAVA_OPTIONS','JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','CLASSPATH','JAVA_OPTS','JDK_JAVAC_OPTIONS')
def ident(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,v):p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--closure',choices=('A','B'),default='B');p.add_argument('--skip-matrix',action='store_true');p.add_argument('--jdk',type=Path,default=Path('/opt/homebrew/opt/openjdk/libexec/openjdk.jdk/Contents/Home'));a=p.parse_args()
 evidence=a.evidence.resolve();evidence.mkdir(parents=True,exist_ok=False)
 roster_bytes=ROSTER.read_bytes();roster=json.loads(roster_bytes);closure=roster['closures']['A-orchestration' if a.closure=='A' else 'B-concrete-renderer-views']
 sources=closure['actual_production_sources']+['native/android/app/src/dev/mixer/android/NativeEnvironmentPlatformV2.java']+[s['source'] for s in closure['substitutes']]+closure['test_support_sources']+[closure['test_source']]
 if len(set(sources))!=len(sources):raise RuntimeError('duplicate explicit source')
 frozen={s:(ROOT/s).read_bytes() for s in sources};frozen[ROSTER_SOURCE]=roster_bytes;frozen['native/android/tests/run-private-owner-host.py']=Path(__file__).read_bytes()
 mapping='verification/android-private-owner-integration-implementation/barrier-map.json';frozen[mapping]=(ROOT/mapping).read_bytes()
 descriptor='verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json';frozen[descriptor]=(ROOT/descriptor).read_bytes()
 save(evidence/'source-map.json',{s:ident(b) for s,b in frozen.items()});save(evidence/'roster.json',closure)
 env=dict(os.environ)
 for k in STRIP:env.pop(k,None)
 scratch=Path(tempfile.mkdtemp(prefix='private-owner-host-',dir=evidence));commands=[];receipt={'schema':1,'closure':a.closure,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':sys.argv,'python':sys.version,'scope':'actual production subjects, controlled Android/JNI leaves; no native runtime','native_or_capture_processes_started_or_queried':False,'status':'failed'}
 def run(label,argv,timeout=60):
  t=time.monotonic();timed=False;overflow=False
  outpath=evidence/(label+'.stdout');errpath=evidence/(label+'.stderr')
  with outpath.open('wb') as out,errpath.open('wb') as err:
   child=subprocess.Popen([str(x) for x in argv],cwd=ROOT,env=env,stdout=out,stderr=err,start_new_session=True)
   try:
    while child.poll() is None:
     timed=time.monotonic()-t>timeout
     overflow=outpath.stat().st_size>4_000_000 or errpath.stat().st_size>4_000_000
     if timed or overflow:os.killpg(child.pid,signal.SIGKILL);break
     time.sleep(.05)
   finally:
    if child.poll() is None:os.killpg(child.pid,signal.SIGKILL)
    child.wait()
  out=outpath.read_bytes();err=errpath.read_bytes()
  commands.append({'label':label,'argv':[str(x) for x in argv],'exit':child.returncode,'timeout':timed,'output_limit_exceeded':overflow,'elapsed':time.monotonic()-t,'stdout':ident(out),'stderr':ident(err),'child_reaped':True});save(evidence/'commands.json',commands)
  if timed or overflow or child.returncode:raise RuntimeError(label+' failed')
  return out

 try:
  jdk=a.jdk.resolve(strict=True);java=jdk/'bin/java';javac=jdk/'bin/javac';javap=jdk/'bin/javap';receipt['tools']={str(x):ident(x.resolve().read_bytes()) for x in (java,javac,javap)}
  run('javac-version',[javac,'-version']);run('java-version',[java,'-version']);receipt['revision']=run('revision',['git','rev-parse','HEAD']).decode().strip()
  files=[]
  for s,b in frozen.items():
   dest=evidence/'inputs'/s;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b)
   if s in sources:files.append(dest)
  classes=scratch/'classes';empty=scratch/'empty';classes.mkdir();empty.mkdir()
  run('compile',[javac,'--release','17','-Xlint:all','-Werror','-proc:none','-classpath',empty,'-sourcepath',empty,'-d',classes,*files])
  shutil.copytree(classes,evidence/'classes')
  run('bytecode',[javap,'-c','-p','-classpath',classes,'dev.mixer.android.NativeCoordinatorV2','dev.mixer.android.NativeRenderer','dev.mixer.android.NativeAppearanceViewsV2$Mutation'] if a.closure=='B' else [javap,'-c','-p','-classpath',classes,'dev.mixer.android.NativeOwnerV2','dev.mixer.android.NativeCoordinatorV2'])
  save(evidence/'class-map.json',{str(x.relative_to(classes)):ident(x.read_bytes()) for x in sorted(classes.rglob('*.class'))})
  hostargv=[java,'-ea','-Xmx256m','-cp',classes,'dev.mixer.android.NativeOwnerV2'+('Concrete' if a.closure=='B' else '')+'HostTests',evidence/'inputs'/descriptor,evidence/'observed-sites.txt',evidence/'inputs'/mapping]
  if not a.skip_matrix:hostargv.append(evidence/'barrier-cases.json')
  result=run('host',hostargv,300)
  if not result.startswith(b'PASS '):raise RuntimeError('missing host PASS')
  receipt['status']='passed-host-only';print(result.decode().strip())
 except BaseException as failure:receipt['failure']={'type':type(failure).__name__,'message':str(failure)};raise
 finally:
  shutil.rmtree(scratch);receipt['cleanup']={'scratch_removed':not scratch.exists(),'children_reaped':all(c['child_reaped'] for c in commands),'native_instances_created':False};receipt['source_stable']=all((ROOT/s).read_bytes()==b for s,b in frozen.items());save(evidence/'receipt.json',receipt)
if __name__=='__main__':main()
