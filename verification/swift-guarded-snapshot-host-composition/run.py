"""Serial bounded compiler and inspected pure-host test routes only."""
from pathlib import Path
import argparse
import gzip
import json
import os
import platform
import re
import shutil
import signal
import struct
import subprocess
import sys
import time
sys.dont_write_bytecode=True
from prepare import (HERE,ROOT,V,COMBINED,ACCOUNT_PACKET,PROFILE,ACCOUNT,CONTROL,
                     COMPILE_KEYS,sha,canonical,row,roster,write,checked_candidate)

RUSTC=Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
SDK=Path('/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk')
FEATURES=['experimental-swift-reactor','experimental-swift-wasi',
          'experimental-stream-validation','experimental-function-cache']
FILES=['prepare.py','run.py','interaction-tests.inc.rs','cache-tests.inc.rs',
       'profile-tests.inc.rs','account-cycle-tests.inc.rs','control-account-tests.inc.rs',
       'entry-cycle-test-bridge.inc.rs','profile-cycle-test-bridge.inc.rs',
       'cache-cycle-test-bridge.inc.rs','host-test-plan.json']

def identity(path):
    data=path.read_bytes()
    return dict(path=str(path),bytes=len(data),sha256=sha(data))
def packed(values):
    data=[os.fsencode(value) for value in values]
    return struct.pack('<Q',len(data))+b''.join(struct.pack('<Q',len(value))+value for value in data)
def packed_env(values):
    return packed([os.fsencode(k)+b'='+os.fsencode(v) for k,v in sorted(values.items(),key=lambda x:os.fsencode(x[0]))])
def absent(group):
    try: os.killpg(group,0); return False
    except ProcessLookupError: return True
def command(label,argv,env,expected=0,required=None,timeout=180):
    folder=HERE/'commands'/label
    folder.mkdir(parents=True,exist_ok=False)
    started=time.monotonic(); actions=[]; limited=False
    with (folder/'stdout').open('wb') as out,(folder/'stderr').open('wb') as err:
        child=subprocess.Popen([str(value) for value in argv],cwd=ROOT,env=env,
                               stdout=out,stderr=err,start_new_session=True)
        try:
            while child.poll() is None:
                if time.monotonic()-started>timeout or out.tell()+err.tell()>4*1024*1024:
                    limited=True
                    os.killpg(child.pid,signal.SIGTERM); actions.append('TERM owned group at cap')
                    try: child.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        os.killpg(child.pid,signal.SIGKILL); actions.append('KILL owned group at grace cap')
                    break
                time.sleep(.05)
        finally:
            code=child.wait(timeout=3)
            if not absent(child.pid):
                os.killpg(child.pid,signal.SIGTERM); actions.append('TERM surviving owned descendants')
                deadline=time.monotonic()+2
                while not absent(child.pid) and time.monotonic()<deadline: time.sleep(.05)
                if not absent(child.pid):
                    os.killpg(child.pid,signal.SIGKILL); actions.append('KILL surviving owned descendants')
    stdout=(folder/'stdout').read_bytes(); stderr=(folder/'stderr').read_bytes()
    passed=code==expected and not limited and absent(child.pid)
    if required: passed=passed and required.encode() in stdout+stderr
    receipt=dict(schema=1,argv=[str(v) for v in argv],environment=env,cwd=str(ROOT),
       exit_code=code,expected_exit_code=expected,required_output=required,
       elapsed_seconds=time.monotonic()-started,timeout_seconds=timeout,
       output_cap_bytes=4*1024*1024,timed_out_or_output_limited=limited,
       owned_process_group=child.pid,new_session=True,child_reaped=True,
       owned_group_absent=absent(child.pid),cleanup_actions=actions,
       stdout_sha256=sha(stdout),stderr_sha256=sha(stderr),expectation_met=passed,
       runner_sha256=sha(Path(__file__).read_bytes()))
    write('commands/'+label+'/receipt.json',receipt)
    print(json.dumps(dict(label=label,exit_code=code,expectation_met=passed,elapsed_seconds=receipt['elapsed_seconds'])),flush=True)
    assert passed,(label,stdout[-1500:],stderr[-3500:])
    return stdout,receipt

def test_source(source):
    exact=dict(source); operations=[]
    def append(name,filenames):
        before=exact[name]
        data=b''.join((HERE/f).read_bytes() for f in filenames)
        exact[name]+=data
        operations.append(dict(path=name,operation='append',before=row(name,before),
            fragments=[identity(HERE/f) for f in filenames],after=row(name,exact[name])))
    # Add bridge inside the account entry only in the separate test overlay.
    before=exact[PROFILE]
    assert before.endswith(b'\n}\n')
    exact[PROFILE]=before[:-2]+(HERE/'entry-cycle-test-bridge.inc.rs').read_bytes()+b'}\n'
    operations.append(dict(path=PROFILE,operation='insert test-only bridge before final entry brace',
        before=row(PROFILE,before),fragment=identity(HERE/'entry-cycle-test-bridge.inc.rs'),after=row(PROFILE,exact[PROFILE])))
    append(PROFILE,['profile-tests.inc.rs','profile-cycle-test-bridge.inc.rs'])
    append(ACCOUNT,['account-cycle-tests.inc.rs'])
    append('src/experimental_swift_reactor/cache.rs',['cache-tests.inc.rs','cache-cycle-test-bridge.inc.rs'])
    append('src/experimental_swift_reactor/control_tests.rs',['interaction-tests.inc.rs','control-account-tests.inc.rs'])
    manifest=dict(schema=1,source=roster(exact),distribution=roster(source),operations=operations,
        synthetic_only=True,product_private_route_not_invoked=True,
        production_visibility_unchanged=True,test_helpers_are_not_host11=True)
    path=HERE/'test-overlay-manifest.json'
    if path.exists(): assert json.loads(path.read_bytes())==manifest
    else: write('test-overlay-manifest.json',manifest)
    return exact

def normalize(text):
    # The accepted source and new tree use different owned scratch paths and
    # initial_profile has the accepted phase/helper lines before the same entry.
    text=re.sub(r'/Users/andreyyurlov/Documents/dev/mixer/verification/[^ :@,{}]+/vm/', '<VM>/',text)
    text=re.sub(r'(?<=\.rs):\d+:\d+: \d+:\d+',':<SPAN>',text)
    return text
def functions(text):
    for m in re.finditer(r'^fn .+ \{$',text,re.M):
        yield text[m.start():text.index('\n}\n',m.start())+3]
def role_inventory(fn):
    header=fn.split('\n',1)[0]
    m=re.fullmatch(r'fn [^(]+\((.*)\) -> (.*) \{',header)
    assert m,header
    roles=[dict(local=n,kind='parameter',compiler_type=t) for n,t in re.findall(r'(_\d+): (.*?)(?=, _\d+:|$)',m[1])]
    roles += [dict(local=n,kind='return-place' if n=='_0' else 'local-or-temporary',compiler_type=t)
      for n,t in re.findall(r'^\s+let (?:mut )?(_\d+): (.*);(?:\s*//[^\n]*)?$',fn,re.M)]
    assert len({r['local'] for r in roles})==len(roles)
    return roles
def compare_inventory(mir):
    accepted=json.loads((ACCOUNT_PACKET/'caller-inventory.json').read_bytes())
    old_mir=(ACCOUNT_PACKET/'entry-and-account.mir').read_text()
    old_functions=list(functions(old_mir))
    assert len(old_functions)==len(accepted['functions'])==19
    all_new={normalize(fn.split('\n',1)[0]):fn for fn in functions(mir.read_text())}
    comparisons=[]; focused=[]
    for old,record in zip(old_functions,accepted['functions']):
        key=normalize(old.split('\n',1)[0]); new=all_new[key]
        roles=role_inventory(new)
        frozen=[{k:r[k] for k in ['local','kind','compiler_type']} for r in record['roles']]
        assert normalize(canonical(roles).decode())==normalize(canonical(frozen).decode()),key
        # Source-span comments and only the implementation location differ.
        old_no_comments='\n'.join(line.split('//',1)[0].rstrip() for line in normalize(old).splitlines())
        new_no_comments='\n'.join(line.split('//',1)[0].rstrip() for line in normalize(new).splitlines())
        assert old_no_comments==new_no_comments,key
        comparisons.append(dict(header=key,roles=len(roles),accepted_logical_bytes=record['measured_logical_bytes'],
          normalized_body_and_all_role_types_identical=True,original_sha256=sha(old.encode()),composed_sha256=sha(new.encode())))
        focused.append(new)
    (HERE/'entry-and-account.mir').write_text('\n'.join(focused))
    write('inventory-invariance.json',dict(schema=1,accepted_source=accepted['source_tree_sha256'],
        composed_source=json.loads((HERE/'source-manifest.json').read_bytes())['tree_sha256'],
        accepted_inventory_sha256=sha((ACCOUNT_PACKET/'caller-inventory.json').read_bytes()),
        function_count=19,roles=sum(f['roles'] for f in comparisons),
        logical_bytes=sum(f['accepted_logical_bytes'] for f in comparisons),functions=comparisons,
        same_compiler_and_target_required=True,source_type_layout_invariants_review='source-type-invariants.json',
        layouts_inherited_under_recorded_source_type_invariants=True,new_layout_queries=0,
        fresh_MIR_inventory_only_not_complete_work_or_operational_storage=True,
        no_original_role_discount=True,P0_roles=208,P0_logical_bytes=234375,
        complete_whole_quote=False,root_policy_or_P0_authority_established=False))

def compile_one(label,interactions=False,optimized=False):
    assert not (HERE/'seal.json').exists()
    source,hosts=checked_candidate()
    work=HERE/'owned-work'/label
    work.mkdir(parents=True,exist_ok=False)
    artifact=work/('tests.bin' if interactions else 'production.rmeta')
    completed=False
    try:
        actual=test_source(source) if interactions else source
        vm=work/'vm'
        for name,data in actual.items():
            path=vm/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        env=dict(PATH='/usr/bin:/bin',TMPDIR=str(work),RUSTC_BOOTSTRAP='1',CARGO_MANIFEST_DIR=str(vm),SDKROOT=str(SDK))
        version,_=command(label+'-rustc-version',[RUSTC,'-vV'],env,required='rustc 1.99.0',timeout=10)
        compiler=identity(RUSTC)
        tools=dict(rustc=compiler,version_sha256=sha(version),python=identity(Path(sys.executable).resolve()),
          python_version=sys.version,cc=identity(Path('/usr/bin/cc')),host_platform=platform.platform(),
          SDK_headers=[identity(SDK/f) for f in ['usr/include/CommonCrypto/CommonDigest.h','usr/include/crt_externs.h','usr/include/mach-o/dyld.h','usr/include/unistd.h']],separate_from_host11=True)
        orchestration=[identity(HERE/f) for f in FILES]
        closure=dict(schema=1,distribution=roster(source),compiled_source=roster(actual),
           host_support=roster(hosts),test_overlay=interactions,orchestration=orchestration,tools=tools,
           root_releases=json.loads((HERE/'input-bindings.json').read_bytes())['releases'],
           private_route_cfg='mixer_bootstrap_one_fixture_v1',
           genuine_loader_fixture_runtime=False,selected_policy_or_whole_quote=False)
        argv=[str(RUSTC),'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin',
          '-C','opt-level='+('3' if optimized else '0'),'-C','overflow-checks=yes','-C','panic=unwind','-Zmir-opt-level=0']
        for f in FEATURES: argv+=['--cfg','feature="'+f+'"']
        argv+=['--cfg','mixer_bootstrap_one_fixture_v1']
        argv+=['--test'] if interactions else ['--crate-type','rlib']
        argv+=[str(vm/'src/lib.rs')]
        argv+=['--emit=link','-o',str(artifact)] if interactions else ['-Zmir-include-spans=yes','--emit=metadata='+str(artifact)+',mir='+str(work/'production.mir')]
        parts=[canonical(closure),packed(argv),packed_env(env),version]
        values=[sha(parts[0]),sha(parts[1]),sha(parts[2]),compiler['sha256'],sha(parts[3])]
        compile_env=env|dict(zip(COMPILE_KEYS,values))
        pre=HERE/'preimages'/label;pre.mkdir(parents=True,exist_ok=False)
        for filename,data in zip(['manifest.json','argv.bin','environment.bin','compiler-version.txt'],parts): (pre/filename).write_bytes(data)
        write('preimages/'+label+'/binding.json',dict(schema=1,distribution_source_tree_sha256=roster(source)['tree_sha256'],
          compiled_source_tree_sha256=roster(actual)['tree_sha256'],source_members=len(source),host_support_members=len(hosts),
          host_support_tree_sha256=roster(hosts)['tree_sha256'],compile_identity_keys=dict(zip(COMPILE_KEYS,values)),
          environment_preimage_excludes_only_five_injected_keys=True,no_prior_identity_reused=True,
          host11_tools_orchestration_test_source_distinct=True))
        command(label,argv,compile_env)
        assert identity(RUSTC)==compiler
        assert [identity(Path(item['path'])) for item in orchestration]==orchestration
        assert roster({p.relative_to(vm).as_posix():p.read_bytes() for p in vm.rglob('*') if p.is_file()})==roster(actual)
        checked_candidate()
        output=identity(artifact)
        assert output['bytes']>0
        write('commands/'+label+'/artifact.json',output|dict(executed=interactions,nonempty=True,
          usable_loader_output_or_executable_qualification=False,scope='synthetic test executable' if interactions else 'production metadata only'))
        if interactions:
            for filter_,count in [('combined_source_interaction_',4),('host_composition_interaction_',2),('host_account_v1::tests::',11)]:
                command(label+'-'+filter_.strip('_').replace(':','-'),[artifact,filter_,'--nocapture','--test-threads=1'],
                   dict(PATH='/usr/bin:/bin'),required=str(count)+' passed; 0 failed',timeout=30)
        else: compare_inventory(work/'production.mir')
        write('commands/'+label+'/scope.json',dict(schema=1,source146=roster(source)['tree_sha256'],compiled_source=roster(actual)['tree_sha256'],
          actual_private_typed_route_compiled=True,metadata_only=not interactions,cfg_test=interactions,
          pure_synthetic_tests=17 if interactions else 0,actual_loader_guest_cache_scope_construct_writer_executed=False,
          unit_metadata_empty_output_used=False,WorkAuditPending_and_root_policy_whole_quote_preserved=True,
          native_simulator_emulator_UI_capture_started=False,healthy_cleanup_full_funding_operational_GA_qualified=False))
        completed=True
    finally:
        receipts=[json.loads(p.read_bytes()) for p in (HERE/'commands').glob(label+'*/receipt.json')]
        groups_absent=all(r['owned_group_absent'] and r['child_reaped'] for r in receipts)
        removed=identity(artifact) if artifact.exists() else None
        if groups_absent: shutil.rmtree(work)
        write('commands/'+label+'/cleanup.json',dict(schema=1,completed=completed,
           recorded_owned_groups_absent=groups_absent,owned_scratch_removed=not work.exists(),removed_artifact=removed,
           no_global_inventory=True,no_native_UI_capture_started=True))
        parent=HERE/'owned-work'
        if parent.exists() and not any(parent.iterdir()):parent.rmdir()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('label');p.add_argument('--interactions',action='store_true');p.add_argument('--optimized',action='store_true')
    a=p.parse_args();compile_one(a.label,a.interactions,a.optimized)
