"""Run focused source/MIR controls with bounded process custody."""
import json,sys
sys.dont_write_bytecode=True
from prepare import HERE,sha,custody
from verify import bounded
p=HERE/'commands/source-ordering-accounting-controls';p.mkdir(parents=True,exist_ok=False)
out,err,r=bounded([sys.executable,str(HERE/'controls.py')],{'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'},HERE.parent.parent)
(p/'stdout').write_bytes(out);(p/'stderr').write_bytes(err)
r.update(schema=1,python_version=sys.version,python_executable=sys.executable,driver_sha256=sha((HERE/'run_controls.py').read_bytes()),controls_sha256=sha((HERE/'controls.py').read_bytes()),source_binding=custody(),stdout_sha256=sha(out),stderr_sha256=sha(err),scope='Exact source differential and focused compiler MIR reconciliation; no VM/writer/loader/runtime dispatch')
(p/'receipt.json').write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
assert r['exit_code']==0 and r['owned_group_absent'] and not r['timed_out'],err.decode()
print(out.decode().strip())
