#!/usr/bin/env python3
from pathlib import Path
import datetime,hashlib,json
base=Path(__file__).resolve().parent
excluded={'inputs','tree','target','target-mir-unit','__pycache__'}
rows=[]
for path in sorted(base.rglob('*')):
 if not path.is_file() or path.name=='seal.json':continue
 relative=path.relative_to(base)
 if any(part in excluded for part in relative.parts):continue
 rows.append({'path':str(relative),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size})
digest=hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()
seal=base/'seal.json'
if seal.exists():
 previous=json.loads(seal.read_text());assert previous['files']==rows and previous['artifact_tree_digest_sha256']==digest,'Sealed evidence changed'
 print(json.dumps({'status':'verified','files':len(rows),'artifact_tree_digest_sha256':digest}));raise SystemExit(0)
result={'schema':'mixer-swift-construction-independent-review-seal-v1','sealed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'artifact_tree_digest_sha256':digest,'files':rows,'excluded_local_only':sorted(excluded),'source_authority':'Original frozen inputs remain in deterministic snapshots/*.tar.gz and per-snapshot manifests. Copied source/build trees are not evidence authority.','root_acceptance':False}
seal.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':'sealed','files':len(rows),'artifact_tree_digest_sha256':digest,'seal_sha256':hashlib.sha256(seal.read_bytes()).hexdigest()}))
