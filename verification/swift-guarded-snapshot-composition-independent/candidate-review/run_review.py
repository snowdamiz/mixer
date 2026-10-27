"""Fresh source/compiler review; never execute a Mixer binary or writer."""
import datetime
import hashlib
import json
import os
import pathlib
import re
import shutil
import signal
import subprocess
import sys
import time

OUT = pathlib.Path(__file__).resolve().parent
ROOT = OUT.parents[2]
CANDIDATE = ROOT / 'verification/swift-guarded-snapshot-composition-source-preparation'
RUSTC = pathlib.Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
WORK = OUT / 'owned-work'
INITIAL = 'src/experimental_swift_reactor/cache/initial_profile_v1.rs'
CONTROL = 'src/experimental_swift_reactor/control.rs'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')


def manifest(directory):
    return [{'path': str(p.relative_to(directory)), 'bytes': p.stat().st_size, 'sha256': digest(p.read_bytes())}
            for p in sorted(directory.rglob('*')) if p.is_file()]


def execute(argv, timeout, env=None):
    started = time.monotonic()
    process = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    timed_out, actions = False, []
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(process.pid, signal.SIGKILL)
            actions.append('SIGKILL own process group')
        except ProcessLookupError:
            actions.append('owned process group already absent')
        stdout, stderr = process.communicate()
    return {'argv': argv, 'cwd': str(ROOT), 'timeout_seconds': timeout, 'timed_out': timed_out,
            'exit_code': process.returncode, 'elapsed_seconds': time.monotonic() - started,
            'owned_group': process.pid, 'new_session': True, 'cleanup_actions': actions,
            'direct_child_reaped': process.poll() is not None}, stdout, stderr


INITIAL_TYPES = [
    'Option<SnapshotPlanV1>', 'Option<[u8;4096]>', 'Option<AError>',
    "(SnapshotAccessV1<'static>,SnapshotPhaseStorageV1)",
    'Result<(usize,SnapshotShapeV1,u64,u64),AError>',
    'Result<(),SnapshotExportErrorV1>',
    "Result<SnapshotViewV2<'static>,SnapshotExportErrorV1>",
    "Result<SnapshotCursorV2<'static>,SnapshotExportErrorV1>",
    "Result<Option<SnapshotBlockV2<'static>>,SnapshotExportErrorV1>",
    'Result<std::fs::Metadata,SnapshotExportErrorV1>', 'Result<u64,SnapshotExportErrorV1>',
    'Option<Stop>', '(InitialProfileConstructionOutcomeV1,SnapshotAttemptV1)',
    '(u32,Option<SwiftRunFailure>,Option<ProfileHeaderErrorV1>,Option<UnverifiedProfileHeaderV1>,Option<Result<ProfileRowsObservationV1,ProfileAdapterErrorV1>>,Option<Result<(),SwiftRunFailure>>,Option<AdoptedProof>)',
    'SnapshotPhaseStorageV1', 'SnapshotOuterV1', 'SnapshotPrimaryRetirementV1',
]
CONTROL_TYPES = [
    'Option<SnapshotWasiAttachmentV1>', 'Result<AccountedWasi,SwiftRunFailure>',
    'Result<(RuntimeControl,AdoptedProof),SnapshotPreScopeFailureV1>',
    'Result<SnapshotScopeV1,SnapshotPreScopeFailureV1>', 'SnapshotScopeFinishV1',
]


def layouts_static(symbol, names):
    values = ',\n'.join(f'std::mem::size_of::<{name}>(),std::mem::align_of::<{name}>()' for name in names)
    return f'\n#[no_mangle]\npub static {symbol}:[usize;{len(names)*2}]=[\n{values}\n];\n'


POSITIVE = '''
fn independent_positive_lifetime_v1(cache:&SwiftFunctionCache,control:&mut RuntimeControl,wasi:Option<&AccountedWasi>,scalars:InitialProfileScalarsV1){
 let (access,storage)=begin_snapshot_access_v1(cache,control,wasi);
 {
  let initial=InitialProfileBorrowV1{cache,control:access.shared_control(),wasi,scalars};
  let view=borrow_snapshot_v2(&initial);
  drop(view);
 }
 let _completion=access.complete(storage);
}
'''
VIEW_NEGATIVE = '''
fn independent_negative_live_view_v1(cache:&SwiftFunctionCache,control:&mut RuntimeControl,wasi:Option<&AccountedWasi>,scalars:InitialProfileScalarsV1){
 let (access,storage)=begin_snapshot_access_v1(cache,control,wasi);
 let initial=InitialProfileBorrowV1{cache,control:access.shared_control(),wasi,scalars};
 let view=borrow_snapshot_v2(&initial);
 let completion=access.complete(storage);
 drop((view,completion));
}
'''
RUN_NEGATIVE = '''
fn independent_negative_live_outer_v1(run:SnapshotRunV1){
 let outer=run.outer_v1();
 let finished=run.finish_v1();
 let _=(outer,finished);
}
'''


def verify_inputs():
    assert digest((CANDIDATE / 'seal.json').read_bytes()) == 'bf17889754e7ef436fababcf8b96f5109285f982bcc48258a0b9e204a95b1751'
    seal = json.loads((CANDIDATE / 'seal.json').read_text())
    for row in seal['members']:
        data = (CANDIDATE / row['path']).read_bytes()
        assert len(data) == row['bytes'] and digest(data) == row['sha256'], row['path']
    frozen = json.loads((CANDIDATE / 'source-manifest.json').read_text())
    actual = manifest(CANDIDATE / 'source/vm')
    assert len(actual) == 144 and actual == frozen['members']
    tree = digest(json.dumps(actual, sort_keys=True, separators=(',', ':')).encode())
    assert tree == '140761754a158c72209120de9ac5f78f7a1d5c20c3cddd6deeb9fff7a2d1b395', tree
    receipt, stdout, stderr = execute([str(RUSTC), '--version', '--verbose'], 15)
    assert receipt['exit_code'] == 0
    save(OUT / 'input-custody.json', {'schema': 1, 'candidate_seal_sha256': digest((CANDIDATE / 'seal.json').read_bytes()),
        'candidate_members_verified': len(seal['members']), 'candidate_bytes_verified': sum(row['bytes'] for row in seal['members']),
        'source_members': actual, 'source_tree_sha256': tree, 'tool_version': stdout.decode(),
        'rustc_sha256': digest(RUSTC.read_bytes()), 'tool_version_command': receipt, 'tool_version_stderr': stderr.decode(),
        'scope': 'exact released immutable source custody; no harness import or execution'})
    return stdout


def decode_layouts(data, symbol):
    lines = [line for line in data.splitlines() if line.startswith('@') and symbol in line and 'constant' in line]
    assert len(lines) == 1, (symbol, lines)
    raw = re.search(r'c"(.*?)"', lines[0]).group(1)
    decoded, i = bytearray(), 0
    while i < len(raw):
        if raw[i] == '\\':
            decoded.append(int(raw[i+1:i+3], 16)); i += 3
        else:
            decoded.append(ord(raw[i])); i += 1
    return [int.from_bytes(decoded[i:i+8], 'little') for i in range(0, len(decoded), 8)], lines[0]


def compile_case(name, version, *, opt=False, unit=False, additions=None, replacement=None, layouts=False, expected=None, default=False):
    command_dir = OUT / 'commands' / name
    command_dir.mkdir(parents=True, exist_ok=False)
    vm = WORK / name / 'vm'
    shutil.copytree(CANDIDATE / 'source/vm', vm)
    edits = []
    for relative, text in (additions or {}).items():
        p = vm / relative
        p.write_text(p.read_text() + text)
        edits.append({'path': relative, 'kind': 'append', 'text': text})
    if replacement:
        relative, before, after = replacement
        p = vm / relative
        text = p.read_text(); assert text.count(before) == 1
        p.write_text(text.replace(before, after, 1))
        edits.append({'path': relative, 'kind': 'replace-one', 'before': before, 'after': after})
    sources = manifest(vm)
    source_tree = digest(json.dumps(sources, sort_keys=True, separators=(',', ':')).encode())
    save(command_dir / 'source-preimage.json', {'source_tree_sha256': source_tree, 'source_members': sources, 'exact_edits': edits})
    emit = 'llvm-ir' if layouts or default else 'metadata'
    artifact = vm.parent / ('artifact.ll' if emit == 'llvm-ir' else 'artifact.rmeta')
    argv = [str(RUSTC), '--crate-name', 'mixer_vm', '--edition=2021', '--target', 'aarch64-apple-darwin',
            '-C', 'opt-level=' + ('3' if opt else '0'), '-C', 'overflow-checks=yes', '-C', 'panic=unwind']
    for feature in ['experimental-swift-reactor', 'experimental-swift-wasi', 'experimental-stream-validation', 'experimental-function-cache']:
        argv += ['--cfg', 'feature="' + feature + '"']
    if layouts:
        argv += ['--cfg', 'mixer_snapshot_composition_layout']
    argv += ['--test'] if unit else ['--crate-type', 'rlib']
    argv += ['--emit=' + emit, str(vm / 'src/lib.rs'), '-o', str(artifact)]
    env = {'PATH': '/usr/bin:/bin', 'TMPDIR': str(WORK), 'CARGO_MANIFEST_DIR': str(vm),
           'MIXER_LOADER_COMPILER_SHA256': digest(RUSTC.read_bytes()),
           'MIXER_LOADER_COMPILER_VERSION_SHA256': digest(version),
           'MIXER_LOADER_MANIFEST_SHA256': source_tree,
           'MIXER_LOADER_COMMAND_SHA256': digest(json.dumps(argv, separators=(',', ':')).encode())}
    env['MIXER_LOADER_COMPILE_ENV_SHA256'] = digest(json.dumps(env, sort_keys=True, separators=(',', ':')).encode())
    receipt, stdout, stderr = execute(argv, 55, env)
    (command_dir / 'stdout').write_bytes(stdout); (command_dir / 'stderr').write_bytes(stderr)
    receipt.update({'environment': env, 'source_tree_sha256': source_tree, 'rustc_version': version.decode(),
                    'expected_diagnostics': expected, 'scope': 'compiler only; never executes product source'})
    receipt['actual_diagnostics'] = sorted(set(re.findall(r'error\[(E\d+)\]', stderr.decode())))
    receipt['passed'] = not receipt['timed_out'] and ((receipt['exit_code'] == 1 and receipt['actual_diagnostics'] == expected) if expected else receipt['exit_code'] == 0)
    if receipt['passed'] and layouts:
        ir = artifact.read_text()
        result = {}
        for symbol, names in [('INDEPENDENT_INITIAL_LAYOUTS_V1', INITIAL_TYPES), ('INDEPENDENT_CONTROL_LAYOUTS_V1', CONTROL_TYPES)]:
            values, line = decode_layouts(ir, symbol)
            (command_dir / (symbol + '.llvm')).write_text(line + '\n')
            assert len(values) == len(names) * 2
            result[symbol] = [{'type': name, 'bytes': values[i*2], 'alignment': values[i*2+1]} for i, name in enumerate(names)]
        save(command_dir / 'layouts.json', result)
        receipt['llvm_sha256'] = digest(artifact.read_bytes())
    if receipt['passed'] and default:
        ir = artifact.read_text()
        names = ['MIXER_COMPOSITION_CONTROL_LAYOUTS_V1', 'MIXER_COMPOSITION_INITIAL_LAYOUTS_V1',
                 'MIXER_COMPOSITION_ENCODER_HELPER_LAYOUTS_V1', 'MIXER_COMPOSITION_LOADER_HELPER_LAYOUTS_V1',
                 'MIXER_COMPOSITION_ENCODER_CAPTURE_LAYOUTS_V1', 'MIXER_COMPOSITION_CAPTURE_PARTIAL_SUM_V1',
                 'COMPOSITION_PARAMETER_CAPTURE_MEASURER_V1', 'composer_measure_span_capture_v1',
                 'composer_measure_parameter_span_capture_v1', 'composer_checked_capture_static_sum_v1']
        found = [name for name in names if name in ir]
        save(command_dir / 'absence.json', {'names_checked': names, 'found': found, 'passed': not found, 'llvm_sha256': digest(artifact.read_bytes())})
        receipt['passed'] = not found
    save(command_dir / 'receipt.json', receipt)
    shutil.rmtree(vm.parent)
    print(json.dumps({'name': name, 'passed': receipt['passed'], 'diagnostics': receipt['actual_diagnostics'], 'elapsed_seconds': receipt['elapsed_seconds']}), flush=True)
    return receipt['passed']


def main():
    OUT.mkdir(exist_ok=True); WORK.mkdir(exist_ok=True)
    version = verify_inputs()
    stage = sys.argv[1]
    results = []
    if stage == 'layouts':
        additions = {INITIAL: layouts_static('INDEPENDENT_INITIAL_LAYOUTS_V1', INITIAL_TYPES),
                     CONTROL: layouts_static('INDEPENDENT_CONTROL_LAYOUTS_V1', CONTROL_TYPES)}
        results.append(compile_case('exact-default-production-debug', version, default=True))
        for unit in [False, True]:
            for opt in [False, True]:
                name = 'independent-layout-' + ('unit-' if unit else 'production-') + ('optimized' if opt else 'debug')
                results.append(compile_case(name, version, opt=opt, unit=unit, additions=additions, layouts=True))
    elif stage == 'bypass':
        witness = '''
// A sibling module can select the Selected constructor from ordinary owner parts.
// This compiler witness is never invoked and adds no actual writer execution.
fn independent_snapshot_parts_bypass_v1(cache:&mut Option<super::cache::SwiftFunctionCache>,control:&mut RuntimeControl,adopted:super::control::AdoptedProof,claims:&super::cache::SnapshotClaimsV1,rows:&mut File,snapshot:&mut File){
 let _retained=super::cache::construct_snapshot_in_scope_v1(cache,control,None,adopted,claims,rows,snapshot);
}
'''
        inner_witness = '''
// The parent cache module can select the inner Selected constructor directly.
fn independent_snapshot_inner_parts_bypass_v1(cache:&mut Option<SwiftFunctionCache>,control:&mut RuntimeControl,adopted:AdoptedProof,claims:&SnapshotClaimsV1,rows:&mut std::fs::File,snapshot:&mut std::fs::File){
 let _retained=initial_profile_v1::construct_snapshot_owned_v1(cache,control,None,adopted,claims,rows,snapshot);
}
'''
        for opt in [False, True]:
            results.append(compile_case('undesired-parts-bypass-' + ('optimized' if opt else 'debug'), version,
                opt=opt, additions={'src/experimental_swift_reactor/retained_profile_loader_v1.rs': witness,
                                  'src/experimental_swift_reactor/cache.rs': inner_witness}))
    elif stage == 'lifetimes':
        for opt in [False, True]:
            mode = 'optimized' if opt else 'debug'
            results.append(compile_case('positive-lifetime-' + mode, version, opt=opt, additions={INITIAL: POSITIVE}))
            cases = [
                ('live-view', {INITIAL: VIEW_NEGATIVE}, None, ['E0505']),
                ('live-outer', {CONTROL: RUN_NEGATIVE}, None, ['E0505']),
                ('direct-control', None, (INITIAL, 'cache,control:access.shared_control(),wasi,scalars', 'cache,control,wasi,scalars'), ['E0502']),
                ('forge-capability', {'src/experimental_swift_reactor/cache.rs': '\nfn independent_forge_v1(body:super::retained_profile_loader_v1::AdoptionBodyV1){let _=super::retained_profile_loader_v1::SelectedSnapshotBodyV1(body);}\n'}, None, ['E0603']),
                ('extract-control', {'src/experimental_swift_reactor/cache.rs': '\nfn independent_extract_v1(scope:super::control::SnapshotScopeV1){let _=scope.control;}\n'}, None, ['E0616']),
            ]
            for name, additions, replacement, expected in cases:
                results.append(compile_case('negative-' + name + '-' + mode, version, opt=opt,
                    additions=additions, replacement=replacement, expected=expected))
    else:
        raise ValueError(stage)
    save(OUT / (stage + '-summary.json'), {'schema': 1, 'passed': all(results), 'commands': len(results),
         'scope': 'fresh bounded compiler source controls only; no writer/VM execution or floor selection'})
    if WORK.exists() and not list(WORK.iterdir()): WORK.rmdir()
    raise SystemExit(0 if all(results) else 1)


if __name__ == '__main__':
    main()
