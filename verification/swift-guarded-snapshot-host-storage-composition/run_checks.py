"""Pure source/evidence derivation and deterministic storage controls."""
from pathlib import Path
import datetime,hashlib,json,os,re,subprocess,sys,time
sys.dont_write_bytecode=True
from derive import HERE,ROOT,derive,sha,save,SOURCE,HOST
from model import evaluate
from test_storage import fixture

def generated():
 custody,inv,pending=derive()
 for name,value in [('input-custody.json',custody),('inline-inventory.json',inv),('pending-layout-roster.json',pending)]:
  assert json.loads((HERE/name).read_bytes())==value,('stale-derived-output',name)
 assert inv['required_layouts']==[] and inv['loader_known_bytes']==644008
 assert sum(r['known_bytes'] for r in inv['loader_slots'] if r['validator'])==171197
 bindings=json.loads((HERE/'generic-source-binding.json').read_bytes())
 actual=[{'id':r['id'],'function':r['function'],'function_sha256':r['function_sha256'],'local':r['local'],'type':r['type'],'binding':r['layout_proof']} for r in inv['loader_slots'] if r['layout_proof'] and r['layout_proof']['rule']=='maximum-over-closed-actual-source-instantiations']
 assert actual==bindings['generic_roles'] and len(actual)==28
 y=evaluate(inv,fixture(inv));y['example_scope']='synthetic unselected positive interface values; no real path/fixture/policy/grant'
 return custody,inv,y

def main():
 frozen=(HERE/'seal.json').exists()
 custody,inv,example=generated()
 argv=[sys.executable,'-B','-m','unittest','discover','-s',str(HERE),'-p','test_storage.py','-v']
 start=time.monotonic();at=datetime.datetime.now(datetime.timezone.utc).isoformat()
 p=subprocess.run(argv,cwd=ROOT,stdin=subprocess.DEVNULL,capture_output=True,timeout=45,start_new_session=True)
 elapsed=time.monotonic()-start
 matched=re.search(rb'Ran (\d+) tests',p.stderr);assert matched
 result={'schema':1,'source_tree_sha256':SOURCE,'host_tree_sha256':HOST,'source_members':146,'host_members':11,
 'methods':int(matched[1]),'all_passed':p.returncode==0 and b'\nOK\n' in p.stderr,
 'caller_roles':396,'caller_inline_bytes':311071,'P0_roles':208,'P0_inline_bytes':234375,'child_caller_inline_bytes':76696,
 'leaf_roles':205,'leaf_inline_bytes':320766,'loader_functions':219,'loader_roles':9403,'loader_inline_bytes':644008,
 'original_validator_functions':152,'original_validator_roles':6458,'original_validator_inline_bytes':171197,
 'all_layout_extents_closed':True,'raw_layout_records':3072,'extra_named_storage_rows':14,'anonymous_Bytes_env_bytes':8,
 'initial_cache_max_requested_backing':54976,'resource_candidate_independently_accepted':False,
 'P0_funded_before_policy_quote_or_entry_required':True,'C':79676,'S':941467,'A':430175,'H_unit':81327,'full_product_retention':1899541,
 'all_six_child_components_required':True,'native_work_bytes_used_for_storage':0,'originals_retained_through_payload_destruction':True,
 'root_policy_selected':False,'whole_host_grant':False,'actual_fixture_or_product_executed':False,'healthy_cleanup_accepted':False,'native_UI_capture_or_GA':False}
 assert result['all_passed']
 if frozen:
  assert json.loads((HERE/'results.json').read_bytes())==result
  assert json.loads((HERE/'synthetic-example.json').read_bytes())==example
 else:
  cmd=HERE/'commands/final-controls';cmd.mkdir(parents=True,exist_ok=True)
  (cmd/'stdout').write_bytes(p.stdout);(cmd/'stderr').write_bytes(p.stderr)
  preimage=[{'path':str(q.relative_to(ROOT)),'bytes':len(q.read_bytes()),'sha256':sha(q.read_bytes())} for q in sorted(HERE.glob('*.py'))]
  receipt={'schema':1,'at':at,'argv':argv,'cwd':str(ROOT),'python_version':sys.version,'python_executable':str(Path(sys.executable).resolve()),'python_executable_sha256':sha(Path(sys.executable).resolve().read_bytes()),'root_supplied_source_revision_at_child_entry_acceptance':'510c2e123b356de6fda062379e6cbaa2233e69e3','source_tree_sha256':SOURCE,'host_tree_sha256':HOST,
  'tested_own_source_preimages':preimage,'exit_code':p.returncode,'elapsed_seconds':elapsed,'timeout_seconds':45,'direct_child_waited':True,'stdout_sha256':sha(p.stdout),'stderr_sha256':sha(p.stderr),'scope':'pure Python deterministic controls; no compiler or product/native runtime','native_or_product_processes_started':False,'global_process_inventory':False}
  (cmd/'receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
  save('results.json',result);save('synthetic-example.json',example)
 print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()
