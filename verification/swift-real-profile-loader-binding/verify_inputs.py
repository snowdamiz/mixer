"""Read-only frozen input/source custody verification."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;ROOT=Path('/Users/andreyyurlov/Documents/dev/mixer')
def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):return json.loads(p.read_bytes())
def check_packet(name,digest):
 folder=ROOT/'verification'/name;assert sha((folder/'seal.json').read_bytes())==digest
 seal=read(folder/'seal.json');members={m['path']:m for m in seal['members']};assert len(members)==seal['member_count']
 assert {str(p.relative_to(folder))for p in folder.rglob('*')if p.is_file()}==set(members)|{'seal.json'}
 for name,m in members.items():
  b=(folder/name).read_bytes();assert len(b)==m['bytes']and sha(b)==m['sha256'],name
 return {'path':str(folder.relative_to(ROOT)),'seal_sha256':digest,'members':len(members),'bytes':sum(m['bytes']for m in members.values()),'exact_set_and_all_hashes':True}
def main():
 results=[]
 for name,digest in [('swift-typed-result-codec-implementation','4f5e0ffd63c343511948d1bacc933698cd36369f94b3b96f3047ff325cd94b86'),('swift-typed-result-codec-independent','8f22a9842cb609027d6f6cbe808eefb13d56cd52b68ef6cddec9a9926f5fc16b'),('swift-retained-profile-real-binding-preparation','e6e4b3b1d32ade11ef3136f3e4416e86bb8c0a32889af6bbe62a1799cb093b01'),('swift-retained-profile-real-binding-contract-review','2b94fd0095c898f427809b8f088d5dc2708cdc3f33c8b12bd9936bb10da4d60e')]:results.append(check_packet(name,digest))
 original=ROOT/'verification/swift-initial-profile-construction-implementation';assert sha((original/'seal.json').read_bytes())=='50d1c32174ee4cbcade6095039261ea0ff8eed05680322bfb59b5de0dd4cd8b1';sealed={m['path']:m for m in read(original/'seal.json')['members']}
 for filename in ['source-manifest-attempt-12.json','host-support-manifest.json']:
  b=(original/filename).read_bytes();assert sha(b)==sealed[filename]['sha256']and len(b)==sealed[filename]['bytes']
 source=read(original/'source-manifest-attempt-12.json');support=read(original/'host-support-manifest.json');assert source['member_count']==140 and support['member_count']==11
 for m in source['members']:
  b=(original/'source/vm'/m['path']).read_bytes();assert sha(b)==m['sha256']and len(b)==m['bytes']
 for m in support['members']:
  b=(original/m['retained_path']).read_bytes();assert sha(b)==m['sha256']and len(b)==m['bytes'];b=(HERE/m['retained_path']).read_bytes();assert sha(b)==m['sha256']and len(b)==m['bytes']
 own=read(HERE/'source-manifest.json');assert own['member_count']==144
 expected={m['path']:m for m in own['members']};assert {str(p.relative_to(HERE/'source/vm'))for p in (HERE/'source/vm').rglob('*')if p.is_file()}==set(expected)
 for name,m in expected.items():
  b=(HERE/'source/vm'/name).read_bytes();assert sha(b)==m['sha256']and len(b)==m['bytes']
 baseline=read(HERE/'baseline-source-manifest.json');base={m['path']:m for m in baseline['members']}
 assert set(expected)-set(base)=={'src/experimental_swift_reactor/retained_profile_loader_v1.rs','src/experimental_swift_reactor/retained_profile_loader_v1_tests.rs'}
 assert [name for name in base if base[name]!=expected[name]]==['src/experimental_swift_reactor/mod.rs']
 print(json.dumps({'frozen_packets':results,'accepted_original_source140_support11_verified':True,'own_source144_exact':True,'only_prior_file_delta':'private module declaration','own_host11_unchanged':True,'source_tree_sha256':own['tree_sha256']},sort_keys=True))
if __name__=='__main__':main()
