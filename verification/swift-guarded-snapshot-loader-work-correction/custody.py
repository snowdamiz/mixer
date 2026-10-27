"""Read-only frozen input custody; no original producer script is imported."""
import gzip,hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent;R=D.parents[1];BASE=D.parent/'swift-guarded-snapshot-loader-work'
EXPECTED_SEAL='0550b44baf9f576d8379e1dd93f89ea9bd5b48ff7367762ae008181d29d2c30c'
FINDING=R/'verification/swift-semantic-adapter-root-review/guarded-snapshot-loader-work-callback-finding.json'
EXPECTED_FINDING='aac057a0cf4727a054a8998a02a0fd6da947ed15ac978e8080fe017c83b784ed'
def sha(data):return hashlib.sha256(data).hexdigest()
def verify_inputs():
 b=(BASE/'seal.json').read_bytes()
 if sha(b)!=EXPECTED_SEAL:raise ValueError('producer-seal-changed')
 seal=json.loads(b);total=0
 for row in seal['members']:
  rel=Path(row['path'])
  if rel.is_absolute() or '..' in rel.parts:raise ValueError('bad-seal-member')
  p=BASE/rel
  if p.is_symlink():raise ValueError('symlink-member')
  data=p.read_bytes()
  if len(data)!=row['bytes'] or sha(data)!=row['sha256']:raise ValueError('producer-member-changed:'+str(rel))
  total+=len(data)
 if len(seal['members'])!=46 or total!=9071546:raise ValueError('producer-cardinality')
 finding=FINDING.read_bytes()
 if sha(finding)!=EXPECTED_FINDING:raise ValueError('root-finding-changed')
 x=json.loads((BASE/'mir-extraction.json').read_text())
 selected=gzip.decompress((BASE/'selected-definitions.mir.gz').read_bytes())
 raw=gzip.decompress((BASE/'whole-source.mir.gz').read_bytes())
 if sha(selected)!=x['selected_sha256'] or sha(raw)!=x['parent_mir_sha256']:raise ValueError('MIR-parent-binding')
 return dict(schema=1,producer_seal_sha256=EXPECTED_SEAL,members_verified=46,member_bytes_verified=total,
  root_finding_sha256=EXPECTED_FINDING,source_members=145,host_support_members=11,
  source_tree_sha256='450b6d9b3a05d160e19fa888b68173286b8f6af20ecc7216fdf86283f09b308a',
  parent_mir_sha256=x['parent_mir_sha256'],selected_mir_sha256=x['selected_sha256'],definitions=len(x['functions']),
  producer_imported_or_replayed=False,full_source_MIR_duplicated=False,compiler_executed=False,product_runtime=False)
if __name__=='__main__':print(json.dumps(verify_inputs(),sort_keys=True,indent=2))
