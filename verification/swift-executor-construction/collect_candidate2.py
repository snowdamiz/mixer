#!/usr/bin/env python3
"""A fresh candidate using the preserved candidate1 collector and new freeze."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import tarfile

import collect

BASE = Path(__file__).resolve().parent
collect.OUT = BASE / 'candidate-2'
collect.OUT.mkdir(exist_ok=True)
collect.TREE = collect.OUT / 'build/source/vm'
collect.META = collect.OUT / 'build/metadata/vm'
collect.ENV['CARGO_TARGET_DIR'] = str(collect.OUT / 'build/target')
collect.receipt['schema'] = 'mixer.swift-executor-construction-producer.candidate2'
collect.receipt['prior_candidate'] = {
    'receipt': '../receipt.json',
    'sha256': hashlib.sha256((BASE / 'receipt.json').read_bytes()).hexdigest(),
    'preserved': True,
}


def candidate2_metadata_overlay():
    shutil.copytree(collect.TREE, collect.META)
    execution = collect.META / 'src/experimental_swift_reactor/execution.rs'
    source = execution.read_text()
    originals = ['SwiftExecutionState', 'SwiftReactorInstance', 'SwiftFrame',
                 'ExecutionConstructionPhase', 'ExecutionOperationPhase', 'PartialState',
                 'PartialInstance', 'ExecutionCleanupTail', 'HeaderCompletionParts',
                 'ConstructionCleanupTail', 'ScalarReader', 'ConstructionDescriptors',
                 'ConstructionTransfers', 'ConstructionBorrowChain', 'ConstructionIterationInventory',
                 'ConstructionBootstrapInventory', 'CleanupPreflightInventory']
    supplements = [name for name in re.findall(r'\bstruct (\w+)', source)
                   if 'Supplement' in name or name.startswith(('ConstructorApi', 'ConstructionPositive'))]
    names = list(dict.fromkeys(originals + supplements))
    generic = {'ExecutionConstructionPhase', 'ExecutionOperationPhase', 'ScalarReader'}
    probe = '\npub(super) fn construction_metadata_probe() {\n'
    probe += 'println!("bounds foundation {} bootstrap {} construction {} header {} cleanup_original {}", foundation_construction_bytes().unwrap(), CONSTRUCTION_BOOTSTRAP_BYTES, construction_bytes().unwrap(), execution_header_bytes().unwrap(), phase_bytes("cleanup").unwrap());\n'
    roles = {}
    for name in names:
        ty = name + ("<'static>" if name in generic else '')
        if name == 'ConstructionPositiveTestHookArguments':
            probe += '#[cfg(test)] {\n'
        probe += f'println!("layout {name} {{}} {{}}", size_of::<{ty}>(), std::mem::align_of::<{ty}>());\n'
        roles[name] = []
        for field, field_type in collect.fields(source, name):
            field_type = field_type.replace("'a", "'static")
            roles[name].append({'field': field, 'type': field_type})
            probe += f'println!("role {name} {field} {{}} {{}} {{}}", std::mem::offset_of!({ty}, {field}), size_of::<{field_type}>(), std::mem::align_of::<{field_type}>());\n'
        if name == 'ConstructionPositiveTestHookArguments':
            probe += '}\n'
    for ty in ['ConstructionFailure', 'Option<ConstructionFailure>',
               'Result<SwiftReactorInstance,ConstructionFailure>',
               'Option<Result<SwiftReactorInstance,ConstructionFailure>>',
               'Option<ConstructionCleanupTail>',
               'Result<ConstructionCleanupTail,SwiftRunFailure>',
               '(HeaderCompletionParts,usize)']:
        roles[ty] = []
        probe += f'println!("layout {ty} {{}} {{}}", size_of::<{ty}>(), std::mem::align_of::<{ty}>());\n'
    descriptor = collect.META / 'src/experimental/swift.rs'
    descriptor_source = descriptor.read_text()
    descriptor_name = 'ConstructionPositiveDescriptor'
    descriptor_probe = '\npub(crate) fn construction_descriptor_metadata_probe() {\n'
    descriptor_probe += f'println!("layout {descriptor_name} {{}} {{}}", std::mem::size_of::<{descriptor_name}>(), std::mem::align_of::<{descriptor_name}>());\n'
    roles[descriptor_name] = []
    for field, field_type in collect.fields(descriptor_source, descriptor_name):
        roles[descriptor_name].append({'field': field, 'type': field_type})
        descriptor_probe += f'println!("role {descriptor_name} {field} {{}} {{}} {{}}", std::mem::offset_of!({descriptor_name}, {field}), std::mem::size_of::<{field_type}>(), std::mem::align_of::<{field_type}>());\n'
    descriptor_probe += '}\n'
    descriptor.write_text(descriptor_source + descriptor_probe)
    probe += 'crate::experimental::swift::construction_descriptor_metadata_probe();\n}\n#[cfg(test)]\n#[test]\nfn frozen_construction_metadata() { construction_metadata_probe(); }\n'
    execution.write_text(source + probe)
    module = collect.META / 'src/experimental_swift_reactor/mod.rs'
    module.write_text(module.read_text() + '\npub fn construction_metadata_probe_only() { execution::construction_metadata_probe(); }\n')
    example = collect.META / 'examples/construction_metadata.rs'
    example.parent.mkdir(exist_ok=True)
    example.write_text('fn main() { mixer_vm::experimental_swift_reactor::construction_metadata_probe_only(); }\n')
    (collect.OUT / 'metadata-probe.rs').write_text(probe)
    collect.save('metadata-overlay.json', {str(p.relative_to(collect.META)): collect.sha(p)
                                         for p in [execution, descriptor, module, example]})
    return roles


collect.metadata_overlay = candidate2_metadata_overlay
original_parse_metadata = collect.parse_metadata


def candidate2_parse_metadata(output, roles):
    excluded = []
    expected = dict(roles)
    name = 'ConstructionPositiveTestHookArguments'
    if f'layout {name} ' not in output:
        expected.pop(name, None)
        excluded.append({'type': name, 'reason': 'cfg(test) instrumentation only; production constant is zero'})
    result = original_parse_metadata(output, expected)
    result['cfg_excluded'] = excluded
    return result


collect.parse_metadata = candidate2_parse_metadata
collect.main()
archive = collect.OUT / 'frozen-source.tar.gz'
with tarfile.open(archive, 'w:gz') as packed:
    packed.add(collect.TREE, arcname='vm')
receipt_path = collect.OUT / 'receipt.json'
receipt = json.loads(receipt_path.read_text())
receipt['archive'] = {'path': archive.name, 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}
receipt['collector_hashes'] = {
    path.name: hashlib.sha256(path.read_bytes()).hexdigest()
    for path in [BASE / 'collect.py', Path(__file__).resolve()]
}
receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
