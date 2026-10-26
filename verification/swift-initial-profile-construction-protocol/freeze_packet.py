#!/usr/bin/env python3
from pathlib import Path
import hashlib,json
OUT=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
members=[]
for p in sorted(OUT.rglob('*'),key=lambda p:str(p.relative_to(OUT))):
 if p.is_file() and p.name not in {'seal.json','seal.sha256'}:
  b=p.read_bytes();members.append({'path':str(p.relative_to(OUT)),'bytes':len(b),'sha256':sha(b)})
assert not any(m['path'].split('/')[0].startswith('initial-profile-layout-') or '__pycache__' in m['path'].split('/') for m in members)
j={'schema':1,'scope':'Exact outcome/signature/ownership/local-layout/test-plan proposal; data-only host probes and offline packet controls',
 'excluded':['seal.json','seal.sha256'],'tree_definition':'SHA256 sorted full relative string path TAB decimal bytes TAB lowercase sha256 LF',
 'members':members,'member_count':len(members),'total_bytes':sum(m['bytes'] for m in members),
 'tree_sha256':sha(''.join(f"{m['path']}\t{m['bytes']}\t{m['sha256']}\n" for m in members).encode()),
 'product_implementation_or_component_semantics_or_runtime_or_GA_accepted':False}
b=(json.dumps(j,indent=2,sort_keys=True)+'\n').encode();(OUT/'seal.json').write_bytes(b);(OUT/'seal.sha256').write_text(sha(b)+'  seal.json\n')
print(json.dumps({'seal_sha256':sha(b),'members':j['member_count'],'bytes':j['total_bytes'],'tree_sha256':j['tree_sha256']}))
