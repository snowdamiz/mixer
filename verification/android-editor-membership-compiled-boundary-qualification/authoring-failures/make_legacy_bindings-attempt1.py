from pathlib import Path
import json,gzip,collections
D=Path(__file__).resolve().parent;Q=D.parent;E=D/'context17-1';inv=json.loads((E/'product-class-inventory.json').read_bytes());oldinv=json.loads((Q/'host-class-inventory.json').read_bytes());oldby={r['id']:r for r in oldinv['rows']};hist=json.loads((Q/'historical-dispositions.json').read_bytes())['records'];extra={r['historical_id']:r['fresh_compiled_candidates'] for r in json.loads((Q/'intermediate-historical-21/findings.json').read_bytes())['records']};oldmap={r['baseline']:r for r in json.loads((Q/'inputs/protocol/barrier-map.json').read_bytes())['records']};fields=('source','class','method','descriptor','source_line','opcode','target');rows=[]
for h in hist:
 key=h['historical_id'];sourcecandidates=[oldby[sid] for sid in h['exact_current_compiled_site_ids']] or extra.get(key,[]);matches=[]
 for a in sourcecandidates:
  matches.extend([r for r in inv['rows'] if all(r[k]==a[k] for k in fields)])
 if h['direct_adapter_replacement_site_ids']:
  method=key.split('.')[-1]
  matches=[r for r in inv['rows'] if r['target']['owner']=='android/view/inputmethod/InputConnection' and r['target']['name']==method and 'direct-editor' in r['categories']]
  if method=='closeConnection':matches=[r for r in inv['rows'] if r['class']=='dev/mixer/android/NativeAppearanceViewsV2$NativeField' and r['method']=='drain' and r['target']['owner']=='android/view/inputmethod/InputConnection' and r['target']['name']=='closeConnection']
 assert matches,(key,sourcecandidates);matches=list({r['id']:r for r in matches}.values());rows.append({'historical_id':key,'original_boundary':oldmap[key]['boundary'],'fresh_compiled_candidates':matches,'disposition':'replaced-direct-adapter' if h['direct_adapter_replacement_site_ids'] or key in extra and extra[key][0]['source'].endswith('NativeEditorConnectionV2.java') else 'retained-with-reviewed-current-authority','behavioral_state_qualification':'pending','root_independent_semantic_review':'pending'})
# Discover actual exact caller/native entry/return candidates in unchanged legacy scenarios.
index={(r['class'].replace('/','.'),r['method'],r['descriptor'],r['bci']):r['id'] for r in inv['rows']}
for item in rows:
 candidateids={r['id'] for r in item['fresh_compiled_candidates']};hits=[]
 for p in sorted(E.glob('legacy-discovery-*.jsonl.gz')):
  with gzip.open(p,'rt') as f:run=json.loads(f.readline())
  for i,event in enumerate(run['native_sequence']):
   frameids=[index.get((f['class'],f['method'],f['descriptor'],f['bci'])) for f in run['frame_sets'][event['frame_set']]]
   ids=candidateids.intersection(frameids)
   if not ids:continue
   boundary=item['original_boundary'];target=boundary['entry_native_suffix'] if event['phase']=='entry' else boundary['return_native_suffix']
   if target=='*' or event['method']==target or event['method'].endswith('.'+target):hits.append({'scenario':run['scenario'],'sequence_index':i,'phase':event['phase'],'native_method':event['method'],'caller_ids':sorted(ids),'receiver_identity':event['receiver_identity'],'frame_set':event['frame_set']})
 item['discovery_hits']=hits;item['witness_scenarios']=sorted(set(h['scenario'] for h in hits));item['discovered_entry_and_return']=any(h['phase']=='entry' for h in hits) and any(h['phase']=='beforeReturn' for h in hits)
(E/'legacy189-bindings.json').write_text(json.dumps({'schema':1,'source_tree':inv['product_tree'],'context':'official17-normal-no-g','all189_preserved':True,'records':rows,'state_qualification':False},indent=2)+'\n');print('rows',len(rows),'both anchors',sum(r['discovered_entry_and_return'] for r in rows),'no hits',[r['historical_id'] for r in rows if not r['discovery_hits']])
