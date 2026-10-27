#!/usr/bin/env python3
"""Owned recorder for read-only offline review children; no producer recorder."""
import datetime, hashlib, json, os, pathlib, subprocess, sys, time
D = pathlib.Path(__file__).resolve().parent
R = D.parents[1]
P = R / 'verification/swift-guarded-snapshot-string-provenance'
def digest(raw): return hashlib.sha256(raw).hexdigest()
def main():
    requested = sys.argv[1:]
    assert requested
    script = pathlib.Path(requested[0]).resolve()
    assert script.parent == D or (script.parent == P and script.name in ('derive.py', 'check.py', 'test_provenance.py'))
    assert script.name != 'derive.py' or requested[1:] == ['--check']
    assert not (D/'seal.json').exists(), 'packet already frozen'
    history = D/'commands'; history.mkdir(exist_ok=True)
    attempt = history / ('attempt-%03d' % (1+len(list(history.glob('attempt-*')))))
    attempt.mkdir()
    for f in sorted(D.glob('*.py')): (attempt/('review-'+f.name)).write_bytes(f.read_bytes())
    if script.parent == P:
        for f in sorted(P.glob('*.py')): (attempt/('producer-'+f.name)).write_bytes(f.read_bytes())
    argv=[sys.executable,'-B',str(script),*requested[1:]]
    environment=dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    started=datetime.datetime.now(datetime.timezone.utc).isoformat(); t=time.monotonic()
    child=subprocess.run(argv,cwd=R,env=environment,capture_output=True,timeout=55)
    for name,raw in [('stdout',child.stdout),('stderr',child.stderr)]: (attempt/name).write_bytes(raw)
    receipt={'schema':1,'at':started,'argv':argv,'cwd':str(R),'python_version':sys.version,
        'python_executable':sys.executable,'python_sha256':digest(pathlib.Path(sys.executable).read_bytes()),
        'source_revision':'frozen-source146-exacttree-690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185',
        'script_sha256':digest(script.read_bytes()),'exit_code':child.returncode,'waited_child':True,
        'elapsed_seconds':time.monotonic()-t,'outputs':{n:{'bytes':len(b),'sha256':digest(b)} for n,b in [('stdout',child.stdout),('stderr',child.stderr)]},
        'PYTHONDONTWRITEBYTECODE':'1','compiler_or_product_execution':False,'native_or_UI_or_capture':False,
        'Git_or_global_process_inventory':False,'only_owned_packet_written':True}
    (attempt/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(child.stdout.decode(),end='');print(child.stderr.decode(),end='',file=sys.stderr)
    print(json.dumps({'attempt':str(attempt.relative_to(R)),'exit_code':child.returncode}))
    return child.returncode
if __name__=='__main__': sys.exit(main())
