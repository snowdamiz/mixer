#!/usr/bin/env python3
"""Independent frozen source/MIR/receipt review; no candidate driver execution."""
import difflib
import hashlib
import json
import platform
import re
import sys
from datetime import datetime,timezone
from pathlib import Path

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
PACK=ROOT/'verification/swift-guarded-snapshot-funding-implementation'
AUTH=ROOT/'verification/swift-guarded-snapshot-scope-authority-correction'
CONTROL='src/experimental_swift_reactor/control.rs'
INITIAL='src/experimental_swift_reactor/cache/initial_profile_v1.rs'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':')).encode()
def js(p):return json.loads(p.read_text())
def write(name,v):(OUT/name).write_text(json.dumps(v,indent=2)+'\n')
checks=[]
def check(label,condition):
 assert condition,label
 checks.append({'name':label,'passed':True})
def section(s,start,end):
 first=s.index(start);return s[first:s.index(end,first)]
def function(s,name):
 start=re.search(r'\bfn (?:[\w]+::)*'+re.escape(name)+r'(?:<[^\n]*?>)?\s*\(',s)
 assert start,name
 brace=s.index('{',start.start());level=1;end=brace+1
 while level:
  if s[end]=='{':level+=1
  elif s[end]=='}':level-=1
  end+=1
 return s[start.start():end]

release=ROOT/'verification/swift-semantic-adapter-root-review/guarded-snapshot-funding-independent-release.json'
check('root frozen release identity',sha(release)=='d0f3b7ec8acd799c9a4a053b308b46a5d9ed45ff04a8cc9215a8b4aaa062fd2f')
check('candidate seal identity',sha(PACK/'seal.json')=='e006b90b8c9e351e0d4dd504c6de309e2c7970b628fe9fc4f788cb30e77bedf7')
seal=js(PACK/'seal.json')
for row in seal['members']:
 p=PACK/row['path'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],row['path']
check('all225 frozen candidate members',len(seal['members'])==225 and sum(r['bytes'] for r in seal['members'])==20037475)
check('candidate seal tree digest',hashlib.sha256(canonical(seal['members'])).hexdigest()==seal['tree_sha256'])
pre=js(OUT/'preaccess-seal.json')
for row in pre['members']:
 p=OUT/row['path'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],row['path']
check('preaccess expectation members still exact',len(pre['members'])==4)

base_manifest=js(AUTH/'source-manifest.json')
manifest=js(PACK/'source-manifest.json')
for root,m in [(AUTH/'source/vm',base_manifest),(PACK/'source/vm',manifest)]:
 for row in m['members']:
  p=root/row['path'];assert sha(p)==row['sha256'] and p.stat().st_size==row['bytes'],row['path']
 assert hashlib.sha256(canonical(m['members'])).hexdigest()==m['source_tree_sha256']
check('source144 exact target tree',len(manifest['members'])==144 and manifest['source_tree_sha256']=='7e3e861ca65d8c6359623443d6a7810b878c1029494a0ae557307d35ed43484b')
changed=[r['path'] for r in base_manifest['members'] if (AUTH/'source/vm'/r['path']).read_bytes()!=(PACK/'source/vm'/r['path']).read_bytes()]
check('actual exactly two source files differ',changed==[INITIAL,CONTROL])
patch=''.join(x for name in changed for x in difflib.unified_diff((AUTH/'source/vm'/name).read_text().splitlines(True),(PACK/'source/vm'/name).read_text().splitlines(True),fromfile='authority144/'+name,tofile='funding144/'+name))
check('actual diff equals retained patch',patch==(PACK/'source-delta.patch').read_text())
before=(AUTH/'source/vm'/CONTROL).read_text();after=(PACK/'source/vm'/CONTROL).read_text()
old_i=(AUTH/'source/vm'/INITIAL).read_text();new_i=(PACK/'source/vm'/INITIAL).read_text()
f0=section(before,'const FOUNDATION_CONSTRUCTION_BYTES:','\n/// Conservative named-object foundation envelope.')
check('same sole13-term F0 initializer',f0 in after and '[(usize, usize); 13]' in f0)
check('no original baseline discount',after.count('const FOUNDATION_CONSTRUCTION_BYTES:')==1 and f0==section(after,'const FOUNDATION_CONSTRUCTION_BYTES:','\n// Exact logical source-place recipe'))
const_fragment=(PACK/'funding-constants.inc.rs').read_text()
check('full const fragment installed once',after.count(const_fragment)==1)
for name,expected in [('COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1',78240),('SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1',941467),('SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1',430175),('SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1',81327)]:
 actual=int(re.search(r'const '+name+r': usize = ([\d_]+);',const_fragment).group(1).replace('_',''))
 check('exact accepted constant '+name,actual==expected)
check('runtime common wrapper exact const copy',function(after,'foundation_construction_bytes').split('{',1)[1].strip()=='COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1\n}')
selected=function(after,'snapshot_scope_candidate_foundation_v1')
check('runtime selected wrapper exact const copy',re.sub(r'//[^\n]*','',selected.split('{',1)[1]).strip()=='SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1\n}')
check('phase replacement exact once',new_i==old_i.replace("const SNAPSHOT_PHASE_PLACES_V1:usize=size_of::<SnapshotPhasePlacesV1<'static>>();",'const SNAPSHOT_PHASE_PLACES_V1:usize=super::super::control::SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1;'))
check('no added runtime function definitions',len(re.findall(r'\bfn\s+',after))==len(re.findall(r'\bfn\s+',before)))
# All control changes outside the new const/docs and two existing wrapper bodies
# must invert exactly to authority. This checks whole files, beyond snippets.
own_new_common=section(after,'// Exact logical source-place recipe','\nimpl RuntimeControl {')
own_old_common=section(before,'/// Conservative named-object foundation envelope.','\nimpl RuntimeControl {')
reverted=after.replace(own_new_common,own_old_common)
reverted=reverted.replace(function(reverted,'snapshot_scope_candidate_foundation_v1'),function(before,'snapshot_scope_candidate_foundation_v1'))
check('entire control source inverse is exact authority',reverted==before)
for name in ['snapshot_storage_preflight_v1','snapshot_commit_storage_v1','end_construction_phase_with_wasi','finish_owned_cleanup','adopt_snapshot_body_v1']:
 check('unchanged exact control function '+name,function(after,name)==function(before,name))
for name in ['begin_snapshot_access_v1','proposed_emission_work_v1','write_snapshot_v1']:
 check('unchanged exact initial function '+name,function(new_i,name)==function(old_i,name))
check('unchanged actual SnapshotAccess completion',section(new_i,"impl SnapshotAccessV1<'_>",'\nstruct SnapshotShapeV1')==section(old_i,"impl SnapshotAccessV1<'_>",'\nstruct SnapshotShapeV1'))
begin=function(new_i,'begin_snapshot_access_v1')
order=['cache.snapshot_pair_v1(control,wasi)?','control.snapshot_storage_preflight_v1(additional)?','control.snapshot_debit_v1(planning)?','snapshot_shape_v1(cache.proof().snapshot_counts_v1())?','proposed_emission_work_v1(&shape)?','control.snapshot_debit_v1(emission)?','control.snapshot_commit_storage_v1(additional)?','transfer:Some([0;4096])']
check('unchanged pair/preflight/work/commit/transfer ordering',[begin.index(x) for x in order]==sorted(begin.index(x) for x in order))
check('writer still unreachable via WorkAuditPending','Err(AError::WorkAuditPending)' in function(new_i,'proposed_emission_work_v1'))

compiler_contexts=[]
for mode in ['production','unit']:
 cmd=PACK/'commands'/('metadata-'+mode)
 receipt=js(cmd/'receipt.json');preimage=js(cmd/'source-preimage.json')
 check('successful exact metadata/MIR receipt '+mode,receipt['exit_code']==0 and receipt['expectation_met'] and receipt['child_reaped'] and receipt['owned_group_absent'] and not receipt['timed_out'])
 check('exact source144 compiler preimage '+mode,preimage['source_members']==manifest['members'])
 for stream in ['stdout','stderr']:check('compiler '+stream+' digest '+mode,sha(cmd/stream)==receipt[stream+'_sha256'])
 check('target Rust1.99 compiler '+mode,'aarch64-apple-darwin' in receipt['argv'] and receipt['compiler_sha256']=='dd6f58440b3418aa9157ae3f05d71eecff741ca41bc4eec120e7e8f2d933b9a0' and receipt['compiler_version'].startswith('rustc 1.99.0'))
 mir=(cmd/'funding-functions.mir').read_text();floor_bodies={}
 for name,const in [('foundation_construction_bytes','COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1'),('snapshot_scope_candidate_foundation_v1','SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1')]:
  body=function(mir,name)
  declarations=re.findall(r'^\s*let (?:mut )?(_\d+): ([^;]+);',body,re.M)
  check('raw MIR only existing Option return '+mode+' '+name,declarations==[('_0','std::option::Option<usize>')])
  check('raw MIR const copy without call '+mode+' '+name,('::'+const+';') in body and ' -> [return:' not in body and 'checked_add' not in body and 'StorageLive' not in body)
  floor_bodies[name]={'declared_places':declarations,'body_sha256':hashlib.sha256(body.encode()).hexdigest()}
 check('raw MIR preserved WorkAuditPending '+mode,'SnapshotAdmissionErrorV1::WorkAuditPending' in function(mir,'proposed_emission_work_v1'))
 compiler_contexts.append({'mode':mode,'compiler':receipt['compiler_version'],'argv':receipt['argv'],'source_tree_sha256':manifest['source_tree_sha256'],'floor_bodies':floor_bodies})

scalar_counts={}
for mode in ['production','unit','overflow']:
 cmd=PACK/'commands'/('scalar-'+mode);r=js(cmd/'receipt.json');run=js(cmd/'scalar-receipt.json');src=(cmd/'standalone-source.rs').read_text()
 check('scalar compile/run success '+mode,r['exit_code']==0 and run['exit_code']==0 and run['child_reaped'] and run['owned_group_absent'] and not run['timed_out'])
 check('scalar source/executable evidence '+mode,sha(cmd/'standalone-source.rs')==run['source_sha256'] and sha(cmd/'scalar-stdout')==run['stdout_sha256'] and sha(cmd/'scalar-stderr')==run['stderr_sha256'])
 check('scalar recipe exact same const fragment '+mode,const_fragment in src)
 check('scalar174 result '+mode,(cmd/'scalar-stdout').read_text()=='PASS 174 scalar phase/overflow/refusal controls; no VM/writer\n')
 scalar_counts[mode]=174
# Recount and recompute the scalar cases with independent unbounded arithmetic.
count=2
for bits in [32,64]:
 limit=(1<<bits)-1
 for f0 in [0,1,300000,400000,366896,limit-78240,limit-78239,limit]:
  for host in [False,True]:
   requested=f0+78240+941467+(81327 if host else 0)
   count+=1
   if requested<=limit:
    for grant in [0,300000,400000,requested,requested+430174,requested+430175,limit]:
     committed=requested+430175 if requested+430175<=min(limit,grant) else requested
     assert committed in [requested,requested+430175]
     count+=1
check('independent scalar174 recomputation',count==174)
negative=PACK/'commands/scalar-overflow-negative';neg=js(negative/'receipt.json')
check('actual expected E0080 output',neg['exit_code']!=0 and neg['expectation_met'] and 'error[E0080]' in (negative/'stderr').read_text() and sha(negative/'stderr')==neg['stderr_sha256'])
ordering=js(PACK/'ordering-controls.json')
check('all34 retained source controls passed',ordering['passed']==34 and len(ordering['controls'])==34 and all(x['passed'] for x in ordering['controls']))
funding=js(ROOT/'verification/swift-guarded-snapshot-owner-storage-alias-correction/funding.json')
old_roles=[r for r in funding['roles'] if r['id'].startswith('owner::snapshot_scope_candidate_foundation_v1::')]
check('old200B conservative selected formula roles retained',sum(sum(r['funding'].values()) for r in old_roles)==200)
actual=js(OUT/'actual-constants.json')
for mode in ['production','unit']:
 receipt=js(OUT/f'compiler-{mode}/receipt.json')
 check('fresh independent actual const diagnostic '+mode,receipt['expected_E0308_count']==3 and receipt['child_reaped'] and receipt['owned_group_absent'] and not receipt['timed_out'])
 check('fresh independent source target '+mode,receipt['source_tree_sha256']==manifest['source_tree_sha256'] and receipt['compiler_sha256']=='dd6f58440b3418aa9157ae3f05d71eecff741ca41bc4eec120e7e8f2d933b9a0')
check('actual production floor values',actual['contexts']['production']=={'F0':366312,'common':444552,'selected_without_H':1386019,'selected':1386019,'admitted':1816194})
check('actual unit floor values',actual['contexts']['unit']=={'F0':366896,'common':445136,'selected_without_H':1386603,'selected':1467930,'admitted':1898105})
check('independent owned scratch cleaned',js(OUT/'compiler-cleanup.json')['scratch_absent'] and not (OUT/'owned-work').exists())
lifetime=js(PACK/'lifetime-obligations.json')
check('H explicit preingress/harness pending',not lifetime['H_pre_ingress']['qualification'] and not lifetime['H_pre_ingress']['external_harness_costs_reserved'] and not lifetime['H_pre_ingress']['production_H_included'])
check('A explicit unreachable and pending',not lifetime['A_narrowing']['admission_reachable'] and 'required independent' in lifetime['A_narrowing']['status'])
check('candidate retains previous at commit',function(after,'snapshot_commit_storage_v1').rstrip().endswith('Ok(previous)\n    }'))
check('candidate still forwards previous to drop/narrow helper','Self::Admitted{control,previous,wasi}=>control.end_construction_phase_with_wasi(storage,previous,wasi)' in new_i)
check('retention alternative is proposal only',not js(PACK/'lifetime-retention-follow-up.json')['current_source_changed_by_this_proposal'])
write('controls.json',{'schema':1,'checks':checks,'passed':len(checks),'pure_preaccess_arithmetic_assertions':123,'candidate_scalar_cases_per_context':scalar_counts,'independent_scalar_recount':count})
write('compiler-receipt-audit.json',{'schema':1,'contexts':compiler_contexts,'new_independent_compile_only_commands':2,'new_product_runtime_executions':0,'actual_constants':actual,'scalar_scope':'synthetic scalar arithmetic; production synthetic F0 is not actual production F0'})
write('review.json',{'schema':1,'at':datetime.now(timezone.utc).isoformat(),'status':'accepted-bounded-constants-only-source-integration-evidence-with-explicit-open-lifetime-obligations','command':[sys.executable,str(Path(__file__).resolve())],'python_version':platform.python_version(),'candidate_seal_sha256':sha(PACK/'seal.json'),'accepted_source_tree_sha256':base_manifest['source_tree_sha256'],'candidate_source_tree_sha256':manifest['source_tree_sha256'],'source_members':144,'changed_files':changed,'controls_passed':len(checks),'preaccess_arithmetic_assertions':123,'new_independent_compile_only_commands':2,'retained_metadata_MIR_contexts':2,'producer_scalar_cases_per_mode':174,'modes':['production','cfg(test)','overflowingSyntheticF0'],'actual_context_floors':actual['contexts'],'added_runtime_places':0,'retained_old_formula_charge_bytes':200,'optional2192_credit_selected':False,'source_constants_recipe_accepted':True,'complete_floor_or_work_or_writer_release_accepted':False,'A_narrowing_lifetime_accepted':False,'H_preingress_or_external_harness_accepted':False,'conservative_finalizer_healthy_cleanup_accepted':False,'production_caller_or_descriptor_accepted':False,'runtime_executions':0,'native_or_capture_or_process_inventory_executions':0,'canonical_or_git_or_root_metadata_mutations':False,'Linux_or_other_targets_qualified':False,'GA_gates_verified':0,'limitations':['Measured logical source places only on aarch64-apple-darwin Rust1.99; no physical stack/RSS or private-library bound.','Actual production F0 differs from cfg(test); 366896 scalar F0 is synthetic and happens to equal cfg(test) only.','400000 common-floor fixture can now refuse earlier; no fixture limit changed and no product runtime fixture was executed.','WorkAuditPending blocks commit; no writer admission or execution occurred.','A refund remains unproved; retained-diagnostic receiving S slots are charged, but producer/return/move retirement and owned backing need proof before narrowing or an independently accepted retain-A amendment.','cfg(test) H admission charge does not fund already-live pre-ingress arguments or the external harness.','Proposal to return committed construction is unselected and was not applied.']})
print(json.dumps({'passed':len(checks),'source_members':144,'changed_files':2,'actual_context_floors':actual['contexts'],'complete_floor_or_writer_release':False}))
