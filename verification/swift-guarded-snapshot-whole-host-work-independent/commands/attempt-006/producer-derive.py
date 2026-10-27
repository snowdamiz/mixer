#!/usr/bin/env python3
"""Derive only this packet from pinned frozen data. No foreign script imports."""
import collections, gzip, hashlib, json, re, sys
from pathlib import Path
from model import PHASES, Linear, Symbol, term, total, add, mul

D = Path(__file__).resolve().parent
R = D.parents[1]
V = R / 'verification'
SOURCE = '690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185'
HOST = '027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2'
inputs = {}; assertions = []; edges = []; symbols = {}

def sha(raw): return hashlib.sha256(raw).hexdigest()
def canonical(value): return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
def check(name, passed):
    if not passed: raise AssertionError(name)
    assertions.append(name)
def read(path):
    raw = path.read_bytes(); inputs[str(path.relative_to(R))] = {'bytes': len(raw), 'sha256': sha(raw)}
    return raw
def load(path): return json.loads(read(path))
def write(name, value):
    raw = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    if '--check' in sys.argv: check('current:' + name, (D/name).read_bytes() == raw)
    else: (D/name).write_bytes(raw)
def pin(path, digest):
    raw = read(path); check('pin:' + path.name, sha(raw) == digest); return json.loads(raw)
def packet(name, digest, count):
    path = V/name; seal = pin(path/'seal.json', digest)
    check('members:' + name, len(seal['members']) == count)
    for member in seal['members']:
        p = Path(member['path']); check('safe:' + name + '/' + str(p), not p.is_absolute() and '..' not in p.parts)
        raw = read(path/p); check('member:' + name + '/' + str(p), len(raw) == member['bytes'] and sha(raw) == member['sha256'])

ACCEPTANCES = {
 'parent-work-source146': '596c92d6269fa39854184b2cd97000390b37a7e28357121b2558f6d7aedb34f2',
 'loader-work-source146': 'c38cfa03526c88b32d4dbcfe578e37bef14ed9cb3de5633fddcd6ebb2082b6db',
 'child-entry-cost': '2efea9e81115620c4c029267ffdf49457e4d1ca6ffa753051eeed3a1a2336ead',
 'leaf-shell-cost': 'abd0fc1d091b903a0a1f89b693d59e090cd24b91a6fb3b6dc55af223c2d6ae8b',
 'payload-destruction': '89cbab409dc2944861f29520149f52b9a2447cc88ded1f1cad4a8e08ef204195',
 'leaf-callee-cost': '649a8219021885b5c1da84b0a77efb22492f386ab1d72a41c76e40cd03c60761',
 'resource-cost': '854c90f7824676cec2483571d5de4fce27965758e7e583186fa2361d965a118f',
}

def symbol(name, unit, reason, positive=True):
    item = Symbol(name, unit, reason, positive).__dict__
    if name in symbols: check('same-symbol:' + name, symbols[name] == item)
    symbols[name] = item; return term(name)

def resource_row(row, cuts):
    out = mul(row['structural_occurrence_allowance'], add(1, row['inline_bytes']))
    for name, count in row['resource_frontiers'].items():
        cut = cuts[name]; price = add(cut['interface_work'], cut['native_resource_backing'])
        dynamic = row.get('dynamic_resource_elements', {}).get(name)
        if dynamic:
            check('all-three-nested:' + row['type'], set(dynamic['resource_frontiers']) == {'Vec<Type>', 'Vec<DecodedInstruction>', 'Vec<u32>'})
            check('slot136/64:' + row['type'], dynamic['inline_bytes'] == cut['element_inline_bytes'] == 136 and cut['max_live_elements'] == 64)
            price = add(price, mul(64, resource_row(dynamic, cut['element_cuts'])))
        out = add(out, mul(count, price))
    return out

def loader_quote(geometry, ledger):
    # Independent expansion of the frozen accepted finite graph, no original runner.
    variables = dict(source=geometry['source'], validator_source=geometry['validator_source'],
        maximum_file=max(geometry[k] for k in ('source','executable','build','session')),
        allocation_cap=max(geometry['metadata'],geometry['scratch']),
        retained_visits=(max(geometry[k] for k in ('source','executable','build','session'))+4095)//4096+1, read_buffer=4096)
    cache = {}; active = set(); nodes = ledger['nodes']; validator = ledger['roots']['validator']
    def expand(key, mode):
        if mode == 'wrapper' and key == validator: return 0  # Charged explicitly as (credits+1)*K below.
        identity = (key, mode)
        if identity in active: raise ValueError('unclassified-loader-cycle')
        if identity in cache: return cache[identity]
        active.add(identity); row = nodes[key]
        check('loader-local:' + key, row['local_actions'] == add(2, *row['parts'].values()))
        price = row['local_actions']
        for native in row['native']:
            extent = variables[native['extent']] if isinstance(native['extent'], str) else native['extent']
            price = add(price, mul(native['count'], extent))
        for call in row['calls']: price = add(price, mul(call['multiplicity'], expand(call['callee'], mode)))
        repeat = row['repeat'] if mode == 'wrapper' else row.get('validator_fixed_repeat', 1)
        if isinstance(repeat, str): repeat = variables[repeat]
        price = mul(repeat, price); active.remove(identity); cache[identity] = price; return price
    wrapper = expand(ledger['roots']['loader'], 'wrapper'); k = expand(validator, 'validator')
    return {'wrapper': wrapper, 'K': k, 'credits': geometry['credits'],
            'work': add(wrapper, mul(add(geometry['credits'], 1), k)), 'geometry': geometry}

def main():
    accepted = {key: pin(V/'swift-semantic-adapter-root-review'/('guarded-snapshot-'+key+'-host-acceptance.json'), digest) for key,digest in ACCEPTANCES.items()}
    for key, value in accepted.items(): check('source146:' + key, value['source_tree_sha256'] == SOURCE)
    for key in accepted:
        for role in ('producer','independent'):
            record=accepted[key][role]; packet(Path(record['path']).name,record['seal_sha256'],record.get('members',record.get('members_verified')))
    C=V/'swift-guarded-snapshot-host-composition'
    manifest=load(C/'source-manifest.json'); check('source-manifest',len(manifest['members'])==146 and sha(canonical(manifest['members']))==SOURCE)
    source={}
    for member in manifest['members']:
        path=C/'overlay/vm'/member['path']
        if not path.is_file(): path=V/'swift-guarded-snapshot-funding-implementation/source/vm'/member['path']
        raw=read(path); check('source:'+member['path'],len(raw)==member['bytes'] and sha(raw)==member['sha256']); source[member['path']]=raw.decode()
    host=load(C/'host-support-manifest.json');check('host11',len(host['members'])==11 and sha(canonical(host['members']))==HOST)
    for member in host['members']:
        raw=read(V/'swift-real-profile-loader-binding/host'/member['path']);check('host:'+member['path'],len(raw)==member['bytes'] and sha(raw)==member['sha256'])
    resource=V/'swift-guarded-snapshot-resource-cost'
    rows=load(resource/'rows.json'); internal=load(resource/'internal-rows.json'); cuts=load(resource/'resource-cuts.json')
    prices={}
    for row in rows+internal['rows']:
        name=row['type'].replace(' ',''); price=resource_row(row,cuts)
        if name in prices:check('duplicate-typed-row:'+name,prices[name]==price)
        prices[name]=price
    components=load(resource/'components.json')
    check('twenty-complete-rows',len(rows)==20 and all(prices[k]==v for k,v in components['rows'].items()))
    check('thirteen-internal-rows',len(internal['rows'])==13 and all(prices[k]==v for k,v in internal['prices_per_one'].items()))
    check('returned-and-pervisit',prices['OwnedFixtureOutcomeV1']==45196204 and components['during_entry_per_visit']==1210256815)
    constructor=load(resource/'constructor-roster-composition.json')
    subset=add(*(mul(prices[k],n) for k,n in constructor['multipliers_imported_from_frozen_caller_roster'].items()))
    check('constructor12typed',subset==constructor['typed_body_price_sum']==134288951629)
    # One missing callee type: exact declaration, concrete compiler type and all nested resources.
    archive=read(V/'swift-guarded-snapshot-host-composition-independent/commands/exact146-metadata-mir/stdout.gz')
    check('full-layout-archive',sha(archive)=='1ddc23c6274a1c4f148e9d4a389aa0aeaa070384929280de044f4889a49ec9ec')
    full=gzip.decompress(archive);check('full-layout-raw',sha(full)=='6c924c8088173db78afb1f648b284df7d8d139b3389bd090a9552df4130cfe7a')
    layout='print-type-size type: `experimental::cache::DecodedFunction`: 96 bytes, alignment: 8 bytes'
    check('DecodedFunction96/8',full.decode().splitlines().count(layout)==1)
    inv=load(V/'swift-guarded-snapshot-payload-destruction-cost/inventory.json')
    declaration=next(x for x in inv['declarations'] if x['name']=='DecodedFunction')
    check('DecodedFunction8nodes',declaration['fields']==['u32','u32','usize','Vec<Type>','Vec<DecodedInstruction>','Vec<u32>','usize'])
    check('DecodedFunction-no-authored-Drop',all(x['type']!='DecodedFunction' for x in inv['source_drop_implementations_including_test_only']))
    text=source['src/experimental/cache/mod.rs']; start=text.index('struct DecodedFunction {'); end=text.index('\n}',start)+2
    check('DecodedFunction-declaration',sha(text[start:end].encode())==declaration['declaration_sha256'])
    decoded={'type':'DecodedFunction','inline_bytes':96,'structural_occurrence_allowance':8,
        'resource_frontiers':{'Vec<Type>':1,'Vec<DecodedInstruction>':1,'Vec<u32>':1},'dynamic_resource_elements':{}}
    prices['DecodedFunction']=resource_row(decoded,cuts)
    write('additive-decoded-function-row.json',{'status':'new-source-interface-candidate','row':decoded,'price':prices['DecodedFunction'],
        'declaration':declaration,'compiler_line':layout,'actual_declared_Drop':False,'private_impl_outside_unit':True,'runtime_authority':False})
    callee=pin(V/'swift-guarded-snapshot-leaf-callee-cost-independent/bound-cost-interface.json','2c1529c4b0431deeda89bc88f3b6ee97b647883630ef5093ada45c3de5a1f268')
    amendment=pin(V/'swift-guarded-snapshot-leaf-callee-cost-independent/capture-roster-correction.json','27ecdff9893e88c9c7b21758a4158ef9ddca7802eb9eab8bd071254c0e6b3d5d')
    check('capture-amendment',amendment['actual_capture_count']==8 and amendment['original_closure_size_observed']==64 and amendment['original_closure_alignment_observed']==8)
    check('all-native-closed',callee['remaining_native_terms']==0 and all(not r['native'] for r in callee['exports'].values()))
    payloads={k for row in callee['exports'].values() for k in row['payload']}
    check('all19typedimports',len(payloads)==19 and all(k[9:].replace(' ','') in prices for k in payloads))
    graph=load(V/'swift-guarded-snapshot-leaf-callee-cost/callee-ledger.json')
    private_roster=[]
    def primitive_roster(node,active=()):
        if node in active:raise ValueError('private-roster-cycle')
        row=graph['nodes'][node]; primitives=collections.Counter(row.get('primitive',{})); named=[]
        if row['kind'].startswith('accepted-'):
            named.append({'node':node,'count':1,'own':row['own'],'parts':row.get('parts',{}),
                'binding':row.get('binding',{}),'native_policy':row.get('native_policy','')})
        for child,count in row['calls'].items():
            prim,ns=primitive_roster(child,active+(node,))
            for key,n in prim.items():primitives[key]=add(primitives[key],mul(count,n))
            named.extend(dict(item,count=mul(count,item['count'])) for item in ns)
        return primitives,named
    for export,node in graph['exports'].items():
        prim,named=primitive_roster(node);row=graph['nodes'][node]
        adapter=row['kind']=='closed-standard-logical-adapter'
        private_roster.append({'export':export,'symbol':callee['exports'][export]['required_private_primitive_cut'],'node':node,
            'kind':row['kind'],'primitive_callsite_occurrences':dict(prim),'accepted_named_source_rows':named,
            'counted_inherited_interfaces':{
                'source_body_and_callsite': 'Exact authored MIR source events and explicitly rebound named row actions in fixed export price; direct closed standard adapter has one declared tag/transfer event.' if not adapter else row['proof'],
                'scalar_and_native_transfers':'Complete actual caller operand/result local occurrences and frozen native substitutions; direct adapter operand/result surfaces paid at caller.',
                'payload':'Every exact actual typed payload occurrence imported separately; resource File/Arc/Error/Vec/Box frontiers and requested backing retain their qualified source rows.',
                'callbacks':'Each actual authored callback edge follows frozen graph multiplicities; private retry behavior is expressly excluded by inherited unit.'},
            'outside_inherited_unit':['private standard-library implementation and panic/unwind internals','compiler lowering and physical copies',
                'allocator implementation/physical overhead','kernel implementation','private retries including atomic retries','CPU/time/stack/RSS'],
            'review_proposal':'Clarify whether any additional in-unit event remains beyond these counted caller/callee/native/payload interfaces. Do not price private implementation by an arbitrary quantum. For this adapter the supplied frozen proof identifies no additional in-unit event.' if adapter else
                'Review this exact primitive/named-row roster for additional in-unit native/resource request events. Where all are already covered, amend the mandatory cut as contract clarification; do not count out-of-unit implementation as missing work.',
            'mandatory_symbol_preserved':True,'symbol_value_selected':False,'closed_by_this_packet':False})
    write('private-export-allowance-roster.json',{'schema':1,'exports':private_roster,'count':len(private_roster),
        'closed_standard_adapter_proposals':sum(x['kind']=='closed-standard-logical-adapter' for x in private_roster),
        'scope':'Source-backed review proposal only. All21 mandatory symbols remain present until an accepted contract amendment.',
        'no_zero_one_default_or_CPU_bound':True})
    # Actual array-to-slice coercion only in AccountedWasi::snapshot_pair_v1.
    wasi=source['src/experimental_wasi/accounted.rs']; pair=wasi[wasi.index('    pub(crate) fn snapshot_pair_v1'):]
    check('wasi-array4-field','buffers: [Option<ReservationTicket>; 4]' in wasi)
    check('wasi-array4-callsites','for ticket in &self.buffers' in pair and 'self.buffers.iter().zip(capacities)' in pair)
    scalar=load(V/'swift-guarded-snapshot-leaf-shell-cost/scalar-shapes.json')
    check('Ticket3-source-leaves',scalar['definitions']['ReservationTicket']['scalar_leaves']==3 and scalar['definitions']['ReservationTicket']['fields']==['u64','SwiftReservationCategory','usize'])
    # Ticket3 + Option tag =4 source leaves; native Option<Ticket>=24. Existing 2x multiplier is retained.
    array_L=4*(4+24)
    symbol('L_str','source scalar leaves and native UTF-8 bytes per str occurrence','Finite actual provenance for every reachable str must be reviewed; static lifetime alone is insufficient.')
    callee_expr={}
    for name,row in callee['exports'].items():
        expression=Linear(add(row['fixed'],*(mul(n,prices[k[9:].replace(' ','')]) for k,n in row['payload'].items())))
        for ty,n in row['unsized'].items():
            if ty=='str': expression=expression.plus(term('L_str',2*n))
            elif ty=='[Option<ReservationTicket>]' and name=='callee::accounted::AccountedWasi::snapshot_pair_v1': expression=expression.plus(Linear(mul(2*n,array_L)))
            else: raise ValueError('unqualified-unsized-interface')
        primitive=row['required_private_primitive_cut'];symbol(primitive,'logical interface allowance','Required inherited callee private boundary; no positive number proves applicability.')
        callee_expr[name]=expression.plus(term(primitive))
    constructor_name='callee::construct_snapshot_in_scope_v1'
    ctorrow=callee['exports'][constructor_name]
    check('actualconstructor6proof',ctorrow['payload']['payload::AdoptedProof']==6)
    exact_ctor=add(*(mul(n,prices[k[9:].replace(' ','')]) for k,n in ctorrow['payload'].items()))
    check('constructor-extra-two-explicit',exact_ctor==add(subset,mul(2,prices['AdoptedProof'])))
    write('typed-callee-imports.json',{'typed_imports':{k:prices[k[9:].replace(' ','')] for k in sorted(payloads)},
        'all19_imported':True,'accepted_resource_rows':33,'additional_row':'DecodedFunction','constructor_subset':subset,
        'extra_AdoptedProof_visits':2,'extra_AdoptedProof_price':mul(2,prices['AdoptedProof']),'constructor_exact_payload':exact_ctor,
        'exports':{k:v.json() for k,v in callee_expr.items()},'private_allowances':21,'actual_native_terms':0})
    shell=load(V/'swift-guarded-snapshot-leaf-shell-cost/operation-ledger.json')
    shell_interface=load(V/'swift-guarded-snapshot-leaf-shell-cost/cost-interface.json')
    native=load(V/'swift-guarded-snapshot-leaf-shell-cost/native-occurrence-interface.json')
    layouts=load(V/'swift-guarded-snapshot-leaf-shell-cost-independent/layout-review-results.json')
    sizes=dict(native['known_actual146_layouts_used']);sizes.update({x['key']:x['size'] for x in layouts['queries']})
    parts={key:Linear(0) for key in PHASES}; observed=collections.Counter(); shell_fixed=0; shell_str=0
    for function in shell['functions']:
        phase='P4_selected_route' if function['function'] in ('construct','outer','finish') else 'P3_before_store'
        base=0; unsized=0
        for block in function['blocks'].values():
            for op in block['lines']:
                base=add(base,op['source_action_units'],op['known_constant_bytes'],*(mul(n,sizes[k]) for k,n in op['native_type_coefficients'].items()))
                check('only-shell-str',set(op['unsized_coefficients'])<={'str'})
                unsized=add(unsized,2*op['unsized_coefficients'].get('str',0))
        parts[phase]=parts[phase].plus(Linear(base)).plus(term('L_str',unsized) if unsized else Linear(0))
        shell_fixed=add(shell_fixed,base);shell_str=add(shell_str,unsized)
        for site in function['callee_and_drop_sites']:
            kind=site['kind']
            if kind=='included-source-body':continue
            if kind=='required-core-split':
                entries=[('core_before_fixed_store','P3_before_store'),('core_fixed_store_and_after','P4_selected_route')]
            else: entries=[(site['key'],phase)]
            for key,where in entries:
                observed[key]+=1
                if key in callee_expr: value=callee_expr[key]
                elif key.startswith('drop_payload::'): value=Linear(prices[key[14:].replace(' ','')])
                else: raise ValueError('unpriced-leaf-edge:'+key)
                parts[where]=parts[where].plus(value)
                edges.append({'owner':function['function'],'phase':where,'key':key,'count':1,'MIR_line':site['MIR_body_line'],
                    'block':site['block'],'statement':site['code'],'work':value.json()})
    for key in ('private_std_compiler_lowering_and_requested_backing_allowance','retained_dynamic_resource_backing_and_native_transfer_allowance'):
        symbol(key,'logical interface/requested backing allowance','Inherited whole-leaf boundary spans P3/P4; paid once in earliest leaf envelope.');observed[key]=1
        parts['P3_before_store']=parts['P3_before_store'].plus(term(key))
    check('all33cuts-exact',dict(sorted(observed.items()))==shell_interface['required_nonzero_callee_drop_and_backing_cuts'])
    check('shell4236953+4376L',shell_fixed==4236953 and shell_str==4376)
    # Four entry bodies + two helpers. Partition every original event exactly once.
    entry=load(V/'swift-guarded-snapshot-child-entry-cost/ledger.json');entry_partition=[]
    parts['P1_setup']=Linear(entry['setup_source_work'])
    leaves={(x['function'],x['local']):x['source_leaves'] for x in entry['actual_native_layouts_as_data']}
    entry_source=entry['setup_source_work']; carrier=entry['functions']['run_prepaid_fixture_v1']
    head=carrier['head'].split(' -> ',1)[0]; params=re.findall(r'(_\d+):',head)
    prologue=add(2,*(mul(2,leaves[('run_prepaid_fixture_v1',p)]) for p in params))
    parts['P2_arguments']=Linear(prologue)
    carrier_sum=prologue
    for statement in carrier['statements']:
        amount=add(2+sum(statement.count(c) for c in '.*[]'),*(mul(2,leaves[('run_prepaid_fixture_v1',p)]) for p in re.findall(r'\b_\d+\b',statement)))
        phase='P5_payload_teardown' if statement.startswith(('drop(','return;')) or 'OwnedFixtureOutcomeV1::' in statement else 'P2_arguments'
        parts[phase]=parts[phase].plus(Linear(amount));carrier_sum=add(carrier_sum,amount)
        entry_partition.append({'statement':statement,'phase':phase,'source_actions':amount})
    check('carrier92906',carrier_sum==carrier['local_actions']==92906)
    for key in ('copy_claims_v1','invoke_loaded_leaf_once_v1','cancellation_default','cancellation_clone'):
        value=entry['functions'][key]['local_actions'];parts['P2_arguments']=parts['P2_arguments'].plus(Linear(value));entry_source=add(entry_source,value)
    entry_source=add(entry_source,carrier_sum);check('entry119922',entry_source==119922)
    check('setup42+caller11drops',sum(x['repeat'] for x in entry['drop_sites'] if x['function']=='setup_files_once_v1')==42 and sum(x['repeat'] for x in entry['drop_sites'] if x['function']!='setup_files_once_v1')==11)
    parts['P1_setup']=parts['P1_setup'].plus(Linear(mul(42,1210256815)))
    parts['P5_payload_teardown']=parts['P5_payload_teardown'].plus(Linear(add(mul(11,1210256815),45196204)))
    parts['P2_arguments']=parts['P2_arguments'].plus(Linear(24))
    for index in range(5):
        name='native_open_request_'+str(index);symbol(name,'native request byte allowance','Actual finite path, conversion/native interface and immutable path binding required.');parts['P1_setup']=parts['P1_setup'].plus(term(name))
    symbol('native_error_request','native request byte allowance','Original owned-File error request boundary remains unqualified.');parts['P1_setup']=parts['P1_setup'].plus(term('native_error_request'))
    loader=load(V/'swift-guarded-snapshot-loader-work-source146/mir-ledger.json')
    cap=loader_quote(load(V/'swift-guarded-snapshot-loader-work-source146/cap-geometry.json'),loader)
    check('loader-cap',cap['work']==895083809874789059 and cap['wrapper']==97394558768720 and cap['K']==1748020339)
    # Full cap is a conservative accepted source bound, NOT actual fixture geometry.
    parts['P1_loader']=Linear(cap['work'])
    fixture=load(V/'swift-semantic-adapter-root-review/guarded-snapshot-host-fixture-source-selection.json')
    check('fixture-selection-only',fixture['actual_build_session_executable_compiler_process_binding_pending'] is True)
    source_raw=read(R/fixture['source']['path']);check('immutable1947source',len(source_raw)==1947 and sha(source_raw)==fixture['source']['sha256'])
    symbol('P0_inspections','finite exact source occurrence count','I cannot default to zero; selected actual root/caller must establish count.',False)
    symbol('P0_usage_reads','finite exact source occurrence count','U cannot default to zero; selected actual root/caller must establish count.',False)
    p0=Linear(2628088).plus(term('P0_inspections',194231)).plus(term('P0_usage_reads',1039))
    for name,reason in [('P0_root_route','Unselected actual trusted root constructor and final quote/caller path.'),('P0_fixture_binding','Immutable paths/claims/budgets/build/session/executable preparation and review binding.'),('P0_dynamic_backing','Parent work to acquire/retain/destroy backing and late finalization not covered by account surface.')]:
        symbol(name,'logical source/interface work',reason);p0=p0.plus(term(name))
    whole=total([p0,*parts.values()])
    conditions=[
        'Independently review this additive DecodedFunction row, edge attribution and source timing composition.',
        'Close finite actual str provenance at every reachable site; static lifetime or maximum authored literal alone is insufficient.',
        'Qualify all21 callee private allowances and both inherited leaf backing/native boundary cuts in the exact logical unit; private implementation and CPU work remain excluded.',
        'Select actual immutable five paths and independently bound all5 native-open/error request terms; no source path cap exists.',
        'Bind actual selected P0 root/caller with finite I/U and complete root/fixture/backing work before account or quote construction; late token release still consumes P0 work.',
        'Complete exact compiled standard-library correspondence and immutable executable/build/session/compiler-context/caller binding; source resource prices remain conditional.',
        'Independently accept complete whole-host storage and lifetime unions; work arithmetic confers no storage or retirement credit.',
        'Review/select actual root policy and actual six-component source integration; current selected functions still refuse WholeQuotePending/RootPolicyPending.',
        'Fresh genuine loader/writer execution and healthy cleanup remain unrun; no native or GA claim.'
    ]
    interface={'schema':1,'status':'source146-whole-host-conditional-logical-work-interface','source_tree_sha256':SOURCE,'host_tree_sha256':HOST,
        'unit':'abstract logical source/typed aggregate/destructor interface occurrences plus requested native-byte allowances; excludes CPU/private implementations/physical allocation/stack/RSS/time',
        'child':{key:parts[key].json() for key in PHASES},'P0':p0.json(),'whole_host':whole.json(),'symbols':symbols,
        'qualification_conditions':conditions,'operational_grant':False,'product451814442_aggregate_credit':0,'native_runtime':'paused',
        'activity_attribution':'Conservative source-frame envelopes, not wall-clock phase-local meters. Every child envelope is committed before first setup; P0 already exists and remains through final token release.'}
    # Keep six tuple order semantic although other JSON documents use sorted keys.
    raw=(json.dumps(interface,indent=2)+'\n').encode()
    if '--check' in sys.argv:check('current:work-interface.json',(D/'work-interface.json').read_bytes()==raw)
    else:(D/'work-interface.json').write_bytes(raw)
    write('entry-partition.json',{'source_total':entry_source,'carrier_source_total':carrier_sum,'statement_partition':entry_partition,
        'setup_drop_visits':42,'caller_drop_visits':11,'per_visit_payload':1210256815,'total_drop_work':mul(53,1210256815),
        'returned_P5_payload':45196204,'returned_carrier_events_separate':True,'53_applied_once':True,
        'rule':'Full setup body six times to P1. Carrier prologue and non-return statements to earliest argument envelope; typed carrier construction, return/drop to P5; helpers exactly once. P2 frame envelope spans setup/loader/return alternatives.'})
    write('actual-edges.json',{'edges':edges,'33cut_occurrences':dict(observed),'shell_fixed':shell_fixed,'shell_L_str_coefficient':shell_str,
        'all_source_frames_once':8,'source_activity_spans':'leaf/adoption frames include both early refusal and post-store return/cleanup, so P3 is an early-funded frame envelope; core callback/store split remains exact.',
        'account_source_order':['preexisting P0','quote','atomic child work/storage commit','FnOnce setup/load/args/leaf','returned typed owner retained','payload destruction','P0 token return','P0 storage release; work never refunded'],
        'constructor_real_typed_payload':exact_ctor,'product_aggregate_credit':0})
    write('unsized-provenance.json',{'array':{'scope':'only AccountedWasi::snapshot_pair_v1','field':'[Option<ReservationTicket>; 4]',
        'callsites':['for ticket in &self.buffers','self.buffers.iter().zip(capacities)'],'count':4,'ticket_source_leaves':3,
        'Option_source_leaves':4,'Option_native_extent':sizes['Option<ReservationTicket>'],'L':array_L,
        'formula':'4*(4+24)=112; inherited2*n applied unchanged; deliberate overcoverage of both dimensions','status':'source-candidate-exact-field-callsite-bound'},
        'str':{'status':'unresolved-required','why':'All reachable values need provenance; no bound selected from lifetime, inline reference width, source scan, arbitrary positive number or maximum literal.',
            'known_declarations':['SwiftRunFailure.code: &static str','Fault.code: &static str'],
            'external_fixture_root_types':['Files','numeric budgets','Instant','Cancellation','8x32 claims bytes'],
            'remaining':'Complete accepted named-callee/constructor/loader forwarding provenance review across all inherited failure/string-producing paths.'}})
    write('loader-geometries.json',{'accepted_cap_bound':cap,'actual_source_selection':fixture['source'],'original_selected_validation_limits':fixture['original_validation_limits'],
        'actual_fixture_loader_work_selected':False,'actual_build_session_executable_bounds_pending':True,
        'cap_is_conservative_component_not_host_budget':True,'no_validator_credit_or_geometry_substitution':True})
    write('remaining-conditions.json',{'conditions':conditions,'symbols':symbols,'known_static_work_constant':whole.fixed,
        'work_grant':False,'static_unit_is_not_physical_CPU':True,'new_compiler':False,'product_or_native_execution':False})
    write('input-custody.json',{'schema':1,'files':inputs})
    write('derivation-results.json',{'schema':1,'assertions':sum(not x.startswith('current:') for x in assertions),'passed':True,
        'whole_host_known_constant':whole.fixed,'symbols':len(symbols),'callee_payload_imports':len(payloads),'leafcuts':len(observed),
        'new_typed_rows':1,'product_execution':False,'compiler':False,'root_policy_selected':False})
    print(json.dumps({'passed':True,'assertions':len(assertions),'known_constant':whole.fixed,'symbols':len(symbols),'whole_quote_or_grant':False},sort_keys=True))

if __name__=='__main__':main()
