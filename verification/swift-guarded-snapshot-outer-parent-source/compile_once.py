#!/usr/bin/env python3
"""Single authorized <=60s compiler-only query; no runtime or automatic retry."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode = True
from prepare import HERE, ROOT, PROFILE, source_data, canonical, row, sha, write

ACCOUNT = 'src/experimental_swift_reactor/cache/initial_profile_v1/host_account_v1.rs'
RUSTC = Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
WORK = HERE/'owned-work/compiler-only-query'
OUT = HERE/'commands/compiler-only-query'

def make_context():
    source, manifest, _, _ = source_data()
    snippet = (HERE/'outer-parent.inc.rs').read_bytes()
    assert snippet.endswith(b'}\n')
    query = (HERE/'query-layout.inc.rs').read_bytes()
    replacement = snippet[:-2]+b'\n'+query+b'}\n'
    assert source[PROFILE].count(snippet) == 1
    source[PROFILE] = source[PROFILE].replace(snippet, replacement, 1)
    source[ACCOUNT] += b'\n'+(HERE/'query-account-layout.inc.rs').read_bytes()
    members = [row(n, source[n]) for n in sorted(source, key=Path)]
    query_manifest = dict(schema=1, member_count=len(members), members=members,
                          tree_sha256=sha(canonical(members)))
    env = dict(PATH='/usr/bin:/bin', RUSTC_BOOTSTRAP='1',
        CARGO_MANIFEST_DIR=str(WORK/'vm'), TMPDIR=str(WORK),
        SDKROOT='/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk')
    argv = [str(RUSTC), '--crate-name', 'mixer_vm', '--edition=2021',
        '--target', 'aarch64-apple-darwin', '-C', 'opt-level=0',
        '-C', 'overflow-checks=yes', '-C', 'panic=unwind', '-Zmir-opt-level=0']
    for feature in ['experimental-swift-reactor', 'experimental-swift-wasi',
                    'experimental-stream-validation', 'experimental-function-cache']:
        argv += ['--cfg', f'feature="{feature}"']
    argv += ['--cfg', 'mixer_bootstrap_one_fixture_v1', '--crate-type', 'rlib',
             str(WORK/'vm/src/lib.rs'), '-Zmir-include-spans=yes',
             f'--emit=metadata={WORK}/query.rmeta,mir={WORK}/query.mir']
    frozen = ROOT/'verification/swift-guarded-snapshot-host-composition'
    original_receipt = json.loads((frozen/'commands/production-metadata/receipt.json').read_bytes())
    compiler_sha = sha(RUSTC.read_bytes())
    assert compiler_sha == original_receipt['environment']['MIXER_LOADER_COMPILER_SHA256']
    version = (frozen/'commands/production-metadata-rustc-version/stdout').read_bytes()
    assert sha(version) == original_receipt['environment']['MIXER_LOADER_COMPILER_VERSION_SHA256']
    context = dict(schema=1, argv=argv, environment=env, cwd=str(ROOT),
        compiler_path=str(RUSTC), compiler_sha256=compiler_sha,
        compiler_version_preimage=version.decode(),
        compiler_version_scope='frozen -vV preimage; same compiler executable bytes freshly rehashed; no new version process',
        candidate_tree_sha256=manifest['tree_sha256'],
        query_tree_sha256=query_manifest['tree_sha256'], query_source_members=146,
        changed_for_query_only=[PROFILE, ACCOUNT], timeout_seconds=60,
        output_limit_bytes=4*1024*1024, no_compile_identity_injection=True,
        loader_runtime_unsupported_without_actual_future_binding=True,
        product_or_test_runtime=False, retries=0)
    return source, query_manifest, context

def main():
    source, manifest, context = make_context()
    if '--describe' in sys.argv:
        print(json.dumps(context, indent=2, sort_keys=True))
        return
    assert '--run-once' in sys.argv
    assert not OUT.exists() and not WORK.exists(), 'no replacement/retry allowed'
    OUT.mkdir(parents=True)
    WORK.mkdir(parents=True)
    for name, data in source.items():
        p = WORK/'vm'/name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    write('commands/compiler-only-query/context.json', context)
    write('commands/compiler-only-query/query-source-manifest.json', manifest)
    started = time.monotonic()
    p = subprocess.Popen(context['argv'], cwd=ROOT, env=context['environment'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    timed_out = False
    try:
        stdout, stderr = p.communicate(timeout=60)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(p.pid, signal.SIGKILL)
        stdout, stderr = p.communicate()
    elapsed = time.monotonic()-started
    (OUT/'stdout').write_bytes(stdout)
    (OUT/'stderr').write_bytes(stderr)
    receipt = dict(context, elapsed_seconds=elapsed, exit_code=p.returncode,
        timed_out=timed_out, child_reaped=p.poll() is not None,
        stdout_bytes=len(stdout), stderr_bytes=len(stderr),
        stdout_sha256=sha(stdout), stderr_sha256=sha(stderr), artifacts=[],
        compiler_invocations=1, product_or_test_runtime=False,
        runner_sha256=sha(Path(__file__).read_bytes()))
    success = p.returncode == 0 and not timed_out and len(stdout)+len(stderr) <= context['output_limit_bytes']
    receipt['compile_success'] = success
    for path in [WORK/'query.rmeta', WORK/'query.mir']:
        if path.exists():
            receipt['artifacts'].append(dict(path=path.name, bytes=path.stat().st_size, sha256=sha(path.read_bytes()), retained=False))
    try:
        if success:
            mir = (WORK/'query.mir').read_text()
            selected = []
            names_to_retain = ['selected_outer_request_v1', 'borrow_original_diagnostics_once_v1',
                'observe_borrowed_originals_v1', 'run_selected_one_fixture_outer_v1',
                'consume_outer_request_v1', 'outer_parent_layout_query_v1',
                'outer_parent_account_layout_query_v1']
            for body in re.split(r'(?=^fn |^const |^static )', mir, flags=re.M):
                header = body.split('\n', 1)[0]
                if any(header.startswith('fn '+name+'(') for name in names_to_retain):
                    selected.append(body)
            assert len(selected) == len(names_to_retain), 'all exact private outer/query MIR bodies required'
            (OUT/'outer-and-query.mir').write_text(''.join(selected))
            layouts = []
            for file_name, fn_name in [('query-layout.inc.rs', 'outer_parent_layout_query_v1'),
                                       ('query-account-layout.inc.rs', 'outer_parent_account_layout_query_v1')]:
                decl = (HERE/file_name).read_text()
                names = re.findall(r'\s+_(\w+): \[u8;', decl)
                header = next(body.split('\n',1)[0] for body in selected if body.startswith('fn '+fn_name+'('))
                values = [int(n) for n in re.findall(r'_\d+: \[u8; (\d+)\]', header)]
                assert len(names) == len(values), (names, values)
                layouts += [dict(query=name, observed=value) for name, value in zip(names, values)]
            write('commands/compiler-only-query/layouts.json', dict(schema=1, rows=layouts,
                observed_by='concrete array lengths in exact rustc MIR query signatures',
                target='aarch64-apple-darwin', compiler_only=True,
                actual_native_or_dynamic_backing_bound=False))
    except Exception as error:
        receipt['postprocess_error'] = str(error)
        success = False
    finally:
        try:
            os.killpg(p.pid, 0)
            owned_group_absent = False
        except ProcessLookupError:
            owned_group_absent = True
        receipt['owned_group_absent'] = owned_group_absent
        shutil.rmtree(WORK)
        if WORK.parent.exists() and not any(WORK.parent.iterdir()): WORK.parent.rmdir()
        receipt['owned_scratch_removed'] = not WORK.exists()
        receipt['postprocess_success'] = success
        write('commands/compiler-only-query/receipt.json', receipt)
    print(json.dumps(dict(compile_success=success, exit_code=p.returncode,
        elapsed_seconds=elapsed, compiler_invocations=1,
        owned_group_absent=owned_group_absent, owned_scratch_removed=not WORK.exists(),
        source_tree_sha256=context['candidate_tree_sha256'],
        query_tree_sha256=context['query_tree_sha256'], actual_runtime=False)))
    if not success: sys.exit(1)

if __name__ == '__main__': main()
