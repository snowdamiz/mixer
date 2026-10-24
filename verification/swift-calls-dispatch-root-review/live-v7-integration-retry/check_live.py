import pathlib,json,hashlib,subprocess,tempfile,os,shutil,signal,datetime
root=pathlib.Path('/Users/andreyyurlov/Documents/dev/mixer');out=root/'verification/swift-calls-dispatch-root-review/live-v7-integration-retry';p=root/'verification/swift-calls-dispatch/v7-fixture-expectations';candidate=json.loads((p/'candidate-final-manifest.json').read_text());h=lambda f:hashlib.sha256(pathlib.Path(f).read_bytes()).hexdigest()
for n,d in candidate.items():assert h(root/'vm'/n)==d,n
for k in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER']:assert not os.environ.get(k),k
compiler=pathlib.Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin/rustc');cargo=compiler.with_name('cargo');assert h(compiler)=='dd6f58440b3418aa9157ae3f05d71eecff741ca41bc4eec120e7e8f2d933b9a0'
scratch=pathlib.Path(tempfile.mkdtemp(prefix='mixer-v7-live-check-'));identity=scratch.stat();env=dict(os.environ,PATH='/opt/homebrew/opt/rustup/bin:'+os.environ['PATH'],CARGO_TARGET_DIR=str(scratch/'target'),CARGO_INCREMENTAL='0',RUSTC=str(compiler));assert pathlib.Path(shutil.which('rustc',path=env['PATH'])).resolve()==pathlib.Path('/opt/homebrew/opt/rustup/bin/rustc').resolve();argv=[str(cargo),'test','--lib','--locked','--offline','--no-default-features','--all-features','--','--nocapture','--test-threads=1'];child=None;passed=False;cleanup=False;failure=None
r={'schema':1,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sourceRevisionContext':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'command':argv,'cwd':str(root/'vm'),'scope':'Fresh all-feature debug library check after exact accepted source integration; prior27-command matrix supplies broader private qualification','sourceClosure':'78e2586b41f698c60e1bcd4cdd4abb33fbf98d747d1ee183a793988dea7b5237','PATH':env['PATH'],'toolSHA256':{'rustc':h(compiler),'cargo':h(cargo)},'toolVersions':{'rustc':subprocess.check_output([str(compiler),'-vV'],text=True),'cargo':subprocess.check_output([str(cargo),'--version'],text=True)},'ownedScratch':str(scratch)}
try:
 child=subprocess.Popen(argv,cwd=root/'vm',env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
 try:stdout,stderr=child.communicate(timeout=300)
 except subprocess.TimeoutExpired:
  if child.poll() is None:os.killpg(child.pid,signal.SIGKILL)
  stdout,stderr=child.communicate(timeout=10);raise
 finally:
  if 'stdout' in locals():(out/'live-check.stdout').write_bytes(stdout);(out/'live-check.stderr').write_bytes(stderr)
 r['exitCode']=child.returncode
 assert child.returncode==0 and b'test result: ok. 342 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out;' in stdout
 for n,d in candidate.items():assert h(root/'vm'/n)==d,n
 passed=True
except BaseException as error:failure={'type':type(error).__name__,'message':str(error)}
finally:
 if child is not None and child.poll() is None:
  os.killpg(child.pid,signal.SIGKILL);child.communicate(timeout=10)
 probe=subprocess.run(['lsof','-nP','+D',str(scratch)],capture_output=True,timeout=30);r['holderCheck']={'argv':probe.args,'exitCode':probe.returncode,'stdout':probe.stdout.decode(),'stderr':probe.stderr.decode()}
 if probe.returncode==1 and not probe.stdout and not probe.stderr and scratch.stat().st_dev==identity.st_dev and scratch.stat().st_ino==identity.st_ino:
  shutil.rmtree(scratch);cleanup=not scratch.exists()
 r.update(testsPassed=passed,cleanupPassed=cleanup,passed=passed and cleanup,failure=failure,tests=342 if passed else None,nativeInstancesCreated=0,bindings={f.name:h(f) for f in [out/'live-check.stdout',out/'live-check.stderr'] if f.exists()})
 (out/'live-check.json').write_text(json.dumps(r,indent=2)+'\n');(out/'check_live.py').write_bytes(pathlib.Path(__file__).read_bytes());print(json.dumps({k:v for k,v in r.items() if k not in ['toolVersions','command','bindings']},indent=2))
raise SystemExit(0 if passed and cleanup else 1)
