#!/usr/bin/env python3
"""Verify frozen candidate bindings without booting PostgreSQL or changing files."""
import hashlib,json,pathlib,sys
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 manifest=json.loads((HERE/'artifact-manifest.json').read_text());seen=set()
 for x in manifest['files']:
  assert x['path'] not in seen,x['path'];seen.add(x['path']);p=ROOT/x['path'];b=p.read_bytes();assert len(b)==x['bytes'] and sha(b)==x['sha256'],x['path']
 actual={str(p.relative_to(ROOT)) for p in HERE.rglob('*') if p.is_file() and p.name!='artifact-manifest.json'}
 expected={x for x in seen if x.startswith(str(HERE.relative_to(ROOT))+'/')};assert actual==expected,{'extra':sorted(actual-expected),'missing':sorted(expected-actual)}
 receipt=json.loads((HERE/'receipt.json').read_text());latest=HERE/receipt['final_run'];r=json.loads((latest/'receipt.json').read_text());s=json.loads((latest/'summary.json').read_text());assert r['success'] and s['passed']==s['total']==receipt['tests_passed'] and not s['failed'];assert r['source_digest']==receipt['source_digest']
 for attempt in receipt['attempts']:
  a=json.loads((HERE/attempt['run']/'receipt.json').read_text());assert a['success']==attempt['success'];assert a['cleanup']['owned_cluster_stopped'] and a['cleanup']['owned_scratch_removed'];assert not pathlib.Path(a['scratch']).exists()
 src=json.loads((latest/'source-manifest.json').read_text());assert sha(json.dumps(src,sort_keys=True,separators=(',',':')).encode())==r['source_digest']
 for x in src:
  b=(HERE/x['path']).read_bytes();assert sha(b)==x['sha256'] and len(b)==x['bytes'];assert (latest/'source'/pathlib.Path(x['path']).name).read_bytes()==b
 for x in json.loads((latest/'input-manifest.json').read_text()):assert sha((latest/'inputs'/x['path']).read_bytes())==x['sha256']
 c=json.loads((latest/'catalog.json').read_text());assert len(c['tables'])==14 and len(c['types'])==6 and len(c['functions'])==10;assert all(t['rls'] and t['force'] for t in c['tables']);assert all(not f['public_execute'] for f in c['functions']);assert sum(f['runtime_execute'] for f in c['functions'])==3 and sum(f['writer_execute'] for f in c['functions'])==1
 print(json.dumps({'integrity':'passed','bindings':len(seen),'final_run':receipt['final_run'],'tests':s['passed'],'source_digest':r['source_digest'],'all_owned_cleanup':True,'scope':'isolated prerequisite only; acceptance and product migration pending'},indent=2))
if __name__=='__main__':main()
