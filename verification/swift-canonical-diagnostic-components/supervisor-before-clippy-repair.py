"""Bounded canonical diagnostic-component commands; never imports frozen runners."""
from pathlib import Path
import hashlib
import json
import os
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
BIN = Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin')
OWNED = HERE / 'owned'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def members():
    paths = [ROOT / 'vm/Cargo.toml', ROOT / 'vm/Cargo.lock']
    for directory in ('src', 'tests', 'include'):
        paths.extend(p for p in (ROOT / 'vm' / directory).rglob('*') if p.is_file())
    return [{'path': p.relative_to(ROOT).as_posix(), 'bytes': p.stat().st_size,
             'sha256': sha(p.read_bytes())} for p in sorted(paths)]


def compact(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def main(case):
    for name in ('tmp', 'cargo-home', 'target'):
        (OWNED / name).mkdir(parents=True, exist_ok=True)
    env = {
        'PATH': str(BIN) + ':/usr/bin:/bin:/usr/sbin:/sbin',
        'HOME': os.environ['HOME'],
        'TMPDIR': str(OWNED / 'tmp'),
        'CARGO_HOME': str(OWNED / 'cargo-home'),
        'CARGO_TARGET_DIR': str(OWNED / 'target'),
        'CARGO_BUILD_JOBS': '2',
        'CARGO_TERM_COLOR': 'never',
        'RUSTC': str(BIN / 'rustc'),
        'RUSTDOC': str(BIN / 'rustdoc'),
        'LANG': 'C', 'LC_ALL': 'C',
    }
    base = [str(BIN / 'cargo')]
    common = ['--locked', '--offline', '--manifest-path', str(ROOT / 'vm/Cargo.toml')]
    commands = {
        'cargo-version': [str(BIN / 'cargo'), '--version', '--verbose'],
        'rustc-version': [str(BIN / 'rustc'), '--version', '--verbose'],
        'clippy-version': [str(BIN / 'cargo'), 'clippy', '--version'],
        'default-check': base + ['check'] + common + ['--lib'],
        'stream-check': base + ['check'] + common + ['--lib', '--features', 'experimental-stream-validation'],
        'reactor-clippy': base + ['clippy'] + common + ['--lib', '--features', 'experimental-swift-reactor', '--', '-D', 'warnings'],
    }
    for mode in ('debug', 'release'):
        for component in ('diagnostic_result_v1', 'diagnostic_profile'):
            commands[mode + '-' + component] = base + ['test'] + common + (
                ['--release'] if mode == 'release' else []
            ) + ['--lib', '--features', 'experimental-swift-reactor', component,
                 '--', '--nocapture', '--test-threads=4']
    if case == 'format-owned-tests':
        commands[case] = [str(BIN / 'rustfmt'), '--edition', '2021', '--check',
                          str(ROOT / 'vm/src/experimental_swift_reactor/diagnostic_profile_tests.rs')]
    if case not in commands:
        raise ValueError('Unknown bounded command: ' + case)
    directory = HERE / 'commands' / case
    directory.mkdir(parents=True, exist_ok=False)
    source_before = members()
    source_file = HERE / 'source-manifest.json'
    if not source_file.exists():
        source_file.write_text(json.dumps({'schema': 1, 'members': source_before,
            'tree_sha256': sha(compact(source_before))}, indent=2) + '\n')
    assert source_before == json.loads(source_file.read_text())['members']
    preimage = {'schema': 1, 'argv': commands[case], 'cwd': str(ROOT), 'environment': env,
                'source_manifest_sha256': sha(source_file.read_bytes()),
                'source_tree_sha256': sha(compact(source_before)),
                'supervisor_sha256': sha(Path(__file__).read_bytes()),
                'timeout_seconds': 180, 'tool_path': commands[case][0],
                'tool_sha256': sha(Path(commands[case][0]).read_bytes())}
    (directory / 'preimage.json').write_text(json.dumps(preimage, indent=2) + '\n')
    started = time.monotonic()
    process = subprocess.Popen(commands[case], cwd=ROOT, env=env,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               start_new_session=True)
    timed_out = False
    actions = []
    try:
        stdout, stderr = process.communicate(timeout=180)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(process.pid, signal.SIGTERM)
            actions.append('SIGTERM owned process group')
        except ProcessLookupError:
            pass
        try:
            stdout, stderr = process.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
                actions.append('SIGKILL owned process group')
            except ProcessLookupError:
                pass
            stdout, stderr = process.communicate(timeout=3)
    try:
        os.killpg(process.pid, 0)
        group_absent = False
    except ProcessLookupError:
        group_absent = True
    if not group_absent:
        os.killpg(process.pid, signal.SIGKILL)
        actions.append('SIGKILL remaining owned group after direct-child completion')
        # Any such case remains failed; it is not relabeled a clean command.
    (directory / 'stdout').write_bytes(stdout)
    (directory / 'stderr').write_bytes(stderr)
    unchanged = members() == source_before
    success = process.returncode == 0 and not timed_out and group_absent and unchanged
    receipt = {**preimage, 'case': case, 'exit_code': process.returncode,
               'elapsed_seconds': time.monotonic() - started,
               'timed_out': timed_out, 'direct_owned_child_reaped': process.poll() is not None,
               'owned_process_group': process.pid, 'new_session': True,
               'owned_group_absent': group_absent, 'cleanup_actions': actions,
               'source_unchanged_after': unchanged, 'success': success,
               'stdout_bytes': len(stdout), 'stdout_sha256': sha(stdout),
               'stderr_bytes': len(stderr), 'stderr_sha256': sha(stderr),
               'owned_test_fixture_entries_after': sorted(p.name for p in (OWNED / 'tmp').iterdir())}
    (directory / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({k: receipt[k] for k in ('case', 'exit_code', 'elapsed_seconds',
        'timed_out', 'owned_group_absent', 'source_unchanged_after', 'success',
        'owned_test_fixture_entries_after')}, sort_keys=True), flush=True)
    print(stdout.decode(errors='replace')[-2000:], flush=True)
    print(stderr.decode(errors='replace')[-2000:], flush=True)
    return success


if __name__ == '__main__':
    raise SystemExit(0 if len(sys.argv) == 2 and main(sys.argv[1]) else 1)
