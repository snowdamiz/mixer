"""Read-only frozen closure verification and deterministic replay."""
from pathlib import Path
import hashlib,json,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent

def main():
 s=json.loads((HERE/'seal.json').read_bytes());rows=s['members']
 assert len(rows)==s['member_count'] and sum(x['bytes'] for x in rows)==s['total_bytes']
 expected={r['path'] for r in rows};actual={str(p.relative_to(HERE)) for p in HERE.rglob('*') if p.is_file() and p!=HERE/'seal.json'}
 assert len(expected)==len(rows) and actual==expected
 for r in rows:
  p=HERE/r['path'];assert not p.is_symlink() and p.resolve()==p.absolute(),p
  b=p.read_bytes();assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'],p
 from run_checks import main as checks
 checks()
 print(json.dumps({'frozen_members_verified':len(rows),'frozen_bytes_verified':s['total_bytes'],'seal_sha256':hashlib.sha256((HERE/'seal.json').read_bytes()).hexdigest()}))
if __name__=='__main__':main()
