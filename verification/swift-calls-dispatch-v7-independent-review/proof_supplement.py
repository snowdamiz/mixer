#!/usr/bin/env python3
"""Independent V7 source/seal/fixture graph replay; no producer code imports."""
from pathlib import Path
import collections, datetime, difflib, gzip, hashlib, json, re, sys, traceback
from review import BASE, PACKET, archive, contexts, logical_bytes, read, require, sha
HERE = Path(__file__).resolve().parent
OLD = BASE / 'verification/swift-calls-dispatch'
SOURCE = '78e2586b41f698c60e1bcd4cdd4abb33fbf98d747d1ee183a793988dea7b5237'
SEAL = '79089f1ef382a14e02fbbbf0a6e6dcd0a67158bcfa5354d565a5b037b1d149b2'
SELECTED = [
 'experimental_swift_reactor::execution::frame_operations::tests::af22_frozen_accounting_and_value_phase_reservations_stay_distinct',
 'experimental_swift_reactor::execution::frame_operations::memory_operations::tests::mm16_accounting_restore',
 'experimental_swift_reactor::execution::frame_operations::bulk_memory_operations::tests::bm16_accounting_restore']
PREFIXES = [x.rsplit('::', 1)[0] + '::' for x in SELECTED]
enc = lambda x: (json.dumps(x, sort_keys=True, indent=2) + '\n').encode()
def digest(p):
 h = hashlib.sha256()
 with p.open('rb') as f:
  while block := f.read(1024 * 1024): h.update(block)
 return h.hexdigest()
def manifest(p):
 return {str(q.relative_to(p)): digest(q) for q in sorted(p.rglob('*')) if q.is_file() and 'target' not in q.relative_to(p).parts}
def normalized(x):
 if isinstance(x, str): return re.sub(r'DefId\(\d+:\d+ ~ ', 'DefId(<compiler-session-index> ~ ', x)
 if isinstance(x, list): return [normalized(v) for v in x]
 if isinstance(x, dict): return {k:normalized(v) for k,v in x.items() if k != 'querySHA256'}
 return x
def query(base, q):
 raw = gzip.decompress((base / q['attempt'] / 'exact-layouts.jsonl.gz').read_bytes())
 require(sha(raw) == q['sha256'] and len(raw) == q['bytes'], 'query digest/extent')
 rows = [json.loads(s) for s in raw.splitlines()]
 require(len(rows) == q['records'], 'query record count')
 return rows
def full(base, q):
 rows = [x for x in read(base / q['attempt'] / 'artifacts.json') if x['path'].endswith('.mir.gz')]
 require(len(rows) == 1, 'full MIR archive ambiguity')
 raw = gzip.decompress((base / q['attempt'] / rows[0]['path']).read_bytes())
 require(sha(raw) == rows[0]['sha256'] and len(raw) == rows[0]['bytes'], 'full MIR digest/extent')
 return raw.decode()
def bodies(text):
 result = collections.defaultdict(list)
 for m in re.finditer(r'(?m)^([^\s][^\n]*\{)\n', text):
  end = text.index('\n}\n', m.end()) + 3
  result[m[1]].append(text[m.start():end])
 return result
def family(path):
 return next((s for s in SELECTED if path == s or path.startswith(s+'::')), None)
def check_source():
 before = manifest(OLD / 'candidate'); after = manifest(PACKET / 'candidate'); baseline = manifest(PACKET / 'baseline')
 require(sha(enc(before)) == 'ba9231499244692bbed61f0566ec72864a979df9e3fc71511560ec66a2e00c70', 'V5 source drift')
 require(sha(enc(after)) == SOURCE and sha(enc(baseline)) == '1e89853d56f0ae46720cb0e9d72a4a2a13003f777e1d01f65db154f30782ed9c', 'source closure drift')
 require(read(PACKET/'candidate-final-manifest.json') == after, 'manifest versus actual source')
 archive(PACKET/'candidate-final-source.tar.gz', after)
 root = BASE / 'verification/swift-calls-dispatch-root-review'
 first = read(root/'frame-bound-fixture-amendment.json'); extra = read(root/'additional-frame-bound-fixture-amendment.json')
 edits = [(first['file'],first['exactOldExpression'],first['exactNewExpression'],first['originalFileSHA256'],first['expectedCorrectedFileSHA256'])]
 edits += [(r['file'],r['exactOldSuffix'],r['exactNewSuffix'],r['oldSHA256'],r['newSHA256']) for r in extra['selectedFiles']]
 insertions = {}; diffs = []
 for rel, old, new, oldhash, newhash in edits:
  a=(OLD/'candidate'/rel).read_bytes(); b=(PACKET/'candidate'/rel).read_bytes()
  require(sha(a)==oldhash and sha(b)==newhash and a.count(old.encode())==1, 'authorized amendment hash/uniqueness')
  require(a.replace(old.encode(),new.encode())==b, 'unselected source mutation')
  at=next(i for i,(x,y)in enumerate(zip(a,b)) if x!=y); delta=len(b)-len(a)
  require(delta>0 and a[at:]==b[at+delta:], 'source amendment is not single insertion')
  insertions[rel]=(a[:at].count(b'\n')+1,len(a[:at].rsplit(b'\n',1)[-1])+1,delta)
  diffs.extend(difflib.unified_diff(a.decode().splitlines(True),b.decode().splitlines(True),fromfile='v5/'+rel,tofile='v7/'+rel))
 selected={x[0]for x in edits}; changed={x for x in before.keys()|after.keys() if before.get(x)!=after.get(x)}
 delta={x for x in baseline.keys()|after.keys() if baseline.get(x)!=after.get(x)}
 require(changed==selected and len(delta)==11 and len(after)==130 and len(baseline)==128, 'source delta closure')
 require(delta-selected==set(read(OLD/'review-seal.json')['allowedChangedCandidateFiles']), 'eight implementation file set changed')
 (HERE/'selected-fixture-source.diff').write_text(''.join(diffs))
 return insertions, {'baselineFiles':len(baseline),'candidateFiles':len(after),'changedFromV5':sorted(changed),'changedFromBaseline':sorted(delta),'originalEightImplementationFilesByteIdentical':True}
def old_header(header, insertions):
 def change(m):
  file=m[1]; a,b,c,d=map(int,m.groups()[1:]); edit=insertions.get(file)
  if edit:
   def point(line,col):
    if line==edit[0] and col>=edit[1]:
     require(col>=edit[1]+edit[2], 'header coordinate inside inserted expression'); col-=edit[2]
    return line,col
   a,b=point(a,b);c,d=point(c,d)
  return f'{file}:{a}:{b}: {c}:{d}'
 return re.sub(r'(src/[^\s{}<>]+\.rs):(\d+):(\d+): (\d+):(\d+)',change,header)
def check_roles():
 a={r['field']:r for r in read(OLD/'inventory-v5.json')};b={r['field']:r for r in read(PACKET/'inventory-v5.json')}
 require(a.keys()==b.keys() and len(a)==89124, 'role omission/addition')
 for name in a: require(normalized(a[name])==normalized(b[name]), 'role descriptor/phase/interval drift '+name)
 fa={r['field']:r for r in read(OLD/'finite-numeric-positions-v5.json')};fb={r['field']:r for r in read(PACKET/'finite-numeric-positions-v5.json')}
 require(fa.keys()==fb.keys() and len(fa)==1032, 'finite position scope drift')
 for name in fa: require(normalized(fa[name])==normalized(fb[name]), 'finite identity/interval drift '+name)
 return {'roles':len(b),'finite':len(fb),'phases':dict(collections.Counter(r['ownerClass']for r in b.values())),'exactFieldsAndDescriptorsPreservedExceptQueryDigestAndCompilerDisplayIndex':True}
def check_context(cfg, q, insertions):
 oldq=read(OLD/f'exact-query-{cfg}.json'); old=query(OLD,oldq); new=query(PACKET,q)
 oldruntime={(r['path'],r['promoted']):r for r in old if r['kind']=='body'}
 runtime={(r['path'],r['promoted']):r for r in new if r['kind']=='body'}
 require(runtime==oldruntime, 'raw runtime body changed '+cfg)
 prior={r['defPathHash']:r for r in old if r['kind']=='partition-body'}; parts={r['defPathHash']:r for r in new if r['kind']=='partition-body'}
 require(len(parts)==sum(r['kind']=='partition-body'for r in new) and prior.keys()<=parts.keys(), 'partition identity ambiguity/omission')
 for k in prior: require(prior[k]==parts[k], 'prior helper/TLS/fixture partition drift')
 graph=[r for r in new if r['kind']=='scope-graph-body']; uses=[r for r in new if r['kind']=='scope-graph-function-item-use']
 ids={(r['defPathHash'],r['promoted']):r for r in graph}
 require(len(ids)==len(graph) and graph, 'duplicate/empty graph identities')
 raw=full(PACKET,q); oldraw=full(OLD,oldq); finalblocks=bodies(raw); oldblocks=bodies(oldraw)
 for r in graph:
  if r['defKind'] in ['Fn','AssocFn','Closure','Ctor(Struct, Fn)','Ctor(Variant, Fn)'] or r['promoted'] is not None:
   require(r['header'] in finalblocks, 'executable graph header absent from complete emitted MIR '+r['path'])
  else:
   require(r['defKind'] in ['AnonConst','Const { is_type_const: false }','AssocConst { is_type_const: false }'] or r['defKind'].startswith('Static {'), 'unsupported non-executable graph definition')
   # The callback returns actual CTFE MIR headers for constants; rustc emits
   # evaluated constants as single-line values. Those headers are metadata,
   # not falsely claimed as identical emitted executable MIR bytes.
   require(r['span'] and r['path'] and r['header'], 'incomplete actual CTFE graph metadata')
 for edge in uses:
  require((edge['bodyDefPathHash'],edge['promoted'])in ids, 'graph edge owner missing')
  owner=ids[edge['bodyDefPathHash'],edge['promoted']]
  require(edge['path']==owner['path'] and edge['span'] and edge['location'] and edge['actualType'].startswith('FnDef('), 'graph edge actual owner/type drift')
 additional=[r for k,r in parts.items() if k not in prior]
 scoped=[r for r in graph if any(r['path'].startswith(p)for p in PREFIXES)]
 # Every non-promoted actual body in the three added source partitions has a
 # complete partition record. Promoted bodies are bound directly to raw MIR.
 require({(r['defPathHash'],None)for r in additional} == {(r['defPathHash'],None)for r in scoped if r['promoted']is None}, 'incomplete three-family actual partition')
 changed=[]; promoted_changed=[]; bridged=0
 for r in scoped:
  if r['defKind'] not in ['Fn','AssocFn','Closure','Ctor(Struct, Fn)','Ctor(Variant, Fn)'] and r['promoted'] is None:continue
  matches=finalblocks[r['header']];require(len(matches)==1, 'ambiguous raw scoped graph header '+r['header']); body=matches[0]
  header=r['header']; before=oldblocks.get(header,[])
  if not before:
   require(family(r['path']) is not None, 'coordinate bridge outside selected fixture family')
   header=old_header(header,insertions);before=oldblocks.get(header,[]);bridged+=1
  require(len(before)==1, 'missing/ambiguous original actual scoped body '+header)
  if before[0]!=body:
   require(family(r['path']) is not None, 'original helper/TLS actual MIR changed '+r['path'])
   item={'path':r['path'],'defPathHash':r['defPathHash'],'promoted':r['promoted'],'oldSHA256':sha(before[0].encode()),'finalSHA256':sha(body.encode())}
   diff=''.join(difflib.unified_diff(before[0].splitlines(True),body.splitlines(True),fromfile='old/'+r['path'],tofile='final/'+r['path']))
   diffpath=HERE/'fixture-raw-diffs'/cfg/(sha(enc([r['defPathHash'],r['promoted']]))[:20]+'.diff');diffpath.parent.mkdir(parents=True,exist_ok=True);diffpath.write_text(diff);item['rawDiff']=str(diffpath.relative_to(HERE))
   (promoted_changed if r['promoted']is not None else changed).append(item)
 for r in additional:
  require(r['partition']=='prior-selected-test-body-preserve-original-classification', 'new namespace accounting exemption')
  require((r['defPathHash'],None)in ids and r['mir'].splitlines()[0]==ids[r['defPathHash'],None]['header'], 'actual partition identity/header drift')
  if r['defKind'] in ['Fn','AssocFn','Closure','Ctor(Struct, Fn)','Ctor(Variant, Fn)']:
   require(raw.count(r['mir'])==1, 'executable partition body absent/ambiguous in full raw MIR')
 require(len(changed)==(7 if cfg.endswith('-unit') else 0), 'changed fixture family count')
 # Selected fixture promotions are retained as raw differences too. They are
 # never admitted runtime bodies or new accounting credit.
 for item in promoted_changed:require(family(item['path']) is not None, 'changed promoted body outside exact selected fixture family')
 fixtures=[]; incoming_report={}
 for f in SELECTED:
  found=[r for r in scoped if r['path']==f and r['defKind']=='Fn' and r['promoted']is None]
  require(len(found)==int(cfg.endswith('-unit')), 'exact fixture identity count')
  for r in found:
   fixtures.append(r['defPathHash']); incoming=[e for e in uses if e['calleeDefPathHash']==r['defPathHash']]
   allowed={f+'::{closure#0}'}
   if f==SELECTED[0]:allowed.add('experimental_swift_reactor::execution::frame_operations::tests::control_tests::sc11_completion_accounting')
   require({e['path']for e in incoming}==allowed and all(e['promoted']is None for e in incoming), 'unselected actual fixture ingress')
   incoming_report[f]=[{'owner':e['bodyDefPathHash'],'path':e['path'],'promoted':e['promoted'],'location':e['location']}for e in incoming]
 require(not any(r['kind']=='FnDef' and r['calleeDefPathHash']in fixtures for r in new), 'selected runtime reaches corrected fixture')
 # Conservative actual FnDef reachability from every selected runtime body,
 # retaining owner hashes and promoted indexes rather than displayed names.
 edges=collections.defaultdict(set)
 for e in uses:edges[e['bodyDefPathHash']].add(e['calleeDefPathHash'])
 seen={r['defPathHash']for r in runtime.values()}; todo=list(seen)
 while todo:
  for callee in edges[todo.pop()]:
   if callee not in seen:seen.add(callee);todo.append(callee)
 require(not seen.intersection(fixtures), 'transitive runtime FnDef path to corrected fixture')
 receipt=read(PACKET/f'v7-original-test-partition-{cfg}.json')
 require(receipt['actualWholeCrateGraphBodies']==len(graph) and receipt['actualWholeCrateFunctionItemUses']==len(uses) and receipt['actualPromotedGraphBodies']==sum(r['promoted']is not None for r in graph), 'producer graph count differs from raw metadata')
 require({r['defPathHash']for r in receipt['additionalActualRecords']}=={r['defPathHash']for r in additional}, 'producer additional partition record set')
 return {'runtimeBodiesRawByteEqual':len(runtime),'wholeCrateGraphBodies':len(graph),'actualFnDefUses':len(uses),'promotedGraphBodies':sum(r['promoted']is not None for r in graph),'scopedActualBodiesIncludingPromoted':len(scoped),'additionalActualPartitions':len(additional),'changedFixtures':changed,'changedPromotedBodies':promoted_changed,'sourceCoordinateHeaderBridges':bridged,'exactFixtureIncomingOwners':incoming_report,'runtimeFnDefReachabilityHasNoCorrectedFixture':True}
def check_seal():
 require(digest(PACKET/'review-seal.json')==SEAL, 'producer-confirmed seal digest')
 seal=read(PACKET/'review-seal.json'); require(seal['version']==7 and seal['candidateSourceClosure']==SOURCE and not seal['runtimeQualified'], 'seal source/scope')
 require((PACKET/'review-seal.sha256').read_text().strip()==SEAL+'  review-seal.json', 'seal sidecar')
 total=0
 for rel,b in seal['bindings'].items():
  require(not Path(rel).is_absolute() and '..' not in Path(rel).parts, 'sealed path escape')
  p=PACKET/rel;require(p.stat().st_size==b['bytes'] and digest(p)==b['sha256'], 'sealed bytes drift '+rel);total+=b['bytes']
 require(digest(OLD/'review-seal.json')==seal['parentSealSHA256']=='7d5a043e7c982a84d5fe1a85444a6a492a40ebddf87a36e95ebdedde02593b15','historical V5 seal drift')
 return {'producerSealSHA256':SEAL,'files':len(seal['bindings']),'bytes':total,'parentSealSHA256':seal['parentSealSHA256']}
def main():
 result={'schema':1,'status':'in-progress','command':sys.argv,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pythonVersion':sys.version,'verifierSHA256':digest(Path(__file__)),'compilerExecuted':False,'qualifiedRuntimeExecuted':False,'nativeInstancesCreated':0,'accountingAccepted':False}
 try:
  result['seal']=check_seal();insertions,result['source']=check_source();result['sourceHeaderInsertions']=insertions;result['roles']=check_roles();result['contexts']={}
  queries=read(PACKET/'final-query-bindings.json');require(set(queries)==set(contexts()),'eight contexts')
  for cfg,q in queries.items():result['contexts'][cfg]=check_context(cfg,q,insertions)
  result['status']='independent-source-seal-fixture-graph-supplement-passed'
 except BaseException:result.update(status='rejected',failure=traceback.format_exc())
 (HERE/'proof-supplement.json').write_bytes(enc(result));print(json.dumps({k:v for k,v in result.items()if k!='contexts'},indent=2));return result['status']=='rejected'
if __name__=='__main__':raise SystemExit(main())
