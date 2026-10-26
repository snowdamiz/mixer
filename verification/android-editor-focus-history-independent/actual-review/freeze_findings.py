#!/usr/bin/env python3
from pathlib import Path
import datetime,hashlib,json,shutil
D=Path(__file__).resolve().parent
T=D/'findings-1';T.mkdir(exist_ok=False)
def row(path):
    data=path.read_bytes();return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def copy(relative,destination):
    target=T/destination;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(D/relative,target)
for name in ['findings.md','root-custody.json','producer-seal.json']:
    copy(name,name)
for path in sorted((D/'controls-2/source').glob('*.java')):copy(str(path.relative_to(D)),'controls/'+path.name)
for name in ['receipt.json','compile.stdout','compile.stderr','post-attach-rollback.stdout','post-attach-rollback.stderr','cross-renderer-end.stdout','cross-renderer-end.stderr','exhaustion.stdout','exhaustion.stderr']:
    copy('controls-2/'+name,'execution/'+name)
for name in ['NativeAppearanceViewsV2.java','NativeRenderer.java','NativeCoordinatorV2.java']:
    copy('frozen/source/'+name,'source/'+name)
for name in ['source-map.json','class-map.json','receipt.json']:
    copy('frozen/runs/host-1/'+name,'complete-source-replay/'+name)
members=[{'path':str(path.relative_to(T)),**row(path)} for path in sorted(T.rglob('*')) if path.is_file()]
seal={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Two independent actual-source correction findings; ordinary eligible rollback and private wrong-owner count consumption','verdict':'changes-required','members':members,'member_count':len(members),'member_bytes':sum(item['bytes'] for item in members)}
data=(json.dumps(seal,indent=2)+'\n').encode();(T/'seal.json').write_bytes(data);print(json.dumps({'seal':str(T/'seal.json'),'sha256':hashlib.sha256(data).hexdigest(),'members':len(members),'bytes':seal['member_bytes']}))
