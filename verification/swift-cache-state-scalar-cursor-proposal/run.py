#!/usr/bin/env python3
"""Run only this packet's bounded Python checker, retaining exact evidence."""
import datetime,hashlib,json,pathlib,subprocess,sys
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
now=datetime.datetime.now(datetime.timezone.utc);out=HERE/'commands'/now.strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True)
script=(HERE/'check.py').read_bytes();(out/'checker-source.py.txt').write_bytes(script)
rows=[]
for name,argv in [('normal',[sys.executable,'-B',str(HERE/'check.py')]),('optimized',[sys.executable,'-O','-B',str(HERE/'check.py')])]:
 start=datetime.datetime.now(datetime.timezone.utc);r=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=60)
 (out/(name+'.stdout')).write_bytes(r.stdout);(out/(name+'.stderr')).write_bytes(r.stderr)
 rows.append(dict(name=name,argv=argv,cwd=str(ROOT),started=start.isoformat(),finished=datetime.datetime.now(datetime.timezone.utc).isoformat(),exit_code=r.returncode,stdout_bytes=len(r.stdout),stderr_bytes=len(r.stderr),stdout_sha256=hashlib.sha256(r.stdout).hexdigest(),stderr_sha256=hashlib.sha256(r.stderr).hexdigest()))
 if r.returncode:print(r.stderr.decode(),file=sys.stderr)
receipt=dict(schema=1,python=sys.version,executable=sys.executable,checker_sha256=hashlib.sha256(script).hexdigest(),source_sha256=hashlib.sha256((HERE/'source/cache_state.rs.txt').read_bytes()).hexdigest(),input_tree_digest=json.loads((HERE/'input-bindings.json').read_text())['input_tree_digest'],commands=rows,owned_children='two sequential bounded Python checker children reaped by subprocess.run',owned_external_products=[],native_capture_process_inventory_or_Git=False)
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');(HERE/'latest-run.json').write_text(json.dumps(dict(receipt=str((out/'receipt.json').relative_to(HERE)),all_passed=all(r['exit_code']==0 for r in rows)),indent=2)+'\n')
print(json.dumps(dict(receipt=str((out/'receipt.json').relative_to(HERE)),all_passed=all(r['exit_code']==0 for r in rows))))
if any(r['exit_code']for r in rows):sys.exit(1)
