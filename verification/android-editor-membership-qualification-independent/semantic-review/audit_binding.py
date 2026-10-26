#!/usr/bin/env python3
"""Independent static identity audit; explicit semantic and state qualification remain pending."""
import hashlib,importlib.util,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
D=Path(__file__).resolve().parent
P=D/'input'
R=D.parent
CLASSES=R/'derivative-review/run-first/classes'
RELEASED=R/'preaccess/interface-v3'
def digest(b):return hashlib.sha256(b).hexdigest()
def identity(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':digest(b)}
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
spec=importlib.util.spec_from_file_location('independent_semantic_classfile',RELEASED/'classfile.py');cf=importlib.util.module_from_spec(spec);spec.loader.exec_module(cf)
reference=json.loads((RELEASED/'reference-obligations.json').read_bytes())
sources={p.name:identity(p) for p in (P/'accepted-source').glob('*.java')};assert sources==reference['exact16_source_map']
parsed={};class_map={}
for p in CLASSES.rglob('*.class'):
 c=cf.parse(p.read_bytes())
 if c['source_file'] in sources:
  assert c['class'] not in parsed;parsed[c['class']]=c;class_map[p.relative_to(CLASSES).as_posix()]=identity(p)
context=digest(json.dumps({'source_map':sources,'class_map':class_map},sort_keys=True,separators=(',',':')).encode())
assert context=='1b71af17048675296435ca74af284d54f93f2506b9c406517a452a3ce816dbdd'
assert len(parsed)==209
all_invocations=sum(1 for c in parsed.values() for m in c['methods'] for i in m['instructions'] if 0xb6<=i['opcode']<=0xba)
assert all_invocations==7256
def method(cl,name,descriptor):
 matches=[m for m in parsed[cl]['methods'] if m['name']==name and m['descriptor']==descriptor];assert len(matches)==1;return matches[0]
semantic=json.loads((P/'active-semantic-obligations.json').read_bytes());assert semantic['root_selected'] is False
subjects=semantic['subjects'];assert len(subjects)==280 and len({s['id'] for s in subjects})==280
for s in subjects:
 cl=parsed[s['class']];m=method(s['class'],s['method'],s['descriptor'])
 assert s['class_sha256']==class_map[s['class']+'.class']['sha256']
 assert s['source_sha256']==sources[cl['source_file']]['sha256']
 assert s['invocations']==[i for i in m['instructions'] if 0xb6<=i['opcode']<=0xba]
 assert s['returns_and_throws']==[i for i in m['instructions'] if i['opcode'] in (*range(0xac,0xb2),0xbf)]
 assert s['state_qualification']=='pending per-subject exact executable case binding'
original_file=Path('/Users/andreyyurlov/Documents/dev/mixer/verification/android-editor-integration-protocol/inputs/repo/verification/android-private-owner-integration-implementation/barrier-map.json')
original_bytes=original_file.read_bytes();assert digest(original_bytes)=='065099211419b03e3f6988db175f7445f43efce2c37f2fb0140f41889ea335a8'
(D/'original-barrier-map.json').write_bytes(original_bytes)
original=json.loads(original_bytes);byid={r['baseline']:r for r in original['records']};assert len(byid)==189
bindings=json.loads((P/'historical189-current-bindings.json').read_bytes());records=bindings['records'];assert len(records)==189 and {r['historical_id'] for r in records}==set(byid)==set(reference['historical189_ids'])
seen=set()
for r in records:
 assert r['original_boundary']==byid[r['historical_id']]['boundary']
 assert len(r['fresh_compiled_candidates'])==1
 b=r['fresh_compiled_candidates'][0];cl=parsed[b['class']];m=method(b['class'],b['method'],b['descriptor'])
 assert b['class_sha256']==class_map[b['class']+'.class']['sha256'] and b['source_sha256']==sources[cl['source_file']]['sha256']
 ins=[i for i in m['instructions'] if i['bci']==b['bci']];assert len(ins)==1
 assert ins[0]['mnemonic']==b['opcode'] and ins[0]['target']==b['target']
 key=(b['class'],b['method'],b['descriptor'],b['bci']);assert key not in seen;seen.add(key)
 assert r['behavioral_state_qualification']=='pending' and r['root_independent_semantic_review']=='pending'
scalar_category_examples=[s['id'] for s in subjects if s['id'].startswith('dev/mixer/android/AppearanceGeometryV2#close(') or s['id'].startswith('dev/mixer/android/OwnerLifecycleV2$Snapshot#close')]
pending_discovery=[r['historical_id'] for r in records if not r['discovered_entry_and_return']]
result={'scope':'Static exact compiled/source/BCI identity only against independently fresh JDK17 classes; not source-semantic mapping acceptance or behavior qualification',
 'context_id':context,'exact_sources':len(sources),'product_classes':len(parsed),'actual_invocations':all_invocations,
 'proposed_semantic_subjects_verified':len(subjects),'original189_identity_and_boundary_fields_verified':len(records),
 'distinct_current_historical_tuples':len(seen),'historical_ids_without_discovered_entry_and_return':pending_discovery,
 'scalar_name_category_examples_requiring_source_backed_disposition':scalar_category_examples,
 'all_original189_required_callback_states':sorted({state for row in original['records'] for state in row['required_cases']}),
 'source_revision_context_only':'Fresh reviewed input identities are the source authority; current Git HEAD is not used to authorize this audit.',
 'limitations':['Full per-subject semantic/case joins remain pending; classes alone cannot prove source semantic equivalence.',
 'Category assignment uses name/class substrings and needs source-backed scalar/factory/accessor versus actual callback applicability.',
 'Separate five V1 actual compiled positive callsites are not present in this semantic review packet and remain required.',
 'No final immutable semantic policy/context/execution-closure authority selected.'],
 'behavior_policy_or_GA_accepted':False}
save(D/'static-binding-audit.json',result);print(json.dumps({'classes':len(parsed),'invocations':all_invocations,'subjects':len(subjects),'historical_bindings':len(records),'semantic_behavior_accepted':False}))
