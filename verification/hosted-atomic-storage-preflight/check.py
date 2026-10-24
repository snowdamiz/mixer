#!/usr/bin/env python3
"""Read-only packet verifier. Does not rerun tests or grant release/root acceptance."""
import hashlib,json,pathlib,sys
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):return json.loads(p.read_text())
seal=read(HERE/'seal.json');manifest=read(HERE/'artifact-manifest.json');receipt=read(HERE/'receipt.json')
assert sha((HERE/'artifact-manifest.json').read_bytes())==seal['manifest_sha256'],'manifest binding'
seen=set()
for item in manifest['files']:
 p=ROOT/item['path'];assert p.is_file(),f'missing {p}'
 assert len(p.read_bytes())==item['bytes'] and sha(p.read_bytes())==item['sha256'],f'drift {p}'
 assert item['path'] not in seen;seen.add(item['path'])
assert len(seen)==seal['bindings']
run=HERE/receipt['passing_run'];r=read(run/'receipt.json');t=read(run/'tests.json')
assert r['passed'] and t['summary']==receipt['summary']=={'total':41,'failures':0,'skipped':0,'excluded':0}
for item in receipt['all_attempts']:
 c=item['cleanup'];assert all(c[k] for k in ['owned_proxy_stopped','owned_postgres_stopped','owned_scratch_removed','owned_socket_removed'])
 assert not pathlib.Path(c['owned_scratch']).exists(),'scratch still exists'
 assert not c['other_clusters_touched'] and not c['native_processes_started']
source=read(run/'source-manifest.json')
assert sha(json.dumps(source,sort_keys=True,separators=(',',':')).encode())==r['probe_source_tree_digest']==seal['source_tree_digest']
for item in source:
 assert sha((HERE/item['path']).read_bytes())==item['sha256'],'current producer source drift'
 assert sha((run/'inputs'/item['path']).read_bytes())==item['sha256'],'frozen run source drift'
for item in read(run/'contract-inputs.json'):
 assert sha((run/'inputs'/'contracts'/item['path']).read_bytes())==item['sha256'],'captured input drift'
proxy=[json.loads(line) for line in (run/'proxy.jsonl').read_text().splitlines()]
assert any(e.get('dropped')=='COMMIT CommandComplete' and e['server_commit_completed'] and not e['client_ack_sent'] for e in proxy),'wire COMMIT observation'
commands=read(run/'commands.json')
assert all(c.get('returncode')==0 for c in commands if c['argv'][:2] in [['go','test'],['go','run']]),'Go preservation checks'
assert sum(c['argv'][:2]==['go','test'] for c in commands)==1 and sum(c['argv'][:2]==['go','run'] for c in commands)==1
v=read(HERE/'probe/golden-vectors.json')
for key,domain in [('initial','mixer.hosted.state.v1'),('transition','mixer.hosted.state.v1'),('event','mixer.hosted.audit.v1')]:
 assert sha(domain.encode()+b'\0'+bytes.fromhex(v[key]['cbor_hex']))==v[key]['sha256'],f'{key} standard SHA256 vector'
legacy=read(HERE/'probe/legacy-golden.json');assert sha(legacy['preimage'].encode())==legacy['hash']
assert legacy['final']==legacy['preimage'][:-2]+legacy['hash']+'"}'
c=read(HERE/'contract-manifest.json')
assert len(c['product']['context_fields'])==9 and c['product']['context_fields'][-1]=='authentication_completed_at:numeric(20,0)'
assert not receipt['root_acceptance'] and not receipt['product_implementation'] and not seal['root_accepted']
print(json.dumps({'verified':True,'bindings':len(seen),'passing_run':run.name,'tests':t['summary'],'source_tree_digest':r['probe_source_tree_digest'],'all_owned_cleanup_verified':True,'scope':receipt['scope'],'root_accepted':False}))
