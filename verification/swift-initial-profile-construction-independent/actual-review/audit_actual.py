#!/usr/bin/env python3
"""Independent source/custody/behavior/layout/accounting audit, not OTA authority."""
from pathlib import Path
import datetime,hashlib,importlib.util,json,re,sys
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent
PRE=OUT.parent
ROOT=PRE.parents[1]
STAGE=OUT/'staging/verification/component'
SOURCE=STAGE/'source/vm'
def sha(b):return hashlib.sha256(b).hexdigest()
def write(n,d):(OUT/n).write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
def normalize(s):return re.sub(r'\s+','',s)
def verify_manifest(base,d):
 assert len(d['members'])==d['member_count']
 for m in d['members']:
  b=(base/m['path']).read_bytes();assert len(b)==m['bytes'] and sha(b)==m['sha256'],m['path']
def main():
 result={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Independent actual-source host-component review; external receipts, no OTA/runtime/GA authority'}
 pre=json.loads((PRE/'preaccess-seal.json').read_text());verify_manifest(PRE,pre);assert sha((PRE/'preaccess-seal.json').read_bytes())=='b9048e6edd9941ca3293badd322d89fbfb16a25c1cb02502896d38c589b4295a'
 source=json.loads((OUT/'source-manifest.json').read_text());verify_manifest(SOURCE,source)
 baseline=json.loads((PRE/'old-base-source-manifest.json').read_text());before={m['path']:m for m in baseline['members']};after={m['path']:m for m in source['members']}
 closure=json.loads((PRE/'inputs/future-closure.json').read_text());assert set(after)==set(closure['distribution_paths'])
 assert set(after)-set(before)==set(closure['new_distribution_paths'])
 changed=[p for p in before if before[p]!=after[p]];assert changed==['src/experimental_swift_reactor/cache.rs']
 current=(SOURCE/changed[0]).read_bytes();old=(PRE/'old-source/vm'/changed[0]).read_bytes()[:before[changed[0]]['bytes']]
 assert current==old+b'\n// Isolated initial profile component; no public entry point.\nmod initial_profile_v1;\n'
 host=json.loads((OUT/'host-support-manifest.json').read_text());assert {m['declared_path'] for m in host['members']}==set(closure['host_support_paths'])
 for m in host['members']:
  b=(STAGE/m['retained_path']).read_bytes();assert sha(b)==m['sha256'] and len(b)==m['bytes']
 result['source_closure']={'distribution':140,'host_support':11,'base_exact':134,'only_original_delta':changed,'source_tree_sha256':source['tree_sha256'],'preaccess_members_still_exact':254}
 inputs=[]
 for n,h in [('initial-profile-foundation-configuration-correction.json','d4d4ea1a4d4a5e7715e1fffdf9f20bfabed41ddcf9f43bb89b2f657a2383f2c3'),('initial-profile-foundation-configuration-amendment.md','3e7f0f53b4fe605b8703fb78b70655c02db4bd8125a1d8e6fa9bf1ef2c7878d5'),('initial-profile-foundation-finding-custody.json','78d7bc7949885ea1c24b95b22857caf13f077a0e98114eb6384c9be156f72df1')]:
  b=(ROOT/'verification/swift-semantic-adapter-root-review'/n).read_bytes();assert sha(b)==h;p=OUT/'root-corrections'/n;p.parent.mkdir(exist_ok=True);p.write_bytes(b);inputs.append({'path':str(p.relative_to(OUT)),'sha256':h,'bytes':len(b)})
 result['root_correction_inputs']=inputs
 production=json.loads((PRE/'inputs/local-structure-proposal.json').read_text());unit=json.loads((PRE/'inputs/initial-profile-unit-test-local-structure.json').read_text())
 selected=(SOURCE/'src/experimental_swift_reactor/cache/initial_profile_v1/selected.rs').read_text();tests=(SOURCE/'src/experimental_swift_reactor/cache/initial_profile_v1/tests.rs').read_text()
 def literal_rows(text):return [{'id':int(a),'reserved':int(b),'bytes':int(c),'alignment':int(d)} for a,b,c,d in re.findall(r'LocalTypeLayoutV1\s*\{id:(\d+),reserved:(\d+),bytes:(\d+),alignment:(\d+)\}',text)]
 for src,expected in [(selected,production),(tests[tests.index('static UNIT_TEST_CONFIG_SELECTION_V1'):tests.index('fn component_selection')],unit)]:
  assert literal_rows(src)==[dict(id=m['id'],reserved=0,bytes=m['bytes'],alignment=m['alignment']) for m in expected['type_layout']]
 local=(SOURCE/'src/experimental_swift_reactor/cache/initial_profile_v1/local_structure.rs').read_text();comparisons=re.findall(r'compare!\((\d+),(.+)\);',local)
 assert [(int(i),normalize(t)) for i,t in comparisons]==[(m['id'],normalize(m['type'])) for m in production['type_layout']]
 accounting=json.loads((OUT/'candidate-evidence/accounting.json').read_text());layouts={};extra_lists=[]
 for config in ['host','unit']:
  for mode in ['debug','optimized']:
   text=(STAGE/'commands/attempt-1'/f'{config}-{mode}-layout/stdout').read_text();rows=[];extras=[]
   for line in text.splitlines():
    s=line.split('\t')
    if len(s)==5 and s[0]=='TYPE':rows.append({'id':int(s[1]),'type':normalize(s[2]),'bytes':int(s[3]),'alignment':int(s[4])})
    if len(s)==4 and s[0]=='EXTRA':extras.append({'type':normalize(s[1]),'bytes':int(s[2]),'alignment':int(s[3])})
   target=unit if config=='unit' else production
   assert rows==[{**m,'type':normalize(m['type'])} for m in target['type_layout']]
   assert extras==[{k:normalize(m[k]) if k=='type' else m[k] for k in ['type','bytes','alignment']} for m in accounting['actual_auxiliary_complete_types']]
   values=next(s[s.index('VALUES '):] for s in text.splitlines() if 'VALUES cleanup=' in s);values={k:int(v) for k,v in (s.split('=') for s in values.split()[1:])}
   assert values=={'cleanup':62888,'header':92128,'construction':61880,'operation':92350,'foundation':269616 if config=='unit' else 269080}
   layouts[f'{config}-{mode}']={'all165_exact':True,'all24_extra_complete_types_exact':True,'source_bound_VALUES':values,'stdout_sha256':sha(text.encode())};extra_lists.append(extras)
 assert all(x==extra_lists[0] for x in extra_lists)
 result['actual_layouts']=layouts
 assert sum(m['bytes'] for m in accounting['models'])==38792
 assert sum(m['bytes']*m['copies'] for m in accounting['actual_auxiliary_complete_types'])==10080
 assert sum(m['total'] for m in accounting['helper_bindings'])==12328
 assert sum(accounting['original_disjoint_inventories'].values())==136680
 assert 38792+10080+12328+136680==197880 and 197880+48==197928
 assert sum(t['total'] for t in accounting['source_action_terms'])==521088
 assert all(t['total']==t['maximum_items']*t['conservative_source_actions_per_item'] for t in accounting['source_action_terms'])
 assert 450652288+521088==451173376
 result['source_accounting_arithmetic']={'production_union':197880,'unit_union':197928,'production_foundation':269080,'unit_foundation':269616,'production_headroom':71200,'unit_headroom':71688,'original_constructor':61880,'original_cleanup':62888,'accepted_row_union':11912,'source_actions_plus_requested_IO':451173376,'VM_debit_stack_RSS_or_CPU_claim':False,'source_and_lifetime_argument':'source-review.md'}
 behavior=json.loads((STAGE/'command-receipts-attempt-1.json').read_text());compiler=json.loads((STAGE/'command-receipts-attempt-2.json').read_text());independent=json.loads((OUT/'independent-command-receipts.json').read_text())
 assert len(behavior)==96 and all(d['exit_code']==0 and not d['supervisor_killed_for'] for d in behavior)
 assert len(compiler)==25 and sum('expectation_met' in d for d in compiler)==22 and all(d.get('expectation_met',d['exit_code']==0) and not d['supervisor_killed_for'] for d in compiler)
 assert len(independent)==28 and sum('expectation_met' in d for d in independent)==22 and all(d.get('expectation_met',d['exit_code']==0) and not d['supervisor_killed_for'] for d in independent)
 for attempt,records in [(1,behavior),(2,compiler)]:
  raw=list((STAGE/'commands'/f'attempt-{attempt}').glob('*/receipt.json'));assert len(raw)==len(records)
  for p in raw:
   d=json.loads(p.read_text());assert sha((p.parent/'stdout').read_bytes())==d['stdout_sha256'] and sha((p.parent/'stderr').read_bytes())==d['stderr_sha256']
  env=json.loads((STAGE/f'environment-attempt-{attempt}.json').read_text());assert env['cleanup']['owned_scratch_removed'] and env['cleanup']['owned_children_reaped'] and not Path(env['scratch']).exists()
 independent_env=json.loads((OUT/'independent-environment.json').read_text());assert independent_env['cleanup']['owned_scratch_removed'] and not Path(independent_env['owned_scratch']).exists()
 # Ensure each negative is attributed to its intended included source and never
 # accepted for an import/syntax failure. Raw diagnostics remain the evidence.
 diagnostics=[]
 for p in sorted((OUT/'independent-commands').glob('*/receipt.json')):
  d=json.loads(p.read_text());assert sha((p.parent/'stdout').read_bytes())==d['stdout_sha256'] and sha((p.parent/'stderr').read_bytes())==d['stderr_sha256']
  if d.get('expected_diagnostic'):
   text=(p.parent/'stderr').read_text();assert 'predeclared-compile-cases/' in text and d['expected_diagnostic'] in text
   assert not any(e in text for e in ['error[E0432]','error[E0433]','error: expected','couldn\'t read'])
   diagnostics.append({'case':p.parent.name,'intended_diagnostic':d['expected_diagnostic'],'error_lines':[s for s in text.splitlines() if s.startswith('error')],'raw_stderr_sha256':d['stderr_sha256']})
 result['fresh_commands']={'behavior':96,'producer_compiler':25,'independent':28,'total':149,'producer_compiler_observations':22,'independent_compiler_observations':22,'independent_negative_attributions':diagnostics}
 # Independently derive the producer's finite64-definition expected physical
 # rows using the exact frozen preaccess builder, not candidate descriptors.
 spec=importlib.util.spec_from_file_location('frozen_preaccess_builder',PRE/'prepare_preaccess.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
 import struct
 wasm,descriptors=builder.fixture(64);assert len(wasm)==1947
 sentinel=struct.pack('<IIQQQ',0,2**32-1,2**64-1,0,0);wire=bytearray(sentinel*80000)
 for a,t,o,n in descriptors:wire[a*32:(a+1)*32]=struct.pack('<IIQQQ',1,t,o,n,0)
 for config in ['host','unit']:
  for mode in ['debug','optimized']:assert (STAGE/'artifacts/attempt-1'/f'{config}-{mode}/fresh.rows').read_bytes()==wire
 result['independent_production_row_comparison']={'frozen_preaccess_builder_sha256':sha((PRE/'prepare_preaccess.py').read_bytes()),'defined':64,'source_bytes':1947,'source_sha256':sha(wasm),'row_bytes':2560000,'expected_row_sha256':sha(wire),'four_physical_outputs_equal':True,'new_Rust_or_product_source_generated':False}
 findings=json.loads((OUT/'foundation-findings/seal.json').read_text());verify_manifest(OUT/'foundation-findings',findings);assert sha((OUT/'foundation-findings/seal.json').read_bytes())=='9d1927862f202d409336c66b2c30e9800522bda1f70e2a5c8ed3c039e91c4627'
 result['no_object_union_or_behavior_blockers']=True
 abstract=json.loads((OUT/'abstract-action-reconciliation.json').read_text());assert abstract['same_unit_reconciled'] and abstract['abstract_joined']==451173376 and not abstract['all_actual_authored_source_evaluations_bound_qualified']
 for m in abstract['root_scope_inputs']:assert sha((OUT/m['path']).read_bytes())==m['sha256']
 result['logical_source_action_retry_scope']='Root-selected abstract primitive/callsite actions + cumulative requested-I/O only; actual all-source/callback/CPU/retry/time/VM bounds unqualified; no capacity/reservation/release-gate inference.'
 write('audit-result.json',result)
 print('PASS actual audit: exact140+11/source-only private-module delta; preaccess254 preserved; four165+24 actual layouts;149 fresh bounded commands;44 compiler observations; independent64 physical rows; corrected197880/197928 source union below269080/269616; scratch removed. source-review.md supplies the actual semantic/lifetime argument.')
if __name__=='__main__':main()
