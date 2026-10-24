from run import *
import importlib.util,collections
sys.dont_write_bytecode=True
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
bulk=load('review_bulk_inventory',PACKET/'inventory.py');old=load('review_old_inventory',PACKET/'inputs/accepted-memory-inventory.py')
schema=json.loads((PACKET/'inventory-schema.json').read_text());old_schema=json.loads((PACKET/'inputs/accepted-memory-schema.json').read_text())
keys=['field','rustType','binding','sourceNames','mirFunction','position','config','kind','envelope','window']
project=lambda rows:[{k:r.get(k)for k in keys}for r in rows]
report=[]
for features,flags in [('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
 for config in ['production','unit']:
  name='fresh-mir-'+features+'-'+config;target=SCRATCH/('target-'+name)
  args=['cargo','rustc','--lib','--locked','--offline',*flags,'--','--emit=mir','-Zmir-include-spans=yes']if config=='production'else['cargo','test','--lib','--no-run','--locked','--offline',*flags]
  extra={'RUSTC_BOOTSTRAP':'1','CARGO_TARGET_DIR':str(target)}
  if config=='unit':extra['RUSTFLAGS']='--emit=mir,link -Zmir-include-spans=yes'
  p=run(name,args,SCRATCH/'candidate',extra) if not (HERE/'commands'/name/'receipt.json').exists() else None
  assert p is None or p.returncode==0
  paths=list((target/'debug/deps').glob('mixer_vm*.mir'));assert len(paths)==1,paths
  content=paths[0].read_bytes();dest=HERE/(name+'.mir.gz');dest.write_bytes(gzip.compress(content,mtime=0))
  rows,functions,captures=bulk.canonical(dest,config);assert project(rows)==project([r for r in schema if r['config']==config])
  prior,_,_=old.canonical(dest,config);expected=project([r for r in old_schema if r['config']==config]);actual=project(prior);assert len(actual)==len(expected)
  delta=[]
  prefix='experimental_swift_reactor::execution::frame_operations::'
  for a,b in zip(actual,expected):
   changes={k:[a[k],b[k]]for k in keys if a[k]!=b[k]}
   if changes:
    assert set(changes)=={'mirFunction'},changes
    assert a['mirFunction']==prefix+b['mirFunction']and b['mirFunction'].startswith('memory_operations::'),changes
    delta.append(dict(field=a['field'],**changes))
  assert len(delta)==(1672 if config=='unit'else 0),len(delta)
  # Separately enumerate raw function AND const headers; promotions are not
  # inferred solely from the production collector's selected-function list.
  text=content.decode();raw=[]
  for line in text.splitlines():
   if not (line.startswith('fn ')or line.startswith('const ')):continue
   if 'bulk_memory_'in line and '::tests::'not in line and '::tests}'not in line:raw.append(line)
  standalone=[h for h in raw if h.startswith('const bulk_memory_pinned_step::promoted[')]
  preflight=[h for h in raw if 'bulk_memory_preflight' in h and h.startswith('const ')]
  assert set(h.split('(',1)[0][3:]if h.startswith('fn ')else h[6:].split(': &',1)[0]for h in raw)==set(f['function']for f in functions)
  assert preflight and (bool(standalone)==(config=='unit')),(features,config,raw)
  report.append(dict(features=features,config=config,mirSHA256=hashlib.sha256(content).hexdigest(),fields=len(rows),oldFields=len(prior),qualificationOnlyDelta=delta,functions=functions,captures=captures,rawHeaders=raw,standalonePromotions=standalone,preflightPromotions=preflight))
  (HERE/'canonical-results.json').write_bytes(enc(report))
print('PASS fresh 4 canonical compiler inventories, all retained rows, exact qualification delta, standalone and closure promotions')
