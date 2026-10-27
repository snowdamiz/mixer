from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,tempfile,time
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRODUCER=ROOT/'verification/swift-real-profile-loader-binding'
def ident(p):
 p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def write(name,v):(HERE/name).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
scratch=Path(tempfile.mkdtemp(prefix='replay-host-',dir=HERE));copy=scratch/'producer';shutil.copytree(PRODUCER,copy)
runner=copy/'run_checks.py';original=runner.read_bytes();old=b"HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];SOURCE=HERE/'source/vm'";new=b"HERE=Path(__file__).resolve().parent;ROOT=Path('/Users/andreyyurlov/Documents/dev/mixer');SOURCE=HERE/'source/vm'";assert original.count(old)==1;runner.write_bytes(original.replace(old,new));(HERE/'replayed_run_checks.py').write_bytes(runner.read_bytes())
write('replay-runner-variant.json',{'source_runner':ident(PRODUCER/'run_checks.py'),'copied_runner':ident(runner),'exact_replacement_before':old.decode(),'exact_replacement_after':new.decode(),'source_distribution_unchanged':True,'frozen_prepare_or_finalizer_rerun':False})
start=time.monotonic();code=None
try:
 with (HERE/'replay.stdout').open('wb')as o,(HERE/'replay.stderr').open('wb')as e:
  child=subprocess.Popen([sys.executable,'-B',str(runner)],cwd=ROOT,stdout=o,stderr=e)
  code=child.wait()
 preserve=['source-manifest.json','build-input-manifest.json','receipt.json','command-receipts.json','data-layouts.json','compile-variants.json','scenarios.json','unsupported-path-cases.json','session-observations.json','cleanup.json','build-preimage-debug.bin','build-preimage-optimized.bin','logs','sessions','source-preimages']
 dest=HERE/'replay';dest.mkdir()
 for name in preserve:
  p=copy/name
  if p.is_dir():shutil.copytree(p,dest/name)
  elif p.is_file():shutil.copyfile(p,dest/name)
 write('replay-outer-command.json',{'argv':[sys.executable,'-B',str(runner)],'cwd':str(ROOT),'exit_code':code,'elapsed_seconds':time.monotonic()-start,'terminally_waited':True,'stdout':ident(HERE/'replay.stdout'),'stderr':ident(HERE/'replay.stderr'),'subprocess_bounds':'Copied runner enforces60s/256KiB per owned child','frozen_producer_writes':False})
 assert code==0,(code,(HERE/'replay.stderr').read_text()[-4000:])
 print(json.dumps({'replay_exit_code':code,'nested_commands':json.loads((dest/'receipt.json').read_text())['commands']}))
finally:
 shutil.rmtree(scratch)
 write('replay-cleanup.json',{'scratch_path':str(scratch),'scratch_removed':not scratch.exists(),'outer_child_terminally_waited':code is not None,'native_UI_capture_process_inventory_used':False})
