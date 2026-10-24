#!/usr/bin/env python3
"""Freeze and qualify the private uninitialized constructor; never a target runner."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
TREE = OUT / 'build' / 'source' / 'vm'
META = OUT / 'build' / 'metadata' / 'vm'
ENV = dict(os.environ, PATH='/opt/homebrew/opt/rustup/bin:' + os.environ['PATH'],
           CARGO_TARGET_DIR=str(OUT / 'build' / 'target'))
receipt = {'schema': 'mixer.swift-executor-construction-producer.v1', 'commands': [],
           'scope': 'Private uninitialized same-ABI synthetic construction and zero-frame cleanup only.',
           'implementation_acceptance': False, 'accounting_acceptance': False,
           'full_target_instantiated': False, 'initialize_or_invoke': False,
           'physical_device_runs': False, 'ga_acceptance': False}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n')


def run(name, argv, cwd=TREE, expected=0):
    print(name, flush=True)
    started = time.time()
    result = subprocess.run(argv, cwd=cwd, env=ENV, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log = OUT / 'logs' / (name + '.log')
    log.parent.mkdir(exist_ok=True)
    log.write_text(result.stdout)
    row = {'name': name, 'argv': argv, 'cwd': str(cwd), 'exit_code': result.returncode,
           'expected': expected, 'seconds': round(time.time() - started, 3),
           'log': str(log.relative_to(ROOT)), 'sha256': sha(log)}
    receipt['commands'].append(row)
    save('receipt.partial.json', receipt)
    if (result.returncode == 0) != (expected == 0):
        raise RuntimeError(f'{name}: exit {result.returncode}; see {log}')
    return result.stdout


def fields(source, name):
    match = re.search(r'\bstruct ' + name + r'(?:<[^\n]*>)?\s*\{', source)
    assert match, name
    body = source[match.end():source.index('\n}', match.end())]
    declarations = []
    pending = ''
    depth = 0
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('//'):
            continue
        pending += ' ' + stripped
        depth += sum(stripped.count(c) for c in '<[(') - sum(stripped.count(c) for c in '>])')
        if depth == 0 and stripped.endswith(','):
            field, field_type = pending.strip().rstrip(',').split(':', 1)
            field = re.sub(r'^pub(?:\([^)]*\))?\s+', '', field)
            declarations.append((field, field_type.strip()))
            pending = ''
    assert not pending.strip(), (name, pending)
    return declarations


def metadata_overlay():
    shutil.copytree(TREE, META)
    execution = META / 'src/experimental_swift_reactor/execution.rs'
    source = execution.read_text()
    names = ['SwiftExecutionState', 'SwiftReactorInstance', 'SwiftFrame',
             'ExecutionConstructionPhase', 'ExecutionOperationPhase', 'PartialState',
             'PartialInstance', 'ExecutionCleanupTail', 'HeaderCompletionParts',
             'ScalarReader', 'ConstructionDescriptors', 'ConstructionTransfers',
             'ConstructionBorrowChain', 'ConstructionIterationInventory',
             'ConstructionBootstrapInventory', 'CleanupPreflightInventory']
    generic = {'ExecutionConstructionPhase', 'ExecutionOperationPhase', 'ScalarReader'}
    probe = '\npub(super) fn construction_metadata_probe() {\n'
    probe += 'println!("bounds foundation {} bootstrap {} construction {} header {} cleanup_original {}", foundation_construction_bytes().unwrap(), CONSTRUCTION_BOOTSTRAP_BYTES, construction_bytes().unwrap(), execution_header_bytes().unwrap(), phase_bytes("cleanup").unwrap());\n'
    roles = {}
    for name in names:
        ty = name + ("<'static>" if name in generic else '')
        probe += f'println!("layout {name} {{}} {{}}", size_of::<{ty}>(), std::mem::align_of::<{ty}>());\n'
        roles[name] = []
        for field, field_type in fields(source, name):
            field_type = field_type.replace("'a", "'static")
            roles[name].append({'field': field, 'type': field_type})
            probe += f'println!("role {name} {field} {{}} {{}} {{}}", std::mem::offset_of!({ty}, {field}), size_of::<{field_type}>(), std::mem::align_of::<{field_type}>());\n'
    probe += '}\n#[cfg(test)]\n#[test]\nfn frozen_construction_metadata() { construction_metadata_probe(); }\n'
    execution.write_text(source + probe)
    module = META / 'src/experimental_swift_reactor/mod.rs'
    module.write_text(module.read_text() + '\npub fn construction_metadata_probe_only() { execution::construction_metadata_probe(); }\n')
    example = META / 'examples/construction_metadata.rs'
    example.parent.mkdir(exist_ok=True)
    example.write_text('fn main() { mixer_vm::experimental_swift_reactor::construction_metadata_probe_only(); }\n')
    (OUT / 'metadata-probe.rs').write_text(probe)
    save('metadata-overlay.json', {str(p.relative_to(META)): sha(p) for p in [execution, module, example]})
    return roles


def parse_metadata(output, roles):
    result = {'types': {}, 'bounds': {}}
    for line in output.splitlines():
        if line.startswith('bounds '):
            parts = line.split()[1:]
            result['bounds'] = dict(zip(parts[::2], map(int, parts[1::2])))
        elif line.startswith('layout '):
            _, name, size, align = line.split()
            result['types'][name] = {'size': int(size), 'align': int(align), 'fields': {}}
        elif line.startswith('role '):
            _, name, field, offset, size, align = line.split()
            declared = next(row['type'] for row in roles[name] if row['field'] == field)
            result['types'][name]['fields'][field] = {'type': declared, 'offset': int(offset), 'size': int(size), 'align': int(align)}
    assert len(result['types']) == len(roles)
    return result


def main():
    if TREE.exists():
        raise RuntimeError('Freeze already exists; preserve it and choose a new candidate directory.')
    TREE.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / 'vm', TREE, ignore=shutil.ignore_patterns('target', '.git'))
    inputs = {str(p.relative_to(TREE)): sha(p) for p in sorted(TREE.rglob('*')) if p.is_file()}
    save('source-manifest.json', inputs)
    receipt['revision'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    receipt['dirty_state'] = subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True)
    receipt['source_tree_digest'] = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
    receipt['source_files'] = len(inputs)
    for name, argv in [('rustc-version', ['rustc', '-Vv']), ('cargo-version', ['cargo', '-V']),
                       ('host', ['uname', '-a']), ('python-version', ['python3', '--version'])]:
        run(name, argv)
    counts = {}
    for profile, opts in [('debug', []), ('release', ['--release'])]:
        output = run('construction-' + profile, ['cargo', 'test', '--locked'] + opts +
                     ['--features', 'experimental-swift-reactor', '--lib', 'swift_construction_', '--', '--nocapture', '--test-threads=1'])
        assert re.search(r'test result: ok\. 14 passed; 0 failed', output)
        counts[profile] = 14
        run('layout-' + profile, ['cargo', 'test', '--locked'] + opts +
            ['--features', 'experimental-swift-reactor', '--lib', 'swift_executor_layout', '--', '--nocapture', '--test-threads=1'])
        for label, flags in [('neither', []), ('span', ['--features', 'experimental-span-execution']),
                             ('swift', ['--features', 'experimental-swift-reactor']),
                             ('swift-cache', ['--features', 'experimental-swift-reactor,experimental-function-cache']),
                             ('swift-span', ['--features', 'experimental-swift-reactor,experimental-span-execution']),
                             ('all', ['--all-features'])]:
            run(label + '-' + profile, ['cargo', 'test', '--locked'] + opts + flags + ['--lib'])
    for label, flags in [('swift', ['--features', 'experimental-swift-reactor']), ('all', ['--all-features'])]:
        run('clippy-' + label, ['cargo', 'clippy', '--locked', '--lib'] + flags + ['--', '-D', 'warnings'])
    run('format', ['rustfmt', '--check', '--edition', '2021', 'src/experimental_swift_reactor/execution.rs', 'src/experimental_swift_reactor/execution_tests.rs'])
    qualify_metadata(inputs)


def qualify_metadata(inputs):
    roles = metadata_overlay()
    layouts = {'schema': 'mixer.swift-construction-layout-map.v1', 'scope': 'Candidate actual chosen object layouts; counts await independent root call-chain review.', 'configurations': {}}
    for profile, opts in [('debug', []), ('release', ['--release'])]:
        for kind, argv in [('production', ['cargo', 'run', '--locked'] + opts + ['--features', 'experimental-swift-reactor', '--example', 'construction_metadata']),
                           ('unit', ['cargo', 'test', '--locked'] + opts + ['--features', 'experimental-swift-reactor', '--lib', 'frozen_construction_metadata', '--', '--nocapture'])]:
            output = run('metadata' + str(receipt.get('metadata_attempt', 1)) + '-' + kind + '-' + profile, argv, META)
            layouts['configurations'][kind + '-' + profile] = parse_metadata(output, roles)
    assert layouts['configurations']['production-debug'] == layouts['configurations']['production-release']
    assert layouts['configurations']['unit-debug'] == layouts['configurations']['unit-release']
    save('layout-map.json', layouts)
    # External callers still cannot name an executable owner or constructor.
    privacy = META / 'examples/construction_privacy.rs'
    privacy.write_text('fn main() { let _ = mixer_vm::experimental_swift_reactor::execution::SwiftReactorInstance::construct; }\n')
    output = run('private-constructor' + str(receipt.get('metadata_attempt', 1)), ['cargo', 'check', '--locked', '--features', 'experimental-swift-reactor', '--example', 'construction_privacy'], META, expected=1)
    assert 'private' in output and 'E0603' in output
    assert all(sha(TREE / path) == digest for path, digest in inputs.items())
    receipt['construction_test_counts'] = {'debug':14, 'release':14}
    receipt['metadata'] = 'layout-map.json'
    receipt['limitations'] = 'No full executor acceptance; no every-work/check/deadline/growth/active-frame unwind qualification; no target initialize/invoke, physical stack/RSS/device, published FieldLog, signing/store/GA evidence.'
    receipt['status'] = 'producer qualification passed; independent review pending'
    save('receipt.json', receipt)


if __name__ == '__main__':
    if '--resume-metadata' in sys.argv:
        receipt = json.loads((OUT / 'receipt.partial.json').read_text())
        receipt['metadata_attempt'] = 2
        historical = OUT / 'historical-metadata-attempt1'
        historical.mkdir()
        for name in ['metadata-overlay.json', 'metadata-probe.rs']:
            shutil.copy2(OUT / name, historical / name)
        META.rename(META.parent / 'vm-attempt1')
        receipt['metadata_correction'] = 'First derived metadata probe used undeclared generic lifetime and omitted multiline tuple fields; no engine source or qualification outcome changed. Attempt1 source/probe/log retained. Attempt2 substitutes static lifetimes and parses full tuple declarations.'
        qualify_metadata(json.loads((OUT / 'source-manifest.json').read_text()))
    else:
        main()
