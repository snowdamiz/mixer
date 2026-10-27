"""Run only expanded finite Python model; retained earlier eight-group output unchanged."""
import sys,json,pathlib
from run_controls import command,HERE,dump,digest
r,out,err=command('python-controls-expanded',[sys.executable,'-B',str(HERE/'controls.py')],HERE)
assert r['exit_code']==0,err
result=json.loads(out)
result['runner_sha256']=digest(pathlib.Path(__file__))
result['controls_sha256']=digest(HERE/'controls.py')
dump(HERE/'expanded-controls-result.json',result)
print(json.dumps(result,indent=2))
