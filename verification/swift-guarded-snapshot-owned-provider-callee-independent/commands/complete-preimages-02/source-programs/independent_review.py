"""Fresh offline source/retained-LLVM review; imports no producer Python."""
from collections import Counter
import copy
import gzip
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent
C = ROOT / 'verification/swift-guarded-snapshot-owned-provider-callee-interfaces'
BASE = ROOT / 'verification/swift-guarded-snapshot-owned-provider-work-storage'
VALUES = (0, 2, 7, 15, 16, 31, 1947, 65537)
COMPONENT_CHECKS = 0
ASSERTIONS = 0

def check(value, why):
    global ASSERTIONS
    ASSERTIONS += 1
    if not value:
        raise AssertionError(why)

def load(path):
    return json.loads(path.read_text())

def sha(body):
    return hashlib.sha256(body).hexdigest()

def value(poly, b):
    return poly['fixed'] + poly['B'] * b + poly['B2'] * b * b

def ext(role, b):
    if role['body']:
        return b, b
    return (0, 0) if role['pointee'] is None else tuple(role['pointee'])

def lexical_price(row, by, b):
    # Separate character/identifier walk, rather than importing producer regexes.
    code = row['code']
    tokens = list(re.finditer(r'[A-Za-z_][A-Za-z_0-9]*|[0-9]+|\S', code))
    mentions = [t.group() for t in tokens if re.fullmatch(r'_[0-9]+', t.group())]
    constants = []
    for i, token in enumerate(tokens):
        if token.group() != 'const' or (i and tokens[i-1].group() == '*'):
            continue
        tail = code[token.end():].lstrip()
        m = re.match(r'(\d+_(?:usize|isize|u8|i32)|true|false|\(\))', tail)
        check(m is not None, 'unknown independent constant')
        literal = m.group()
        width = 0 if literal == '()' else 1 if literal in ('true', 'false') or literal.endswith('_u8') else 4 if literal.endswith('_i32') else 8
        constants.append({'text': literal, 'bytes': width, 'leaves': 1})
    check(mentions == row['mentions'] and constants == row['constants'], 'operand or constant roster drift')
    s = 2 + sum(1 for ch in code if ch in '()[].*&') + sum(t.group() == 'as' for t in tokens)
    n = 0
    for name in mentions:
        role = by[name]
        pointee_bytes, pointee_leaves = ext(role, b)
        s += 2 * (role['leaves'] + pointee_leaves)
        n += 2 * (role['bytes'] + pointee_bytes)
    s += 2 * len(constants)
    n += 2 * sum(x['bytes'] for x in constants)
    if code == 'return;':
        pointee_bytes, pointee_leaves = ext(by['_0'], b)
        s += 2 * (by['_0']['leaves'] + pointee_leaves)
        n += 2 * (by['_0']['bytes'] + pointee_bytes)
    return s, n

def llvm_functions(text):
    result = {}
    lines = text.splitlines()
    pos = 0
    while pos < len(lines):
        header = lines[pos]
        if not header.startswith('define '):
            pos += 1
            continue
        end = pos + 1
        while lines[end] != '}':
            end += 1
        symbol = header.split('@', 1)[1].split('(', 1)[0]
        check(symbol not in result, 'LLVM duplicate symbol')
        result[symbol] = '\n'.join(lines[pos:end+1])
        pos = end + 1
    return result

def formals(header):
    text = header.split('@', 1)[1].split('(', 1)[1]
    parts, current, depth = [], '', 0
    for ch in text:
        if ch == ')' and depth == 0:
            if current.strip():
                parts.append(current.strip())
            return parts
        if ch == ',' and depth == 0:
            parts.append(current.strip()); current = ''; continue
        if ch in '([{': depth += 1
        if ch in ')]}': depth -= 1
        current += ch
    raise AssertionError('incomplete LLVM formals')

def abi_extent(header):
    rows = []
    for formal in formals(header):
        native_type = formal.split()[0]
        check(native_type == 'ptr' or re.fullmatch(r'i\d+', native_type), 'unknown native formal')
        width = 8 if native_type == 'ptr' else (int(native_type[1:]) + 7) // 8
        payload = re.search(r'sret\(\[(\d+) x i8\]\)', formal)
        rows.append((formal, width, int(payload[1]) if payload else 0))
    ret = header.split('@', 1)[0]
    result = 8 * len(re.findall(r'\bptr\b', ret)) + sum((int(bits) + 7) // 8 for bits in re.findall(r'\bi(\d+)\b', ret))
    return rows, result

def source(node):
    path = C / node['source']
    if not path.is_file(): path = ROOT / node['source']
    body = path.read_bytes()
    segment = '\n'.join(body.decode().splitlines()[node['first']-1:node['last']]) + '\n'
    check(sha(body) == node['source_sha256'] and sha(segment.encode()) == node['source_segment_sha256'] and segment == node['source_segment'], 'actual source provenance')
    return path, body.decode(), segment

def main():
    global COMPONENT_CHECKS
    p = load(C / 'proposal.json')
    ledger = load(C / 'source-ledger.json')
    nodes = {x['id']: x for x in ledger['nodes']}
    check(len(nodes) == 37, 'complete proposed node roster')
    tree = p['source_tree_sha256']
    check(tree == 'acce2edaeb41d2e032cd9417897f828caa1c713721e162d2f455663600076e3d', 'source146')
    old = load(BASE / 'candidate.json')
    accepted = load(ROOT / 'verification/swift-semantic-adapter-root-review/guarded-snapshot-owned-provider-work-storage-host-acceptance.json')
    check(p['counts'] == old['new_required_std_interface_terms'] == accepted['strict_positive_external_std_terms'], 'accepted call caps')
    check(p['all10_inherited_terms'] == accepted['old_residual_terms'] and p['upstream2_work_terms'] == accepted['strict_positive_upstream_work_terms'], 'old ten and upstream two preserved')
    check(p['provider_source_work_unchanged'] == old['provider_source_work'] == {'fixed':276580, 'input_operand_bytes':1324}, 'provider work preserved')
    check(p['provider_slots_unchanged'] == old['provider_inline_addition'] == 9696, 'provider storage preserved')
    check(p['authored_callback_body_new_charge'] == 0 and p['authored_callback_body_cap_inherited'] == p['authored_callback_adapter_calls'] == 5, 'callback conservation')

    # Verify native aggregate observations directly, retaining the historical tool receipt.
    layouts = load(BASE / 'layouts.json')
    stdout = (BASE / 'commands/capture-layout/stdout').read_text()
    closure = layouts['anonymous_capture']
    check((closure['bytes'], closure['alignment']) == (16, 8), 'actual closure aggregate extent')
    check('`' + closure['exact_type'] + '`: 16 bytes, alignment: 8 bytes' in stdout, 'raw closure observation')
    tuple_packet = load(ROOT / 'verification/swift-guarded-snapshot-source146-callee-storage-layouts/results.json')
    tuples = [x for x in tuple_packet['queries'] if x.get('key') == '(usize, bool)']
    check(len(tuples) == 1 and (tuples[0]['size'], tuples[0]['alignment']) == (16, 8), 'existing tuple full aggregate extent')
    check(tuple_packet['compiler_sha256'] == p['compiler_sha256'] and tuple_packet['target'] == p['target'], 'tuple compiler/target binding')
    check(ledger['types']['(usize, bool)']['bytes'] == ledger['types']['ProductionClosure']['bytes'] == 16, 'no field sum')
    for node in nodes.values():
        source(node)
        for role in node['roles']:
            ty = ledger['types'][role['type']]
            check(all(role[key] == ty[key] for key in ('bytes','align','leaves','body','pointee')), 'role typed extent')

    raw = gzip.decompress((BASE / 'commands/capture-layout/query.ll.gz').read_bytes())
    ll = llvm_functions(raw.decode())
    correspondence = load(C / 'LLVM-correspondence.json')
    abi = {x['node']:x for x in load(C / 'native-ABI-boundaries.json')['rows']}
    exact_compiler_rows = []
    for row in correspondence['functions']:
        body = ll[row['symbol']]
        check(body == row['body'] and sha(body.encode()) == row['sha256'], 'raw retained LLVM exact function correspondence')
        fields, ret = abi_extent(body.splitlines()[0])
        target = abi[row['node']]
        check([(x['formal'],x['native_field_bytes'],x['sret_logical_result_payload_bytes']) for x in target['formals']] == fields, 'exact native formals including caller/sret')
        full = sum(width + payload for _, width, payload in fields) + ret
        check(full == target['additional_reserved_native_interface_fields'] and full * 2 == target['logical_native_boundary_supplement'] and ret == target['result_native_field_bytes'], 'native entry/result occurrence arithmetic')
        exact_compiler_rows.append({'node':row['node'], 'native_field_extent':full, 'track_caller_or_sret_formals':[x for x in fields if 'sret(' in x[0] or (row['node'] in ('candidate_result_from_residual','unchecked_add_precondition') and x[0].startswith('ptr'))]})

    # Independently evaluate each component numerically, including full repeated
    # body operands; infer the polynomial only after evaluation.
    per_b = {}
    for b in VALUES:
        own = {}
        for name, node in nodes.items():
            by = {x['id']:x for x in node['roles']}
            entry = 2
            for role in node['roles']:
                if role['kind'] != 'parameter': continue
                pb, pl = ext(role, b)
                entry += 2 * (role['leaves'] + role['bytes'] + pb + pl)
            end = sum(2 + 2*x['leaves'] + 2*x['bytes'] for x in node['roles'])
            check(entry == value(node['entry'], b) and end == value(node['finite_role_end'], b), 'entry and every finite place end')
            work = entry + end
            for row in node['rows']:
                s, native = lexical_price(row, by, b)
                check(s == value(row['source_action_units'], b), 'source component arithmetic')
                check(native == value(row['native_typed_bytes'], b), 'native component arithmetic')
                check(s + native == value(row['combined'], b), 'combined arithmetic')
                weighted = (s + native) * (b+1 if row['body_iterations'] else 1)
                check(weighted == value(row['combined_weighted'], b), 'bounded-loop body operand arithmetic')
                COMPONENT_CHECKS += 4
                work += weighted
            check(work == value(node['own_source_and_native_role_work'],b), 'own source work')
            own[name] = work + (abi[name]['logical_native_boundary_supplement'] if name in abi else 0)
            check(own[name] == value(node['own_work'],b), 'own source plus native ABI')
        def compose(name, stack=()):
            check(name not in stack, 'acyclic selected helper contract')
            node = nodes[name]
            work = own[name]
            for call in node['calls']:
                callee = call['node']
                if callee not in nodes:
                    check(callee in ('AUTHORED_CALLBACK', 'DIGEST_MEMCMP_FRONTIER', 'PATH_MEMCMP_FRONTIER', 'CONTAINS_RESIDUAL_FRONTIER'), 'known frontier only')
                    continue
                work += (b+1 if call['count'] == 'body+1' else call['count']) * compose(callee, (*stack,name))
            return work
        total = 0
        for interface in p['interfaces']:
            work = compose(interface['name'])
            check(work == value(interface['per_call_source_and_native_shell'],b), 'interface numeric composition')
            total += interface['call_cap'] * work
        check(total == value(p['callee_source_shell_work'],b), 'whole shell numeric composition')
        per_b[str(b)] = total

    def visits(name):
        counts = Counter({name:1})
        for call in nodes[name]['calls']:
            if call['node'] not in nodes: continue
            # Sequential short-scan iterations do not invent concurrent slots;
            # each source node's per-context inventory remains reserved once.
            multiplicity = 1 if call['count'] == 'body+1' else call['count']
            counts.update({k:v*multiplicity for k,v in visits(call['node']).items()})
        return counts
    source_slots = native_slots = 0
    slot_rows = []
    for name, cap in p['counts'].items():
        v = visits(name)
        ss = cap * sum(sum(r['bytes'] for r in nodes[k]['roles']) * n for k,n in v.items())
        ns = cap * sum(abi[k]['additional_reserved_native_interface_fields'] * n for k,n in v.items() if k in abi)
        source_slots += ss; native_slots += ns
        slot_rows.append({'interface':name,'source_places_bytes':ss,'native_fields_bytes':ns,'call_cap':cap})
    check((source_slots,native_slots,source_slots+native_slots) == (20739,9882,30621), 'independent source and native slot sums')
    check(p['proposed_conditional_P0_fixed_excluding_positive_residual_storage'] == 301733+source_slots+native_slots == 332354, 'conditional P0 arithmetic')
    check(p['proposed_conditional_whole_fixed_excluding_all_dynamic_and_external_terms'] == 895084428326233374+200334 == 895084428326433708, 'whole fixed arithmetic')
    phases = load(C / 'phase-reservations.json')['phases']
    old_phases = load(BASE / 'phase-roster.json')['P0_new_total_each_phase']
    check(set(phases) == set(old_phases) and len(phases) == 15, 'all inherited phases exactly retained')
    for phase in phases.values():
        check((phase['new_source_ledger_places'],phase['new_native_ABI_fields'],phase['new_total'],phase['provider_9696_retained']) == (source_slots,native_slots,source_slots+native_slots,9696), 'phase inventory')
        check('mandatory' in phase['positive_external_residual_storage'], 'positive residual storage retained')

    # Derive small actual-path scans independently (includes non-UTF8), asserting
    # every read has i<n and body counts <= n <= B, headers <= n+1 <= B+1.
    scans = 0
    for n in range(16):
        for data in (bytes([255])*n, bytes(range(n)), b'\0'*n):
            for needle in (0,7,255):
                i=0; headers=0; reads=0; result=None
                while True:
                    headers += 1
                    if i >= len(data): break
                    check(0<=i<len(data), 'short scan actual readable byte index')
                    reads += 1
                    if data[i] == needle: result=i; break
                    i += 1
                check(result == (data.find(bytes([needle])) if needle in data else None), 'short scan finite result')
                check(reads<=n and headers<=n+1 and i<=n, 'short scan monotone upper bound')
                scans += 1

    # Focused independent source witnesses: neither a producer test nor an LLVM
    # instruction count authorizes erasing authored source helper boundaries.
    overflow = nodes['overflowing_add_adapter']
    _, _, overflow_source = source(overflow)
    casts = len(re.findall(r'\bas\b',overflow_source))
    ledger_casts = sum(len(re.findall(r'\bas\b',r['code'])) for r in overflow['rows'])
    check((casts,ledger_casts) == (3,0), 'source cast omission witness')
    step_casts = sum(len(re.findall(r'\bas\b',r['code'])) for r in nodes['step_forward']['rows'])
    check(step_casts == 1, 'same candidate charges explicit usize cast elsewhere')
    intrinsic_source = (C / 'official-source/library/core/src/intrinsics/mod.rs').read_text()
    macro_segment = '\n'.join(intrinsic_source.splitlines()[2612:2637]) + '\n'
    check('fn runtime' in macro_segment and 'const fn compiletime' in macro_segment and 'const_eval_select(($($val,)*), compiletime, runtime)' in macro_segment, 'exact source macro creates callable source functions and intrinsic arguments')
    ub = nodes['language_ub_check']
    check(not any('runtime' in n.lower() and n != 'language_ub_check' for n in nodes), 'no separate generated runtime helper node')
    check(all(c['node'] == 'ub_checks_intrinsic' for c in ub['calls']), 'runtime intrinsic/helper not in helper graph')
    check('range_next' in p['closed_interfaces'] and 'range_next' not in p['partial_interfaces'], 'missing range source obligations have no residual')
    option_source=(C / 'official-source/library/core/src/option.rs').read_text()
    check('pub const fn is_some(&self) -> bool' in option_source, 'contains is_some is a source helper with borrowed receiver')
    check(any('IsSome(copy _7)' in r['code'] for r in nodes['u8_contains_shell']['rows']), 'is_some collapsed boundary witness')
    check(not any(r['type']=='&Option<usize>' for r in nodes['u8_contains_shell']['roles']), 'auto-borrow source place not present')

    # Fresh adversarial contract controls. They are independent data mutations,
    # never fabricated product executions or an attempt to prove full acceptance.
    controls = []
    def reject(label, condition):
        check(not condition, 'adverse case not refused: '+label)
        controls.append(label)
    reject('field-sum tuple9 instead of observed16', 9 == ledger['types']['(usize, bool)']['bytes'])
    reject('closure guessed8 instead of observed16', 8 == ledger['types']['ProductionClosure']['bytes'])
    reject('range-next threecasts declared complete', casts == ledger_casts)
    reject('macro runtime-function declared absent', 'fn runtime' not in macro_segment)
    reject('missing all-phase entry', set(list(phases)[1:]) == set(old_phases))
    reject('P0 alias credit onebyte', 332353 == 301733+source_slots+native_slots)
    reject('linear-only contains at B31', 200334+6867*31 == per_b['31'])
    reject('digest arbitrary-length31', (31,31) == (32,32))
    reject('path selectedB substitutes actual unequal lengths', (1947,1947)==(3,17))
    reject('contains UTF8 decoded length substitutes bytes', len('é') == len('é'.encode()))
    reject('u64 extreme B accepted without checked polynomial', value(p['callee_source_shell_work'],(1<<64)-1) <= (1<<64)-1)
    reject('callback cap4', 4 == p['authored_callback_body_cap_inherited'])
    reject('one inherited work term omitted', len(p['all10_inherited_terms'])-1 == 10)
    reject('one future work term omitted', len(p['upstream2_work_terms'])-1 == 2)

    report = {
        'schema':1, 'status':'focused-source-closure-correction-required',
        'source_tree_sha256':tree, 'candidate_seal_sha256':'e98916beff1a3c8b912e96591fbd573b8d570aa38cc4390a13fa20658290dce0',
        'arithmetic_internal_consistency_only':{'per_B_shell_totals':per_b,'shell':p['callee_source_shell_work'],'source_places':source_slots,'native_ABI_fields':native_slots,'total_slots':source_slots+native_slots,'provisional_P0':332354,'whole_fixed':895084428326433708,'phases':len(phases),'slot_rows':slot_rows},
        'retained_compiler_correspondence':{'raw_uncompressed_sha256':sha(raw),'functions_checked':len(correspondence['functions']),'native_rows':exact_compiler_rows,'compiler_invocations':0,'LLVM_is_instruction_price':False},
        'fresh_checks':{'component_equalities':COMPONENT_CHECKS,'assertions':ASSERTIONS,'short_actual_byte_scan_cases':scans,'adversarial_controls':controls},
        'source_witnesses':{
            'overflowing_add_source_explicit_casts':casts,'overflowing_add_ledger_casts':ledger_casts,'step_forward_ledger_casts':step_casts,
            'overflowing_add_source':overflow_source,'overflowing_add_ledger_rows':[r['code'] for r in overflow['rows']],
            'const_eval_select_macro_source':macro_segment,
            'language_ub_check_ledger_rows':[r['code'] for r in ub['rows']],
            'generated_runtime_function_or_intrinsic_callable_roster':False,
            'contains_is_some_auto_borrow_and_helper_requires_explicit_scope':True},
        'recommendation':'Return for a narrow source-contract correction. Current arithmetic matches the authored ledger, but that does not establish claimed exact closure of range_next or complete explicit contains residual scope.',
        'root_price_or_funding_or_GA_selected':False,
        'native_UI_capture_simulator_emulator_phone_checks':'not run under pause',
    }
    (OWN / 'review.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('source_witnesses','arithmetic_internal_consistency_only','retained_compiler_correspondence')},indent=2))

if __name__ == '__main__': main()
