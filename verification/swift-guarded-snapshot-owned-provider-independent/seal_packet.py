#!/usr/bin/env python3
"""Read-only evidence recheck followed by one immutable owned review seal."""
from pathlib import Path
import datetime,gzip,hashlib,json,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def sha(d):return hashlib.sha256(d).hexdigest()
def canonical(o):return json.dumps(o,sort_keys=True,separators=(',',':')).encode()
def write(p,o):p.write_text(json.dumps(o,indent=2,sort_keys=True)+'\n')
def row(p):
 d=p.read_bytes();return {'path':p.relative_to(HERE).as_posix(),'bytes':len(d),'sha256':sha(d)}
def main():
 assert not (HERE/'seal.json').exists(),'packet already frozen'
 from review_host import frozen
 frozen(ROOT/'verification/swift-guarded-snapshot-owned-binding-provider','7af047d181125c0e3da36f2d4585d4a31204bedf8f367793300022391aca02de',50)
 frozen(ROOT/'verification/swift-guarded-snapshot-scoped-binding-source','84a9bf52a127f5fcebd5d6db3dedb9c0e65fc9ef9cfd57b432c8e1f65f8e5ed2',200)
 compiler=json.loads((HERE/'commands/compiler-metadata-mir/receipt.json').read_bytes())
 assert compiler['success'] and compiler['compiler_invocations']==1 and compiler['retries']==0
 assert compiler['owned_group_absent'] and compiler['owned_scratch_removed'] and compiler['child_reaped']
 assert not (HERE/'owned-work/compiler-metadata-mir').exists()
 artifact=next(r for r in compiler['artifacts'] if r['path']=='query.mir')
 data=(HERE/'commands/compiler-metadata-mir/query.mir.gz').read_bytes();assert sha(data)==artifact['retained_gzip_sha256'] and sha(gzip.decompress(data))==artifact['sha256']
 h=json.loads((HERE/'host-replay-receipt.json').read_bytes());i=json.loads((HERE/'independent-receipt.json').read_bytes());m=json.loads((HERE/'mir-comparison.json').read_bytes())
 assert h['tests_run']==18 and h['exit_code']==0 and h['frozen_inputs_unchanged']
 assert i['tests_run']==14 and i['success'] and not i['failures'] and not i['errors'] and not i['skipped']
 assert m['equal'] and m['before_blocks']==m['after_blocks']==6006 and not m['differences']
 assert m['baseline_partition']['complete_partition'] and m['candidate_partition']['complete_partition']
 assert json.loads((HERE/'mir-adverse-controls.json').read_bytes())['all_detected']
 for receipt,name in [(h,'host'),(i,'independent')]:assert sha((HERE/(name+'.stdout')).read_bytes())==receipt['stdout_sha256']
 assert sha((HERE/'review_host.py').read_bytes())==h['runner_sha256']
 assert sha((HERE/'run_independent.py').read_bytes())==i['runner_sha256']
 assert sha((HERE/'test_independent.py').read_bytes())==i['test_sha256']
 assert sha((HERE/'compile_once.py').read_bytes())==compiler['runner_sha256']
 mr=json.loads((HERE/'mir-review-receipt.json').read_bytes());assert sha((HERE/'review_mir.py').read_bytes())==mr['runner_sha256']
 for name in ('input-custody.json','query-source-custody.json'):
  custody=json.loads((HERE/name).read_bytes());rows=custody['candidate_source_custody'] if name=='input-custody.json' else custody['members']
  for r in rows:
   d=(ROOT/r['origin']).read_bytes();assert (len(d),sha(d))==(r['bytes'],r['sha256'])
 assert not list(HERE.rglob('__pycache__'))
 write(HERE/'final-validation.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':[sys.executable,*sys.argv],'python_version':sys.version,'source_revision_at_compile':compiler['source_revision'],'candidate_source_tree_sha256':compiler['candidate_tree_sha256'],'query_source_tree_sha256':compiler['query_tree_sha256'],'provider50_and_base200_members_rehashed':True,'candidate146_and_query146_custody_origins_rehashed':True,'host18_independent14_pass':True,'compiler_once_full_MIR_hashes_match':True,'old6006_MIR_blocks_equal':True,'scratch_absent':True,'no_bytecode_files':True,'scope':'offline custody and retained evidence consistency; no new test/compiler/native/runtime invocation','operational_grant':False,'root_acceptance':False,'GA':False})
 members=[row(p) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name!='seal.json']
 seal={'schema':1,'status':'frozen-independent-conditional-source-protocol-production-metadata-review','member_count':len(members),'member_bytes':sum(r['bytes'] for r in members),'members':members,'tree_sha256':sha(canonical(members)),'provider_seal_sha256':'7af047d181125c0e3da36f2d4585d4a31204bedf8f367793300022391aca02de','conditional_base_source146_tree':'69068367d2eaf334d6881a624cac9142a0b4ecfeed50f23382724ae29e51d5e7','candidate_source146_tree':compiler['candidate_tree_sha256'],'blocking_findings':0,'producer_host_methods':18,'independent_host_methods':14,'compiler_invocations':1,'compiler_retries':0,'old_MIR_blocks_equal':6006,'old_function_bodies_equal':2020,'singleline_constants_compared':1785,'layout_observations':20,'independent_offline_harness_failures_preserved':2,'actual_provider_or_loader_execution':False,'authenticated_owner_or_acquisition':False,'provider_pricing_complete':False,'all_three_selectors':'Pending','upstream_acquisition_funding':'Pending','conditional_base_independent_root_acceptance':False,'root_acceptance':False,'operational_grant':False,'native_runtime_FieldLog_OTA_GA':False,'cleanup_complete':True}
 write(HERE/'seal.json',seal)
 print(json.dumps({'seal_sha256':sha((HERE/'seal.json').read_bytes()),'members':len(members),'bytes':seal['member_bytes'],'tree_sha256':seal['tree_sha256'],'blocking_findings':0}))
if __name__=='__main__':main()
