"""Independent compiler-only review of the frozen scope-authority correction."""
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
CANDIDATE = ROOT / 'verification/swift-guarded-snapshot-scope-authority-correction'
RUSTC = pathlib.Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
CONTROL = 'src/experimental_swift_reactor/control.rs'
LOADER = 'src/experimental_swift_reactor/retained_profile_loader_v1.rs'


def sha(data): return hashlib.sha256(data).hexdigest()
def canonical(value): return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
def save(path, value): path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
def manifest(root):
    return [{'path': str(p.relative_to(root)), 'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())}
            for p in sorted(root.rglob('*')) if p.is_file()]


def execute(argv, env=None, timeout=55):
    started = time.monotonic()
    process = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    timed_out, actions = False, []
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(process.pid, signal.SIGKILL); actions.append('SIGKILL owned group')
        except ProcessLookupError:
            actions.append('owned group already absent')
        stdout, stderr = process.communicate()
    try:
        os.killpg(process.pid, 0); group_absent = False
    except ProcessLookupError:
        group_absent = True
    return {'argv': argv, 'cwd': str(ROOT), 'timeout_seconds': timeout, 'timed_out': timed_out,
            'exit_code': process.returncode, 'elapsed_seconds': time.monotonic() - started,
            'owned_process_group': process.pid, 'new_session': True, 'cleanup_actions': actions,
            'direct_child_reaped': process.poll() is not None, 'owned_group_absent': group_absent}, stdout, stderr


def verify_inputs():
    release = ROOT / 'verification/swift-semantic-adapter-root-review/guarded-snapshot-scope-authority-independent-release.json'
    assert sha(release.read_bytes()) == '3cb7b1ae0f010d44e23a353dfd6b11315786be28fbd227c975610383b82bf2a7'
    seal_bytes = (CANDIDATE / 'source-seal.json').read_bytes()
    assert sha(seal_bytes) == 'a51d5791cad11e6fb3a587d11b7c225216c11b75ccd89768a691c477a7f51b4c'
    seal = json.loads(seal_bytes)
    assert len(seal['members']) == 149
    for row in seal['members']:
        data = (CANDIDATE / row['path']).read_bytes()
        assert len(data) == row['bytes'] and sha(data) == row['sha256'], row['path']
    source = manifest(CANDIDATE / 'source/vm')
    assert source == json.loads((CANDIDATE / 'source-manifest.json').read_text())['members']
    assert len(source) == 144
    tree = sha(canonical(source))
    assert tree == '575b55d3391729749039dc2badccc9107449cb2c9a021d8ef67282c39b2e1896'
    receipt, stdout, stderr = execute([str(RUSTC), '--version', '--verbose'], timeout=10)
    assert receipt['exit_code'] == 0 and receipt['owned_group_absent']
    save(OUT / 'input-custody.json', {'schema': 1, 'source_seal_sha256': sha(seal_bytes),
        'verified_members': len(seal['members']), 'verified_bytes': sum(row['bytes'] for row in seal['members']),
        'source_tree_sha256': tree, 'source_members': source, 'tool_version_command': receipt,
        'rustc_version': stdout.decode(), 'rustc_sha256': sha(RUSTC.read_bytes()), 'tool_version_stderr': stderr.decode(),
        'read_scope': 'exact source-seal149 only; root active commands and other active lanes not read'})
    return stdout


POSITIVE = '''
fn independent_authentic_route_v1(selected:SelectedValidatedProfileV1,budget:SwiftRunBudget,started:Instant,cancellation:Cancellation,claims:&super::cache::SnapshotClaimsV1,rows:&mut File,snapshot:&mut File){
 if let Ok(scope)=selected.into_snapshot_scope_v1(budget,started,cancellation){
  let run=scope.construct_v1(claims,rows,snapshot);
  let _finish=run.finish_v1();
 }
}
'''
RELATIONSHIP = '''
// Actual type relationship only; no guessed bytes or floor selection.
const _:()=assert!(std::mem::size_of::<SnapshotScopeBorrowV1<'static>>()==std::mem::size_of::<(&'static mut Option<super::cache::SwiftFunctionCache>,&'static mut RuntimeControl,Option<&'static AccountedWasi>,AdoptedProof)>());
const _:()=assert!(std::mem::align_of::<SnapshotScopeBorrowV1<'static>>()==std::mem::align_of::<(&'static mut Option<super::cache::SwiftFunctionCache>,&'static mut RuntimeControl,Option<&'static AccountedWasi>,AdoptedProof)>());
'''
CASES = {
    'authentic-route': ({LOADER: POSITIVE, CONTROL: RELATIONSHIP}, []),
    'private-forge': ({LOADER: '''
fn independent_private_forge_v1<'a>(cache:&'a mut Option<super::cache::SwiftFunctionCache>,control:&'a mut RuntimeControl,adopted:super::control::AdoptedProof)->super::control::SnapshotScopeBorrowV1<'a>{
 super::control::SnapshotScopeBorrowV1{cache,control,wasi:None,adopted}
}
'''}, ['E0451']),
    'reuse-after-consume': ({LOADER: '''
fn independent_reuse_v1(owners:super::control::SnapshotScopeBorrowV1<'_>){let _first=owners.into_parts();let _second=owners.into_parts();}
'''}, ['E0382']),
    'borrow-escape': ({CONTROL: '''
fn independent_escape_v1(mut scope:SnapshotScopeV1)->SnapshotScopeBorrowV1<'static>{
 let adopted=scope.adopted.take().expect("actual owner");
 SnapshotScopeBorrowV1{cache:&mut scope.cache,control:&mut scope.control,wasi:scope.wasi.as_ref(),adopted}
}
'''}, ['E0515', 'E0515', 'E0515']),
    'move-borrowed-scope': ({CONTROL: '''
fn independent_move_scope_v1(mut scope:SnapshotScopeV1){
 let adopted=scope.adopted.take().expect("actual owner");
 let owners=SnapshotScopeBorrowV1{cache:&mut scope.cache,control:&mut scope.control,wasi:scope.wasi.as_ref(),adopted};
 let moved=scope;
 drop((owners,moved));
}
'''}, ['E0505']),
    'substitute-control': ({LOADER: '''
fn independent_substitute_v1(owners:&mut super::control::SnapshotScopeBorrowV1<'_>,foreign:&mut RuntimeControl){owners.control=foreign;}
'''}, ['E0616']),
}


def compile_case(case, opt, version, edits, expected):
    label = case + ('-optimized' if opt else '-debug')
    command = OUT / 'commands' / label
    command.mkdir(parents=True, exist_ok=False)
    scratch = OUT / 'owned-work' / label
    vm = scratch / 'vm'
    shutil.copytree(CANDIDATE / 'source/vm', vm)
    for relative, text in edits.items():
        path = vm / relative; path.write_text(path.read_text() + text)
    preimage = {'schema': 1, 'source_members': manifest(vm), 'exact_appends': edits,
                'driver_sha256': sha(pathlib.Path(__file__).read_bytes())}
    save(command / 'source-preimage.json', preimage)
    artifact = scratch / 'candidate.rmeta'
    argv = [str(RUSTC), '--crate-name', 'mixer_vm', '--edition=2021', '--target', 'aarch64-apple-darwin',
            '--error-format=json', '-C', 'opt-level=' + ('3' if opt else '0'), '-C', 'overflow-checks=yes', '-C', 'panic=unwind']
    for feature in ['experimental-swift-reactor', 'experimental-swift-wasi', 'experimental-stream-validation', 'experimental-function-cache']:
        argv += ['--cfg', 'feature="' + feature + '"']
    argv += ['--crate-type', 'rlib', '--emit=metadata', str(vm / 'src/lib.rs'), '-o', str(artifact)]
    env = {'PATH': '/usr/bin:/bin', 'TMPDIR': str(scratch), 'CARGO_MANIFEST_DIR': str(vm),
           'MIXER_LOADER_COMPILER_SHA256': sha(RUSTC.read_bytes()), 'MIXER_LOADER_COMPILER_VERSION_SHA256': sha(version),
           'MIXER_LOADER_MANIFEST_SHA256': sha(canonical(preimage)), 'MIXER_LOADER_COMMAND_SHA256': sha(canonical(argv))}
    env['MIXER_LOADER_COMPILE_ENV_SHA256'] = sha(canonical(env))
    receipt, stdout, stderr = execute(argv, env)
    (command / 'stdout').write_bytes(stdout); (command / 'stderr').write_bytes(stderr)
    diagnostics = []
    for line in stderr.splitlines():
        try: value = json.loads(line)
        except ValueError: continue
        if value.get('level') == 'error' and value.get('code'):
            diagnostics.append({'code': value['code']['code'], 'message': value['message'], 'spans': value.get('spans', [])})
    codes = [row['code'] for row in diagnostics]
    success = receipt['exit_code'] == (1 if expected else 0) and sorted(codes) == sorted(expected)
    receipt.update({'schema': 1, 'case': case, 'mode': 'optimized' if opt else 'debug',
        'source_tree_sha256': sha(canonical(preimage['source_members'])), 'environment': env,
        'rustc_version': version.decode(), 'expected_diagnostics': expected, 'observed_diagnostics': codes,
        'passed': success and not receipt['timed_out'] and receipt['owned_group_absent'],
        'scope': 'metadata compiler only; no writer or VM execution'})
    save(command / 'diagnostics.json', diagnostics)
    save(command / 'receipt.json', receipt)
    shutil.rmtree(scratch)
    print(json.dumps({'case': label, 'passed': receipt['passed'], 'codes': codes, 'elapsed_seconds': receipt['elapsed_seconds']}), flush=True)
    return receipt['passed']


def main():
    OUT.mkdir(exist_ok=True)
    version = verify_inputs()
    evidence = ROOT / 'verification/swift-guarded-snapshot-composition-independent/candidate-review/bypass-evidence.json'
    assert sha(evidence.read_bytes()) == '9d9a84a970e2c7c2417c9ac5c8a297e353074cfce8499c1fb211638a3d123608'
    edits = {row['path']: row['text'] for row in json.loads(evidence.read_text())['results'][0]['exact_witnesses']}
    cases = [('both-old-bypasses', edits, ['E0061', 'E0061'])] + [(name, edits, expected) for name, (edits, expected) in CASES.items()]
    results = []
    for opt in [False, True]:
        for name, edits, expected in cases:
            results.append(compile_case(name, opt, version, edits, expected))
    work = OUT / 'owned-work'
    if work.exists() and not list(work.iterdir()): work.rmdir()
    save(OUT / 'compiler-summary.json', {'schema': 1, 'commands': len(results), 'all_passed': all(results),
        'python_command': [sys.executable, '-B', str(pathlib.Path(__file__).resolve())], 'python_version': sys.version,
        'scope': 'fresh compiler privacy/lifetime controls and exact old witnesses; no runtime or floor selection'})
    raise SystemExit(0 if all(results) else 1)


if __name__ == '__main__': main()
