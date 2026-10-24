#!/usr/bin/env python3
"""Finite selected-position reconciliation; no type name wildcard grants credit."""
from pathlib import Path
import collections,gzip,json,re,sys
from review import BASE,PACKET,read,require,sha,logical_bytes
HERE=Path(__file__).resolve().parent
AUTH=BASE/'verification/swift-calls-dispatch-root-review'
AUDIT=BASE/'verification/swift-optimized-accounting-contract-audit'
PREFIX='experimental_swift_reactor::execution::frame_operations::'
FREE=['check','trap','pop_checked','typed_i32','frame_guard','fetch','prefix','call_selected','signature_mismatch','indirect','local_slot','local_get','local_set','global_get','global_set','select_guard','publication','result_guard','run','complete']
def body(n):
 n=re.sub(r'::<impl at [^>]+>::enter_inner',"::FrameOperationPhase::<'_>::enter_inner",n)
 n=re.sub(r'host_runtime_import::<impl at [^>]+>::host_operation_inner',"host_runtime_import::<impl experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'_>>::host_operation_inner",n)
 n=re.sub(r'memory_growth_operations::<impl at [^>]+>::prepare_growth','memory_growth_operations::<impl experimental_swift_reactor::execution::SwiftReactorInstance>::prepare_growth',n)
 if n.startswith(('memory_growth_operations::','host_runtime_import::')):n=PREFIX+n
 if n.split('::')[0]in FREE:n=PREFIX+'call_dispatch::'+n
 if n.split('::')[0]in ['CHECK_COUNT','CANCEL_AT']:n=PREFIX+'call_dispatch::tests::'+n
 return n
def closure_coordinates(s):return re.sub(r'(?<=\.rs):\d+:\d+(?:: \d+:\d+)?',':<compiler-source-coordinates>',s)
def display(s):return re.sub(r'DefId\(\d+:\d+ ~','DefId(<compiler-session-index> ~',json.dumps(s,sort_keys=True))
def main():
 old=read(PACKET/'finite-numeric-positions-v4.json');final=read(PACKET/'finite-numeric-positions-v5.json');oldmap={r['field']:r for r in old};finalmap={r['field']:r for r in final};require(set(oldmap)==set(finalmap)and len(oldmap)==1032,'finite set drift');records=[];used=set();counts=collections.Counter()
 def add(group,origin,current,projection_proof=None):
  field=current['field'];require(field not in used,'selected position reused '+field);used.add(field);counts[group]+=1
  records.append({'selection':group,'origin':origin,'v4Field':field,'v4Binding':current['binding'],'v4MirType':current['mirType'],'v4ActualIdentity':current['actualIdentity'],'v4BodySHA256':current['bodySHA256'],'v4QuerySHA256':current['querySHA256'],'finalField':field,'finalBinding':finalmap[field]['binding'],'finalActualIdentity':finalmap[field]['actualIdentity'],'finalBodySHA256':finalmap[field]['bodySHA256'],'finalQuerySHA256':finalmap[field]['querySHA256'],'sourceCoordinateDrift':origin.get('mirType')!=current.get('mirType'),'compilerLocalRenumbered':origin.get('binding','_'+str(origin.get('local')))!=current['binding'],'exactNormalizedRawVecProjectionWhenRenumbered':projection_proof})
 root=read(AUTH/'optimized-accounting-amendment.json')
 for rel,h in root['bindings'].items():
  if rel in ['verification/swift-optimized-accounting-contract-audit/closure-substitutions.json','verification/swift-optimized-accounting-contract-audit/exact-private-inventory.json']:require(sha((BASE/rel).read_bytes())==h,'original selected inventory drift')
 index=collections.defaultdict(list)
 for r in old:index[(r['config'],r['body'],r['binding'],r['position'],closure_coordinates(r['mirType']))].append(r)
 for r in read(AUDIT/'closure-substitutions.json'):
  key=(r['config'],body(r['function']),r['binding'],r['position'],closure_coordinates(r['mirType']));matches=index[key];require(len(matches)==1,'original closure position missing/ambiguous '+str(key));require(matches[0]['kind']=='canonical'and matches[0]['method']=='finite-numeric-actual-closure','closure kind/proof drift');add('original560actual-closure-positions',r,matches[0])
 groups=read(AUDIT/'exact-private-inventory.json');body_cache={}
 def projection(lines,binding):
  out=[]
  for line in lines:
   if re.search(r'\b'+re.escape(binding)+r' = copy .*RawVec<',line):out.append(re.sub(r'_\d+','_<compiler-local>',line.split('//',1)[0].strip()))
  require(len(out)==1,'ambiguous finite RawVec capacity projection');return out[0]
 def compiler_body(cfg,name):
  if cfg not in body_cache:
   q=read(PACKET/'accounting-v4-summary.json')['queryBindings'][cfg];raw=gzip.decompress((PACKET/q['attempt']/'exact-layouts.jsonl.gz').read_bytes());require(sha(raw)==q['sha256']and q['exitCode']==0,'historical compiler query binding');body_cache[cfg]={r['path']:r['mir']for r in map(json.loads,raw.splitlines())if r['kind']=='body'and r['promoted']is None}
  return body_cache[cfg][name]
 for g in groups:
  if g['groupId']in ['U07','U09','U13']:continue
  for r in g['positions']:
   key=(r['config'],body(r['function']),r['binding'],r['position'],closure_coordinates(r['mirType']));matches=index[key];projection_proof=None
   if not matches and g['groupId']=='U08':
    evidence=next(x['mirEvidence']for x in g['positions']if all(x[k]==r[k]for k in ['config','function','binding'])and'mirEvidence'in x)
    origin_projection=projection(evidence['declarationAndUses'],r['binding']);projection_proof=origin_projection;candidates=[x for x in old if x['config']==r['config']and x['body']==body(r['function'])and x['position']==r['position']and x['mirType']==r['mirType']]
    matches=[x for x in candidates if projection(compiler_body(x['config'],x['body']).splitlines(),x['binding'])==origin_projection]
    for x in matches:require(sha(compiler_body(x['config'],x['body']).encode())==x['bodySHA256'],'RawVec projection is not exact bound compiler body')
   require(len(matches)==1,'original private position missing/ambiguous '+str(key));require(matches[0]['method']=='finite-numeric-private-std','private proof drift');add('original248private-std-positions',r,matches[0],projection_proof)
 for name,amendment,total,group in [('compiler-discovered-closure-positions.json','compiler-discovered-closure-amendment.json',96,'compiler-discovered96closure-positions'),('compiler-constant-exception-positions-v3.json','compiler-constant-exception-amendment-v3.json',120,'constant112closure-plus8PhantomData'),('compiler-unstable-global-positions-v3.json','compiler-unstable-global-amendment-v3.json',8,'constant8Global')]:
  selected=read(AUTH/name);a=read(AUTH/amendment);require(len(selected)==total,'selected finite map extent');require(sha((AUTH/name).read_bytes())==a.get('sha256',a.get('manifestSHA256')),'selected finite map digest')
  for r in selected:
   if 'field'in r and r['field']in oldmap:current=oldmap[r['field']]
   else:
    matches=[x for x in old if (x['config'],x['body'],x.get('local'),x['position'])==(r['config'],r['body'],r.get('local'),r['position'])];require(len(matches)==1,'selected TLS position ambiguous');current=matches[0]
   require(r['actualIdentity']==current['actualIdentity'],'selected actual type identity drift')
   require(display(r['actualType'])==display(current['actualType'])and display(r['layout'])==display(current['layout']),'selected actual type/layout drift')
   if total!=96:require(all(r[k]==current[k]for k in ['body','bodyDefPathHash','bodySHA256','binding','config','position','promoted','kind','querySHA256']),'selected constant source binding drift')
   add(group,r,current)
 require(used==set(oldmap),'unselected numeric exception '+str(set(oldmap)-used))
 raw=(json.dumps(records,sort_keys=True,indent=2)+'\n').encode();(HERE/'selected-authority-reconciliation.json.gz').write_bytes(gzip.compress(raw,mtime=0));receipt={'schema':1,'status':'finite-selected-authority-reconciliation-passed','command':sys.argv,'tool':sys.version,'positions':len(used),'selectedCounts':dict(counts),'mappingLogicalSHA256':sha(raw),'accountingAccepted':False,'qualifiedRuntimeExecuted':False};(HERE/'selected-authority-review.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
