#!/usr/bin/env python3
"""Offline source/custody verification; only bounded, explicitly readonly Git children."""
from pathlib import Path
import ast, hashlib, io, json, subprocess, sys, tarfile, zipfile
BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
PATHS = ['hosted/scripts/test-identity-network.py', 'hosted/scripts/test_identity_network_collector.py', 'docs/hosted-identity-production-network-ci-contract.md']
def row(b): return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def canon(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def write(p,v): p.parent.mkdir(exist_ok=True,parents=True);p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
def methods(s): return {c.name+'.'+n.name:ast.get_source_segment(s,n) for c in ast.parse(s).body if isinstance(c,ast.ClassDef) for n in c.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')}
prior_source=(BASE/'before'/PATHS[0]).read_text();current_source=(ROOT/PATHS[0]).read_text()
prior=ast.parse(prior_source); current=ast.parse(current_source)
before=methods((BASE/'before'/PATHS[1]).read_text());after=methods((ROOT/PATHS[1]).read_text())
assert len(before)==111 and len(after)==126 and all(after[name]==body for name,body in before.items())
def assignments(tree):
 result={}
 for n in tree.body:
  if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name):
   try: result[n.targets[0].id]=ast.literal_eval(n.value)
   except (ValueError,TypeError): pass
 return result
def assigned_nodes(tree): return {n.targets[0].id:ast.dump(n.value) for n in tree.body if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name)}
old_nodes,new_nodes=assigned_nodes(prior),assigned_nodes(current)
assert all(new_nodes[key]==value for key,value in old_nodes.items() if key!='MANIFEST_EXS')
old,new=assignments(prior),assignments(current)
assert old.keys() <= new.keys()
changed_constants=[key for key in old if old[key] != new[key]]
assert changed_constants==['MANIFEST_EXS'],changed_constants
assert set(new)-set(old)=={'GENERATED_DAG_PATH','MAX_GENERATED_DAG_BYTES','GENERATED_DAG_PARENTS','TELEMETRY_INPUTS'}
def function_source(s,t,c,n): return ast.get_source_segment(s,next(f for cls in t.body if isinstance(cls,ast.ClassDef) and cls.name==c for f in cls.body if isinstance(f,ast.FunctionDef) and f.name==n))
for name in ('copy_file_out','copy_in','execute','create','stop_remove','cleanup','seal'):
 assert function_source(prior_source,prior,'Collector',name)==function_source(current_source,current,'Collector',name),name
for name in ('validate_source_manifest','validate_source_unchanged','validate_prepared_archive','validate_transfer_archive','validate_environment','validate_events'):
 a=next(n for n in prior.body if isinstance(n,ast.FunctionDef) and n.name==name)
 b=next(n for n in current.body if isinstance(n,ast.FunctionDef) and n.name==name)
 assert ast.get_source_segment(prior_source,a)==ast.get_source_segment(current_source,b),name
commands=[]
def git(args,timeout=10,data=None):
 argv=['git','--no-replace-objects',*args];r=subprocess.run(argv,cwd=ROOT,input=data,capture_output=True,check=True,timeout=timeout);commands.append({'argv':argv,'timeout_seconds':timeout,'exit_code':r.returncode});return r.stdout
head=git(['rev-parse','HEAD','HEAD^{tree}'],5).decode().splitlines();version=git(['--version'],5).decode().strip()
manifest=new['FROZEN_MANIFEST'];refs=''.join(head[0]+':'+name+'\n' for name in sorted(manifest)).encode();batch=git(['cat-file','--batch'],10,refs)
observed={};offset=0
for name in sorted(manifest):
 end=batch.index(b'\n',offset);header=batch[offset:end].split();assert len(header)==3 and header[1]==b'blob';size=int(header[2]);body=batch[end+1:end+1+size];assert batch[end+1+size:end+2+size]==b'\n';offset=end+2+size;observed[name]=row(body)
assert offset==len(batch) and observed==manifest and len(manifest)==177 and canon(manifest)=='023df04c9a4599c3d5a6cdf2afb53a95e2faf37765d8b96ba2bcc0e1b007c92e'
expected_packets={
 'identity-production-network-contract':'a3a806d83e285213df4c0e951282686dcfcfa81701e8005040d5172b3300050d',
 'identity-network-image-prerequisite-review':'261023b77cb55255f666959f367330783a354174252ed23b71145566f87ba597',
 'identity-network-image-amendment-v1':'c6116eb09de8bdd75ac3f3036c469efed7e11f6beef4210e9577ff9b72cd392c',
 'identity-network-image-amendment-v2':'878b66c7e21a5ca2da2b8fdc97275f302abc99da450c9acf9429bfdaaa78149a',
 'github-delivery-runtime-followup/network-review':'69832104e969c2746dc99edda71c86961b84c05c1576da1368b19a72fa2e3bb1',
 'github-delivery-binary-export-and-ui/network-review':None}
# The latest tree is verified against its exact caller-supplied manifest bytes too.
latest=ROOT/'verification/github-delivery-binary-export-and-ui/network-review';latest_raw=(latest/'packet-manifest.json').read_bytes();assert hashlib.sha256(latest_raw).hexdigest()=='148912f1c031a1bdd757376436cd4959235b170f7dd2ae60e6c38df2d6a96d8c'
expected_packets['github-delivery-binary-export-and-ui/network-review']=json.loads(latest_raw)['tree_digest_sha256']
immutable={}
for folder,digest in expected_packets.items():
 base=ROOT/'verification'/folder;seal=(base/'packet-manifest.json').read_bytes();packet=json.loads(seal);assert canon(packet['files'])==packet['tree_digest_sha256']==digest
 for name,expected in packet['files'].items(): assert row((base/name).read_bytes())==expected,name
 immutable[folder]={'files':len(packet['files']),'tree_digest_sha256':digest,'packet_manifest':row(seal),'all_files_rehashed':True}
assert immutable['github-delivery-binary-export-and-ui/network-review']['files']==483
protected_expected={'.github/workflows/hosted.yml':'fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57','hosted/lib/mixer_hosted/browser_auth/store.ex':'8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299','.github/workflows/identity-network.yml':'4b5fa14bfa80601354bd063f3e93f728fa1175e52de3d5c6bcc62a99b044eb19','THIRD_PARTY.yml':'27b3d9becb46e9207903119f00c634276033fa595709f65c87276acab5ff7085'}
protected={p:row((ROOT/p).read_bytes()) for p in protected_expected};assert all(protected[p]['sha256']==h for p,h in protected_expected.items())
# Preserve only selected existing public evidence, never the unavailable DAG.
proof=BASE/'proof';proof.mkdir(exist_ok=True)
for name in ('decision.json','manifest-diff.json','verification-result.json','packet-manifest.json','selected/artifact/prepared-manifest.json','selected/artifact/logs/0089.json','selected/artifact/logs/0089.stdout','selected/artifact/logs/0089.stderr'):
 b=(latest/name).read_bytes();p=proof/'runtime-review'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
prepared=json.loads((latest/'selected/artifact/prepared-manifest.json').read_bytes())
with tarfile.open(latest/'selected/artifact/prepared-source-dependencies-tools.tar',mode='r:') as archive:
 for path,expected in new['TELEMETRY_INPUTS'].items():
  member=archive.getmember(path);assert member.isfile() and member.size<=65536
  body=archive.extractfile(member).read();assert row(body)==expected==prepared['deps'][path]
  destination=proof/'locked-inputs'/path;destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(body)
rebar=(latest/'selected/artifact/bootstrap-rebar-3.28.0').read_bytes();assert len(rebar)==823379 and hashlib.sha512(rebar).hexdigest()==new['BOOTSTRAP']['rebar']['sha512']
literals={}
with zipfile.ZipFile(io.BytesIO(rebar)) as archive:
 for name in ('rebar/ebin/rebar_compiler_dag.beam','rebar/ebin/rebar_dir.beam'):
  member=archive.getinfo(name);assert member.file_size<=65536;body=archive.read(member);assert body[:4]==b'FOR1' and body[8:12]==b'BEAM';offset=12;chunk=None
  while offset<len(body):
   tag=body[offset:offset+4];size=int.from_bytes(body[offset+4:offset+8],'big');data=body[offset+8:offset+8+size];assert len(data)==size
   if tag==b'LitT':chunk=data
   offset+=8+(size+3)//4*4
  assert offset==len(body) and chunk is not None and len(chunk)<=65536
  tokens=[b'source.dag',b'.dag',b'source',b'compressed'] if 'compiler_dag' in name else [b'_build',b'lib',b'.rebar3']
  assert all(token in chunk for token in tokens)
  p=proof/'pinned-rebar-literals'/(Path(name).stem+'.LitT.bin');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(chunk)
  literals[name]={'beam':row(body),'literal_table':row(chunk),'tokens_present':[t.decode() for t in tokens],'scope':'inert literal presence corroborates names only; no BEAM dataflow, ETF or generated DAG interpretation'}
write(BASE/'source-support.json',{'rebar':{**row(rebar),'sha512':hashlib.sha512(rebar).hexdigest()},'literal_tables':literals,'locked_telemetry_inputs':new['TELEMETRY_INPUTS'],'unknown_prior_dag_bytes_available':False,'classification':'bounded exact-phase/path hypothesis; fresh Linux metadata/runtime evidence pending'})
bindings={p:row((ROOT/p).read_bytes()) for p in PATHS}
for p in PATHS:
 b=(ROOT/p).read_bytes();d=BASE/'after'/p;d.parent.mkdir(parents=True,exist_ok=True);d.write_bytes(b)
write(BASE/'source-bindings.json',bindings)
result={'scope':'source and Python pure controls only','python':sys.version,'git_version':version,'HEAD':head[0],'git_tree':head[1],'commands':commands,'canonical_source_tree_digest_sha256':canon(bindings),'prior_tests':len(before),'all111_prior_test_bodies_unchanged':True,'new_tests':len(after)-len(before),'total_tests':len(after),'changed_existing_literal_constants':changed_constants,'old_MANIFEST_EXS':row(old['MANIFEST_EXS'].encode()),'new_MANIFEST_EXS':row(new['MANIFEST_EXS'].encode()),'all_other_existing_literal_constants_unchanged':True,'original_copy_export_allowlist_and_method_unchanged':True,'prepared_archive_and_exact_equality_validator_bodies_unchanged':True,'frozen_product_files':177,'frozen_product_digest_sha256':canon(manifest),'immutable_packets':immutable,'unchanged_workflow_inventory_and_protected_sources':protected,'runtime_qualification':False}
write(BASE/'source-checks.json',result);print(json.dumps(result,sort_keys=True,indent=2))
