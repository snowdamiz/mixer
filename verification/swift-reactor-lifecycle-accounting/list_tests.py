"""Build exact unit binaries and run only libtest --list. No test body executes."""
from pathlib import Path
import collect as c
import gzip,json,os,shutil,signal,subprocess,tempfile,datetime

def group_members(group):
 output=subprocess.check_output(['/bin/ps','-axo','pid=,pgid=,command='],text=True)
 return [line.strip()for line in output.splitlines()if len(line.split(None,2))>=2 and line.split(None,2)[1]==str(group)]
def main():
 records=[]
 for features in ['swift','all']:
  for profile in ['debug','release']:
   cfg=features+'-'+profile;print('compile/list',cfg,flush=True)
   flags=['--no-default-features']+(['--features','experimental-swift-reactor']if features=='swift'else['--all-features'])+(['--release']if profile=='release'else[])
   code,attempt,out,err=c.run(['cargo','test','--lib','--no-run','--locked','--offline',*flags,'--message-format=json-render-diagnostics'],label='compile-list-'+cfg)
   assert code==0
   cargo=[json.loads(line)for line in out.decode().splitlines()if line.startswith('{')]
   executable=[row for row in cargo if row.get('reason')=='compiler-artifact'and row.get('executable')and row['profile']['test']and row['target']['name']=='mixer_vm'];assert len(executable)==1
   artifact=executable[0];name=Path(artifact['executable']).name
   saved=[row for row in json.loads((attempt/'artifacts.json').read_text())if Path(row['path']).name==name+'.gz'];assert len(saved)==1
   binding=saved[0];raw=gzip.decompress((attempt/binding['path']).read_bytes());assert c.sha(raw)==binding['sha256']
   scratch=Path(tempfile.mkdtemp(prefix='mixer-lifecycle-test-list-'));exe=scratch/name;exe.write_bytes(raw);exe.chmod(0o755)
   process=None
   try:
    started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    argv=[str(exe),'--list'];assert argv[1:]==['--list']
    process=subprocess.Popen(argv,cwd=c.HERE/'candidate',stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    try:stdout,stderr=process.communicate(timeout=30)
    except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);stdout,stderr=process.communicate();raise
    left=group_members(process.pid);assert not left
    c.save(attempt/'list-stdout.gz',gzip.compress(stdout,mtime=0));c.save(attempt/'list-stderr.gz',gzip.compress(stderr,mtime=0))
    assert process.returncode==0 and not stderr
    assert exe.read_bytes()==raw
    tests=[line[:-6]for line in stdout.decode().splitlines()if line.endswith(': test')]
    lifecycle=[test for test in tests if '::swift_lifecycle_sl'in test]
    assert len(lifecycle)==23 and len(set(lifecycle))==23
    for number in range(1,24):assert sum(f'::swift_lifecycle_sl{number:02d}_'in test for test in lifecycle)==1
    record={'context':cfg,'attempt':str(attempt.relative_to(c.HERE)),'sourceClosure':json.loads((attempt/'command.json').read_text())['sourceClosure'],'executableSHA256':binding['sha256'],'executableBytes':len(raw),'cargoArtifact':artifact,'argv':argv,'exitCode':process.returncode,'processGroup':process.pid,'remainingGroup':left,'startedUTC':started,'finishedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'stdoutSHA256':c.sha(stdout),'stderrSHA256':c.sha(stderr),'allTestCount':len(tests),'lifecycleTests':lifecycle,'listOnly':True,'testBodiesExecuted':0,'vmExecutions':0}
    c.save(attempt/'list-identity.json',record);records.append(record);c.save(c.HERE/'test-inventories.json',records)
   finally:
    if process is not None:
     left=group_members(process.pid)
     if left:os.killpg(process.pid,signal.SIGKILL)
     assert not group_members(process.pid)
    holders=subprocess.run(['/usr/sbin/lsof','-nP','+D',str(scratch)],capture_output=True)
    assert holders.returncode==1 and not holders.stdout
    shutil.rmtree(scratch);c.save(attempt/'list-cleanup.json',{'scratch':str(scratch),'removed':not scratch.exists(),'holderCheckEmpty':True,'remainingGroup':[],'filesRemoved':1,'logicalBytesRemoved':len(raw),'testBodiesExecuted':0})
 print('Four exact binaries list all23 lifecycle test identities; no test body executed',flush=True)
if __name__=='__main__':main()
