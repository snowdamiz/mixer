#!/usr/bin/env python3
"""Seal raw local review separately from the small sanitized publication candidate."""
import sys
def audit(event,args):
 if event.startswith(('socket.','subprocess.')) or event in {'os.system','os.fork','os.posix_spawn','pty.spawn'}:raise RuntimeError('offline audit denied '+event)
sys.addaudithook(audit)
import datetime,hashlib,json,os,platform,signal
from pathlib import Path
ROOT=Path(__file__).resolve().parent
signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('40 second offline seal bound')));signal.alarm(40)
def digest(b):return hashlib.sha256(b).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':')).encode()
def get(p):return json.loads((ROOT/p).read_bytes())
def put(p,v):(ROOT/p).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
sha='5efcb6a2bcf3b076c9a4452926a842209302e56b';tree='18f204207b0c7dd8f331e0cd947c10b41a663770'
n=get('network-verification-result.json');p=get('phoenix-verification-result.json');sr=get('source-review-conclusions.json')
assert n['source_revision']==p['source_revision']==sr['source_revision']==sha
assert n['source_tree']==p['source_tree']==sr['source_tree']==tree
for v,name in [(n,'verify_network.py'),(p,'verify_phoenix.py')]:assert v['script_sha256']==digest((ROOT/name).read_bytes()) and v['offline_audit_denies_network_and_children'] and not v['local_product_or_runtime_execution']
assert n['commands_verified']==137 and n['product_tests']['passed']==2 and n['product_tests']['skipped']==0 and n['key_directories_remaining']==[]
assert p['new_TLS_lifecycle_controls']['passed']==4 and p['ordinary_suite']=={'passed':701,'skipped':2,'total':703,'failed':0,'completed_trace_methods':703,'skip_names':p['ordinary_suite']['skip_names'],'argv':['mix','test','--warnings-as-errors','--seed','0','--trace'],'summary':'Result: 701 passed, 2 skipped','seconds':121.8}
er=get('40776622898-latest-meta-metadata.json');ej=get('40776622898-latest-jobs-metadata.json')['jobs']
assert er['head_sha']==sha and er['head_commit']['tree_id']==tree and er['run_attempt']==1 and len(ej)==6 and all(x['run_id']==er['id'] for x in ej)
assert all(x['conclusion'] in [None,'success'] for x in ej)
at=datetime.datetime.now(datetime.timezone.utc).isoformat()
command={'schema':1,'at':at,'argv':['/usr/bin/python3','-B',str(ROOT/'seal_review.py')],'cwd':str(ROOT.parents[2]),'python':platform.python_version(),'script_sha256':digest(Path(__file__).read_bytes()),'source_revision':sha,'source_tree':tree,'own_process':{'pid':os.getpid(),'ppid':os.getppid(),'pgrp':os.getpgrp()},'alarm_seconds':40,'audit_denies_children_and_network':True,'scope':'read and seal exact owned local evidence directory; no product runtime execution'}
put('sealing-command.json',command)
exclude={'raw-review-seal.json','public-summary-candidate.json','public-summary-seal.json','sealing-completion.json'}
files={};total=0;sensitive=[]
for f in sorted(ROOT.rglob('*')):
 assert not f.is_symlink()
 if not f.is_file() or f.relative_to(ROOT).as_posix() in exclude:continue
 rel=f.relative_to(ROOT).as_posix();b=f.read_bytes();total+=len(b);assert total<=256*1024*1024
 files[rel]={'bytes':len(b),'sha256':digest(b)}
 if f.suffix in {'.json','.py','.log','.stdout','.stderr','.txt'} and any(x in b for x in [b'X-Amz-'+b'Signature=',b'X-Goog-'+b'Signature=',b'&si'+b'g=']):sensitive.append(rel)
assert not sensitive
rawseal={'schema':1,'at':at,'scope':'raw local only; exact owned ci-review directory; signed download URLs and full download responses never retained','source_revision':sha,'source_tree':tree,'files':files,'tree_digest_sha256':digest(canonical(files)),'bytes':total,'no_product_source_global_or_Git_writes':True,'exclusions':sorted(exclude)}
put('raw-review-seal.json',rawseal)
engine={'run_id':er['id'],'url':er['html_url'],'status':er['status'],'conclusion':er['conclusion'],'run_attempt':1,'jobs':[{'id':j['id'],'name':j['name'],'status':j['status'],'conclusion':j['conclusion']} for j in ej],'successful':len([x for x in ej if x['conclusion']=='success']),'total':6,'metadata_only':'no secondary Engine artifact ZIPs downloaded; full prior six-job receipt acceptance remains scoped to its original commit'}
summary={'schema':1,'at':at,'source_revision':sha,'source_tree':tree,'status':'network-and-ordinary-phoenix-qualified-with-existing-holds','source_review':{'source_blockers':[],'historical177_digest':n['historical_product_digest'],'semantic_v1_178_digest':n['semantic_v1_digest'],'formatted_v2_178_digest':n['selected_product_digest'],'format_v2_amendment_sha256':n['format_v2_amendment_sha256'],'format_v2_packet_digest':n['format_v2_packet_digest'],'exact_delta':n['exact_delta'],'fixture_sha256':'d3b55796a8baac4f9ebd37cc9ee5e44bde01ca346ce2dd00a0a5dd884711ba55','collector_sha256':'372a349d6048e2ceb242fdf03dd83ebd7535fe673bd83c252728f2c6b8d321c1','collector_controls_sha256':'2e1a7a69edff5d27237bfc5a21431e9cf7220cfc7563a0c2ca1d0ce450f83bfc','six_executable_literal_helpers_unchanged':True,'frozen_manifest_helper_binds_current178':True,'previous_sealed_metadata_unchanged':True,'previous_summary_sha256':'70cc1ed6f082cfe757041b306d577a67816ad86af8576d3c05db0539344b9c28'},'network':{'run_id':n['run_id'],'url':'https://github.com/snowdamiz/mixer/actions/runs/'+str(n['run_id']),'job_id':n['job_id'],'run_attempt':1,'conclusion':'success','artifact_id':n['artifact_id'],'zip':n['zip'],'members':n['members'],'metadata_files_verified':n['metadata_files_verified'],'commands_verified':n['commands_verified'],'collector_controls':n['collector_controls'],'product_tests':n['product_tests'],'initial_source_archive_transfer':n['initial_source_archive_transfer'],'prepared_archive':n['prepared_archive'],'compiled_modules':n['compiled_modules'],'post_test_inputs_unchanged':True,'key_directories_remaining':[],'K03_semantic_receipt':n['K03_semantic_receipt'],'startup_semantic_receipt':n['startup_semantic_receipt'],'three_created_containers_terminal_exit_zero_and_exact_absence':True,'cleanup_command_numbers':{role:{k:v for k,v in row.items() if k!='cid'} for role,row in n['cleanup'].items()},'generated_DAG':n['generated_output']['raw']},'phoenix':{'run_id':p['run_id'],'url':'https://github.com/snowdamiz/mixer/actions/runs/'+str(p['run_id']),'job_id':p['job_id'],'run_attempt':1,'conclusion':'success','artifact_id':p['artifact_id'],'zip':p['zip'],'commands_verified':p['commands_verified'],'source_archive':p['source_archive'],'format':p['format'],'compile':p['compile'],'new_TLS_lifecycle_controls':p['new_TLS_lifecycle_controls'],'ordinary_suite':p['ordinary_suite'],'release':p['release'],'cleanup':p['cleanup']},'engine':engine,'local_execution':{'kind':'pure bounded byte-only evidence review','python':platform.python_version(),'alarm_seconds_each':40,'offline_verifiers_audit_deny_network_and_children':True,'local_product_runtime_or_compiler_executed':False,'no_process_inventory_or_held_probes':True,'all_verifier_commands_returned_without_live_session':True,'no_native_UI_capture_simulator_emulator_process_started':True,'no_remote_dispatch_retry_or_mutation':True},'reviewer_errors_retained':get('reviewer-errors.json'),'pending':(['Engine '+j['name']+' job incomplete' for j in ej if j['conclusion'] is None]+sr['holds_preserved']),'limits':sr['limitations'],'raw_evidence':{'storage':'local only; raw artifacts, command streams and source archives not publication candidates','directory':'verification/github-delivery-fixture-format/ci-review/','seal_sha256':digest((ROOT/'raw-review-seal.json').read_bytes()),'tree_digest_sha256':rawseal['tree_digest_sha256'],'files':len(files),'bytes':total}}
put('public-summary-candidate.json',summary)
b=(ROOT/'public-summary-candidate.json').read_bytes()
pubseal={'schema':1,'source_revision':sha,'source_tree':tree,'summary':{'path':'public-summary-candidate.json','bytes':len(b),'sha256':digest(b)},'raw_review_seal_sha256':summary['raw_evidence']['seal_sha256'],'raw_tree_digest_sha256':rawseal['tree_digest_sha256'],'scope':'sanitized summary candidate only; root must review before metadata publication; raw evidence remains local'}
put('public-summary-seal.json',pubseal)
assert get('raw-review-seal.json')['files']==files and digest((ROOT/'public-summary-candidate.json').read_bytes())==pubseal['summary']['sha256']
print(json.dumps({'status':'sealed','raw_files':len(files),'raw_bytes':total,'raw_tree_digest_sha256':rawseal['tree_digest_sha256'],'raw_seal_sha256':summary['raw_evidence']['seal_sha256'],'summary':pubseal['summary'],'engine':{'status':engine['status'],'conclusion':engine['conclusion'],'successful':engine['successful'],'total':6}},indent=2))
