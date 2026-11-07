import hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
members=[]
for p in sorted(HERE.rglob('*')):
    if p.is_file() and p.name!='seal.json':
        b=p.read_bytes()
        members.append({'path':p.relative_to(ROOT).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
seal={'schema':1,'at':datetime.now(timezone.utc).isoformat(),'status':'frozen independent proposal2 source-only design disposition; no final cost/lifetime/implementation acceptance','member_path_base':'repository-root','command':[sys.executable,'-B',str(Path(__file__).resolve())],'python':sys.version,'members':members,'member_count':len(members),'member_bytes':sum(m['bytes'] for m in members),'excluded':['verification/swift-cache-state-g3-independent-review/proposal2/seal.json'],'parent_proposal_seal_sha256':'08b6b164cb4cb8d420538f9bcf4cb0b97850912789b29635aaf8e140a74263b7','prior_review_seal_sha256':'4773adbb72299087ba2c7ee1f060186e373d1091b8d8eeac07b059099584e6c6','runtime_tests':0,'implementation_accepted':False,'repair_selected':False}
(HERE/'seal.json').write_text(json.dumps(seal,indent=2)+'\n')
print(json.dumps({'seal':str((HERE/'seal.json').relative_to(ROOT)),'sha256':hashlib.sha256((HERE/'seal.json').read_bytes()).hexdigest(),'members':len(members),'bytes':seal['member_bytes']}))
