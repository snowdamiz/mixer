"""Build and execute an explicitly closed V5 packet; preserve every attempt."""
import argparse
import datetime
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
ROOT=BASE.parents[1]
SOURCES=['bind_inputs.py','derive_v5.py','prepare.py','importer.py','adapter.py','test_importer.py','auxiliary_inventory.py',
         'test_repair.py','replay_review.py','frozen_inputs.py','replay_v3_review.py','replay_precision.py','test_precision.py',
         'replay_v4_review.py','test_v5.py','execute_controls.py','verify_host.py','freeze.py','child-guard/sitecustomize.py',
         'input-bindings.json','namespace-adaptation.patch','namespace-sources.json','v4-to-v5-repair.patch','supplemental-inputs.json']
sha=lambda raw:hashlib.sha256(raw).hexdigest()
stable=lambda value:(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def row(path):
    assert path.resolve()==path and path.is_file() and not path.is_symlink(),path
    raw=path.read_bytes();return {'kind':'file','mode':stat.S_IMODE(path.stat().st_mode),'bytes':len(raw),'sha256':sha(raw)}

def packet(out):
    meta=json.loads((BASE/'input-bindings.json').read_bytes())
    assert row(BASE/'frozen-inputs.tar.gz')==meta['archive']
    payloads={};rows={}
    with tarfile.open(BASE/'frozen-inputs.tar.gz','r:gz') as source:
        members=source.getmembers();assert len(members)==len(meta['bindings'])
        by_storage={stored:name for name,stored in meta['storage'].items()}
        assert set(by_storage)=={m.name for m in members}
        for member in members:
            assert member.isfile() and not member.issym() and not member.islnk()
            raw=source.extractfile(member).read();name=by_storage[member.name];expected=meta['bindings'][name]
            assert {'kind':'file','mode':member.mode,'bytes':len(raw),'sha256':sha(raw)}==expected
            payloads[member.name]=raw;rows[member.name]=expected
    for name in SOURCES:
        path=BASE/name;stored=str(path.relative_to(ROOT));payloads[stored]=path.read_bytes();rows[stored]=row(path)
    doc=ROOT/'docs/apple-focus-reference-runtime-v5.md'
    payloads[str(doc.relative_to(ROOT))]=doc.read_bytes();rows[str(doc.relative_to(ROOT))]=row(doc)
    path=out/'closed-packet.tar.gz'
    with path.open('xb') as stream,gzip.GzipFile(fileobj=stream,mode='wb',mtime=0,filename='') as zipped,tarfile.open(fileobj=zipped,mode='w') as target:
        for name in sorted(payloads):
            raw=payloads[name];member=tarfile.TarInfo(name);member.size=len(raw);member.mode=rows[name]['mode'];member.mtime=0
            target.addfile(member,io.BytesIO(raw))
    manifest={'schema':'mixer.apple-focus-reference-runtime-v5-closed-packet.1','members':rows,'memberTreeSHA256':sha(stable(rows)),
              'archive':row(path),'immutableInputFiles':len(meta['bindings']),'explicitlyEnumerated':True,
              'sourceInputToolOutputScope':'Frozen source/input/tool bytes and selected V5 implementation; outputs are separately archived after execution'}
    (out/'closed-packet-manifest.json').write_bytes(stable(manifest))
    return manifest

def main(attempt):
    assert attempt>0
    out=BASE/('host-attempt-'+str(attempt));out.mkdir()
    started=time.monotonic();manifest=packet(out)
    scratch=Path(tempfile.mkdtemp(prefix='.scratch-v5-'+str(attempt)+'-',dir=BASE));repo=scratch/'repo';repo.mkdir()
    result=None;failure=None;command=None
    try:
        with tarfile.open(out/'closed-packet.tar.gz','r:gz') as tar:
            for member in tar.getmembers():
                name=Path(member.name);assert not name.is_absolute() and '..' not in name.parts
                assert member.isfile() and not member.issym() and not member.islnk()
                raw=tar.extractfile(member).read();path=repo/name;path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(raw);path.chmod(member.mode);assert row(path)==manifest['members'][member.name]
        (repo/'closed-v5-root.json').write_bytes(stable({'packetTreeSHA256':manifest['memberTreeSHA256'],'noWorkspaceFallback':True}))
        execute=repo/'verification/apple-focus-reference-runtime-v5/execute_controls.py'
        output=execute.parent/'controls-output'
        command=[sys.executable,'-B',str(execute),'--output',str(output)]
        env=dict(os.environ,MIXER_V5_CLOSED_ROOT=str(repo));env.pop('PYTHONPATH',None)
        with (out/'stdout.log').open('w') as stdout,(out/'stderr.log').open('w') as stderr:
            result=subprocess.run(command,cwd=repo,env=env,stdout=stdout,stderr=stderr,timeout=360)
        if output.exists():shutil.copytree(output,out/'controls')
    except BaseException:failure=traceback.format_exc()
    finally:
        shutil.rmtree(scratch)
    generated=out/'controls/receipt.json'
    control=json.loads(generated.read_bytes()) if generated.exists() else None
    outputs={str(p.relative_to(out)):row(p) for p in sorted(out.rglob('*')) if p.is_file()}
    receipt={'schema':'mixer.apple-focus-reference-runtime-v5-isolated-host-attempt.1',
             'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,'-B',str(Path(__file__).resolve()),'--attempt',str(attempt)],
             'executedCommand':command,'python':sys.version,'pythonExecutable':str(Path(sys.executable).resolve()),'hostUname':list(os.uname()),
             'sourceRevisionLabel':'ba9ad4372f94463ba4d363cdfd76dd565c96413f','sourceRevisionMeaning':'Inherited compile label only; exact closed tree hashes define this source; no Git query',
             'elapsedSeconds':time.monotonic()-started,'closedPacketManifest':row(out/'closed-packet-manifest.json'),
             'closedPacketTreeSHA256':manifest['memberTreeSHA256'],'filesCopied':len(manifest['members']),
             'exitCode':result.returncode if result is not None else None,'exception':failure,
             'passed':result is not None and result.returncode==0 and control is not None and control['passed'],
             'controlsReceipt':row(generated) if generated.exists() else None,'outputs':outputs,'outputTreeSHA256':sha(stable(outputs)),
             'cleanup':{'ownedIsolatedScratchAbsent':not scratch.exists(),'nativeCommandsInvoked':0,'nativeInstancesCreatedOrQueried':0,
                        'servicesStarted':0,'otherProjectsTouched':False},'nativeExecuted':False,'compileRerun':False,'uiOrCapturePerformed':False,
             'gitMutationPerformed':False,'runtimeSelected':False,'independentV5ReviewPending':True,'physicalPhones':'disconnected-deferred',
             'runPassed':False,'nativeKeyboardQualification':False,'carrierAccepted':False,'gaAccepted':False}
    (out/'receipt.json').write_bytes(stable(receipt))
    print(json.dumps({'passed':receipt['passed'],'exitCode':receipt['exitCode'],'exception':failure,'receiptSHA256':sha((out/'receipt.json').read_bytes()),'cleanup':receipt['cleanup']},sort_keys=True))
    if not receipt['passed']:raise SystemExit(1)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--attempt',required=True,type=int);main(p.parse_args().attempt)
