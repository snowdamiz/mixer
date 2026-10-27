"""Independent exact146 custody, compile and focused synthetic interaction review.

All writes are confined to this directory. No real fixture or product runtime is
dispatched. Compiler/test children are isolated, capped and terminally reaped.
"""
from pathlib import Path
from collections import Counter
import argparse
import gzip
import hashlib
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

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
V = ROOT / 'verification'
P = V / 'swift-guarded-snapshot-host-composition'
BASE = V / 'swift-guarded-snapshot-funding-implementation'
COMBINED = V / 'swift-guarded-snapshot-combined-source'
ACCOUNT_PACKET = V / 'swift-guarded-snapshot-host-account-entry'
BOOT = V / 'swift-guarded-snapshot-bootstrap-host-boundary'
SUPPORT = V / 'swift-real-profile-loader-binding'
PROFILE = 'src/experimental_swift_reactor/cache/initial_profile_v1.rs'
ACCOUNT = 'src/experimental_swift_reactor/cache/initial_profile_v1/host_account_v1.rs'
CONTROL = 'src/experimental_swift_reactor/control.rs'
LOADER = 'src/experimental_swift_reactor/retained_profile_loader_v1.rs'
HELPER = 'src/experimental_swift_reactor/cache/initial_profile_v1/emission_bound_v1.rs'
TREE = '690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185'
HOST_TREE = '027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2'
KEYS = ['MIXER_LOADER_MANIFEST_SHA256', 'MIXER_LOADER_COMMAND_SHA256',
        'MIXER_LOADER_COMPILE_ENV_SHA256', 'MIXER_LOADER_COMPILER_SHA256',
        'MIXER_LOADER_COMPILER_VERSION_SHA256']
RUSTC = Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
SDK = Path('/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk')
FEATURES = ['experimental-swift-reactor', 'experimental-swift-wasi',
            'experimental-stream-validation', 'experimental-function-cache']

def sha(data): return hashlib.sha256(data).hexdigest()
def canonical(value): return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
def read(path): return json.loads(path.read_bytes())
def row(name, data): return dict(path=str(name), bytes=len(data), sha256=sha(data))
def identity(path): return row(path, path.read_bytes())
def write(name, value):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
def roster(source):
    rows = [row(name, source[name]) for name in sorted(source, key=Path)]
    return dict(schema=1, members=rows, member_count=len(rows), tree_sha256=sha(canonical(rows)))
def checked(path, expected):
    data = path.read_bytes()
    assert sha(data) == expected, path
    return json.loads(data)
def checked_seal(folder, expected):
    sealed = checked(folder/'seal.json', expected)
    assert len(sealed['members']) == sealed['member_count']
    for item in sealed['members']:
        assert row(item['path'], (folder/item['path']).read_bytes()) == item, item
    return dict(path=str(folder.relative_to(ROOT)), seal_sha256=expected,
        members=len(sealed['members']), bytes=sum(item['bytes'] for item in sealed['members']))
def reconstruct(folder, base):
    manifest = read(folder/'source-manifest.json')
    result = {}
    for item in manifest['members']:
        name = item['path']
        candidate = base.get(name)
        if candidate is None or row(name, candidate) != item:
            candidate = (folder/'overlay/vm'/name).read_bytes()
        assert row(name, candidate) == item
        result[name] = candidate
    return result
def inputs():
    release = checked(V/'swift-semantic-adapter-root-review/guarded-snapshot-host-composition-independent-release.json',
        '2d3170946aca8385fd5cb147b653ac26e7813f19be5a801337834366753fee51')
    custody = [checked_seal(folder, digest) for folder, digest in [
        (P, '2fc002b2598effdc70a74ecfa3da775b4aa82f2572cbbb93650207925238dc2e'),
        (COMBINED, '2eb3dab82f2b492b491e9f80e1d05fb0f8745e41c452f4f3bc777a33b62e8bdc'),
        (ACCOUNT_PACKET, '6e8c8e2d8dde62e2e35fe2e8fb1a851a342d8d95f8c71facd938416ac3e153e3'),
        (BOOT, '00f5bf754a13317ac18dd9959a1db4a9b025b16c72fc99a9d4cfddfcc7cb4dba')]]
    checked(BASE/'seal.json', 'e006b90b8c9e351e0d4dd504c6de309e2c7970b628fe9fc4f788cb30e77bedf7')
    rows = read(BASE/'source-manifest.json')['members']
    base = {r['path']: (BASE/'source/vm'/r['path']).read_bytes() for r in rows}
    assert roster(base)['members'] == rows and len(base) == 144
    assert roster(base)['tree_sha256'] == '7e3e861ca65d8c6359623443d6a7810b878c1029494a0ae557307d35ed43484b'
    combined = reconstruct(COMBINED, base)
    assert len(combined) == 145
    account145 = dict(base)
    appends = b'\n\n' + (BOOT/'driver.inc.rs').read_bytes() + b'\n\n' + (ACCOUNT_PACKET/'entry.inc.rs').read_bytes()
    account145[PROFILE] += appends
    account145[ACCOUNT] = (ACCOUNT_PACKET/'host_account.rs').read_bytes()
    assert roster(account145)['members'] == read(ACCOUNT_PACKET/'source-manifest.json')['members']
    exact = reconstruct(P, base)
    expected = dict(combined)
    expected[PROFILE] += appends
    expected[ACCOUNT] = account145[ACCOUNT]
    before, after = b'if word(b, 32) != 145\n', b'if word(b, 32) != 146\n'
    assert expected[LOADER].count(before) == 1
    expected[LOADER] = expected[LOADER].replace(before, after, 1)
    assert exact == expected
    assert set(exact) == set(combined) | set(account145)
    assert len(exact) == 146 and roster(exact)['tree_sha256'] == TREE
    assert exact[CONTROL] == combined[CONTROL]
    assert exact[HELPER] == combined[HELPER]
    delta = sum(len(v) for v in exact.values()) - sum(len(v) for v in combined.values())
    assert delta == 24052 and len(appends) == 8521 and len(exact[ACCOUNT]) == 15531
    assert len(exact[LOADER]) == len(combined[LOADER])
    host = {r['path']: (SUPPORT/'host'/r['path']).read_bytes() for r in read(P/'host-support-manifest.json')['members']}
    assert roster(host) == read(P/'host-support-manifest.json')
    assert len(host) == 11 and roster(host)['tree_sha256'] == HOST_TREE
    assert sum(v.count(b'checked_snapshot_emission_bound_v1') for k, v in exact.items() if k != HELPER) == 0
    assert b'Err(AError::WorkAuditPending)' in exact[PROFILE]
    for name in [b'RootPolicyPending', b'WholeQuotePending']:
        assert b'Err(RefusalV1::' + name + b')' in exact[ACCOUNT]
    for binding in read(P/'input-bindings.json')['releases']:
        checked(ROOT/binding['path'], binding['sha256'])
    return exact, host, dict(schema=1, release=release, custody=custody,
        source=roster(exact), host_support=roster(host), union_count=146,
        exact_union_and_only_appends_and_loader_count_verified=True,
        account_bytes=15531, appends_bytes=8521, total_delta_bytes=delta,
        funding_full_packet_reverified=False, funding_source_members_verified=144)

def packed(values):
    values = [os.fsencode(v) for v in values]
    return struct.pack('<Q', len(values)) + b''.join(struct.pack('<Q', len(v)) + v for v in values)
def packed_env(env):
    return packed([os.fsencode(k)+b'='+os.fsencode(v) for k, v in sorted(env.items(), key=lambda p: os.fsencode(p[0]))])

def testing_source(source):
    result = dict(source)
    assert result[PROFILE].endswith(b'\n}\n')
    result[PROFILE] = result[PROFILE][:-2] + (P/'entry-cycle-test-bridge.inc.rs').read_bytes() + b'}\n'
    for name, fragments in [
        (PROFILE, ['profile-tests.inc.rs', 'profile-cycle-test-bridge.inc.rs']),
        (ACCOUNT, ['account-cycle-tests.inc.rs']),
        ('src/experimental_swift_reactor/cache.rs', ['cache-tests.inc.rs', 'cache-cycle-test-bridge.inc.rs']),
        ('src/experimental_swift_reactor/control_tests.rs', ['interaction-tests.inc.rs', 'control-account-tests.inc.rs'])]:
        result[name] += b''.join((P/f).read_bytes() for f in fragments)
    assert roster(result) == read(P/'test-overlay-manifest.json')['source']
    return result

def audit():
    source, hosts, custody = inputs()
    testing = testing_source(source)
    builds = []
    for folder in sorted((P/'preimages').iterdir()):
        label = folder.name
        closure_data = (folder/'manifest.json').read_bytes()
        closure = json.loads(closure_data)
        rec = read(P/'commands'/label/'receipt.json')
        binding = read(folder/'binding.json')
        argv = (folder/'argv.bin').read_bytes()
        env = (folder/'environment.bin').read_bytes()
        version = (folder/'compiler-version.txt').read_bytes()
        assert argv == packed(rec['argv'])
        assert env == packed_env({k:v for k,v in rec['environment'].items() if k not in KEYS})
        compiler = closure.get('tools', {}).get('rustc', closure.get('compiler'))
        assert identity(Path(compiler['path'])) == compiler
        expected = dict(zip(KEYS, [sha(closure_data), sha(argv), sha(env), compiler['sha256'], sha(version)]))
        assert expected == binding['compile_identity_keys'] == {k:rec['environment'][k] for k in KEYS}
        assert binding['source_members'] == 146 and binding['host_support_members'] == 11
        assert binding['distribution_source_tree_sha256'] == TREE
        assert binding['host_support_tree_sha256'] == HOST_TREE
        assert closure['host_support'] == roster(hosts)
        if label.startswith('privacy-'):
            actual = {'host_account.rs': source[ACCOUNT], 'driver.rs': (P/(label+'.rs')).read_bytes()}
            assert closure['distribution_source'] == roster(source)
            assert closure['compiled_source'] == roster(actual)
        else:
            assert closure['distribution'] == roster(source)
            assert closure['compiled_source'] == roster(testing if label.startswith('interactions-') else source)
            assert 'mixer_bootstrap_one_fixture_v1' in rec['argv']
        orchestration = closure.get('orchestration', [])
        if isinstance(orchestration, dict): orchestration = [orchestration]
        for item in orchestration:
            assert identity(Path(item['path'])) == item
        tools = closure.get('tools', {})
        for key in ['python', 'cc']:
            if key in tools: assert identity(Path(tools[key]['path'])) == tools[key]
        for item in tools.get('SDK_headers', []): assert identity(Path(item['path'])) == item
        builds.append(dict(label=label, manifest_sha256=sha(closure_data), compile_identity_keys=expected,
            distribution_tree=TREE, host_tree=HOST_TREE, source_host_tests_tools_orchestration_separate=True))
    receipts = []
    for folder in sorted((P/'commands').iterdir()):
        rec = read(folder/'receipt.json')
        assert rec['expectation_met'] and rec['exit_code'] == rec['expected_exit_code']
        assert rec['owned_group_absent'] and rec['child_reaped'] and not rec['timed_out_or_output_limited']
        for stream in ['stdout', 'stderr']:
            assert sha((folder/stream).read_bytes()) == rec[stream+'_sha256']
        if rec['required_output']:
            assert rec['required_output'].encode() in (folder/'stdout').read_bytes()+(folder/'stderr').read_bytes()
        receipts.append(dict(label=folder.name, expected_exit=rec['expected_exit_code'], verified=True))
    assert len(builds) == 9 and len(receipts) == 19
    for label in ['production-metadata', 'interactions-debug', 'interactions-optimized']:
        clean = read(P/'commands'/label/'cleanup.json')
        artifact = read(P/'commands'/label/'artifact.json')
        assert clean['completed'] and clean['owned_scratch_removed'] and clean['recorded_owned_groups_absent']
        assert artifact['bytes'] > 0 and artifact['nonempty'] and not Path(artifact['path']).exists()
    assert read(P/'commands/production-metadata/artifact.json')['bytes'] == 25579436
    assert read(P/'privacy-cleanup.json')['owned_scratch_removed']
    assert not (P/'owned-work').exists() and not (P/'owned-privacy-work').exists()
    write('input-custody.json', custody)
    write('producer-audit.json', dict(schema=1, builds=builds, identity_keys=45, command_receipts=receipts,
        metadata_bytes=25579436, tests_each_mode=17, negative_controls=5, positive_controls=1,
        source145_quote_applies_to146=False, work_quote_fullquote_P0_policy_not_authorized=True))
    print(json.dumps(dict(audit='passed', source_members=146, producer_keys=45, producer_receipts=19)), flush=True)

def absent(group):
    try: os.killpg(group, 0); return False
    except ProcessLookupError: return True
def command(label, argv, env, expected=0, required=None, cap=180):
    folder = HERE/'commands'/label
    folder.mkdir(parents=True, exist_ok=False)
    start = time.monotonic(); limited = False; actions = []
    with (folder/'stdout').open('wb') as out, (folder/'stderr').open('wb') as err:
        child = subprocess.Popen([str(v) for v in argv], cwd=ROOT, env=env,
            stdout=out, stderr=err, start_new_session=True)
        try:
            while child.poll() is None:
                if time.monotonic()-start > cap or out.tell()+err.tell() > 16*1024*1024:
                    limited = True
                    os.killpg(child.pid, signal.SIGTERM); actions.append('TERM at owned time/output cap')
                    try: child.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        os.killpg(child.pid, signal.SIGKILL); actions.append('KILL after owned grace cap')
                    break
                time.sleep(.05)
        finally:
            code = child.wait(timeout=3)
            if not absent(child.pid):
                os.killpg(child.pid, signal.SIGTERM); actions.append('TERM owned surviving descendants')
                deadline = time.monotonic()+2
                while not absent(child.pid) and time.monotonic() < deadline: time.sleep(.05)
                if not absent(child.pid):
                    os.killpg(child.pid, signal.SIGKILL); actions.append('KILL owned surviving descendants')
                    deadline = time.monotonic()+2
                    while not absent(child.pid) and time.monotonic() < deadline: time.sleep(.05)
    stdout = (folder/'stdout').read_bytes(); stderr = (folder/'stderr').read_bytes()
    passed = code == expected and not limited and absent(child.pid)
    if required: passed = passed and required.encode() in stdout+stderr
    rec = dict(schema=1, argv=[str(v) for v in argv], environment=env, cwd=str(ROOT),
        exit_code=code, expected_exit_code=expected, required_output=required,
        timeout_seconds=cap, output_cap_bytes=16*1024*1024, elapsed_seconds=time.monotonic()-start,
        owned_process_group=child.pid, child_reaped=True, owned_group_absent=absent(child.pid),
        timed_out_or_output_limited=limited, cleanup_actions=actions,
        stdout=row('stdout', stdout), stderr=row('stderr', stderr), expectation_met=passed,
        runner=identity(Path(__file__)), global_process_inventory=False)
    write('commands/'+label+'/receipt.json', rec)
    print(json.dumps(dict(label=label, exit_code=code, passed=passed, elapsed_seconds=rec['elapsed_seconds'])), flush=True)
    assert passed, (label, stdout[-1000:], stderr[-3500:])
    return stdout, stderr

def normalize(text):
    text = re.sub(r'/Users/andreyyurlov/Documents/dev/mixer/verification/[^ :@,{}]+/vm/', '<VM>/', text)
    return re.sub(r'(?<=\.rs):\d+:\d+: \d+:\d+', ':<SPAN>', text)
def functions(text):
    for match in re.finditer(r'^fn .+ \{$', text, re.M):
        yield text[match.start():text.index('\n}\n', match.start())+3]
def body(text):
    return '\n'.join(line.split('//', 1)[0].rstrip() for line in normalize(text).splitlines())
def roles(fn):
    match = re.fullmatch(r'fn [^(]+\((.*)\) -> (.*) \{', fn.split('\n', 1)[0])
    assert match
    result = [dict(local=n, kind='parameter', compiler_type=t)
        for n,t in re.findall(r'(_\d+): (.*?)(?=, _\d+:|$)', match[1])]
    result += [dict(local=n, kind='return-place' if n=='_0' else 'local-or-temporary', compiler_type=t)
        for n,t in re.findall(r'^\s+let (?:mut )?(_\d+): (.*);(?:\s*//[^\n]*)?$', fn, re.M)]
    assert len(result) == len({r['local'] for r in result})
    return result
def inventory(mir, stdout):
    accepted = read(ACCOUNT_PACKET/'caller-inventory.json')
    old = list(functions((ACCOUNT_PACKET/'entry-and-account.mir').read_text()))
    new = {normalize(f.split('\n', 1)[0]):f for f in functions(mir.read_text())}
    selected = []; records = []
    assert len(old) == len(accepted['functions']) == 19
    for original, previous in zip(old, accepted['functions']):
        key = normalize(original.split('\n', 1)[0]); fresh = new[key]
        observed = roles(fresh)
        expected = [{k:r[k] for k in ['local', 'kind', 'compiler_type']} for r in previous['roles']]
        assert normalize(canonical(observed).decode()) == normalize(canonical(expected).decode())
        assert body(original) == body(fresh)
        selected.append(fresh)
        records.append(dict(header=key, roles=len(observed), phase=previous['phase'],
            accepted_bytes=previous['measured_logical_bytes'], identical_normalized_body_and_types=True))
    assert sum(r['roles'] for r in records) == 396
    assert sum(r['accepted_bytes'] for r in records) == 311071
    selected_types = {r['compiler_type'] for fn in selected for r in roles(fn)}
    closures = [(ty, int(size), int(align)) for ty,size,align in re.findall(
        r'print-type-size type: `([^`]+)`: (\d+) bytes, alignment: (\d+) bytes', stdout.decode())
        if '{closure@' in ty and ty in selected_types]
    assert len(closures) == 1 and closures[0][1:] == (8,8), closures
    closure_roles = sum(r['compiler_type']=='impl FnOnce() -> T' or '{closure@' in r['compiler_type']
        for fn in selected for r in roles(fn))
    assert closure_roles == 4
    (HERE/'entry-and-account.mir').write_text('\n'.join(selected))
    write('mir-and-closure.json', dict(schema=1, source_tree=TREE, functions=records,
        function_count=19, roles=396, logical_bytes_pending_fresh_layouts=311071,
        closure=dict(compiler_type=closures[0][0], bytes=8, alignment=8, role_instances=4,
            fresh_actual_compiler_print_type_size=True), no_other_type_layouts_cataloged=True,
        fullquote_or_P0_authority=False))

def layout_source(source):
    accepted = read(ACCOUNT_PACKET/'caller-inventory.json')
    raw_types = sorted({r['compiler_type'] for f in accepted['functions'] for r in f['roles']})
    query = []
    for ty in raw_types:
        if ty == 'impl FnOnce() -> T' or '{closure@' in ty: continue
        # Parameter repair introduced this short spelling. Its exact qualified
        # concrete type is already included in the accepted ninety queries.
        if ty == "ReservationV1<'_>": continue
        resolved = re.sub(r'\bT\b', 'OwnedFixtureOutcomeV1', ty)
        if resolved != '()': query.append(dict(original=ty, concrete=resolved))
    assert len(query) == 90
    prefix = '''\n#[cfg(mixer_bootstrap_one_fixture_v1)]
mod independent_final146_layout_v1 {
use super::*;
use super::super::*;
use crate::experimental_swift_reactor::{control,retained_profile_loader_v1};
use crate::experimental_swift_reactor::cache::initial_profile_v1;
use crate::experimental_swift_reactor;
use crate::{experimental,experimental_wasi};
use crate::execute;
use crate::Cancellation;
'''
    fragment = prefix + ''.join('const FINAL146_LAYOUT_'+str(i)+': [(); usize::MAX] = [(); std::mem::size_of::<'+q['concrete']+'>()];\n'
        for i,q in enumerate(query)) + '}\n'
    result = dict(source)
    result[ACCOUNT] += fragment.encode()
    result['src/lib.rs'] = b'#![feature(never_type)]\n' + result['src/lib.rs']
    (HERE/'layout-queries.inc.rs').write_text(fragment)
    write('layout-query-bindings.json', dict(schema=1, distribution_tree=TREE,
        query_count=90, query=query, actual_outcome_substitution=True,
        fixture_or_binding_constructor_created=False, compiled_source=roster(result)))
    return result
def reconcile_layout(stderr):
    queries = read(HERE/'layout-query-bindings.json')['query']
    accepted = read(ACCOUNT_PACKET/'caller-inventory.json')
    assert stderr.count(b'error[E0308]') == 90
    assert re.findall(rb'error\[E(?!0308)\d+\]', stderr) == []
    sizes = {'()':0}; seen = set(); diagnostics = []
    for block in stderr.decode().split('error[E0308]:')[1:]:
        indices = set(re.findall(r'FINAL146_LAYOUT_(\d+)', block))
        assert len(indices) == 1
        index = int(next(iter(indices))); assert index not in seen; seen.add(index)
        size = int(re.search(r'found one with a size of (\d+)', block)[1])
        ty = queries[index]['concrete']
        assert accepted['actual_type_sizes'][ty] == size, (ty,size,accepted['actual_type_sizes'][ty])
        if ty in sizes: assert sizes[ty] == size
        sizes[ty] = size
        diagnostics.append(dict(index=index, **queries[index], bytes=size))
    assert seen == set(range(90))
    assert sizes == accepted['actual_type_sizes']
    fresh_mir = read(HERE/'mir-and-closure.json')
    phase = {}; total = 0; count = 0; closure_count = 0
    for fn in accepted['functions']:
        measured = 0
        for role in fn['roles']:
            ty = role['compiler_type']
            if ty == 'impl FnOnce() -> T' or '{closure@' in ty:
                size = fresh_mir['closure']['bytes']; closure_count += 1
            else: size = sizes[role['concrete_production_type']]
            assert size == role['bytes']
            measured += size; count += 1
        assert measured == fn['measured_logical_bytes']
        target = phase.setdefault(fn['phase'], dict(roles=0, logical_bytes=0, functions=0))
        target['roles'] += len(fn['roles']); target['logical_bytes'] += measured; target['functions'] += 1
        total += measured
    assert count == 396 and total == 311071 and closure_count == 4
    assert phase['P0-pre-existing-parent-account-bookkeeping']['roles'] == 208
    assert phase['P0-pre-existing-parent-account-bookkeeping']['logical_bytes'] == 234375
    write('fresh-layout-results.json', dict(schema=1, source_tree=TREE, diagnostic_queries=90,
        expected_E0308_only=True, distinct_nonunit_types=len(sizes)-1, actual_type_sizes=sizes,
        queries=diagnostics, closure_bytes=8, closure_roles=4, role_count=count,
        logical_source_object_bytes=total, phases=phase, final146_layout_uncertainty_closed=True,
        aliases_moves_overlap_failure_places_discounted=False,
        dynamic_backing_stack_RSS_allocator_CPU_work_fullquote_P0_authority=False))

def compile_one(mode):
    assert not (HERE/'seal.json').exists()
    source, host, _ = inputs()
    scratch = HERE/'owned-work'/mode
    scratch.mkdir(parents=True, exist_ok=False)
    artifact = scratch/('synthetic.bin' if mode=='synthetic-optimized' else 'output.rmeta')
    completed = False
    try:
        if mode == 'exact146-metadata-mir': actual = source
        elif mode == 'actual90-layout-queries': actual = layout_source(source)
        elif mode == 'synthetic-optimized':
            actual = testing_source(source)
            actual['src/experimental_swift_reactor/control_tests.rs'] += (HERE/'extra-interactions.inc.rs').read_bytes()
        else: raise AssertionError(mode)
        vm = scratch/'vm'
        for name,data in actual.items():
            path = vm/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
        env = dict(PATH='/usr/bin:/bin', TMPDIR=str(scratch), RUSTC_BOOTSTRAP='1', CARGO_MANIFEST_DIR=str(vm), SDKROOT=str(SDK))
        version,_ = command(mode+'-version', [RUSTC,'-vV'], env, required='rustc 1.99.0', cap=10)
        tools = dict(rustc=identity(RUSTC), python=identity(Path(sys.executable).resolve()),
            python_version=sys.version, platform=platform.platform(), cc=identity(Path('/usr/bin/cc')),
            SDK_headers=[identity(SDK/n) for n in ['usr/include/CommonCrypto/CommonDigest.h',
                'usr/include/crt_externs.h', 'usr/include/mach-o/dyld.h', 'usr/include/unistd.h']])
        closure = dict(schema=1, distribution=roster(source), compiled_source=roster(actual), host_support=roster(host),
            tools=tools, orchestration=[identity(Path(__file__)), identity(HERE/'extra-interactions.inc.rs')],
            producer_seal=identity(P/'seal.json'), independent_release=identity(V/'swift-semantic-adapter-root-review/guarded-snapshot-host-composition-independent-release.json'),
            production_typed_route=mode=='exact146-metadata-mir', metadata_or_synthetic_only=True,
            genuine_fixture_loader_VM_cache_scope_construct_writer_execution=False)
        argv = [str(RUSTC), '--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin',
            '-C','opt-level='+('3' if mode=='synthetic-optimized' else '0'),'-C','overflow-checks=yes',
            '-C','panic=unwind','-Zmir-opt-level=0','-Zmir-include-spans=yes']
        for feature in FEATURES: argv += ['--cfg','feature="'+feature+'"']
        argv += ['--cfg','mixer_bootstrap_one_fixture_v1']
        argv += ['--test'] if mode=='synthetic-optimized' else ['--crate-type','rlib']
        argv += [str(vm/'src/lib.rs')]
        if mode == 'synthetic-optimized': argv += ['--emit=link','-o',str(artifact)]
        elif mode == 'exact146-metadata-mir':
            argv += ['-Zprint-type-sizes','--emit=metadata='+str(artifact)+',mir='+str(scratch/'output.mir')]
        else: argv += ['--emit=metadata='+str(artifact)]
        preimages = [canonical(closure), packed(argv), packed_env(env), version]
        values = [sha(preimages[0]),sha(preimages[1]),sha(preimages[2]),tools['rustc']['sha256'],sha(version)]
        pre = HERE/'preimages'/mode; pre.mkdir(parents=True, exist_ok=False)
        for name,data in zip(['manifest.json','argv.bin','environment.bin','compiler-version.txt'], preimages): (pre/name).write_bytes(data)
        write('preimages/'+mode+'/binding.json', dict(schema=1, keys=dict(zip(KEYS,values)),
            distribution_tree=TREE, compiled_tree=roster(actual)['tree_sha256'], source_members=146,
            host_members=11, host_tree=HOST_TREE, all_five_keys_fresh=True))
        out, err = command(mode, argv, env|dict(zip(KEYS, values)), expected=1 if mode=='actual90-layout-queries' else 0)
        assert identity(RUSTC) == tools['rustc']
        assert roster({p.relative_to(vm).as_posix():p.read_bytes() for p in vm.rglob('*') if p.is_file()}) == roster(actual)
        inputs()
        if mode == 'exact146-metadata-mir':
            assert artifact.exists() and artifact.stat().st_size > 0
            write('commands/'+mode+'/artifact.json', identity(artifact)|dict(nonempty=True, executed=False, metadata_only=True))
            inventory(scratch/'output.mir', out)
            folder = HERE/'commands'/mode
            raw = (folder/'stdout').read_bytes()
            (folder/'stdout.gz').write_bytes(gzip.compress(raw, mtime=0)); (folder/'stdout').unlink()
            write('commands/'+mode+'/stdout-archive.json', dict(schema=1, original=row('stdout',raw),
                archive=identity(folder/'stdout.gz'), full_raw_compiler_output_retained=True,
                unrelated_layouts_not_cataloged=True))
        elif mode == 'actual90-layout-queries':
            assert not artifact.exists()
            reconcile_layout(err)
        else:
            assert artifact.exists() and artifact.stat().st_size > 0
            write('commands/'+mode+'/artifact.json', identity(artifact)|dict(nonempty=True, executed=True, synthetic_only=True))
            for filter_,count in [('combined_source_interaction_',4),('host_account_v1::tests::',11),
                                  ('host_composition_interaction_',2),('independent_composition_',2)]:
                command(mode+'-'+filter_.strip('_').replace(':','-'), [artifact,filter_,'--nocapture','--test-threads=1'],
                    dict(PATH='/usr/bin:/bin'), required=str(count)+' passed; 0 failed', cap=30)
        completed = True
    finally:
        records = [read(p) for p in (HERE/'commands').glob(mode+'*/receipt.json')]
        reaped = all(r['child_reaped'] and r['owned_group_absent'] for r in records)
        if reaped: shutil.rmtree(scratch)
        write('commands/'+mode+'/cleanup.json', dict(schema=1, completed=completed,
            child_groups_reaped_and_absent=reaped, owned_scratch_removed=not scratch.exists(),
            removed_artifact=not artifact.exists(), global_process_inventory=False,
            native_device_simulator_emulator_UI_capture=False))
        parent = HERE/'owned-work'
        if parent.exists() and not any(parent.iterdir()): parent.rmdir()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('mode', choices=['audit','exact146-metadata-mir','actual90-layout-queries','synthetic-optimized'])
    mode = parser.parse_args().mode
    if mode == 'audit': audit()
    else: compile_one(mode)
