#!/usr/bin/env python3
"""Independent source/host review. No native process or instance operation."""
import datetime
import hashlib
import json
import os
import pathlib
import platform
import subprocess
import sys
import time

HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PACKET=ROOT/'verification/apple-toggle-keyboard-full-case-preparation-v3'
EXPECTED='2d600f0289324591cfab82b3ff3d0d987dcdfce9e081a0ff2571d47d6c844039'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
write=lambda p,v:p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')

def main():
    assert not (HERE/'review-seal.json').exists(), 'A sealed independent review is immutable'
    assert sha(PACKET/'packet-seal.json')==EXPECTED
    inputs=json.loads((PACKET/'packet-seal.json').read_bytes())['files']
    before={name:sha(ROOT/name) for name in inputs}
    assert before==inputs
    before['verification/apple-toggle-keyboard-full-case-preparation-v3/packet-seal.json']=EXPECTED
    write(HERE/'producer-inputs-before.json',before)
    rows=[]
    selected=json.loads((PACKET/'runtime-selection.json').read_bytes())
    probes=[
        ('verify',[sys.executable,'-B',str(PACKET/'run.py'),'verify']),
        ('verify-isolated',[sys.executable,'-B',str(PACKET/'verify_isolated.py')]),
        ('imports',[sys.executable,'-B',str(HERE/'controls.py'),'imports']),
        ('preloaded-durable',[sys.executable,'-B',str(HERE/'controls.py'),'preloaded-durable']),
        ('retained-keyboard',[sys.executable,'-B',str(HERE/'controls.py'),'retained-keyboard']),
        ('retained-adapters',[sys.executable,'-B',str(HERE/'controls.py'),'retained-adapters']),
        ('controls',[sys.executable,'-B',str(HERE/'controls.py'),'controls']),
        ('repair-controls',[sys.executable,'-B',str(HERE/'repair_controls.py'),'support']),
        ('allocation-probe',[sys.executable,'-B',str(HERE/'allocation_probe.py'),'support']),
        ('allocation-adjacent',[sys.executable,'-B',str(HERE/'allocation_adjacent.py'),'support']),
    ]+[(('preload-alias-'+alias),[sys.executable,'-B',str(HERE/'controls.py'),'preload:'+alias]) for alias in selected['moduleAliases']]
    for name,argv in probes:
        started=time.monotonic()
        p=subprocess.run(argv,cwd=ROOT,text=True,capture_output=True,timeout=60)
        out=HERE/(name+'.stdout');err=HERE/(name+'.stderr')
        out.write_text(p.stdout);err.write_text(p.stderr)
        rows.append(dict(name=name,argv=argv,cwd=str(ROOT),exitCode=p.returncode,
            elapsedSeconds=time.monotonic()-started,stdoutSHA256=sha(out),stderrSHA256=sha(err)))
        print(name,p.returncode,flush=True)
    after={name:sha(ROOT/name) for name in before}
    write(HERE/'producer-inputs-after.json',after)
    assert after==before,'Producer packet changed during independent review'
    write(HERE/'commands.json',dict(schema=1,observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        commands=rows,allCommandsSucceeded=all(r['exitCode']==0 for r in rows),
        python=sys.version,executable=str(pathlib.Path(sys.executable).resolve()),
        executableSHA256=sha(pathlib.Path(sys.executable).resolve()),platform=platform.platform(),
        producerSealSHA256=EXPECTED,producerSealedFiles=len(inputs),producerInputsUnchanged=True,
        reviewSources={str(p.relative_to(HERE)):sha(p) for p in [HERE/'review.py',HERE/'controls.py',HERE/'repair_controls.py',HERE/'allocation_probe.py',HERE/'allocation_adjacent.py']},
        nativeCompiled=False,nativeExecuted=False,nativeInstancesQueried=False,physicalPhones='disconnected-deferred',gaAccepted=False))
    assert all(r['exitCode']==0 for r in rows)

if __name__=='__main__':main()
