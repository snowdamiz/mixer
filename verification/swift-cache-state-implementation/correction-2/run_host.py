#!/usr/bin/env python3
"""Bounded, serial rustc-only host execution; preserves all raw outputs."""
import hashlib,json,os,pathlib,platform,shutil,subprocess,time
ROOT=pathlib.Path(__file__).resolve().parent
REPO=ROOT.parents[2]
RUST=pathlib.Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def remove_product(path):
 p=pathlib.Path(path)
 if not p.exists():return
 row={'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p),'removed_at':time.time(),'owned_product':True}
 p.unlink();row['absent_after_removal']=not p.exists()
 receipt=ROOT/'evidence/owned-product-cleanup.json'
 rows=json.loads(receipt.read_text())if receipt.exists()else[]
 rows.append(row);receipt.write_text(json.dumps(rows,indent=2)+'\n')
def run(name,cmd,env=None):
 import selectors,signal
 argv=[str(v)for v in cmd];start=time.time();clock=time.monotonic();limit=60;cap=8*1024*1024
 proc=subprocess.Popen(argv,cwd=REPO,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
 ownership={'command':argv,'cwd':str(REPO),'pid':proc.pid,'pgid':proc.pid,'new_session':True,'started':start,'per_command_deadline_seconds':limit,'per_stream_output_cap':cap}
 (ROOT/'evidence'/f'{name}.start.json').write_text(json.dumps(ownership,indent=2)+'\n')
 sel=selectors.DefaultSelector();sel.register(proc.stdout,selectors.EVENT_READ,'stdout');sel.register(proc.stderr,selectors.EVENT_READ,'stderr')
 buffers={'stdout':bytearray(),'stderr':bytearray()};failure=None;killed=False
 while sel.get_map() or proc.poll() is None:
  if time.monotonic()-clock>=limit and failure is None:failure='timeout'
  if failure and not killed:
   try:os.killpg(proc.pid,signal.SIGKILL)
   except ProcessLookupError:pass
   killed=True
  for key,_ in sel.select(0.05):
   data=os.read(key.fileobj.fileno(),65536)
   if not data:sel.unregister(key.fileobj);key.fileobj.close();continue
   target=buffers[key.data];space=cap-len(target);target.extend(data[:space])
   if len(data)>space and failure is None:failure='output-cap'
 proc.wait(timeout=5);sel.close()
 stdout=bytes(buffers['stdout']);stderr=bytes(buffers['stderr'])
 (ROOT/'evidence'/f'{name}.stdout').write_bytes(stdout);(ROOT/'evidence'/f'{name}.stderr').write_bytes(stderr)
 receipt=dict(ownership,exit=proc.returncode,elapsed=time.time()-start,group_termination_requested=killed,failure=failure,parent_exit_observed=True,stdout_sha256=hashlib.sha256(stdout).hexdigest(),stderr_sha256=hashlib.sha256(stderr).hexdigest())
 (ROOT/'evidence'/f'{name}.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(name,proc.returncode,stdout.decode(errors='replace').splitlines()[-1:] or stderr.decode(errors='replace').splitlines()[-3:],flush=True)
 return subprocess.CompletedProcess(argv,proc.returncode if failure is None else (proc.returncode or 124),stdout,stderr)
if __name__=='__main__':
 run('rust-version',[RUST,'--version','--verbose'])
 snapshot={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'source').rglob('*') if p.is_file()}
 (ROOT/'evidence'/'source-before.json').write_text(json.dumps(snapshot,indent=2)+'\n')
 failures=0
 for mode,opts in [('debug',[]),('optimized',['-O'])]:
  exe=ROOT/'evidence'/f'host-tests-{mode}'
  r=run(f'compile-{mode}',[RUST,'--edition=2021','--test',*opts,ROOT/'source/library/analyzer.rs','-o',exe]);
  if r.returncode:failures+=1;remove_product(exe);continue
  scratch=ROOT/f'.scratch-{mode}';scratch.mkdir()
  current_cases=ROOT/'evidence/public-cases'/mode
  if current_cases.exists():
   archived=ROOT/'evidence/attempts'/f'prior-cases-{mode}-{time.time_ns()}';archived.parent.mkdir(exist_ok=True);shutil.move(current_cases,archived)
  env=dict(os.environ,MIXER_ANALYZER_LIBRARY_TEST_SCRATCH=str(scratch),MIXER_ENVELOPE_SCRATCH=str(scratch),MIXER_ANALYZER_LIBRARY_HISTORICAL=str(REPO/'verification/swift-envelope-ci-pack/inputs/historical'),MIXER_CACHE_FIXTURE_EVIDENCE=str(ROOT/'evidence/public-cases'/mode))
  try:
   r=run(f'tests-{mode}',[exe,'--test-threads=1','--nocapture'],env)
   if r.returncode:failures+=1
  finally:shutil.rmtree(scratch);remove_product(exe)
 (ROOT/'evidence'/'cleanup.json').write_text(json.dumps({'scratch_directories_removed':True,'owned_test_executables_removed':True,'native_runtime_or_capture_started':False,'other_project_processes_inspected':False},indent=2)+'\n')
 assert snapshot=={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'source').rglob('*') if p.is_file()}

 if failures:raise SystemExit(1)
