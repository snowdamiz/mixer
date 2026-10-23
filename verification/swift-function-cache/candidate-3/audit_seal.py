#!/usr/bin/env python3
"""Read-only source/artifact/archive audit with a separate immutable result."""
from pathlib import Path
import datetime,hashlib,json,tarfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text())
def verify(bindings):
 for path,expected in bindings.items():assert sha(ROOT/path)==expected,path
 return len(bindings)
def archive_source(directory):
 freeze=read(directory/'source-freeze.json')
 with tarfile.open(directory/'frozen-source.tar.gz','r:gz')as archive:
  members=archive.getmembers();assert len(members)==len(freeze['source_manifest'])
  for member in members:
   assert member.isfile()and member.name in freeze['source_manifest']
   assert hashlib.sha256(archive.extractfile(member).read()).hexdigest()==freeze['source_manifest'][member.name]
 return len(members)
producer_path=HERE/'producer-receipt.json';producer=read(producer_path);freeze=read(HERE/'source-freeze.json')
assert producer['source_manifest_sha256']==freeze['source_manifest_sha256']
counts={'producer_artifacts':verify(producer['bindings']),'current_source_files':verify(freeze['source_manifest']),'candidate3_archive_files':archive_source(HERE)}
prior=read(HERE/'prior-candidate-preservation.json');counts['candidate2_artifacts']=verify(prior['candidate2_artifacts']);counts['candidate2_archive_files']=archive_source(HERE.parent/'candidate-2')
preserved=read(HERE.parent/'candidate-1/preservation-map.json')
for kind in ['source','evidence']:
 for row in preserved[kind].values():assert sha(ROOT/row['preserved'])==row['sha256']
 counts['candidate1_'+kind]=len(preserved[kind])
record={'schema':'mixer-swift-cache-candidate3-seal-audit-v1','observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'all_bound_artifacts_current_source_and_preserved_prior_bytes_match','scope':'No historical C2 exact-source acceptance is extended to C3; independent/root C3 review remains separate.','verified':counts,'bindings':{str(p.relative_to(ROOT)):sha(p)for p in [producer_path,HERE/'source-freeze.json',HERE/'prior-candidate-preservation.json',Path(__file__).resolve()]}}
out=HERE/'seal-audit.json';assert not out.exists();out.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({'sha256':sha(out),'verified':counts},indent=2))
