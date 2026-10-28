#!/usr/bin/env python3
"""Source-only checks and bounded readonly Git; no product/runtime execution."""
from pathlib import Path
import ast,hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
PATHS=['hosted/scripts/test-identity-network.py','hosted/scripts/test_identity_network_collector.py','docs/hosted-identity-production-network-ci-contract.md']
def row(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def canon(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def methods(src):return {c.name+'.'+n.name:ast.get_source_segment(src,n) for c in ast.parse(src).body if isinstance(c,ast.ClassDef) for n in c.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')}
before=methods((BASE/'before'/PATHS[1]).read_text());after=methods((ROOT/PATHS[1]).read_text());assert len(before)==103 and all(after[name]==body for name,body in before.items())
prior=ast.parse((BASE/'before'/PATHS[0]).read_text());current=ast.parse((ROOT/PATHS[0]).read_text())
constants=['FROZEN_PRODUCT_DIGEST','FROZEN_LOCK_SHA256','CONTRACT_SHA256','CONTRACT_PACKET','CONTRACT_PACKET_SHA256','AMENDMENT_SHA256','AMENDMENT_PACKET','SOURCE_REVIEW_PACKET','EXECUTION_SHA256','EXECUTION_PACKET','EXECUTION_PACKET_SHA256','IMAGES','BOOTSTRAP','RESOURCES','OLD_TMPFS','TMPFS','MOUNT_POLICY','REBAR_TRANSFER','CAPS','BASE_ENV','FROZEN_MANIFEST','PREREQUISITES_EXS','BOOTSTRAP_EXS','MOUNTS_EXS','MANIFEST_EXS','NETNS_EXS','OBSERVER_EXS','MAX_COMMAND_BYTES','MAX_LOG_BYTES','MAX_ARCHIVE_BYTES','MAX_ARTIFACT_BYTES']
def values(tree):return {n.targets[0].id:ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in constants}
old_values,new_values=values(prior),values(current);assert old_values==new_values and set(old_values)==set(constants)
manifest=new_values['FROZEN_MANIFEST'];assert len(manifest)==177
head=subprocess.run(['git','--no-replace-objects','rev-parse','HEAD','HEAD^{tree}'],cwd=ROOT,capture_output=True,check=True,timeout=5).stdout.decode().splitlines()
refs=''.join(head[0]+':'+name+'\n' for name in sorted(manifest)).encode();batch=subprocess.run(['git','--no-replace-objects','cat-file','--batch'],cwd=ROOT,input=refs,capture_output=True,check=True,timeout=10).stdout
observed={};offset=0
for name in sorted(manifest):
 end=batch.index(b'\n',offset);header=batch[offset:end].split();assert len(header)==3 and header[1]==b'blob';size=int(header[2]);body=batch[end+1:end+1+size];assert batch[end+1+size:end+2+size]==b'\n';offset=end+2+size;observed[name]=row(body)
assert offset==len(batch) and observed==manifest and canon(manifest)=='023df04c9a4599c3d5a6cdf2afb53a95e2faf37765d8b96ba2bcc0e1b007c92e'
immutable={}
for folder,digest in [('identity-production-network-contract','a3a806d83e285213df4c0e951282686dcfcfa81701e8005040d5172b3300050d'),('identity-network-image-prerequisite-review','261023b77cb55255f666959f367330783a354174252ed23b71145566f87ba597'),('identity-network-image-amendment-v1','c6116eb09de8bdd75ac3f3036c469efed7e11f6beef4210e9577ff9b72cd392c'),('identity-network-image-amendment-v2','878b66c7e21a5ca2da2b8fdc97275f302abc99da450c9acf9429bfdaaa78149a'),('github-delivery-runtime-followup/network-review','69832104e969c2746dc99edda71c86961b84c05c1576da1368b19a72fa2e3bb1')]:
 base=ROOT/'verification'/folder;packet=json.loads((base/'packet-manifest.json').read_bytes());assert canon(packet['files'])==packet['tree_digest_sha256']==digest
 for name,expected in packet['files'].items():assert row((base/name).read_bytes())==expected,name
 immutable[folder]={'files':len(packet['files']),'tree_digest_sha256':digest,'all_files_rehashed':True}
old=json.loads((BASE/'before-manifest.json').read_bytes());unchanged={name:row((ROOT/name).read_bytes()) for name in ['.github/workflows/identity-network.yml','THIRD_PARTY.yml','.github/workflows/hosted.yml','hosted/lib/mixer_hosted/browser_auth/store.ex']};assert all(old[name]==body for name,body in unchanged.items())
# The source path allowlist and original cap gate remain exactly the first two
# decisions in copy_file_out; no new input path is admitted.
def copy_method(tree):return next(n for c in tree.body if isinstance(c,ast.ClassDef) and c.name=='Collector' for n in c.body if isinstance(n,ast.FunctionDef) and n.name=='copy_file_out')
assert [ast.dump(n) for n in copy_method(prior).body[:2]]==[ast.dump(n) for n in copy_method(current).body[:2]]
bindings={name:row((ROOT/name).read_bytes()) for name in PATHS};(BASE/'source-bindings.json').write_text(json.dumps(bindings,sort_keys=True,indent=2)+'\n')
result={'scope':'source and Python pure controls only','python':sys.version,'HEAD':head[0],'git_tree':head[1],'canonical_source_tree_digest_sha256':canon(bindings),'prior_tests':len(before),'all103_prior_test_bodies_unchanged':True,'new_tests':len(after)-len(before),'total_tests':len(after),'preserved_collector_constant_count':len(constants),'original_copy_path_and_cap_admission_unchanged':True,'frozen_product_files':177,'frozen_product_digest_sha256':canon(manifest),'immutable_packets':immutable,'unchanged_workflow_inventory_and_protected_sources':unchanged,'copy_callers':['Hex public bootstrap /workspace/downloads/hex.ez <=16MiB','Rebar public bootstrap /workspace/tooling/rebar3 <=16MiB','prepared tar /workspace/prepared.tar <=512MiB','events /workspace/evidence/events.jsonl <=2MiB','two fixed semantic JSON files under /workspace/evidence/identity <=8MiB each','runtime identity /workspace/evidence/runtime.json <=8MiB'],'runtime_qualification':False}
(BASE/'source-checks.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print(json.dumps(result,sort_keys=True,indent=2))
