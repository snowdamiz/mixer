#!/usr/bin/env python3
"""Freeze owned packet after a successful real run; never grants product/root acceptance."""
import datetime,hashlib,json,pathlib,sys
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def dump(path,v):path.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
run=HERE/sys.argv[1]
r=json.loads((run/'receipt.json').read_text());t=json.loads((run/'tests.json').read_text())
assert r['passed'] and t['summary']=={'total':41,'failures':0,'skipped':0,'excluded':0}
assert all(r['cleanup'][k] for k in ['owned_proxy_stopped','owned_postgres_stopped','owned_scratch_removed','owned_socket_removed'])
runs=[]
for candidate in sorted(HERE.glob('run-*'),key=lambda p:int(p.name.split('-')[1])):
 item=json.loads((candidate/'receipt.json').read_text())
 runs.append({'run':candidate.name,'passed':item['passed'],'test_summary':item.get('test_summary'),'error':item['error'],'cleanup':item['cleanup']})
commands=json.loads((run/'commands.json').read_text())
versions=[{'argv':c['argv'],'stdout':c.get('stdout'),'stderr':c.get('stderr'),'returncode':c.get('returncode')} for c in commands if any(v in c['argv'] for v in ['--version','version'])]
receipt={'schema':1,'status':'producer-preimplementation-primitive-recommended-for-root-review','scope':'synthetic local PostgreSQL17/Elixir atomic-storage, codec/budget and local blob development fixture only','frozen_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'passing_run':run.name,'observed_head':r['observed_head'],'probe_source_tree_digest':r['probe_source_tree_digest'],'summary':t['summary'],'all_attempts':runs,'tool_versions':versions,'dependency_baseline':r['baseline_revision'],'dependency_additions':False,'root_acceptance':False,'product_implementation':False,'migration':False,'http_provider_ga_acceptance':False,'legacy_source_manifest':str((run/'legacy-source-manifest.json').relative_to(HERE)),'limitations':['synthetic identity/policy/clock/opaque artifact bytes; not full resolver or v3 admission','fixed tenant/target fixture RLS; full target-aware product policies/constraints/startup inspector pending','coordinator timestamp seam uses fixture99; actual ConfiguredVerifier integration pending','Agent cap4 only accepted in-flight references; mailbox/HTTP/cancellation/lifetime integration pending','owned local single-process blobs; trusted directory listing, no power-loss/R2/multi-host durability','terminal event linkage and generated fixed display mapping only; full historical chain/closed public decoder pending','no Oban job insert, domain/job atomicity and G24 pending','controlled completed-server-COMMIT acknowledgement drop; arbitrary cancellation/provider timing pending','no Linux/provider/native/physical/FieldLog/GA qualification']}
dump(HERE/'receipt.json',receipt)
paths=[ROOT/'docs/hosted-atomic-storage-preflight.md']+[p for p in HERE.rglob('*') if p.is_file() and p.name not in ['artifact-manifest.json','seal.json','integrity-output.log'] and '__pycache__' not in p.parts]
manifest={'schema':1,'files':[{'path':str(p.relative_to(ROOT)),'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size} for p in sorted(paths)]}
dump(HERE/'artifact-manifest.json',manifest)
dump(HERE/'seal.json',{'schema':1,'status':receipt['status'],'passing_run':run.name,'manifest_sha256':sha((HERE/'artifact-manifest.json').read_bytes()),'bindings':len(manifest['files']),'source_tree_digest':r['probe_source_tree_digest'],'scope':receipt['scope'],'root_accepted':False})
print(json.dumps({'passing_run':run.name,'bindings':len(manifest['files']),'source_tree_digest':r['probe_source_tree_digest'],'root_accepted':False}))
