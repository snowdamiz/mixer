#!/usr/bin/env python3
"""External imports must not expose private attempt or retirement machinery."""
import hashlib,json,os,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    base=HERE/'2026-10-23-candidate-4/receipt.json';r=json.loads(base.read_text())
    common=next(c['command'] for c in r['commands'] if c['name']=='debug-tests-link');common=common[:common.index('-emit-library')]
    out=HERE/'2026-10-23-opacity';out.mkdir(exist_ok=False);rows=[]
    for name,expected,fragment in [('attempt',1,"cannot find type 'CapabilityConcreteAttempt'"),('retirement',1,"cannot find type 'CapabilityConcreteRetirement'"),('public-positive',0,None)]:
        source=HERE/'CompileNegative'/(name+'.swift');command=common+['-typecheck',str(source)]
        result=subprocess.run(command,cwd=ROOT,env=os.environ|{'DEVELOPER_DIR':'/Applications/Xcode.app/Contents/Developer'},stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
        log=out/(name+'.log');log.write_bytes(result.stdout);rows.append(dict(command=command,source=str(source.relative_to(ROOT)),source_sha256=sha(source),exit_code=result.returncode,expected_exit=expected,log=log.name,log_sha256=sha(log)))
        assert result.returncode==expected and (fragment is None or fragment.encode() in result.stdout)
    record=dict(status='passed',base_receipt=dict(path=str(base.relative_to(ROOT)),sha256=sha(base)),commands=rows,driver_sha256=sha(Path(__file__)),scope='External ordinary Swift imports only; no I/O, private tests or authority ingress.')
    (out/'receipt.json').write_text(json.dumps(record,indent=2)+'\n');print('receipt_sha256 '+sha(out/'receipt.json'))
if __name__=='__main__':main()
