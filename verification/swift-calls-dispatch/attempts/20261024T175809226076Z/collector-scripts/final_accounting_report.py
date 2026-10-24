"""Fail-closed reconciliation of final compiler identity/fields/temporal bounds.
This tool performs no compilation or interpreter execution. Raw compiler output,
source archives and exact type identities remain separate from this report.
"""
import collect as c
import json,gzip,re,collections,sys
import identity_bridge

def read(path):return c.read_json(path)
def rawquery(q):
 raw=gzip.decompress((c.HERE/q['attempt']/'exact-layouts.jsonl.gz').read_bytes());assert c.sha(raw)==q['sha256'];return [json.loads(x)for x in raw.decode().splitlines()]
def semantic(text):
 # Normalize only compiler source coordinates and allocation display identifiers.
 # No type/owner/operand/opcode/value is erased or substituted.
 lines=[]
 for line in text.splitlines():
  quote=False;escape=False;cut=len(line)
  for i,ch in enumerate(line):
   if escape:escape=False;continue
   if ch=='\\'and quote:escape=True;continue
   if ch=='"':quote=not quote
   if not quote and line[i:i+2]=='//':cut=i;break
  lines.append(line[:cut].strip())
 text='\n'.join(lines)
 text=re.sub(r'((?:src/|/rustc/)[^\s{}<>]*?\.rs):\d+:\d+(?:: \d+:\d+)?',r'\1:<source-coordinate>',text)
 allocs={}
 text=re.sub(r'alloc\d+',lambda m:allocs.setdefault(m[0],'allocDisplay'+str(len(allocs))),text)
 return text

def classes(records):
 out={}
 for x in records:
  if x['kind']=='declaration':
   tail=x['path'].split('::')[-1]
   if tail in ['CallsActivePositions','CallsPermanentPositions','NeverActivePositions','NeverPermanentPositions','CallsKindActivePositions','CallsKindPermanentPositions']:
    assert tail not in out;out[tail]=x
 assert len(out)==6,set(out);return out

def fields(cls):
 l=cls['layout'];vs=l['variants'];assert len(vs)==1;v=vs[0];assert len(v['fieldNames'])==len(l['fields'])==len(v['fields'])
 out={name:f for name,f in zip(v['fieldNames'],l['fields'])};assert len(out)==len(l['fields']);interval=[]
 for name,f in out.items():
  a=f['alignment'];off=f['offset'];end=off+f['bytes'];assert a>0 and off%a==0 and 0<=off<=end<=l['bytes'],(cls['path'],name,f,l['bytes'])
  if f['bytes']:interval.append((off,end,name))
 interval.sort()
 for prev,nxt in zip(interval,interval[1:]):assert prev[1]<=nxt[0],(cls['path'],prev,nxt)
 return out

def main(write):
 final=read(c.HERE/'candidate-final-source.json');assert c.sha(c.enc(c.manifest(c.HERE/'candidate')))==final['sourceClosure']
 rows=read(c.HERE/'inventory-v5.json');assert len(rows)==89124;assert len({r['field']for r in rows})==89124
 summary=read(c.HERE/'accounting-v5-summary.json');numeric=read(c.HERE/'finite-numeric-positions-v5.json');assert len(numeric)==1032
 reconciliation=read(c.HERE/'finite-exception-reconciliation-v5.json');assert len(reconciliation)==1032
 remap={r['field']:r for r in reconciliation};assert set(remap)=={r['field']for r in numeric}
 for r in numeric:assert remap[r['field']]['final']==r and remap[r['field']]['sameExactIdentityLayoutAndRole']
 offsets=collections.defaultdict(int)
 for r in numeric:
  n=r['layout']['bytes'];a=r['layout']['alignment'];assert a>0 and a&(a-1)==0 and n>=0
  key=(r['ownerClass'],r['unitOnly']);at=(offsets[key]+a-1)//a*a;end=at+n;assert end<2**64
  assert (r['relativeOffset'],r['exclusiveEnd'])==(at,end);offsets[key]=end
 for (phase,unit),value in offsets.items():assert value==summary['numericBytes'][phase]['unit'if unit else'production']
 method_counts=dict(collections.Counter(r['method']for r in rows));assert method_counts==summary['methods'];assert not any('pending'in k for k in method_counts)
 final_bindings={cfg:read(c.HERE/f'exact-query-{cfg}.json')for cfg in summary['queryBindings']};bridge=identity_bridge.Bridge(final_bindings);context_reports={};field_reports=[];body_reports=[];fndef_reports=[];partition_reports=[]
 for cfg,stage in summary['queryBindings'].items():
  q=read(c.HERE/f'exact-query-{cfg}.json');assert q['exitCode']==0 and q['sourceClosure']==final['sourceClosure'];assert q['toolSHA256']==read(c.HERE/'layout-driver-build.json')['sha256'];final_bindings[cfg]=q
  records=rawquery(q);ctx=[x for x in records if x['kind']=='context'];assert len(ctx)==1 and ctx[0]['target']=='aarch64-apple-darwin'
  bs={(x['path'],x['promoted']):x for x in records if x['kind']=='body'};old={(x['path'],x['promoted']):x for x in rawquery(stage)if x['kind']=='body'};assert set(bs)==set(old)
  for key,b in bs.items():
   assert b['mir']==old[key]['mir'],(cfg,key,'inventory not bound to final actual MIR')
   body_reports.append({'config':cfg,'body':key[0],'promoted':key[1],'defPathHash':b['defPathHash'],'rawSHA256':c.sha(b['mir'].encode()),'inventoryRawSHA256':c.sha(old[key]['mir'].encode()),'normalizedSHA256':c.sha(semantic(b['mir']).encode()),'inventoryExactRawEqual':True})
  locals={(x['path'],x['promoted'],x['local']):x for x in records if x['kind']=='local'}
  canonical=[r for r in rows if r.get('config')==cfg and r.get('kind')=='canonical'];observed=collections.Counter((r['body'],r['promoted'],r['local'])for r in canonical);assert set(observed)==set(locals)and set(observed.values())=={4}
  for r in canonical:assert r['actualIdentity']==locals[(r['body'],r['promoted'],r['local'])]['layout']['identity'],(cfg,r['field'],'actual local identity drift')
  cls=classes(records);maps={name:fields(x)for name,x in cls.items()};expected={name:[]for name in cls}
  for r in rows:
   if r['unitOnly']and not cfg.endswith('-unit'):continue
   if 'numeric'in r['method']:continue
   title=r['ownerClass'].title();name=('Never'+title+'Positions'if r['method']=='exact-inferred-never'else'CallsKind'+title+'Positions'if r['method']=='exact-defining-module-kind'else'Calls'+title+'Positions')
   expected[name].append(r);f=maps[name][r['field']]
   if 'layout'in r:assert (f['bytes'],f['alignment'])==(r['layout']['bytes'],r['layout']['alignment']),(cfg,r['field'],'layout drift')
   if r.get('config')==cfg:assert f['identity']==r['actualIdentity'],(cfg,r['field'],'typed identity mismatch')
   bridge.field(r,cfg,name,f)
   field_reports.append({'context':cfg,'field':r['field'],'class':name,'originConfig':r['config'],'method':r['method'],'offset':f['offset'],'bytes':f['bytes'],'alignment':f['alignment'],'actualIdentity':f['identity'],'originIdentity':r.get('actualIdentity')})
  for name,rs in expected.items():assert set(maps[name])=={r['field']for r in rs},(cfg,name,'missing or unexpected fields')
  for x in records:
   if x['kind']=='FnDef':
    assert x['layout']['bytes']==0 and x['layout']['alignment']==1
    assert '::dispatch_old_refund'not in x['calleePath']and '::dispatch_growth_check'not in x['calleePath']and 'DispatchOldRefund'not in x['calleePath']
    fndef_reports.append(dict(config=cfg,querySHA256=q['sha256'],**x))
   if x['kind']=='partition-body':partition_reports.append({'config':cfg,'body':x['path'],'partition':x['partition'],'defPathHash':x['defPathHash'],'rawSHA256':c.sha(x['mir'].encode()),'span':x['span']})
  context_reports[cfg]={'query':q,'target':ctx[0],'bodies':len(bs),'canonicalLocals':len(locals),'classes':{n:{'bytes':v['layout']['bytes'],'alignment':v['layout']['alignment'],'fields':len(maps[n])}for n,v in cls.items()},'allCanonicalFourRoles':True,'allExactTypedFields':True,'allUnionFieldsHaveRecursiveIdentityAndFullLayoutBridge':True,'disjointFieldsIncludingNamedZeroRoles':True}
 # The final paired compiler metadata probes must project exactly to the frozen source.
 pairs={};prior=0;frozen_bounds={}
 for cfg in final_bindings:
  b=read(c.HERE/f'paired-layout-baseline-{cfg}.json');n=read(c.HERE/f'paired-layout-candidate-{cfg}.json');assert b['exitCode']==n['exitCode']==0
  assert b['sourceClosure']=='1e89853d56f0ae46720cb0e9d72a4a2a13003f777e1d01f65db154f30782ed9c';assert n['sourceClosure']==final['sourceClosure']
  assert b['owners']==n['owners']and b['types']==n['types'];bt=b['totals'];nt=n['totals']
  assert nt['header']==bt['header']+nt['calls_permanent'];assert nt['frame']==bt['frame']+nt['calls_active']
  for k in bt:
   if k not in ['header','frame']:assert bt[k]==nt[k],(cfg,k)
  for phase in ['active','permanent']:
   assert nt['calls_'+phase]==sum(nt['calls_'+part+'_'+phase]for part in ['typed','kind','never','numeric'])
  assert nt['header']+nt['frame']<=nt['state_limit']<=nt['combined_limit']
  baseline_raw=gzip.decompress((c.HERE/b['attempt']/b['compilerLayouts']['path']).read_bytes());candidate_raw=gzip.decompress((c.HERE/n['attempt']/n['compilerLayouts']['path']).read_bytes());assert c.sha(baseline_raw)==b['compilerLayouts']['sha256']and c.sha(candidate_raw)==n['compilerLayouts']['sha256']
  baseline_types=json.loads(baseline_raw);candidate_types=json.loads(candidate_raw);old_classes={k:v for k,v in baseline_types.items()if ('Positions'in k or 'Inventory'in k)and k.startswith(('experimental_swift_reactor::','experimental_wasi::'))};assert old_classes
  for k,v in old_classes.items():assert k in candidate_types and candidate_types[k]==v,(cfg,k,'prior class drift')
  if cfg.startswith('all-'):
   def bound(ts):
    sizes={k:ts[k]['bytes']for k in ['experimental::execution::SpanInstance','experimental::cache::FunctionCache','experimental::execution::ExecutionFailure','experimental::cache::CacheFailure','experimental::cache::DecodedInstruction','experimental::execution::Control',"experimental::execution::ScalarReader<'_>"]}
    value=sizes['experimental::execution::SpanInstance']-sizes['experimental::cache::FunctionCache']+3*sizes['experimental::execution::ExecutionFailure']+2*sizes['experimental::cache::CacheFailure']+sizes['experimental::cache::DecodedInstruction']+sizes['experimental::execution::Control']+sizes["experimental::execution::ScalarReader<'_>"]+512
    assert value==2912;return dict(bytes=value,actualCompilerSizes=sizes,unchangedLiteral=512)
   frozen_bounds[cfg]={'baseline':bound(baseline_types),'candidate':bound(candidate_types)}
   assert frozen_bounds[cfg]['baseline']==frozen_bounds[cfg]['candidate']
  prior+=len(old_classes);pairs[cfg]={'baseline':b,'candidate':n,'priorClassesByteEqual':len(old_classes)}
 frozen=read(c.HERE/'frozen-identity.json');assert frozen['baseline']['methods']==frozen['candidate']['methods']and len(frozen['baseline']['methods'])==39
 # Growth fixture hooks and owners are an exact original prefix; only external harness helpers append.
 rel='src/experimental_swift_reactor/memory_growth_operations_tests.rs';assert (c.HERE/'candidate'/rel).read_bytes().startswith((c.HERE/'baseline'/rel).read_bytes())
 report={'sourceClosure':final['sourceClosure'],'methodCounts':method_counts,'roles':len(rows),'finiteNumericRoles':len(numeric),'phaseCounts':summary['phases'],'numericBytes':summary['numericBytes'],'contexts':context_reports,'pairedLayouts':pairs,'allPriorClassesEqual':True,'priorClassComparisons':prior,'frozen2912Bounds':frozen_bounds,'all39FrozenExpandedMethodsEqual':True,'growthHookOriginalPrefixEqual':True,'runtimeQualified':False,'independentAccountingAccepted':False,'scope':'Exact logical named roles, not stack/RSS or full Swift lifecycle acceptance'}
 artifacts={'final-accounting-report.json':c.enc(report),'final-query-bindings.json':c.enc(final_bindings),'final-runtime-body-reconciliation.json':c.enc(body_reports),'final-function-item-operands.json.gz':gzip.compress(c.enc(fndef_reports),mtime=0),'final-compiler-partition.json':c.enc(partition_reports),'final-typed-field-layouts.json.gz':gzip.compress(c.enc(field_reports),mtime=0)}
 artifacts.update(bridge.artifacts())
 for name,data in artifacts.items():
  path=c.HERE/name
  if write:c.save(path,data)
  else:assert path.read_bytes()==data,name
 print('Final accounting reconciliation passed:',len(rows),'roles,',len(numeric),'finite numeric roles,8MIR/16layouts,39Frozen; independent acceptance pending')
if __name__=='__main__':main('--check'not in sys.argv)
