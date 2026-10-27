"""Read-only complete membership and digest verification of this packet."""
import hashlib,json,sys
from pathlib import Path
D=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 seal=json.loads((D/'seal.json').read_text());members=seal['members'];names=[]
 for m in members:
  q=Path(m['path']);assert not q.is_absolute() and '..' not in q.parts
  p=D/q;assert not p.is_symlink();raw=p.read_bytes()
  assert len(raw)==m['bytes'] and sha(raw)==m['sha256'],str(q);names.append(str(q))
 assert len(names)==len(set(names))==seal['member_count']
 assert sum(m['bytes'] for m in members)==seal['bytes']
 actual={str(p.relative_to(D)) for p in D.rglob('*') if p.is_file()}
 assert actual==set(names)|{'seal.json'},'complete sealed membership'
 for flag in ('L_str_selected','actual_P0_caller_selected','selected_whole_host_bound','operational_grant','runtime_or_OTA_or_GA'):assert seal[flag] is False
 print(json.dumps({'seal_sha256':sha((D/'seal.json').read_bytes()),'members':len(members),'bytes':seal['bytes'],'read_only':True,'all_member_digests_and_membership_match':True,'operational_grant':False},sort_keys=True))
if __name__=='__main__':main()
