"""One-shot finite logical-action proposal capture; never runs an engine."""
from pathlib import Path
import hashlib,json,platform,subprocess,sys,time
HERE=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    assert not (HERE/'seal.json').exists()
    argv=[sys.executable,'-B',str(HERE/'check.py')];start=time.monotonic()
    result=subprocess.run(argv,capture_output=True,timeout=10)
    (HERE/'check.stdout').write_bytes(result.stdout);(HERE/'check.stderr').write_bytes(result.stderr)
    (HERE/'command.json').write_text(json.dumps({'argv':argv,'python_version':platform.python_version(),'script_sha256':sha((HERE/'check.py').read_bytes()),'exit_code':result.returncode,'elapsed_seconds':time.monotonic()-start,'stdout_sha256':sha(result.stdout),'stderr_sha256':sha(result.stderr),'scope':'Finite source logical-action assertions only; no engine, writer, native or UI execution'},indent=2)+'\n')
    result.check_returncode()
    members=[]
    for p in sorted(HERE.rglob('*')):
        if p.is_file():members.append({'path':p.relative_to(HERE).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())})
    seal={'schema':1,'member_count':len(members),'member_bytes':sum(m['bytes'] for m in members),'members':members,'tree_sha256':sha(json.dumps(members,sort_keys=True,separators=(',',':')).encode()),'scope':'Proposed exact authority constructor work delta; independent review and integrated admission pending'}
    (HERE/'seal.json').write_text(json.dumps(seal,indent=2)+'\n');print(json.dumps({'members':len(members),'seal_sha256':sha((HERE/'seal.json').read_bytes())}))
if __name__=='__main__':main()
