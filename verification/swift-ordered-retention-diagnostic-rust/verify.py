"""Read-only frozen receipt verifier. Executes no product or archived code."""
from pathlib import Path
import hashlib,json,tarfile,re
P=Path(__file__).resolve().parent;R=P.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
seal=json.loads((P/'seal.json').read_bytes());assert sha((P/'seal.json').read_bytes())==(P/'seal.sha256').read_text().strip()
for entry in seal['members']:
 path=R/entry['path'];assert path.is_file()and not path.is_symlink();raw=path.read_bytes();assert len(raw)==entry['bytes']and sha(raw)==entry['sha256'],entry['path']
base=json.loads((P/'baseline-source-manifest.json').read_bytes());candidate=json.loads((P/'candidate-manifest.json').read_bytes());assert len(base)==len(candidate)==132
for label,manifest in [('baseline',base),('candidate',candidate)]:
 with tarfile.open(P/(label+'-source.tar.gz'),'r:gz')as archive:
  assert sorted(archive.getnames())==sorted(manifest)
  for member in archive:
   assert member.isfile()and member.name in manifest;assert sha(archive.extractfile(member).read())==manifest[member.name]
assert {n:sha((R/'vm'/n).read_bytes())for n in base}==base
assert json.loads((P/'reversal.json').read_bytes())['all132Restored']
assert json.loads((P/'cleanup.json').read_bytes())['live132UnchangedAfterCleanup']
assert not(P/'.scratch').exists()
result=json.loads((P/'result.json').read_bytes());assert result['counts']['candidateSwift']==356
for group in ['generic-private','generic-integration']:
 assert sha((P/f'commands/baseline-{group}/stdout.txt').read_bytes())==sha((P/f'commands/candidate-{group}/stdout.txt').read_bytes())
print(json.dumps({'sealedMembers':len(seal['members']),'live132Unchanged':True,'bothCompleteSourceArchivesVerified':True,'scope':'frozen finite provisional evidence only; no full schema/replay/target acceptance'},sort_keys=True))
