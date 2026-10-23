#!/usr/bin/env python3
"""Freeze corrected VM, run integration matrices, measure named final roles."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TREE = HERE / 'inputs'
BUILD = HERE / 'build'
sha = lambda data: hashlib.sha256(data).hexdigest()
env = dict(os.environ, PATH='/opt/homebrew/opt/rustup/bin:' + os.environ['PATH'], CARGO_TARGET_DIR=str(BUILD / 'target'))
receipt = {'schema': 'mixer.swift-final-boundary-accounting.v1', 'status': 'running',
           'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'commands': [], 'scope': 'Corrected foundation and compiling private executor layout only; no runnable executor or target initialization/invocation.'}


def save():
    (HERE / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')


def run(name, argv, cwd=TREE / 'vm', rejected=None):
    start = time.monotonic()
    result = subprocess.run(list(map(str, argv)), cwd=cwd, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=900)
    logfile = HERE / 'logs' / (name + '.log')
    logfile.parent.mkdir(exist_ok=True)
    logfile.write_bytes(result.stdout)
    receipt['commands'].append({'name': name, 'argv': list(map(str, argv)), 'cwd': str(cwd),
        'exit_code': result.returncode, 'expected_rejection': rejected,
        'seconds': round(time.monotonic() - start, 3), 'log': str(logfile.relative_to(ROOT)),
        'log_sha256': sha(result.stdout)})
    text = result.stdout.decode(errors='replace')
    save()
    if rejected is None:
        assert result.returncode == 0, name
    else:
        assert result.returncode != 0 and rejected in text, name
    print(name, result.returncode, flush=True)
    return text


def main():
    TREE.mkdir(exist_ok=False)
    raw = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z', '--', 'vm'], cwd=ROOT)
    paths = sorted(set(p.decode() for p in raw.split(b'\0') if p))
    paths += ['docs/swift-final-boundary-accounting.md', str(Path(__file__).relative_to(ROOT))]
    files = {}
    for name in paths:
        data = (ROOT / name).read_bytes()
        files[name] = sha(data)
        dest = TREE / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    receipt['base_revision'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    receipt['source_tree_sha256'] = sha(json.dumps(files, sort_keys=True, separators=(',', ':')).encode())
    (HERE / 'input-manifest.json').write_text(json.dumps({'files': files, 'source_tree_sha256': receipt['source_tree_sha256']}, indent=2) + '\n')
    receipt['environment'] = {'PATH_prefix': '/opt/homebrew/opt/rustup/bin', 'CARGO_TARGET_DIR': env['CARGO_TARGET_DIR']}
    save()
    for name, argv in [('rustc-version', ['rustc', '-Vv']), ('cargo-version', ['cargo', '-V']), ('host', ['uname', '-a'])]:
        run(name, argv)
    features = [('neither', []), ('span', ['--features', 'experimental-span-execution']),
        ('swift', ['--features', 'experimental-swift-reactor']),
        ('swift-cache', ['--features', 'experimental-swift-reactor,experimental-function-cache']),
        ('swift-span', ['--features', 'experimental-swift-reactor,experimental-span-execution']),
        ('all', ['--all-features'])]
    for mode, opts in [('debug', []), ('release', ['--release'])]:
        for label, flags in features:
            # The all-features run also executes every integration and doc test.
            lib = [] if label == 'all' else ['--lib']
            run(label + '-' + mode, ['cargo', 'test', '--locked'] + opts + lib + flags)
        run('final-boundary-' + mode, ['cargo', 'test', '--locked'] + opts +
            ['--lib', '--features', 'experimental-swift-reactor', 'final_boundary_', '--', '--nocapture', '--test-threads=1'])
        run('executor-layout-' + mode, ['cargo', 'test', '--locked'] + opts +
            ['--lib', '--features', 'experimental-swift-reactor', 'swift_executor_layout', '--', '--nocapture', '--test-threads=1'])
    for label, flags in [('minimal', features[2][1]), ('combined', features[4][1])]:
        run('clippy-' + label, ['cargo', 'clippy', '--locked', '--lib'] + flags + ['--', '-D', 'warnings'])
    changed = ['src/experimental/mod.rs', 'src/experimental/execution/mod.rs',
        'src/experimental/execution/borrowed.rs', 'src/experimental/execution/tests.rs',
        'src/experimental_swift_reactor/mod.rs', 'src/experimental_swift_reactor/control.rs',
        'src/experimental_swift_reactor/control_tests.rs', 'src/experimental_swift_reactor/execution.rs',
        'src/experimental_swift_reactor/execution_tests.rs']
    run('format', ['rustfmt', '--check', '--edition', '2021', '--config', 'skip_children=true'] + changed)
    # Independent reviewer already measured field roles. Use actual production
    # types here, without inserting replacement inventory definitions.
    metadata = BUILD / 'metadata-vm'
    shutil.copytree(TREE / 'vm', metadata)
    decision = json.loads((ROOT / 'verification/swift-executor-final-accounting-review/decision.json').read_text())
    names = {'FinalOutputBorrows': 'FinalOutputBorrows', 'ClockLeaf': 'FinalClockInventory',
        'FaultLeaf': 'FinalFaultInventory', 'CategoryLeaves': 'FinalCategoryInventory',
        'RefundParent': 'FinalRefundInventory', 'RecordParent': 'FinalRecordInventory',
        'FinishConstFormulaParent': 'FinalFinishInventory'}
    probe = '\npub(super) fn root_final_metadata_probe() {\n'
    probe += 'println!("foundation {} additional {} control {}", FOUNDATION_CONSTRUCTION_BYTES.unwrap(), FOUNDATION_FINAL_BOUNDARY_BYTES, size_of::<RuntimeControl>());\n'
    for old, new in names.items():
        probe += f'println!("layout {old} {{}} {{}}", size_of::<{new}>(), std::mem::align_of::<{new}>());\n'
        for row in decision['source_roles'][old]:
            probe += f'println!("offset {old} {row["field"]} {{}}", std::mem::offset_of!({new}, {row["field"]}));\n'
    probe += '}\n'
    (HERE / 'metadata-probe.rs').write_text(probe)
    control = metadata / 'src/experimental_swift_reactor/control.rs'
    control.write_text(control.read_text() + probe)
    module = metadata / 'src/experimental_swift_reactor/mod.rs'
    hook = '\npub fn root_final_metadata_probe() { control::root_final_metadata_probe(); }\n'
    module.write_text(module.read_text() + hook)
    example = metadata / 'examples/root_final_metadata.rs'
    example.parent.mkdir(exist_ok=True)
    example.write_text('fn main() { mixer_vm::experimental_swift_reactor::root_final_metadata_probe(); }\n')
    receipt['metadata_overlays'] = {str(p.relative_to(metadata)): sha(p.read_bytes()) for p in [control, module, example]}
    layouts = {}
    for mode, opts in [('debug', []), ('release', ['--release'])]:
        output = run('production-metadata-' + mode, ['cargo', 'run', '--locked'] + opts +
            ['--features', 'experimental-swift-reactor', '--example', 'root_final_metadata'], cwd=metadata)
        values = [line for line in output.splitlines() if line.startswith(('foundation ', 'layout ', 'offset '))]
        assert 'foundation 17368 additional 864 control 1720' in values
        for old in names:
            row = decision['layouts'][old]
            assert f'layout {old} {row["size"]} {row["align"]}' in values
            for field in decision['source_roles'][old]:
                assert f'offset {old} {field["field"]} {field["offset"]}' in values
        layouts[mode] = values
    assert layouts['debug'] == layouts['release']
    receipt['production_metadata'] = layouts['debug']
    # Negative public API checks on a derived copy; never add a public owner.
    for name, source in [
        ('private-swift-owner', 'use mixer_vm::experimental_swift_reactor::execution::SwiftReactorInstance; fn main() {}'),
        ('private-legacy-in-swift-only', 'use mixer_vm::experimental::execution::SpanInstance; fn main() {}')]:
        example.write_text(source + '\n')
        for mode, opts in [('debug', []), ('release', ['--release'])]:
            run(name + '-' + mode, ['cargo', 'check', '--locked'] + opts +
                ['--features', 'experimental-swift-reactor', '--example', 'root_final_metadata'], cwd=metadata, rejected='E0603')
    for name, expected in files.items():
        assert sha((ROOT / name).read_bytes()) == sha((TREE / name).read_bytes()) == expected, name
    receipt.update(status='passed', completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        source_checks=len(files) * 2, limitations='Private compiling shapes and corrected named-object accounting. Not physical stack, RSS, interpreter execution, target run, native device, release or GA qualification.')
    save()
    print('PASS', receipt['source_tree_sha256'], flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        receipt.update(status='failed', error=str(error))
        save()
        raise
