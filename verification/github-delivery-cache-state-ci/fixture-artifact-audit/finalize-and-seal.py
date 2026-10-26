"""Close data custody and freeze the independently audited fixture CI packet."""
from datetime import datetime,timezone
import hashlib,json,pathlib,sys
HERE=pathlib.Path(__file__).resolve().parent
REPO=HERE.parents[2]
assert __debug__ and not (HERE/'seal.json').exists()
SHA='db6332d4c27efec4f9e22b9adc43000d48c591a1';TREE='dc76d1caa4ad6db89b51f82172314dd6d4b89995';RUN=40373807988

def digest(data):return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def read(path):return json.loads(path.read_bytes())
def save(name,data):(HERE/name).write_text(json.dumps(data,indent=2)+'\n')

records=[];failed=[]
for path in sorted(HERE.glob('*.command.json')):
    row=read(path);stem=path.name.removesuffix('.command.json')
    assert digest((HERE/row.get('stdout_file',stem+'.stdout')).read_bytes())==row['stdout']
    assert digest((HERE/(stem+'.stderr')).read_bytes())==row['stderr']
    if row['exit_code']:
        assert stem=='fixture-job-log' and row['exit_code']==1
        assert (HERE/(stem+'.stderr')).read_text()=='the response contains terminal escape sequences; pass --allow-escape-sequences to output it anyway\n'
        failed.append({'command_record':path.name,'reason':'gh declined raw terminal escape bytes; original failure preserved','resolution':'Separately named fixture-job-log-raw collection used the supported flag and retained bytes without rendering them; no CI retry'})
    records.append(path.name)
assert len(failed)==1
run=read(HERE/'global-at-seal.stdout');jobs=read(HERE/'global-jobs-at-seal.stdout')['jobs']
assert run['head_sha']==SHA and run['run_attempt']==1 and run['status']=='in_progress' and run['conclusion'] is None
assert {j['name'] for j in jobs}=={'swift','swift-capability-native','vm','services','android-owner-host','swift-cache-state-fixture'}
fixture,=[j for j in jobs if j['name']=='swift-cache-state-fixture']
assert fixture['id']==121751312835 and fixture['head_sha']==SHA and fixture['run_attempt']==1
assert fixture['status']=='completed' and fixture['conclusion']=='success' and len(fixture['steps'])==8
assert all(s['status']=='completed' and s['conclusion']=='success' for s in fixture['steps'])
assert (HERE/'source-tree.stdout').read_text().strip()==TREE
report=read(HERE/'full-audit.json');local=read(HERE/'comparison-final-decision.json');selection=read(HERE/'source-selection.stdout')
assert report['passed'] and report['source_revision']==SHA and report['source_tree']==TREE
assert report['actual_compiler_release']=='1.98.1'
assert report['modes']==local['modes']
assert report['runner_sha256']==selection['canonical_runner_sha256']==local['runner_sha256']
old=REPO/'verification/github-delivery-host-component-editor-contract/artifact-audit'
assert digest((old/'acceptance.json').read_bytes())['sha256']=='709f437353b8ea21e0b086fc5f45871178816b35ec628b854d867bb427469a64'
assert digest((old/'seal.json').read_bytes())['sha256']=='bc99470f09aeef7dee0743f90469d8f35b36f9309623ba5631ef99e9d1e2b2fb'
old_seal=read(old/'seal.json')
for row in old_seal['members']:
    assert digest((old/row['path']).read_bytes())=={k:row[k] for k in ('bytes','sha256')}
save('prior-audit-custody.json',{'path':str(old.relative_to(REPO)),'acceptance_sha256':old_seal['acceptance_sha256'],'seal_sha256':digest((old/'seal.json').read_bytes())['sha256'],'frozen_members_reverified':len(old_seal['members']),'frozen_bytes_reverified':sum(m['bytes'] for m in old_seal['members']),'all_frozen_bytes_unchanged':True,'scope':'Read-only hash revalidation; no old one-shot script or artifact code executed'})
receipt={
    'schema':1,'at':datetime.now(timezone.utc).isoformat(),'argv':sys.argv,'python':sys.version,'builder_sha256':digest(pathlib.Path(__file__).read_bytes())['sha256'],
    'status':'accepted-exact-selected-Rust1.98.1-Actions-closed-host-fixture-only',
    'source_revision':SHA,'source_tree':TREE,'run_id':RUN,'run_url':run['html_url'],'run_attempt':1,
    'fixture_job':{'id':fixture['id'],'name':fixture['name'],'status':fixture['status'],'conclusion':fixture['conclusion'],'steps':len(fixture['steps']),'started_at':fixture['started_at'],'completed_at':fixture['completed_at'],'url':fixture['html_url']},
    'global_CI':{'status':run['status'],'conclusion':run['conclusion'],'captured_at':read(HERE/'global-at-seal.command.json')['completed_utc'],'job_snapshot':[{'name':j['name'],'status':j['status'],'conclusion':j['conclusion']} for j in jobs],'qualified':False},
    'artifact':report['artifact'],'actual_compiler':report['compiler'],
    'actual_compiler_host_fixture_qualified':True,'canonical_closed_fixture_CI_component_accepted':True,
    'source_bindings':{'canonical_paths':report['artifact']['exact_committed_source_paths_bound'],'runner_sha256':report['runner_sha256'],'pack_manifest_sha256':selection['pack_manifest_sha256'],'workflow_sha256':selection['workflow_sha256'],'local_accepted_decision_sha256':digest((HERE/'comparison-final-decision.json').read_bytes())['sha256'],'canonical_root_selection_sha256':digest((HERE/'source-selection.stdout').read_bytes())['sha256']},
    'focused_controls':report['focused_controls'],'normal_full_invocations':report['normal_full_invocations'],'commands':report['commands'],
    'deadlines':{'active_seconds':600,'cleanup_seconds':60,'child_seconds':60,'source_constants_unchanged':True},
    'active_elapsed_seconds':report['active_elapsed_seconds'],'cleanup_elapsed_seconds':report['cleanup_elapsed_seconds'],'elapsed_seconds':report['elapsed_seconds'],'max_child_seconds':report['max_child_seconds'],
    'modes':report['modes'],'retained_logical_files_verified':report['retained_files_verified'],'retained_logical_bytes_verified':report['retained_logical_bytes_verified'],'unique_content_members_verified':report['unique_content_members_verified'],
    'derived_source_files_verified':report['derived_source_files_verified'],'compiler_products_hashed_removed_per_receipt':report['compiler_products_hashed_removed'],'postflight_checks_passed':report['postflight_checks_passed'],
    'all_command_outputs_and_retained_bytes_hashed':report['all_command_outputs_and_retained_bytes_hashed'],'all103commands_owned_TMP':report['all103children_owned_TMP'],
    'full_raw_audit_sha256':digest((HERE/'full-audit.json').read_bytes())['sha256'],'command_records_digest_verified':len(records),'command_records':records,
    'collection_failures_preserved':failed,'audit_authoring_failures':0,'CI_retries_executed':0,
    'historical_full_Debug_timeout_remains_failed':local['original_full_producer_Debug60s_timeout_remains_failed'],'performance_equivalence_claimed':False,
    'limits':report['limits'],
    'cleanup':{'artifacts_extracted_or_executed':False,'new_Rust_or_native_runtime_invocations':0,'UI_capture_or_process_inventory':False,'git_mutations':False,'source_or_root_metadata_edits':False,'children_reaped':True,'original8ac_audit_reverified_and_unchanged':True},
    'full_runtime_or_public_File_or_target_native_or_FieldLog_or_GA_qualified':False,
}
save('acceptance.json',receipt)
members=[]
for path in sorted(HERE.rglob('*')):
    assert not path.is_symlink()
    if path.is_file():members.append({'path':str(path.relative_to(HERE)),**digest(path.read_bytes())})
seal={'schema':1,'at':datetime.now(timezone.utc).isoformat(),'source_revision':SHA,'source_tree':TREE,'run_id':RUN,'scope':'Frozen exact-source data-only dedicated fixture CI artifact audit; global CI still running at recorded snapshot','acceptance_sha256':digest((HERE/'acceptance.json').read_bytes())['sha256'],'members':members,'member_count':len(members),'total_bytes':sum(m['bytes'] for m in members)}
save('seal.json',seal)
print(json.dumps({'status':'sealed','acceptance_sha256':seal['acceptance_sha256'],'seal_sha256':digest((HERE/'seal.json').read_bytes())['sha256'],'members':len(members),'bytes':seal['total_bytes'],'actual_compiler':'Rust1.98.1 arm64','global_status_at_snapshot':run['status']}))
