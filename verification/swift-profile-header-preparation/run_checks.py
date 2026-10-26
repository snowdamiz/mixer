"""Execute only the authored offline design controls, retaining exact output."""
from pathlib import Path
import datetime, hashlib, json, os, subprocess, sys, time
P=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
cmd=[sys.executable,'-B',str(P/'test_design.py'),'-v']
start=time.monotonic();at=datetime.datetime.now(datetime.timezone.utc).isoformat()
env=dict(os.environ);env['PYTHONDONTWRITEBYTECODE']='1'
r=subprocess.run(cmd,cwd=P,env=env,capture_output=True,timeout=60)
(P/'checks.stdout').write_bytes(r.stdout);(P/'checks.stderr').write_bytes(r.stderr)
files={n:{'bytes':len((P/n).read_bytes()),'sha256':sha((P/n).read_bytes())}for n in ['test_design.py','run_checks.py','contract.json','closure-comparison.json','input-manifest.json','additional-inputs.json','acceptance-input.json']}
result={'schema':1,'at':at,'argv':cmd,'cwd':str(P),'environment_added':{'PYTHONDONTWRITEBYTECODE':'1'},'python_executable':sys.executable,'python_executable_sha256':sha(Path(sys.executable).resolve().read_bytes()),'python':sys.version,'source_revision_context':json.loads((P/'environment.json').read_text())['commands'][0]['stdout'].strip(),'canonical_tree_sha256':json.loads((P/'closure-comparison.json').read_text())['canonical_tree_sha256'],'inputs_and_authored_checks':files,'elapsed_seconds':time.monotonic()-start,'exit_code':r.returncode,'stdout':{'bytes':len(r.stdout),'sha256':sha(r.stdout)},'stderr':{'bytes':len(r.stderr),'sha256':sha(r.stderr)},'scope':'32 offline source/arithmetic/encoding design controls only; no product import/compile/run, runtime/layout/custody/accounting acceptance, native/capture/process inventory, Git mutation or103-command replay','timeout_seconds':60,'all_authority_flags':False}
(P/'checks-receipt.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps({'exit_code':r.returncode,'elapsed_seconds':result['elapsed_seconds'],'stdout_bytes':len(r.stdout),'stderr_bytes':len(r.stderr),'scope':result['scope']}))
print(r.stderr.decode()[-2200:]);raise SystemExit(r.returncode)
