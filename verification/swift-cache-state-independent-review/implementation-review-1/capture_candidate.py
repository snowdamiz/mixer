"""Independent root-admitted candidate data capture; no producer execution."""
from datetime import datetime,timezone
import hashlib,json
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 admission='verification/swift-semantic-adapter-root-review/candidate-public-review-admission.json'
 a=(ROOT/admission).read_bytes()
 if sha(a)!='c238edff3f5ef05a770640a0f67b2d748e6e95108dfe00d93e7d890e42333df0':raise ValueError('admission')
 (OUT/'root-admission.json').write_bytes(a)
 p=ROOT/'verification/swift-cache-state-implementation/candidate-repo-seal.json';b=p.read_bytes()
 if sha(b)!='caceb9db9263de46ed876ff109f34eacb8fe13a9bd3ac47758f2bdac5c693ad3':raise ValueError('seal')
 (OUT/'candidate-seal.json').write_bytes(b);s=json.loads(b);members=[]
 for m in s['members']:
  n=PurePosixPath(m['path'])
  if n.is_absolute() or '..' in n.parts:raise ValueError('member path')
  if not (str(n).startswith('verification/swift-cache-state-implementation/') or str(n)=='docs/swift-cache-state-implementation.md'):raise ValueError('member scope')
  data=(ROOT/str(n)).read_bytes()
  if len(data)!=m['bytes'] or sha(data)!=m['sha256']:raise ValueError('member drift')
  dest=OUT/'candidate-snapshot'/str(n);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
  members.append(m)
 if len(members)!=454 or sum(m['bytes'] for m in members)!=15362764:raise ValueError('totals')
 receipt={'at':datetime.now(timezone.utc).isoformat(),'command':['python3.14','-B',str(Path(__file__).relative_to(ROOT))],
  'members':members,'member_count':454,'member_bytes':15362764,'seal_sha256':sha(b),
  'producer_models_harnesses_tests_imported_or_executed':False,
  'access_order':'Unchanged runner first verified all454 members and staged exact three Rust sources; first header/index read then preceded this full separate snapshot. Substantive source proof review uses this snapshot.'}
 (OUT/'candidate-snapshot-manifest.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
 print(json.dumps({'members':454,'bytes':15362764,'source_execution':'none by this capture'}))
if __name__=='__main__':main()
