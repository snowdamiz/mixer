"""Fresh owned temporary runner output, complete retained bytes and path mapping."""
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import uuid

PACKET=Path(__file__).resolve().parent
ROOT=PACKET.parents[1]
spec=importlib.util.spec_from_file_location('correction_evidence',PACKET/'run-evidence.py')
evidence=importlib.util.module_from_spec(spec);spec.loader.exec_module(evidence)
base=Path(tempfile.mkdtemp(prefix='mixer-envelope-ci-correction-')).resolve()
marker={'purpose':'mixer-envelope-ci-correction-fresh-output','token':uuid.uuid4().hex}
(base/'ownership.json').write_text(json.dumps(marker,sort_keys=True)+'\n')
identity=[base.stat().st_dev,base.stat().st_ino,base.stat().st_uid]
out=base/'run'
state={'schema':1,'started_utc':datetime.now(timezone.utc).isoformat(),'temporary_parent':str(base),
       'temporary_parent_identity':identity,'ownership_marker':marker,'original_output':str(out),
       'retained_output':'host-run-1','source_freeze_sha256':evidence.digest(PACKET/'freeze.json'),
       'native_runtime_or_capture_started':False,'GA_qualified':False}
(PACKET/'full-run-state.json').write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')
command=evidence.run('full-host-command',[sys.executable,'-B',ROOT/'scripts/ci/check-analyzer-envelope.py',
    '--rustc','/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin/rustc','--out',out],timeout=560)
def inventory(path):
    rows=[]
    for item in sorted(path.rglob('*')):
        if item.is_symlink() or not (item.is_file() or item.is_dir()):
            raise RuntimeError('Unexpected member in correction-owned retention: '+str(item))
        if item.is_file():
            rows.append({'path':item.relative_to(path).as_posix(),'bytes':item.stat().st_size,'sha256':evidence.digest(item)})
    return rows
before=inventory(out)
retained=PACKET/'host-run-1'
shutil.copytree(out,retained)
after=inventory(retained)
if before!=after or before!=inventory(out): raise RuntimeError('Lossless retention comparison failed; temporary source preserved')
state.update({'finished_utc':datetime.now(timezone.utc).isoformat(),'command_exit':command['exit'],
    'mapping':{'from':str(out),'to':str(retained),'rule':'replace the exact original-output prefix in receipt paths; retained file bytes are unchanged'},
    'members':before,'member_count':len(before),'total_bytes':sum(x['bytes'] for x in before),
    'retained_inventory_sha256':__import__('hashlib').sha256(json.dumps(before,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
    'all_retained_bytes_and_paths_verified':True,'temporary_parent_removed':False})
(PACKET/'full-run-state.json').write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')
receipt=json.loads((retained/'receipt.json').read_bytes())
# A failed/unclean runner output remains recoverable; never erase its source.
if command['exit']==0 and receipt['status']=='passed-host-fixture-check' and receipt['cleanup'].get('removed'):
    observed=[base.stat().st_dev,base.stat().st_ino,base.stat().st_uid]
    if observed!=identity or json.loads((base/'ownership.json').read_bytes())!=marker:
        raise RuntimeError('Temporary parent ownership changed; preserved')
    if sorted(x.name for x in base.iterdir())!=['ownership.json','run']:
        raise RuntimeError('Unexpected temporary parent member; preserved')
    if inventory(out)!=before: raise RuntimeError('Temporary output changed before cleanup; preserved')
    shutil.rmtree(base)
    if base.exists(): raise RuntimeError('Temporary parent removal incomplete')
    state['temporary_parent_removed']=True
    state['cleanup_scope']='Only exact owned temporary parent after verified complete retained output; runner already removed its exact scratch.'
(PACKET/'full-run-state.json').write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'command_exit':command['exit'],'members':len(before),
    'bytes':state['total_bytes'],'temporary_parent_removed':state['temporary_parent_removed']}),flush=True)
sys.exit(command['exit'] if command['exit'] is not None else 1)
