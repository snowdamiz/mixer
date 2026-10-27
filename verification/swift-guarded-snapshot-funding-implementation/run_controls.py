"""Run the owned pure source controls with bounded command custody."""
from pathlib import Path
import json
import sys

sys.dont_write_bytecode=True
from prepare import HERE,sha,write
from verify import bounded,custody

def main():
    label='source-ordering-accounting-controls'
    directory=HERE/'commands'/label
    directory.mkdir(parents=True,exist_ok=False)
    binding=custody()
    argv=[sys.executable,str(HERE/'controls.py')]
    out,err,receipt=bounded(argv,{'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'},HERE.parent.parent)
    (directory/'stdout').write_bytes(out)
    (directory/'stderr').write_bytes(err)
    receipt.update(schema=1,python_version=sys.version,python_executable=sys.executable,
        driver_sha256=sha(Path(__file__).read_bytes()),control_sha256=sha((HERE/'controls.py').read_bytes()),
        source_binding=binding,stdout_sha256=sha(out),stderr_sha256=sha(err),
        scope='Exact source/MIR accounting and ordering controls only; no engine/writer/native runtime')
    (directory/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    assert receipt['exit_code']==0 and receipt['owned_group_absent'] and not receipt['timed_out'],err.decode()
    print(out.decode().strip())

if __name__=='__main__':
    main()
