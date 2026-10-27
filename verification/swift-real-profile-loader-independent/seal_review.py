from pathlib import Path
import hashlib,json,sys
HERE=Path(__file__).resolve().parent
SEAL=HERE/'seal.json'
def sha(b):return hashlib.sha256(b).hexdigest()
def members():
 rows=[]
 for p in sorted(HERE.rglob('*')):
  assert not p.is_symlink(),str(p)
  if p.is_file()and p!=SEAL:
   b=p.read_bytes();rows.append({'path':str(p.relative_to(HERE)),'bytes':len(b),'sha256':sha(b)})
 return rows
rows=members()
if sys.argv[1:]==['--write']:
 assert not SEAL.exists(),'Do not rewrite a frozen review'
 data={'schema':1,'scope':'Independent actual private loader host review with one nonblocking diagnostic finding; no runtime/native/GA acceptance','member_count':len(rows),'member_bytes':sum(m['bytes']for m in rows),'members':rows}
 SEAL.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
else:
 data=json.loads(SEAL.read_bytes());assert rows==data['members'];assert data['member_count']==len(rows);assert data['member_bytes']==sum(m['bytes']for m in rows)
 if sys.argv[1:]:assert sys.argv[1:]==['--expected',sha(SEAL.read_bytes())]
print(json.dumps({'seal_sha256':sha(SEAL.read_bytes()),'member_count':len(rows),'member_bytes':sum(m['bytes']for m in rows),'exact_closed_custody':True}))
