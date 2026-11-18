#!/usr/bin/env python3
"""Build the installed Swift guests and replay source diagnostics on the macOS host."""
import argparse
import json
from pathlib import Path
import re
import shutil
import sys

from run import HERE, ROOT, build_compact_guest, replay_abi
from analyze import Reader
from qualification_support import CommandRecorder, clean_environment, digest


def uleb(value):
    result = bytearray()
    while value >= 128:
        result.append((value & 127) | 128)
        value >>= 7
    return bytes(result + bytes([value]))


def custom(name, payload):
    content = uleb(len(name)) + name + payload
    return b'\x00' + uleb(len(content)) + content


def sections(data):
    reader = Reader(data)
    if bytes(reader.take(8)) != b'\x00asm\x01\x00\x00\x00':
        raise ValueError('unexpected compiler output header')
    while reader.position < len(reader.data):
        start = reader.position
        kind = reader.byte()
        payload = Reader(reader.take(reader.uint()))
        name = bytes(payload.take(payload.uint())) if kind == 0 else None
        yield kind, name, start, reader.position, bytes(payload.data[payload.position:])


def write_controls(fault, stripped):
    out = fault.parent
    data = fault.read_bytes()
    parsed = list(sections(data))
    [(_, _, start, end, line)] = [section for section in parsed if section[1] == b'.debug_line']
    if [(kind, payload) for kind, _, _, _, payload in parsed if kind] != [
            (kind, payload) for kind, _, _, _, payload in sections(stripped.read_bytes()) if kind]:
        raise ValueError('adding debug information changed the executable sections')

    controls = {
        'malformed': data[:start] + custom(b'.debug_line', line + b'\xff') + data[end:],
        'unsupported': data[:start] + custom(b'.debug_line', line[:4] + b'\x05\x00' + line[6:]) + data[end:],
        'duplicate': data + data[start:end],
        'oversized': data[:start] + custom(b'.debug_line', bytes(262_145)) + data[end:],
        'external': data + custom(b'external_debug_info', b'\x0adebug.wasm'),
    }
    for label, contents in controls.items():
        (out / f'fault-{label}.wasm').write_bytes(contents)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('name', help='New directory name under verification/local')
    parser.add_argument('--toolchain', type=Path, default=Path.home() /
                        'Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin')
    parser.add_argument('--cargo', type=Path, default=Path.home() /
                        '.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/cargo')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}', args.name):
        parser.error('name must be a bounded path component')
    out = ROOT / 'verification/local' / args.name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.mkdir()
    for name in ('logs', 'tmp', 'lib', 'host/experimental-capability-runtime'):
        (out / name).mkdir(parents=True)

    env = clean_environment()
    env.update(TMPDIR=str(out / 'tmp'), L03_GUEST_FIXTURES=str(out))
    env['PATH'] = str(args.cargo.parent) + ':' + env['PATH']
    commands = []
    recorder = CommandRecorder(out / 'logs', commands, ROOT)
    receipt = {'status': 'incomplete', 'scope': 'macOS host Swift bridge', 'commands': commands}

    def run(name, *argv, timeout=120):
        return recorder.run(name, argv, env=env, timeout=timeout)

    try:
        git, swift = (shutil.which(name) for name in ('git', 'swift'))
        receipt['baseRevision'] = run('revision', git, 'rev-parse', 'HEAD').strip()
        receipt['versions'] = {
            label: run(label, executable, *flags).strip()
            for label, executable, flags in (
                ('host', '/usr/bin/sw_vers', ()), ('host-swift', swift, ('--version',)),
                ('guest-swift', args.toolchain / 'swiftc', ('--version',)),
                ('wasm-ld', args.toolchain / 'wasm-ld', ('--version',)),
                ('llvm-objcopy', args.toolchain / 'llvm-objcopy', ('--version',)),
                ('rustc', args.cargo.parent / 'rustc', ('--version',)),
            )
        }
        inputs = run('inputs', git, 'ls-files', '--cached', '--others', '--exclude-standard', '-z', '--',
                     'experimental-capability-runtime/Package.swift', 'experimental-capability-runtime/Sources',
                     'experimental-capability-runtime/Tests', 'sdk/Package.swift', 'sdk/Package.resolved', 'sdk/Sources',
                     'vm/Cargo.toml', 'vm/Cargo.lock', 'vm/include', 'vm/src', str(HERE.relative_to(ROOT)),
                     'compiler/qualification_support.py', 'compiler/experiments/fieldlog-reactor/support.py',
                     'compiler/experiments/profile-budget/analyze.py')
        receipt['inputSHA256'] = {name: digest(ROOT / name) for name in sorted(set(inputs.split('\0')) - {''})}

        common = HERE / 'TaskCompletion.swift'
        fault_sources = [common, HERE / 'DiagnosticGuest.swift']
        toolchain = args.toolchain
        for name, sources, diagnostics, optimization in (
            ('baseline-compact', [common, HERE / 'InstalledGuest.swift'], True, '-Osize'),
            ('fault-osize', fault_sources, True, '-Osize'),
            ('fault-opt', fault_sources, True, '-O'),
        ):
            wasm = build_compact_guest(run, toolchain, out, name, sources, diagnostics=diagnostics,
                                       optimization=optimization)
            replay_abi.check_descriptors(wasm.read_bytes())
        stripped = out / 'fault.wasm'
        run('fault-strip-line-table', toolchain / 'llvm-objcopy', '--remove-section=.debug_line',
            out / 'fault-osize.wasm', stripped)
        write_controls(out / 'fault-osize.wasm', stripped)
        receipt['fixtureSHA256'] = {path.name: digest(path) for path in sorted(out.glob('*.wasm'))}

        run('rust-build', args.cargo, 'build', '--locked', '--offline', '--release', '--lib', '--features',
            'experimental-capability-native', '--manifest-path', ROOT / 'vm/Cargo.toml', '--target-dir', out / 'rust')
        archive = out / 'rust/release/libmixer_vm.a'
        receipt['vmArchiveSHA256'] = digest(archive)
        (out / 'lib/libmixer_vm_capability_experimental.a').symlink_to(archive)

        # Resolve the pinned graph without creating a lockfile in the checkout.
        package = out / 'host/experimental-capability-runtime'
        (package.parent / 'sdk').symlink_to(ROOT / 'sdk', target_is_directory=True)
        for entry in ('Package.swift', 'Sources', 'Tests'):
            (package / entry).symlink_to(ROOT / 'experimental-capability-runtime' / entry)
        shutil.copyfile(ROOT / 'sdk/Package.resolved', package / 'Package.resolved')
        output = run('swift-test', swift, 'test', '--package-path', package, '--scratch-path', out / 'swiftpm',
                     '--disable-prefetching', '--skip-update', '--force-resolved-versions',
                     '-Xcc', '-I', '-Xcc', ROOT / 'vm/include', '-Xlinker', '-L', '-Xlinker', out / 'lib', timeout=240)
        receipt['observations'] = [line for line in output.splitlines()
                                   if line.startswith('L03 ') or 'Test run with ' in line]
        if len([line for line in receipt['observations'] if line.endswith(' retired and drained')]) != 10:
            raise ValueError('installed-guest replay did not run all variants')
        for name, expected in receipt['inputSHA256'].items():
            if digest(ROOT / name) != expected:
                raise ValueError(f'replay input changed: {name}')
        receipt['status'] = 'passed'
        print(out / 'receipt.json')
    finally:
        (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    main()
