from pathlib import Path
import datetime,hashlib,json,sys
HERE=Path(__file__).resolve().parent
SEAL=HERE/'seal.json'
def member(path):
 data=path.read_bytes();return {'path':str(path.relative_to(HERE)),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
if sys.argv[1:]==['--verify']:
 seal=json.loads(SEAL.read_text())
 for item in seal['members']:assert member(HERE/item['path'])==item
 assert hashlib.sha256(json.dumps(seal['members'],sort_keys=True,separators=(',',':')).encode()).hexdigest()==seal['tree_sha256']
 print(json.dumps({'verified_members':seal['member_count'],'bytes':seal['bytes'],'seal_sha256':hashlib.sha256(SEAL.read_bytes()).hexdigest(),'tree_sha256':seal['tree_sha256']},sort_keys=True))
else:
 assert not sys.argv[1:]and not SEAL.exists()
 assert not any((HERE/name).exists()for name in('work','privacy-work','helper-work','capture-work'))
 assert not list(HERE.rglob('__pycache__'))
 members=[member(path)for path in sorted(HERE.rglob('*'))if path.is_file()]
 assert not any(path.is_symlink()for path in HERE.rglob('*'))
 review=json.loads((HERE/'review.json').read_text())
 seal={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':review['status'],'command':[sys.executable,'-B',str(Path(__file__).resolve())],'python':sys.version,'candidate_seal_sha256':review['candidate_seal_sha256'],'preaccess_seal_sha256':review['preaccess_seal_sha256'],'scope':'independent pure encoder component review with additive future-admission source-place/layout inputs; no original-control or operational floor','member_count':len(members),'bytes':sum(item['bytes']for item in members),'members':members,'tree_sha256':hashlib.sha256(json.dumps(members,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'retained_failures':3,'cleanup_limit':'Known direct children reaped and owned compiler files removed; timeout descendant/process-group cleanup unverified. No global inventory or retroactive run.'}
 SEAL.write_text(json.dumps(seal,sort_keys=True,indent=2)+'\n')
 print(json.dumps({'seal_sha256':hashlib.sha256(SEAL.read_bytes()).hexdigest(),'members':len(members),'bytes':seal['bytes'],'tree_sha256':seal['tree_sha256']},sort_keys=True))
