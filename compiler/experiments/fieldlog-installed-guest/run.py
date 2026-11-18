#!/usr/bin/env python3
"""Build and compare the two fixed FieldLog task guests with the installed UI bridge."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE.parent / 'fieldlog-reactor'))
import support
import analyze
import qualification_support
import replay_abi
from qualification_support import CommandRecorder, clean_environment, digest, strict_json

FIELDLOG = '552559d2d3278abb9b1aa7dcf0288102c09a202b'
WORKSPACE_HASH = '6f11d54b41081b20429be486f074f886ec6f53083753bf7a19c67a3c5d19e014'
WORKSPACE_API = 'repos/snowdamiz/fieldlog/contents/Sources/FieldLogModels/Workspace.swift'
SDK_NAME = 'swift-6.3.3-RELEASE_wasm'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('name', help='Unused directory name under verification/local')
    parser.add_argument('--workspace', type=Path, help='Local copy of the pinned Workspace.swift')
    parser.add_argument('--cargo', type=Path, default=Path.home() / '.rustup/toolchains/stable-aarch64-apple-darwin/bin/cargo')
    parser.add_argument('--toolchain', type=Path, default=Path.home() /
                        'Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin')
    parser.add_argument('--sdk', type=Path, default=Path.home() /
                        f'.swiftpm/swift-sdks/{SDK_NAME}.artifactbundle/{SDK_NAME}/wasm32-unknown-wasip1')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}', args.name):
        parser.error('name must be a bounded path component')
    out = ROOT / 'verification/local' / args.name
    out.mkdir(exist_ok=False)
    for name in ('tmp', 'logs', 'lib', 'host/src'):
        (out / name).mkdir(parents=True)
    env = clean_environment()
    env['TMPDIR'] = str(out / 'tmp')
    env['PATH'] = str(args.cargo.parent) + ':' + env['PATH']
    commands = []
    recorder = CommandRecorder(out / 'logs', commands, ROOT)
    receipt = dict(status='running', fieldlogRevision=FIELDLOG, workspaceSHA256=WORKSPACE_HASH, commands=commands)

    def run(name, *argv):
        return recorder.run(name, argv, env=env, timeout=90)

    def manifest():
        inputs = run('mixer-inputs', shutil.which('git'), 'ls-files',
                     '--cached', '--others', '--exclude-standard', '-z', '--',
                     'vm/src', 'vm/include', 'vm/Cargo.toml', 'vm/Cargo.lock',
                     'experimental-capability-runtime/Sources', 'experimental-capability-runtime/Package.swift',
                     'sdk/Sources', 'sdk/Package.swift', 'sdk/Package.resolved').split('\0')
        paths = {ROOT / name for name in inputs if name}
        paths.update(HERE / name for name in ('HostProbe.swift', 'InstalledGuest.swift',
                     'TaskCompletion.swift', 'ProbePackage.swift.in'))
        paths.add(Path(__file__).resolve())
        paths.update(Path(module.__file__).resolve() for module in
                     (support, analyze, qualification_support, replay_abi))
        return {str(path.relative_to(ROOT)): digest(path) for path in sorted(paths)}

    try:
        swift = shutil.which('swift')
        swiftc, linker = (args.toolchain / name for name in ('swiftc', 'wasm-ld'))
        receipt['versions'] = dict(guestSwift=run('guest-swift-version', swiftc, '--version').strip(),
            linker=run('linker-version', linker, '--version').strip(),
            hostSwift=run('host-swift-version', swift, '--version').strip(),
            rust=run('rust-version', args.cargo.parent / 'rustc', '--version').strip(),
            replayPython=sys.version,
            host=run('host-version', '/usr/bin/sw_vers').strip())
        receipt['mixerRevision'] = run('mixer-revision', shutil.which('git'), 'rev-parse', 'HEAD').strip()
        receipt['mixerInputs'] = manifest()

        workspace = out / 'host/src/Workspace.swift'
        if args.workspace:
            shutil.copyfile(args.workspace, workspace)
        else:
            source = run('workspace-source', shutil.which('gh'), 'api', '-H', 'Accept: application/vnd.github.raw+json',
                         f'{WORKSPACE_API}?ref={FIELDLOG}')
            workspace.write_bytes(source.encode())
        if digest(workspace) != WORKSPACE_HASH:
            raise ValueError('Pinned FieldLog Workspace.swift content differs')

        source = [HERE / 'TaskCompletion.swift', HERE / 'InstalledGuest.swift']
        exports = [f'--export={name}' for name in replay_abi.SIGNATURES]
        compile_flags = ['-whole-module-optimization', '-Osize', '-parse-as-library']
        receipt['guests'] = {}
        receipt['descriptorControls'] = {}
        for variant, flags in [('baseline', []), ('reviewed', ['-D', 'REQUIRE_REVIEW'])]:
            obj = out / f'{variant}.o'
            wasm = out / f'{variant}.wasm'
            run(f'{variant}-swift', swiftc, '-target', 'wasm32-unknown-none-wasm', '-enable-experimental-feature', 'Embedded',
                *compile_flags, '-Xfrontend', '-disable-stack-protector', *flags, '-emit-object', *source, '-o', obj)
            run(f'{variant}-link', linker, '--no-entry', '--gc-sections', '--strip-all', '-z', 'stack-size=16384',
                '--max-memory=65536', *exports, obj, '-o', wasm)
            data = wasm.read_bytes()
            info = replay_abi.check_descriptors(data)
            receipt['guests'][variant] = dict(bytes=len(data), sha256=digest(wasm),
                gzipBytes=len(gzip.compress(data, compresslevel=9, mtime=0)), **info)
            receipt['descriptorControls'][variant] = replay_abi.negative_controls(data, info)

        full = out / 'full-sdk-baseline.wasm'
        resource = args.sdk / 'swift.xctoolchain/usr/lib/swift_static'
        run('full-sdk-swift', swiftc, '-target', 'wasm32-unknown-wasip1', '-sdk', args.sdk / 'WASI.sdk',
            '-resource-dir', resource, '-module-cache-path', out / 'wasi-cache', '-static-stdlib', *compile_flags,
            '-Xclang-linker', '-resource-dir', '-Xclang-linker', resource / 'clang',
            '-Xclang-linker', '-mexec-model=reactor', '-Xlinker', '--strip-all',
            *(item for export in exports for item in ('-Xlinker', export)), *source, '-o', full)
        receipt['fullSDKControl'] = dict(bytes=full.stat().st_size, sha256=digest(full))

        run('owned-vm-build', args.cargo, 'build', '--offline', '--release', '--lib', '--features',
            'experimental-capability-native', '--manifest-path', ROOT / 'vm/Cargo.toml', '--target-dir', out / 'rust')
        library = out / 'rust/release/libmixer_vm.a'
        receipt['vmArchiveSHA256'] = digest(library)
        (out / 'lib/libmixer_vm_capability_experimental.a').symlink_to(library)
        shutil.copyfile(HERE / 'ProbePackage.swift.in', out / 'host/Package.swift')
        shutil.copyfile(ROOT / 'sdk/Package.resolved', out / 'host/Package.resolved')
        for name in ('HostProbe.swift', 'TaskCompletion.swift'):
            shutil.copyfile(HERE / name, out / 'host/src' / name)
        build_flags = ['--package-path', out / 'host', '--scratch-path', out / 'swiftpm']
        run('host-build', swift, 'build', *build_flags, '--disable-prefetching', '--skip-update', '--force-resolved-versions',
            '-Xcc', '-I', '-Xcc', ROOT / 'vm/include', '-Xlinker', '-L', '-Xlinker', out / 'lib')
        bin_path = Path(run('host-bin-path', swift, 'build', *build_flags, '--show-bin-path').strip())
        receipt['observations'] = strict_json(run('owned-vm-probe', bin_path / 'Probe',
                                                  out / 'baseline.wasm', out / 'reviewed.wasm', full))
        receipt['fullSDKControl']['rejection'] = (out / 'logs/owned-vm-probe.stderr').read_text().strip()
        receipt['mixerInputDigest'] = hashlib.sha256(json.dumps(receipt['mixerInputs'], sort_keys=True,
                                                                separators=(',', ':')).encode()).hexdigest()
        receipt['status'] = 'pass'
    finally:
        (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    main()
