#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,datetime,sys
R=Path(__file__).resolve().parents[2]; O=Path(__file__).resolve().parent
P=R/'verification/android-editor-source-pair5-host-integration'; B=R/'verification/android-editor-source-pair5-rebinding'
def ident(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def verify(packet,expected,manifest_name=None):
 assert ident(packet/'seal.json')['sha256']==expected
 seal=json.loads((packet/'seal.json').read_text()); m=json.loads((packet/(manifest_name or 'seal.json')).read_text())
 if manifest_name: assert ident(packet/manifest_name)==seal['manifest']
 members=m['members']; paths=[x['path'] for x in members]; assert len(set(paths))==len(paths)
 for x in members:
  q=Path(x['path']);assert not q.is_absolute() and '..' not in q.parts
  p=packet/q;assert p.is_file() and not p.is_symlink();assert ident(p)=={k:x[k] for k in ('bytes','sha256')},str(p)
 assert not any(x.is_symlink() for x in packet.rglob('*'))
 allowed={'seal.json'}|({manifest_name} if manifest_name else set())
 assert {str(x.relative_to(packet)) for x in packet.rglob('*') if x.is_file()}==set(paths)|allowed
 assert len(members)==m['member_count'] and sum(x['bytes'] for x in members)==m['member_bytes']
 if manifest_name:
  assert len(members)==seal['member_count'] and m['member_bytes']==seal['member_bytes']
  assert hashlib.sha256(''.join(x['path']+'\0'+x['sha256']+'\n' for x in members).encode()).hexdigest()==seal['member_projection_sha256']
 return {'seal':ident(packet/'seal.json'),'member_count':len(members),'member_bytes':m['member_bytes'],'closed':True,'no_symlinks':True}
r={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'producer':verify(P,'c356544da794b1ae630ec2bb4522f8a9ed93fe1aedb9958676dc84f27188733a','manifest.json'),'rebinding':verify(B,'088b6dd59bbfd91cd93e7c4cbb16ca1285018b0f6eb6045932b348f7beaf8864')}
selection=R/'verification/android-editor-boundary-root-review/source-pair5-integration-selection.json'
assert ident(selection)['sha256']=='364af243803a30dd0e6dbd66fd23ddb68671a0b0ce494731841a891888248e9e';r['selection']=ident(selection)
bindings=json.loads((P/'final-candidate-bindings.json').read_text()); C=P/'candidate'; actual={str(p.relative_to(C)):ident(p) for p in sorted(C.rglob('*')) if p.is_file()}
assert set(actual)==set(bindings)
assert all(all(bindings[n].get(k)==v for k,v in x.items()) for n,x in actual.items())
projection=hashlib.sha256(''.join(n+'\0'+actual[n]['sha256']+'\n' for n in sorted(actual)).encode()).hexdigest();assert projection=='9571123478012f36b0d720f73cc5635da9b40125dd3c5a8bf43a0f2ce6196ef1'
r['candidate']={'files':len(actual),'projection_sha256':projection,'bindings_exact':True}
(O/'custody.json').write_text(json.dumps(r,indent=2)+'\n'); print(json.dumps(r,indent=2))
