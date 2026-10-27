#!/usr/bin/env python3
"""One-time self-owned manifest seal; does not change any other packet."""
from pathlib import Path
import datetime,hashlib,json,sys,os,signal,time
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    signal.alarm(55);started=time.monotonic()
    if (HERE/'seal.json').exists():raise ValueError('already immutable')
    import derive as D
    before=D.input_roster()
    if before!=D.load(HERE/'input-lock.json'):raise ValueError('immutable input custody before seal')
    after=D.input_roster()
    if after!=before:raise ValueError('immutable input custody after seal preparation')
    receipt={'schema':1,'argv':[sys.executable,'-B',str(HERE/'freeze.py')],'cwd':os.getcwd(),'environment':dict(os.environ),'python_version':sys.version,'python_executable_sha256':sha(Path(sys.executable).resolve().read_bytes()),'timeout_seconds':55,'elapsed_before_seal_seconds':time.monotonic()-started,'source_tree_sha256':D.TREE,'input_roster_sha256_before':sha(D.canon(before)),'input_roster_sha256_after':sha(D.canon(after)),'input_members':len(before['files']),'child_processes_spawned':0,'no_process_group_created':True,'no_owned_scratch_created':True,'compiler_or_runtime_or_global_inventory':False}
    (HERE/'freeze-receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    members=[]
    for p in sorted(HERE.rglob('*')):
        if not p.is_file():continue
        if p.is_symlink() or '__pycache__' in p.parts:raise ValueError('unsealed cache or foreign member')
        b=p.read_bytes();members.append({'path':p.relative_to(HERE).as_posix(),'bytes':len(b),'sha256':sha(b)})
    seal={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'separate proposed owned-provider exact callee logical source/typed-byte amendment; fresh independent review and root price selection required','members':members,'member_count':len(members),'bytes':sum(x['bytes'] for x in members)}
    p=HERE/'seal.json';p.write_text(json.dumps(seal,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'seal_sha256':sha(p.read_bytes()),'members':len(members),'bytes':seal['bytes']}))
    signal.alarm(0)
if __name__=='__main__':main()
