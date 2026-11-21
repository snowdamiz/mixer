#!/usr/bin/env python3
"""Run a compact Swift event through the owned host VM and resolve its trap."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE.parent / 'fieldlog-installed-guest'))
from replay_swift_diagnostics import Reader, custom, sections
from run import ROOT, build_compact_guest, replay_abi
from qualification_support import CommandRecorder, clean_environment, digest, strict_json

PIN = '34a165c8783e9868c7c1eb655a88f472445ca190'
RUNTIME = ROOT / 'experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime'
GUEST = HERE / 'SwiftEventGuest.swift'
PROBE = HERE / 'OwnedEventProbe.swift'
HOST_SOURCES = [RUNTIME / f'{name}.swift' for name in ('Types', 'Failure', 'GuestDebugLines')]
PINNED = ('vm/Cargo.toml', 'vm/Cargo.lock', 'vm/src', 'vm/include', 'compiler/qualification_support.py',
          'compiler/experiments/fieldlog-installed-guest', 'compiler/experiments/fieldlog-reactor/support.py',
          'compiler/experiments/profile-budget/analyze.py', str(RUNTIME.relative_to(ROOT)))


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def artifact(path):
    return {'bytes': path.stat().st_size, 'sha256': digest(path)}


def inspect_modules(paths, receipt):
    receipt['wasm'] = {key: artifact(path) for key, path in paths.items()}
    parsed = {}
    for label, path in paths.items():
        data = path.read_bytes()
        replay_abi.check_descriptors(data)
        parsed[label] = list(sections(data))
    executable = {key: [(kind, payload) for kind, _, _, _, payload in entries if kind]
                  for key, entries in parsed.items()}
    tables = {}
    for label, entries in parsed.items():
        if label == 'alternate':
            require(dict(executable[label])[10] == dict(executable['matched'])[10],
                    'alternate instruction bytes differ')
        else:
            require(executable[label] == executable['matched'], f'{label} executable sections differ')
        lines = [payload for kind, name, _, _, payload in entries if kind == 0 and name == b'.debug_line']
        require(len(lines) == (0 if label == 'stripped' else 1), f'{label} line-table count')
        if lines:
            tables[label] = hashlib.sha256(lines[0]).hexdigest()
    require(tables['matched'] != tables['alternate'] == tables['wrongTable'],
            'wrong-table candidate must contain only the alternate line table')
    receipt['lineTableSHA256'] = tables
    receipt['sameExecutableSectionsAsMatched'] = ['stripped', 'wrongTable']
    return parsed['matched']


def check_observations(rows, parsed, wasm, disassembly, line_dump):
    require(set(rows) == {'matched', 'stripped', 'wrongTable', 'alternate'}, 'missing owned event results')
    matched = rows['matched']
    for label, row in rows.items():
        expected = label != 'wrongTable'
        require(row['metadataIdentityMatched'] is expected, f'{label} diagnostic artifact identity')
        require(row['eventResults'] == [0, 1] and row['nativeStatus'] == 2 and row['code'] == 'unreachable'
                and row['closedHandleStatus'] == 3, f'{label} event path or session closure')
        for field in ('functionIndex', 'absoluteOffset', 'fuelUsed', 'initialDocument'):
            require(row[field] == matched[field], f'{label} differs at {field}')
        if label in ('matched', 'alternate'):
            marker = 'expected diagnostic' if label == 'matched' else 'alternate diagnostic'
            [line] = [number for number, source in enumerate(GUEST.read_text().splitlines(), 1)
                      if source.strip() == f'precondition(!rejected) // {marker}']
            require(row.get('file') == GUEST.name and row.get('line') == line,
                    f'{label} did not resolve to the executed Swift precondition')
        else:
            require(not {'file', 'line', 'column'} & row.keys(), f'{label} fabricated a source location')
    require(strict_json(matched['initialDocument']) == {
        'schemaVersion': 1, 'revision': 1, 'root': {
            'id': 'button', 'kind': 'button', 'properties': {'label': 'Validate'},
            'actions': [{'id': 'validate', 'event': 'activate'}], 'children': [],
        }}, 'unexpected initial frame')

    [(_, _, _, end, code)] = [section for section in parsed if section[0] == 10]
    code_start = end - len(code)
    body = Reader(code)
    count = body.uint()
    require(0 <= matched['functionIndex'] < count, 'runtime function index outside code section')
    for _ in range(matched['functionIndex'] + 1):
        size = body.uint()
        start = body.position
        body.take(size)
    pc = matched['absoluteOffset'] - code_start
    require(start <= pc < body.position and wasm.read_bytes()[matched['absoluteOffset']] == 0,
            'runtime position is outside its function body or differs from unreachable')
    require(re.search(rf'^\s*0*{matched["absoluteOffset"]:x}:\s+00\s+unreachable\s*$', disassembly, re.MULTILINE),
            'LLVM did not decode unreachable at the owned runtime position')
    [file_index] = re.findall(rf'file_names\[\s*(\d+)\]:\s+name: "{re.escape(GUEST.name)}"\s+dir_index: 1\b',
                              line_dump)
    directory = re.escape(str(HERE.relative_to(ROOT)))
    require(re.search(rf'^include_directories\[\s*1\] = "{directory}"$', line_dump, re.MULTILINE)
            and re.search(rf'^0x0*{pc:x}\s+{matched["line"]}\s+{matched["column"]}\s+{file_index}\s',
                          line_dump, re.MULTILINE), 'LLVM did not confirm the exact relative Swift source row')
    return {'functionIndex': matched['functionIndex'], 'absoluteWasmOffset': matched['absoluteOffset'],
            'codeRelativeOffset': pc, 'instruction': 'unreachable',
            'file': str(GUEST.relative_to(ROOT)), 'line': matched['line'], 'column': matched.get('column')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('name', help='Unused directory name under verification/local')
    parser.add_argument('--source-revision', default=PIN,
                        help='Exact checkout containing the diagnostic fixture. Engine inputs must still match the v79 pin.')
    parser.add_argument('--developer-dir', type=Path,
                        help='Xcode developer directory for the host Swift compiler and dwarfdump.')
    parser.add_argument('--toolchain', type=Path, default=Path.home() /
                        'Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin')
    parser.add_argument('--cargo', type=Path, default=Path.home() /
                        '.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/cargo')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}', args.name) or args.name in ('.', '..'):
        parser.error('name must be a bounded path component')
    if not re.fullmatch(r'[0-9a-f]{40}', args.source_revision):
        parser.error('source revision must be a full lowercase Git commit hash')
    out = ROOT / 'verification/local' / args.name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.mkdir()
    for name in ('logs', 'tmp', 'cargo-home'):
        (out / name).mkdir()
    env = clean_environment()
    env.update(TMPDIR=str(out / 'tmp'), CARGO_HOME=str(out / 'cargo-home'),
               PATH=str(args.cargo.parent) + ':/usr/bin:/bin:/usr/sbin:/sbin',
               GIT_NO_REPLACE_OBJECTS='1', GIT_NO_LAZY_FETCH='1')
    if args.developer_dir is not None:
        env['DEVELOPER_DIR'] = str(args.developer_dir.absolute())
    commands = []
    recorder = CommandRecorder(out / 'logs', commands, ROOT)
    receipt = {'status': 'incomplete', 'scope': 'local macOS owned VM, compact Swift UI v1 event',
               'commands': commands}
    stage = 'source pin'
    sources = [GUEST, PROBE, Path(__file__).resolve()]
    fixture_paths = tuple(str(path.relative_to(ROOT)) for path in sources)

    def run(name, *argv, timeout=35):
        return recorder.run(name, argv, env=env, timeout=timeout)

    def check_pin(label):
        run('pin-' + label, '/usr/bin/git', 'diff', '--quiet', PIN, '--', *PINNED)
        run('pin-index-' + label, '/usr/bin/git', 'diff', '--cached', '--quiet', PIN, '--', *PINNED)
        require(not run('untracked-' + label, '/usr/bin/git', 'ls-files', '--others', '--', *PINNED),
                'unpinned file under an owning input path')
        if args.source_revision != PIN:
            tracked = run('fixture-tracked-' + label, '/usr/bin/git', 'ls-files',
                          '--', *fixture_paths).splitlines()
            require(set(tracked) == set(fixture_paths), 'diagnostic fixture files must be tracked')
            run('fixture-pin-' + label, '/usr/bin/git', 'diff', '--quiet',
                args.source_revision, '--', *fixture_paths)
            run('fixture-index-' + label, '/usr/bin/git', 'diff', '--cached', '--quiet',
                args.source_revision, '--', *fixture_paths)

    try:
        receipt['baseRevision'] = run('revision', '/usr/bin/git', 'rev-parse', 'HEAD').strip()
        require(receipt['baseRevision'] == args.source_revision, 'checkout does not match source revision')
        receipt['baseTree'] = run('tree', '/usr/bin/git', 'rev-parse', 'HEAD^{tree}').strip()
        receipt['engineInputRevision'] = PIN
        check_pin('before')
        receipt['diagnosticInputs'] = {str(path.relative_to(ROOT)): digest(path) for path in sources}

        stage = 'toolchain'
        toolchain = args.toolchain
        if args.developer_dir is not None:
            receipt['developerDir'] = env['DEVELOPER_DIR']
            receipt['xcode'] = run('xcode', '/usr/bin/xcodebuild', '-version').strip()
        receipt['versions'] = {label: run(label, executable, *flags).strip() for label, executable, flags in (
            ('host', '/usr/bin/sw_vers', ()), ('host-swift', '/usr/bin/swiftc', ('--version',)),
            ('guest-swift', toolchain / 'swiftc', ('--version',)), ('wasm-ld', toolchain / 'wasm-ld', ('--version',)),
            ('llvm-objcopy', toolchain / 'llvm-objcopy', ('--version',)),
            ('llvm-objdump', toolchain / 'llvm-objdump', ('--version',)),
            ('llvm-dwarfdump', '/usr/bin/dwarfdump', ('--version',)),
            ('rustc', args.cargo.parent / 'rustc', ('--version',)), ('cargo', args.cargo, ('--version',)),
        )}
        stage = 'compact Wasm build and identity'
        matched = build_compact_guest(run, toolchain, out, 'matched', [GUEST], diagnostics=True)
        alternate = build_compact_guest(run, toolchain, out, 'alternate', [GUEST], diagnostics=True,
                                        flags=['-D', 'ALTERNATE_LINE'])
        stripped = out / 'stripped.wasm'
        run('strip', toolchain / 'llvm-objcopy', '--remove-section=.debug_line', matched, stripped)
        original = matched.read_bytes()
        [(start, end)] = [(start, end) for _, name, start, end, _ in sections(original)
                          if name == b'.debug_line']
        [replacement] = [payload for _, name, _, _, payload in sections(alternate.read_bytes())
                         if name == b'.debug_line']
        wrong = out / 'wrong-table.wasm'
        wrong.write_bytes(original[:start] + custom(b'.debug_line', replacement) + original[end:])
        modules = {'matched': matched, 'alternate': alternate, 'stripped': stripped, 'wrongTable': wrong}
        parsed = inspect_modules(modules, receipt)

        stage = 'owned VM and host probe build'
        target = out / 'rust'
        run('vm-build', args.cargo, 'build', '--offline', '--locked', '--release', '--lib',
            '--features', 'experimental-capability-native', '--manifest-path', ROOT / 'vm/Cargo.toml',
            '--target-dir', target, timeout=120)
        archive = target / 'release/libmixer_vm.a'
        receipt['vmArchive'] = artifact(archive)
        include = ROOT / 'vm/include'
        (out / 'module.modulemap').write_text(
            f'module CMixerVMCapability {{ header "{include}/mixer_vm_guest_ui.h" export * }}\n')
        binary = out / 'probe'
        run('probe-build', '/usr/bin/swiftc', '-swift-version', '6', '-O', '-whole-module-optimization',
            '-parse-as-library', '-module-cache-path', out / 'swift-modules', '-I', out,
            PROBE, *HOST_SOURCES, archive, '-o', binary, timeout=60)
        receipt['probe'] = artifact(binary)

        stage = 'owned event execution'
        rows = strict_json(run('ownership-and-events', binary, matched, stripped, alternate, wrong, timeout=10))
        receipt['observations'] = rows
        stage = 'executed position and source'
        disassembly = run('disassembly', toolchain / 'llvm-objdump', '-d', matched)
        line_dump = run('line-table', '/usr/bin/dwarfdump', '--debug-line', matched)
        receipt['diagnostic'] = check_observations(rows, parsed, matched, disassembly, line_dump)
        require(receipt['wasm'] == {key: artifact(path) for key, path in modules.items()},
                'Wasm artifact changed during replay')
        require(receipt['diagnosticInputs'] == {str(path.relative_to(ROOT)): digest(path) for path in sources},
                'diagnostic source changed during replay')
        check_pin('after')
        receipt['status'] = 'passed'
    except Exception as error:
        receipt['firstFailure'] = {'stage': stage, 'error': str(error)}
        if commands and commands[-1].get('error') and commands[-1]['terminalCustody'] == 'TERMINAL':
            stderr = out / 'logs' / commands[-1]['stderr']['path']
            with stderr.open('rb') as stream:
                receipt['firstFailure']['stderrPrefix'] = stream.read(4096).decode('utf-8', errors='replace')
        raise
    finally:
        path = out / 'receipt.json'
        path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
        print(path, flush=True)


if __name__ == '__main__':
    main()
