#!/usr/bin/env python3
"""Bounded Python-only evidence collection into this owned packet."""
from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys,time
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def run(name,argv):
 folder=HERE/'commands'/name;folder.mkdir(parents=True,exist_ok=True)
 started=time.monotonic()
 proc=subprocess.run(argv,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=55,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
 (folder/'stdout').write_bytes(proc.stdout);(folder/'stderr').write_bytes(proc.stderr)
 value=dict(argv=argv,cwd=str(ROOT),at=datetime.datetime.now(datetime.timezone.utc).isoformat(),exit_code=proc.returncode,elapsed_seconds=time.monotonic()-started,timeout_seconds=55,direct_child_waited=True,stdout=dict(bytes=len(proc.stdout),sha256=sha(proc.stdout)),stderr=dict(bytes=len(proc.stderr),sha256=sha(proc.stderr)),compiler=False,product_runtime=False,native_UI_capture=False,global_process_inventory=False)
 (folder/'receipt.json').write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
 if proc.returncode:raise SystemExit(name+' failed; retained original command output')
 return value
if __name__=='__main__':
 if (HERE/'seal.json').exists():raise SystemExit('frozen packet read-only')
 records=[run('derive',[sys.executable,str(HERE/'derive.py')]),run('pure-controls',[sys.executable,str(HERE/'test_cost.py')])]
 revision=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout.decode().strip()
 own=[dict(path=p.name,bytes=len(p.read_bytes()),sha256=sha(p.read_bytes())) for p in sorted(HERE.glob('*.py'))]
 receipt=dict(schema=1,status='pure-component-proposal-controls-pass',at=datetime.datetime.now(datetime.timezone.utc).isoformat(),python_version=sys.version,python_executable=str(Path(sys.executable).resolve()),python_executable_sha256=sha(Path(sys.executable).resolve().read_bytes()),source_revision=revision,source_tree_sha256='690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185',own_python_sources=own,commands=records,new_compiler=False,new_actual_fixture_or_callee_or_destructor_execution=False,new_native_UI_capture_or_global_process_inventory=False,owned_scratch_created=False,owned_children_all_waited=True)
 (HERE/'verification-results.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
 print(json.dumps(dict(status=receipt['status'],commands=len(records),compiler=False,runtime=False)))
