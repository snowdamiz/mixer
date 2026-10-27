#!/usr/bin/env python3
"""Prepare, then (only after root authorization) run one bounded LLVM query.

No linked executable or runtime. Preparation has no compiler invocation.
"""
from pathlib import Path
import datetime, gzip, hashlib, json, os, shutil, signal, subprocess, sys, time
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PROVIDER = ROOT / 'verification/swift-guarded-snapshot-owned-binding-provider'
INDEPENDENT = ROOT / 'verification/swift-guarded-snapshot-owned-provider-independent'
PROFILE = 'src/experimental_swift_reactor/cache/initial_profile_v1.rs'
SCRATCH = HERE / 'owned-work/capture-layout'
CMD = HERE / 'commands/capture-layout'
COMPILER = Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
TREE = 'acce2edaeb41d2e032cd9417897f828caa1c713721e162d2f455663600076e3d'
TYPES = [
    ('option_usize', 'Option<usize>'),
    ('result_usize', 'Result<usize, CandidateShapeRefusalV1>'),
    ('residual', 'Result<std::convert::Infallible, CandidateShapeRefusalV1>'),
    ('control_flow', 'std::ops::ControlFlow<Result<std::convert::Infallible, CandidateShapeRefusalV1>, usize>'),
    ('range', 'std::ops::Range<usize>'),
    ('slice_ref', "&'static [u8]"),
    ('path_ref', "&'static std::path::Path"),
    ('osstr_ref', "&'static std::ffi::OsStr"),
    ('slice_header_ref', "&'static &'static [u8]"),
    ('retained_array_ref', "&'static [&'static [u8]; 5]"),
    ('identity_ref', "&'static super::ImmutableIdentityPreimageV1<'static>"),
    ('range_ref', "&'static mut std::ops::Range<usize>"),
    ('usize_ref', "&'static usize"),
    ('byte_ref', "&'static u8"),
    ('digest_ref', "&'static [u8; 32]"),
    ('binding', "super::super::ReviewedFixtureBindingV1<'static>"),
    ('identities', "super::ImmutableFixtureIdentitiesV1<'static>"),
    ('preexisting', "super::PreexistingImmutableBindingV1<'static>"),
]
def sha(data): return hashlib.sha256(data).hexdigest()
def canon(obj): return json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()
def write(path, obj): path.write_text(json.dumps(obj, sort_keys=True, indent=2) + '\n')
def row(path, data): return {'path': path, 'bytes': len(data), 'sha256': sha(data)}
def absent(group):
    try: os.killpg(group, 0)
    except ProcessLookupError: return True
    return False
def query_tail():
    return '''
// Inert work/storage query only. Exact production function pointer forces
// code generation of the unchanged function and its actual and_then closure.
#[used]
static OWNED_PROVIDER_LAYOUT_FORCE_V1: for<'p0> fn(
    super::super::ReviewedFixtureBindingV1<'p0>,
    super::ImmutableFixtureIdentitiesV1<'p0>,
    [&'p0 [u8]; 5],
) -> Result<UnqualifiedExistingOwnerCandidateV1<'p0>, CandidateShapeRefusalV1>
    = describe_existing_owner_candidate_v1;
fn owned_provider_remaining_layout_query_v1(
''' + ''.join(f'    _{name}_{op}: [u8; std::mem::{op}_of::<{ty}>()],\n' for name, ty in TYPES for op in ('size', 'align')) + ') {}\n'
def source():
    custody = json.loads((PROVIDER / 'proposed-source-custody.json').read_bytes())
    assert len(custody) == 146
    assert sha(canon([{k: r[k] for k in ('path', 'bytes', 'sha256')} for r in custody])) == TREE
    result = {}
    for item in custody:
        data = (ROOT / item['origin']).read_bytes()
        assert row(item['path'], data) == {k: item[k] for k in ('path', 'bytes', 'sha256')}
        result[item['path']] = data
    fragment = (PROVIDER / 'existing-owner-candidate.inc.rs').read_bytes()
    needle = fragment + b'\n}\n}\n'
    assert result[PROFILE].endswith(needle) and fragment.endswith(b'}\n')
    result[PROFILE] = result[PROFILE][:-len(needle)] + fragment[:-2] + query_tail().encode() + fragment[-2:] + b'\n}\n}\n'
    return result
def prepare():
    assert not (HERE / 'compiler-plan.json').exists(), 'plan already declared'
    assert not SCRATCH.exists() and not CMD.exists()
    result = source()
    (HERE / 'query-layout.inc.rs').write_text(query_tail())
    (HERE / 'query-profile.rs').write_bytes(result[PROFILE])
    manifest = [row(name, data) for name, data in result.items()]
    write(HERE / 'query-source-manifest.json', {'schema': 1, 'members': manifest, 'member_count': len(manifest), 'tree_sha256': sha(canon(manifest))})
    retained = json.loads((INDEPENDENT / 'compiler-plan.json').read_bytes())
    assert sha(COMPILER.read_bytes()) == retained['compiler_sha256']
    argv = [str(COMPILER), '--crate-name', 'mixer_vm', '--edition=2021', '--target', 'aarch64-apple-darwin', '-C', 'opt-level=0', '-C', 'overflow-checks=yes', '-C', 'panic=unwind', '-Zmir-opt-level=0', '-Zprint-type-sizes', '--cfg', 'feature="experimental-swift-reactor"', '--cfg', 'feature="experimental-swift-wasi"', '--cfg', 'feature="experimental-stream-validation"', '--cfg', 'feature="experimental-function-cache"', '--cfg', 'mixer_bootstrap_one_fixture_v1', '--crate-type', 'rlib', str(SCRATCH / 'vm/src/lib.rs'), '-Zmir-include-spans=yes', f'--emit=metadata={SCRATCH}/query.rmeta,mir={SCRATCH}/query.mir,llvm-ir={SCRATCH}/query.ll']
    env = {'CARGO_MANIFEST_DIR': str(SCRATCH / 'vm'), 'PATH': '/usr/bin:/bin', 'RUSTC_BOOTSTRAP': '1', 'SDKROOT': '/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk', 'TMPDIR': str(SCRATCH)}
    plan = {'schema': 1, 'argv': argv, 'environment': env, 'cwd': str(ROOT), 'compiler_path': str(COMPILER), 'compiler_sha256': sha(COMPILER.read_bytes()), 'compiler_version_preimage': retained['compiler_version_preimage'], 'compiler_version_sha256': retained['compiler_version_sha256'], 'compiler_version_scope': 'retained version bound to exact executable bytes; no version process', 'source_revision': retained['source_revision'], 'candidate_tree_sha256': TREE, 'query_tree_sha256': sha(canon(manifest)), 'source_members': len(manifest), 'query_profile': row('query-profile.rs', result[PROFILE]), 'query_tail': row('query-layout.inc.rs', query_tail().encode()), 'runner_sha256': sha(Path(__file__).read_bytes()), 'mode': 'one-production-opt0-LLVM-IR-metadata-MIR-and-print-type-sizes-query', 'compiler_invocations_requested': 1, 'child_timeout_seconds': 55, 'output_limit_bytes': 4194304, 'retries': 0, 'cfg_test': False, 'linked_executable': False, 'runtime_or_native_execution': False, 'forced_exact_production_pointer': "for<'p0> fn(ReviewedFixtureBindingV1<'p0>, ImmutableFixtureIdentitiesV1<'p0>, [&'p0 [u8]; 5]) -> Result<UnqualifiedExistingOwnerCandidateV1<'p0>, CandidateShapeRefusalV1> = describe_existing_owner_candidate_v1", 'missing_aggregate': 'actual anonymous and_then closure with MIR fields native_path_bodies: &[&[u8];5], position: &usize; size/alignment/padding must be observed, never summed', 'named_layout_queries': [{'name': name, 'type': ty, 'observations': ['size', 'align']} for name, ty in TYPES], 'cleanup': 'owned child process group only, reaped; owned scratch removed; no global inventory'}
    write(HERE / 'compiler-plan.json', plan)
    print(json.dumps({'status': 'prepared-no-compiler-invocation', 'plan_sha256': sha((HERE / 'compiler-plan.json').read_bytes()), 'query_tree_sha256': plan['query_tree_sha256'], 'tail_sha256': plan['query_tail']['sha256'], 'runner_sha256': plan['runner_sha256'], 'named_layout_queries': len(TYPES)}))
def run():
    plan = json.loads((HERE / 'compiler-plan.json').read_bytes())
    authorization = json.loads((HERE / 'compiler-root-authorization.json').read_bytes())
    assert authorization['plan_sha256'] == sha((HERE / 'compiler-plan.json').read_bytes()) and authorization['authorized_invocations'] == 1
    assert sha(Path(__file__).read_bytes()) == plan['runner_sha256']
    assert not CMD.exists() and not SCRATCH.exists(), 'no retry or reuse'
    assert sha(COMPILER.read_bytes()) == plan['compiler_sha256']
    result = source()
    manifest = [row(name, data) for name, data in result.items()]
    assert sha(canon(manifest)) == plan['query_tree_sha256']
    SCRATCH.mkdir(parents=True); CMD.mkdir(parents=True)
    for name, data in result.items():
        dest = SCRATCH / 'vm' / name; dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(data)
    started = datetime.datetime.now(datetime.timezone.utc).isoformat(); begin = time.monotonic()
    child = None; timed_out = False; excessive = False; error = None; artifacts = []; signals = []
    try:
        with (CMD / 'stdout').open('wb') as out, (CMD / 'stderr').open('wb') as err:
            child = subprocess.Popen(plan['argv'], cwd=ROOT, env=plan['environment'], stdout=out, stderr=err, start_new_session=True)
            while child.poll() is None:
                timed_out = time.monotonic() - begin >= 55
                excessive = sum((CMD / n).stat().st_size for n in ('stdout', 'stderr')) > 4194304
                if timed_out or excessive:
                    os.killpg(child.pid, signal.SIGTERM); signals.append('SIGTERM')
                    try: child.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        os.killpg(child.pid, signal.SIGKILL); signals.append('SIGKILL'); child.wait(timeout=2)
                    break
                time.sleep(.02)
            child.wait(timeout=2)
        if not absent(child.pid):
            os.killpg(child.pid, signal.SIGTERM); signals.append('post-terminal SIGTERM')
            until = time.monotonic() + 1
            while not absent(child.pid) and time.monotonic() < until: time.sleep(.02)
            if not absent(child.pid): os.killpg(child.pid, signal.SIGKILL); signals.append('post-terminal SIGKILL')
        for name in ('query.rmeta', 'query.mir', 'query.ll'):
            path = SCRATCH / name
            if path.exists():
                data = path.read_bytes(); item = row(name, data)
                if name != 'query.rmeta':
                    compressed = gzip.compress(data, mtime=0); (CMD / (name + '.gz')).write_bytes(compressed)
                    item.update(gzip_sha256=sha(compressed), gzip_bytes=len(compressed))
                artifacts.append(item)
    except BaseException as exc: error = repr(exc)
    finally:
        if child is not None and child.poll() is None:
            os.killpg(child.pid, signal.SIGKILL); signals.append('finally SIGKILL'); child.wait(timeout=2)
        group_absent = child is not None and absent(child.pid)
        if SCRATCH.exists(): shutil.rmtree(SCRATCH)
        receipt = plan | {'started_at': started, 'finished_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'elapsed_seconds': time.monotonic() - begin, 'compiler_invocations': int(child is not None), 'owned_pid': None if child is None else child.pid, 'owned_pgid': None if child is None else child.pid, 'exit_code': None if child is None else child.returncode, 'timed_out': timed_out, 'output_exceeded': excessive, 'exception': error, 'child_reaped': child is not None and child.returncode is not None, 'owned_group_absent': group_absent, 'owned_scratch_removed': not SCRATCH.exists(), 'cleanup_signals': signals, 'artifacts': artifacts, 'python_version': sys.version}
        for name in ('stdout', 'stderr'): receipt[name] = row(name, (CMD / name).read_bytes())
        receipt['success'] = error is None and child is not None and child.returncode == 0 and not timed_out and not excessive and group_absent and not SCRATCH.exists() and len(artifacts) == 3
        write(CMD / 'receipt.json', receipt)
        print(json.dumps({k: receipt[k] for k in ('success', 'elapsed_seconds', 'exit_code', 'timed_out', 'owned_group_absent', 'owned_scratch_removed', 'exception')}))
    return 0 if receipt['success'] else 1
if __name__ == '__main__':
    if sys.argv[1:] == ['--prepare']: prepare()
    elif sys.argv[1:] == ['--run-root-authorized']: raise SystemExit(run())
    else: raise SystemExit('use --prepare or --run-root-authorized')
