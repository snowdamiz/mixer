import hashlib,importlib.util,json,os,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
LIFE=HERE.parent/'native-custody-premise/cleanup_control.py'
EXPECTED='8885f85a8d49ffbce813dd4221dc381ca88feef98f0f3905e67f4610381365df'
if hashlib.sha256(LIFE.read_bytes()).hexdigest()!=EXPECTED: raise RuntimeError('Supervisor digest changed')
spec=importlib.util.spec_from_file_location('accepted_cleanup',LIFE)
life=importlib.util.module_from_spec(spec);spec.loader.exec_module(life)
out=HERE/'commands';out.mkdir(exist_ok=False)
scratch=out/'scratch';scratch.mkdir()
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',DEVELOPER_DIR='/Applications/Xcode_26.6.app/Contents/Developer')
m=life.Commands(out,env,deadline=time.monotonic()+65,output_bytes=8*life.MIB,total_output_bytes=32*life.MIB)
r={'supervisorSHA256':EXPECTED,'python':sys.version,'perCommandExecutionSeconds':25,'cleanupSeconds':5,'maxInspections':2,'preliminaryDeviation':'Unsupervised pwd executed before supervisor discovery; completed with exit 0. No accepted custody receipt exists for pwd; do not treat its tool return as accepted group custody proof.'}
try:
 for label,argv in [('simctl-help',['/Applications/Xcode_26.6.app/Contents/Developer/usr/bin/simctl','help']),('simulator-disassembly',['/usr/bin/otool','-arch','arm64','-tvV','/Applications/Xcode_26.6.app/Contents/Developer/Applications/Simulator.app/Contents/MacOS/Simulator'])]:
  m.run(label,argv,HERE,25)
 r['status']='complete'
except BaseException as e: r.update(status='stopped',error=repr(e))
finally:
 r['cleanup']=m.cleanup(scratch);r['commands']=m.records
 if not r['cleanup']['allTerminalCustody']: r['status']='UNKNOWN'
 (HERE/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r))
