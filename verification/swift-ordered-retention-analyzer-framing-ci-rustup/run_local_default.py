"""Owned Homebrew-like shared-binary chain; one local selected Rust execution."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    out = OWN / 'commands/local-default-closure-2'
    out.mkdir()
    scratch = OWN / 'owned-shim-scratch-2'
    scratch.mkdir()
    marker = {'owner': '/root/swift_analyzer_framing_ci', 'path': str(scratch), 'nonce': str(uuid.uuid4())}
    (scratch / 'ownership.json').write_text(json.dumps(marker) + '\n')
    stamp = scratch.stat()
    source = Path('/opt/homebrew/Cellar/rustup/1.29.1/libexec/bin/rustup').resolve(strict=True)
    require(source.read_bytes()[:2] != b'#!', 'Use the shared binary, not the Homebrew shell wrapper')
    cellar = scratch / 'opt/homebrew/Cellar/rustup/1.29.1/bin'
    cellar.mkdir(parents=True)
    shared = cellar / 'rustup-init'
    shutil.copyfile(source, shared)
    shared.chmod(0o755)
    brew_bin = scratch / 'opt/homebrew/bin'
    brew_bin.mkdir()
    (brew_bin / 'rustc').symlink_to(shared)
    cargo_bin = scratch / 'cargo/bin'
    cargo_bin.mkdir(parents=True)
    (cargo_bin / 'rustc').symlink_to(brew_bin / 'rustc')
    overrides = {'PATH': str(cargo_bin) + os.pathsep + os.environ.get('PATH', ''),
                 'RUSTUP_AUTO_INSTALL': '0', 'RUSTUP_TOOLCHAIN': 'stable-aarch64-apple-darwin'}
    argv = [sys.executable, '-B', 'scripts/ci/check-analyzer-framing.py',
            '--output', str(OWN / 'local-default-darwin-2')]
    command = {'argv': argv, 'cwd': str(ROOT), 'started_utc': datetime.now(timezone.utc).isoformat(),
               'python': platform.python_version(), 'timeout_seconds': 420, 'environment_overrides': overrides,
               'setup_collector_sha256': sha(Path(__file__)),
               'owned_shim_chain': {'source_binary': str(source), 'source_sha256': sha(source),
                                    'copied_binary': str(shared), 'copied_sha256': sha(shared),
                                    'symlinks': {str(cargo_bin / 'rustc'): str(brew_bin / 'rustc'), str(brew_bin / 'rustc'): str(shared)},
                                    'ownership': marker, 'identity': [stamp.st_dev, stamp.st_ino],
                                    'local_PATH_originally_had_rustc': shutil.which('rustc') is not None,
                                    'matches_remote_dispatch_basename_and_chain': True,
                                    'remote_rustup_version': '1.29.0', 'local_rustup_package_version': '1.29.1',
                                    'remote_CI_qualification': False}}
    (out / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
    returned = False
    try:
        with (out / 'stdout').open('wb') as stdout, (out / 'stderr').open('wb') as stderr:
            result = subprocess.run(argv, cwd=ROOT, env=dict(os.environ, **overrides),
                                    stdout=stdout, stderr=stderr, timeout=420)
        returned = True
        command.update(exit=result.returncode, stdout_sha256=sha(out / 'stdout'), stderr_sha256=sha(out / 'stderr'))
    finally:
        command['child_returned'] = returned
        if returned:
            current = scratch.stat()
            require((current.st_dev, current.st_ino) == (stamp.st_dev, stamp.st_ino)
                    and json.loads((scratch / 'ownership.json').read_text()) == marker,
                    'Owned shim scratch changed; preserve')
            shutil.rmtree(scratch)
            command['owned_shim_cleanup'] = {'removed': not scratch.exists(), 'child_returned': True,
                                             'only_exact_owned_tree': True}
        (out / 'result.json').write_text(json.dumps(command, indent=2) + '\n')
    print((out / 'stdout').read_text())
    print((out / 'stderr').read_text())
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
