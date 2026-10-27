#!/usr/bin/env python3
"""Run only named finite packet utilities, preserving commands and outputs."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    assert not (HERE/'seal.json').exists()
    records=[]
    folder=HERE/'pure-outputs'
    folder.mkdir(exist_ok=False)
    for name in ['verify_inputs.py','finalize_inventory.py','ordering_model.py','audit_packet.py']:
        script=HERE/name
        argv=[sys.executable,str(script)]
        env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'}
        started=time.monotonic()
        result=subprocess.run(argv,cwd=ROOT,env=env,capture_output=True,timeout=30)
        (folder/(name+'.stdout')).write_bytes(result.stdout)
        (folder/(name+'.stderr')).write_bytes(result.stderr)
        records.append(dict(argv=argv,cwd=str(ROOT),environment=env,exit_code=result.returncode,
                            elapsed_seconds=time.monotonic()-started,child_waited=True,
                            python_version=sys.version,python_executable_sha256=sha(Path(sys.executable).read_bytes()),
                            script_sha256=sha(script.read_bytes()),
                            scope='pure finite Python/retained artifact analysis only; no product import/dispatch or compiler invocation',
                            output={key:dict(bytes=len(value),sha256=sha(value)) for key,value in [('stdout',result.stdout),('stderr',result.stderr)]}))
        if result.returncode:
            print(result.stderr.decode(),end='')
            break
    (HERE/'pure-command-receipts.json').write_text(json.dumps(dict(schema=1,
        at=datetime.datetime.now(datetime.timezone.utc).isoformat(),commands=records),indent=2,sort_keys=True)+'\n')
    assert len(records)==4 and all(r['exit_code']==0 for r in records)
    print(json.dumps(dict(pure_commands_passed=4,product_executables_executed=0)))


if __name__=='__main__':
    main()
