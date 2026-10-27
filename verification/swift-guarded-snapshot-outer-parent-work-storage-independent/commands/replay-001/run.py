#!/usr/bin/env python3
"""Owned-output Python command recorder. No compiler/native processes."""
import datetime, hashlib, json, os, platform, subprocess, sys, time
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
C=ROOT/'verification/swift-guarded-snapshot-outer-parent-work-storage'
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    mode=sys.argv[1] if len(sys.argv)>1 else 'review'
    i=1
    while (HERE/'commands'/f'{mode}-{i:03}').exists():i+=1
    folder=HERE/'commands'/f'{mode}-{i:03}';folder.mkdir(parents=True)
    if mode=='review':argv=[sys.executable,'-B',str(HERE/'review.py')];cwd=ROOT
    elif mode=='controls':argv=[sys.executable,'-B',str(HERE/'controls.py')];cwd=ROOT
    elif mode=='replay':argv=[sys.executable,'-B',str(C/'derive.py'),'--check'];cwd=ROOT
    elif mode=='producer-tests':argv=[sys.executable,'-B','-m','unittest','test_model','-v'];cwd=C
    else:raise ValueError(mode)
    for p in [HERE/'run.py',HERE/'review.py',HERE/'controls.py']:
        if p.exists():(folder/p.name).write_bytes(p.read_bytes())
    start=time.monotonic()
    result=subprocess.run(argv,cwd=cwd,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,timeout=60)
    for name,b in [('stdout',result.stdout),('stderr',result.stderr)]:(folder/name).write_bytes(b)
    receipt=dict(schema=1,at=datetime.datetime.now(datetime.timezone.utc).isoformat(),argv=argv,cwd=str(cwd),
       python_executable=sys.executable,python_version=sys.version,platform=platform.platform(),
       candidate_tree='27deefde4b492bab2e2d5a28da9ae749cc4ae51094e0fca30154d044097988a3',
       source_revision_from_frozen_receipt='a32d056355ec2f417e9ef7a73788b420176377b6',
       environment_delta={'PYTHONDONTWRITEBYTECODE':'1'},exit_code=result.returncode,
       elapsed_seconds=time.monotonic()-start,
       stdout=dict(bytes=len(result.stdout),sha256=sha(result.stdout)),stderr=dict(bytes=len(result.stderr),sha256=sha(result.stderr)),
       scope='Offline source/MIR reconstruction or pure Python controls; no compiler/product/native/runtime/UI/capture/Git/root metadata operation',
       cleanup=dict(children_completed=True,compiler_children_started=0,native_started=False,scratch_created=False,outside_owned_writes=False,global_process_inventory=False))
    (folder/'receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print(json.dumps(dict(command=mode,attempt=i,exit_code=result.returncode,receipt=str(folder/'receipt.json'))))
    if result.stdout:print(result.stdout.decode())
    if result.stderr:print(result.stderr.decode())
    return result.returncode
if __name__=='__main__':sys.exit(main())
