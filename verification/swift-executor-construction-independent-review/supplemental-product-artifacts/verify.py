#!/usr/bin/env python3
"""Verify the unchanged original evidence and this separate appended seal."""
from pathlib import Path
import datetime,hashlib,json,sys
out=Path(__file__).resolve().parent;base=out.parent
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
original_sha='81e5c76ec4f169978e9bed534c4b22bc97788dbd585a62d7af3432655a9a5099'
assert sha(base/'seal.json')==original_sha
original=json.loads((base/'seal.json').read_text())
for row in original['files']:assert sha(base/row['path'])==row['sha256'],row['path']
rows=[{'path':str(path.relative_to(out)),'sha256':sha(path),'bytes':path.stat().st_size}for path in sorted(out.rglob('*'))if path.is_file()and path.name!='seal.json']
digest=hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()
seal=out/'seal.json'
if '--seal'in sys.argv:
 assert not seal.exists(),'Do not overwrite supplemental seal'
 seal.write_text(json.dumps({'schema':'mixer-swift-construction-independent-supplemental-seal-v1','sealed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'original_seal_sha256':original_sha,'original_entries_verified_unchanged':len(original['files']),'artifact_tree_digest_sha256':digest,'files':rows},indent=2)+'\n')
else:
 frozen=json.loads(seal.read_text());assert frozen['original_seal_sha256']==original_sha;assert frozen['files']==rows;assert frozen['artifact_tree_digest_sha256']==digest
expected={row['path']for row in original['files']}|{'seal.json'}|{str(path.relative_to(base))for path in out.rglob('*')if path.is_file()}
actual={str(path.relative_to(base))for path in base.rglob('*')if path.is_file()and not any(part in set(original['excluded_local_only'])for part in path.relative_to(base).parts)}
assert expected==actual,('Unexpected file extension',sorted(actual-expected),sorted(expected-actual))
print(json.dumps({'status':'verified-original-and-supplement','original_entries_unchanged':len(original['files']),'supplement_entries':len(rows),'supplement_tree_sha256':digest,'supplement_seal_sha256':sha(seal)}))
