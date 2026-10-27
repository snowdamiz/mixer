"""Small metadata-only compiler controls over the exact unchanged account file."""
from pathlib import Path
import json
import shutil
import sys
sys.dont_write_bytecode=True
from prepare import HERE,ACCOUNT_PACKET,ACCOUNT,COMPILE_KEYS,sha,canonical,roster,write,checked_candidate
from run import command,RUSTC,identity,packed,packed_env

def main():
    assert not (HERE/'seal.json').exists()
    source,hosts=checked_candidate()
    controls={}
    for name,code in [('double_dispatch','E0382'),('borrow_escape','E0515'),('cross_thread','E0277')]:
        data=(ACCOUNT_PACKET/('negative_'+name+'.rs')).read_bytes()
        controls[name]=(data,1,code)
    prefix=b'#![allow(dead_code)]\n#[path = "host_account.rs"] mod host_account;\n'
    controls['private_quote']=(prefix+b'fn fake() -> host_account::ReviewedWholeQuoteV1 { host_account::ReviewedWholeQuoteV1 { total: panic!() } }\n',1,'E0451')
    controls['private_destroyed_token']=(prefix+b'fn fake(reservation: host_account::ReservationV1<\'_>) -> host_account::DestroyedStorageV1<\'_> { host_account::DestroyedStorageV1 { reservation } }\n',1,'E0451')
    controls['positive_borrowed_and_retirement']=(prefix+b"fn borrowed<'a,'b>(owner: &'b host_account::PrepaidOwnedV1<'a,Vec<u8>>) -> Option<&'b Vec<u8>> { owner.inspect_v1() }\nfn retire<'a>(owner: host_account::PrepaidOwnedV1<'a,Vec<u8>>) { if let Some(token) = owner.destroy_owned_v1() { token.release_destroyed_v1(); } }\n",0,None)
    results=[]
    scratch=HERE/'owned-privacy-work';scratch.mkdir(exist_ok=False)
    completed=False
    try:
        env=dict(PATH='/usr/bin:/bin',TMPDIR=str(scratch))
        version,_=command('privacy-rustc-version',[RUSTC,'-vV'],env,required='rustc 1.99.0',timeout=10)
        compiler=identity(RUSTC)
        for name,(driver,expected,error) in controls.items():
            label='privacy-'+name
            work=scratch/name;work.mkdir()
            exact={'host_account.rs':source[ACCOUNT],'driver.rs':driver}
            for path,data in exact.items():(work/path).write_bytes(data)
            out=work/'control.rmeta'
            argv=[str(RUSTC),'--crate-name','composition_account_control','--edition=2021',
                '--target','aarch64-apple-darwin','--crate-type','rlib','-C','opt-level=0',
                '-C','overflow-checks=yes','-C','panic=unwind',str(work/'driver.rs'),'--emit=metadata='+str(out)]
            closure=dict(schema=1,distribution_source=roster(source),host_support=roster(hosts),compiled_source=roster(exact),
                exact_account_file_sha256=sha(source[ACCOUNT]),actual_root_private_typed_route_compiled=False,
                control_only=True,source_host_compiler_orchestration_distinct=True,
                compiler=compiler,compiler_version_sha256=sha(version),orchestration=identity(Path(__file__)))
            parts=[canonical(closure),packed(argv),packed_env(env),version]
            keys=dict(zip(COMPILE_KEYS,[sha(parts[0]),sha(parts[1]),sha(parts[2]),compiler['sha256'],sha(version)]))
            pre=HERE/'preimages'/label;pre.mkdir(parents=True,exist_ok=False)
            for file,data in zip(['manifest.json','argv.bin','environment.bin','compiler-version.txt'],parts):(pre/file).write_bytes(data)
            write('preimages/'+label+'/binding.json',dict(schema=1,distribution_source_tree_sha256=roster(source)['tree_sha256'],
               compiled_source_tree_sha256=roster(exact)['tree_sha256'],source_members=len(source),compiled_members=2,
               host_support_members=11,host_support_tree_sha256=roster(hosts)['tree_sha256'],compile_identity_keys=keys,
               environment_preimage_excludes_only_five_injected_keys=True,no_prior_identity_reused=True,
               standalone_control_is_not_whole_tree_build=True))
            (HERE/(label+'.rs')).write_bytes(driver)
            _,receipt=command(label,argv,env|keys,expected=expected,required=error,timeout=30)
            if expected==0:assert out.stat().st_size>0
            results.append(dict(name=name,expected_exit=expected,required_error=error,
                exact_account_sha256=sha(source[ACCOUNT]),compiled_source_tree_sha256=roster(exact)['tree_sha256'],
                artifact=identity(out) if out.exists() else None,executed=False,expectation_met=receipt['expectation_met']))
        assert identity(RUSTC)==compiler
        completed=True
    finally:
        receipts=[json.loads(p.read_bytes()) for p in (HERE/'commands').glob('privacy-*/receipt.json')]
        absent=all(r['owned_group_absent'] and r['child_reaped'] for r in receipts)
        if absent:shutil.rmtree(scratch)
        write('privacy-cleanup.json',dict(schema=1,completed=completed,owned_scratch_removed=not scratch.exists(),
            recorded_owned_groups_absent=absent,no_global_inventory=True,no_runtime_UI_capture_started=True))
    write('privacy-results.json',dict(schema=1,distribution_source_tree_sha256=roster(source)['tree_sha256'],
        controls=results,negative_controls=5,positive_controls=1,metadata_only=True,
        actual_root_route_privacy_evidence='unchanged account/entry/leaf visibility + exact production metadata compile; controls exercise account source only',
        production_source_visibility_widened=False,grant_or_root_policy_or_whole_quote_selected=False))

if __name__=='__main__':main()
