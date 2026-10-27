#!/usr/bin/env python3
"""Compiler-free reconciliation of frozen source-object inventory evidence.

Never imports producer utilities, executes product code, or invokes a compiler.
All writes stay in this independent packet. Compiler diagnostics are input data.
"""
import collections
import datetime
import gzip
import hashlib
import json
from pathlib import Path
import platform
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PRODUCER = ROOT / 'verification/swift-guarded-snapshot-host-account-entry'
BOOT = ROOT / 'verification/swift-guarded-snapshot-bootstrap-host-boundary'
BASE = ROOT / 'verification/swift-guarded-snapshot-funding-implementation/source/vm'
RELEASE = ROOT / 'verification/swift-semantic-adapter-root-review/guarded-snapshot-host-account-independent-release.json'
PROFILE = 'src/experimental_swift_reactor/cache/initial_profile_v1.rs'
ACCOUNT = 'src/experimental_swift_reactor/cache/initial_profile_v1/host_account_v1.rs'
EXPECTED_TREE = '5cd522af7e126d88496b5aefee722ff481821f0cf5babdbdbd7fbeba646c380b'
checks = []
inputs = {}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def check(label, predicate):
    if not predicate:
        raise AssertionError(label)
    checks.append(label)


def read(path):
    data = path.read_bytes()
    inputs[str(path.relative_to(ROOT))] = {'bytes': len(data), 'sha256': sha(data)}
    return data


def load(path):
    return json.loads(read(path))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def member(path, data):
    return {'path': path, 'bytes': len(data), 'sha256': sha(data)}


def verify_seal(folder, expected):
    data = read(folder / 'seal.json')
    check(str(folder.relative_to(ROOT)) + ': seal digest', sha(data) == expected)
    seal = json.loads(data)
    check(str(folder.relative_to(ROOT)) + ': member count', len(seal['members']) == seal['member_count'])
    for item in seal['members']:
        data = read(folder / item['path'])
        check(str(folder.relative_to(ROOT)) + ': ' + item['path'],
              len(data) == item['bytes'] and sha(data) == item['sha256'])
    check(str(folder.relative_to(ROOT)) + ': byte sum', sum(i['bytes'] for i in seal['members']) == seal['member_bytes'])
    return seal


def split_functions(raw):
    """Use the compiler's outermost line indentation, not a name filter."""
    current = None
    result = []
    for line in raw.splitlines(keepends=True):
        if line.startswith('fn '):
            check('MIR function starts outside previous function', current is None)
            current = [line]
        elif current is not None:
            current.append(line)
        elif line.strip():
            raise AssertionError('unparsed MIR outside a function')
        if current is not None and line.rstrip('\n') == '}':
            result.append(''.join(current))
            current = None
    check('MIR no unfinished function', current is None)
    return result


def roles_from_mir(body):
    header = body.splitlines()[0]
    start = header.index('(')
    depth = 0
    end = None
    for pos in range(start, len(header)):
        if header[pos] == '(':
            depth += 1
        elif header[pos] == ')':
            depth -= 1
            if depth == 0:
                end = pos
                break
    check('balanced complete MIR signature ' + header, end is not None and header[end + 1:].startswith(' -> '))
    parameters = header[start + 1:end]
    # Parameter markers are compiler local identities. Commas inside generic
    # types and the nested FnOnce() signature never terminate this scan.
    markers = list(re.finditer(r'(?:^|, )(_\d+): ', parameters))
    result = {}
    for i, match in enumerate(markers):
        stop = markers[i + 1].start() if i + 1 < len(markers) else len(parameters)
        result[match[1]] = {'kind': 'parameter', 'compiler_type': parameters[match.end():stop]}
    check('all MIR parameter text consumed ' + header, bool(markers) or not parameters)
    for line in body.splitlines()[1:]:
        code = line.split('//', 1)[0].strip()
        if not code.startswith('let '):
            continue
        declaration = code.removeprefix('let ').removeprefix('mut ')
        local, ty = declaration.split(': ', 1)
        check('MIR whole declaration ends in semicolon ' + local, ty.endswith(';'))
        check('MIR unique declared place ' + header + local, local not in result)
        result[local] = {'kind': 'return-place' if local == '_0' else 'local-or-temporary', 'compiler_type': ty[:-1]}
    code = '\n'.join(line.split('//', 1)[0] for line in body.splitlines())
    references = set(re.findall(r'\b_\d+\b', code))
    check('all referenced MIR locals covered ' + header, references == set(result))
    check('one MIR return place ' + header, result.get('_0', {}).get('kind') == 'return-place')
    return result


def block_graph(body):
    blocks = {}
    active = None
    for line in body.splitlines()[1:]:
        code = line.split('//', 1)[0].rstrip()
        match = re.fullmatch(r'    (bb\d+)( \(cleanup\))?: \{', code)
        if match:
            active = match[1]
            blocks[active] = {'cleanup': bool(match[2]), 'lines': []}
        elif active is not None and code == '    }':
            active = None
        elif active is not None and code.strip():
            blocks[active]['lines'].append(code.strip())
    for block in blocks.values():
        block['successors'] = sorted(set(re.findall(r'\bbb\d+\b', '\n'.join(block['lines']))))
    return blocks


def reachable(graph, start, excluded=()):
    seen = set()
    todo = [start]
    while todo:
        item = todo.pop()
        if item in seen or item in excluded:
            continue
        seen.add(item)
        todo.extend(graph[item]['successors'])
    return seen


def main():
    check('root release digest', sha(read(RELEASE)) == '0ff404a5075827db7e055f16c75a5ec48da09902caa85b594a0cd171d370588f')
    producer_seal = verify_seal(PRODUCER, '6e8c8e2d8dde62e2e35fe2e8fb1a851a342d8d95f8c71facd938416ac3e153e3')
    check('released producer totals', (producer_seal['member_count'], producer_seal['member_bytes']) == (136, 3432402))
    boot_seal = verify_seal(BOOT, '00f5bf754a13317ac18dd9959a1db4a9b025b16c72fc99a9d4cfddfcc7cb4dba')
    check('bootstrap frozen separately', (boot_seal['member_count'], boot_seal['member_bytes']) == (62, 344883))
    bindings = load(PRODUCER / 'input-bindings.json')
    for item in bindings['inputs']:
        data = read(ROOT / item['path'])
        check('frozen input binding ' + item['path'], member(item['path'], data) == item)

    source = load(PRODUCER / 'source-manifest.json')
    original = {}
    for path in sorted(BASE.rglob('*')):
        if path.is_file():
            original[path.relative_to(BASE).as_posix()] = read(path)
    original_members = [member(name, data) for name, data in sorted(original.items(), key=lambda item: Path(item[0]))]
    check('exact funding144 source tree', len(original_members) == 144 and sha(canonical(original_members)) == source['base_tree_sha256'] == bindings['base_tree_sha256'])
    composed = dict(original)
    composed[PROFILE] += b'\n\n' + read(BOOT / 'driver.inc.rs') + b'\n\n' + read(PRODUCER / 'entry.inc.rs')
    composed[ACCOUNT] = read(PRODUCER / 'host_account.rs')
    reconstructed = [member(name, data) for name, data in sorted(composed.items(), key=lambda item: Path(item[0]))]
    check('all exact source145 members derive from funding plus leaf plus account/caller', reconstructed == source['members'])
    check('source145 tree digest', sha(canonical(reconstructed)) == source['source_tree_sha256'] == EXPECTED_TREE)
    check('source145 changes exactly one existing and one new member', source['added_distribution_members'] == [ACCOUNT] and source['altered_existing_members'] == [PROFILE] and len(reconstructed) == 145)
    check('not final composed145 authority', source['composed_source145_or_selected_real_fixture_qualified'] is False)

    receipts = {}
    for name in ['production-metadata-mir', 'actual-type-layout-queries']:
        folder = PRODUCER / 'compiler-commands' / name
        receipt = load(folder / 'receipt.json')
        outputs = {}
        for stream, spec in receipt['output'].items():
            stored = read(folder / spec.get('stored_path', stream))
            if spec.get('storage_encoding') == 'gzip':
                check(name + ': gzip custody', len(stored) == spec['stored_bytes'] and sha(stored) == spec['stored_sha256'])
                data = gzip.decompress(stored)
            else:
                data = stored
            check(name + ': original ' + stream + ' custody', len(data) == spec['bytes'] and sha(data) == spec['sha256'])
            outputs[stream] = data.decode()
        check(name + ': production base binding', receipt['source_tree_sha256'] == EXPECTED_TREE and receipt['source_manifest_sha256'] == sha(read(PRODUCER / 'source-manifest.json')))
        check(name + ': library custom cfg without test mode', '--test' not in receipt['argv'] and 'test' not in receipt['argv'] and '--crate-type' in receipt['argv'] and 'lib' in receipt['argv'] and 'mixer_bootstrap_one_fixture_v1' in receipt['argv'])
        receipts[name] = {'receipt': receipt, 'outputs': outputs}

    raw = read(PRODUCER / 'entry-and-account.mir').decode()
    functions = split_functions(raw)
    claimed_mir = load(PRODUCER / 'mir-roles.json')
    inventory = load(PRODUCER / 'caller-inventory.json')
    phase = load(PRODUCER / 'phase-inventory.json')
    check('19 selected MIR functions in both inventories', len(functions) == len(claimed_mir['functions']) == len(inventory['functions']) == 19)
    check('all inventory source bindings', all(obj['source_tree_sha256'] == EXPECTED_TREE for obj in [claimed_mir, inventory, phase]))
    expected_names = ['checked_components_v1', 'selected_whole_quote_v1', 'selected_parent_account_v1', 'from_preexisting_root_v1', 'usage_v1', 'reserve_whole_v1', 'dispatch_v1', 'inspect_v1', 'destroy_owned_v1', 'drop', 'release_destroyed_v1', 'run_one_fixture_v1', '{closure#0}', 'destroy_returned_fixture_v1', 'release_after_retirement_v1', 'setup_files_once_v1', 'copy_claims_v1', 'run_prepaid_fixture_v1', 'invoke_loaded_leaf_once_v1']
    observed_names = [body.splitlines()[0].split('(', 1)[0].rsplit('::', 1)[-1].removeprefix('fn ') for body in functions]
    check('all18 authored production functions plus actual dispatch closure selected', observed_names == expected_names)
    production_account = composed[ACCOUNT].decode().split('#[cfg(test)]', 1)[0]
    source_names = re.findall(r'\bfn ([a-z_0-9]+)', production_account + read(PRODUCER / 'entry.inc.rs').decode())
    check('production source function definitions exactly match selected MIR excluding closure', collections.Counter(source_names) == collections.Counter(n for n in expected_names if n != '{closure#0}'))
    observed = []
    bodies = {}
    for body, first, second, ph in zip(functions, claimed_mir['functions'], inventory['functions'], phase['functions'], strict=True):
        header = body.splitlines()[0]
        roles = roles_from_mir(body)
        check('exact function header agreement ' + header, header == first['header'] == second['header'] == ph['header'])
        check('exact complete selected MIR hash ' + header, sha(body.encode()) == first['sha256'] == second['sha256'])
        check('both inventories agree on complete role measurements ' + header, first['roles'] == second['roles'])
        for record in [first, second]:
            actual = {r['local']: {'kind': r['kind'], 'compiler_type': r['compiler_type']} for r in record['roles']}
            check('complete declared role identities/types ' + header, len(record['roles']) == len(actual) and actual == roles)
        blocks = block_graph(body)
        calls = [line.strip() for line in body.splitlines() if ' -> [' in line and ' = ' in line and 'assert(' not in line]
        check('finite MIR block/call/assert counts ' + header, len(blocks) == ph['MIR_basic_blocks'] and calls == ph['calls'] and len(calls) == ph['MIR_call_terminators'] and sum('assert(' in line for line in body.splitlines()) == ph['MIR_assert_terminators'])
        check('no missing MIR successor blocks ' + header, all(n in blocks for b in blocks.values() for n in b['successors']))
        check('per-function measured counts ' + header, len(roles) == second['role_count'] and sum(r['bytes'] for r in second['roles']) == second['measured_logical_bytes'] and second['unmeasured_roles'] == 0)
        observed.append({'header': header, 'phase': second['phase'], 'roles': len(roles), 'parameters': sum(r['kind'] == 'parameter' for r in roles.values()), 'return_places': 1, 'logical_bytes': second['measured_logical_bytes'], 'MIR_blocks': len(blocks), 'cleanup_blocks': sum(b['cleanup'] for b in blocks.values()), 'drop_terminators': sum(line.startswith('drop(') for b in blocks.values() for line in b['lines'])})
        bodies[header] = body

    diagnostic = receipts['actual-type-layout-queries']['outputs']['stderr']
    query_data = {}
    query_declarations = []
    for block in diagnostic.split('error[E0308]:')[1:]:
        originals = re.findall(r'^\d+ - (const ENTRY_LAYOUT_(\d+): \[\(\); usize::MAX\] = \[\(\); std::mem::size_of::<(.+)>\(\)\];)$', block, re.M)
        found = set(re.findall(r'found one with a size of (\d+)', block))
        check('diagnostic has one complete original type and one measured size', len(originals) == 1 and len(found) == 1)
        declaration, index, ty = originals[0]
        check('distinct query ordinal ' + index, int(index) not in query_data)
        query_data[int(index)] = {'type': ty, 'bytes': int(next(iter(found)))}
        query_declarations.append((int(index), declaration))
    check('90 intentional layout errors only', len(query_data) == 90 and re.findall(r'error\[(E\d+)\]', diagnostic) == ['E0308'] * 90 and receipts['actual-type-layout-queries']['receipt']['exit_code'] == 1)
    measured_types = {}
    for row in query_data.values():
        check('duplicate concrete query agrees ' + row['type'], row['type'] not in measured_types or measured_types[row['type']] == row['bytes'])
        measured_types[row['type']] = row['bytes']
    check('89 distinct nonunit types', len(measured_types) == 89 and '()' not in measured_types)
    check('diagnostics equal actual type size table plus zero-sized unit', {**measured_types, '()': 0} == inventory['actual_type_sizes'])
    printed = receipts['production-metadata-mir']['outputs']['stdout']
    anonymous = [(name, int(size), int(align)) for name, size, align in re.findall(r'print-type-size type: `([^`]+)`: (\d+) bytes, alignment: (\d+) bytes', printed) if '/swift-guarded-snapshot-host-account-entry/' in name and '{closure@' in name]
    actual_closures = {r['compiler_type'] for f in inventory['functions'] for r in f['roles'] if r['compiler_type'].startswith('{closure@')}
    closure_rows = [r for r in anonymous if r[0] in actual_closures]
    check('actual selected closure measured once as 8 bytes alignment 8', len(actual_closures) == len(closure_rows) == 1 and closure_rows[0][1:] == (8, 8))
    closure_name = closure_rows[0][0]
    generic_count = 0
    size_rows = 0
    for fn in inventory['functions']:
        for role in fn['roles']:
            ty = role['compiler_type']
            if ty in ['impl FnOnce() -> T', closure_name]:
                check('actual closure role uses measured closure', role['concrete_production_type'] == closure_name and role['bytes'] == 8)
            else:
                concrete = re.sub(r'\bT\b', 'OwnedFixtureOutcomeV1', ty)
                if concrete not in measured_types and concrete != '()':
                    alternatives = [n for n in measured_types if n.endswith('::' + concrete)]
                    check('unique compiler-qualified alias ' + concrete, len(alternatives) == 1)
                    concrete = alternatives[0]
                check('every role size from exact concrete compiler diagnostic ' + fn['header'] + role['local'], concrete == role['concrete_production_type'] and role['bytes'] == ({**measured_types, '()': 0})[concrete])
                size_rows += 1
            generic_count += bool(re.search(r'\bT\b', ty))
    check('all 396 places retained without alias or move discount', sum(f['roles'] for f in observed) == inventory['role_count'] == 396 and sum(f['logical_bytes'] for f in observed) == inventory['measured_logical_bytes'] == 311071 and inventory['unmeasured_roles'] == 0)
    check('generic binding uses real retained outcome', measured_types['OwnedFixtureOutcomeV1'] == 13608 and generic_count > 0 and inventory['generic_T_bound_only_to_actual_production_owned_outcome'] is True)

    # Reconstruct the exact query-only source delta from compiler-rendered
    # original declarations and the explicit include prelude; no tool import.
    prefix = '\n#[cfg(mixer_bootstrap_one_fixture_v1)]\nmod host_entry_layout_queries_v1 {\nuse super::*;\nuse super::super::*;\nuse crate::experimental_swift_reactor::{control,retained_profile_loader_v1};\nuse crate::experimental_swift_reactor::cache::initial_profile_v1;\nuse crate::experimental_swift_reactor;\nuse crate::{experimental,experimental_wasi};\nuse crate::execute;\nuse crate::Cancellation;\n'
    layout_tree = dict(composed)
    layout_tree[ACCOUNT] += (prefix + ''.join(line + '\n' for _, line in sorted(query_declarations)) + '}\n').encode()
    layout_tree['src/lib.rs'] = b'#![feature(never_type)]\n' + layout_tree['src/lib.rs']
    layout_members = [member(name, data) for name, data in sorted(layout_tree.items(), key=lambda item: Path(item[0]))]
    layout_manifest = load(PRODUCER / 'layout-source-manifest.json')
    check('exact145 layout source derives only from compiler-rendered type queries and never_type', layout_members == layout_manifest['members'])
    check('layout query tree digest separate from production tree', sha(canonical(layout_members)) == layout_manifest['source_tree_sha256'] == '98f82db0d7277d0f0e9ded5fd563fd26b2ebb1fbedceac826bc4207562acb21b')
    amendment = load(PRODUCER / 'compiler-receipt-amendments.json')
    check('layout receipt base-tree field is explicitly amended to actual query tree', amendment['actual_layout_query_source_tree_sha256'] == layout_manifest['source_tree_sha256'] and amendment['actual_layout_query_manifest_sha256'] == sha(read(PRODUCER / 'layout-source-manifest.json')) and amendment['command_receipt_source_tree_field_is_production_base_for_layout_query'] is True)

    phase_totals = {}
    for row in observed:
        total = phase_totals.setdefault(row['phase'], dict(functions=0, logical_bytes=0, parameters=0, return_places=0, roles=0))
        total['functions'] += 1
        for key in ['logical_bytes', 'parameters', 'return_places', 'roles']:
            total[key] += row[key]
    check('all phase totals reconstructed', phase_totals == phase['by_phase'])
    p0 = 'P0-pre-existing-parent-account-bookkeeping'
    p0_names = ['checked_components_v1', 'selected_whole_quote_v1', 'selected_parent_account_v1', 'from_preexisting_root_v1', 'usage_v1', 'reserve_whole_v1', 'dispatch_v1', 'inspect_v1', 'destroy_owned_v1', 'drop', 'release_destroyed_v1', 'run_one_fixture_v1', 'destroy_returned_fixture_v1', 'release_after_retirement_v1']
    p0_rows = [r for r in observed if r['phase'] == p0]
    check('all account policy quote closure destroy token release places assigned preexisting P0', len(p0_rows) == 15 and all(any(('::' + name + '(') in r['header'] or r['header'].startswith('fn ' + name + '(') for name in p0_names) or 'run_one_fixture_v1::{closure#0}' in r['header'] for r in p0_rows))
    check('P0 remains unpriced and preexisting', phase['P0_call_return_token_release_places_preexisting_and_not_child_funded'] is True and phase['P0_exact_logical_work_price'] is None and phase['whole_quote_complete'] is False and phase['MIR_counts_are_work_price_or_OTA_authorization'] is False)
    for name, wanted in [('TrustedRootPolicyV1', 64), ('experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1::host_account_v1::TrustedHostAccountV1', 104), ("DestroyedStorageV1<'_>", 16)]:
        check('P0 concrete header diagnostic ' + name, measured_types[name] == wanted)
    def body_named(fragment):
        matches = [body for header, body in bodies.items() if fragment in header]
        check('unique MIR function ' + fragment, len(matches) == 1)
        return matches[0]
    destruction = body_named('::destroy_owned_v1(')
    graph = block_graph(destruction)
    token_blocks = [n for n, b in graph.items() if any('DestroyedStorageV1::' in l and '{ reservation:' in l for l in b['lines'])]
    wrapper_drop = [n for n, b in graph.items() if any('std::mem::drop::<PrepaidOwnedV1' in l for l in b['lines'])]
    payload_drop = [n for n, b in graph.items() if any('std::mem::drop::<T>' in l for l in b['lines'])]
    check('one explicit token construction and payload/wrapper destruction site', len(token_blocks) == len(wrapper_drop) == len(payload_drop) == 1)
    check('token cannot be built before wrapper drop call', token_blocks[0] not in reachable(graph, 'bb0', wrapper_drop))
    cleanup = [n for n, b in graph.items() if b['cleanup']]
    check('destructor unwind cleanup cannot produce completion token', all(token_blocks[0] not in reachable(graph, n) for n in cleanup))
    check('destruction has no account commit or release call', 'Cell::<UsageV1>::set' not in destruction and 'release_destroyed_v1' not in destruction)
    ordinary_drop = body_named('::drop(')
    check('ordinary Drop retains all inventory places and has no release', 'std::mem::drop::<T>' in ordinary_drop and 'release_destroyed_v1' not in ordinary_drop and 'Cell::<UsageV1>::set' not in ordinary_drop)
    release = body_named('::release_destroyed_v1(')
    release_roles = roles_from_mir(release)
    check('release has only consuming original token parameter', [(n, r['compiler_type']) for n, r in release_roles.items() if r['kind'] == 'parameter'] == [('_1', "DestroyedStorageV1<'_>")])
    check('release commits storage only and preserves work/peak', 'checked_sub' in release and 'UsageV1 { work: copy (_2.0: u64), storage: move _12, peak_storage: copy (_2.2: u64) }' in release)
    caller = body_named('fn run_prepaid_fixture_v1(')
    check('failure and loaded outcome alternatives appear in measured MIR', all(s in caller for s in ['OwnedFixtureOutcomeV1::SetupRefused', 'PrimaryOutcomeV1::LoaderRefused', 'OwnedFixtureOutcomeV1::Loaded', 'LoaderFailureV1', 'ReturnedLoaderFilesV1', 'SnapshotPreScopeFailureV1']))
    check('setup failure original error and prior File owners are measured', all(s in body_named('fn setup_files_once_v1(') for s in ['SetupOutcomeV1::Refused', 'SetupOutcomeV1::InvariantRefused', '[std::option::Option<std::fs::File>; 5]', 'std::io::Error']))

    boot_inventory = load(BOOT / 'driver-inventory.json')
    boot_roles = roles_from_mir(read(BOOT / 'driver.mir').decode())
    check('bootstrap leaf30 roles retained separately', len(boot_roles) == boot_inventory['role_count'] == 30 and {r['local']: {'kind': r['kind'], 'compiler_type': r['compiler_type']} for r in boot_inventory['roles']} == boot_roles)
    check('bootstrap leaf95850 bytes and7 parameters1344 bytes separately', sum(r['bytes'] for r in boot_inventory['roles']) == boot_inventory['logical_source_object_union_bytes'] == 95850 and len([r for r in boot_inventory['roles'] if r['kind'] == 'parameter']) == 7 and sum(r['bytes'] for r in boot_inventory['roles'] if r['kind'] == 'parameter') == boot_inventory['parameter_source_object_bytes'] == 1344)
    check('bootstrap leaf requires final composed source rebinding', boot_inventory['final_composed_source_layout_rebinding_pending'] is True and boot_inventory['whole_launcher_inventory_or_authority_qualified'] is False)

    old = load(PRODUCER / 'attempts/02-parameter-parser-repair/caller-inventory.json')
    previous = {f['header']: {r['local']: r for r in f['roles']} for f in old['functions']}
    recovered = []
    for fn in inventory['functions']:
        for r in fn['roles']:
            if r['local'] not in previous[fn['header']]:
                recovered.append({'header': fn['header'], **r})
    check('prior394/311047 failed assumption preserved', old['role_count'] == 394 and old['measured_logical_bytes'] == 311047)
    check('only two missing dispatch parameters explain24-byte repair', [(r['local'], r['kind'], r['bytes']) for r in recovered] == [('_1', 'parameter', 16), ('_2', 'parameter', 8)] and all('::dispatch_v1(' in r['header'] for r in recovered))
    attempt = load(PRODUCER / 'attempts/tool-failure.json')
    check('other producer parser/filter failures preserved', 'array types' in attempt['first_layout_attempt'] and attempt['closure_filter_compiler_invocations'] == 0)

    result = {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'status': 'accepted-bounded-frozen-source-object-inventory-only', 'source_tree_sha256': EXPECTED_TREE, 'layout_query_source_tree_sha256': layout_manifest['source_tree_sha256'], 'checks_passed': len(checks), 'producer_members_verified': producer_seal['member_count'], 'producer_bytes_verified': producer_seal['member_bytes'], 'source_members_verified': len(reconstructed), 'functions': observed, 'new_function_count': 19, 'new_role_count': 396, 'logical_source_object_bytes': 311071, 'diagnostic_queries': 90, 'distinct_nonunit_types': 89, 'compiler_diagnostic_sized_role_instances': size_rows, 'actual_compiler_closure_role_instances': 396-size_rows, 'generic_role_instances_bound_to_actual_outcome': generic_count, 'actual_closure_bytes': 8, 'phase_totals': phase_totals, 'bootstrap_leaf_separate': {'roles': 30, 'logical_source_object_bytes': 95850, 'parameters': 7, 'parameter_bytes': 1344, 'composed_with_newer_combined145': False}, 'historical_counterexample': {'superseded_roles': 394, 'superseded_bytes': 311047, 'omitted_parameters': recovered, 'source_changed_for_parameter_repair': False}, 'aliases_overlaps_moves_failure_places_discounted': False, 'whole_quote_P0_policy_fixture_complete': False, 'stack_RSS_allocator_CPU_full_work_operational_native_OTA_FieldLog_GA_authority': False, 'compiler_runtime_native_UI_capture_process_inventory_invocations': 0, 'git_state_read_or_changed': False, 'writes_owned_packet_only': True, 'checks': checks}
    # The assertions remain executable above; retain their count and digest
    # instead of repeating long compiler paths in thousands of labels.
    result.pop('checks')
    result['passed_assertion_labels_sha256'] = sha(canonical(checks))
    result['host_check_tool'] = {'python': sys.version, 'executable': sys.executable, 'platform': platform.platform(), 'checker_sha256': sha(Path(__file__).read_bytes())}
    if '--check-only' not in sys.argv:
        (HERE / 'results.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
        (HERE / 'input-custody.json').write_text(json.dumps({'schema': 1, 'source_tree_sha256': EXPECTED_TREE, 'inputs': inputs}, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: result[k] for k in ['status', 'checks_passed', 'new_function_count', 'new_role_count', 'logical_source_object_bytes', 'diagnostic_queries', 'distinct_nonunit_types', 'actual_closure_bytes']}, sort_keys=True))


if __name__ == '__main__':
    if (HERE / 'seal.json').exists() and '--check-only' not in sys.argv:
        raise SystemExit('Packet is frozen; use --check-only for read-only reconciliation.')
    main()
