"""Complete compiler-owned body/local/operand accounting without header omissions.
Every exact local including _0, every alias/capture, and every non-FnDef constant
operand obtains four disjoint roles. FnDef operands have a separate exact audit.
No naming predicate exempts a selected canonical local. All proof methods explicit.
"""
import collect as c
from inventory_v2 import normal,body_name
from inventory import capture_fields,split_top
import json,gzip,re,collections
ROLES=['source','argument','returned','caller']
def display_index_free(value):
 if isinstance(value,str):return re.sub(r'DefId\(\d+:\d+ ~ ', 'DefId(<compiler-session-index> ~ ',value)
 if isinstance(value,list):return [display_index_free(x)for x in value]
 if isinstance(value,dict):return {k:display_index_free(v)for k,v in value.items()}
 return value

def contexts():
 for f in ['swift','all']:
  for p in ['debug','release']:
   for u in ['production','unit']:yield f'{f}-{p}-{u}'
def load(cfg):
 q=json.loads((c.HERE/f'exact-query-{cfg}.json').read_text());assert q['exitCode']==0
 assert q['sourceClosure']==c.sha(c.enc(c.manifest(c.HERE/'candidate'))),(cfg,'query source drift')
 raw=gzip.decompress((c.HERE/q['attempt']/'exact-layouts.jsonl.gz').read_bytes());assert c.sha(raw)==q['sha256'];return q,[json.loads(x)for x in raw.decode().splitlines()]
def raw_decls(body):
 out=dict(re.findall(r'let (?:mut )?(_\d+): ([^\n]+);',body));h=body.splitlines()[0]
 if h.startswith('fn '):
  pos=h.index('(');end=pos+1;d=1
  while d:d+=(h[end]=='(')-(h[end]==')');end+=1
  for arg in split_top(h[pos+1:end-1]):ident,ty=arg.split(': ',1);assert ident not in out or out[ident]==ty;out[ident]=ty
 return {int(k[1:]):t for k,t in out.items()}
def method(ty):
 if ty=='!':return 'exact-inferred-never'
 if ty=='experimental::execution::Kind':return 'exact-defining-module-kind'
 if ty.startswith('std::marker::PhantomData<alloc::sync::ArcInner<'):return 'pending-numeric-new-private'
 if ty=='std::alloc::Global':return 'pending-numeric-unstable-global'
 if '{closure@'in ty:return 'finite-numeric-actual-closure'
 n=normal(ty)
 if n in PRIVATE_TYPES:return 'finite-numeric-private-std'
 assert not any(x in ty for x in ['niche_types::','alloc::sync::ArcInner','::private::','std::sys::','std::thread::local_impl::']),ty
 return 'exact-typed'
PRIVATE_TYPES={normal(g['type'])for g in json.loads((c.HERE/'unnameable-positions.json').read_text())if g['type']!='!' and not g['type'].startswith('std::sync::Arc<') and '::execution::Kind'not in g['type']}

def main():
 rows=[];headers=[];operands=[];bindings={};selected={};partitions=[]
 for cfg in contexts():
  q,rs=load(cfg);bindings[cfg]=q;bodies={(x['path'],x['promoted']):x for x in rs if x['kind']=='body'};ls={};constants={}
  for x in rs:
   if x['kind']=='local':ls.setdefault((x['path'],x['promoted']),{})[x['local']]=x
   if x['kind']=='constant-operand':constants.setdefault((x['path'],x['promoted']),[]).append(x)
   if x['kind']=='partition-body':partitions.append(dict(config=cfg,querySHA256=q['sha256'],**x))
   if x['kind']=='FnDef':operands.append(dict(config=cfg,querySHA256=q['sha256'],**x))
  assert len(bodies)==len(ls)
  named_types={}
  for key,body in bodies.items():
   for index,ty in raw_decls(body['mir']).items():named_types.setdefault(ls[key][index]['layout']['identity'],ty)
  for ordinal,(bk,b)in enumerate(sorted(bodies.items(),key=lambda x:(x[0][0],-1 if x[0][1]is None else x[0][1]))):
   decl=raw_decls(b['mir']);assert set(decl)==set(ls[bk]),(cfg,b['path'],set(decl)^set(ls[bk]))
   bid=c.sha(c.enc([b['path'],b['promoted']]))[:12];tag=cfg.replace('-','_')+'_'+bid;bodysha=c.sha(b['mir'].encode())
   headers.append({'config':cfg,'body':b['path'],'promoted':b['promoted'],'bodyDefPathHash':b['defPathHash'],'bodySHA256':bodysha,'header':b['mir'].splitlines()[0],'locals':sorted(decl),'constantOperands':len(constants.get(bk,[])),'partition':'new-changed-runtime','querySHA256':q['sha256']})
   selected[(cfg,*bk)]=b
   def add(stem,binding,ty,kind,layout,local=None,capture=None,source=None):
    proof='finite-numeric-actual-closure'if layout['identity'].startswith('Closure(')else method(ty)
    for role in ROLES:
     row={'field':stem+'_'+role,'config':cfg,'body':b['path'],'promoted':b['promoted'],'bodyDefPathHash':b['defPathHash'],'bodySHA256':bodysha,'binding':binding,'kind':kind,'position':role,'mirType':ty,'method':proof,'unitOnly':cfg.endswith('-unit'),'querySHA256':q['sha256'],'actualType':layout['type'],'actualIdentity':layout['identity'],'layout':layout}
     if local is not None:row['local']=local;row['sourceInfo']=ls[bk][local]['sourceInfo']
     if capture is not None:row['capture']=capture
     if source is not None:row['source']=source
     rows.append(row)
   for i,ty in sorted(decl.items()):
    add('m_'+tag+'_'+str(i),'_'+str(i),ty,'canonical',ls[bk][i]['layout'],local=i)
   for a,(alias,local)in enumerate(re.findall(r'debug (\w+) => (_\d+);',b['mir'])):
    n=int(local[1:]);add('a_'+tag+'_'+str(a),alias,decl[n],'authored-alias',ls[bk][n]['layout'],local=n,source=alias)
   captures=capture_fields(b['mir'])if 1 in decl and '{closure@'in decl[1]else{}
   if captures:
    cl=ls[bk][1]['captureLayout'];assert cl is not None and len(cl['fields'])==len(captures),(cfg,b['path'],captures)
    for i,ty in captures.items():
     f=cl['fields'][i];layout={'type':f['type'],'identity':f['identity'],'bytes':f['bytes'],'alignment':f['alignment'],'fields':[],'variants':[],'captureFieldOf':cl['identity'],'captureOffset':f['offset']};add('c_'+tag+'_'+str(i),'capture_'+str(i),ty,'captured-alias',layout,local=1,capture=i)
   for i,op in enumerate(constants.get(bk,[])):
    # Exact type comes from the compiler operand, not guessed from literal text.
    ty=op['layout']['type']
    if ty.startswith('Binder '):
     assert op['layout']['identity']in named_types,ty
     ty=named_types[op['layout']['identity']]
    # Debug Ty uses erased regions; MIR Rust paths use equivalent lifetime erasure.
    ty=ty.replace("'{erased}","'static")
    add('o_'+tag+'_'+str(i),op['location']+':'+str(i),ty,'constant-operand',op['layout'],source=op['constant'])
 # Keep the original retained complete-owner wrappers as exact typed fields.
 retained=[dict(r,method='exact-typed')for r in json.loads((c.HERE/'inventory-schema.json').read_text())if r['config']=='source']
 assert len({r['field']for r in rows+retained})==len(rows)+len(retained)
 # Classification only proposes a method. Finite authority is this exact old set.
 selected_old={r['field']:r for r in json.loads((c.HERE/'finite-numeric-positions-v4.json').read_text())}
 changes=[]
 for r in rows:
  if r['method'] in ['pending-numeric-new-private','pending-numeric-unstable-global']:
   assert r['field']in selected_old,r['field'];r['method']=selected_old[r['field']]['method']
  if 'numeric'not in r['method']:continue
  assert r['field']in selected_old,('unselected finite position',r['field'])
  old=selected_old[r['field']]
  keys=['actualIdentity','bodyDefPathHash','config','position','binding','body','promoted','kind','method']
  assert all(r[k]==old[k]for k in keys),(r['field'],[(k,old[k],r[k])for k in keys if r[k]!=old[k]])
  for k in ['actualType','layout']:assert display_index_free(r[k])==display_index_free(old[k]),(r['field'],k,'non-display identity/layout drift')
  changes.append({'field':r['field'],'old':old,'final':r,'sameExactIdentityLayoutAndRole':True,'compilerSessionDisplayIndexChanged':r['actualType']!=old['actualType'],'displayNormalization':'Only numeric crate/DefIndex in DefId(N:N ~ path); exact DefPathHash identity, full path, args, actual size/alignment/fields/variants must remain equal','oldBodySHA256':old['bodySHA256'],'finalBodySHA256':r['bodySHA256'],'finalQuerySHA256':r['querySHA256'],'rootFinalSelectionPending':True})
 assert {r['field']for r in rows if 'numeric'in r['method']}==set(selected_old)
 for r in rows:r['ownerClass']='permanent'if ('::prepare_growth' in r['body'] or r['body'].endswith('call_dispatch::complete') or 'call_dispatch::complete::'in r['body'])else'active'
 for r in retained:r['ownerClass']='permanent'
 mapping=[{'field':r['field'],'method':r['method'],'body':r['body'],'config':r['config'],'oldClass':('permanent'if ('::prepare_growth' in r['body'] or r['body'].endswith('call_dispatch::complete') or 'call_dispatch::complete::'in r['body'])else'active'),'newClass':r['ownerClass'],'noLossOrReuse':True}for r in rows]
 offsets={(phase,unit):0 for phase in ['active','permanent']for unit in [False,True]};numeric=[]
 for r in rows:
  if 'numeric'not in r['method']:continue
  l=r['layout'];n=l['bytes'];a=l['alignment'];assert a>0 and a&(a-1)==0 and n>=0;k=(r['ownerClass'],r['unitOnly']);at=(offsets[k]+a-1)//a*a;end=at+n;assert end<2**64;offsets[k]=end;numeric.append(dict(r,relativeOffset=at,exclusiveEnd=end,component=r['ownerClass']+('-unit-numeric'if r['unitOnly']else'-production-numeric')))
 numeric_by_field={r['field']:r for r in numeric}
 for change in changes:
  change['final']=numeric_by_field[change['field']]
  assert change['old']['ownerClass']==change['final']['ownerClass']
 c.save(c.HERE/'finite-exception-reconciliation-v5.json',changes)
 def cls(name,rs,override=None):
  out=['#[allow(dead_code)]','pub(super) struct '+name+' {']
  for r in rs:
   if r['unitOnly']:out.append('    #[cfg(test)]')
   out.append('    '+r['field']+': '+(override or normal(r.get('mirType',r.get('type'))))+',')
  return out+['}']
 code=['// Complete phase-correct positive accounting. No row reuse or numeric type surrogate.']
 for phase in ['active','permanent']:
  code+=cls('Calls'+phase.title()+'Positions',[r for r in rows+retained if r['method']=='exact-typed'and r['ownerClass']==phase])
  code+=cls('Never'+phase.title()+'Positions<T>',[r for r in rows if r['method']=='exact-inferred-never'and r['ownerClass']==phase],'T')
 code+=['// Only a function item used in const type inference; it must never execute.','fn accounting_never_type() -> ! { panic!("accounting type witness must never execute") }']
 for phase in ['active','permanent']:
  upper=phase.upper();title=phase.title()
  code += [f'const fn exact_never_{phase}<T>(_: fn() -> T) -> usize {{ size_of::<Never{title}Positions<T>>() }}',f'pub(super) const NEVER_{upper}_BYTES:usize=exact_never_{phase}(accounting_never_type);',f'pub(super) const NUMERIC_{upper}_PRODUCTION_BYTES:usize={offsets[(phase,False)]};','#[cfg(test)]',f'pub(super) const NUMERIC_{upper}_UNIT_BYTES:usize={offsets[(phase,True)]};','#[cfg(not(test))]',f'pub(super) const NUMERIC_{upper}_UNIT_BYTES:usize=0;',f'pub(super) const {upper}_BYTES:Option<usize> = match size_of::<Calls{title}Positions>().checked_add(NEVER_{upper}_BYTES) {{Some(n)=>match n.checked_add(crate::experimental::execution::borrowed::calls_kind_accounting::{upper}_BYTES) {{Some(n)=>match n.checked_add(NUMERIC_{upper}_PRODUCTION_BYTES) {{Some(n)=>n.checked_add(NUMERIC_{upper}_UNIT_BYTES),None=>None}},None=>None}},None=>None}};']
 kind=['// Private Kind fields remain in the original defining-module child.','#[allow(dead_code)]','pub(crate) mod calls_kind_accounting {']
 for phase in ['active','permanent']:
  kind+=cls('CallsKind'+phase.title()+'Positions',[r for r in rows if r['method']=='exact-defining-module-kind'and r['ownerClass']==phase],'super::super::Kind')+[f'pub(crate) const {phase.upper()}_BYTES:usize=std::mem::size_of::<CallsKind{phase.title()}Positions>();']
 kind+=['}']
 c.save(c.HERE/'positive-positions-v5.rs',('\n'.join(code)+'\n').encode());c.save(c.HERE/'kind-positions-v5.rs',('\n'.join(kind)+'\n').encode());c.save(c.HERE/'inventory-v5.json',rows+retained);c.save(c.HERE/'finite-numeric-positions-v5.json',numeric);c.save(c.HERE/'compiler-headers-v5.json',headers);c.save(c.HERE/'compiler-partitions-v5.json',partitions);c.save(c.HERE/'compiler-function-items-v5.json',operands);c.save(c.HERE/'accounting-v5-summary.json',{'methods':dict(collections.Counter(r['method']for r in rows+retained)),'numericBytes':{phase:{'production':offsets[(phase,False)],'unit':offsets[(phase,True)]}for phase in ['active','permanent']},'phases':dict(collections.Counter(r['ownerClass']for r in rows+retained)),'queryBindings':bindings,'canonicalLocals':sum(r['kind']=='canonical'for r in rows)//4,'constantOperands':sum(r['kind']=='constant-operand'for r in rows)//4,'allAcceptancePending':True})
 c.save(c.HERE/'temporal-position-mapping-v5.json',mapping)
 print(collections.Counter(r['method']for r in rows+retained),offsets)
if __name__=='__main__':main()
