"""Bounded Python-only runner; preserve failures before any repair."""
import datetime,hashlib,json,os,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
def main():
    label=sys.argv[1];argv=[sys.executable,'-B',str(HERE/sys.argv[2]),*sys.argv[3:]]
    d=HERE/'commands'/label
    if d.exists():raise SystemExit('command label already exists; preserve prior attempt')
    d.mkdir(parents=True)
    sources=[]
    for p in sorted(HERE.glob('*.py')):
        data=p.read_bytes();(d/p.name).write_bytes(data)
        sources.append({'path':p.name,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
    start=time.monotonic();at=datetime.datetime.now(datetime.timezone.utc).isoformat()
    with (d/'stdout').open('wb') as out,(d/'stderr').open('wb') as err:
        proc=subprocess.Popen(argv,cwd=HERE,stdout=out,stderr=err,start_new_session=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
        try:code=proc.wait(timeout=45)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,15)
            try:code=proc.wait(timeout=3)
            except subprocess.TimeoutExpired:os.killpg(proc.pid,9);code=proc.wait(timeout=3)
    receipt={'schema':1,'at':at,'argv':argv,'cwd':str(HERE),'python':sys.version,'executable':sys.executable,
      'exit_code':code,'elapsed_seconds':time.monotonic()-start,'child_pid':proc.pid,'waited':True,
      'source_tree_sha256':'690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185',
      'source_files':sources,'scope':'pure host source/provenance/arithmetic controls; no compiler/product/native runtime',
      'stdout_sha256':hashlib.sha256((d/'stdout').read_bytes()).hexdigest(),
      'stderr_sha256':hashlib.sha256((d/'stderr').read_bytes()).hexdigest()}
    try:os.killpg(proc.pid,0);receipt['owned_process_group_absent']=False
    except ProcessLookupError:receipt['owned_process_group_absent']=True
    (d/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print((d/'stdout').read_text(),end='');print((d/'stderr').read_text(),end='',file=sys.stderr)
    print(json.dumps({'command':label,'exit_code':code,'waited':True,'owned_process_group_absent':receipt['owned_process_group_absent']}))
    raise SystemExit(code)
if __name__=='__main__':main()
