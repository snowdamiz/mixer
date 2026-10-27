#!/usr/bin/env python3
"""Compile-only exact leaf MIR/layout inventory, with bounded owned scratch."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
BASE = ROOT / 'verification/swift-guarded-snapshot-funding-implementation'
RUSTC = Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
PROFILE = 'src/experimental_swift_reactor/cache/initial_profile_v1.rs'
TREE = '7e3e861ca65d8c6359623443d6a7810b878c1029494a0ae557307d35ed43484b'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def write(name, data):
    (HERE / name).write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')


def members(folder):
    return [dict(path=p.relative_to(folder).as_posix(), bytes=p.stat().st_size,
                 sha256=digest(p.read_bytes())) for p in sorted(folder.rglob('*')) if p.is_file()]


def command(name, argv, env, expected):
    folder = HERE / 'commands' / name
    folder.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    # A directly owned child only; no process inventory or product execution.
    with (folder / 'stdout').open('wb') as out, (folder / 'stderr').open('wb') as err:
        child = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=out, stderr=err)
        try:
            code = child.wait(timeout=60)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=10)
            raise
    record = dict(argv=argv, cwd=str(ROOT), environment=env,
                  elapsed_seconds=time.monotonic()-start, exit_code=code,
                  expected_exit_code=expected, expectation_met=code == expected,
                  direct_child_pid=child.pid, direct_child_waited=True,
                  descendant_or_global_process_inventory=False,
                  scope='compiler only; no loader/guest/VM/cache/scope/construct/writer dispatch',
                  output={n: dict(bytes=(folder/n).stat().st_size,
                                  sha256=digest((folder/n).read_bytes())) for n in ['stdout', 'stderr']})
    (folder / 'receipt.json').write_text(json.dumps(record, indent=2, sort_keys=True)+'\n')
    assert code == expected, (name, code)
    return folder


def main():
    assert not (HERE / 'seal.json').exists(), 'Frozen packet must not be replayed in place'
    assert digest((BASE/'seal.json').read_bytes()) == 'e006b90b8c9e351e0d4dd504c6de309e2c7970b628fe9fc4f788cb30e77bedf7'
    base_members = members(BASE/'source/vm')
    assert len(base_members) == 144 and digest(canonical(base_members)) == TREE
    scratch = HERE / 'owned-work'
    assert not scratch.exists()
    scratch.mkdir()
    try:
        vm = scratch/'vm'
        shutil.copytree(BASE/'source/vm', vm)
        scaffold = (HERE/'driver.inc.rs').read_bytes()
        with (vm/PROFILE).open('ab') as f:
            f.write(b'\n\n'+scaffold)
        source_members = members(vm)
        write('source-manifest.json', dict(schema=1, base_tree_sha256=TREE,
              source_tree_sha256=digest(canonical(source_members)), members=source_members,
              copied_members=144, altered_existing_members=[PROFILE],
              added_distribution_members=0, source145_qualified=False,
              new_driver_identity_separate_from_historical_host11=True,
              source_scope='accepted funding144 plus private cfg(test) leaf only; no runtime'))
        env = dict(PATH='/usr/bin:/bin', TMPDIR=str(scratch), CARGO_MANIFEST_DIR=str(vm), RUSTC_BOOTSTRAP='1')
        version = command('compiler-version', [str(RUSTC), '--version', '--verbose'], env, 0)
        flags = [str(RUSTC), '--crate-name', 'mixer_vm', '--edition=2021', '--target', 'aarch64-apple-darwin',
                 '-C', 'opt-level=0', '-C', 'overflow-checks=yes', '-C', 'panic=unwind',
                 '-Zmir-opt-level=0', '-Zmir-include-spans=yes',
                 '--cfg', 'feature="experimental-swift-reactor"',
                 '--cfg', 'feature="experimental-swift-wasi"',
                 '--cfg', 'feature="experimental-stream-validation"',
                 '--cfg', 'feature="experimental-function-cache"', '--test', str(vm/'src/lib.rs')]
        mir = scratch/'candidate.mir'
        command('leaf-metadata-mir', flags+['--emit=metadata='+str(scratch/'candidate.rmeta')+',mir='+str(mir)], env, 0)
        text = mir.read_text()
        marker = '\nfn '
        # MIR function may carry its fully qualified path; use line-level start.
        start = text.rfind('\n', 0, text.index('run_one_loaded_fixture_v1'))+1
        end = text.find(marker, start+1)
        fn = text[start:end if end != -1 else len(text)]
        assert fn.startswith('fn ') and 'run_one_loaded_fixture_v1(' in fn
        (HERE/'driver.mir').write_text(fn)
        header = fn.split('\n',1)[0]
        # This is compiler output inventory, not syntax-based release permission.
        match = re.fullmatch(r'fn .*\((.*)\) -> (.*) \{', header)
        assert match, header
        parameters = re.findall(r'(_\d+): (.*?)(?=, _\d+:|$)', match[1])
        roles = [dict(local=local, kind='parameter', compiler_type=ty) for local,ty in parameters]
        roles += [dict(local=local, kind='return-place' if local == '_0' else 'local-or-temporary', compiler_type=ty)
                  for local,ty in re.findall(r'^\s+let (?:mut )?(_\d+): (.*?);', fn, flags=re.M)]
        assert len({r['local'] for r in roles}) == len(roles)
        types = sorted({r['compiler_type'] for r in roles})
        # Fresh exact layout queries compile in this same module/type context.
        # Each intended E0308 reports its evaluated actual usize array length.
        # No executable/link output is requested or run.
        prefix = '''\n#[cfg(test)]\nmod bootstrap_leaf_layout_queries_v1 {\nuse super::*;\nuse crate::experimental_swift_reactor::control::*;\nuse crate::experimental_swift_reactor::retained_profile_loader_v1::*;\nuse crate::experimental_swift_reactor::{control,retained_profile_loader_v1};\nuse crate::experimental_swift_reactor::cache::initial_profile_v1;\nuse crate::execute;\nuse crate::Cancellation;\nuse std::time::Instant;\n'''
        # MIR identities with private module names resolve through these imports.
        queries = ''.join(f'const LEAF_QUERY_{i}: [(); 0] = [(); std::mem::size_of::<{ty}>()];\n' for i,ty in enumerate(types) if ty != '()')
        with (vm/PROFILE).open('a') as f:
            f.write(prefix+queries+'}\n')
        lib = vm/'src/lib.rs'
        lib.write_text('#![feature(never_type)]\n'+lib.read_text())
        layout_members = members(vm)
        write('layout-source-manifest.json', dict(schema=1, source_tree_sha256=digest(canonical(layout_members)),
              members=layout_members, scope='same source plus compile-only actual-type size queries'))
        folder = command('leaf-layout-queries', flags+['--emit=metadata='+str(scratch/'layouts.rmeta')], env, 1)
        errors = (folder/'stderr').read_text()
        sizes = {'()': 0}
        for i,ty in enumerate(types):
            if ty == '()': continue
            # rustc prints the expression identifier on the source excerpt and
            # the evaluated length in the following explanatory note.
            block = errors.split('const LEAF_QUERY_'+str(i)+':', 1)[1].split('\nerror[',1)[0]
            measured = re.search(r'found one with a size of (\d+)', block)
            assert measured, (i,ty,block)
            sizes[ty] = int(measured[1])
        assert errors.count('error[E0308]') == sum(ty != '()' for ty in types)
        for role in roles: role['bytes'] = sizes[role['compiler_type']]
        write('driver-inventory.json', dict(schema=1, target='aarch64-apple-darwin',
              compiler_version=(version/'stdout').read_text(), compiler_sha256=digest(RUSTC.read_bytes()),
              source_tree_sha256=digest(canonical(source_members)),
              scaffold_sha256=digest(scaffold), driver_mir_sha256=digest(fn.encode()),
              role_count=len(roles), logical_source_object_union_bytes=sum(r['bytes'] for r in roles),
              parameters=len(parameters), roles=roles, actual_type_sizes=sizes,
              zero_test_registration=True, zero_product_runtime_dispatch=True,
              no_WASI_attachment=True, old_H_81327_and_external_163_roles_reused=False,
              fresh_compiler_role_inventory=True, physical_stack_RSS_CPU_bound=False,
              whole_launcher_inventory_or_authority_qualified=False,
              product_common_selected_or_dispatch_corrections_qualified=False,
              final_composed_source_layout_rebinding_pending=True))
    finally:
        shutil.rmtree(scratch)
        write('compiler-cleanup.json', dict(schema=1, owned_scratch_removed=not scratch.exists(),
              product_executables_created=0, product_executables_executed=0,
              native_simulator_emulator_UI_capture_started=False,
              global_process_inventory=False, other_projects_inspected_or_changed=False,
              scope='Direct compiler children waited; only owned scratch directory removed.'))


if __name__ == '__main__':
    main()
