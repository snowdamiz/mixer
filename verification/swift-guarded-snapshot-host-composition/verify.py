"""Offline custody/configuration/receipt audit. Never compiles or runs Rust."""
from pathlib import Path
import json
import struct
import sys
sys.dont_write_bytecode=True
from prepare import HERE,COMBINED,ACCOUNT_PACKET,ACCOUNT,COMPILE_KEYS,sha,canonical,roster,write,checked_candidate
from run import packed,packed_env,test_source

def unpack(data):
    count=struct.unpack_from('<Q',data,0)[0];offset=8;values=[]
    for _ in range(count):
        size=struct.unpack_from('<Q',data,offset)[0];offset+=8
        values.append(data[offset:offset+size]);offset+=size
    assert offset==len(data)
    return values

def main():
    source,hosts=checked_candidate()
    testing=test_source(source)
    compiled=[];commands=[]
    folders=list((HERE/'preimages').iterdir())
    assert len(folders)==9
    for folder in sorted(folders):
        label=folder.name
        receipt=json.loads((HERE/'commands'/label/'receipt.json').read_bytes())
        binding=json.loads((folder/'binding.json').read_bytes())
        manifest=(folder/'manifest.json').read_bytes();closure=json.loads(manifest)
        argv=(folder/'argv.bin').read_bytes();env=(folder/'environment.bin').read_bytes()
        version=(folder/'compiler-version.txt').read_bytes()
        assert unpack(argv)==[str(v).encode() for v in receipt['argv']]
        base_env={k:v for k,v in receipt['environment'].items() if k not in COMPILE_KEYS}
        assert packed_env(base_env)==env
        compiler_key=closure.get('tools',{}).get('rustc',closure.get('compiler'))
        expected=dict(zip(COMPILE_KEYS,[sha(manifest),sha(argv),sha(env),compiler_key['sha256'],sha(version)]))
        assert expected==binding['compile_identity_keys']
        assert expected=={k:receipt['environment'][k] for k in COMPILE_KEYS}
        assert binding['source_members']==146 and binding['host_support_members']==11
        if label.startswith('privacy-'):
            exact={'host_account.rs':source[ACCOUNT],'driver.rs':(HERE/(label+'.rs')).read_bytes()}
            assert closure['distribution_source']==roster(source)
            assert closure['compiled_source']==roster(exact)
            assert closure['host_support']==roster(hosts)
        else:
            assert closure['distribution']==roster(source) and closure['host_support']==roster(hosts)
            expected_source=testing if label.startswith('interactions-') else source
            assert closure['compiled_source']==roster(expected_source)
            assert 'mixer_bootstrap_one_fixture_v1' in receipt['argv']
        assert sha(Path(compiler_key['path']).read_bytes())==compiler_key['sha256']
        compiled.append(dict(label=label,five_keys_verified=True,manifest_sha256=sha(manifest),
            compiled_source_tree_sha256=binding['compiled_source_tree_sha256']))
    for folder in sorted((HERE/'commands').iterdir()):
        receipt=json.loads((folder/'receipt.json').read_bytes())
        for stream in ['stdout','stderr']:
            assert sha((folder/stream).read_bytes())==receipt[stream+'_sha256']
        assert receipt['child_reaped'] and receipt['owned_group_absent']
        assert not receipt['timed_out_or_output_limited'] and receipt['expectation_met']
        assert receipt['exit_code']==receipt['expected_exit_code']
        assert receipt['timeout_seconds']<=180
        commands.append(dict(label=folder.name,expected_exit=receipt['expected_exit_code'],expectation_met=True))
    assert len(commands)==19
    for label in ['production-metadata','interactions-debug','interactions-optimized']:
        cleanup=json.loads((HERE/'commands'/label/'cleanup.json').read_bytes())
        assert cleanup['completed'] and cleanup['recorded_owned_groups_absent'] and cleanup['owned_scratch_removed']
        artifact=json.loads((HERE/'commands'/label/'artifact.json').read_bytes())
        assert artifact['nonempty'] and artifact['bytes']>0
        assert not Path(artifact['path']).exists()
    assert json.loads((HERE/'privacy-cleanup.json').read_bytes())['owned_scratch_removed']
    assert not (HERE/'owned-work').exists() and not (HERE/'owned-privacy-work').exists()
    inventory=json.loads((HERE/'inventory-invariance.json').read_bytes())
    types=json.loads((HERE/'source-type-invariants.json').read_bytes())
    assert inventory['function_count']==19 and inventory['roles']==396 and inventory['logical_bytes']==311071
    assert types['fresh_layout_queries']==0 and types['no_role_discount']
    assert types['P0_roles_retained']==208 and types['P0_logical_bytes_retained']==234375
    costs=json.loads((HERE/'cost-rebinding-required.json').read_bytes())
    assert costs['total_source_bytes_delta']==24052
    assert costs['complete_work_or_storage_quote'] is None
    assert not costs['source145_loader_quote_applies_to_source146']
    summary=dict(schema=1,source_members=146,source_tree_sha256=roster(source)['tree_sha256'],
      audit_command=['python3','verification/swift-guarded-snapshot-host-composition/verify.py'],
      audit_python_version=sys.version,audit_tool_sha256=sha(Path(__file__).read_bytes()),
      host_support_members=11,host_support_tree_sha256=roster(hosts)['tree_sha256'],
      test_overlay_tree_sha256=roster(testing)['tree_sha256'],
      production_metadata_bytes=json.loads((HERE/'commands/production-metadata/artifact.json').read_bytes())['bytes'],
      exact_private_production_route_compile_only=True,whole_tree_builds=3,
      compiler_builds_including_narrow_controls=len(compiled),verified_identity_keys=len(compiled)*5,
      inspected_command_receipts=len(commands),compilations=compiled,commands=commands,
      filtered_synthetic_tests_each_mode=17,new_composition_tests_each_mode=2,
      frozen_combined_tests_each_mode=4,frozen_account_tests_each_mode=11,
      negative_privacy_controls=5,positive_privacy_controls=1,
      unexpected_Rust_or_test_failures=0,driver_assertion_failures=0,
      fresh_MIR_functions=19,fresh_MIR_roles=396,
      accepted_layout_bytes_retained_under_invariants=311071,fresh_layout_remeasurement=False,
      P0_roles_retained=208,P0_logical_bytes_retained=234375,
      source145_quote_not_reused=True,WorkAuditPending=True,RootPolicyPending=True,WholeQuotePending=True,
      helper_undispatched=True,all_owned_groups_reaped=True,all_owned_scratch_removed=True,
      global_process_inventory=False,native_UI_capture_runtime=False,
      real_loader_guest_cache_scope_construct_writer_runtime=False,
      complete_funding_healthy_cleanup_operational_OTA_GA_accepted=False)
    if (HERE/'seal.json').exists():
        assert json.loads((HERE/'verification-results.json').read_bytes())==summary
    else: write('verification-results.json',summary)
    print(json.dumps({k:summary[k] for k in ['source_members','source_tree_sha256','production_metadata_bytes','verified_identity_keys','inspected_command_receipts','filtered_synthetic_tests_each_mode']}))

if __name__=='__main__':main()
