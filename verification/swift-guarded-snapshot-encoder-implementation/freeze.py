#!/usr/bin/env python3
"""Verify custody, close owned scratch and seal this exact component packet."""
from pathlib import Path
import datetime,difflib,hashlib,json,shutil,sys
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT/'host'))
import runner
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def input_custody():
 paths={
 'verification/swift-semantic-adapter-root-review/guarded-snapshot-export-contract-host-acceptance.json':'02f8feb30c9a4ab84c31cfcb2c2b1bdcb4518b55d75770426d587f31b4e241cc',
 'verification/swift-semantic-adapter-root-review/guarded-snapshot-encoder-component-selection.json':'c1dda5391c60f3b3bb145eefa27dcf934918cdfc53df6273eaebead807e0d5ff',
 }
 paths['verification/swift-guarded-snapshot-export-contract-correction/seal.json']='e1e5fd13eb421131e8b610ec2cdca7a494cc9f6d3554a48764d37984a9082667'
 paths['verification/swift-guarded-snapshot-export-contract-correction-independent/seal.json']='8d1da9664d6d6f5359f4007603f2b8248b298102ffe8b5a3f430311f658f29fe'
 paths['verification/swift-guarded-snapshot-encoder-implementation/interface-proposal.md']='0d7013f15f3abe0186ccbb2d94d61e3d3cb2a635f9797338d82bdd64b4f92f10'
 result=[]
 for rel,expected in paths.items():
  p=runner.REPO/rel;assert sha(p)==expected,(rel,sha(p));result.append(runner.description(p))
  if p.name=='seal.json':
   seal=json.loads(p.read_text())
   for m in seal['members']:
    member=p.parent/m['path'];assert member.stat().st_size==m['bytes']and sha(member)==m['sha256'],str(member)
 return result
def main():
 assert not(OUT/'seal.json').exists(),'already frozen'
 custody=input_custody();closure=runner.closure();baseline=closure['baseline'];source=closure['source'];support=closure['support']
 compiled={n:json.loads((OUT/'compiled'/f'{n}.json').read_text())for n in ['unit-debug','unit-optimized','host-debug','host-optimized']}
 for j in compiled.values():assert j['context']['source']==source and j['context']['support']==support
 layouts={n:json.loads((OUT/'layouts'/f'{n}.json').read_text())['rows']for n in compiled}
 assert all(v==layouts['unit-debug']for v in layouts.values())and len(layouts['unit-debug'])==52
 supplement=json.loads((OUT/'layout-supplement.json').read_text());assert supplement['source']==source and len(supplement['assertions'])==27
 old={m['path']:m for m in baseline['members']};new={m['path']:m for m in source['members']};assert set(old)==set(new)
 delta=[];patch=[]
 for path in old:
  if old[path]==new[path]:continue
  before=(runner.BASE/path).read_text();after=(runner.SOURCE/path).read_text()
  delta.append({'path':path,'before':old[path],'after':new[path]});patch.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='accepted/'+path,tofile='component/'+path))
 assert len(delta)==10
 initial='src/experimental_swift_reactor/cache/initial_profile_v1.rs'
 before=(runner.BASE/initial).read_text();after=(runner.SOURCE/initial).read_text()
 hook='\n    #[cfg(any(test,mixer_snapshot_encoder_host))]\n    snapshot_encoder_host::observe_v2(&initial);'
 def section(s,start,end):return s[s.index(start):s.index(end,s.index(start))]
 assert section(before,'enum InitialProfileConstructionOutcomeV1','#[repr(C)]\nstruct LocalTypeLayoutV1')==section(after,'enum InitialProfileConstructionOutcomeV1','#[repr(C)]\nstruct LocalTypeLayoutV1')
 assert section(before,'fn construct_with_initial_profile_v1(','fn write_initial_profile_rows_v1(')==section(after,'fn construct_with_initial_profile_v1(','fn write_initial_profile_rows_v1(').replace(hook,'')
 assert before.count('let initial=InitialProfileBorrowV1 { cache,control,wasi,scalars };')==after.count('let initial=InitialProfileBorrowV1 { cache,control,wasi,scalars };')==1
 for rel in ['src/experimental_swift_reactor/cache/initial_profile_v1/header.rs','src/experimental_swift_reactor/diagnostic_profile.rs']:
  assert old[rel]==new[rel]
 comparisons=[]
 for p in sorted((OUT/'runs').glob('*/oracle-comparison.json')):
  j=json.loads(p.read_text());assert j['all_bytes_equal'];comparisons.append({'path':str(p.relative_to(OUT)),**j})
 assert len(comparisons)==12
 privacy=[json.loads((OUT/'privacy'/f'{mode}.json').read_text())for mode in ['debug','optimized']]
 assert all(len(v)==16 and all(x['expectation_met']for x in v)for v in privacy)
 commands=[json.loads(p.read_text())for p in sorted((OUT/'commands').glob('*/receipt.json'))]
 assert all(c['child_reaped']for c in commands)
 runner.save(OUT/'final-source-manifest.json',source);runner.save(OUT/'final-support-manifest.json',support)
 runner.save(OUT/'source-delta.json',{'schema':1,'members':delta,'original_constructor_minus_selected_cfg_hook_identical':True,'original_outcome_enum_identical':True,'sole_guard_literal_count':1,'original_header_rows_files_identical':True})
 (OUT/'source-delta.patch').write_text(''.join(patch))
 runner.save(OUT/'input-custody-after.json',{'baseline':baseline,'released_inputs':custody,'frozen_sources_unchanged':True})
 # Every Popen child has returned and was waited. Delete only this packet's own
 # known compiler/scratch tree; no process inventory or foreign cleanup occurs.
 scratch=runner.manifest(runner.WORK);shutil.rmtree(runner.WORK)
 assert not runner.WORK.exists()
 assert not list(OUT.rglob('__pycache__'))and not list(OUT.rglob('*.pyc'))
 report={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'pure-encoder-component-frozen-independent-review-pending',
 'source_tree_sha256':source['tree_sha256'],'source_members':144,'host_support_members':11,'host_support_tree_sha256':support['tree_sha256'],
 'new_source_files':0,'changed_source_files':10,'selected_guard_byte_comparisons':comparisons,'missing_selected_refusals':4,
 'continuous_blocks_per_positive':3,'allocation_calls_per_encoder_operation':0,'layout_identities':52,'helper_layout_assertions':27,
 'layout_configurations':list(layouts),'internal_privacy_positive':2,'internal_privacy_negative':30,'external_privacy_negative':6,
 'ordinary_production_default_metadata_and_library_builds':4,'ordinary_production_symbol_checks':2,'unit_enum_option_and_span_checks':4,
 'command_count':len(commands),'historical_command_failures':[c['label']for c in commands if not c['expectation_met']],
 'runner_failures_retained':len(list((OUT/'runner-failures').glob('*'))),'scratch_removed':scratch,'owned_children_reaped':True,
 'cleanup':'Owned compiler products/scratch removed; no native/UI/capture/process inventory or foreign process cleanup; historical source/receipts preserved',
 'per_call_bounds':{'init':'fixed nine inventories,34 enum words and fixed field/limit loops only','next_block_bytes':4096,'progress_iterations_max':515,'metadata_record_visits_max':513,'directory_probes_per_iteration_max':9},
 'limits':['No actual writer or File custody','No work/storage/stop admission or selected owning scope','No new simultaneous floor or operational budget acceptance','Original cleanup observations cover original owners only','No all-eight operational export behavior','No canonical/full workload/native/device/OTA/signing/store/customer/FieldLog/GA acceptance'],'native_or_GA_accepted':False}
 runner.save(OUT/'result.json',report)
 # Hash every retained member including this freeze program and report; the seal
 # excludes only itself and is immutable after this point.
 members=[{'path':str(p.relative_to(OUT)),'bytes':p.stat().st_size,'sha256':sha(p)}for p in sorted(OUT.rglob('*'))if p.is_file()and p.name!='seal.json']
 seal={'schema':1,'scope':'pure guarded logical snapshot encoder component; independent review and operational composition pending','member_count':len(members),'bytes':sum(m['bytes']for m in members),'members':members,'tree_sha256':hashlib.sha256(json.dumps(members,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
 runner.save(OUT/'seal.json',seal)
 print(json.dumps({'seal_sha256':sha(OUT/'seal.json'),'member_count':seal['member_count'],'bytes':seal['bytes'],'source_tree_sha256':source['tree_sha256'],'status':report['status']}))
if __name__=='__main__':main()
