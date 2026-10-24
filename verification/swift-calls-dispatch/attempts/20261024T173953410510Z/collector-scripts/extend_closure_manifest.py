import collect as c
import json,gzip
out=[]
for features in ['swift','all']:
 for profile in ['debug','release']:
  cfg=f'{features}-{profile}-unit';q=json.loads((c.HERE/f'exact-query-{cfg}.json').read_text());raw=gzip.decompress((c.HERE/q['attempt']/'exact-layouts.jsonl.gz').read_bytes());assert c.sha(raw)==q['sha256'];rs=[json.loads(l)for l in raw.decode().splitlines()];bodies={(r['path'],r['promoted']):r for r in rs if r['kind']=='body'}
  selected=[r for r in rs if r['kind']=='local' and r['path'].endswith('::{constant#0}') and r['local']in [2,3]];assert len(selected)==6
  for r in selected:
   b=bodies[(r['path'],r['promoted'])];assert r['layout']['identity'].startswith('Closure(')
   for role in ['source','argument','returned','caller']:
    tls=r['path'].split('::tests::')[1].split('::')[0]
    out.append({'field':f'compiler_discovered_{cfg.replace("-","_")}_{tls}_{r["local"]}_{role}','config':cfg,'body':r['path'],'bodyDefPathHash':b['defPathHash'],'bodySHA256':c.sha(b['mir'].encode()),'local':r['local'],'position':role,'actualType':r['layout']['type'],'actualIdentity':r['layout']['identity'],'layout':r['layout'],'sourceInfo':r['sourceInfo'],'queryAttempt':q['attempt'],'querySHA256':q['sha256'],'sourceClosure':q['sourceClosure'],'method':'finite-numeric-exact-compiler-identity-acceptance-pending'})
assert len(out)==96
c.save(c.HERE/'compiler-discovered-closure-positions.json',out);print(c.sha((c.HERE/'compiler-discovered-closure-positions.json').read_bytes()))
