#!/usr/bin/env python3
"""Bounded compile-only source/MIR and actual-type layout inventory."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
BASE = ROOT/'verification/swift-guarded-snapshot-funding-implementation'
BOOT = ROOT/'verification/swift-guarded-snapshot-bootstrap-host-boundary'
RUSTC = Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
PROFILE = 'src/experimental_swift_reactor/cache/initial_profile_v1.rs'
ACCOUNT = 'src/experimental_swift_reactor/cache/initial_profile_v1/host_account_v1.rs'
BASE_TREE = '7e3e861ca65d8c6359623443d6a7810b878c1029494a0ae557307d35ed43484b'

def sha(data): return hashlib.sha256(data).hexdigest()
def canonical(value): return json.dumps(value,sort_keys=True,separators=(',',':')).encode()
def write(name,value): (HERE/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def members(folder):
    return [dict(path=p.relative_to(folder).as_posix(),bytes=p.stat().st_size,
                 sha256=sha(p.read_bytes())) for p in sorted(folder.rglob('*')) if p.is_file()]

def prepare(scratch):
    bindings=[]
    for relative, expected in [
        ('verification/swift-semantic-adapter-root-review/guarded-snapshot-bootstrap-next-source-release.json',
         '92889d223971bf99c3a7fdf9d2afe8d0491d02273f62d922ee78010f38ae9164'),
        ('verification/swift-semantic-adapter-root-review/guarded-snapshot-work-admission-host-acceptance.json',
         'c08376ad082af1b12fed92571d23f2544d52dad389096b62790a4073b7b3a8b3'),
        ('verification/swift-guarded-snapshot-bootstrap-host-boundary/seal.json',
         '00f5bf754a13317ac18dd9959a1db4a9b025b16c72fc99a9d4cfddfcc7cb4dba'),
        ('verification/swift-guarded-snapshot-funding-implementation/seal.json',
         'e006b90b8c9e351e0d4dd504c6de309e2c7970b628fe9fc4f788cb30e77bedf7')]:
        path=ROOT/relative
        assert sha(path.read_bytes())==expected,relative
        bindings.append(dict(path=relative,sha256=expected,bytes=path.stat().st_size))
    seal=json.loads((BOOT/'seal.json').read_text())
    listing=seal['members']
    assert len(listing)==62
    for item in listing:
        data=(BOOT/item['path']).read_bytes()
        assert len(data)==item['bytes'] and sha(data)==item['sha256'],item['path']
    assert sum(item['bytes'] for item in listing)==344883
    original=members(BASE/'source/vm')
    assert len(original)==144 and sha(canonical(original))==BASE_TREE
    vm=scratch/'vm'
    shutil.copytree(BASE/'source/vm',vm)
    (vm/ACCOUNT).write_bytes((HERE/'host_account.rs').read_bytes())
    with (vm/PROFILE).open('ab') as out:
        out.write(b'\n\n'+(BOOT/'driver.inc.rs').read_bytes())
        out.write(b'\n\n'+(HERE/'entry.inc.rs').read_bytes())
    source=members(vm)
    manifest=dict(schema=1,base_tree_sha256=BASE_TREE,source_tree_sha256=sha(canonical(source)),
                  members=source,distribution_members=len(source),added_distribution_members=[ACCOUNT],
                  altered_existing_members=[PROFILE],
                  composed_source145_or_selected_real_fixture_qualified=False,
                  scope='frozen funding144 plus bootstrap leaf and private account/caller; not active combined source145')
    path=HERE/'source-manifest.json'
    if path.exists(): assert json.loads(path.read_text())==manifest
    else: write('source-manifest.json',manifest)
    write('input-bindings.json',dict(schema=1,inputs=bindings,
          bootstrap_members_verified=62,bootstrap_member_bytes_verified=344883,
          base_members_verified=144,base_tree_sha256=BASE_TREE,
          authored=[dict(path=n,bytes=(HERE/n).stat().st_size,sha256=sha((HERE/n).read_bytes()))
                    for n in ['host_account.rs','entry.inc.rs']],
          actual_fixture_geometry_or_completed_quote_bound=False))
    return vm,manifest

def command(name,argv,env,expected,source):
    folder=HERE/'compiler-commands'/name
    folder.mkdir(parents=True,exist_ok=False)
    start=time.monotonic()
    with (folder/'stdout').open('wb') as out,(folder/'stderr').open('wb') as err:
        child=subprocess.Popen(argv,cwd=ROOT,env=env,stdout=out,stderr=err)
        try: code=child.wait(timeout=180)
        except subprocess.TimeoutExpired:
            child.kill();child.wait(timeout=10);raise
    result=dict(argv=argv,cwd=str(ROOT),environment=env,elapsed_seconds=time.monotonic()-start,
                exit_code=code,expected_exit_code=expected,direct_child_pid=child.pid,
                direct_child_waited=True,source_tree_sha256=source['source_tree_sha256'],
                source_manifest_sha256=sha((HERE/'source-manifest.json').read_bytes()),
                tool_sha256=sha(Path(__file__).read_bytes()),
                output={n:dict(bytes=(folder/n).stat().st_size,sha256=sha((folder/n).read_bytes()))
                        for n in ['stdout','stderr']},
                scope='production library compiler only; no loader/VM/cache/scope/writer/native runtime')
    (folder/'receipt.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    assert code==expected,(name,code)
    return folder

def functions(text):
    for match in re.finditer(r'^fn .+ \{$',text,re.M):
        end=text.index('\n}\n',match.start())+3
        yield text[match.start():end]

def role_inventory(fn):
    header=fn.split('\n',1)[0]
    match=re.fullmatch(r'fn .*\((.*)\) -> (.*) \{',header)
    assert match,header
    params=re.findall(r'(_\d+): (.*?)(?=, _\d+:|$)',match[1])
    roles=[dict(local=local,kind='parameter',compiler_type=ty) for local,ty in params]
    roles += [dict(local=local,kind='return-place' if local=='_0' else 'local-or-temporary',compiler_type=ty)
              for local,ty in re.findall(r'^\s+let (?:mut )?(_\d+): (.*?);',fn,re.M)]
    assert len(set(r['local'] for r in roles))==len(roles),header
    return roles

NAMES=['run_one_fixture_v1','setup_files_once_v1','copy_claims_v1','run_prepaid_fixture_v1',
       'invoke_loaded_leaf_once_v1','checked_components_v1','selected_whole_quote_v1',
       'selected_parent_account_v1','from_preexisting_root_v1','usage_v1','reserve_whole_v1',
       'dispatch_v1','inspect_v1','destroy_owned_v1','release_destroyed_v1']

def classify(header):
    if any(name in header for name in ['run_one_fixture_v1','checked_components_v1',
           'selected_whole_quote_v1','selected_parent_account_v1','from_preexisting_root_v1',
           'usage_v1','reserve_whole_v1','dispatch_v1','inspect_v1','destroy_owned_v1',
           'release_destroyed_v1']) or 'host_account_v1.rs:' in header:
        return 'P0-pre-existing-parent-account-bookkeeping'
    if 'setup_files_once_v1' in header:return 'P1-fixture-setup'
    if 'copy_claims_v1' in header:return 'P2-argument-production'
    if 'run_prepaid_fixture_v1' in header:return 'P1-P5-owned-caller-union'
    if 'invoke_loaded_leaf_once_v1' in header:return 'P2-P4-call-arguments-and-typed-result'
    return 'P0-pre-existing-parent-account-bookkeeping'

def mir_phase(vm,scratch,env,flags,source):
    mir=scratch/'entry.mir'
    folder=command('production-metadata-mir',flags+['-Zprint-type-sizes',
             '--emit=metadata='+str(scratch/'entry.rmeta')+',mir='+str(mir)],env,0,source)
    raw=mir.read_text()
    assert 'original_refusal_output_and_diagnostic_owners_keep_storage_through_drop' not in raw
    selected=[]
    for fn in functions(raw):
        header=fn.split('\n',1)[0]
        if any(n in header for n in NAMES) or ('host_account_v1.rs:' in header and '::drop(' in header):
            selected.append(fn)
    assert len(selected)>=17,len(selected)
    focused='\n'.join(selected)
    (HERE/'entry-and-account.mir').write_text(focused)
    records=[dict(header=fn.split('\n',1)[0],phase=classify(fn.split('\n',1)[0]),
                  roles=role_inventory(fn),sha256=sha(fn.encode())) for fn in selected]
    write('mir-roles.json',dict(schema=1,source_tree_sha256=source['source_tree_sha256'],
          function_count=len(records),functions=records,build_mode='production-library custom cfg; cfg(test) absent',
          runtime_dispatched=False,logical_union_not_RSS=True))
    return records

def layout_phase(vm,scratch,env,flags,source):
    records=json.loads((HERE/'mir-roles.json').read_text())['functions']
    types=sorted({r['compiler_type'] for fn in records for r in fn['roles']})
    # Only the production instantiation is inventoried: T is the actual retained
    # typed fixture outcome. Anonymous closure types have no Rust spelling and
    # are kept explicitly pending rather than assigned a guessed/default size.
    query_types={}
    pending={}
    for ty in types:
        if 'impl FnOnce' in ty or '{closure@' in ty or 'fn(' in ty:
            pending[ty]='anonymous closure/callback layout remains pending; never defaulted to zero'
            continue
        resolved=re.sub(r'\bT\b','OwnedFixtureOutcomeV1',ty)
        query_types[ty]=resolved
    prefix='''\n#[cfg(mixer_bootstrap_one_fixture_v1)]\nmod host_entry_layout_queries_v1 {\nuse super::*;\nuse super::super::*;\nuse crate::experimental_swift_reactor::{control,retained_profile_loader_v1};\nuse crate::experimental_swift_reactor::cache::initial_profile_v1;\nuse crate::experimental_swift_reactor;\nuse crate::execute;\nuse crate::Cancellation;\n'''
    # Query inside the account module so private root-policy/bookkeeping types
    # are measured without widening their visibility or exposing constructors.
    queries=''.join(f'const ENTRY_LAYOUT_{i}: [(); usize::MAX] = [(); std::mem::size_of::<{ty}>()];\n'
                    for i,ty in enumerate(query_types.values()) if ty!='()')
    with (vm/ACCOUNT).open('a') as out:out.write(prefix+queries+'}\n')
    lib=vm/'src/lib.rs'
    lib.write_text('#![feature(never_type)]\n'+lib.read_text())
    layout_members=members(vm)
    write('layout-source-manifest.json',dict(schema=1,source_tree_sha256=sha(canonical(layout_members)),
          members=layout_members,scope='exact production source plus compile-only actual-type const layout queries'))
    folder=command('actual-type-layout-queries',flags+['--emit=metadata='+str(scratch/'layout.rmeta')],env,1,source)
    errors=(folder/'stderr').read_text()
    values=list(query_types.values())
    sizes={'()':0}
    for block in errors.split('error[E0308]:')[1:]:
        indices=set(re.findall(r'ENTRY_LAYOUT_(\d+)',block))
        assert len(indices)==1,indices
        ty=values[int(next(iter(indices)))]
        found=re.search(r'found one with a size of (\d+)',block)
        assert found,(ty,block)
        sizes[ty]=int(found[1])
    assert errors.count('error[E0308]')==sum(ty!='()' for ty in values)
    assert not re.findall(r'error\[E(?!0308)\d+\]',errors),errors[-1000:]
    for fn in records:
        for role in fn['roles']:
            ty=role['compiler_type']
            if ty in pending:role['size_status']='pending-anonymous-layout'
            else:
                role['concrete_production_type']=query_types[ty]
                role['bytes']=sizes[query_types[ty]]
        fn['role_count']=len(fn['roles'])
        fn['measured_logical_bytes']=sum(r.get('bytes',0) for r in fn['roles'])
        fn['unmeasured_roles']=sum('bytes' not in r for r in fn['roles'])
    write('caller-inventory.json',dict(schema=1,source_tree_sha256=source['source_tree_sha256'],
          actual_type_queries=len(sizes)-1,actual_type_sizes=sizes,pending_types=pending,
          functions=records,function_count=len(records),role_count=sum(len(f['roles']) for f in records),
          measured_logical_bytes=sum(f['measured_logical_bytes'] for f in records),
          unmeasured_roles=sum(f['unmeasured_roles'] for f in records),
          role_union_is_complete_quote_or_authority=False,
          generic_T_bound_only_to_actual_production_owned_outcome=True,
          account_release_and_token_places_belong_to_preexisting_P0=True,
          P0_logical_work_or_complete_source_storage_quote_reviewed=False,
          actual_fixture_loader_leaf_dispatched=False))

def main():
    assert not (HERE/'seal.json').exists()
    phase=sys.argv[1]
    assert phase in ['mir','layouts']
    scratch=HERE/f'owned-{phase}-work'
    scratch.mkdir(exist_ok=False)
    try:
        vm,source=prepare(scratch)
        env=dict(PATH='/usr/bin:/bin',TMPDIR=str(scratch),CARGO_MANIFEST_DIR=str(vm),RUSTC_BOOTSTRAP='1')
        flags=[str(RUSTC),'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin',
               '-C','opt-level=0','-C','overflow-checks=yes','-C','panic=unwind',
               '-Zmir-opt-level=0','-Zmir-include-spans=yes',
               '--cfg','feature="experimental-swift-reactor"','--cfg','feature="experimental-swift-wasi"',
               '--cfg','feature="experimental-stream-validation"','--cfg','feature="experimental-function-cache"',
               '--cfg','mixer_bootstrap_one_fixture_v1','--crate-type','lib',str(vm/'src/lib.rs')]
        if phase=='mir':mir_phase(vm,scratch,env,flags,source)
        else:layout_phase(vm,scratch,env,flags,source)
    finally:
        shutil.rmtree(scratch)
        write(f'{phase}-cleanup.json',dict(schema=1,owned_scratch_removed=not scratch.exists(),
              product_executables_created=0,product_executables_executed=0,direct_children_waited=True,
              native_UI_capture_device_simulator_emulator_started=False,global_process_inventory=False,
              other_projects_inspected_or_changed=False))

if __name__=='__main__':main()
