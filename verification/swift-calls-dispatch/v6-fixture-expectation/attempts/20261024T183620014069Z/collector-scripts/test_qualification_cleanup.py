"""Tool-only failure controls. Python helper children; no Mixer/compiler/native run."""
from pathlib import Path
import sys,subprocess,tempfile,datetime,types,shutil,signal,os
import collect as c
import qualified_runtime as q
base=c.HERE/'tooling-tests'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');base.mkdir(parents=True)
children=[];scratches=[];original_here=c.HERE
try:
 capture=subprocess.Popen([sys.executable,'-c','import sys; print(123); print(456,file=sys.stderr)'],start_new_session=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE);children.append(capture);event={};stdout,stderr=q.RetainedChild(capture,base/'raw-capture.json',event).communicate(timeout=5);assert stdout==b'123\n'and stderr==b'456\n';assert __import__('gzip').decompress((base/'raw-capture-stdout.gz').read_bytes())==stdout
 first=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'],start_new_session=True);second=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'],start_new_session=True);children.extend([first,second])
 class FailOnce:
  def __init__(self,child):self.child=child;self.pid=child.pid;self.failed=False
  def poll(self):
   if not self.failed:self.failed=True;raise RuntimeError('injected first-process cleanup observation failure')
   return self.child.poll()
  def __getattr__(self,name):return getattr(self.child,name)
 f=types.SimpleNamespace(root=base/'process-failure',children=[FailOnce(first),second],events=[],kill_events=[])
 safe=q.OwnedOS(f);r=q.independent_cleanup(f.root,f,safe,set((c.HERE/'attempts').iterdir()));assert not r['cleanupComplete']and r['processes'][0]['cleanupComplete']is False and r['processes'][1]['cleanupComplete']is True;assert first.poll()is None and second.poll()is not None
 safe.killpg(first.pid,signal.SIGKILL);first.wait(timeout=5)
 f.root=base/'process-recovery';r=q.independent_cleanup(f.root,f,safe,set((c.HERE/'attempts').iterdir()));assert r['cleanupComplete']
 # A completed numeric PID/PGID must not authorize killing a currently live
 # helper group. This fake is declared explicitly; no unrelated process is used.
 live=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'],start_new_session=True);children.append(live)
 fake=types.SimpleNamespace(pid=live.pid,poll=lambda:0)
 g=types.SimpleNamespace(root=base/'completed-numeric-group',children=[fake],events=[],kill_events=[])
 try:q.OwnedOS(g).killpg(live.pid,signal.SIGKILL)
 except AssertionError:pass
 else:raise AssertionError('completed numeric group kill unexpectedly authorized')
 assert live.poll()is None and not g.kill_events[-1]['killed']
 real=types.SimpleNamespace(root=base/'completed-control-recovery',children=[live],events=[],kill_events=[]);q.OwnedOS(real).killpg(live.pid,signal.SIGKILL);live.wait(timeout=5)
 # Two owned scratch fixtures, each outside actual collector attempts. Inject
 # malformed first metadata and verify the second target is still cleaned.
 fixtures=base/'scratch-fixtures';(fixtures/'attempts').mkdir(parents=True);c.HERE=fixtures
 targets=[]
 for name in ['first','second']:
  scratch=Path(tempfile.mkdtemp(prefix='mixer-calls-dispatch-'));scratches.append(scratch);target=str(scratch/'target');(scratch/'target').mkdir();a=fixtures/'attempts'/name;a.mkdir();c.save(a/'command.json',{'environment':{'CARGO_TARGET_DIR':target}});targets.append(target)
 c.save(fixtures/'attempts/first/command.json',{'injectedMalformedFixture':True})
 h=types.SimpleNamespace(root=base/'scratch-failure',children=[],events=[{'cargoTargetDir':t}for t in targets],kill_events=[])
 r=q.independent_cleanup(h.root,h,q.OwnedOS(h),set());assert not r['cleanupComplete']and r['targets'][0]['cleanupComplete']is False and r['targets'][1]['cleanupComplete']is True;assert scratches[0].exists()and not scratches[1].exists()
 c.save(fixtures/'attempts/first/command.json',{'environment':{'CARGO_TARGET_DIR':targets[0]}});h.root=base/'scratch-recovery';r=q.independent_cleanup(h.root,h,q.OwnedOS(h),set());assert r['cleanupComplete']and not any(p.exists()for p in scratches)
 c.save(base/'controls.json',{'toolOnly':True,'mixerVMExecuted':False,'compilerExecuted':False,'nativeExecuted':False,'oneProcessObservationFailureDoesNotSuppressLaterProcessCleanup':True,'completedNumericPGIDCannotKillLiveHelperGroup':True,'oneScratchMetadataFailureDoesNotSuppressLaterScratchCleanup':True,'allOwnedPythonChildrenStopped':all(p.poll()is not None for p in children),'allOwnedScratchRemoved':all(not p.exists()for p in scratches),'allFailureAndRecoveryRecordsPreserved':True,'rawPipeBytesSavedBeforeCollectorValidation':True})
 print('Tool cleanup4controls pass; all own Python helper groups/targets removed; no VM/compiler/native execution')
finally:
 c.HERE=original_here
 for child in children:
  if child.poll()is None:
   assert os.getpgid(child.pid)==child.pid;os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=5)
 for scratch in scratches:
  if scratch.exists():
   holders=subprocess.run(['lsof','-nP','+D',str(scratch)],capture_output=True);assert not holders.stdout;shutil.rmtree(scratch)
 c.save(base/'test-final-cleanup.json',{'allOwnedChildrenStopped':all(p.poll()is not None for p in children),'allOwnedTargetsRemoved':all(not p.exists()for p in scratches),'nativeInstancesCreated':0})
