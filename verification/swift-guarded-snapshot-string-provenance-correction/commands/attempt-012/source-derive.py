#!/usr/bin/env python3
"""Rehash accepted immutable inputs; derive this source candidate only."""
import gzip,json,sys
from pathlib import Path
from mir_graph import analyze,sha,require,Refused
D=Path(__file__).resolve().parent;R=D.parents[1];V=R/'verification'
SOURCE='690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185'
HOST='027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2'
ACCEPT='d797f7c9a86259fdb40700c290e5f83488142117a355f7b5826c1d92710a784f'
PACKETS={'swift-guarded-snapshot-whole-host-work-composition':'95c1a3087b36996dc06e8411f97e3ebce2610120f9ac742326824a52ab9c63ca',
'swift-guarded-snapshot-whole-host-work-independent':'7d18cb048499cac2cb62bec2b4a954d1d032b1fbd950cb6f6941d181debc024b'}
inputs={}
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()
def read(path):
    raw=path.read_bytes();inputs[str(path.relative_to(R))]={'bytes':len(raw),'sha256':sha(raw)};return raw
def load(path):return json.loads(read(path))
def pin(path,digest):
    raw=read(path);require(sha(raw)==digest,'pin:'+str(path));return json.loads(raw)
def save(name,value,check):
    raw=(json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
    if check:require((D/name).read_bytes()==raw,'rederived:'+name)
    else:(D/name).write_bytes(raw)

def main(check=False):
    inputs.clear()
    # Original producer/reviewer bytes and failure receipts stay immutable.
    pins={'swift-guarded-snapshot-string-provenance':'b228f62a0751e6d1b45e27edabe500cc5e52449db1d33ee59abca0f695b6fa2f',
          'swift-guarded-snapshot-string-provenance-independent':'741e104537fc3ddc57fc499a764cca9fedaa2b42d2fe109eeb590504b01241d9'}
    for name,digest in pins.items():
        seal=pin(V/name/'seal.json',digest)
        for member in seal['members']:
            relative=Path(member['path']);require(not relative.is_absolute() and '..' not in relative.parts,'frozen-member-path')
            raw=read(V/name/relative);require(len(raw)==member['bytes'] and sha(raw)==member['sha256'],'frozen-member:'+name+'/'+str(relative))
    pin(V/'swift-semantic-adapter-root-review/guarded-snapshot-string-provenance-review-return.json','142648fc21ef7e9dcd36b3e7849b17a18f7a94cc2ac2c6b848c362140fea668b')
    correction=pin(V/'swift-guarded-snapshot-string-provenance-independent/correction-contract.json','b699930771cb7980b1ced76867c4d8a9760014be80c7fa63e4057145e6883341')
    require([r['id'] for r in correction['requirements']]==['R1','R2','R3','R4','R5'],'binding-correction-requirements')
    external=load(D/'external-contracts.json')
    require(external['no_general_classifier'] is True and external['new_instantiations_refuse'] is True,'closed-typed-interface-catalog')
    accepted=pin(V/'swift-semantic-adapter-root-review/guarded-snapshot-whole-host-work-host-acceptance.json',ACCEPT)
    for name,digest in PACKETS.items():
        seal=pin(V/name/'seal.json',digest)
        for member in seal['members']:
            relative=Path(member['path']);require(not relative.is_absolute() and '..' not in relative.parts,'member-path')
            raw=read(V/name/relative);require(len(raw)==member['bytes'] and sha(raw)==member['sha256'],'member:'+name+'/'+str(relative))
    custody=load(V/'swift-guarded-snapshot-whole-host-work-composition/input-custody.json')['files']
    def frozen(name):
        path=V/name;raw=read(path);key=str(path.relative_to(R));require(key in custody and inputs[key]==custody[key],'accepted-input:'+key);return raw
    base='swift-guarded-snapshot-loader-work-source146/'
    manifest=json.loads(frozen(base+'source146-manifest.json'));ref=json.loads(frozen(base+'source-reference-map.json'))
    require(manifest['tree_sha256']==SOURCE and len(manifest['members'])==146 and sha(canonical(manifest['members']))==SOURCE,'source146-exacttree')
    indexed={m['path']:m for m in manifest['members']};source={}
    require(len(ref['members'])==146,'complete-source-reference-map')
    for member in ref['members']:
        require({k:member[k] for k in ('path','bytes','sha256')}==indexed[member['path']],'map-to-manifest')
        raw=read(R/member['source']);require(len(raw)==member['bytes'] and sha(raw)==member['sha256'],'actual-source:'+member['path'])
        if member['path'].endswith('.rs'):source[member['path']]=raw.decode()
    host=json.loads(frozen(base+'host11-manifest.json'));require(len(host['members'])==11 and sha(canonical(host['members']))==HOST,'host11-exacttree')
    for member in host['members']:
        raw=read(V/'swift-real-profile-loader-binding/host'/member['path']);require(len(raw)==member['bytes'] and sha(raw)==member['sha256'],'host-member:'+member['path'])
    receipt=json.loads(frozen(base+'compiler-receipt.json'));archive=frozen(base+'whole-source146.mir.gz');raw=gzip.decompress(archive)
    require(receipt['source_tree_sha256']==SOURCE and receipt['source_members']==146 and receipt['exit_code']==0,'accepted-compiler-source')
    require(sha(archive)==receipt['MIR']['archive_sha256'] and len(archive)==receipt['MIR']['archive_bytes'],'accepted-MIR-archive')
    require(sha(raw)==receipt['MIR']['raw_sha256'] and len(raw)==receipt['MIR']['raw_bytes'],'accepted-MIR-raw')
    graph=analyze(raw.decode(),source)
    # The exact selected input has paths/bytes/numeric limits, with no caller
    # Fault, SwiftRunFailure, RuntimeControl, arbitrary proof or custom callback.
    initial=source['src/experimental_swift_reactor/cache/initial_profile_v1.rs']
    a=initial.index('    struct ReviewedFixtureBindingV1 {');b=initial.index('\n    }',a)+6;binding=initial[a:b]
    require(binding=="    struct ReviewedFixtureBindingV1 {\n        paths: [&'static Path; 5],\n        claims: UnverifiedProfileDigestBytesV1,\n        original_validation_budget: SwiftValidationBudget,\n        product_budget: SwiftRunBudget,\n    }",'exact-binding-type')
    control=source['src/experimental_swift_reactor/control.rs']
    require('            first_failure: None,' in control and '            cleanup_invariant: None,' in control,'fresh-control-string-state')
    require('let cancellation = Cancellation::default();' in initial,'fresh-cancellation')
    require('selected: Option<LoaderProvenanceV1>' in source['src/experimental_swift_reactor/retained_profile_loader_v1.rs'],'selected-proof-carrier')
    require('let policy = policy::Policy::swift();' in source['src/experimental/swift.rs'] and 'Self::SwiftReactorExperimentV1' in source['src/experimental/policy.rs'],'selected-validator-policy')
    # This extra imported inventory is immutable data, not an imported runner.
    drops=json.loads(frozen('swift-guarded-snapshot-payload-destruction-cost/inventory.json'))
    require(len(drops['observed_production_authored_drop_headers'])==3,'authored-drop-roster')
    require(any('PrepaidOwnedV1' in h for h in drops['observed_production_authored_drop_headers']),'actual-owned-drop-hook')
    require(any('PrepaidOwnedV1' in row['header'] and row['base']=='drop' for row in graph['nodes'].values()),'drop-hook-expanded')
    # Each str-valued callee result is resolved to an authored definition or a
    # reviewed preserving external frontier; no invented default closes a port.
    for row in graph['nodes'].values():
        for call in row['calls']:
            if call['result_type']=='&str':require(call['target']=='swift::ValidatedSwiftReactor::policy_identity','only-known-str-return')
    L=graph['L_str_source_candidate'];require(L==5080,'actual-constant-allocation-envelope')
    exact_contract={
      'entry':'trusted_local_host_account_entry_v1::run_one_fixture_v1',
      'prospective_dispatched_body':'trusted_local_host_account_entry_v1::run_prepaid_fixture_v1',
      'binding_declaration':binding,'binding_sha256':sha(binding.encode()),
      'root_incoming_authored_str_ports':[],
      'selected_specializations':{'B':'SnapshotBranchV1','B::Access':'SnapshotAccessV1','P':'SnapshotAdoptionV1','D':'SwiftDeclaration','MeterControl':'SwiftControl','Read':'std::fs::File','dispatch callback':'run_one_fixture_v1::{closure#0}'},
      'required_route':['FrozenFixtureV1 is the exact private binding carrier','selected proof is the unmodified result of load_selected_retained_profile_v1 in run_prepaid_fixture_v1','fresh control has first_failure=None; no caller control/failure/Fault is an input','no custom callback, custom Read implementation, policy substitution, fault injection or intervening mutation','all exact authored calls and callbacks remain the frozen graph; native Path/io::Error backing is a separate allowance'],
      'alternate_entry_obligation':'For every incoming direct str parameter or nested failure/Fault/code/policy string, supply its complete provenance and UTF-8 byte length. This packet cannot qualify a different caller from length, lifetime or pointer width; extend and re-review the source-bound graph.',
      'native_backing_excluded_from_L_str':['Path/OsStr native requests','io::Error private backing and kernel/native message strings'],
      'actual_P0_root_caller_and_fixture_binding_selected':False}
    failures={
      'Fault.code':'Fault::new forwards its code input; limit preserves it; RuntimeControl::fail copies fault.code, latches first_failure, and returns an existing failure unchanged.',
      'SwiftRunFailure.code':'Fresh latch None becomes one of the closed Fault producers. cleanup_fault_with_wasi forwards its code through Fault::new. Existing-stop, preparation/construction/completion/retirement, and cleanup paths forward the same typed values.',
      'experimental::Failure.code':'Reader::error/BodyState::error/Meter::error forward selected caller literals; Swift failure mapping copies raw.code. The selected loader retains the original typed validation failure.',
      'Policy::Frozen':'It can contain caller strings in another ingress. This selected validator constructs SwiftReactorExperimentV1; policy_identity returns its fixed literal. Root must retain that exact producer path.',
      'compile_time_option_env':'The exact retained compiler MIR and all allocations bind baked compile identity strings; a recompile needs fresh source/compiler/constant binding.',
      'caller_injection':'Public SwiftRunFailure literals and lower Fault/Meter/cleanup APIs permit arbitrary static string lengths. They are not inputs of the exact selected host entry and are refused as alternate caller evidence.'}
    trace={'schema':2,'conservation_rule':'Every primitive str assignment is literal, borrowed field/reference transfer or expanded authored return. Complete typed statement and nested carrier inventories accompany this conditional induction candidate. External contracts are exact identities plus compatible argument/result types, with all closure/named callbacks expanded. Fresh independent review remains required.',
      'direct_str_ports':[],
      'carrier_operations':{key:{'function':row['name'],'MIR_sha256':row['MIR_sha256'],'operations':row['carrier_operations']} for key,row in graph['nodes'].items() if row['carrier_operations']}}
    for port in graph['direct_str_parameters']:
        inbound=[]
        for edge in graph['edges']:
            if edge['callee']==port['function']:
                row=graph['nodes'][edge['caller']]
                calls=[call for call in row['calls'] if call['line']==edge['line']]
                inbound.append({'caller':edge['caller'],'kind':edge['kind'],'line':edge['line'],'statements':[x['statement'] for x in calls]})
        trace['direct_str_ports'].append(dict(port,function_name=graph['nodes'][port['function']]['name'],incoming=inbound))
    import induction
    full_induction=induction.derive(graph,source,
        load(V/'swift-guarded-snapshot-string-provenance-independent/source-semantic-review.json'),
        load(V/'swift-guarded-snapshot-string-provenance/graph.json'),
        load(V/'swift-guarded-snapshot-string-provenance-independent/typed-graph.json'),raw.decode())
    candidate={'schema':2,'status':'source146-string-provenance-correction-candidate-for-independent-review','source_tree_sha256':SOURCE,'host_tree_sha256':HOST,
      'accepted_wholework_sha256':ACCEPT,'unit':'one source scalar leaf and one native UTF-8 byte per str occurrence; inherited 2*n coefficients stay unchanged',
      'L_str':L,'literal_utf8_max':graph['literal_pool']['max_utf8_bytes'],'compiled_constant_allocation_max':graph['constant_allocations']['max_bytes'],
      'bound_derivation':'Candidate envelope max(all pinned compiler cooked-str literal UTF-8 extents, every pinned compiler constant allocation extent). Corrected typed graph and complete statement/carrier evidence support conditional reference conservation only under caller-contract.json. Allocation-bearing aggregate constants are deliberate overcoverage. Fresh independent review and root selection remain required.',
      'external_contracts_sha256':sha((D/'external-contracts.json').read_bytes()),'general_standard_library_classifier':False,
      'correction_contract_sha256':'b699930771cb7980b1ced76867c4d8a9760014be80c7fa63e4057145e6883341',
      'shell':{'fixed':4236953,'L_str_coefficient':4376,'substituted_candidate':4236953+4376*L},
      'whole_work_L_str_coefficient':67424,'whole_work_L_str_addition':67424*L,
      'counts':{'compiled_function_bodies':graph['compiled_function_bodies'],'selected_overapprox_bodies':len(graph['nodes']),'authored_and_callback_edges':len(graph['edges']),'named_authored_callback_edges':28,'named_authored_callback_sites':22,'standard_named_callback_frontiers':len(graph['standard_named_callbacks']),'external_frontiers':len(graph['external_frontier']),'external_sites':sum(len(x['sites']) for x in graph['external_frontier']),'direct_str_assignments':len(graph['source_str_assignments']),'carrier_forwarding_operations':sum(len(row['carrier_operations']) for row in graph['nodes'].values()),'compiled_literals':graph['literal_pool']['occurrences'],'compiled_unique_literals':len(graph['literal_pool']['values']),'compiled_allocations':graph['constant_allocations']['count'],'unique_allocation_ids':graph['constant_allocations']['unique_ids'],'unresolved_allocation_ids':graph['constant_allocations']['unresolved_ids']},
      'source_closure_conditional_on_exact_caller_contract':True,'scope_is_global_product_or_all_static_str':False,
      'genuinely_unclosed':['actual P0 caller and immutable fixture/compiler/session/executable selection remain unselected','alternate or injected caller strings require complete new provenance; L=5080 is not a global static-str theorem','remaining private/native work/storage allowances and complete binary correspondence remain separate','independent review of this candidate is required'],
      'accepted_bound':False,'whole_host_funding':False,'policy_or_work_grant':False,'runtime_or_native_test':False,'OTA_authority':False,'GA':False}
    save('graph.json',graph,check);save('provenance-trace.json',trace,check);save('caller-contract.json',exact_contract,check);save('failure-routes.json',failures,check);save('candidate.json',candidate,check);save('carrier-induction.json',full_induction,check)
    save('input-bindings.json',{'schema':1,'files':inputs,'source_revision':'frozen-source146-exacttree-'+SOURCE,'no_Git_operation':True},check)
    print(json.dumps({'status':candidate['status'],'L_str':L,**candidate['counts'],'accepted_bound':False,'grant':False},sort_keys=True))
    return candidate
if __name__=='__main__':main('--check' in sys.argv)
