"""Verify the immutable V5 closure, replay it once, and retain compact evidence."""
import datetime
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import traceback

BASE=Path(__file__).resolve().parent
REPO=BASE.parents[1]
PRODUCER=REPO/'verification/apple-focus-reference-runtime-v5'
EXPECTED='3d22fa59106d6bc6c585ed53d720b31f1bbe50f8e811cf528758b274918ac02b'
stable=lambda v:(json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
sha=lambda b:hashlib.sha256(b).hexdigest()
def row(p):
    info=p.lstat();assert stat.S_ISREG(info.st_mode) and not p.is_symlink()
    raw=p.read_bytes();return dict(kind='file',mode=stat.S_IMODE(info.st_mode),bytes=len(raw),sha256=sha(raw))
def closure():
    assert sha((PRODUCER/'handoff.json').read_bytes())==EXPECTED
    h=json.loads((PRODUCER/'handoff.json').read_bytes())
    for n,v in h['members'].items():assert row(REPO/n)==v,n
    assert sha(stable(h['members']))==h['memberTreeSHA256']
    return {'handoffSHA256':EXPECTED,'memberCount':len(h['members']),'memberTreeSHA256':h['memberTreeSHA256'],'packetSHA256':h['packetSHA256'],'hostReceiptSHA256':h['hostReceiptSHA256']}
def archive_outputs(folder,destination):
    rows={str(p.relative_to(folder)):row(p) for p in sorted(folder.rglob('*')) if p.is_file()}
    with destination.open('xb') as stream,gzip.GzipFile(fileobj=stream,mode='wb',mtime=0,filename='') as z,tarfile.open(fileobj=z,mode='w') as tar:
        for name,record in rows.items():
            raw=(folder/name).read_bytes();m=tarfile.TarInfo(name);m.size=len(raw);m.mode=record['mode'];m.mtime=0;tar.addfile(m,io.BytesIO(raw))
    return {'members':rows,'treeSHA256':sha(stable(rows)),'archive':row(destination)}
def main(attempt,adversaries_only):
    started=time.monotonic();before=closure()
    out=BASE/('attempt-'+str(attempt));out.mkdir()
    source_snapshot=out/'authoring-sources';source_snapshot.mkdir()
    for name in ['run_review.py','guard_bootstrap.py','run_adversaries.py']:shutil.copyfile(BASE/name,source_snapshot/name)
    scratch=Path(tempfile.mkdtemp(prefix='.scratch-independent-v5-',dir=BASE))
    root=scratch/'repo';root.mkdir();commands=[];failure=None;replay=None;adversaries=None
    try:
        manifest=json.loads((PRODUCER/'host-attempt-3/closed-packet-manifest.json').read_bytes())
        archive=PRODUCER/'host-attempt-3/closed-packet.tar.gz'
        assert row(archive)==manifest['archive']
        assert sha(stable(manifest['members']))==manifest['memberTreeSHA256']
        with tarfile.open(archive,'r:gz') as tar:
            members=tar.getmembers();assert len(members)==len(manifest['members'])
            assert {m.name for m in members}==set(manifest['members'])
            for m in members:
                p=Path(m.name);assert not p.is_absolute() and '..' not in p.parts and m.isfile() and not m.issym() and not m.islnk()
                assert not any(w in m.name.lower() for w in ('hosted','catalog','authority-driver','worker-transport'))
                raw=tar.extractfile(m).read();want=manifest['members'][m.name]
                assert {'kind':'file','mode':m.mode,'bytes':len(raw),'sha256':sha(raw)}==want
                target=root/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);target.chmod(m.mode)
        (root/'closed-v5-root.json').write_bytes(stable({'packetTreeSHA256':manifest['memberTreeSHA256'],'noWorkspaceFallback':True,'independentReview':True}))
        own=root/'independent-review';own.mkdir()
        for name in ['guard_bootstrap.py','run_adversaries.py']:shutil.copyfile(BASE/name,own/name)
        target=root/'verification/apple-focus-reference-runtime-v5/execute_controls.py';generated=target.parent/'controls-output'
        env=dict(os.environ,MIXER_V5_CLOSED_ROOT=str(root),MIXER_V5_LIVE_ROOT=str(REPO));env.pop('PYTHONPATH',None)
        jobs=[('independent-adversaries',own/'run_adversaries.py',[])]
        if not adversaries_only:jobs.insert(0,('retained-replay',target,['--output',str(generated)]))
        for label,script,args in jobs:
            command=[sys.executable,'-B',str(own/'guard_bootstrap.py'),str(script)]+args
            with (out/(label+'.stdout.log')).open('w') as stdout,(out/(label+'.stderr.log')).open('w') as stderr:
                result=subprocess.run(command,cwd=root,env=env,stdout=stdout,stderr=stderr,timeout=480)
            commands.append({'label':label,'argv':command,'exitCode':result.returncode})
        if adversaries_only:
            replay=json.loads((BASE/'attempt-1/retained-replay-receipt.json').read_bytes())
        else:
            replay=json.loads((generated/'receipt.json').read_bytes())
            shutil.copyfile(generated/'receipt.json',out/'retained-replay-receipt.json')
            # The immutable historical input archives remain referenced by their hashes;
            # this archive contains only outputs freshly generated by this review.
            outputs=archive_outputs(generated,out/'retained-replay-outputs.tar.gz')
            (out/'retained-replay-output-manifest.json').write_bytes(stable(outputs))
        a=own/'adversary-output';shutil.copytree(a,out/'independent-adversaries')
        adversaries=json.loads((a/'receipt.json').read_bytes())
    except BaseException:failure=traceback.format_exc()
    finally:shutil.rmtree(scratch)
    after=closure()
    receipt={'schema':'mixer.apple-focus-reference-runtime-v5-independent-review.1','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'command':[sys.executable,'-B',str(Path(__file__).resolve()),'--attempt',str(attempt)]+(['--adversaries-only'] if adversaries_only else []),'python':sys.version,'pythonExecutable':str(Path(sys.executable).resolve()),
             'hostUname':list(os.uname()),'elapsedSeconds':time.monotonic()-started,'frozenClosureBefore':before,'frozenClosureAfter':after,
             'sourceRevisionLabel':'ba9ad4372f94463ba4d363cdfd76dd565c96413f','sourceRevisionMeaning':'Inherited label; exact verified closure defines source; no Git query',
             'closedPacketTreeSHA256':manifest['memberTreeSHA256'],'closedPacketArchive':manifest['archive'],'immutableInputArchiveReused':True,
             'commands':commands,'exception':failure,'retainedReplayPassed':bool(replay and replay['passed']),
             'retainedReplayReusedFromAttempt1':adversaries_only,'retainedReplayReceipt':row(BASE/'attempt-1/retained-replay-receipt.json'),
             'authoringSources':{p.name:row(p) for p in source_snapshot.iterdir()},
             'independentAdversaries':adversaries,'nativeSelectionBlocked':True,'acceptedForFreshNativeSelection':False,
             'findings':['V5 dispatch and actual selected adapter use native-run-v4- rather than native-run-v5-'],
             'cleanup':{'ownedScratchAbsent':not scratch.exists(),'producerClosureUnchanged':before==after,'nativeCommandsInvoked':0,'servicesStarted':0,'otherProjectsTouched':False},
             'nativeExecuted':False,'uiOrCapturePerformed':False,'physicalPhones':'disconnected-deferred','gitMutationPerformed':False,'gaAccepted':False}
    (out/'receipt.json').write_bytes(stable(receipt))
    print(json.dumps({k:receipt[k] for k in ['retainedReplayPassed','acceptedForFreshNativeSelection','findings','exception','cleanup']},indent=2))
    assert failure is None

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--attempt',type=int,required=True);parser.add_argument('--adversaries-only',action='store_true')
    args=parser.parse_args();main(args.attempt,args.adversaries_only)
