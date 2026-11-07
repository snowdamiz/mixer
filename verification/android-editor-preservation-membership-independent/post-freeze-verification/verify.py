from pathlib import Path
import hashlib,json
p=Path(__file__).resolve().parents[1]/'preaccess';s=json.loads((p/'seal.json').read_text())
for r in s['members']:
 q=p/r['path'];b=q.read_bytes();assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'],q
m=json.loads((p/'manifest.json').read_text())
manifest={r['path']:r for r in m['members']};sealed={r['path']:r for r in s['members'] if r['path']!='manifest.json'}
assert len(manifest)==len(m['members']) and len(sealed)+1==len(s['members'])
assert manifest==sealed
assert sum(r['bytes'] for r in s['members'])==s['member_bytes']
print('VERIFIED',len(s['members']),'members',s['member_bytes'],'bytes; seal',hashlib.sha256((p/'seal.json').read_bytes()).hexdigest())
