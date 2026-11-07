"""Compiler-reconciled exact typed / finite numeric positive accounting.
No closure tuples, Infallible, pointer erasure, padding credit or old-row reuse.
The earlier parser/declaration attempt remains immutable and unaccepted.
"""
import collect as c
import inventory as v
import json,gzip,re,collections
ROLES=['source','argument','returned','caller']
P=v.PREFIX

def body_name(text):
 h=text.splitlines()[0]
 if h.startswith('fn '):return h[3:h.index('(')]
 return re.fullmatch(r'(?:(?:const|static) )?(.+): (.+) = \{',h)[1]
def canon(name):
 if name.startswith(('memory_growth_operations::','host_runtime_import::')):return P.removesuffix('call_dispatch::')+name
 if name.split('::')[0] in v.FREE:return P+name
 if name.split('::')[0] in ['CHECK_COUNT','CANCEL_AT']:return P+'tests::'+name
 return name

def normal(ty):
 assert '{closure@' not in ty and ty!='!'
 bound=set(re.findall(r"'[A-Za-z_][A-Za-z_0-9]*",' '.join(re.findall(r'for<([^>]+)>',ty))))
 ty=re.sub(r"'[A-Za-z_][A-Za-z_0-9]*",lambda m:m[0] if m[0] in bound else "'static",ty)
 # normalize only accessible paths and lifetimes; preserve HRTB binders.
 for name,target in [('experimental_swift_reactor::','crate::experimental_swift_reactor::'),('experimental_wasi::','crate::experimental_wasi::'),('experimental::','crate::experimental::'),('descriptors::','crate::experimental::descriptors::'),('control::','crate::experimental_swift_reactor::control::'),('accounted::','crate::experimental_wasi::accounted::')]:ty=re.sub(r'(?<![:\w])'+name,target,ty)
 ty=ty.replace('crate::experimental_wasi::descriptor::WasiFunction','crate::experimental_wasi::WasiFunction').replace('std::sync::atomic::Atomic<bool>','std::sync::atomic::AtomicBool')
 for name in ['SwiftGrowthContext','SwiftGrowthStorage','GrowthCompletion']:ty=re.sub(r'(?<![:\w])'+name+r'\b','crate::experimental_swift_reactor::execution::frame_operations::memory_growth_operations::'+name,ty)
 ty=re.sub(r'(?<![:\w])Cell<','std::cell::Cell<',ty);ty=re.sub(r'(?<![:\w])LocalKey<','std::thread::LocalKey<',ty);ty=re.sub(r'(?<![:\w])execute::Cancellation','crate::Cancellation',ty)
 return re.sub(r"&(?!(?:'|\s*'))","&'static ",ty)

def query(cfg):
 q=json.loads((c.HERE/f'exact-query-{cfg}.json').read_text());assert q['exitCode']==0
 raw=gzip.decompress((c.HERE/q['attempt']/'exact-layouts.jsonl.gz').read_bytes());assert c.sha(raw)==q['sha256']
 rs=[json.loads(x)for x in raw.decode().splitlines()];bodies={};locals={};fn=[];fixtures=[];closures={}
 for r in rs:
  if r['kind']=='body':
   k=(r['path'],r['promoted']);assert k not in bodies;bodies[k]=dict(r,name=body_name(r['mir']))
  if r['kind']=='local':
   k=(r['path'],r['promoted'],r['local']);assert k not in locals;locals[k]=r
   if r['layout']['identity'].startswith('Closure('):closures[r['layout']['identity']]=r['layout']
  if r['kind']=='FnDef':fn.append(r)
  if r['kind']=='fixture-body':fixtures.append(r)
 named={canon(b['name']):k for k,b in bodies.items()};assert len(named)==len(bodies)
 return q,bodies,locals,named,fn,fixtures,closures

def main():
 old=json.loads((c.HERE/'inventory-schema.json').read_text());groups=json.loads((c.HERE/'unnameable-positions.json').read_text())
 private_fields={p['field']for g in groups if g['type']!='!' and not g['type'].startswith('std::sync::Arc<') and '::execution::Kind'not in g['type'] for p in g['positions']};assert len(private_fields)==248
 extension={r['field']:r for r in json.loads((c.HERE/'compiler-discovered-closure-positions.json').read_text())};assert len(extension)==96
 allrows=[];headers=[];implicit=[];contexts={};raw_query_bindings={}
 for f in ['swift','all']:
  for profile in ['debug','release']:
   for unit in ['production','unit']:
    cfg=f'{f}-{profile}-{unit}';q,bodies,locals,named,fns,fixtures,closures=query(cfg);contexts[cfg]=(q,bodies,locals,named,closures);raw_query_bindings[cfg]=q
    for b in bodies.values():headers.append({'config':cfg,'body':b['path'],'promoted':b['promoted'],'name':b['name'],'header':b['mir'].splitlines()[0],'defPathHash':b['defPathHash'],'bodySHA256':c.sha(b['mir'].encode()),'canonicalLocals':[n for (path,p,n)in locals if path==b['path'] and p==b['promoted']],'partition':'unit-runtime-hook'if'::tests::'in b['path']else'admitted-product','querySHA256':q['sha256']})
    headers.extend(dict(config=cfg,partition='fixture-only-outside-admitted-execution',**x)for x in fixtures)
    implicit.extend(dict(config=cfg,querySHA256=q['sha256'],**x)for x in fns)
    rows=[dict(r)for r in old if r['config']==cfg];covered=set()
    for r in rows:
     name=canon(r['function']);assert name in named,(cfg,name)
     k=named[name];b=bodies[k];r.update(body=b['path'],promoted=b['promoted'],bodyDefPathHash=b['defPathHash'],bodySHA256=c.sha(b['mir'].encode()),querySHA256=q['sha256'])
     if r['kind']=='canonical':idx=int(r['binding'][1:]);covered.add((*k,idx))
     elif r['kind']=='authored-alias':
      matches=re.findall(r'debug '+re.escape(r['source'])+r' => (_\d+);',b['mir']);idx=int(r['field'].rsplit('_',3)[1]);assert '_'+str(idx) in matches,(r,matches)
     elif r['kind']=='captured-alias':idx=1
     elif r['kind']=='literal':idx=None
     else:raise AssertionError(r)
     if idx is not None:
      lr=locals[(*k,idx)];r.update(local=idx,sourceInfo=lr['sourceInfo'],actualIdentity=lr['layout']['identity'],actualType=lr['layout']['type'])
      if r['kind']=='captured-alias':
       ident=lr['layout']['identity'];ident=ident[ident.index('Closure('):] if 'Closure('in ident else ident
       if ident not in closures and ident.endswith(')'):ident=ident[:-1]
       assert ident in closures,(r['field'],ident)
       field=int(r['binding'].split('_')[1]);fl=closures[ident]['fields'][field];r.update(capture=field,actualIdentity=fl['identity'],actualType=fl['type'])
     if r['mirType']=='!':r['method']='exact-inferred-never'
     elif '::execution::Kind'in r['type']:r['method']='exact-defining-module-kind'
     elif r['field']in private_fields:r['method']='finite-numeric-private-std'
     elif '{closure@'in r['mirType']:r['method']='finite-numeric-actual-closure'
     else:r['method']='exact-typed'
     allrows.append(r)
    for lk,lr in locals.items():
     if lk in covered:continue
     k=lk[:2];b=bodies[k];decl=dict(re.findall(r'let (?:mut )?(_\d+): ([^\n]+);',b['mir']));rawty=decl['_'+str(lr['local'])]
     # Every missing canonical local is retained explicitly; no matching by spelling alone.
     for role in ROLES:
      if '{closure@'in rawty:
       tls=b['path'].split('::tests::')[1].split('::')[0];field=f'compiler_discovered_{cfg.replace("-","_")}_{tls}_{lr["local"]}_{role}';assert field in extension
       ex=extension[field];assert ex['actualIdentity']==lr['layout']['identity'] and ex['bodyDefPathHash']==b['defPathHash'];method='finite-numeric-actual-closure-extension'
      else:field=f'compiler_discovered_{cfg.replace("-","_")}_{len(allrows)}_{lr["local"]}_{role}';method='exact-typed'
      allrows.append({'field':field,'type':None,'mirType':rawty,'binding':'_'+str(lr['local']),'kind':'compiler-discovered-canonical','position':role,'config':cfg,'function':b['name'],'header':b['mir'].splitlines()[0],'unitOnly':unit=='unit','body':b['path'],'promoted':b['promoted'],'bodyDefPathHash':b['defPathHash'],'bodySHA256':c.sha(b['mir'].encode()),'querySHA256':q['sha256'],'local':lr['local'],'sourceInfo':lr['sourceInfo'],'actualIdentity':lr['layout']['identity'],'actualType':lr['layout']['type'],'method':method})
    assert len(covered)==len({(*named[canon(r['function'])],int(r['binding'][1:]))for r in rows if r['kind']=='canonical'})
 permanent=[dict(r,method='exact-typed')for r in old if r['config']=='source']
 assert len({r['field']for r in allrows+permanent})==len(allrows)+len(permanent)
 assert sum(r['method']=='finite-numeric-private-std'for r in allrows)==248
 assert sum(r['method']=='finite-numeric-actual-closure'for r in allrows)==560
 assert sum(r['method']=='finite-numeric-actual-closure-extension'for r in allrows)==96
 assert sum(r['method']=='exact-inferred-never'for r in allrows)==432
 assert sum(r['method']=='exact-defining-module-kind'for r in allrows)==16
 numeric=[];offsets={False:0,True:0}
 for r in allrows:
  if not r['method'].startswith('finite-numeric'):continue
  q,bodies,locals,named,closures=contexts[r['config']];layout=locals[(r['body'],r['promoted'],r['local'])]['layout'];assert layout['identity']==r['actualIdentity']
  a=layout['alignment'];n=layout['bytes'];assert a>0 and a&(a-1)==0 and n>=0
  start=(offsets[r['unitOnly']]+a-1)//a*a;end=start+n;assert end<2**64;offsets[r['unitOnly']]=end
  numeric.append(dict(r,layout=layout,relativeOffset=start,exclusiveEnd=end,component='unit-numeric'if r['unitOnly']else'production-numeric'))
 code=['// Exact typed declarations. Finite numeric authority is a separate additive component.']
 def cls(name,rs,ty_override=None):
  out=['#[allow(dead_code)]','pub(super) struct '+name+' {']
  for r in rs:
   if r['unitOnly']:out.append('    #[cfg(test)]')
   out.append('    '+r['field']+': '+(ty_override or normal(r['mirType'] if 'mirType'in r else r['type']))+',')
  return out+['}']
 code+=cls('CallsActivePositions',[r for r in allrows if r['method']=='exact-typed'])
 code+=cls('CallsPermanentPositions',permanent)
 never=[r for r in allrows if r['method']=='exact-inferred-never'];code+=cls('NeverPositions<T>',never,'T')
 code+=['// This function item is used only for type inference during const evaluation; never called.','fn accounting_never_type() -> ! { panic!("accounting type witness must never execute") }','const fn exact_never_bytes<T>(_: fn() -> T) -> usize { size_of::<NeverPositions<T>>() }','const NEVER_BYTES: usize = exact_never_bytes(accounting_never_type);',f'const NUMERIC_PRODUCTION_BYTES:usize={offsets[False]};','#[cfg(test)]',f'const NUMERIC_UNIT_BYTES:usize={offsets[True]};','#[cfg(not(test))]','const NUMERIC_UNIT_BYTES:usize=0;','pub(super) const ACTIVE_BYTES:Option<usize> = match size_of::<CallsActivePositions>().checked_add(NEVER_BYTES) { Some(n)=>match n.checked_add(crate::experimental::execution::borrowed::calls_kind_accounting::BYTES) {Some(n)=>match n.checked_add(NUMERIC_PRODUCTION_BYTES) {Some(n)=>n.checked_add(NUMERIC_UNIT_BYTES),None=>None},None=>None},None=>None};','pub(super) const PERMANENT_BYTES:usize=size_of::<CallsPermanentPositions>();']
 kind=cls('CallsKindPositions',[r for r in allrows if r['method']=='exact-defining-module-kind'],'super::super::Kind')
 kind=['// Exact private Kind declarations remain inside a child of its original defining module.','#[allow(dead_code)]','pub(crate) mod calls_kind_accounting {']+kind+['pub(crate) const BYTES: usize = size_of::<CallsKindPositions>();','}']
 c.save(c.HERE/'positive-positions-v2.rs',('\n'.join(code)+'\n').encode());c.save(c.HERE/'kind-positions-v2.rs',('\n'.join(kind)+'\n').encode());c.save(c.HERE/'inventory-v2.json',allrows+permanent);c.save(c.HERE/'finite-numeric-positions-v2.json',numeric);c.save(c.HERE/'compiler-header-partition-v2.json',headers);c.save(c.HERE/'compiler-function-items-v2.json',implicit);c.save(c.HERE/'accounting-v2-summary.json',{'methods':dict(collections.Counter(r['method']for r in allrows+permanent)),'numericBytes':{'production':offsets[False],'unit':offsets[True]},'queryBindings':raw_query_bindings,'allAcceptancePending':True})
 print(collections.Counter(r['method']for r in allrows+permanent),offsets)
if __name__=='__main__':main()
