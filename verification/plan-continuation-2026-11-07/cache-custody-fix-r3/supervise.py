"""Exactly two supervised pure/fake commands, one normal and one optimized."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
CONTROL=HERE.parent/'native-custody-premise/cleanup_control.py'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,value):(HERE/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
if sha(CONTROL)!='8885f85a8d49ffbce813dd4221dc381ca88feef98f0f3905e67f4610381365df':raise RuntimeError('Controller drift')
paths=[ROOT/p for p in json.loads((HERE/'projection-paths.json').read_bytes())]
for directory in [HERE,HERE.parent/'cache-custody-premise-r2']:
    seal=json.loads((directory/'sources.json').read_bytes())
    paths += [directory/r['path'] for r in seal['members']]+[directory/'sources.json']
paths += [HERE.parent/'cache-custody-review-r2/review_fakes.py',CONTROL]
paths=sorted(set(paths))
before={str(p.relative_to(ROOT)):sha(p) for p in paths}
save('observed-inputs.json',before)
spec=importlib.util.spec_from_file_location('accepted_controller',CONTROL)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
out=HERE/'supervision';out.mkdir()
scratch=HERE/'supervisor-scratch';scratch.mkdir()
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(scratch),TMP=str(scratch),TEMP=str(scratch))
controller=module.Commands(out,env,deadline=time.monotonic()+250,output_bytes=8*1024*1024,total_output_bytes=16*1024*1024,cleanup_seconds=5)
save('host.json',{'argv':sys.argv,'cwd':str(Path.cwd()),'python':sys.version,'executable':sys.executable,'python_sha256':sha(Path(sys.executable).resolve()),'uname':list(os.uname()),'controller_sha256':sha(CONTROL),'suite_sha256':sha(HERE/'combined_fakes.py'),'supervisor_sha256':sha(Path(__file__)),'revision':'0f30624df2edcd50ee7f1b069afb96c0ae263791','tree':'ad8066ea6ff9a8e97a162b357bd4cfcb3fee7d13','input_tree_sha256':hashlib.sha256(json.dumps(before,sort_keys=True).encode()).hexdigest()})
results=[]
for mode,flags in [('normal',[]),('optimized',['-O'])]:
    if controller.hold:break
    argv=[sys.executable,'-B',*flags,str(HERE/'combined_fakes.py')]
    try:
        controller.run(mode,argv,ROOT,timeout=120,allowed=(0,1))
        results.append({'mode':mode,'exit':controller.records[-1]['exit_code']})
    except BaseException as error:
        results.append({'mode':mode,'error':repr(error)});break
cleanup=controller.cleanup(scratch)
after={str(p.relative_to(ROOT)):sha(p) for p in paths}
save('postflight.json',{'unchanged':before==after,'after':after})
save('result.json',{'results':results,'cleanup':cleanup,'source_unchanged':before==after,'scope':'Two pure/fake suites. Original suite bodies not executed; fake suite through actual entrypoint. No real descendant/compiler/CI/native execution.'})
print(json.dumps({'results':results,'cleanup':cleanup,'source_unchanged':before==after}))
sys.exit(0 if len(results)==2 and all(r.get('exit')==0 for r in results) and cleanup['allTerminalCustody'] and before==after else 1)
