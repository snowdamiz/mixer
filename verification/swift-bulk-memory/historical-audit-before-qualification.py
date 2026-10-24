from pathlib import Path
import importlib.util,json,re,sys,gzip
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE));import inventory as bulk
enc=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
schema=json.loads((HERE/'inventory-schema.json').read_text())
spec=importlib.util.spec_from_file_location('accepted_memory_inventory',HERE/'inputs/accepted-memory-inventory.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
old_schema=json.loads((HERE/'inputs/accepted-memory-schema.json').read_text());assert len(old_schema)==4800
keys=['field','rustType','binding','sourceNames','mirFunction','position','config','kind','envelope','window']
def projected(rows):return [{k:r.get(k)for k in keys}for r in rows]
audit=[]
for features,stage in [('all','sealed'),('swift','sealed-swift')]:
 for config in ['production','unit']:
  path=HERE/(stage+'-'+config+'.mir.gz')
  rows,functions,captures=bulk.canonical(path,config)
  expected=[r for r in schema if r['config']==config]
  assert projected(rows)==projected(expected),(features,config,'new canonical disagreement')
  prior,_,_=old.canonical(path,config);prior_expected=[r for r in old_schema if r['config']==config]
  assert projected(prior)==projected(prior_expected),(features,config,'accepted canonical changed')
  promotions=[f for f in functions if '::promoted['in f['function']]
  if config=='unit':assert any(f['function']=='bulk_memory_pinned_step::promoted[0]'for f in promotions)
  assert all('::tests::'not in f['function']for f in functions)
  audit.append(dict(features=features,config=config,positiveCanonicalFields=len(rows),functions=len(functions),promotions=promotions,acceptedMemoryCanonicalFields=len(prior),captures=captures))
(HERE/'canonical-audit.json').write_bytes(enc(audit))
# Regress standalone promotion selection independently of containing module text.
assert bulk.selected('bulk_memory_pinned_step::promoted[0]')
assert not bulk.selected('bulk_memory_operations::tests::fixture::promoted[0]')
assert not bulk.selected('memory_pinned_step::promoted[0]')
(HERE/'collector-regressions.json').write_bytes(enc(dict(passed=3,standalonePromotion=True,testPromotionExcluded=True,existingMemoryNotBorrowedAsCredit=True)))
print('four exact canonical configurations and all 4800 accepted rows retained; promotions and three selection regressions pass')
