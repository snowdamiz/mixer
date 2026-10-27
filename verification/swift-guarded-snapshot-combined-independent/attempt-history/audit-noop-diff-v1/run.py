"""Bounded independent audit and narrow host interactions; owned files only."""
from pathlib import Path
import datetime
import json
import os
import platform
import shutil
import signal
import struct
import subprocess
import sys
import time

sys.dont_write_bytecode = True
from audit import HERE, ROOT, P, KEYS, PROFILE, digest, canon, read, write, row, roster, checked_sources

RUSTC = Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
SDK = Path('/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk')


def ident(path):
    return row(str(path), path.read_bytes())


def pack(values):
    b = [os.fsencode(v) for v in values]
    return struct.pack('<Q', len(b)) + b''.join(struct.pack('<Q', len(v)) + v for v in b)


def absent(pid):
    try:
        os.killpg(pid, 0)
        return False
    except ProcessLookupError:
        return True


def command(label, argv, environment, seconds=55):
    out = HERE / 'commands' / label
    out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    actions, limited = [], False
    with (out / 'stdout').open('wb') as stdout, (out / 'stderr').open('wb') as stderr:
        proc = subprocess.Popen([str(a) for a in argv], cwd=ROOT, env=environment,
                                stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            while proc.poll() is None:
                if time.monotonic() - started > seconds or sum((out / s).stat().st_size for s in ('stdout', 'stderr')) > 4194304:
                    limited = True
                    os.killpg(proc.pid, signal.SIGTERM)
                    actions.append('TERM own command group after timeout/output cap')
                    try:
                        proc.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid, signal.SIGKILL)
                        actions.append('KILL own command group after TERM timeout')
                    break
                time.sleep(.02)
        finally:
            code = proc.wait(timeout=3)
            if not absent(proc.pid):
                os.killpg(proc.pid, signal.SIGTERM)
                actions.append('TERM own surviving descendants')
                deadline = time.monotonic() + 2
                while not absent(proc.pid) and time.monotonic() < deadline:
                    time.sleep(.02)
                if not absent(proc.pid):
                    os.killpg(proc.pid, signal.SIGKILL)
                    actions.append('KILL own surviving descendants')
    receipt = dict(schema=1, timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        argv=list(map(str, argv)), cwd=str(ROOT), environment=environment, exit_code=code,
        elapsed_seconds=time.monotonic()-started, timeout_seconds=seconds, output_cap_bytes=4194304,
        timed_out_or_output_limited=limited, owned_process_group=proc.pid, child_reaped=True,
        owned_group_absent=absent(proc.pid), cleanup_actions=actions,
        stdout_sha256=digest((out / 'stdout').read_bytes()), stderr_sha256=digest((out / 'stderr').read_bytes()),
        runner_sha256=digest(Path(__file__).read_bytes()), source_tree_sha256=roster(checked_sources()[1])['tree_sha256'],
        python=ident(Path(sys.executable).resolve()), python_version=sys.version)
    write('commands/' + label + '/receipt.json', receipt)
    print(json.dumps(dict(label=label, exit_code=code, seconds=receipt['elapsed_seconds'], owned_group_absent=receipt['owned_group_absent'])), flush=True)
    assert code == 0 and not limited and receipt['owned_group_absent'], (label, (out / 'stderr').read_text()[-3000:])
    return (out / 'stdout').read_bytes()


def one(mode):
    _, source, hosts = checked_sources()
    work = HERE / 'owned-work' / mode
    assert not work.exists()
    work.mkdir(parents=True)
    exe = work / 'interactions.bin'
    completed = False
    try:
        tests = dict(source)
        appendices = [
            ('src/experimental_swift_reactor/control_tests.rs', HERE / 'interaction-tests.inc.rs'),
            ('src/experimental_swift_reactor/cache.rs', P / 'cache-tests.inc.rs'),
            (PROFILE, P / 'profile-tests.inc.rs')]
        appends = []
        for name, appendix in appendices:
            before = tests[name]
            tests[name] += appendix.read_bytes()
            appends.append(dict(path=name, base=row(name, before), appendix=ident(appendix), result=row(name, tests[name])))
        vm = work / 'vm'
        for name, b in tests.items():
            path = vm / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b)
        env = dict(PATH='/usr/bin:/bin', TMPDIR=str(work), RUSTC_BOOTSTRAP='1', CARGO_MANIFEST_DIR=str(vm), SDKROOT=str(SDK))
        version = command(mode + '-rustc-version', [RUSTC, '-vV'], env, 10)
        assert b'rustc 1.99.0' in version
        identity = dict(schema=1, distribution=roster(source), compiled_source=roster(tests), host_support=roster(hosts),
            overlay_appends=appends, root_release=ident(ROOT / 'verification/swift-semantic-adapter-root-review/guarded-snapshot-combined-independent-release.json'),
            tools=dict(rustc=ident(RUSTC), python=ident(Path(sys.executable).resolve()), python_version=sys.version,
                rustc_version_sha256=digest(version), cc=ident(Path('/usr/bin/cc')),
                SDK_headers=[ident(SDK / n) for n in ['usr/include/CommonCrypto/CommonDigest.h', 'usr/include/crt_externs.h', 'usr/include/mach-o/dyld.h', 'usr/include/unistd.h']],
                platform=platform.platform()),
            orchestration=[ident(HERE / n) for n in ['audit.py', 'run.py', 'interaction-tests.inc.rs']],
            scope='Independent synthetic ordinary-proof/private selected policy, actual A commit and real complete only; no authentic loader, scope, guest, cache or writer runtime',
            tools_runner_SDK_outside_host11=True)
        argv = [str(RUSTC), '--crate-name', 'mixer_vm', '--edition=2021', '--target', 'aarch64-apple-darwin',
                '-C', 'opt-level=' + ('3' if mode == 'optimized' else '0'), '-C', 'overflow-checks=yes',
                '-C', 'panic=unwind', '-Zmir-opt-level=0']
        for feature in ['experimental-swift-reactor', 'experimental-swift-wasi', 'experimental-stream-validation', 'experimental-function-cache']:
            argv += ['--cfg', 'feature="' + feature + '"']
        argv += ['--test', str(vm / 'src/lib.rs'), '--emit=link', '-o', str(exe)]
        env_bytes = pack([k + '=' + v for k, v in sorted(env.items())])
        blobs = [canon(identity), pack(argv), env_bytes, version]
        values = [digest(blobs[0]), digest(blobs[1]), digest(blobs[2]), identity['tools']['rustc']['sha256'], digest(blobs[3])]
        env = env | dict(zip(KEYS, values))
        pre = HERE / 'preimages' / mode
        pre.mkdir(parents=True)
        for name, b in zip(['manifest.json', 'argv.bin', 'environment.bin', 'compiler-version.txt'], blobs):
            (pre / name).write_bytes(b)
        write('preimages/' + mode + '/binding.json', dict(compile_identity_keys=dict(zip(KEYS, values)),
            source_tree_sha256=roster(source)['tree_sha256'], compiled_tree_sha256=roster(tests)['tree_sha256'],
            host_tree_sha256=roster(hosts)['tree_sha256'], test_only_overlay_files=3,
            environment_preimage_excludes_only_five_injected_keys=True))
        assert roster({str(p.relative_to(vm)):p.read_bytes() for p in vm.rglob('*') if p.is_file()}) == roster(tests)
        command(mode + '-compile', argv, env)
        write('commands/' + mode + '-compile/artifact.json', ident(exe))
        output = command(mode + '-tests', [exe, 'combined_independent_', '--nocapture', '--test-threads=1'], {'PATH':'/usr/bin:/bin'}, 20)
        assert b'4 passed; 0 failed' in output
        assert output.count(b' ... ok') == 4
        assert ident(RUSTC) == identity['tools']['rustc']
        assert [ident(Path(i['path'])) for i in identity['orchestration']] == identity['orchestration']
        assert roster({str(p.relative_to(vm)):p.read_bytes() for p in vm.rglob('*') if p.is_file()}) == roster(tests)
        assert checked_sources()[1] == source
        completed = True
    finally:
        removed = ident(exe) if exe.exists() else None
        receipts = [read(p) for p in (HERE / 'commands').glob(mode + '-*/receipt.json')]
        groups_absent = all(r['owned_group_absent'] for r in receipts)
        if groups_absent:
            shutil.rmtree(work)
        write('commands/' + mode + '-compile/cleanup.json', dict(completed=completed,
            owned_groups_absent=groups_absent, scratch_removed=not work.exists(), removed_artifact=removed,
            native_UI_capture_started=False, global_inventory=False))
        if (HERE / 'owned-work').exists() and not any((HERE / 'owned-work').iterdir()):
            (HERE / 'owned-work').rmdir()


if __name__ == '__main__':
    if sys.argv[1] == 'audit':
        command('audit', [Path(sys.executable), HERE / 'audit.py'], {'PATH':'/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE':'1'}, 20)
    else:
        one(sys.argv[1])
