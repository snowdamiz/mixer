"""Read-only packet/closure verifier, not execution or full replay acceptance."""
from pathlib import Path
import hashlib,json,tarfile
P=Path(__file__).resolve().parent;R=P.parents[1]
def sha(raw):return hashlib.sha256(raw).hexdigest()
seal=json.loads((P/'seal.json').read_bytes());assert sha((P/'seal.json').read_bytes())==(P/'seal.sha256').read_text().strip()
for item in seal['members']:
    f=R/item['path'];raw=f.read_bytes();assert f.is_file()and not f.is_symlink()and len(raw)==item['bytes']and sha(raw)==item['sha256'],item['path']
for side in ('baseline','candidate'):
    manifest=json.loads((P/(side+'-manifest.json')).read_bytes());assert len(manifest)==132
    with tarfile.open(P/(side+'-source.tar.gz'),'r:gz')as archive:
        assert sorted(archive.getnames())==sorted(manifest)
        for f in archive:assert f.isfile()and sha(archive.extractfile(f).read())==manifest[f.name]
base=json.loads((P/'baseline-manifest.json').read_bytes());assert {n:sha((R/'vm'/n).read_bytes())for n in base}==base
assert not(P/'.scratch').exists()and json.loads((P/'cleanup.json').read_bytes())['ownedScratchRemoved']
assert json.loads((P/'reversal.json').read_bytes())['all132Restored']
for f in (P/'streams').rglob('*.sidecar.json'):
    s=json.loads(f.read_bytes());assert(s['status'],s['failure'])==('invalid',15)and'fullReplayAccepted'not in s
print(json.dumps({'sealedMembers':len(seal['members']),'bothComplete132ArchivesVerified':True,'live132Unchanged':True,'scope':'frozen finite packet; independent acceptance/full replay/target still pending'},sort_keys=True))
