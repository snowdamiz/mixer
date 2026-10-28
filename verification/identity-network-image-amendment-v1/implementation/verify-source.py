#!/usr/bin/env python3
"""Bounded source-only verification; no container/product/native execution."""
from pathlib import Path
import ast,hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[3]
BASE=Path(__file__).resolve().parent
PATHS=['hosted/scripts/test-identity-network.py','hosted/scripts/test_identity_network_collector.py','.github/workflows/identity-network.yml','docs/hosted-identity-production-network-ci-contract.md','THIRD_PARTY.yml']
def row(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def canonical(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def test_methods(src):
 return {c.name+'.'+n.name:ast.get_source_segment(src,n) for c in ast.parse(src).body if isinstance(c,ast.ClassDef) for n in c.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')}
before=test_methods((BASE/'before'/PATHS[1]).read_text());after=test_methods((ROOT/PATHS[1]).read_text())
assert len(before)==68
changed=[name for name,body in before.items() if after.get(name)!=body];assert not changed
parsed=ast.parse((ROOT/PATHS[0]).read_text())
manifest=next(ast.literal_eval(n.value) for n in parsed.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='FROZEN_MANIFEST' for t in n.targets))
assert len(manifest)==177
head=subprocess.run(['git','--no-replace-objects','rev-parse','HEAD','HEAD^{tree}'],cwd=ROOT,check=True,capture_output=True,timeout=5).stdout.decode().splitlines()
refs=''.join(head[0]+':'+path+'\n' for path in sorted(manifest)).encode()
batch=subprocess.run(['git','--no-replace-objects','cat-file','--batch'],cwd=ROOT,input=refs,check=True,capture_output=True,timeout=10).stdout
observed={};offset=0
for path in sorted(manifest):
 end=batch.index(b'\n',offset);header=batch[offset:end].split();assert len(header)==3 and header[1]==b'blob';count=int(header[2]);body=batch[end+1:end+1+count];assert batch[end+1+count:end+2+count]==b'\n';offset=end+2+count;observed[path]=row(body)
assert offset==len(batch) and observed==manifest
assert canonical(observed)=='023df04c9a4599c3d5a6cdf2afb53a95e2faf37765d8b96ba2bcc0e1b007c92e'
oldbase=ROOT/'verification/identity-production-network-contract';packet=json.loads((oldbase/'packet-manifest.json').read_bytes())
assert canonical(packet['files'])=='a3a806d83e285213df4c0e951282686dcfcfa81701e8005040d5172b3300050d'
for path,expected in packet['files'].items():assert row((oldbase/path).read_bytes())==expected,path
protected={path:row((ROOT/path).read_bytes()) for path in ['.github/workflows/hosted.yml','hosted/lib/mixer_hosted/browser_auth/store.ex']}
assert protected['.github/workflows/hosted.yml']['sha256']=='fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57'
assert protected['hosted/lib/mixer_hosted/browser_auth/store.ex']['sha256']=='8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299'
inventory_before=(BASE/'before/THIRD_PARTY.yml').read_text();inventory_after=(ROOT/'THIRD_PARTY.yml').read_text();assert inventory_before.split('# Selected by')[0] in inventory_after and inventory_after.endswith('# Selected by'+inventory_before.split('# Selected by',1)[1])
workflow=(ROOT/PATHS[2]).read_text();assert workflow.count("      - 'verification/identity-network-image-amendment-v1/**'")==2;assert workflow.count('            /verification/identity-network-image-amendment-v1/metadata/**')==1
new={path:row((ROOT/path).read_bytes()) for path in PATHS}
(BASE/'source-bindings.json').write_text(json.dumps(new,indent=2,sort_keys=True)+'\n')
record={'scope':'offline source and pure-control decisions only','python':sys.version,'source_HEAD':head[0],'source_git_tree':head[1],'canonical_changed_source_tree_digest_sha256':canonical(new),'existing_controls':len(before),'existing_controls_body_changes':changed,'new_controls':len(after)-len(before),'total_controls':len(after),'frozen_product_files':177,'committed_product_source_digest_sha256':canonical(observed),'old_contract_complete_packet_files_rehashed':len(packet['files']),'protected_live_sources':protected,'inventory_prior_entries_preserved':True,'workflow_amendment_both_filters_and_metadata_sparse_checkout':True,'runtime_qualification':False}
(BASE/'source-checks.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n');print(json.dumps(record,indent=2,sort_keys=True))
