#!/usr/bin/env python3
"""Independent exact-source whole-work audit. Imports no producer code."""
import collections, copy, functools, gzip, hashlib, json, random, re
from pathlib import Path

D = Path(__file__).resolve().parent
R = D.parents[1]
V = R / 'verification'
C = V / 'swift-guarded-snapshot-whole-host-work-composition'
SOURCE = '690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185'
HOST = '027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2'
SEAL = '95c1a3087b36996dc06e8411f97e3ebce2610120f9ac742326824a52ab9c63ca'
RELEASE = 'e7e5f687469e19ce591c2df0f8f44591863bc93b07d130e9e3d235e771b6f555'
UNIT = 'abstract logical source/typed aggregate/destructor interface occurrences plus requested native-byte allowances; excludes CPU/private implementations/physical allocation/stack/RSS/time'
PHASES = ('P1_setup', 'P1_loader', 'P2_arguments', 'P3_before_store',
          'P4_selected_route', 'P5_payload_teardown')
U64 = 2**64 - 1
checks = []
adverse = []
custody = {}

def digest(raw): return hashlib.sha256(raw).hexdigest()
def canon(x): return json.dumps(x, sort_keys=True, separators=(',', ':')).encode()
def require(ok, why):
    if not ok: raise AssertionError(why)
    checks.append(why)
def read(path):
    raw = path.read_bytes()
    custody[str(path.relative_to(R))] = {'bytes': len(raw), 'sha256': digest(raw)}
    return raw
def load(path): return json.loads(read(path))
def dump(name, x): (D/name).write_text(json.dumps(x, indent=2, sort_keys=True) + '\n')
def safe(path):
    p = Path(path)
    require(not p.is_absolute() and '..' not in p.parts, 'safe-member:' + str(p))
    return p
def bound(value):
    require(type(value) is int and 0 <= value <= U64, 'exact-u64')
    return value
def refuses(name, callback):
    try: callback()
    except (AssertionError, ValueError, KeyError, TypeError):
        adverse.append(name)
        return
    raise AssertionError('adverse-input-accepted:' + name)
def verify_packet(path, expected, count=None, size=None):
    raw = read(path/'seal.json')
    require(digest(raw) == expected, 'seal:' + path.name)
    seal = json.loads(raw)
    if count is not None: require(len(seal['members']) == count, 'member-count:' + path.name)
    paths = set()
    for member in seal['members']:
        p = safe(member['path'])
        require(str(p) not in paths, 'no-duplicate-member:' + str(p))
        paths.add(str(p))
        data = read(path/p)
        require(len(data) == member['bytes'] and digest(data) == member['sha256'], 'member:' + path.name+'/'+str(p))
    if size is not None: require(sum(m['bytes'] for m in seal['members']) == size, 'packet-bytes:' + path.name)
    return seal

def polynomial(fixed=0, **kwargs):
    return collections.Counter({'#fixed': bound(fixed), **kwargs})
def scaled_sum(items):
    answer = collections.Counter()
    for coefficient, row in items:
        bound(coefficient)
        for key, value in row.items(): answer[key] += coefficient * bound(value)
    for value in answer.values(): bound(value)
    return answer
def expression(row):
    return {'fixed': row.get('#fixed', 0),
            'terms': {k:v for k,v in sorted(row.items()) if k != '#fixed' and v}}
def parse_expression(row):
    require(set(row) == {'fixed','terms'}, 'expression-schema')
    return collections.Counter({'#fixed': bound(row['fixed']),
                               **{k:bound(v) for k,v in row['terms'].items()}})

def resource_price(row, cuts):
    # The inherited unit counts declared logical aggregate/field nodes; Vec is
    # one frontier. It is deliberately unrelated to reconstructed drop glue.
    value = row['structural_occurrence_allowance'] * (1 + row['inline_bytes'])
    for kind, count in row['resource_frontiers'].items():
        cut = cuts[kind]
        value += count * (cut['interface_work'] + cut['native_resource_backing'])
        if kind in row.get('dynamic_resource_elements', {}):
            child = row['dynamic_resource_elements'][kind]
            require(set(child['resource_frontiers']) == {'Vec<Type>','Vec<DecodedInstruction>','Vec<u32>'}, 'all-three-SwiftSlot-cuts')
            require(child['inline_bytes'] == cut['element_inline_bytes'] == 136 and cut['max_live_elements'] == 64, 'qualified-SwiftSlot-size-and-count')
            value += count * cut['max_live_elements'] * resource_price(child, cut['element_cuts'])
    return bound(value)

def exact_interface(interface, expected_parts, expected_p0, expected_symbols):
    require(interface['schema'] == 1 and interface['status'] == 'source146-whole-host-conditional-logical-work-interface', 'interface-schema-status')
    require(interface['source_tree_sha256'] == SOURCE and interface['host_tree_sha256'] == HOST, 'interface-exact-trees')
    require(interface['unit'] == UNIT, 'interface-unit-exact')
    require(interface['operational_grant'] is False and interface['product451814442_aggregate_credit'] == 0, 'interface-no-authority-or-counter-credit')
    require(interface['native_runtime'] == 'paused', 'interface-paused-native')
    require(tuple(interface['child']) == PHASES, 'interface-six-ordered-components')
    require(set(interface['symbols']) == set(expected_symbols), 'interface-exact-symbol-domain')
    for key, value in expected_symbols.items():
        require(interface['symbols'][key] == value, 'interface-exact-symbol-scope:'+key)
    for phase in PHASES:
        require(parse_expression(interface['child'][phase]) == expected_parts[phase], 'component-exact:' + phase)
    require(parse_expression(interface['P0']) == expected_p0, 'P0-exact')
    whole = scaled_sum([(1,expected_p0)] + [(1,expected_parts[p]) for p in PHASES])
    require(parse_expression(interface['whole_host']) == whole, 'whole-exact-composition')
    referenced = {k for row in [whole] for k,v in row.items() if k != '#fixed' and v}
    require(referenced == set(expected_symbols), 'no-unused-or-implicit-symbol')
    return whole

def main():
    release_path = V/'swift-semantic-adapter-root-review/guarded-snapshot-whole-host-work-frozen-release.json'
    raw = read(release_path)
    require(digest(raw) == RELEASE, 'root-release-digest')
    release = json.loads(raw)
    require(release['seal_sha256'] == SEAL and release['source_tree_sha256'] == SOURCE, 'root-release-trees')
    verify_packet(C, SEAL, 50, 820408)
    # Pin the producer's complete input set; independently traverse root receipts
    # as well, rather than trusting a producer success flag or counts.
    input_files = load(C/'input-custody.json')['files']
    for name, record in input_files.items():
        raw = read(R/safe(name))
        require(len(raw)==record['bytes'] and digest(raw)==record['sha256'], 'producer-input:'+name)
    roots = {}
    for name in ['parent-work-source146','loader-work-source146','child-entry-cost','leaf-shell-cost',
                 'payload-destruction','leaf-callee-cost','resource-cost']:
        path = V/'swift-semantic-adapter-root-review'/('guarded-snapshot-'+name+'-host-acceptance.json')
        require(str(path.relative_to(R)) in input_files, 'root-record-pinned:'+name)
        root = load(path); roots[name] = root
        require(root['source_tree_sha256']==SOURCE, 'root-source:'+name)
        for role in ['producer','independent']:
            record = root[role]
            verify_packet(R/safe(record['path']), record['seal_sha256'], record.get('members',record.get('members_verified')))
    source_manifest = load(V/'swift-guarded-snapshot-host-composition/source-manifest.json')
    require(len(source_manifest['members'])==146 and digest(canon(source_manifest['members']))==SOURCE, 'source146-manifest')
    source = {}
    for member in source_manifest['members']:
        relative = safe(member['path'])
        path = V/'swift-guarded-snapshot-host-composition/overlay/vm'/relative
        if not path.is_file(): path = V/'swift-guarded-snapshot-funding-implementation/source/vm'/relative
        raw = read(path)
        require(len(raw)==member['bytes'] and digest(raw)==member['sha256'], 'source146-member:'+str(relative))
        source[str(relative)] = raw.decode()
    host_manifest = load(V/'swift-guarded-snapshot-host-composition/host-support-manifest.json')
    require(len(host_manifest['members'])==11 and digest(canon(host_manifest['members']))==HOST, 'host11-manifest')
    for member in host_manifest['members']:
        raw = read(V/'swift-real-profile-loader-binding/host'/safe(member['path']))
        require(len(raw)==member['bytes'] and digest(raw)==member['sha256'], 'host11-member:'+member['path'])

    base = V/'swift-guarded-snapshot-resource-cost'
    rows = load(base/'rows.json') + load(base/'internal-rows.json')['rows']
    cuts = load(base/'resource-cuts.json')
    prices = {row['type'].replace(' ',''):resource_price(row,cuts) for row in rows}
    require(len(rows)==33, 'resource33rows')
    components = load(base/'components.json')
    per_visit_types = roots['payload-destruction']['per_visit_domain']
    per_visit = max(prices[k.replace(' ','')] for k in per_visit_types)
    require(len(per_visit_types)==7 and per_visit==components['during_entry_per_visit']==1210256815, 'complete-max7-before53')
    require(prices['OwnedFixtureOutcomeV1']==45196204, 'returned-owner-price')
    decoded_text = source['src/experimental/cache/mod.rs']
    start = decoded_text.index('struct DecodedFunction {')
    end = decoded_text.index('\n}',start)+2
    declaration = decoded_text[start:end]
    fields = [line.strip().split(':',1)[1].strip().rstrip(',') for line in declaration.splitlines()[1:-1] if ':' in line]
    require(fields==['u32','u32','usize','Vec<Type>','Vec<DecodedInstruction>','Vec<u32>','usize'], 'DecodedFunction-source-seven-fields')
    require(len(fields)+1==8, 'DecodedFunction-logical-eight-nodes')
    require(digest(declaration.encode())=='4c45b80993496ed1be8c272263ed9f8b93617ccdcb22d1a203bf9738f85e2628', 'DecodedFunction-declaration-digest')
    archive = read(V/'swift-guarded-snapshot-host-composition-independent/commands/exact146-metadata-mir/stdout.gz')
    require(digest(archive)=='1ddc23c6274a1c4f148e9d4a389aa0aeaa070384929280de044f4889a49ec9ec', 'DecodedFunction-layout-archive')
    full = gzip.decompress(archive)
    require(digest(full)=='6c924c8088173db78afb1f648b284df7d8d139b3389bd090a9552df4130cfe7a', 'DecodedFunction-layout-raw')
    layout = b'print-type-size type: `experimental::cache::DecodedFunction`: 96 bytes, alignment: 8 bytes'
    require(full.splitlines().count(layout)==1, 'DecodedFunction-observed96-align8')
    del full
    inventory = load(V/'swift-guarded-snapshot-payload-destruction-cost/inventory.json')
    require(all(item['type']!='DecodedFunction' for item in inventory['source_drop_implementations_including_test_only']), 'DecodedFunction-no-authored-Drop')
    decoded = {'type':'DecodedFunction','inline_bytes':96,'structural_occurrence_allowance':8,
               'resource_frontiers':{'Vec<Type>':1,'Vec<DecodedInstruction>':1,'Vec<u32>':1},'dynamic_resource_elements':{}}
    prices['DecodedFunction'] = resource_price(decoded,cuts)
    require(prices['DecodedFunction']==231526438, 'DecodedFunction-new-price231526438')
    require(load(C/'additive-decoded-function-row.json')['row']==decoded, 'DecodedFunction-candidate-row-exact')

    graph = load(V/'swift-guarded-snapshot-leaf-callee-cost/callee-ledger.json')
    native = load(V/'swift-guarded-snapshot-leaf-callee-cost-independent/native-binding-receipt.json')
    observed_sizes = {row['key']:row['size'] for row in native['observations']}
    bound_callee = load(V/'swift-guarded-snapshot-leaf-callee-cost-independent/bound-cost-interface.json')
    amendment = load(V/'swift-guarded-snapshot-leaf-callee-cost-independent/capture-roster-correction.json')
    require((amendment['actual_capture_count'],amendment['original_closure_size_observed'],amendment['original_closure_alignment_observed'])==(8,64,8),'mandatory-eight-capture64/8')
    @functools.lru_cache(None)
    def expand(key, active=()):
        require(key not in active, 'acyclic-callee:'+key)
        row = graph['nodes'][key]
        answer = collections.Counter({'#fixed': row['own']+row.get('known_native',0)+sum(observed_sizes[k]*n for k,n in row.get('missing_native',{}).items())})
        answer.update(row.get('payload',{}))
        answer.update({'unsized::'+k:n for k,n in row.get('unsized',{}).items()})
        for callee,count in row['calls'].items():
            answer = scaled_sum([(1,answer),(count,expand(callee,active+(key,)))])
        return answer
    imports = set(); callee_prices = {}; adapter_rows = []; primitive_reviews = []
    roster = load(C/'private-export-allowance-roster.json')
    proposed_roster = {row['export']:row for row in roster['exports']}
    def primitive_tree(key, active=()):
        require(key not in active, 'acyclic-private-roster:'+key)
        row=graph['nodes'][key]; primitives=collections.Counter(row.get('primitive',{})); named=[]
        if row['kind'].startswith('accepted-'): named.append((key,row['own'],row.get('binding',{})))
        for child,count in row['calls'].items():
            sub,ns=primitive_tree(child,active+(key,))
            primitives.update({k:v*count for k,v in sub.items()}); named.extend(ns)
        return primitives,named
    for name,key in graph['exports'].items():
        raw = expand(key); imported = bound_callee['exports'][name]
        payload={k:v for k,v in raw.items() if k.startswith('payload::')}
        unsized={k[9:]:v for k,v in raw.items() if k.startswith('unsized::')}
        require(raw['#fixed']==imported['fixed'] and payload==imported['payload'] and unsized==imported['unsized'] and imported['native']=={},'exact-export-transitive:'+name)
        imports.update(payload)
        value = raw['#fixed'] + sum(n*prices[k[9:].replace(' ','')] for k,n in payload.items())
        # The only unsized non-string interface is the actual field-to-slice
        # frontier in snapshot_pair_v1, not all slices or every array in source.
        array_count=unsized.get('[Option<ReservationTicket>]',0)
        if array_count:
            require(name=='callee::accounted::AccountedWasi::snapshot_pair_v1' and array_count==8,'one-qualified-array-frontier')
            value += 2*array_count*(4*4+4*24)
        terms={imported['required_private_primitive_cut']:1}
        if unsized.get('str',0): terms['L_str']=2*unsized['str']
        callee_prices[name]=polynomial(value,**terms)
        primitive,named=primitive_tree(key)
        proposal=proposed_roster[name]
        require(proposal['primitive_callsite_occurrences']==dict(primitive),'private-roster-exact:'+name)
        require(proposal['mandatory_symbol_preserved'] is True and proposal['closed_by_this_packet'] is False and proposal['symbol_value_selected'] is False,'private-roster-no-selection:'+name)
        is_adapter=graph['nodes'][key]['kind']=='closed-standard-logical-adapter'
        if is_adapter:
            require(raw=={'#fixed':1} and not primitive and not named,'direct-adapter-one-logical-event:'+name)
            adapter_rows.append({'export':name,'symbol':imported['required_private_primitive_cut'],
                                 'fixed_event_already_charged':1,'native_payload_unsized_or_callback_edges':0})
        primitive_reviews.append({'export':name,'kind':graph['nodes'][key]['kind'],
            'primitive_callsite_occurrences':dict(primitive),
            'accepted_source_row_nodes':sorted({entry[0] for entry in named}),
            'payload':payload,'unsized':unsized,'source_native_fixed':raw['#fixed'],
            'symbol':imported['required_private_primitive_cut'],
            'all_inherited_symbols_remain_required':True})
    require(len(imports)==19 and len(callee_prices)==21 and len(adapter_rows)==9,'19imports21exports9adapters')
    ctor=bound_callee['exports']['callee::construct_snapshot_in_scope_v1']['payload']
    require(len(ctor)==12 and ctor['payload::AdoptedProof']==6,'constructor-real12types6proofs')
    subset_roster=load(base/'constructor-roster-composition.json')['multipliers_imported_from_frozen_caller_roster']
    subset=sum(prices[k]*n for k,n in subset_roster.items())
    exact_ctor=sum(prices[k[9:].replace(' ','')]*n for k,n in ctor.items())
    require(subset==134288951629 and exact_ctor==subset+2*prices['AdoptedProof']==136709543157,'constructor-extra-two-real-destructors')
    require(bound_callee['exports']['core_before_fixed_store']['fixed']==900979 and bound_callee['exports']['core_fixed_store_and_after']['fixed']==874193,'before900979-after874193-separate')
    phase_binding=graph['core_phase_binding'];store=phase_binding['counter_store']
    before_ops=graph['nodes']['core_callback_before']['operations'];after_ops=graph['nodes']['core_fixed_store_and_after']['operations']
    require(not any(op['line']==store['line'] for op in before_ops) and sum(op['line']==store['line'] for op in after_ops)==1,'store-only-in-after-callback')
    require(any(op['code']==store['code'] for op in after_ops),'exact-product-store-operation')
    require(set(phase_binding['pre_callback_blocks']) & set(phase_binding['post_callback_blocks'])==set(phase_binding['overlap_blocks']),'conservative-shared-exit-overlap')

    shell=load(V/'swift-guarded-snapshot-leaf-shell-cost/operation-ledger.json')
    shell_native=load(V/'swift-guarded-snapshot-leaf-shell-cost/native-occurrence-interface.json')
    sizes=dict(shell_native['known_actual146_layouts_used'])
    sizes.update({row['key']:row['size'] for row in load(V/'swift-guarded-snapshot-leaf-shell-cost-independent/layout-review-results.json')['queries']})
    parts={phase:polynomial() for phase in PHASES};cuts_seen=collections.Counter();edge_audit=[]
    shell_fixed=shell_strings=0
    for function in shell['functions']:
        name=function['function'];phase='P4_selected_route' if name in ['construct','outer','finish'] else 'P3_before_store'
        binding=function['binding'];source_text=source[binding['path']]
        source_start=source_text.index(binding['signature'])
        brace=source_text.index('{',source_start+len(binding['signature']))
        cursor=brace+1;depth=1
        while depth:
            if source_text[cursor]=='{':depth+=1
            elif source_text[cursor]=='}':depth-=1
            cursor+=1
        actual_body=source_text[source_start:cursor].encode()
        require(len(actual_body)==binding['source_function_bytes'] and digest(actual_body)==binding['source_function_sha256'],'exact-eight-source-frame:'+name)
        fixed=0;strings=0
        for block in function['blocks'].values():
            for op in block['lines']:
                fixed += op['source_action_units']+op['known_constant_bytes']+sum(sizes[k]*n for k,n in op['native_type_coefficients'].items())
                require(set(op['unsized_coefficients'])<={'str'},'shell-only-unsized-str')
                strings += 2*op['unsized_coefficients'].get('str',0)
        shell_fixed+=fixed;shell_strings+=strings
        parts[phase]=scaled_sum([(1,parts[phase]),(1,polynomial(fixed,**({'L_str':strings} if strings else {})))])
        for site in function['callee_and_drop_sites']:
            if site['kind']=='included-source-body': continue
            sites=[('core_before_fixed_store','P3_before_store'),('core_fixed_store_and_after','P4_selected_route')] if site['kind']=='required-core-split' else [(site['key'],phase)]
            for cut,where in sites:
                cuts_seen[cut]+=1
                price=callee_prices[cut] if cut in callee_prices else polynomial(prices[cut[14:].replace(' ','')])
                parts[where]=scaled_sum([(1,parts[where]),(1,price)])
                edge_audit.append({'key':cut,'phase':where,'owner':name,'MIR_line':site['MIR_body_line'],'work':expression(price)})
    for cut in ['private_std_compiler_lowering_and_requested_backing_allowance','retained_dynamic_resource_backing_and_native_transfer_allowance']:
        cuts_seen[cut]=1;parts['P3_before_store'][cut]+=1
    required=load(V/'swift-guarded-snapshot-leaf-shell-cost/cost-interface.json')['required_nonzero_callee_drop_and_backing_cuts']
    require(dict(cuts_seen)==required and len(required)==33,'33-exact-cut-coefficients')
    require((shell_fixed,shell_strings)==(4236953,4376),'all8-source-frames4236953+4376L')
    actual_edges=load(C/'actual-edges.json')['edges']
    require([{k:e[k] for k in ['key','phase','owner','MIR_line','work']} for e in actual_edges]==edge_audit,'all-actual-edge-attributions-exact')

    entry=load(V/'swift-guarded-snapshot-child-entry-cost/ledger.json')
    funcs=entry['functions'];carrier=funcs['run_prepaid_fixture_v1']
    leaf_counts={(row['function'],row['local']):row['source_leaves'] for row in entry['actual_native_layouts_as_data']}
    parameters=re.findall(r'(_\d+):',carrier['head'].split(' -> ',1)[0])
    prologue=2+2*sum(leaf_counts[('run_prepaid_fixture_v1',p)] for p in parameters)
    partition=[];carrier_counts=collections.Counter(P2_arguments=prologue)
    for statement in carrier['statements']:
        weight=2+sum(statement.count(c) for c in '.*[]')+2*sum(leaf_counts[('run_prepaid_fixture_v1',p)] for p in re.findall(r'\b_\d+\b',statement))
        phase='P5_payload_teardown' if statement.startswith(('drop(','return;')) or 'OwnedFixtureOutcomeV1::' in statement else 'P2_arguments'
        carrier_counts[phase]+=weight;partition.append({'statement':statement,'phase':phase,'source_actions':weight})
    require(sum(carrier_counts.values())==92906 and len(partition)==len(carrier['statements']),'all-carrier-events-once92906')
    setup_source=funcs['setup_files_once_v1']['repeat']*funcs['setup_files_once_v1']['local_actions']
    helpers=sum(funcs[k]['local_actions'] for k in ['copy_claims_v1','invoke_loaded_leaf_once_v1','cancellation_default','cancellation_clone'])
    require(setup_source+sum(carrier_counts.values())+helpers==119922,'entry119922-exact')
    visits=collections.Counter()
    for site in entry['drop_sites']: visits['setup' if site['function']=='setup_files_once_v1' else 'caller']+=site['repeat']
    require(visits=={'setup':42,'caller':11},'42setup11caller53visits')
    parts['P1_setup']=polynomial(setup_source+visits['setup']*per_visit,
                                  **{'native_open_request_'+str(i):1 for i in range(5)},native_error_request=1)
    parts['P2_arguments']=polynomial(carrier_counts['P2_arguments']+helpers+24)
    parts['P5_payload_teardown']=polynomial(carrier_counts['P5_payload_teardown']+visits['caller']*per_visit+prices['OwnedFixtureOutcomeV1'])
    require(load(C/'entry-partition.json')['statement_partition']==partition,'entry-exact-partition')
    wasi=source['src/experimental_wasi/accounted.rs']
    pair=wasi[wasi.index('    pub(crate) fn snapshot_pair_v1'):]
    require('buffers: [Option<ReservationTicket>; 4]' in wasi and 'for ticket in &self.buffers' in pair and 'self.buffers.iter().zip(capacities)' in pair,'actual-array4-field-and-both-sites')
    require(sizes['Option<ReservationTicket>']==24,'OptionTicket24-observed')
    scalar=load(V/'swift-guarded-snapshot-leaf-shell-cost/scalar-shapes.json')['definitions']['ReservationTicket']
    require(scalar['fields']==['u64','SwiftReservationCategory','usize'] and scalar['scalar_leaves']==3,'Ticket3-plus-Option-tag4')

    loader=load(V/'swift-guarded-snapshot-loader-work-source146/mir-ledger.json')
    geometry=load(V/'swift-guarded-snapshot-loader-work-source146/cap-geometry.json')
    maxfile=max(geometry[k] for k in ['source','executable','build','session'])
    env={'source':geometry['source'],'validator_source':geometry['validator_source'],'maximum_file':maxfile,
         'allocation_cap':max(geometry['metadata'],geometry['scratch']),'retained_visits':(maxfile+4095)//4096+1,'read_buffer':4096}
    def node_price(key, mode, active=()):
        require(key not in active,'acyclic-loader:'+key)
        if mode=='wrapper' and key==loader['roots']['validator']: return 0
        row=loader['nodes'][key]
        require(row['local_actions']==2+sum(row['parts'].values()),'loader-explicit-local:'+key)
        base=row['local_actions']+sum(event['count']*(env[event['extent']] if isinstance(event['extent'],str) else event['extent']) for event in row['native'])
        base+=sum(call['multiplicity']*node_price(call['callee'],mode,active+(key,)) for call in row['calls'])
        repeat=row['repeat'] if mode=='wrapper' else row.get('validator_fixed_repeat',1)
        return bound(base*(env[repeat] if isinstance(repeat,str) else repeat))
    wrapper=node_price(loader['roots']['loader'],'wrapper');coefficient=node_price(loader['roots']['validator'],'validator')
    loader_price=bound(wrapper+(geometry['credits']+1)*coefficient)
    require((wrapper,coefficient,geometry['credits'],loader_price)==(97394558768720,1748020339,512000000,895083809874789059),'independent-loader-cap-expansion')
    parts['P1_loader']=polynomial(loader_price)
    p0=polynomial(2628088,P0_inspections=194231,P0_usage_reads=1039,P0_root_route=1,P0_fixture_binding=1,P0_dynamic_backing=1)
    interface=load(C/'work-interface.json')
    # Independently declare the unresolved scope from accepted component cuts;
    # do not trust a self-consistent caller's replacement symbol definitions.
    expected_symbols={}
    def define(name, unit, reason, positive=True):
        expected_symbols[name]={'name':name,'unit':unit,'reason':reason,'positive':positive}
    define('L_str','source scalar leaves and native UTF-8 bytes per str occurrence','Finite actual provenance for every reachable str must be reviewed; static lifetime alone is insufficient.')
    for row in bound_callee['exports'].values():
        define(row['required_private_primitive_cut'],'logical interface allowance','Required inherited callee private boundary; no positive number proves applicability.')
    for key in ['private_std_compiler_lowering_and_requested_backing_allowance','retained_dynamic_resource_backing_and_native_transfer_allowance']:
        define(key,'logical interface/requested backing allowance','Inherited whole-leaf boundary spans P3/P4; paid once in earliest leaf envelope.')
    for index in range(5):
        define('native_open_request_'+str(index),'native request byte allowance','Actual finite path, conversion/native interface and immutable path binding required.')
    define('native_error_request','native request byte allowance','Original owned-File error request boundary remains unqualified.')
    define('P0_inspections','finite exact source occurrence count','I cannot default to zero; selected actual root/caller must establish count.',False)
    define('P0_usage_reads','finite exact source occurrence count','U cannot default to zero; selected actual root/caller must establish count.',False)
    for name,reason in [('P0_root_route','Unselected actual trusted root constructor and final quote/caller path.'),('P0_fixture_binding','Immutable paths/claims/budgets/build/session/executable preparation and review binding.'),('P0_dynamic_backing','Parent work to acquire/retain/destroy backing and late finalization not covered by account surface.')]:
        define(name,'logical source/interface work',reason)
    require(len(expected_symbols)==35 and interface['symbols']['P0_inspections']['positive'] is False and interface['symbols']['P0_usage_reads']['positive'] is False,'35symbols-no-default-IU')
    whole=exact_interface(interface,parts,p0,expected_symbols)
    require(whole['#fixed']==895084428322997895 and whole['L_str']==67424,'independent-whole-constant-and-Lcoefficient')
    # Semantic source order accompanies the numerical partition. These excerpts
    # are bound to source146 above; neither a token check nor this model is OTA
    # authority. Private source/native operation proofs remain separate imports.
    entry_source=source['src/experimental_swift_reactor/cache/initial_profile_v1.rs']
    require(entry_source.index('let quote = host_account_v1::selected_whole_quote_v1()?;') < entry_source.index('let reservation = account.reserve_whole_v1(quote)?;') < entry_source.index('Ok(reservation.dispatch_v1(|| run_prepaid_fixture_v1(fixture)))'),'source-quote-commit-before-dispatch')
    account=source['src/experimental_swift_reactor/cache/initial_profile_v1/host_account_v1.rs']
    production=account.split('#[cfg(test)]',1)[0]
    require('Err(RefusalV1::WholeQuotePending)' in production and 'Err(RefusalV1::RootPolicyPending)' in production,'source-selected-producers-refuse')
    require('fn dispatch_v1<T>(self, action: impl FnOnce() -> T)' in production,'source-consuming-FnOnce-ticket')
    require(production.index('self.usage.set(after);') < production.index('let owned = action();'),'source-commit-before-action')
    require('work: before' not in production[production.index('pub(super) fn release_destroyed_v1'):],'source-late-release-no-work-refund')
    require('if let Some(owned) = self.owned.take() { drop(owned); }' in production and 'This function itself does NOT release storage.' in production,'source-owner-destroy-before-P0-token')

    # Independent adverse controls preserve the exact derived expectation, not
    # a self-consistent mutant's own totals or arbitrary positive choices.
    for phase in PHASES:
        changed=copy.deepcopy(interface);changed['child'][phase]['fixed']+=1
        changed['whole_host']['fixed']+=1
        refuses('self-consistent-underived-phase:'+phase,lambda x=changed:exact_interface(x,parts,p0,expected_symbols))
    for field,bad in [('unit','CPU instructions'),('source_tree_sha256','0'*64),('host_tree_sha256','0'*64),('native_runtime','accepted'),('operational_grant',True),('product451814442_aggregate_credit',451814442)]:
        changed=copy.deepcopy(interface);changed[field]=bad
        refuses('scope-mismatch:'+field,lambda x=changed:exact_interface(x,parts,p0,expected_symbols))
    for key in expected_symbols:
        for modification in ['omit','positive','unit']:
            changed=copy.deepcopy(interface)
            if modification=='omit': del changed['symbols'][key]
            elif modification=='positive': changed['symbols'][key]['positive']=not expected_symbols[key]['positive']
            else:changed['symbols'][key]['unit']='arbitrary positive count'
            refuses('symbol-scope:'+modification+':'+key,lambda x=changed:exact_interface(x,parts,p0,expected_symbols))
    for name,row in callee_prices.items():
        changed=copy.deepcopy(row);changed['#fixed']-=1
        refuses('underprice-export:'+name,lambda x=changed,y=row:require(x==y,'exact-export-required'))
    for key,count in required.items():
        changed=dict(cuts_seen);changed[key]=count-1
        refuses('omit-leaf-edge:'+key,lambda x=changed:require(x==required,'all-leaf-cut-multiplicities-required'))
    for kind in decoded['resource_frontiers']:
        changed=copy.deepcopy(decoded);del changed['resource_frontiers'][kind]
        refuses('DecodedFunction-missing-nested:'+kind,lambda x=changed:require(resource_price(x,cuts)==prices['DecodedFunction'],'complete-three-cuts-required'))
    for key in imports:
        changed=set(imports);changed.remove(key)
        refuses('omit-payload-import:'+key,lambda x=changed:require(x==imports,'all19-imports-required'))
    for value in [True,False,None,-1,1.0,'1',U64+1]:
        refuses('non-u64:'+repr(value),lambda x=value:bound(x))
    for n in [52,54]: refuses('wrong-entry-visits:'+str(n),lambda x=n:require(x*per_visit==53*per_visit,'entry53-once'))
    refuses('constructor-four-proof-subset-as-complete',lambda:require(subset==exact_ctor,'six-actual-proof-visits'))
    refuses('crossed-core-split',lambda:require(callee_prices['core_before_fixed_store']==callee_prices['core_fixed_store_and_after'],'distinct-source-phase-prices'))
    # Test integer math independently, including nontrivial near-overflow cases.
    rng=random.Random(0x14635)
    numeric=[]
    for index in range(96):
        values={key:rng.randrange(0 if not row['positive'] else 1,1000000) for key,row in expected_symbols.items()}
        calc=lambda row:sum(value*(1 if key=='#fixed' else values[key]) for key,value in row.items())
        subtotal=calc(p0)+sum(calc(parts[key]) for key in PHASES)
        require(subtotal==calc(whole) and subtotal<=U64,'independent-numeric-oracle')
        numeric.append({'case':index,'input_sha256':digest(canon(values)),'whole':subtotal})
    for key in ['L_str','P0_inspections','P0_usage_reads']:
        refuses('derived-overflow:'+key,lambda k=key:bound(whole['#fixed']+whole[k]*U64))

    dump('recomposition.json',{'schema':1,'source_tree_sha256':SOURCE,'host_tree_sha256':HOST,
        'parts':{k:expression(v) for k,v in parts.items()},'P0':expression(p0),'whole_host':expression(whole),
        'entry_visits':dict(visits),'per_visit':per_visit,'returned_payload':prices['OwnedFixtureOutcomeV1'],
        'typed_imports':{k:prices[k[9:].replace(' ','')] for k in sorted(imports)},
        'constructor_subset':subset,'constructor_actual':exact_ctor,'DecodedFunction':{'row':decoded,'price':prices['DecodedFunction']},
        'source_native_core_before':900979,'source_native_core_after':874193,
        'edge_audit':edge_audit,'numeric_oracles':numeric,'no_product_policy_or_runtime_authority':True})
    dump('private-interface-audit.json',{'schema':1,'exports':primitive_reviews,'direct_adapter_amendment_candidates':adapter_rows,
        'decision':'A bounded clarification amendment is warranted for these nine exact direct adapters if root selects it. No numerical zero/default is assigned; all 21 symbols remain mandatory in the frozen interface.',
        'counted_unit':['authored logical source/control/callsite events','actual caller scalar/native operand and result occurrences','named source-row actions and multiplicities','actual authored callback edges','complete qualified payload teardown and requested resource backing interfaces'],
        'outside_unit':['private standard-library/compiler implementation','panic and unwind implementation','private allocator/kernel implementation and physical overhead','private retry/atomic retry implementation','CPU instructions/time/stack/RSS'],
        'remaining12_export_review':'Retain exact transitive primitive and accepted-row rosters. Native/resource requests need separately reviewed bounds/correspondence and exact caller binding; no blanket private-implementation number is required by this logical unit.',
        'root_selection_applied':False,'whole_funding':False})
    dump('adverse-results.json',{'schema':1,'cases':adverse,'count':len(adverse),'all_refused':True})
    dump('input-custody.json',{'schema':1,'files':custody})
    dump('audit-results.json',{'schema':1,'passed':True,'assertions':len(checks),'adverse_cases':len(adverse),
        'source_members':146,'host_members':11,'candidate_seal_sha256':SEAL,'known_constant':whole['#fixed'],
        'symbols':35,'private_adapter_amendment_candidates':9,'complete_host_funding':False,'operational_grant':False,
        'compiler_or_product_or_native_execution':False})
    print(json.dumps({'passed':True,'assertions':len(checks),'adverse_cases':len(adverse),'known_constant':whole['#fixed'],'symbols':35},sort_keys=True))

if __name__=='__main__':main()
