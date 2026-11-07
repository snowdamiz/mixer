"""Fresh bounded two-job Swift host test, scratch isolated from historical builds."""
import datetime, hashlib, json, os, pathlib, shutil, subprocess, tempfile, time
from cleanup_control import stop
P=pathlib.Path
OUT=P(__file__).resolve().parent
ROOT=OUT.parents[2]
SWIFT=P('/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift')
scratch=P(tempfile.mkdtemp(prefix='mixer-effective-motion-cli-',dir='/tmp'))
env=dict(os.environ,DEVELOPER_DIR='/Applications/Xcode_26.6.app/Contents/Developer')
argv=[str(SWIFT),'test','--package-path',str(ROOT/'cli'),'--scratch-path',str(scratch),'--jobs','2','--filter','androidCompatibility']
start=time.monotonic();receipt={'argv':argv,'cwd':str(ROOT),'sourceRevision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'startedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'swiftVersion':subprocess.check_output([str(SWIFT),'--version'],text=True,env=env).strip(),'swiftSHA256':hashlib.sha256(SWIFT.read_bytes()).hexdigest(),'scratch':str(scratch),'deadlineSeconds':900,'buildJobs':2}
sources=['cli/Sources/MixerBuild/AndroidSDKCompatibility.swift','cli/Sources/MixerBuild/Resources/android-build.py','cli/Tests/MixerBuildTests/AndroidSDKCompatibilityTests.swift']
receipt['sources']={rel:hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() for rel in sources}
with (OUT/'pair8-swift-tests.log').open('wb') as stream:
 p=subprocess.Popen(argv,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
 receipt['pid']=p.pid;receipt['pgid']=p.pid
 try:
  p.wait(timeout=900)
 except subprocess.TimeoutExpired:
  receipt['timeout']=True
 finally:
  receipt['cleanup']=stop(p);receipt['exit']=p.poll();receipt['elapsedSeconds']=time.monotonic()-start
  receipt['status']='passed' if p.returncode==0 and receipt['cleanup']['groupAbsent'] else 'failed'
  if receipt['cleanup']['groupAbsent']:shutil.rmtree(scratch)
  receipt['scratchRemoved']=not scratch.exists()
  receipt['sourceStable']=all(hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==h for rel,h in receipt['sources'].items())
  (OUT/'pair8-swift-receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(json.dumps(receipt,indent=2))
raise SystemExit(0 if receipt['status']=='passed' else 1)
