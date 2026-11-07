#!/usr/bin/env python3
"""Independent, distinct identity/API refusal fixture; actual compilation beneath wrapper."""
import json
from pathlib import Path
import subprocess
import sys

ROUND=Path('REPLACED_ROUND')
MODE='REPLACED_MODE'
TOOLCHAIN=ROUND/('blackbox-'+MODE+'-toolchain')
RECORDS=ROUND/'blackbox-records'
REAL=Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin/rustc')
args=sys.argv[1:]
if args==['--print','sysroot']:print(TOOLCHAIN);sys.exit(0)
result=subprocess.run([str(REAL),*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
stdout,stderr=result.stdout,result.stderr
if args==['--version','--verbose'] and MODE=='identity':
    (RECORDS/'identity-original-version.stdout').write_bytes(stdout)
    stdout=stdout.replace(b'host: aarch64-apple-darwin\n',b'host: x86_64-unknown-linux-gnu\nhost: aarch64-apple-darwin\n')
if '--error-format=json' in args and MODE=='api':
    source=next(Path(x) for x in args if x.endswith('.rs'))
    (RECORDS/(source.stem+'.original.stderr')).write_bytes(stderr)
    changed=[];spans=[]
    for line in stderr.splitlines():
        diagnostic=json.loads(line)
        if diagnostic.get('level')=='error' and diagnostic.get('code'):
            for span in diagnostic.get('spans',[]):
                if span.get('is_primary'):
                    spans.append({'original':dict(span),'altered_source_bytes':'u'})
                    span.update(byte_start=0,byte_end=1,line_start=1,line_end=1,column_start=1,column_end=2)
        changed.append(json.dumps(diagnostic).encode())
    stderr=b'\n'.join(changed)+b'\n'
    (RECORDS/(source.stem+'.changes.json')).write_text(json.dumps(spans,indent=2,sort_keys=True)+'\n')
sys.stdout.buffer.write(stdout);sys.stderr.buffer.write(stderr);sys.exit(result.returncode)
