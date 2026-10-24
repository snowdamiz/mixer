#!/usr/bin/env python3
"""Uncalled four-context production owner-entry type checks; no guest/test run."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
TOOL=Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin')
PINS={'rustc':'dd6f58440b3418aa9157ae3f05d71eecff741ca41bc4eec120e7e8f2d933b9a0','cargo':'fc7aa5077deca8abc0651f329e8ec1d968f520e996a93b428f9935014362b382'}
def sha(data):return hashlib.sha256(data).hexdigest()
def encoded(value):return (json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(value if isinstance(value,bytes) else encoded(value))
def manifest(tree):return {str(p.relative_to(tree)):sha(p.read_bytes()) for p in sorted(tree.rglob('*')) if p.is_file()}
def group_members(group):
    result=subprocess.run(['/bin/ps','-axo','pid=,pgid=,command='],check=True,capture_output=True,text=True)
    return [line.strip() for line in result.stdout.splitlines() if len(line.split(None,2))>=2 and line.split(None,2)[1]==str(group)]
def main():
    attempt=HERE/'attempts'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');attempt.mkdir(parents=True)
    baseline=json.loads((HERE/'baseline-manifest.json').read_bytes())
    for name,pin in baseline.items():assert sha((ROOT/'vm'/name).read_bytes())==pin,name
    for name,pin in PINS.items():assert sha((TOOL/name).read_bytes())==pin,name
    assert not any(os.environ.get(k) for k in ['DYLD_INSERT_LIBRARIES','LD_PRELOAD','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS'])
    candidate=HERE/'candidate';source_manifest=manifest(candidate)
    changed=[name for name,pin in source_manifest.items() if baseline.get(name)!=pin]
    assert set(changed)<=set(['src/experimental_swift_reactor/memory_growth_operations.rs','src/experimental_swift_reactor/lifecycle.rs','src/experimental_swift_reactor/lifecycle_tests.rs','src/experimental_swift_reactor/execution.rs'])
    assert set(baseline)<=set(source_manifest)
    write(attempt/'candidate-manifest.json',source_manifest)
    with tarfile.open(attempt/'candidate-source.tar.gz','w:gz') as packed:
        for name in source_manifest:packed.add(candidate/name,arcname=name,recursive=False)
    scratch=Path(tempfile.mkdtemp(prefix='mixer-lifecycle-implementation-')).resolve()
    source=scratch/'source';shutil.copytree(candidate,source)
    commands=[]
    receipt={'schema':'mixer.swift-lifecycle.owner-entry-compile.1','sourceRevisionContext':'fb531a185b7b020fe3e17d6e24d78a0977352c8d','candidateClosure':sha(encoded(source_manifest)),'candidateFileCount':len(source_manifest),'baselineClosure':sha(encoded(baseline)),'changedFiles':changed,'toolSHA256':PINS,'commands':commands,'scratch':str(scratch),'vmExecutions':0,'nativeInstancesCreated':0,'targetArtifactRead':False,'accountingAccepted':False,'runtimeSelected':False,'scope':'Uncalled full original-owner request/preparation/error/retained-result compiler proof only.'}
    def run(label,argv,target=None):
        before=manifest(source)
        env={k:v for k,v in os.environ.items() if not k.startswith(('CARGO_','RUST'))}
        env.update(PATH=str(TOOL)+':/usr/bin:/bin:/usr/sbin:/sbin',RUSTC=str(TOOL/'rustc'),CARGO_INCREMENTAL='0',CARGO_NET_OFFLINE='true')
        if target:env['CARGO_TARGET_DIR']=str(target)
        started=datetime.now(timezone.utc).isoformat()
        process=subprocess.Popen(argv,cwd=source,env=env,start_new_session=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        timed_out=False
        try:output,_=process.communicate(timeout=180)
        except subprocess.TimeoutExpired:
            timed_out=True;os.killpg(process.pid,signal.SIGKILL);output,_=process.communicate()
        remaining=group_members(process.pid)
        if remaining:os.killpg(process.pid,signal.SIGKILL);remaining=group_members(process.pid)
        write(attempt/(label+'.log.gz'),gzip.compress(output,mtime=0))
        row={'label':label,'argv':argv,'cwd':str(source),'target':str(target) if target else None,'startedUTC':started,'finishedUTC':datetime.now(timezone.utc).isoformat(),'exitCode':process.returncode,'timedOut':timed_out,'processGroup':process.pid,'remainingGroup':remaining,'sourceBefore':sha(encoded(before)),'sourceAfter':sha(encoded(manifest(source))),'sourceUnchanged':before==manifest(source),'outputSHA256':sha(output),'log':label+'.log.gz'}
        commands.append(row);write(attempt/'commands.json',commands)
        assert not timed_out and not remaining and row['sourceUnchanged'],row
        print(label,process.returncode,flush=True)
        return output
    try:
        run('rustc-version',[str(TOOL/'rustc'),'--version','--verbose'])
        run('cargo-version',[str(TOOL/'cargo'),'--version'])
        run('python-version',[sys.executable,'--version'])
        for features in ['swift','all']:
            for release in [False,True]:
                label=features+('-release' if release else '-debug')
                argv=[str(TOOL/'cargo'),'check','--lib','--locked','--offline','--no-default-features']
                argv+=['--all-features'] if features=='all' else ['--features','experimental-swift-reactor']
                if release:argv+=['--release']
                run(label,argv,scratch/('target-'+label))
        receipt['fullOwnerEntryBorrowRouteProven']=all(row['exitCode']==0 for row in commands if row['target'])
        assert manifest(candidate)==source_manifest
        assert all(sha((ROOT/'vm'/name).read_bytes())==pin for name,pin in baseline.items())
        receipt['liveBaselineRecheckedAfter']=True
    except BaseException as error:
        receipt['failure']={'type':type(error).__name__,'message':str(error)}
        raise
    finally:
        holders=subprocess.run(['/usr/sbin/lsof','-nP','+D',str(scratch)],capture_output=True)
        write(attempt/'holders.log',holders.stdout+holders.stderr)
        remaining={str(row['processGroup']):group_members(row['processGroup']) for row in commands}
        cleanup={'scratch':str(scratch),'holderCheckExitCode':holders.returncode,'holderCheckEmpty':holders.returncode==1 and not holders.stdout,'remainingCommandGroups':remaining,'groupsEmpty':not any(remaining.values())}
        if cleanup['holderCheckEmpty'] and cleanup['groupsEmpty']:
            files=[p for p in scratch.rglob('*') if p.is_file()]
            cleanup.update(filesRemoved=len(files),logicalBytesRemoved=sum(p.stat().st_size for p in files));shutil.rmtree(scratch)
        cleanup['ownedScratchRemoved']=not scratch.exists();write(attempt/'cleanup.json',cleanup)
        receipt['cleanupPassed']=cleanup['ownedScratchRemoved'] and cleanup['holderCheckEmpty'] and cleanup['groupsEmpty'];receipt['finishedUTC']=datetime.now(timezone.utc).isoformat();write(attempt/'receipt.json',receipt)
        print(attempt,flush=True)
if __name__=='__main__':main()
