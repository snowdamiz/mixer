#!/usr/bin/env python3
"""Consume the released root compile-only observation as immutable data."""
import collections
import copy
import json
from pathlib import Path
import re
import struct
import sys
sys.dont_write_bytecode = True
import audit as A

HERE, ROOT = A.HERE, A.ROOT
DATA = ROOT / 'verification/swift-guarded-snapshot-source146-leaf-payload-layouts'
RELEASE = ROOT / 'verification/swift-semantic-adapter-root-review/guarded-snapshot-source146-leaf-payload-layout-release.json'
RELEASE_SHA = '5a66c532917e723285c8d30ce9e40b2fc5d97012c9c8469349ab3cdbc87c6834'
SEAL_SHA = 'f2021a5fa0be89481bc02bdb811ec6ac2fb5e4112900a9f1e831135070be2952'


def uncount(raw):
    if len(raw) < 8 or len(raw) > 16384:
        raise ValueError('bad counted preimage extent')
    count = int.from_bytes(raw[:8], 'little')
    if count > 64:
        raise ValueError('too many counted values')
    cursor, result = 8, []
    for _ in range(count):
        if cursor + 8 > len(raw):
            raise ValueError('missing counted length')
        size = int.from_bytes(raw[cursor:cursor+8], 'little')
        cursor += 8
        if size >= 4096 or cursor + size > len(raw):
            raise ValueError('bad counted item')
        item = raw[cursor:cursor+size]
        if b'\0' in item:
            raise ValueError('NUL in counted item')
        result.append(item.decode())
        cursor += size
    if cursor != len(raw):
        raise ValueError('trailing counted bytes')
    return result


def diagnostics(messages, queries, appended, compiled_path, original_bytes):
    found = {}
    warnings = []
    for msg in messages:
        code = msg.get('code', {}).get('code') if msg.get('code') else None
        if msg.get('level') == 'warning':
            if code != 'unused_imports' or msg['message'] != 'unused import: `super::*`':
                raise ValueError('unexpected compiler warning')
            warnings.append(msg)
            continue
        if msg.get('level') == 'error' and code:
            if code != 'E0308' or msg['message'] != 'mismatched types':
                raise ValueError('unexpected compiler error')
            primary = [s for s in msg['spans'] if s['is_primary']]
            if len(primary) != 1:
                raise ValueError('ambiguous primary span')
            span = primary[0]
            if span['file_name'] != compiled_path or span['byte_start'] < original_bytes or span['byte_end'] > len(appended):
                raise ValueError('diagnostic outside appended query')
            labels = re.fullmatch(r'expected an array with a size of usize::MAX, found one with a size of (\d+)', span['label'] or '')
            if labels is None:
                raise ValueError('unexpected primary layout label')
            value = int(labels[1])
            texts = [line['text'] for s in msg['spans'] for line in s['text']]
            names = set(re.findall(r'LP_(SIZE|ALIGN)_(\d+)', '\n'.join(texts)))
            if len(names) != 1:
                raise ValueError('ambiguous query name')
            kind, index = names.pop()
            index = int(index)
            if index >= len(queries) or (index, kind) in found:
                raise ValueError('duplicate/unknown query')
            query = queries[index]
            method = 'size_of' if kind == 'SIZE' else 'align_of'
            expected_expr = '[(); std::mem::' + method + '::<' + query['concrete'] + '>()]'
            if appended[span['byte_start']:span['byte_end']].decode() != expected_expr:
                raise ValueError('primary byte span differs from concrete query')
            source_lines = appended.decode().splitlines()
            if span['line_start'] != span['line_end'] or texts[0] != source_lines[span['line_start']-1]:
                raise ValueError('diagnostic source line differs')
            for s in msg['spans']:
                if s['file_name'] != compiled_path or s['expansion'] is not None:
                    raise ValueError('diagnostic attributed through unexpected source expansion')
            if value <= 0 or value >= 1 << 64:
                raise ValueError('nonpositive/overflowing sized extent')
            found[(index, kind)] = value
        elif msg.get('level') == 'error':
            if msg['message'] != 'aborting due to 110 previous errors; 1 warning emitted':
                raise ValueError('unexpected compiler terminal error')
        elif msg.get('level') == 'failure-note':
            if msg['message'] != 'For more information about this error, try `rustc --explain E0308`.':
                raise ValueError('unexpected compiler failure note')
        else:
            raise ValueError('unexpected compiler diagnostic kind')
    expected = {(i, kind) for i in range(len(queries)) for kind in ['SIZE', 'ALIGN']}
    if set(found) != expected or len(warnings) != 1:
        raise ValueError('missing layout diagnostics')
    return found


def main():
    A.need('frozen layout root release digest', A.digest(A.read(RELEASE)) == RELEASE_SHA)
    release = A.load(RELEASE)
    packet = A.verify_packet(DATA, SEAL_SHA, 22)
    A.need('frozen layout release dimensions', packet['bytes'] == release['bytes'] == 603977 and release['seal_sha256'] == SEAL_SHA)
    selection = A.load(DATA / 'selection.json')
    results = A.load(DATA / 'results.json')
    binding = A.load(DATA / 'binding.json')
    closure = A.load(DATA / 'compiled-manifest.json')
    receipt = A.load(DATA / 'compiler-receipt.json')
    version_receipt = A.load(DATA / 'compiler-version-receipt.json')
    cleanup = A.load(DATA / 'cleanup.json')
    prior = A.load(A.PRODUCER / 'source-manifest.json')
    roster = A.load(A.PRODUCER / 'layout-query-roster.json')['sized_types']
    ci = A.load(A.PRODUCER / 'cost-interface.json')
    A.need('same exact146 source manifest in compile closure', closure['source_manifest'] == prior and prior['tree_sha256'] == A.TREE and A.digest(A.canon(prior['members'])) == A.TREE)
    original = {}
    for row in prior['members']:
        path = row['path']
        overlay = A.COMPOSE / 'overlay/vm' / path
        data = A.read(overlay if overlay.exists() else A.BASE / path)
        A.need('layout original actual146 member ' + path, len(data) == row['bytes'] and A.digest(data) == row['sha256'])
        original[path] = data
    append_to = selection['append_to']
    fragment = A.read(DATA / 'layout-queries.inc.rs')
    A.need('source append identity', append_to == 'src/experimental_swift_reactor/cache/initial_profile_v1.rs' and selection['append_original_bytes'] == len(original[append_to]) == 49980 and selection['append_original_sha256'] == A.digest(original[append_to]))
    A.need('query fragment bound in compiled closure', A.digest(fragment) == closure['query_fragment_sha256'])
    A.need('selection and runner bytes bound in closure', A.digest(A.read(DATA / 'selection.json')) == closure['selection_sha256'] and A.digest(A.read(DATA / 'query.py')) == closure['script_sha256'])
    queries = selection['queries']
    A.need('55 unique query entries', len(queries) == len(results['queries']) == 55 and len({q['key'] for q in queries}) == 55)
    A.need('exact 53 frozen concrete types and coefficients', [(q['key'], q['concrete'], q['leaf_occurrence_coefficient']) for q in queries[:53]] == [(q['key'], q['concrete_type'], q['occurrence_coefficient']) for q in roster] and {q['key']:q['leaf_occurrence_coefficient'] for q in queries[:53]} == ci['missing_native_occurrence_coefficients'])
    A.need('two payload-only extras add no leaf coefficient', [(q['key'],q['concrete'],q['leaf_occurrence_coefficient']) for q in queries[53:]] == [('SwiftFunctionCache','crate::experimental_swift_reactor::cache::SwiftFunctionCache',0), ('SwiftSlot','crate::experimental_swift_reactor::cache::SwiftSlot',0)])
    expected_fragment = '\n#[cfg(mixer_bootstrap_one_fixture_v1)]\nmod source146_leaf_payload_layout_queries_v1 {\nuse super::*;\n'
    for i, query in enumerate(queries):
        expected_fragment += f"const LP_SIZE_{i}: [(); usize::MAX] = [(); std::mem::size_of::<{query['concrete']}>()];\n"
        expected_fragment += f"const LP_ALIGN_{i}: [(); usize::MAX] = [(); std::mem::align_of::<{query['concrete']}>()];\n"
    expected_fragment += '}\n'
    A.need('exact unused const-only fragment, no visibility rewrite or executable body', fragment == expected_fragment.encode())
    mask = A.lexical_mask(original[append_to].decode())
    A.need('query append is at module EOF', mask.count('{') == mask.count('}'))
    compiled = []
    for row in prior['members']:
        path = row['path']
        data = original[path] + (fragment if path == append_to else b'')
        compiled.append({'path':path, 'bytes':len(data), 'sha256':A.digest(data)})
    A.need('all 146 compiled source members reconstructed', compiled == closure['compiled_source_members'] and A.digest(A.canon(compiled)) == closure['compiled_tree_sha256'])
    A.need('only appended member differs', [r['path'] for r,s in zip(compiled,prior['members']) if r != s] == [append_to])
    A.need('unmodified host11 support tree bound', closure['host_support']['member_count'] == 11 and closure['host_support']['tree_sha256'] == ci['host_tree_sha256'] and A.digest(A.canon(closure['host_support']['members'])) == ci['host_tree_sha256'])
    argv = uncount(A.read(DATA / 'argv.bin'))
    env_items = uncount(A.read(DATA / 'environment.bin'))
    env = dict(item.split('=',1) for item in env_items)
    A.need('argv frame exact', argv == receipt['argv'])
    A.need('compile environment preimage is exact five base fields', len(env) == 5 and set(env) == {'CARGO_MANIFEST_DIR','TMPDIR','SDKROOT','RUSTC_BOOTSTRAP','PATH'} and all(receipt['environment'][k] == v for k,v in env.items()))
    version = A.read(DATA / 'compiler-version.stdout')
    A.need('retained exact compiler version', version.decode().startswith('rustc 1.99.0 (b940084d7 2026-09-28)\n') and b'host: aarch64-apple-darwin\n' in version and A.digest(version) == closure['compiler_version_sha256'])
    expected_keys = {'MIXER_LOADER_MANIFEST_SHA256':A.digest(A.read(DATA / 'compiled-manifest.json')), 'MIXER_LOADER_COMMAND_SHA256':A.digest(A.read(DATA / 'argv.bin')), 'MIXER_LOADER_COMPILE_ENV_SHA256':A.digest(A.read(DATA / 'environment.bin')), 'MIXER_LOADER_COMPILER_SHA256':closure['compiler_sha256'], 'MIXER_LOADER_COMPILER_VERSION_SHA256':A.digest(version)}
    A.need('all five compile identity preimages exact', expected_keys == binding['compile_identity_keys'] and all(receipt['environment'][k] == v for k,v in expected_keys.items()))
    A.need('no extra compiler environment authorities', set(receipt['environment']) == set(env) | set(expected_keys))
    expected_compiler = '/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc'
    expected_path = str(DATA / 'owned-work/vm' / append_to)
    expected_argv = [expected_compiler, '--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin','-C','opt-level=0','-C','overflow-checks=yes','-C','panic=unwind','-Zmir-opt-level=0','--error-format=json']
    for feature in ['experimental-swift-reactor','experimental-swift-wasi','experimental-stream-validation','experimental-function-cache']:
        expected_argv += ['--cfg', 'feature="'+feature+'"']
    expected_argv += ['--cfg','mixer_bootstrap_one_fixture_v1','--crate-type','rlib',str(DATA / 'owned-work/vm/src/lib.rs'),'--emit=metadata='+str(DATA / 'owned-work/output.rmeta')]
    A.need('compile context only and exact production feature set', argv == expected_argv and '--test' not in argv and not any('cfg(test)' in a for a in argv))
    # Read the compiler file only to bind the retained version to actual bytes.
    compiler_bytes = Path(expected_compiler).read_bytes()
    A.need('compiler binary byte digest matches retained compile', A.digest(compiler_bytes) == closure['compiler_sha256'] == results['compiler_sha256'] == 'dd6f58440b3418aa9157ae3f05d71eecff741ca41bc4eec120e7e8f2d933b9a0')
    stderr = A.read(DATA / 'compiler.stderr')
    stdout = A.read(DATA / 'compiler.stdout')
    A.need('compiler stdout/stderr exact raw extents', len(stderr) == receipt['outputs']['stderr']['bytes'] and A.digest(stderr) == receipt['outputs']['stderr']['sha256'] and len(stdout) == 0 and A.digest(stdout) == receipt['outputs']['stdout']['sha256'])
    A.need('expected compile-only diagnostic exit', receipt['exit_code'] == 1 and not receipt['timed_out'] and receipt['direct_child_waited'] and receipt['owned_group_absent'] and not receipt['product_runtime'] and not receipt['global_process_inventory'])
    messages = [json.loads(line) for line in stderr.decode().splitlines()]
    appended = original[append_to] + fragment
    found = diagnostics(messages, queries, appended, expected_path, len(original[append_to]))
    A.need('110 primary structured diagnostics bound to exact source bytes', len(found) == results['diagnostic_count'] == 110)
    normalized = []
    for index, query in enumerate(queries):
        expected = dict(query, size=found[(index,'SIZE')], alignment=found[(index,'ALIGN')])
        A.need('structured result agrees with raw query ' + str(index), results['queries'][index] == expected)
        size, align = expected['size'], expected['alignment']
        A.need('actual sized alignment valid ' + str(index), align > 0 and align & (align-1) == 0 and size % align == 0)
        normalized.append({'index':index, 'key':query['key'], 'size':size, 'alignment':align, 'leaf_coefficient':query['leaf_occurrence_coefficient']})
    expected_diagnostics = [{'index':i,'kind':kind.lower(),'concrete':q['concrete'],'value':found[(i,kind)]} for i,q in enumerate(queries) for kind in ['SIZE','ALIGN']]
    A.need('all normalized diagnostic rows agree', results['diagnostics'] == expected_diagnostics)
    sizes = {q['key']:q['size'] for q in results['queries'] if q['leaf_occurrence_coefficient']}
    weighted = sum(ci['missing_native_occurrence_coefficients'][key]*size for key,size in sizes.items())
    A.need('all native size extents closed by actual146 queries', set(sizes) == set(ci['missing_native_occurrence_coefficients']) and weighted == 3479056 and weighted + ci['known_native_occurrence_bytes'] == 3597716)
    A.need('no metadata/runtime/backing promotion', not results['metadata_produced'] and not results['product_executed'] and not closure['product_runtime'] and not release['actual_resource_backing_or_drop_closed'] and not release['whole_component_or_grant_accepted'])
    A.need('retained compiler cleanup is exact and scratch absent', cleanup['completed'] and cleanup['command_children_waited_and_groups_absent'] and cleanup['owned_scratch_removed'] and cleanup['removed_files'] == 146 and not (DATA / 'owned-work').exists() and not cleanup['native_or_product_processes_started'])
    A.need('retained removed file identities match reconstructed compile tree', {r['path']:r for r in cleanup['scratch_inventory']} == {'vm/'+r['path']:dict(r,path='vm/'+r['path']) for r in compiled})
    A.need('retained removed byte sum agrees', cleanup['removed_bytes'] == sum(r['bytes'] for r in compiled) == 19692585)
    # Deliberate pure corruption must refuse instead of accepting a partial query.
    errors = [i for i,m in enumerate(messages) if m.get('code') and m['code']['code']=='E0308']
    mutant = copy.deepcopy(messages)
    del mutant[errors[0]]
    A.reject('missing raw query refuses', diagnostics, mutant, queries, appended, expected_path, len(original[append_to]))
    mutant = copy.deepcopy(messages)
    mutant.append(copy.deepcopy(messages[errors[0]]))
    A.reject('duplicate raw query refuses', diagnostics, mutant, queries, appended, expected_path, len(original[append_to]))
    for change in ['code','path','label','bytes','index','warning']:
        mutant = copy.deepcopy(messages)
        msg = mutant[errors[0]]
        primary = next(s for s in msg['spans'] if s['is_primary'])
        if change == 'code':
            msg['code']['code'] = 'E9999'
        elif change == 'path':
            primary['file_name'] = 'foreign.rs'
        elif change == 'label':
            primary['label'] = 'expected an array with a size of usize::MAX, found one with a size of 0'
        elif change == 'bytes':
            primary['byte_start'] -= 1
        elif change == 'index':
            for span in msg['spans']:
                for row in span['text']:
                    row['text'] = row['text'].replace('LP_SIZE_0','LP_SIZE_999')
        else:
            mutant[0]['code']['code'] = 'unused_variable'
        A.reject('corrupted raw diagnostic refuses ' + change, diagnostics, mutant, queries, appended, expected_path, len(original[append_to]))
    raw_frame = A.read(DATA / 'argv.bin')
    for raw in [b'', raw_frame[:-1], raw_frame+b'X', struct.pack('<Q',65), struct.pack('<QQ',1,4096), struct.pack('<QQ',1,1)+b'\0']:
        A.reject('corrupt counted preimage refuses ' + str(len(raw)), uncount, raw)
    report = {'schema':1,'status':'source146-layout-substitution-independently-accepted-for-finite-component','layout_packet_seal_sha256':SEAL_SHA,'layout_root_release_sha256':RELEASE_SHA,'source_tree_sha256':A.TREE,'compiled_query_tree_sha256':closure['compiled_tree_sha256'],'compiler_sha256':closure['compiler_sha256'],'compiler_context':'rustc 1.99.0 aarch64-apple-darwin opt0 unwind, metadata-only expected E0308 diagnostics','all55sizes_and_alignments_reconciled':True,'raw_structured_diagnostics':110,'leaf_sized_terms_closed':53,'leaf_new_native_occurrence_bytes':weighted,'leaf_known_plus_new_native_occurrence_bytes':weighted+ci['known_native_occurrence_bytes'],'fixed_source_actions_unchanged':639237,'combined_constant_source_and_native_component':639237+weighted+ci['known_native_occurrence_bytes'],'remaining_expression':'4236953 + 4376*L_str + sum(required_positive_cut_coefficient*independently_accepted_cut_price)','remaining_positive_cuts':33,'unsized_string_bound_selected':False,'callee_drop_backing_prices_selected':False,'metadata_success':False,'compiler_invoked_by_review':False,'product_runtime':False,'complete_host_quote':False,'operational_grant':False,'native_OTA_GA':False,'independent_assertions':len(A.CHECKS),'queries':normalized}
    outputs = {'layout-review-results.json':report, 'layout-input-custody.json':{'packet':packet,'inputs':A.INPUTS}, 'layout-assertions.json':{'count':len(A.CHECKS),'checks':A.CHECKS}}
    for name,value in outputs.items():
        if '--read-only' in sys.argv or (HERE / 'seal.json').exists():
            if json.loads((HERE/name).read_bytes()) != value:
                raise AssertionError('retained independent layout result differs '+name)
        else:
            (HERE/name).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['status','independent_assertions','leaf_sized_terms_closed','leaf_new_native_occurrence_bytes','leaf_known_plus_new_native_occurrence_bytes','combined_constant_source_and_native_component','compiler_invoked_by_review','product_runtime']}))


if __name__ == '__main__':
    main()
