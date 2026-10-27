#!/usr/bin/env python3
"""Prepare an exact source146 P0 rebind candidate from frozen data only.

No compiler/product execution. This is preparation pending another independent
review, never a root policy, complete P0 quote, or grant.
"""
from __future__ import annotations
import collections
import difflib
import gzip
import hashlib
import json
from pathlib import Path
import platform
import re
import sys
sys.dont_write_bytecode = True
import helpers as H

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
V = ROOT/'verification'
OLD = V/'swift-guarded-snapshot-parent-work'
REVIEW = V/'swift-guarded-snapshot-parent-work-independent'
ACCOUNT = V/'swift-guarded-snapshot-host-account-entry'
BASE = V/'swift-guarded-snapshot-funding-implementation/source/vm'
COMPOSE = V/'swift-guarded-snapshot-host-composition'
FRESH = V/'swift-guarded-snapshot-host-composition-independent'
SOURCE145 = '5cd522af7e126d88496b5aefee722ff481821f0cf5babdbdbd7fbeba646c380b'
SOURCE146 = '690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185'
PROFILE = 'src/experimental_swift_reactor/cache/initial_profile_v1.rs'
ACCOUNT_PATH = 'src/experimental_swift_reactor/cache/initial_profile_v1/host_account_v1.rs'
HELPER_PATH = 'src/experimental_swift_reactor/cache/initial_profile_v1/emission_bound_v1.rs'
CONTROL = 'src/experimental_swift_reactor/control.rs'
LOADER = 'src/experimental_swift_reactor/retained_profile_loader_v1.rs'
checks = H.checks
require = H.require
sha = H.sha
inputs = {}


def read(path):
    data = Path(path).read_bytes()
    inputs[Path(path).relative_to(ROOT).as_posix()] = {'bytes': len(data), 'sha256': sha(data)}
    return data


def load(path):
    return json.loads(read(path))


def row(path, data):
    return {'path': path, 'bytes': len(data), 'sha256': sha(data)}


def roster(source):
    members = [row(p, source[p]) for p in sorted(source, key=Path)]
    return {'schema': 1, 'members': members, 'member_count': len(members), 'tree_sha256': sha(H.canon(members))}


def seal(folder, expected, count, size):
    raw = read(folder/'seal.json')
    require('exact packet seal ' + folder.name, sha(raw) == expected)
    s = json.loads(raw)
    require('packet closure dimensions ' + folder.name, len(s['members']) == count and sum(x['bytes'] for x in s['members']) == size)
    for m in s['members']:
        require('sealed member ' + folder.name + '/' + m['path'], row(m['path'], read(folder/m['path'])) == m)


def vector(data):
    """Decode the frozen u64-little-endian length-prefixed preimage format."""
    count, cursor, answer = int.from_bytes(data[:8], 'little'), 8, []
    for _ in range(count):
        n = int.from_bytes(data[cursor:cursor+8], 'little')
        cursor += 8
        if cursor+n > len(data):
            raise ValueError('truncated preimage')
        answer.append(data[cursor:cursor+n].decode())
        cursor += n
    if cursor != len(data):
        raise ValueError('unconsumed preimage')
    return answer


def compiler_binding(mode, expected_compiled, source_manifest):
    pre = FRESH/'preimages'/mode
    manifest_raw = read(pre/'manifest.json')
    manifest = json.loads(manifest_raw)
    binding = load(pre/'binding.json')
    receipt = load(FRESH/'commands'/mode/'receipt.json')
    argv_raw, env_raw, version_raw = [read(pre/n) for n in ('argv.bin', 'environment.bin', 'compiler-version.txt')]
    expected_keys = {
        'MIXER_LOADER_MANIFEST_SHA256': sha(manifest_raw),
        'MIXER_LOADER_COMMAND_SHA256': sha(argv_raw),
        'MIXER_LOADER_COMPILE_ENV_SHA256': sha(env_raw),
        'MIXER_LOADER_COMPILER_VERSION_SHA256': sha(version_raw),
        'MIXER_LOADER_COMPILER_SHA256': manifest['tools']['rustc']['sha256'],
    }
    require('five frozen compiler preimages ' + mode, binding['keys'] == expected_keys and all(receipt['environment'][k] == v for k, v in expected_keys.items()))
    require('compiler argv exact preimage ' + mode, vector(argv_raw) == receipt['argv'])
    without_keys = {k: v for k, v in receipt['environment'].items() if k not in expected_keys}
    require('compiler environment exact preimage ' + mode, dict(x.split('=', 1) for x in vector(env_raw)) == without_keys)
    require('compiler source146 distribution binding ' + mode, manifest['distribution'] == source_manifest and manifest['compiled_source'] == expected_compiled and binding['compiled_tree'] == expected_compiled['tree_sha256'] and binding['distribution_tree'] == SOURCE146)
    require('same accepted compiler and target ' + mode, expected_keys['MIXER_LOADER_COMPILER_SHA256'] == 'dd6f58440b3418aa9157ae3f05d71eecff741ca41bc4eec120e7e8f2d933b9a0' and '--target' in receipt['argv'] and receipt['argv'][receipt['argv'].index('--target')+1] == 'aarch64-apple-darwin' and b'rustc 1.99.0' in version_raw)
    require('compiler command scope remains metadata data ' + mode, manifest['genuine_fixture_loader_VM_cache_scope_construct_writer_execution'] is False and receipt['global_process_inventory'] is False and receipt['exit_code'] == (0 if mode == 'exact146-metadata-mir' else 1))
    if mode == 'exact146-metadata-mir':
        data = gzip.decompress(read(FRESH/'commands'/mode/'stdout.gz'))
    else:
        data = read(FRESH/'commands'/mode/'stdout')
    err = read(FRESH/'commands'/mode/'stderr')
    for kind, actual in [('stdout', data), ('stderr', err)]:
        require('raw frozen compiler ' + mode + ' ' + kind, sha(actual) == receipt[kind]['sha256'] and len(actual) == receipt[kind]['bytes'])
    return receipt, data, err, expected_keys


def normalized(text, prefix):
    """Erase only exact frozen compiler scratch root and .rs source spans."""
    return re.sub(r'(?<=\.rs):\d+:\d+: \d+:\d+', ':<SPAN>', text.replace(prefix+'/', '<VM>/'))


def body_without_comments(text, prefix):
    return '\n'.join(line.split('//', 1)[0].rstrip() for line in normalized(text, prefix).splitlines())


def raw_roles(body):
    header = body.splitlines()[0]
    match = re.fullmatch(r'fn [^(]+\((.*)\) -> (.*) \{', header)
    if not match:
        raise ValueError('unknown MIR header')
    roles = [{'local': n, 'kind': 'parameter', 'compiler_type': t} for n, t in re.findall(r'(_\d+): (.*?)(?=, _\d+:|$)', match[1])]
    roles += [{'local': n, 'kind': 'return-place' if n == '_0' else 'local-or-temporary', 'compiler_type': t} for n, t in re.findall(r'^\s+let (?:mut )?(_\d+): (.*);(?:\s*//[^\n]*)?$', body, flags=re.M)]
    if len(roles) != len({r['local'] for r in roles}):
        raise ValueError('duplicate MIR role')
    return roles


def operation(code, roles):
    mentions = re.findall(r'\b_\d+\b', code)
    constants = []
    for m in re.finditer(r'\bconst\s+', code):
        token = re.match(r'(?:\d+_(?:u64|usize)|true\b|false\b|\(\))', code[m.end():])
        if not token:
            raise ValueError('unpriced constant')
        v = token[0]
        constants.append({'text': v, 'bytes': 0 if v == '()' else 1 if v in ('true', 'false') else 8, 'scalar_leaves': 1})
    base = 2 + sum(code.count(ch) for ch in '()[].*&') + len(re.findall(r'\bas\b', code))
    scalar = 2*sum(roles[x]['scalar_leaves']+roles[x]['pointee_scalar_leaves'] for x in mentions) + 2*len(constants)
    native = 2*sum(roles[x]['bytes']+roles[x]['pointee_bytes'] for x in mentions) + 2*sum(c['bytes'] for c in constants)
    if code == 'return;':
        scalar += 2*(roles['_0']['scalar_leaves']+roles['_0']['pointee_scalar_leaves'])
        native += 2*(roles['_0']['bytes']+roles['_0']['pointee_bytes'])
    return {'local_mentions': mentions, 'constants': constants, 'base_action_units': base, 'scalar_fetch_store_units': scalar, 'source_action_units': base+scalar, 'native_sized_occurrence_bytes': native}


def prepare():
    for name, expected in [
        ('guarded-snapshot-parent-work-host-acceptance.json', '479d0fd1114cd7512c369dae0038a7ccd2407854f5089669ba5e020f2225cd3a'),
        ('guarded-snapshot-host-composition-host-acceptance.json', 'c176aa3802d267d1e5bac6c5c281b1122058d81c4fbc5fa3eff49a05ca404ee8')]:
        require('exact root acceptance ' + name, sha(read(V/'swift-semantic-adapter-root-review'/name)) == expected)
    seal(OLD, 'bc9426ad22da41b354094b1778685bb7bf834e03fc22101272c2f08bf5d2b857', 52, 1665166)
    seal(REVIEW, 'ffdd027f5550f315fb7c63dcee7e532e7aea1d4be39c478d225f8f6ed09a7b2b', 46, 767864)
    seal(COMPOSE, '2fc002b2598effdc70a74ecfa3da775b4aa82f2572cbbb93650207925238dc2e', 152, 1301753)
    seal(FRESH, 'c9ccf4649a4dd5c11ac62d403e6443f58dd018562d667f76d16dc422354f3e63', 96, 1453031)
    old_manifest, new_manifest = load(ACCOUNT/'source-manifest.json'), load(COMPOSE/'source-manifest.json')
    old_source, source = {}, {}
    for m in old_manifest['members']:
        p = m['path']
        raw = read(ACCOUNT/'host_account.rs') if p == ACCOUNT_PATH else read(BASE/p)
        if p == PROFILE:
            raw += b'\n\n' + read(V/'swift-guarded-snapshot-bootstrap-host-boundary/driver.inc.rs') + b'\n\n' + read(ACCOUNT/'entry.inc.rs')
        require('exact source145 member ' + p, row(p, raw) == m)
        old_source[p] = raw
    overlays = {PROFILE, CONTROL, LOADER, ACCOUNT_PATH, HELPER_PATH}
    for m in new_manifest['members']:
        p = m['path']
        raw = read(COMPOSE/'overlay/vm'/p) if p in overlays else read(BASE/p)
        require('exact source146 member ' + p, row(p, raw) == m)
        source[p] = raw
    require('both exact tree identities', roster(old_source)['tree_sha256'] == SOURCE145 and roster(source) == new_manifest and new_manifest['tree_sha256'] == SOURCE146)
    changed = [p for p in old_source if source[p] != old_source[p]]
    added = sorted(set(source)-set(old_source))
    require('bounded source146 delta roster', set(changed) == {PROFILE, CONTROL, LOADER} and added == [HELPER_PATH] and len(set(old_source)&set(source)) == 145)
    require('account bootstrap and typed entry exact unchanged source', source[ACCOUNT_PATH] == old_source[ACCOUNT_PATH] == read(ACCOUNT/'host_account.rs') and source[PROFILE].endswith(b'\n\n'+read(V/'swift-guarded-snapshot-bootstrap-host-boundary/driver.inc.rs')+b'\n\n'+read(ACCOUNT/'entry.inc.rs')))
    patch = ''.join(''.join(difflib.unified_diff(old_source.get(p, b'').decode().splitlines(True), source[p].decode().splitlines(True), fromfile='source145/'+p, tofile='source146/'+p)) for p in sorted(set(changed+added)))
    delta = {'changed': [{'path': p, 'before_sha256': sha(old_source[p]), 'after_sha256': sha(source[p]), 'before_bytes': len(old_source[p]), 'after_bytes': len(source[p])} for p in changed], 'added': [row(p, source[p]) for p in added], 'unchanged': 142, 'net_bytes_added': sum(map(len, source.values()))-sum(map(len, old_source.values()))}
    require('new helper stays undispatched', sum(v.count(b'checked_snapshot_emission_bound_v1') for p, v in source.items() if p != HELPER_PATH) == 0)

    query_binding = load(FRESH/'layout-query-bindings.json')
    query_fragment = read(FRESH/'layout-queries.inc.rs')
    query_source = dict(source)
    query_source[ACCOUNT_PATH] += query_fragment
    query_source['src/lib.rs'] = b'#![feature(never_type)]\n'+query_source['src/lib.rs']
    require('query source only separate bounded diagnostics overlay', roster(query_source) == query_binding['compiled_source'] and query_binding['distribution_tree'] == SOURCE146 and query_binding['fixture_or_binding_constructor_created'] is False)
    mr, compiler_stdout, _, metadata_keys = compiler_binding('exact146-metadata-mir', new_manifest, new_manifest)
    qr, _, layout_stderr, layout_keys = compiler_binding('actual90-layout-queries', roster(query_source), new_manifest)
    old_prefix = str(ACCOUNT/'owned-mir-work/vm')
    fresh_prefix = mr['environment']['CARGO_MANIFEST_DIR']
    old_inventory = load(ACCOUNT/'caller-inventory.json')
    old_mir = H.mir_functions(read(ACCOUNT/'entry-and-account.mir').decode())
    fresh_raw = gzip.decompress(read(FRESH/'entry-and-account.mir.gz'))
    archive = load(FRESH/'entry-and-account.mir-archive.json')
    require('fresh selected MIR lossless archive', sha(fresh_raw) == archive['raw_sha256'] and len(fresh_raw) == archive['raw_bytes'])
    fresh_mir = H.mir_functions(fresh_raw.decode())
    require('nineteen retained body count', len(old_mir) == len(fresh_mir) == len(old_inventory['functions']) == 19)
    for old_body, new_body, record in zip(old_mir, fresh_mir, old_inventory['functions']):
        require('normalized entire fresh MIR body ' + record['header'], body_without_comments(old_body, old_prefix) == body_without_comments(new_body, fresh_prefix))
        expected = [{k: r[k] for k in ('local', 'kind', 'compiler_type')} for r in record['roles']]
        require('fresh raw role identity ' + record['header'], normalized(H.canon(raw_roles(new_body)).decode(), fresh_prefix) == normalized(H.canon(expected).decode(), old_prefix))
    require('all396 roles retained', sum(len(raw_roles(b)) for b in fresh_mir) == 396)
    fresh_closure = load(FRESH/'mir-and-closure.json')['closure']
    closure_type = fresh_closure['compiler_type']
    match = re.search(r'^print-type-size type: `'+re.escape(closure_type)+r'`: (\d+) bytes, alignment: (\d+) bytes$', compiler_stdout.decode(), re.M)
    require('actual fresh exact dispatch closure layout', match is not None and tuple(map(int, match.groups())) == (8, 8) and fresh_closure['bytes'] == 8 and fresh_closure['alignment'] == 8)

    query_records = query_binding['query']
    require('ninety fresh concrete query source declarations', len(query_records) == 90 and re.findall(rb'const FINAL146_LAYOUT_(\d+):', query_fragment) == [str(i).encode() for i in range(90)])
    sizes, seen, diagnostic_records = {'()': 0}, set(), []
    require('only expected compiler size diagnostics', layout_stderr.count(b'error[E0308]') == 90 and not re.findall(rb'error\[E(?!0308)\d+\]', layout_stderr))
    for part in layout_stderr.decode().split('error[E0308]:')[1:]:
        indices = {int(x) for x in re.findall(r'FINAL146_LAYOUT_(\d+)', part)}
        require('one fresh diagnostic query identity', len(indices) == 1)
        index = next(iter(indices))
        require('unique query occurrence ' + str(index), index not in seen)
        seen.add(index)
        m = re.search(r'std::mem::size_of::<(.+)>\(\)\];', part)
        extent = int(re.search(r'found one with a size of (\d+)', part)[1])
        ty = query_records[index]['concrete']
        require('fresh diagnostic concrete type ' + str(index), m[1] == ty and (ty not in sizes or sizes[ty] == extent))
        sizes[ty] = extent
        diagnostic_records.append({'index': index, 'type': ty, 'bytes': extent})
    require('complete fresh query identity set', seen == set(range(90)) and len(sizes) == 90)
    require('fresh measured sizes match retained declaration specializations', sizes == load(FRESH/'fresh-layout-results.json')['actual_type_sizes'] == old_inventory['actual_type_sizes'])
    size_lookup = {H.short(k): v for k, v in sizes.items()}
    shapes = H.SourceShapes(source)
    old_shapes = load(OLD/'scalar-shapes.json')
    old_ledger = load(OLD/'operation-ledger.json')['functions']
    p0_fresh = [(body, old_record) for body, old_record in zip(fresh_mir, old_inventory['functions']) if old_record['phase'] == 'P0-pre-existing-parent-account-bookkeeping']
    recalculated, functions, path_reports, all_roles, operations = {}, [], {}, 0, 0
    for (body, accepted), prior in zip(p0_fresh, old_ledger):
        identity, roles = prior['id'], {}
        observed = {r['local']: r for r in raw_roles(body)}
        for old_role in accepted['roles']:
            local = old_role['local']
            concrete = closure_type if '{closure@' in old_role['concrete_production_type'] else old_role['concrete_production_type']
            extent = 8 if '{closure@' in concrete else sizes[concrete]
            pointed = re.sub(r"^&\s*(?:'[^ ]+\s+)?(?:mut\s+)?", '', concrete) if concrete.startswith('&') else None
            pointed_bytes = size_lookup[H.short(pointed)] if pointed else 0
            roles[local] = {**observed[local], 'concrete_production_type': concrete, 'bytes': extent, 'scalar_leaves': shapes.n(concrete), 'pointee_type': pointed, 'pointee_bytes': pointed_bytes, 'pointee_scalar_leaves': shapes.n(pointed) if pointed else 0}
            prior_role = prior['roles'][local]
            require('fresh measured P0 role dimensions ' + identity + local, all(roles[local][k] == prior_role[k] for k in ('bytes', 'scalar_leaves', 'pointee_bytes', 'pointee_scalar_leaves')))
        graph, weighted_calls = H.mir_blocks(body), collections.Counter()
        source_total = 2 + 2*sum(r['scalar_leaves']+r['pointee_scalar_leaves'] for r in roles.values() if r['kind'] == 'parameter')
        native_total = 2*sum(r['bytes']+r['pointee_bytes'] for r in roles.values() if r['kind'] == 'parameter')
        entry_s, entry_b = source_total, native_total
        out_blocks = {}
        require('fresh complete CFG block set ' + identity, set(graph) == set(prior['blocks']))
        for bid, bb in graph.items():
            former = prior['blocks'][bid]
            require('fresh CFG cleanup alternatives ' + identity + bid, bb['cleanup'] == former['cleanup'])
            require('fresh full operation count ' + identity + bid, len(bb['lines']) == len(former['lines']))
            block_s = block_b = 0
            rows = []
            for (line, code), old_row in zip(bb['lines'], former['lines']):
                operations += 1
                cost = operation(code, roles)
                call = H.call_kind(code, identity)
                require('exact operation after metadata-only normalization ' + identity + str(line), normalized(code, fresh_prefix) == normalized(old_row['code'], old_prefix))
                require('fresh operation cost and cut ' + identity + str(line), all(cost[k] == old_row[k] for k in cost) and call == old_row['call_cut'])
                block_s += cost['source_action_units']
                block_b += cost['native_sized_occurrence_bytes']
                if call:
                    weighted_calls[call] += former['occurrence_bound']
                rows.append({'body_line': line, 'code': code, **cost, 'call_cut': call})
            weight = former['occurrence_bound']
            source_total += weight*block_s
            native_total += weight*block_b
            out_blocks[bid] = {'cleanup': bb['cleanup'], 'occurrence_bound': weight, 'lines': rows, 'source_action_units': block_s, 'native_sized_occurrence_bytes': block_b}
        paths = H.enumerate_paths(identity, graph)
        maxima = collections.Counter()
        for kind, path in paths:
            maxima |= collections.Counter(path)
            require('fresh all normal refusal cleanup path cost ' + identity + str(len(checks)), entry_s+sum(out_blocks[b]['source_action_units'] for b in path) <= source_total and entry_b+sum(out_blocks[b]['native_sized_occurrence_bytes'] for b in path) <= native_total)
        require('fresh path occurrence envelope ' + identity, all(n <= out_blocks[b]['occurrence_bound'] for b, n in maxima.items()))
        require('fresh function dimensions equal accepted source145 rule ' + identity, (source_total, native_total, source_total+native_total) == (prior['source_action_units_per_invocation'], prior['native_sized_occurrence_bytes_per_invocation'], prior['combined_surface_units_per_invocation']) and dict(weighted_calls) == prior['calls_per_invocation_bound'])
        recalculated[identity] = {'source': source_total, 'native': native_total, 'combined': source_total+native_total}
        path_reports[identity] = {'terminal_paths': len(paths), 'terminal_kinds': dict(collections.Counter(k for k, p in paths)), 'max_block_occurrences': dict(maxima)}
        functions.append({'id': identity, 'header': body.splitlines()[0], 'MIR_sha256': sha(body.encode()), 'prior_MIR_sha256': prior['MIR_sha256'], 'roles': roles, 'blocks': out_blocks, 'calls_per_invocation_bound': dict(weighted_calls), 'source_actions': source_total, 'native_occurrence_allowance': native_total, 'combined': source_total+native_total})
        all_roles += len(roles)
    require('exact P0 identity closure', len(functions) == 15 and all_roles == 208 and operations == 613 and sum(p['terminal_paths'] for p in path_reports.values()) == 273)
    require('exact54 transitive source shape closure', set(shapes.used) == set(old_shapes['definitions']) and len(shapes.used) == 54)
    changed_declarations = []
    for name, proof in shapes.used.items():
        former = old_shapes['definitions'][name]
        require('all source-visible field and variant shapes ' + name, {k: v for k, v in proof.items() if k != 'declaration_sha256'} == {k: v for k, v in former.items() if k != 'declaration_sha256'})
        if proof['declaration_sha256'] != former['declaration_sha256']:
            changed_declarations.append({'name': name, 'before_sha256': former['declaration_sha256'], 'after_sha256': proof['declaration_sha256'], 'fields_and_variants_same': True})
    require('only one reviewed field-name data declaration changes', [x['name'] for x in changed_declarations] == ['SnapshotPrimaryRetirementV1'])
    require('actual fresh payload and wrapper geometry', shapes.n('OwnedFixtureOutcomeV1') == 2556 and shapes.n("PrepaidOwnedV1<'_, OwnedFixtureOutcomeV1>") == 2560 and sizes['OwnedFixtureOutcomeV1'] == 13608 and sizes["PrepaidOwnedV1<'_, OwnedFixtureOutcomeV1>"] == 13624)
    drop_old = load(OLD/'drop-surface.json')
    by_name = {f['id']: f for f in functions}
    drop_s = drop_b = 0
    for d in drop_old['rows']:
        selected = [by_name[f]['roles'][local] for f, local in d['operand_selectors']]
        ds = 4 + 2*sum(r['scalar_leaves'] for r in selected)
        db = 2*sum(r['bytes'] for r in selected)
        require('fresh finite drop row dimensions ' + d['operation'], (ds, db, ds+db) == (d['source_action_units_each'], d['native_sized_occurrence_bytes_each'], d['combined_surface_units_each']))
        drop_s += d['occurrence_bound']*ds
        drop_b += d['occurrence_bound']*db
    fixed_s = drop_s+sum(v['source'] for k, v in recalculated.items() if k not in ('inspect_v1', 'usage_v1'))
    fixed_b = drop_b+sum(v['native'] for k, v in recalculated.items() if k not in ('inspect_v1', 'usage_v1'))
    require('source146 candidate formula dimensions', (fixed_s, fixed_b, fixed_s+fixed_b, recalculated['inspect_v1']['combined'], recalculated['usage_v1']['combined'], drop_s+drop_b) == (416998, 2211090, 2628088, 194231, 1039, 131334))
    require('source146 still pending selected constructors', all('::Ok(' not in next(f['header']+'\n'+ '\n'.join(r['code'] for b in f['blocks'].values() for r in b['lines']) for f in functions if f['id'] == name) for name in ('selected_parent_account_v1', 'selected_whole_quote_v1')) and b'Err(RefusalV1::WholeQuotePending)' in source[ACCOUNT_PATH] and b'Err(RefusalV1::RootPolicyPending)' in source[ACCOUNT_PATH])
    cut_interface = load(OLD/'cost-interface.json')
    prior_review = load(REVIEW/'review.json')
    require('all cuts remain required with symbolic counts', cut_interface['operational_grant'] is False and cut_interface['root_constructors_currently_pending'] is True and prior_review['required_unselected_cuts'] and 'neither can default to zero' in cut_interface['I_U'])
    report = {'schema': 1, 'status': 'source146-P0-account-surface-rebinding-candidate-pending-independent-cross-review', 'source_tree_sha256': SOURCE146, 'source_members': 146, 'prior_source_tree_sha256': SOURCE145, 'prior_review_immutable': True, 'formula': '2628088 + 194231*I + 1039*U', 'fixed_source_actions': fixed_s, 'fixed_native_occurrence_allowance': fixed_b, 'drop_addendum': drop_s+drop_b, 'symbolic_I_and_U_selected': False, 'functions': 15, 'roles': all_roles, 'logical_source_object_bytes': sum(r['bytes'] for f in functions for r in f['roles'].values()), 'operations': operations, 'transitive_shapes': len(shapes.used), 'terminal_paths': 273, 'fresh_data_only': {'retained_MIR_functions': 19, 'retained_MIR_roles': 396, 'native_query_diagnostics': 90, 'unique_nonunit_type_spellings': 89, 'exact_selected_closure_bytes': 8, 'exact_selected_closure_alignment': 8}, 'source_delta': delta, 'changed_declarations': changed_declarations, 'function_costs': recalculated, 'path_report': path_reports, 'required_cuts': prior_review['required_unselected_cuts'], 'limitations': prior_review['limitations'], 'new_compiler_invocations': 0, 'new_product_or_fixture_or_native_execution': False, 'full_P0_work_or_storage_or_host_quote': False, 'selected_policy_or_operational_grant': False, 'native_OTA_FieldLog_customer_GA': False, 'cross_review_complete': False, 'python': platform.python_version()}
    candidate_interface = dict(cut_interface, status='source146-rebinding-candidate-pending-independent-cross-review', source_tree_sha256=SOURCE146, source_members=146, cross_review_complete=False)
    return {'candidate.json': report, 'cost-interface.json': candidate_interface, 'operation-ledger.json': {'schema': 1, 'source_tree_sha256': SOURCE146, 'functions': functions}, 'scalar-shapes.json': {'schema': 1, 'source_tree_sha256': SOURCE146, 'definitions': shapes.used}, 'compiler-bindings.json': {'metadata_keys': metadata_keys, 'query_keys': layout_keys, 'source_tree_sha256': SOURCE146, 'diagnostics': diagnostic_records, 'data_only_no_new_compiler': True}, 'source-delta.patch': patch}


def main():
    outputs = prepare()
    outputs['candidate.json']['checks'] = len(checks)
    outputs['checks.json'] = {'checks': len(checks), 'labels': list(checks)}
    outputs['input-custody.json'] = {'schema': 1, 'files': dict(sorted(inputs.items())), 'source_tree_sha256': SOURCE146}
    for name, value in outputs.items():
        expected = value.encode() if isinstance(value, str) else (json.dumps(value, sort_keys=True, indent=2)+'\n').encode()
        if '--check-only' in sys.argv:
            if (HERE/name).read_bytes() != expected:
                raise AssertionError('candidate changed: ' + name)
        else:
            (HERE/name).write_bytes(expected)
    print(json.dumps({'passed': True, 'checks': len(checks), 'source_tree_sha256': SOURCE146, 'status': outputs['candidate.json']['status'], 'mode': 'check-only' if '--check-only' in sys.argv else 'prepare'}))


if __name__ == '__main__':
    main()
