import importlib.util,json,os,sys,time,shlex
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
source=HERE.parent/'native-custody-premise/cleanup_control.py'
spec=importlib.util.spec_from_file_location('accepted_cleanup',source);c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
out=HERE/'controls';out.mkdir(exist_ok=False)
scratch=out/'scratch';scratch.mkdir()
manager=c.Commands(out,dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),deadline=time.monotonic()+365,output_bytes=4*c.MIB,total_output_bytes=32*c.MIB)
commands=json.loads((HERE.parent/'store-journal-delivery/manifest.json').read_text())['controls']['commands']
receipt={'status':'failed','commandsSelected':commands,'maximumCommands':6,'secondsPerCommand':60}
try:
 if len(commands)!=6:raise RuntimeError('six controls required')
 for index,line in enumerate(commands):manager.run('control-'+str(index+1),shlex.split(line),ROOT,60)
 receipt['status']='passed'
except BaseException as error:receipt['error']=repr(error)
finally:
 receipt['cleanup']=manager.cleanup(scratch);receipt['commands']=manager.records
 if not receipt['cleanup']['allTerminalCustody']:receipt['status']='failed'
 (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k not in ('commandsSelected','commands')}))
sys.exit(0 if receipt['status']=='passed' else 1)
