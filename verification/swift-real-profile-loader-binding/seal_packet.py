"""--write freezes once; default verifies exact packet membership read-only."""
from pathlib import Path
import hashlib,json,sys
HERE=Path(__file__).resolve().parent;SEAL=HERE/'seal.json'
def sha(b):return hashlib.sha256(b).hexdigest()
def members():return [{'path':str(p.relative_to(HERE)),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}for p in sorted(HERE.rglob('*'))if p.is_file()and p!=SEAL]
def main():
 actual=members()
 if sys.argv[1:]==['--write']:
  assert not SEAL.exists();SEAL.write_text(json.dumps({'schema':1,'member_count':len(actual),'members':actual},sort_keys=True,indent=2)+'\n')
 else:assert not sys.argv[1:]
 expected=json.loads(SEAL.read_bytes());assert expected['member_count']==len(actual)and expected['members']==actual
 print(json.dumps({'seal_sha256':sha(SEAL.read_bytes()),'members':len(actual),'bytes':sum(m['bytes']for m in actual),'exact_set_and_all_hashes':True},sort_keys=True))
if __name__=='__main__':main()
