import hashlib,importlib.util,json,os,sys,time
from pathlib import Path
out=Path(__file__).resolve().parent
path=out.parent/'native-custody-premise/cleanup_control.py'
assert hashlib.sha256(path.read_bytes()).hexdigest()=='8885f85a8d49ffbce813dd4221dc381ca88feef98f0f3905e67f4610381365df'
spec=importlib.util.spec_from_file_location('control',path);c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
log=out/('supervision-'+sys.argv[1]);log.mkdir()
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
cmd=c.Commands(log,env,deadline=time.monotonic()+125)
try:
 print(cmd.run(sys.argv[1],[sys.executable,'-B',str(out/sys.argv[2])],out,timeout=115))
finally:
 result={'hold':cmd.hold,'allTerminalCustody':all(v['terminal_custody'] for v in cmd.records),'records':cmd.records,'python':sys.version}
 (log/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 if result['allTerminalCustody']:cmd.selector.close()
