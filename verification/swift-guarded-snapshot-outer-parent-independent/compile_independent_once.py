#!/usr/bin/env python3
"""Independent one-shot production metadata/MIR recorder; never executes product code."""
import datetime
import gzip
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
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT / 'verification/swift-guarded-snapshot-outer-parent-source'
FROZEN = ROOT / 'verification/swift-guarded-snapshot-host-composition'
BASE = ROOT / 'verification/swift-guarded-snapshot-funding-implementation/source/vm'
WORK = HERE / 'owned-work/compiler-metadata-mir'
OUT = HERE / 'commands/compiler-metadata-mir'
PROFILE = 'src/experimental_swift_reactor/cache/initial_profile_v1.rs'
ACCOUNT = 'src/experimental_swift_reactor/cache/initial_profile_v1/host_account_v1.rs'
RUSTC = Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')

def sha(data): return hashlib.sha256(data).hexdigest()
def canonical(obj): return json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()
def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n')
def row(name, data): return dict(path=name, bytes=len(data), sha256=sha(data))

def context():
    assert sha((PRODUCER/'seal.json').read_bytes()) == '3936c73a0f3558000834c92c3ade9822465069492740a954765cb775684bcb57'
    old = json.loads((FROZEN/'source-manifest.json').read_bytes())
    source = {}
    for member in old['members']:
        name = member['path']
        path = FROZEN/'overlay/vm'/name
        if not path.is_file(): path = BASE/name
        source[name] = path.read_bytes()
        assert row(name, source[name]) == member
    source[PROFILE] = (PRODUCER/'overlay/vm'/PROFILE).read_bytes()
    candidate = [row(n, source[n]) for n in sorted(source, key=Path)]
    assert candidate == json.loads((PRODUCER/'source-manifest.json').read_bytes())['members']
    assert sha(canonical(candidate)) == '27deefde4b492bab2e2d5a28da9ae749cc4ae51094e0fca30154d044097988a3'
    snippet = (PRODUCER/'outer-parent.inc.rs').read_bytes()
    assert snippet.endswith(b'}\n') and source[PROFILE].count(snippet) == 1
    tails = {}
    for name in ['query-layout.inc.rs', 'query-account-layout.inc.rs']:
        data = (HERE/name).read_bytes()
        assert data == (PRODUCER/name).read_bytes()
        tails[name] = data
    source[PROFILE] = source[PROFILE].replace(snippet, snippet[:-2]+b'\n'+tails['query-layout.inc.rs']+b'}\n', 1)
    source[ACCOUNT] += b'\n'+tails['query-account-layout.inc.rs']
    members = [row(n, source[n]) for n in sorted(source, key=Path)]
    manifest = dict(schema=1, member_count=len(members), members=members, tree_sha256=sha(canonical(members)))
    assert manifest['tree_sha256'] == '11dd778041d13911e656138e75fc3fb3977808afb7e74ec2117b82e1e5709aa4'
    version = (FROZEN/'commands/production-metadata-rustc-version/stdout').read_bytes()
    inherited = json.loads((FROZEN/'commands/production-metadata/receipt.json').read_bytes())
    assert sha(RUSTC.read_bytes()) == inherited['environment']['MIXER_LOADER_COMPILER_SHA256'] == 'dd6f58440b3418aa9157ae3f05d71eecff741ca41bc4eec120e7e8f2d933b9a0'
    assert sha(version) == inherited['environment']['MIXER_LOADER_COMPILER_VERSION_SHA256']
    env = dict(PATH='/usr/bin:/bin', RUSTC_BOOTSTRAP='1', CARGO_MANIFEST_DIR=str(WORK/'vm'), TMPDIR=str(WORK), SDKROOT='/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk')
    argv = [str(RUSTC), '--crate-name', 'mixer_vm', '--edition=2021', '--target', 'aarch64-apple-darwin', '-C', 'opt-level=0', '-C', 'overflow-checks=yes', '-C', 'panic=unwind', '-Zmir-opt-level=0']
    for feature in ['experimental-swift-reactor', 'experimental-swift-wasi', 'experimental-stream-validation', 'experimental-function-cache']:
        argv += ['--cfg', 'feature="'+feature+'"']
    argv += ['--cfg', 'mixer_bootstrap_one_fixture_v1', '--crate-type', 'rlib', str(WORK/'vm/src/lib.rs'), '-Zmir-include-spans=yes', '--emit=metadata='+str(WORK/'query.rmeta')+',mir='+str(WORK/'query.mir')]
    plan = dict(schema=1, argv=argv, environment=env, cwd=str(ROOT), compiler_path=str(RUSTC), compiler_sha256=sha(RUSTC.read_bytes()), compiler_version_preimage=version.decode(), compiler_version_sha256=sha(version), compiler_version_scope='Retained exact executable-byte-bound -vV; no additional compiler/version process', candidate_tree_sha256=sha(canonical(candidate)), query_tree_sha256=manifest['tree_sha256'], source_member_count=146, inert_query_tails=[row(n,d) for n,d in tails.items()], changed_for_inert_queries_only=[PROFILE,ACCOUNT], python_version=sys.version, source_revision='975b2e3ef25255a882e7476780caa2e844ce928d', runner_sha256=sha(Path(__file__).read_bytes()), child_timeout_seconds=60, output_limit_bytes=4194304, product_test_native_runtime=False, cfg_test=False, no_compile_identity_injection=True, retries=0, compiler_invocations_authorized=1, producer_terminal_facts='Unknown exit/elapsed/timeout/PID/group status remain unknown independently of this new query')
    return source, manifest, plan

def owned_group_present(pid):
    try:
        os.killpg(pid, 0)
        return True
    except ProcessLookupError:
        return False

def main():
    source, manifest, plan = context()
    if sys.argv[1:] == ['--plan']:
        assert not OUT.exists() and not WORK.exists()
        write(HERE/'compiler-plan.json', plan)
        write(HERE/'query-source-manifest.json', manifest)
        print(json.dumps(dict(query_tree=manifest['tree_sha256'], plan_sha256=sha((HERE/'compiler-plan.json').read_bytes()), runner_sha256=plan['runner_sha256'], query_observations=44)))
        return
    assert sys.argv[1:] == ['--run-once']
    assert json.loads((HERE/'compiler-plan.json').read_bytes()) == plan
    assert json.loads((HERE/'query-source-manifest.json').read_bytes()) == manifest
    assert not OUT.exists() and not WORK.exists(), 'No repeated or replaced one-shot context'
    OUT.mkdir(parents=True)
    WORK.mkdir(parents=True)
    for name, data in source.items():
        path = WORK/'vm'/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    receipt = dict(plan)
    receipt.update(started_at=datetime.datetime.now(datetime.timezone.utc).isoformat(), state='starting', compiler_invocations=0, artifacts=[], owned_pid=None, owned_pgid=None, exit_code=None, elapsed_seconds=None, timed_out=None, child_reaped=False, owned_group_absent=None, owned_scratch_removed=False, compile_success=False, postprocess_success=False)
    write(OUT/'receipt.json', receipt)
    child = None
    started = time.monotonic()
    try:
        with (OUT/'stdout').open('wb') as stdout, (OUT/'stderr').open('wb') as stderr:
            child = subprocess.Popen(plan['argv'], cwd=ROOT, env=plan['environment'], stdout=stdout, stderr=stderr, start_new_session=True)
            receipt.update(owned_pid=child.pid, owned_pgid=child.pid, state='running', compiler_invocations=1, timed_out=False)
            write(OUT/'receipt.json', receipt)
            try:
                child.wait(timeout=60)
            except subprocess.TimeoutExpired:
                receipt['timed_out'] = True
                os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=5)
            receipt.update(exit_code=child.returncode, elapsed_seconds=time.monotonic()-started, child_reaped=child.poll() is not None)
        # Preserve terminal facts before any extraction/compression can fail.
        receipt['state'] = 'terminal'
        write(OUT/'receipt.json', receipt)
        for name in ['stdout','stderr']:
            data=(OUT/name).read_bytes()
            receipt[name+'_bytes']=len(data)
            receipt[name+'_sha256']=sha(data)
        receipt['compile_success'] = receipt['exit_code'] == 0 and not receipt['timed_out'] and receipt['stdout_bytes']+receipt['stderr_bytes'] <= plan['output_limit_bytes']
        for name in ['query.rmeta', 'query.mir']:
            path=WORK/name
            if path.is_file(): receipt['artifacts'].append(row(name,path.read_bytes()))
        write(OUT/'receipt.json', receipt)
        if receipt['compile_success']:
            data=(WORK/'query.mir').read_bytes()
            with (OUT/'query.mir.gz').open('wb') as dest:
                with gzip.GzipFile(filename='',fileobj=dest,mode='wb',mtime=0) as compressed:
                    compressed.write(data)
            receipt['retained_compressed_mir']=row('query.mir.gz',(OUT/'query.mir.gz').read_bytes())
            wanted=['selected_outer_request_v1','borrow_original_diagnostics_once_v1','observe_borrowed_originals_v1','run_selected_one_fixture_outer_v1','consume_outer_request_v1','outer_parent_layout_query_v1','outer_parent_account_layout_query_v1']
            bodies=re.split(r'(?=^fn |^const |^static )',data.decode(),flags=re.M)
            selected=[body for body in bodies if any(body.startswith('fn '+name+'(') for name in wanted)]
            assert len(selected)==7
            (OUT/'outer-and-query.mir').write_text(''.join(selected))
            rows=[]
            for file_name,fn_name in [('query-layout.inc.rs','outer_parent_layout_query_v1'),('query-account-layout.inc.rs','outer_parent_account_layout_query_v1')]:
                names=re.findall(r'\s+_(\w+): \[u8;', (HERE/file_name).read_text())
                header=next(b.split('\n',1)[0] for b in selected if b.startswith('fn '+fn_name+'('))
                values=[int(n) for n in re.findall(r'_\d+: \[u8; (\d+)\]',header)]
                assert len(names)==len(values)
                rows.extend(dict(query=n,observed=v) for n,v in zip(names,values))
            assert len(rows)==44
            write(OUT/'layouts.json',dict(schema=1,rows=rows,scope='Production-only exact-toolchain concrete inline size/alignment, not native or dynamic backing'))
            receipt['postprocess_success']=True
    except BaseException as error:
        receipt['recorder_or_postprocess_error']=repr(error)
    finally:
        if child is not None:
            if child.poll() is None:
                os.killpg(child.pid,signal.SIGKILL)
                child.wait(timeout=5)
                receipt.update(exit_code=child.returncode,child_reaped=True,forced_finally_kill=True)
            present=owned_group_present(child.pid)
            receipt['owned_group_present_before_cleanup']=present
            if present:
                os.killpg(child.pid,signal.SIGKILL)
                receipt['owned_group_cleanup_signal']='SIGKILL'
            receipt['owned_group_absent']=not owned_group_present(child.pid)
        shutil.rmtree(WORK)
        if WORK.parent.exists() and not any(WORK.parent.iterdir()): WORK.parent.rmdir()
        receipt['owned_scratch_removed']=not WORK.exists()
        receipt['finished_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        receipt['state']='complete'
        write(OUT/'receipt.json',receipt)
    success=receipt['compile_success'] and receipt['postprocess_success'] and receipt['child_reaped'] and receipt['owned_group_absent'] and receipt['owned_scratch_removed']
    print(json.dumps({k:receipt.get(k) for k in ['compile_success','exit_code','elapsed_seconds','timed_out','owned_pid','owned_pgid','child_reaped','owned_group_absent','owned_scratch_removed','postprocess_success','recorder_or_postprocess_error']}))
    if not success: sys.exit(1)

if __name__=='__main__': main()
