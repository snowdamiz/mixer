import hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
members=[]
for p in sorted(HERE.rglob('*')):
    if p.is_file() and p.name!='seal.json':
        b=p.read_bytes(); members.append({'path':p.relative_to(ROOT).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
seal={'schema':1,'at':datetime.now(timezone.utc).isoformat(),'status':'frozen independent G6/clear source-design review; no whole-work/lifetime/implementation acceptance','member_path_base':'repository-root','command':[sys.executable,'-B',str(Path(__file__).resolve())],'python':sys.version,'members':members,'member_count':len(members),'member_bytes':sum(x['bytes'] for x in members),'excluded':['verification/swift-cache-state-g6-independent-review/seal.json'],'runtime_tests':0,'repair_selected':False,'implementation_accepted':False}
(HERE/'seal.json').write_text(json.dumps(seal,indent=2)+'\n')
print(json.dumps({'seal':str((HERE/'seal.json').relative_to(ROOT)),'sha256':hashlib.sha256((HERE/'seal.json').read_bytes()).hexdigest(),'members':len(members),'bytes':seal['member_bytes']}))
