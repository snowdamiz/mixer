"""Independent, bounded rustc MIR emission. No product code is executed."""
from pathlib import Path
import hashlib, json, os, platform, signal, subprocess, sys, time

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
SOURCE = HERE.parent / 'swift-guarded-snapshot-composition-source-preparation'
RUSTC = Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
sha = lambda b: hashlib.sha256(b).hexdigest()

def main():
    seal_bytes = (SOURCE / 'seal.json').read_bytes()
    assert sha(seal_bytes) == 'bf17889754e7ef436fababcf8b96f5109285f982bcc48258a0b9e204a95b1751'
    manifest = json.loads((SOURCE / 'source-manifest.json').read_text())['members']
    assert len(manifest) == 144
    for member in manifest:
        content = (SOURCE / 'source/vm' / member['path']).read_bytes()
        assert len(content) == member['bytes'] and sha(content) == member['sha256']
    work = HERE / 'owned-work'
    work.mkdir(exist_ok=False)
    argv = [str(RUSTC), '--crate-name', 'mixer_vm', '--edition=2021', '--target',
            'aarch64-apple-darwin', '-C', 'opt-level=0', '-C', 'overflow-checks=yes',
            '-C', 'panic=unwind']
    for feature in ['experimental-swift-reactor', 'experimental-swift-wasi',
                    'experimental-stream-validation', 'experimental-function-cache']:
        argv += ['--cfg', 'feature="' + feature + '"']
    argv += ['--crate-type', 'rlib', str(SOURCE / 'source/vm/src/lib.rs'),
             '--emit=mir', '-Zmir-opt-level=0', '-Zmir-include-spans=yes',
             '-o', str(work / 'independent.mir')]
    env = {'PATH': '/usr/bin:/bin', 'TMPDIR': str(work),
           'CARGO_MANIFEST_DIR': str(SOURCE / 'source/vm'), 'RUSTC_BOOTSTRAP': '1'}
    version = subprocess.run([str(RUSTC), '--version', '--verbose'], capture_output=True,
                             check=True, timeout=10).stdout.decode()
    started = time.monotonic()
    child = subprocess.Popen(argv, cwd=REPO, env=env, start_new_session=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    actions, timed_out = [], False
    try:
        stdout, stderr = child.communicate(timeout=55)
    except subprocess.TimeoutExpired:
        timed_out = True
        for sig, timeout in [(signal.SIGTERM, 2), (signal.SIGKILL, 2)]:
            try:
                os.killpg(child.pid, sig)
                actions.append(sig.name + ' owned compiler group')
            except ProcessLookupError:
                pass
            try:
                stdout, stderr = child.communicate(timeout=timeout)
                break
            except subprocess.TimeoutExpired:
                continue
        else:
            stdout, stderr = child.communicate()
    (HERE / 'compiler.stdout').write_bytes(stdout)
    (HERE / 'compiler.stderr').write_bytes(stderr)
    output = work / 'independent.mir'
    result = dict(schema=1, argv=argv, cwd=str(REPO), environment=env,
                  python_version=platform.python_version(), rustc_version=version,
                  compiler_sha256=sha(RUSTC.read_bytes()), timeout_seconds=55,
                  elapsed_seconds=time.monotonic()-started, exit_code=child.returncode,
                  owned_process_group=child.pid, new_session=True, child_reaped=True,
                  timed_out=timed_out, cleanup_actions=actions,
                  stdout_bytes=len(stdout), stderr_bytes=len(stderr),
                  stdout_sha256=sha(stdout), stderr_sha256=sha(stderr),
                  output_bytes=output.stat().st_size if output.exists() else None,
                  output_sha256=sha(output.read_bytes()) if output.exists() else None,
                  source_seal_sha256=sha(seal_bytes), source_members=144,
                  scope='rustc metadata only; no engine/VM/writer/native/UI/capture/process inventory')
    (HERE / 'compiler-receipt.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))
    assert not timed_out and child.returncode == 0

if __name__ == '__main__':
    main()
