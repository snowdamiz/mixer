#!/usr/bin/env python3
"""Root-only integration of reviewed original-owner private memory operations."""
import datetime,hashlib,json,os,pathlib,shutil,subprocess,tarfile,tempfile
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
CANDIDATE=ROOT/'verification/swift-memory-promoted-correction'
REVIEW=ROOT/'verification/swift-memory-promoted-review'
REVIEW_RECEIPT_HASH='784291149313df96edf29921e814a4ec400a0a8d2fccd3c56a69c35c0e92e6c0'
sha=lambda b:hashlib.sha256(b).hexdigest()
encoded=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
def save(name,x):(HERE/name).write_bytes(encoded(x))
def source():
 vm=ROOT/'vm';paths=[vm/'Cargo.toml',vm/'Cargo.lock']+[p for d in ['src','tests','include']for p in sorted((vm/d).rglob('*'))if p.is_file()]
 return{str(p.relative_to(vm)):sha(p.read_bytes())for p in paths}
def main():
 assert REVIEW_RECEIPT_HASH!='PENDING','independent review not selected'
 assert not(HERE/'integration.json').exists(),'one-time integration collector'
 assert sha((REVIEW/'receipt.json').read_bytes())==REVIEW_RECEIPT_HASH
 baseline=json.loads((CANDIDATE/'baseline-source-manifest.json').read_text());reviewed=json.loads((CANDIDATE/'candidate-source-manifest.json').read_text());expected=json.loads((HERE/'expected-source-manifest.json').read_text())
 assert source()==baseline,'live VM drift; no overwrite'
 commands=[];status='failed';applied=[];scratch=None
 env={**os.environ,'PATH':'/opt/homebrew/opt/rustup/bin:'+os.environ['PATH']}
 for key in ['RUSTFLAGS','RUSTC_BOOTSTRAP']:env.pop(key,None)
 def run(label,argv,cwd=ROOT,expected_tests=None):
  start=datetime.datetime.now(datetime.timezone.utc).isoformat();p=subprocess.run(argv,cwd=cwd,env=env,capture_output=True)
  output=p.stdout+p.stderr;path=HERE/(label+'.log');path.write_bytes(output)
  commands.append({'label':label,'argv':argv,'cwd':str(cwd),'startedUTC':start,'finishedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exitCode':p.returncode,'log':path.name,'sha256':sha(output),'sourceDigest':sha(encoded(source()))});save('commands.json',commands)
  assert p.returncode==0,(label,p.returncode)
  if expected_tests is not None:assert f'test result: ok. {expected_tests} passed; 0 failed; 0 ignored;'in output.decode(),label
  print(label+' passed',flush=True)
 try:
  run('producer-integrity',['python3','-B',str(CANDIDATE/'verify.py'),'--live-baseline'])
  run('review-integrity',['python3','-B',str(REVIEW/'verify.py'),'--live-baseline'])
  with tarfile.open(CANDIDATE/'candidate-source.tar.gz')as t:
   members=t.getmembers();assert len(members)==len(reviewed)
   assert all(m.isfile()and m.name.startswith('vm/')and'..'not in pathlib.PurePosixPath(m.name).parts for m in members)
   bodies={m.name.removeprefix('vm/'):t.extractfile(m).read()for m in members}
  assert set(bodies)==set(reviewed)and all(sha(body)==reviewed[name]for name,body in bodies.items())
  name='src/experimental/execution/mod.rs';lines=bodies[name].splitlines(keepends=True)
  assert lines[1138]==lines[1139]==b'    \n';lines[1138]=lines[1139]=b'\n';bodies[name]=b''.join(lines)
  assert all(sha(body)==expected[name]for name,body in bodies.items())
  for name,body in bodies.items():
   if expected[name]!=baseline.get(name):
    p=ROOT/'vm'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(body);applied.append('vm/'+name)
  assert source()==expected;save('integrated-source-manifest.json',source())
  scratch=pathlib.Path(tempfile.mkdtemp(prefix='mixer-memory-root-',dir='/private/tmp'));env['CARGO_TARGET_DIR']=str(scratch/'target')
  run('rustc-version',['rustc','--version','--verbose']);run('cargo-version',['cargo','--version']);run('host-version',['uname','-a'])
  run('integrated-memory-frame-value-control',['cargo','test','--lib','--locked','--offline','--all-features','--release','experimental_swift_reactor::execution::','--','--nocapture','--test-threads=1'],ROOT/'vm',62)
  run('integrated-frozen',['cargo','test','--test','span_execution','--locked','--offline','--all-features','--release','--','--nocapture','--test-threads=1'],ROOT/'vm',16)
  run('integrated-ci-swift-clippy',['cargo','clippy','--locked','--offline','--lib','--features','experimental-swift-reactor','--','-D','warnings'],ROOT/'vm')
  run('integrated-whitespace',['git','diff','--check','--',*applied])
  assert source()==expected;status='passed-private-memory-integration'
 finally:
  if scratch:shutil.rmtree(scratch)
  cleanup={'ownedScratch':str(scratch)if scratch else None,'ownedScratchRemoved':scratch is None or not scratch.exists(),'nativeInstancesStarted':0,'physicalRuns':0,'otherProjectProcessesModified':False};save('cleanup.json',cleanup)
  save('integration.json',{'schema':1,'status':status,'sourceRevision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'reviewReceiptSHA256':REVIEW_RECEIPT_HASH,'reviewedSourceClosure':sha(encoded(reviewed)),'integratedSourceClosure':sha(encoded(expected)),'normalization':'Removed four spaces from each of two otherwise blank lines1139/1140 in experimental/execution/mod.rs; separate exact patch bound.','appliedFiles':applied,'commands':commands,'sourceFiles':len(expected),'plannedRootTests':{'memoryFrameValueControl':62,'frozenIntegration':16,'configuration':'all-feature Release serial','ciSwiftOnlyClippy':'warnings denied'},'cleanup':cleanup,'fullDispatcher':False,'publicInvocation':False,'gaAcceptance':False})
if __name__=='__main__':main()
