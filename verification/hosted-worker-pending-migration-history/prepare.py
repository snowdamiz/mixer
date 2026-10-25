from pathlib import Path
import json,hashlib,shutil
root=Path(__file__).resolve().parents[2];packet=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
producer=root/'verification/hosted-worker-pending-terminal-consistency';review=root/'verification/hosted-worker-pending-terminal-consistency-review'
expected={producer:'e4afac5866c26ffd96c460bbdd54e3cf0098bc1d378601ba7e542d6f819e677b',review:'2a5646144c8696d6ff2c02d935a6942a18d61dd0c5f8ddf7e99314f5aa0dab13'}
checks=[]
for base,digest in expected.items():
 assert sha((base/'receipt.json').read_bytes())==digest
 for p in sorted(base.rglob('*')):
  if p.is_file():
   assert not any(x in str(p.relative_to(base)).lower() for x in ['inspector','authority-driver','outbound-transport'])
   b=p.read_bytes();checks.append({'path':str(p.relative_to(root)),'sha256':sha(b),'bytes':len(b)})
manifest=json.loads((producer/'source-manifest.json').read_text());assert manifest['sourceDigest']=='b46bac2e4377663e2df078743c655c062f42cc92893a3d53b702476b05b6966f'
for e in manifest['entries']:
 b=(producer/'candidate'/e['path']).read_bytes();assert sha(b)==e['sha256'] and len(b)==e['bytes']
 for dst in [packet/'inputs/producer'/e['path'],packet/'candidate'/e['path']]:dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(b)
for name in ['test/worker.ts','test/harness.mjs','test/independent.mjs']:
 b=(review/'candidate'/name).read_bytes()
 for dst in [packet/'inputs/review'/name,packet/'candidate'/name]:dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(b)
p=packet/'candidate/test/harness.mjs';p.write_text(p.read_text().replace('mixer-pending-terminal-review-owned-','mixer-pending-migration-history-owned-'))
(packet/'input-manifest.json').write_text(json.dumps({'schema':1,'frozenProducerReceiptSHA256':expected[producer],'frozenProducerSourceDigest':manifest['sourceDigest'],'frozenReviewReceiptSHA256':expected[review],'checks':checks},indent=2)+'\n')
print(json.dumps({'frozenSourceEntries':len(manifest['entries']),'frozenFiles':len(checks)}))
