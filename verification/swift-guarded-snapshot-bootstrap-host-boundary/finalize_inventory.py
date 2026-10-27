#!/usr/bin/env python3
"""Finalize retained compiler evidence; never launches the compiler or product."""
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
BASE = ROOT/'verification/swift-guarded-snapshot-funding-implementation/source/vm'
PROFILE = 'src/experimental_swift_reactor/cache/initial_profile_v1.rs'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    fn = (HERE/'driver.mir').read_text()
    assert fn.startswith('fn run_one_loaded_fixture_v1(') and fn.endswith('\n}\n')
    head = re.fullmatch(r'fn .*\((.*)\) -> (.*) \{', fn.splitlines()[0])
    parameters = re.findall(r'(_\d+): (.*?)(?=, _\d+:|$)',head[1])
    roles = [dict(local=local,kind='parameter',compiler_type=ty) for local,ty in parameters]
    roles += [dict(local=local,kind='return-place' if local=='_0' else 'local-or-temporary',compiler_type=ty)
              for local,ty in re.findall(r'^\s+let (?:mut )?(_\d+): (.*?);',fn,flags=re.M)]
    assert len({r['local'] for r in roles})==len(roles)
    assert len(parameters)==7
    types = sorted({r['compiler_type'] for r in roles})
    errors = (HERE/'commands/leaf-layout-queries/stderr').read_text()
    blocks = errors.split('error[E0308]:')[1:]
    assert len(blocks)==len(types)
    sizes={}
    for block in blocks:
        indices=set(re.findall(r'LEAF_QUERY_(\d+)',block))
        assert len(indices)==1,indices
        index=int(next(iter(indices)))
        ty=types[index]
        assert f'std::mem::size_of::<{ty}>()' in block
        measured=re.search(r'found one with a size of (\d+)',block)
        assert measured,(ty,block)
        assert ty not in sizes
        sizes[ty]=int(measured[1])
    assert set(sizes)==set(types)
    for role in roles: role['bytes']=sizes[role['compiler_type']]
    for name,expected in [('leaf-metadata-mir',0),('leaf-layout-queries',1),('compiler-version',0)]:
        folder=HERE/'commands'/name
        receipt=json.loads((folder/'receipt.json').read_text())
        assert receipt['exit_code']==expected and receipt['expectation_met']
        assert '--test' not in receipt['argv']
        for member in ['stdout','stderr']:
            data=(folder/member).read_bytes()
            assert receipt['output'][member]==dict(bytes=len(data),sha256=sha(data))
    source=json.loads((HERE/'source-manifest.json').read_text())
    rows={r['path']:r for r in source['members']}
    for p in BASE.rglob('*'):
        if not p.is_file():continue
        name=p.relative_to(BASE).as_posix()
        data=p.read_bytes()+(b'\n\n'+(HERE/'driver.inc.rs').read_bytes() if name==PROFILE else b'')
        assert rows[name]==dict(path=name,bytes=len(data),sha256=sha(data)),name
    assert len(rows)==144
    result=dict(schema=1,target='aarch64-apple-darwin',
                compiler_version=(HERE/'commands/compiler-version/stdout').read_text(),
                source_tree_sha256=source['source_tree_sha256'],
                scaffold_sha256=sha((HERE/'driver.inc.rs').read_bytes()),
                driver_mir_sha256=sha(fn.encode()),role_count=len(roles),
                logical_source_object_union_bytes=sum(r['bytes'] for r in roles),
                parameter_source_object_bytes=sum(r['bytes'] for r in roles if r['kind']=='parameter'),
                roles=roles,actual_type_sizes=sizes,
                build_mode='production library with mixer_bootstrap_one_fixture_v1; cfg(test) absent',
                no_WASI_attachment=True, no_test_registration=True,
                old_H_81327_and_external_163_roles_reused=False,
                cfg_test_specific_instrumentation_not_compiled=True,
                no_claim_of_zero_all_host_or_standard_library_instrumentation=True,
                fresh_compiler_role_inventory=True,product_runtime_dispatched=False,
                physical_stack_RSS_CPU_bound=False,
                whole_launcher_inventory_or_authority_qualified=False,
                final_composed_source_layout_rebinding_pending=True,
                compiler_driver_snapshot_sha256=sha((HERE/'commands/compiler-driver-at-start.py').read_bytes()),
                compiler_driver_snapshot_capture='Captured unchanged after commands and before further utility edits; not embedded loader/custody authority')
    (HERE/'driver-inventory.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:result[k] for k in ['role_count','logical_source_object_union_bytes','parameter_source_object_bytes','source_tree_sha256']}))


if __name__=='__main__':
    main()
