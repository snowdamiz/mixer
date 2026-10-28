#!/usr/bin/env python3
"""Bounded offline source checks; only read-only Git child calls are allowed."""
from pathlib import Path
import ast,hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
PATHS=['hosted/scripts/test-identity-network.py','hosted/scripts/test_identity_network_collector.py','.github/workflows/identity-network.yml','docs/hosted-identity-production-network-ci-contract.md']
def row(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def canon(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def methods(src):return {c.name+'.'+n.name:ast.get_source_segment(src,n) for c in ast.parse(src).body if isinstance(c,ast.ClassDef) for n in c.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')}
before=methods((BASE/'before'/PATHS[1]).read_text());after=methods((ROOT/PATHS[1]).read_text());assert len(before)==84
original=methods((ROOT/'verification/identity-network-image-amendment-v1/implementation/before'/PATHS[1]).read_text());assert len(original)==68
assert all(after[name]==body for name,body in original.items())
changed=[name for name,body in before.items() if after.get(name)!=body];assert changed==['CollectorMethodWiringControls.test_collect_requires_actual_prepare_result_before_bootstrap']
manifest=next(ast.literal_eval(n.value) for n in ast.parse((ROOT/PATHS[0]).read_text()).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='FROZEN_MANIFEST' for t in n.targets))
head=subprocess.run(['git','--no-replace-objects','rev-parse','HEAD','HEAD^{tree}'],cwd=ROOT,capture_output=True,check=True,timeout=5).stdout.decode().splitlines()
refs=''.join(head[0]+':'+name+'\n' for name in sorted(manifest)).encode();batch=subprocess.run(['git','--no-replace-objects','cat-file','--batch'],cwd=ROOT,input=refs,capture_output=True,check=True,timeout=10).stdout
observed={};offset=0
for name in sorted(manifest):
 end=batch.index(b'\n',offset);header=batch[offset:end].split();assert len(header)==3 and header[1]==b'blob';size=int(header[2]);body=batch[end+1:end+1+size];assert batch[end+1+size:end+2+size]==b'\n';offset=end+2+size;observed[name]=row(body)
assert offset==len(batch) and observed==manifest and len(manifest)==177 and canon(manifest)=='023df04c9a4599c3d5a6cdf2afb53a95e2faf37765d8b96ba2bcc0e1b007c92e'
immutable={}
for folder,digest in [('identity-production-network-contract','a3a806d83e285213df4c0e951282686dcfcfa81701e8005040d5172b3300050d'),('identity-network-image-prerequisite-review','261023b77cb55255f666959f367330783a354174252ed23b71145566f87ba597'),('identity-network-image-amendment-v1','c6116eb09de8bdd75ac3f3036c469efed7e11f6beef4210e9577ff9b72cd392c')]:
 base=ROOT/'verification'/folder;packet=json.loads((base/'packet-manifest.json').read_bytes());assert canon(packet['files'])==packet['tree_digest_sha256']==digest
 for name,expected in packet['files'].items():assert row((base/name).read_bytes())==expected,name
 immutable[folder]={'files':len(packet['files']),'tree_digest_sha256':digest,'all_files_rehashed':True}
checks={name:row((ROOT/name).read_bytes()) for name in ['THIRD_PARTY.yml','.github/workflows/hosted.yml','hosted/lib/mixer_hosted/browser_auth/store.ex']};old=json.loads((BASE/'before-manifest.json').read_bytes())
assert all(checks[name]==old[name] for name in checks)
workflow=(ROOT/PATHS[2]).read_text();assert workflow.count("      - 'verification/identity-network-image-amendment-v2/**'")==2 and workflow.count('            /verification/identity-network-image-amendment-v2/metadata/**')==1
bindings={name:row((ROOT/name).read_bytes()) for name in PATHS};(BASE/'source-bindings.json').write_text(json.dumps(bindings,sort_keys=True,indent=2)+'\n')
result={'scope':'source and Python pure controls only; no runtime acceptance','python':sys.version,'HEAD':head[0],'git_tree':head[1],'changed_canonical_source_tree_digest_sha256':canon(bindings),'frozen_product_files':len(manifest),'frozen_product_tree_digest_sha256':canon(manifest),'prior_tests':len(before),'original_68_test_bodies_unchanged':True,'v1_test_body_adaptations':changed,'v1_test_adaptation_scope':'Represent new prior mount gate and v2 metadata while keeping old prerequisite-refusal assertion and no-bootstrap checks.','new_tests':len(after)-len(before),'total_tests':len(after),'immutable_packets':immutable,'unchanged_protected_and_inventory':checks,'workflow_both_filters_and_sparse_path':True,'runtime_qualification':False}
(BASE/'source-checks.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print(json.dumps(result,sort_keys=True,indent=2))
