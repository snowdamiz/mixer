import hashlib, importlib.util, json, os, sys, time
from pathlib import Path
OWN=Path(__file__).resolve().parent
CONTROL=OWN.parent/'mainactor-controller-rebind-r2/cleanup_control.py'
EXPECTED='8885f85a8d49ffbce813dd4221dc381ca88feef98f0f3905e67f4610381365df'
if hashlib.sha256(CONTROL.read_bytes()).hexdigest()!=EXPECTED: raise RuntimeError('custodian drift')
spec=importlib.util.spec_from_file_location('accepted_cleanup_control',CONTROL)
control=importlib.util.module_from_spec(spec);spec.loader.exec_module(control)
out=OWN/'audit-2'; out.mkdir(exist_ok=False)
scratch=OWN/'audit-2-scratch';scratch.mkdir(exist_ok=False)
start=time.monotonic()
commands=control.Commands(out,dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),deadline=start+60)
receipt={'scope':'one child-free data/oracle audit','python':sys.version,'lifecycleSHA256':EXPECTED,'scriptSHA256':hashlib.sha256((OWN/'audit-r2.py').read_bytes()).hexdigest(),'childSeconds':55,'outerSeconds':60}
try:
    receipt['output']=commands.run('retained-actual-evidence-audit',['/opt/homebrew/opt/python@3.14/bin/python3.14','-I','-B',OWN/'audit-r2.py'],scratch,55)
    receipt['status']='passed'
except BaseException as error:
    receipt['status']='failed';receipt['failure']=repr(error)
finally:
    receipt['cleanup']=commands.cleanup(scratch)
    receipt['commands']=commands.records
    receipt['elapsedSeconds']=time.monotonic()-start
    (OWN/'audit-custody-r2.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
sys.exit(0 if receipt['status']=='passed' and receipt['cleanup'].get('allTerminalCustody') and receipt['cleanup'].get('scratchRemoved') else 1)
