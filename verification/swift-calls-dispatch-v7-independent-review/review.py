#!/usr/bin/env python3
"""Pure host accounting replay. Imports no producer code; executes no VM/compiler."""
from pathlib import Path
import argparse, collections, copy, datetime, gzip, hashlib, json, re, sys, tarfile
BASE=Path(__file__).resolve().parents[2]
PACKET=BASE/'verification/swift-calls-dispatch/v7-fixture-expectations'
ROLES={'source','argument','returned','caller'}
DEFINITION_CACHE={}
SOURCE_HASH_CACHE={}
def sha(b):return hashlib.sha256(b).hexdigest()
def logical_bytes(p):
 p=Path(p)
 if p.exists():return p.read_bytes()
 final_transport=p.parent/'final-inventory-transport.json'
 if final_transport.exists():
  row=json.loads(final_transport.read_bytes())
  if p.name==row['logicalPath']:
   packed=(p.parent/row['transportPath']).read_bytes();require(sha(packed)==row['transportSHA256']and len(packed)==row['transportBytes'],'final inventory gzip transport extent/digest mismatch');raw=gzip.decompress(packed)
   require(sha(raw)==row['logicalSHA256']and len(raw)==row['logicalBytes'],'final inventory logical bytes drift');return raw
 for name in ['historical-json-transports.json','json-transports.json']:
  index=p.parent/name
  if not index.exists():continue
  transports=json.loads(index.read_bytes())
  if p.name not in transports:continue
  row=transports[p.name];packed=(p.parent/row['transport']).read_bytes();require(sha(packed)==row['gzipSHA256']and len(packed)==row['gzipBytes'],'gzip transport extent/digest mismatch');raw=gzip.decompress(packed)
  require(sha(raw)==row['logicalSHA256']and len(raw)==row['logicalBytes'],'lossless logical inventory digest mismatch');return raw
 raise FileNotFoundError(p)
def read(p):return json.loads(logical_bytes(p))
def require(ok,msg):
 if not ok:raise ValueError(msg)
def archive(path,manifest):
 with tarfile.open(path) as t:
  members=[m for m in t if m.isfile()]
  require(len({m.name for m in members})==len(members),'duplicate archive member')
  require({m.name for m in members}==set(manifest),'archive member closure mismatch')
  result={m.name:t.extractfile(m).read() for m in members}
 require(all(sha(result[k])==v for k,v in manifest.items()),'archive content mismatch')
 return result
def contexts():return [f'{f}-{p}-{u}'for f in ['swift','all']for p in ['debug','release']for u in ['production','unit']]
def field_groups(rows):
 require(len({r['field']for r in rows})==len(rows),'duplicate named role')
 groups=collections.defaultdict(list)
 for r in rows:
  require(r['position']in ROLES,'unknown role')
  require(r['field'].endswith('_'+r['position']),'role suffix mismatch')
  groups[r['field'].rsplit('_',1)[0]].append(r)
 for k,rs in groups.items():
  require({r['position']for r in rs}==ROLES and len(rs)==4,'incomplete four-role set '+k)
  projections=[{k:v for k,v in r.items()if k not in ['field','position','relativeOffset','exclusiveEnd']}for r in rs]
  require(all(x==projections[0]for x in projections),'role type/context drift '+k)
 return groups
def numeric(rows):
 offsets=collections.defaultdict(int)
 for r in rows:
  l=r['layout'];n=l['bytes'];a=l['alignment']
  require(type(n)is int and 0<=n<2**64,'invalid numeric size')
  require(type(a)is int and a>0 and a&(a-1)==0,'invalid numeric alignment')
  k=(r['ownerClass'],r['unitOnly']);start=(offsets[k]+a-1)//a*a;end=start+n
  require(end<2**64,'numeric arithmetic overflow')
  require((r['relativeOffset'],r['exclusiveEnd'])==(start,end),'numeric interval overlap/gap '+r['field'])
  require(l['identity']==r['actualIdentity']and l['type']==r['actualType'],'numeric type substitution '+r['field'])
  offsets[k]=end
 return {phase:{'production':offsets[(phase,False)],'unit':offsets[(phase,True)]}for phase in ['active','permanent']}
def layout_valid(l):
 n=l['bytes'];a=l['alignment'];require(type(n)is int and n>=0 and type(a)is int and a>0 and not a&(a-1),'unsupported layout size/alignment')
 for container in [l]+l.get('variants',[]):
  require('fields'in container,'incomplete field metadata')
  for f in container['fields']:
   require(set(['index','offset','bytes','alignment','type','identity'])<=set(f),'incomplete actual field metadata')
   require(f['offset']>=0 and f['offset']%f['alignment']==0 and f['offset']+f['bytes']<=container['bytes'],'invalid actual field interval')
def bodykey(r):return (r.get('body',r.get('path')),r.get('promoted'))
def query(pointer):
 require(pointer['exitCode']==0,'compiler query failure')
 path=PACKET/pointer['attempt']/'exact-layouts.jsonl.gz';raw=gzip.decompress(path.read_bytes())
 require(sha(raw)==pointer['sha256'],'compiler query hash')
 rs=[json.loads(s)for s in raw.splitlines()]
 require(len(rs)==pointer['records']and len(raw)==pointer['bytes'],'query extent mismatch')
 result={k:[]for k in ['context','body','local','constant-operand','FnDef','partition-body','declaration','generic-declaration','type-graph','type-layout','scope-graph-body','scope-graph-function-item-use']}
 for r in rs:
  require(r['kind']in result,'unknown compiler record kind '+r['kind']);result[r['kind']].append(r)
 require(len(result['context'])==1,'missing compiler target context')
 require(result['context'][0]['target']=='aarch64-apple-darwin','unexpected compiler target')
 artifacts=read(PACKET/pointer['attempt']/'artifacts.json');mir_artifacts=[r for r in artifacts if r['path'].endswith('.mir.gz')]
 require(len(mir_artifacts)==1,'expected one full compiler MIR artifact')
 art=mir_artifacts[0];full=gzip.decompress((PACKET/pointer['attempt']/art['path']).read_bytes());require(sha(full)==art['sha256'],'whole MIR artifact digest')
 text=full.decode();starts={m[0]:m.start()for m in re.finditer(r'^[^\s][^\n]*\{\n',text,re.M)}
 for b in result['body']:
  header=b['mir'].splitlines()[0]+'\n';require(header in starts,'selected body absent from full emitted MIR')
  at=starts[header];require(text[at:at+len(b['mir'])]==b['mir'],'callback body differs from emitted MIR')
 known={r['mir'].splitlines()[0]for r in result['body']+result['partition-body']}
 for m in re.finditer(r'^fn [^\n]*\{\n',text,re.M):
  end=text.find('\n}',m.end());body=text[m.start():end+2]
  if any(int(n)<698 for n in re.findall(r'src/experimental_swift_reactor/call_dispatch.rs:(\d+):',body)):
   require(body.splitlines()[0]in known,'runtime compiler body omitted by selection '+body.splitlines()[0])
 allowed_accounting={'experimental_swift_reactor::execution::frame_operations::call_dispatch::'+n for n in ['accounting_never_type','exact_never_active','exact_never_permanent','exact_never_bytes']}
 require(all(r['path']in allowed_accounting for r in result['partition-body']if r['partition']=='accounting-const-only'and r['defKind']in ['Fn','AssocFn','Closure']),'runtime function hidden in accounting partition')
 return result
def coverage(rows,headers,queries,strict):
 stats={};selected_rows=[r for r in rows if r['config']!='source']
 for cfg,q in queries.items():
  rr=[r for r in selected_rows if r['config']==cfg];hh=[r for r in headers if r['config']==cfg]
  bodies={bodykey(r):r for r in q['body']};local={(*bodykey(r),r['local']):r for r in q['local']}
  require(len(bodies)==len(q['body'])and len(local)==len(q['local']),'duplicate compiler body/local')
  require({bodykey(h)for h in hh}==set(bodies)and len(hh)==len(bodies),'full header coverage')
  groups=field_groups(rr);counts=collections.Counter();constants=collections.defaultdict(list)
  for op in q['constant-operand']:constants[bodykey(op)].append(op)
  expected={}
  for bk,b in bodies.items():
   hh0=next(h for h in hh if bodykey(h)==bk)
   require(hh0['header']==b['mir'].splitlines()[0],'full header mismatch')
   require(hh0['bodyDefPathHash']==b['defPathHash'],'body def identity mismatch')
   if strict:require(hh0['bodySHA256']==sha(b['mir'].encode()),'final header body drift')
   for lk,lr in local.items():
    if lk[:2]==bk:expected[(bk,'canonical',str(lr['local']))]=lr['layout']
   aliases=re.findall(r'debug (\w+) => (_\d+);',b['mir'])
   for i,(name,loc)in enumerate(aliases):expected[(bk,'authored-alias',str(i))]=local[(*bk,int(loc[1:]))]['layout']
   for i,op in enumerate(constants[bk]):expected[(bk,'constant-operand',str(i))]=op['layout']
  seen=set();capture_seen=set()
  for stem,rs in groups.items():
   r=rs[0];bk=bodykey(r);require(bk in bodies,'unknown selected row body');kind=r['kind']
   if strict:
    require(r['bodySHA256']==sha(bodies[bk]['mir'].encode()),'final inventory body drift '+stem)
    require(r['bodyDefPathHash']==bodies[bk]['defPathHash'],'final inventory definition drift '+stem)
    require(r['querySHA256']==next(h['querySHA256']for h in hh if bodykey(h)==bk),'final row query drift')
   if kind=='canonical':
    index=str(r['local']);require(r['binding']=='_'+index,'canonical binding drift')
   elif kind in ['authored-alias','constant-operand']:
    index=stem.rsplit('_',1)[1]
    if kind=='constant-operand':
     op=constants[bk][int(index)];require(r['source']==op['constant']and r['binding']==op['location']+':'+index,'constant value/location drift')
    else:
     alias=re.findall(r'debug (\w+) => (_\d+);',bodies[bk]['mir'])[int(index)]
     require(r['binding']==alias[0]and r['source']==alias[0]and r['local']==int(alias[1][1:]),'authored alias binding drift')
   elif kind=='captured-alias':
    lr=local[(*bk,r['local'])];cl=lr['captureLayout'];require(cl is not None,'missing actual capture layout');f=cl['fields'][r['capture']]
    require(r['actualIdentity']==f['identity']and r['layout']['bytes']==f['bytes']and r['layout']['alignment']==f['alignment'],'capture substitution')
    ck=(bk,r['capture']);require(ck not in capture_seen,'duplicate capture alias');capture_seen.add(ck);counts[kind]+=4;continue
   else:raise ValueError('unknown inventory kind '+kind)
   k=(bk,kind,index);require(k in expected and k not in seen,'missing or duplicate compiler source position '+stem);seen.add(k);l=expected[k]
   require(r['actualIdentity']==l['identity'],'actual compiler type identity drift '+stem)
   require(r['layout']==l,'actual complete compiler layout drift '+stem);counts[kind]+=4
  require(seen==set(expected),'unaccounted compiler positions '+str(set(expected)-seen))
  capture_expected={(lk[:2],f['index'])for lk,lr in local.items()if lk[2]==1 and lr.get('captureLayout')is not None for f in lr['captureLayout']['fields']}
  require(capture_seen==capture_expected,'unaccounted actual closure captures '+str(capture_expected-capture_seen))
  require(all(op['layout']['bytes']==0 and op['layout']['alignment']==1 and op['layout']['identity'].startswith('FnDef(')for op in q['FnDef']),'implicit function-item substitution')
  excluded={r['path']:r['partition']for r in q['partition-body']}
  require(all('calleePath'in op and 'calleeDefPathHash'in op for op in q['FnDef']),'missing compiler callee identity; old driver cannot prove fixture boundary')
  forbidden=[op for op in q['FnDef']if excluded.get(op['calleePath'])=='fixture-only'];require(not forbidden,'runtime call reaches excluded fixture body')
  stats[cfg]={'bodies':len(bodies),'locals':len(local),'nonFnDefConstantOperands':len(q['constant-operand']),'exactImplicitFunctionItems':len(q['FnDef']),'roleCounts':dict(counts),'fixtureCallEdges':0}
 return stats
def canonical_graph(value,source):
 """Preserve actual recursive compiler type structure across local crate ids.
 Local definitions must share the same disambiguated compiler path and exact
 frozen source bytes. Each full contextual hash is independently reconstructed
 by the reviewed pinned-compiler callback from its actual crate seed and path.
 External definitions retain their full raw hash and stable crate identity.
 """
 if isinstance(value,list):return [canonical_graph(v,source)for v in value]
 if not isinstance(value,dict):return value
 if 'rawDefPathHash'in value:
  cache_key=(id(source),json.dumps(value,sort_keys=True))
  if cache_key in DEFINITION_CACHE:return DEFINITION_CACHE[cache_key]
  required={'rawDefPathHash','path','disambiguatedDefPath','kind','crateName','crateStableId','isLocal','span','source','contextHashProof'};require(set(value)==required,'unsupported definition graph schema')
  stable=re.fullmatch(r'StableCrateId\((\d+)\)',value['crateStableId']);require(stable is not None,'unsupported stable crate identity')
  proof=value['contextHashProof'];require(proof['api']=='rustc1.99.0-Definitions::new+DefKey::compute_stable_hash'and proof['compilerRootAndFinalMatch']is True,'compiler hash reconstruction missing')
  require(proof['pathData']==value['disambiguatedDefPath']and proof['final']==value['rawDefPathHash'],'compiler hash proof is not actual definition')
  require(proof['root']==f'DefPathHash(Fingerprint({stable[1]}, {stable[1]}))','compiler crate-root seed mismatch')
  require('['+', '.join(s['component']for s in proof['steps'])+']'==proof['pathData'],'compiler definition path steps mismatch')
  require((proof['steps'][-1]['result']if proof['steps']else proof['root'])==proof['final'],'reconstructed final definition hash mismatch')
  for step in proof['steps']:
   h=re.fullmatch(r'DefPathHash\(Fingerprint\((\d+), (\d+)\)\)',step['result']);require(h is not None and h[1]==stable[1],'hash reconstruction changed contextual crate')
  out=dict(value)
  if value['isLocal']:
   require(value['crateName']=='mixer_vm','unexpected local graph crate');loc=value['source'];require(loc is not None,'local definition source missing');filename=loc['file'];require(filename in source,'local definition outside frozen source')
   lines=source[filename].decode().splitlines(keepends=True);a=loc['startLine']-1;b=loc['endLine']-1;require(0<=a<=b<len(lines),'invalid compiler definition span')
   require(0<=loc['startColumn']<=len(lines[a])and 0<=loc['endColumn']<=len(lines[b]),'invalid source span columns')
   fragment=(lines[a][loc['startColumn']:loc['endColumn']]if a==b else lines[a][loc['startColumn']:]+''.join(lines[a+1:b])+lines[b][:loc['endColumn']]).encode();require(fragment,'empty compiler definition source span')
   hashes=re.fullmatch(r'DefPathHash\(Fingerprint\((\d+), (\d+)\)\)',value['rawDefPathHash']);require(hashes is not None,'unsupported raw definition hash')
   require(stable[1]==hashes[1],'contextual crate identity is not raw hash crate component')
   source_key=(id(source),filename)
   if source_key not in SOURCE_HASH_CACHE:SOURCE_HASH_CACHE[source_key]=sha(source[filename])
   out.pop('rawDefPathHash');out.pop('crateStableId');out['contextHashProof']={'api':proof['api'],'pathData':proof['pathData'],'components':[s['component']for s in proof['steps']],'eachContextExactlyReconstructed':True};out['source']=loc;out['sourceFileSHA256']=SOURCE_HASH_CACHE[source_key];out['sourceFragmentSHA256']=sha(fragment)
  DEFINITION_CACHE[cache_key]=out
  return out
 require(value.get('kind')in ['type','region','const','Adt','Closure','FnDef','Ref','RawPtr','Tuple','Array','Slice','Pat','FnPtr','primitive'],'unsupported actual structural graph kind')
 return {k:canonical_graph(v,source)for k,v in value.items()}
def witness(rows,queries,source):
 stats={};graphs={cfg:{r['identity']:r['graph']for r in q['type-graph']}for cfg,q in queries.items()};canonical={};bridges=collections.Counter();layouts={cfg:{r['identity']:r['layout']for r in q['type-layout']}for cfg,q in queries.items()};layout_cache={};retained_layouts={}
 for cfg,gs in graphs.items():
  require(gs,'compiler structural type graphs missing')
  require(len(gs)==len(queries[cfg]['type-graph']),'duplicate structural graph identity')
 def graph_key(cfg,identity):
  require(identity in graphs[cfg],'compiler type graph mapping missing')
  if (cfg,identity)not in canonical:canonical[(cfg,identity)]=sha(json.dumps(canonical_graph(graphs[cfg][identity],source),sort_keys=True).encode())
  return canonical[(cfg,identity)]
 def normalized_layout(value,cfg):
  if isinstance(value,list):return [normalized_layout(v,cfg)for v in value]
  if not isinstance(value,dict):return value
  out={}
  for k,v in value.items():
   if k=='type':continue # Actual identity is proved through the compiler graph.
   if k=='identity':out[k]=graph_key(cfg,v)
   else:out[k]=normalized_layout(v,cfg)
  return out
 def layout_key(cfg,identity):
  key=(cfg,identity)
  if key not in layout_cache:
   require(identity in layouts[cfg],'complete actual field type layout missing');l=layouts[cfg][identity];require(l['identity']==identity,'actual layout table identity mismatch');layout_valid(l)
   layout_cache[key]=sha(json.dumps(normalized_layout(l,cfg),sort_keys=True).encode())
  return layout_cache[key]
 for cfg,ls in layouts.items():require(ls and len(ls)==len(queries[cfg]['type-layout']),'missing or duplicate actual layout table')
 retained={r['field']:r for r in read(PACKET/'inventory-schema.json')if r['config']=='source'}
 require(len(retained)==36,'original whole-carrier inventory changed')
 for r in rows:
  if r['config']=='source':require(all(r[k]==retained[r['field']][k]for k in retained[r['field']]),'retained whole-carrier declaration changed')
 for cfg,q in queries.items():
  unit=cfg.endswith('-unit');names=['CallsActivePositions','CallsPermanentPositions','NeverActivePositions','NeverPermanentPositions','CallsKindActivePositions','CallsKindPermanentPositions']
  decl={r['path'].split('::')[-1]:r['layout']for r in q['declaration']if r['path'].split('::')[-1]in names};expected={}
  for phase in ['active','permanent']:
   for method,prefix in [('exact-typed','Calls'),('exact-inferred-never','Never'),('exact-defining-module-kind','CallsKind')]:
    name=prefix+phase.title()+'Positions';rs=[r for r in rows if r['method']==method and r['ownerClass']==phase and (unit or not r['unitOnly'])]
    require(name in decl,'missing actual witness layout '+name);l=decl[name];require(len(l['variants'])==1,'witness is not one exact struct')
    v=l['variants'][0];require(len(v['fields'])==len(v['fieldNames']),'witness field metadata missing');fields=dict(zip(v['fieldNames'],v['fields']))
    require(len(fields)==len(rs)and set(fields)=={r['field']for r in rs},'witness named field coverage '+name);positive=[]
    for r in rs:
     f=fields[r['field']]
     if r['config']!='source':
      require(graph_key(cfg,f['identity'])==graph_key(r['config'],r['actualIdentity']),'typed witness actual definition/generic-argument substitution '+r['field'])
      require(layout_key(cfg,f['identity'])==layout_key(r['config'],r['actualIdentity']),'cross-context complete type layout/field/variant drift '+r['field'])
      if cfg==r['config']:require(f['identity']==r['actualIdentity'],'same-context raw typed identity changed')
      bridges[(r['config'],cfg)]+=1
     else:
      key=(graph_key(cfg,f['identity']),layout_key(cfg,f['identity']))
      if r['field']not in retained_layouts:retained_layouts[r['field']]=key
      require(retained_layouts[r['field']]==key,'retained whole-carrier cross-context type/layout drift')
     require(f['offset']%f['alignment']==0,'misaligned typed field');require(f['offset']+f['bytes']<=l['bytes'],'typed field outside bound')
     if f['bytes']:positive.append((f['offset'],f['offset']+f['bytes'],r['field']))
    positive.sort();require(all(a[1]<=b[0]for a,b in zip(positive,positive[1:])),'overlapping positive fields')
    expected[name]={'bytes':l['bytes'],'alignment':l['alignment'],'fields':len(fields),'positiveIntervals':len(positive)}
  stats[cfg]=expected
 # Equal-size mutations must fail despite unchanged bytes/alignment/offsets.
 used=[graphs[cfg][identity]for cfg,identity in canonical]
 def reject_graph(a,b,label):
  original=canonical_graph(a,source)
  try:altered=canonical_graph(b,source)
  except ValueError:return
  require(original!=altered,'graph mutation accepted '+label)
 sample=next(g for g in used if g.get('kind')=='Adt'and g['definition']['isLocal']);changed=copy.deepcopy(sample);changed['definition']['disambiguatedDefPath']+='::WrongDefinition';reject_graph(sample,changed,'definition')
 changed=copy.deepcopy(sample);changed['args'].append({'kind':'type','value':{'kind':'primitive','actual':'Uint(U8)'}})
 reject_graph(sample,changed,'generic argument')
 changed=copy.deepcopy(sample);changed['definition']['rawDefPathHash']=re.sub(r', (\d+)\)\)',lambda m:', '+str(int(m[1])+1)+'))',changed['definition']['rawDefPathHash'])
 reject_graph(sample,changed,'local definition hash')
 changed=copy.deepcopy(sample);changed['definition']['contextHashProof']['root']='DefPathHash(Fingerprint(1, 1))';reject_graph(sample,changed,'crate root seed')
 fn=next(g for g in used if g.get('kind')=='FnPtr');changed=copy.deepcopy(fn);changed['binder']+='WrongBinder'
 reject_graph(fn,changed,'function binder')
 ref=next(g for g in used if g.get('kind')=='Ref');changed=copy.deepcopy(ref);changed['mutability']='Mut'if ref['mutability']=='Not'else'Not'
 reject_graph(ref,changed,'reference mutability')
 cfg,ls=next(iter(layouts.items()));lay=next(l for l in ls.values()if l['variants']and l['variants'][0]['fieldNames']);changed=copy.deepcopy(lay);changed['variants'][0]['fieldNames'][0]+='WrongField'
 require(normalized_layout(lay,cfg)!=normalized_layout(changed,cfg),'same-size field metadata mutation accepted')
 return {'contexts':stats,'originToCompiledFieldComparisons':{origin:{target:bridges[(origin,target)]for target in contexts()if bridges[(origin,target)]}for origin in contexts()},'sameSizeMutationControls':{k:'rejected'for k in ['definition-path','generic-argument','local-definition-hash','crate-root-seed','function-binder','reference-mutability','field-metadata']}}
def mutations(rows,num):
 controls={}
 def reject(name,fn):
  try:fn()
  except (ValueError,KeyError):controls[name]='rejected'
  else:raise ValueError('mutation accepted '+name)
 reject('missing-role',lambda:field_groups(rows[1:]));reject('duplicate-role',lambda:field_groups(rows+[rows[0]]))
 z=next(i for i,r in enumerate(rows)if r.get('layout',{}).get('bytes')==0);reject('missing-named-zero-role',lambda:field_groups(rows[:z]+rows[z+1:]))
 x=copy.deepcopy(num);x[0]['relativeOffset']+=1;reject('numeric-overlap-or-gap',lambda:numeric(x))
 x=copy.deepcopy(num);x[0]['actualIdentity']='RawPtr(Not;u8)';reject('numeric-type-substitution',lambda:numeric(x))
 x=copy.deepcopy(num);x[0]['layout']['alignment']=3;reject('non-power-two-alignment',lambda:numeric(x))
 return controls
def temporal(rows,mapping):
 require(len({r['field']for r in mapping})==len(mapping),'duplicate temporal role')
 indexed={r['field']:r for r in mapping};require(set(indexed)=={r['field']for r in rows if r['config']!='source'},'temporal coverage drift')
 counts=collections.Counter();authority=BASE/'verification/swift-calls-dispatch-root-review';selected=gzip.decompress((authority/'temporal-position-mapping-v4.json.gz').read_bytes());require(sha(selected)=='2f6873682d4bbbe7a5768325dcda53b212bdd16bcabba902cb985456e7bf9260','selected temporal map drift');selected={r['field']:r for r in json.loads(selected)}
 for r in rows:
  permanent=r['config']=='source' or '::prepare_growth'in r['body'] or r['body'].endswith('call_dispatch::complete')or'call_dispatch::complete::'in r['body']
  expected='permanent'if permanent else'active';require(r['ownerClass']==expected,'incorrect temporal placement '+r['field']);counts[expected]+=1
  if r['config']!='source':
   m=indexed[r['field']];require(all(m[k]==r[k]for k in ['field','method','body','config']),'temporal identity mismatch')
   require(m['oldClass']in ['active',selected[r['field']]['newClass']]and m['newClass']==expected and m['noLossOrReuse']is True,'temporal admission or reuse drift')
   require(m['newClass']==selected[r['field']]['newClass'],'selected temporal class drift')
 return dict(counts)
def finite(num):
 old=read(PACKET/'finite-numeric-positions-v4.json');initial=read(Path(__file__).resolve().parent/'initial-input-bindings.json');name='verification/swift-calls-dispatch/finite-numeric-positions-v4.json'
 require(sha(logical_bytes(PACKET/'finite-numeric-positions-v4.json'))==initial[name]['sha256'],'original finite set changed')
 reconciliation=read(PACKET/'finite-exception-reconciliation-v5.json');oldmap={r['field']:r for r in old};newmap={r['field']:r for r in num};maps={r['field']:r for r in reconciliation}
 require(set(oldmap)==set(newmap)==set(maps)and len(maps)==1032,'finite exception expansion or omission')
 normalize=lambda x:re.sub(r'DefId\(\d+:\d+ ~','DefId(<compiler-session-index> ~',json.dumps(x,sort_keys=True))
 counts=collections.Counter()
 for name,new in newmap.items():
  before=oldmap[name];record=maps[name];require(record['old']==before and record['final']==new,'finite reconciliation record substitution')
  for k in ['actualIdentity','field','config','body','bodyDefPathHash','promoted','binding','position','kind','method','unitOnly','ownerClass']:
   require(before[k]==new[k],'finite position/type drift '+name+' '+k)
  require(normalize(before['layout'])==normalize(new['layout']),'finite layout changed beyond compiler display index')
  require(normalize(before['actualType'])==normalize(new['actualType']),'finite actual type identity changed')
  require(record['finalBodySHA256']==new['bodySHA256']and record['finalQuerySHA256']==new['querySHA256'],'finite final body/query binding')
  counts[(new['method'],new['config'])]+=1
 return {method:{cfg:counts[(method,cfg)]for cfg in contexts()if counts[(method,cfg)]}for method in sorted({r['method']for r in num})}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--query-bindings',type=Path);ap.add_argument('--version',default='v4');ap.add_argument('--mode',choices=['early','final'],default='early');args=ap.parse_args();version=args.version
 result={'schema':1,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'early-review-in-progress','tool':sys.version,'command':sys.argv,'cwd':str(Path.cwd()),'verifierSHA256':sha(Path(__file__).read_bytes()),'qualifiedRuntimeExecuted':False,'nativeInstancesCreated':0,'accountingAccepted':False}
 try:
  rows=read(PACKET/f'inventory-{version}.json');headers=read(PACKET/f'compiler-headers-{version}.json');num=read(PACKET/f'finite-numeric-positions-{version}.json');summary=read(PACKET/f'accounting-{version}-summary.json');field_groups(rows)
  result['inventoryRows']=len(rows);result['methods']=dict(collections.Counter(r['method']for r in rows));result['phases']=dict(collections.Counter(r['ownerClass']for r in rows));result['numericPositions']=len(num);result['numericBytes']=numeric(num)
  for r in rows:
   if r['config']!='source':layout_valid(r['layout'])
  require({r['field']for r in num}=={r['field']for r in rows if 'numeric'in r['method']},'numeric position coverage');require(result['numericBytes']==summary['numericBytes'],'numeric byte summary drift')
  require(result['methods']==summary['methods']and result['phases']==summary['phases'],'summary count drift');result['mutationControls']=mutations(rows,num)
  result['temporalRoles']=temporal(rows,read(PACKET/f'temporal-position-mapping-{version}.json'))
  if version=='v5':result['finiteExceptionContexts']=finite(num)
  bindings=read(args.query_bindings)if args.query_bindings else summary['queryBindings'];require(set(bindings)==set(contexts()),'required eight compiler contexts');queries={cfg:query(q)for cfg,q in bindings.items()}
  source_manifest=read(PACKET/'candidate-final-manifest.json');source=archive(PACKET/'candidate-final-source.tar.gz',source_manifest)
  result['sourceClosure']=sha((PACKET/'candidate-final-manifest.json').read_bytes());result['compilerCoverage']=coverage(rows,headers,queries,args.mode=='final');result['witnessLayouts']=witness(rows,queries,source)
  result['status']='method-replay-passed-additional-review-pending'
 except BaseException as e:result['status']='rejected';result['error']=repr(e)
 args.output.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print(json.dumps(result,sort_keys=True,indent=2));return 1 if result['status']=='rejected'else 0
if __name__=='__main__':raise SystemExit(main())
