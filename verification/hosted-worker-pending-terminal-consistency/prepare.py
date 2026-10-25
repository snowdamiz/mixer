from pathlib import Path
import json,hashlib,shutil
root=Path(__file__).resolve().parents[2]; packet=Path(__file__).resolve().parent
frozen=root/'verification/hosted-worker-pending-registry-track-recheck'; review=root/'verification/hosted-worker-pending-registry-track-review'
sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha((frozen/'receipt.json').read_bytes())=='d9bd48d069746b24ed3386e9842a1693e5aba44c33ffd4e095646acaef7cff5c'
assert sha((frozen/'track-recheck.patch').read_bytes())=='a7876fc0786f53ea3e201a1969a3f90a07a0c48c71e2602151f5a4ee7ac64372'
assert sha((review/'receipt.json').read_bytes())=='f9b18c8fe622e14964abcb7e41ba046e1ef4e48cf81b80c22c457fa7bb7f13d1'
manifest=json.loads((frozen/'runs/20261025T052136773Z/source-manifest.json').read_text());assert manifest['sourceDigest']=='f4290d7ab0ece9eb2546d9b6125054d6cbbd4d9ab572d418679fbc41e748b799'
entries=[]
for e in manifest['entries']:
 b=(frozen/'candidate'/e['path']).read_bytes();assert sha(b)==e['sha256'] and len(b)==e['bytes'];entries.append(e)
 for dest in [packet/'inputs/frozen-candidate'/e['path'],packet/'candidate'/e['path']]:dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b)
assert sha(''.join(f"{e['path']}\0{e['sha256']}\0{e['bytes']}\n" for e in entries).encode())==manifest['sourceDigest']
for name in ['test/worker.ts','test/review.mjs','test/snapshot-consistency.mjs']:
 dst=packet/'inputs/review'/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(review/'candidate'/name,dst)
# Prior 81 driver remains byte-identical; augment only excluded Worker with the review controls.
shutil.copy2(review/'candidate/test/worker.ts',packet/'candidate/test/worker.ts');shutil.copy2(review/'candidate/test/review.mjs',packet/'candidate/test/review.mjs')
p=packet/'candidate/test/harness.mjs';p.write_text(p.read_text().replace('mixer-pending-track-recheck-owned-','mixer-pending-terminal-consistency-owned-'))
# Bind all predecessor packet files, including failed historical runs, without executing their scripts.
checks=[]
for base in [frozen,review]:
 for p in sorted(base.rglob('*')):
  if p.is_file():b=p.read_bytes();checks.append({'path':str(p.relative_to(root)),'sha256':sha(b),'bytes':len(b)})
(packet/'input-manifest.json').write_text(json.dumps({'schema':1,'frozenSourceDigest':manifest['sourceDigest'],'checks':checks},indent=2)+'\n')
print(json.dumps({'frozenSourceFilesVerified':len(entries),'packetInputFilesBound':len(checks),'copiedFrozenSourceDigest':manifest['sourceDigest']}))
