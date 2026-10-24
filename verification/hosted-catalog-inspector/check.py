#!/usr/bin/env python3
"""Read-only frozen packet verification. Starts no database/process service."""
import ast,copy,gzip,hashlib,json,pathlib,sys,tarfile
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def js(p):return json.loads(p.read_bytes())
r=js(HERE/'receipt.json');assert sha((HERE/'artifact-manifest.json').read_bytes())==r['artifact_manifest_sha256']
bindings=js(HERE/'artifact-manifest.json')
for x in bindings:
 p=(ROOT/x['path']).resolve();assert ROOT in p.parents and p.is_file();assert p.stat().st_size==x['bytes'] and sha(p.read_bytes())==x['sha256'],x['path']
assert len(bindings)==r['artifact_bindings']
for x in js(HERE/'input-manifest.json'):
 assert sha((HERE/x['copy']).read_bytes())==x['sha256']
 # Frozen originals in this packet remain byte-bound. Reused original evidence
 # is independently covered by root's retained245+6 checker output.
 assert sha((ROOT/x['path']).read_bytes())==x['sha256'],x['path']
assert r['baseline_sha256']=='78c0c8a56c6d358eda1e8a183176d5fe7b7e67e9427bdeb4aa1bb308dfaa8e6e'
assert r['observer_profile_sha256']=='a63e1af41935f1a283618d2601e1b072762355059ca25b3782df6518da02d395'
baseline=(HERE/'component/priv/selected-expected.json').read_bytes();profile=(HERE/'component/priv/observer-profile.json').read_bytes();assert sha(baseline)==r['baseline_sha256'] and sha(profile)==r['observer_profile_sha256']
x=json.loads(baseline);delta=js(HERE/'observer-profile-delta.json');assert len(delta['operations'])==1;op=delta['operations'][0];assert op['path']==['legacy','database','acl'];assert x['legacy']['database']['acl']==op['from'];assert op['to']==op['from'][:-1]+',catalog_inspector_observer=c/andreyyurlov}';x['legacy']['database']['acl']=op['to'];assert profile==(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
tree=ast.parse((HERE/'inputs/oracle/inspector.py').read_text());original=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SESSION' for t in n.targets));assert (HERE/'component/priv/session-original.sql').read_text()==original+'\n';qualified=original
for name in ['jsonb_build_object','current_setting','current_database']:qualified=qualified.replace(name+'(','pg_catalog.'+name+'(')
assert (HERE/'component/priv/session.sql').read_text()==qualified+'\n' and qualified.replace('pg_catalog.','')==original
run=HERE/r['final_attempt'];assert sha((run/'receipt.json').read_bytes())==r['final_attempt_receipt_sha256'];attempt=js(run/'receipt.json');assert attempt['success'] and attempt['source_digest']==r['source_digest']
sources=js(run/'source-manifest.json');deps=js(run/'dependency-manifest.json');assert sha(json.dumps(sources,sort_keys=True,separators=(',',':')).encode())==r['source_digest'];assert sha(json.dumps(deps,sort_keys=True,separators=(',',':')).encode())==r['dependency_digest']
with tarfile.open(run/'source-and-dependencies.tar.gz','r:gz') as arc:
 for x in sources+[{**d,'path':'component/deps/'+d['path']} for d in deps]:
  b=arc.extractfile(x['path']).read();assert len(b)==x['bytes'] and sha(b)==x['sha256'],x['path']
 component=js(HERE/'candidate-source-manifest.json');assert {x['path']:x for x in component}=={x['path']:x for x in sources if x['path'].startswith('component/')}
 for x in component:assert sha((HERE/x['path']).read_bytes())==x['sha256']
 for x in js(HERE/'dependency-disposition/manifest.json'):
  b=arc.extractfile('component/deps/'+x['dependency_path']).read();assert sha(b)==x['source_sha256'];lo,hi=x['lines'];lines=b.decode().splitlines();s='\n'.join(f'{i}: {lines[i-1]}' for i in range(lo,hi+1))+'\n';assert (HERE/'dependency-disposition'/x['excerpt']).read_text()==s
for command in js(run/'commands.json'):
 assert command['exit_code']==0
 assert sha((run/command['log']).read_bytes())==command['log_sha256']
outcomes=[js(p) for p in (run/'evidence').glob('*-outcome.json')];assert len(outcomes)==17 and all(x['passed'] for x in outcomes)
assert js(run/'evidence/elixir-models.json')['total']==1257
assert js(run/'evidence/atom-models.json')['atoms_before']==js(run/'evidence/atom-models.json')['atoms_after']
for label in ['elixir-models','atom-models','transport-models','canonical-models']:assert js(run/'evidence'/f'{label}.json')['passed']
sys.path.insert(0,str(HERE/'inputs/oracle'));import inspector
raw=inspector.decode(gzip.decompress((run/'evidence/baseline-capture.json.gz').read_bytes()));assert inspector.validate(raw,json.loads(profile))==json.loads(profile)
try:inspector.validate(raw,json.loads(baseline))
except ValueError:pass
else:raise AssertionError('oldbaseline acceptedobserverCONNECT')
star=inspector.decode(gzip.decompress((run/'evidence/literal-star-capture.json.gz').read_bytes()));inspector.validate_raw(star)
for key in ['independent_review_accepted','root_accepted','hosted_installed','production_provisioned','ga_accepted']:assert r[key] is False
assert r['immediate_backend_cleanup_on_unavailable_return'] is False
assert r['cleanup']['owned_cluster_stopped'] and r['cleanup']['owned_scratch_removed']
assert not r['cleanup']['tcp_listener_opened'] and not r['cleanup']['other_processes_touched'] and not r['cleanup']['native_or_phone_runs']
print(json.dumps({'verified':True,'artifact_bindings':len(bindings),'unique_raw_models':1257,'actual_postgres_groups':17,'baseline_preserved':True,'observer_profile_pending_independent_review':True,'live_integrated':False,'ga_accepted':False}))
