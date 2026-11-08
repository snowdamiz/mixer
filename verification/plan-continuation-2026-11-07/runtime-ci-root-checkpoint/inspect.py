import hashlib, importlib.util, json, os, sys, time
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path("/Users/andreyyurlov/.t3/worktrees/mixer/t3-84a22cd4")
HERE=Path(__file__).resolve().parent
CTL=ROOT/'verification/plan-continuation-2026-11-07/native-custody-premise/cleanup_control.py'
if hashlib.sha256(CTL.read_bytes()).hexdigest()!='8885f85a8d49ffbce813dd4221dc381ca88feef98f0f3905e67f4610381365df': raise RuntimeError('controller drift')
spec=importlib.util.spec_from_file_location('custody',CTL); m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
out=HERE/'commands';out.mkdir();scratch=HERE/'scratch';scratch.mkdir()
c=m.Commands(out,dict(os.environ,GIT_TERMINAL_PROMPT='0',PYTHONDONTWRITEBYTECODE='1'),deadline=time.monotonic()+90,output_bytes=1024*1024,total_output_bytes=4*1024*1024)
result={'recordedAt':datetime.now(timezone.utc).isoformat(),'scope':'Read-only root shipping and tracker checkpoint'}
try:
 result['head']=c.run('head',['git','rev-parse','HEAD'],ROOT,15)
 result['tracked']=c.run('tracked',['git','diff','--name-only'],ROOT,15).splitlines()
 result['index']=c.run('index',['git','diff','--cached','--name-only'],ROOT,15).splitlines()
 c.run('whitespace',['git','diff','--check'],ROOT,15)
 sp=importlib.util.spec_from_file_location('inventory',ROOT/'scripts/ci/check-android-generated-java.py'); inv=importlib.util.module_from_spec(sp);sys.modules[sp.name]=inv;sp.loader.exec_module(inv)
 inputs=inv.source_inputs(inv.load_profile());result['sourceInputs']=len(inputs);result['sourceDigest']=inv.source_digest(inputs)
 if result['head']!='0f30624df2edcd50ee7f1b069afb96c0ae263791' or result['index'] or result['sourceInputs']!=103 or result['sourceDigest']!='eda43c6bb96bfeb15ab31731858c7388a7ba52329c8ba8e48ed52505bfe86158':raise RuntimeError('unexpected root state')
 result['status']='verified'
except BaseException as e:
 result['status']='failed';result['error']=repr(e)
finally:
 result['cleanup']=c.cleanup(scratch)
 result['commands']=c.records
 if c.limit or c.hold or not result['cleanup']['allTerminalCustody']:result['status']='failed'
 (HERE/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k!='commands'},indent=2))
sys.exit(0 if result['status']=='verified' else 1)
