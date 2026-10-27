#!/usr/bin/env python3
"""Bind independent observations, source excerpts and correction obligations."""
import collections,gzip,hashlib,json,pathlib,re
D=pathlib.Path(__file__).resolve().parent;R=D.parents[1];V=R/'verification';P=V/'swift-guarded-snapshot-string-provenance'
def sha(b):return hashlib.sha256(b).hexdigest()
def write(n,j):(D/n).write_text(json.dumps(j,indent=2,sort_keys=True)+'\n')
def main():
    a=json.loads((D/'analysis.json').read_text());g=json.loads((D/'typed-graph.json').read_text());p=json.loads((P/'graph.json').read_text())
    assert a['selected_bodies']==525 and set(p['nodes'])<=set(g['nodes'])
    assert not a['candidate_edges_not_independently_resolved'] and not a['MIR_body_disagreements']
    assert not a['indirect_calls'] and not a['unresolved_allocation_ids']
    assert a['allocation_count']==1958 and a['allocation_max']==5080 and a['literal_max_utf8']==92
    assert a['literal_occurrences']==3189 and a['literal_unique']==1397
    named=[x for x in a['named_callback_sites'] if x['callees']]
    assert len(named)==22 and sum(len(x['callees']) for x in named)==28
    assert a['authored_and_closure_edges']==1880 and len(g['edges'])==1908
    assert a['direct_str_assignments']==80 and a['carrier_operations']==1735
    assert len(g['external_sites'])==3209 and len({x['target'] for x in g['external_sites']})==1127
    assert all(x['incoming'] for x in a['direct_str_ports']) and len(a['direct_str_ports'])==9
    assert not [x for r in g['nodes'].values() for x in r['string_assignments'] if x['origin']=='unknown']
    assert not [x for r in g['nodes'].values() for x in r['sensitive_operations'] if any(t in x['statement'] for t in ('String','from_utf8','*const str','*mut str'))]
    omitted=[]
    for k,r in g['nodes'].items():
        if k not in p['nodes']:continue
        claimed={x['line'] for x in p['nodes'][k]['str_assignments']}
        omitted.extend(dict(x,function=k,function_name=r['name']) for x in r['string_assignments'] if x['line'] not in claimed)
    assert {(x['function'],x['line']) for x in omitted}=={('f0279',256),('f1035',203)}
    text=gzip.decompress((V/'swift-guarded-snapshot-loader-work-source146/whole-source146.mir.gz').read_bytes()).decode();bodies=text.split('\nfn ')
    allbody={}
    for chunk in bodies:
        body=chunk if chunk.startswith('fn ') else 'fn '+chunk
        if body.startswith('fn '):
            try:body=body[:body.index('\n}\n')+3]
            except ValueError:continue
            allbody[sha(body.encode())]=body
    newbodies={}
    for key in a['missing_candidate_bodies']:
        row=g['nodes'][key];newbodies[key]=dict(row)
        body=allbody[row['MIR_sha256']]
        (D/(key+'-omitted-body.mir.txt')).write_text(body)
        assert not row['string_assignments'] and not row['sensitive_operations']
    ref=json.loads((V/'swift-guarded-snapshot-loader-work-source146/source-reference-map.json').read_text())
    source={m['path']:m for m in ref['members']}
    excerpts=[]
    def excerpt(path,start,end,meaning):
        m=source[path];raw=(R/m['source']).read_bytes();assert sha(raw)==m['sha256']
        excerpts.append({'source':m['source'],'source146_path':path,'source_sha256':sha(raw),'start':start,'end':end,'meaning':meaning,'text':'\n'.join(raw.decode().splitlines()[start-1:end])})
    initial='src/experimental_swift_reactor/cache/initial_profile_v1.rs';control='src/experimental_swift_reactor/control.rs';loader='src/experimental_swift_reactor/retained_profile_loader_v1.rs'
    excerpt(initial,659,676,'Selected proof is consumed into snapshot scope, then construction and finish preserve the returned typed result.')
    excerpt(initial,703,746,'Frozen input contains Path references, byte claims and numeric budgets; host quote/reservation dispatches its closed FnOnce callback.')
    excerpt(initial,796,836,'Fresh Cancellation; exact loader-produced selected proof reaches the leaf unchanged; original failures and file owners remain held.')
    excerpt(control,216,230,'Public SwiftRunFailure.code is a caller-injectable static string on other routes; static lifetime supplies no length ceiling.')
    excerpt(control,255,282,'Fault::new and limit preserve the supplied code reference.')
    excerpt(control,657,687,'Selected shared core initializes first_failure and cleanup_invariant to None.')
    excerpt(control,983,1010,'RuntimeControl::fail returns the existing latch or copies fault.code into both new return and latch.')
    excerpt(control,1775,1799,'Cleanup forwards its code through Fault::new; cleanup observation updates do not replace code.')
    excerpt('src/experimental/reader.rs',1,34,'Reader owns bytes and numeric cursor fields; error forwards caller code through Meter.')
    excerpt('src/experimental/account.rs',90,128,'Swift Meter starts from numeric limits/observations; error copies the input code.')
    excerpt('src/experimental/validate.rs',21,36,'BodyState error preserves its code input through Meter.')
    excerpt('src/experimental/swift.rs',153,164,'Selected policy_identity returns fixed authored literal; Frozen branch is unreachable under sealed Swift policy.')
    excerpt('src/experimental/swift.rs',322,354,'Swift validation failure conversion copies raw.code rather than formatting fixture bytes.')
    excerpt('src/experimental/swift.rs',409,420,'The selected validator creates Policy::swift().')
    excerpt('src/experimental/policy.rs',132,139,'Policy::swift selects SwiftReactorExperimentV1.')
    excerpt(loader,24,37,'Five option_env compile identities are baked into the retained compiler constant pool.')
    excerpt(loader,136,190,'Private selected proof/provenance carriers and consuming conversion preserve original validated proof; no arbitrary public constructor is admitted.')
    excerpt('src/experimental_wasi/accounted.rs',432,432,'Omitted named callback forwards scalar WasiBudget and WasiGrants from context.')
    excerpt('src/experimental_wasi/mod.rs',638,638,'Omitted context body copies scalar budget and grants; no string producer.')
    write('source-semantic-review.json',{'schema':1,'excerpts':excerpts,'syntax_scan_alone_is_not_OTA_authority':True,'compiler_or_runtime_reran':False})
    write('missing-coverage.json',{'schema':1,'omitted_direct_str_assignments':omitted,'missing_bodies':newbodies,
        'named_callback_sites':named,'missing_transitive_regular_edges':a['independent_edges_missing_in_candidate'],
        'new_edges':29,'all_original_body_hashes_and_edges_reproduced':True,
        'body_semantics':{'f1605':'Copies AccountedWasi context reference into f1697 call; returns numeric budget/grants tuple.','f1697':'Reads existing context budget and grants fields into the returned tuple.',
          'f1899/f1900':'Two retained MIR bodies for enum Runtime constructor, moving existing SwiftRunFailure unchanged into its wrapper.',
          'f1927/f1928':'Two retained MIR bodies for enum Stop constructor, moving existing SnapshotStopV1 unchanged into its wrapper.',
          'f1590':'AccountedWasi::usage is already a candidate node through other calls; its 15 named-callback edges are absent.'}})
    correction={'schema':1,'status':'required-correction-contract-for-new-separate-frozen-packet','source_tree_sha256':'690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185',
        'frozen_candidate_must_remain_unchanged':True,'product_source_must_remain_unchanged':True,
        'requirements':[
          {'id':'R1','problem':'Local declarations are anchored to exactly four spaces, dropping nested-scope str locals.','required':'Parse all MIR local declaration scopes and preserve complete types including semicolons in arrays. Census assignments through every primitive str local and annotated nested carrier field.','expected_current':'80 direct str assignments; both f0279::_35 line256 and f1035::_29 line203 are retained preserving transfers.'},
          {'id':'R2','problem':'Only {closure@...} callbacks are expanded, missing named function items and enum constructors.','required':'Resolve every typed named Fn/FnMut/FnOnce argument, including standard predicates, exact authored bodies, repeated compiler enum constructor bodies and transitive calls. Unknown function items and indirect callees refuse.','expected_current':'525 bodies,1908 authored/closure/named edges,1127 external targets at3209sites; preserve all original1879edges, add28 named edges and f1605→f1697.'},
          {'id':'R3','problem':'Basename allowlist plus std/core/reference/generic receiver prefixes is broader than reviewed string-conservation contracts.','required':'Resolve authored implementations before external classification. Require reviewed standard namespace, receiver and trait identities and compatible typed argument/return contracts. Refuse unknown reference/generic traits, comparison-named custom traits, and unknown namespaces even with allowlisted method names.','expected_current':'All six independent adverse tests now pass as fail-closed expectations; new tests must cover an end-to-end unrecognized nested string carrier producer as well as isolated classifier cases.'},
          {'id':'R4','problem':'Origin proof and complete graph claims overstate actual retained coverage.','required':'Re-derive all original and newly discovered origins, direct/nested string ports, fields, incoming values, failures/latches, policy branch, callbacks, specializations, return/error/retirement/Drop paths from pinned typed MIR/source. Preserve the exact unmodified-loader/fresh-control/no-incoming-failure/no-policy-substitution/no-mutation contract.','expected_current':'The two extra transfers and six callback bodies preserve existing references/scalars; they do not supply evidence for arbitrary caller strings.'},
          {'id':'R5','problem':'Current14 passing tests did not expose the review findings.','required':'Retain original failed namespace-hardening attempts006/007 and this independent adverse failure receipt. Add deterministic regressions, rerun a read-only exact derivation and custody check, then freeze a new packet for root release and independent review.','expected_current':'Never rewrite or relabel original failures as passes; no compiler/runtime/native/UI/capture requirement is silently substituted.'}
        ],'origin_extent_may_remain_5080':True,'new_bound_or_whole_host_budget_selected':False,'root_selection_required':True}
    write('correction-contract.json',correction)
    review={'schema':1,'status':'return-frozen-candidate-for-correction','candidate_seal_sha256':'b228f62a0751e6d1b45e27edabe500cc5e52449db1d33ee59abca0f695b6fa2f',
       'candidate_accepted':False,'L_str_selected':False,'source_closure_selected':False,'root_selection_required':True,
       'custody_pass':True,'producer_14_tests_pass':True,'producer_derive_check_pass':True,
       'independent_fail_closed_tests':{'total':8,'pass':2,'fail':6,'failing_result_is_retained_finding':True},
       'independent_reconstruction':{'compiled_bodies':2009,'reachable_bodies':525,'all_edges':1908,'new_bodies':6,'new_edges':29,'direct_str_assignments':80,'new_preserving_transfers':2,'carrier_operations':1735,'external_frontiers':1127,'external_sites':3209,'direct_str_ports':9},
       'constant_extent':{'allocations':1958,'unique_allocation_ids':1464,'unresolved_allocation_ids':[],'max_allocation_bytes':5080,'literal_occurrences':3189,'unique_literals':1397,'max_literal_UTF8_bytes':92,
          'assessment':'Finite extent envelope supported for the frozen origin pool. The independently recovered additions preserve values, but the sealed candidate binder does not establish its claimed complete induction and is returned for correction.'},
       'formulas_checked':{'shell':26467033,'whole_L_str_addition':342513920,'whole_host_bound_selected':False},
       'authority':{'operational_grant':False,'actual_P0_binding':False,'binary_correspondence':False,'runtime':False,'native':False,'OTA':False,'GA':False},
       'limitations':['This independent reconstruction is an offline review of compiler data and matching frozen source, with no new compiler or product execution.',
          'Alternate callers can inject public SwiftRunFailure.code or lower Fault/Reader/Meter/cleanup/Frozen-policy strings of arbitrary lengths. Static lifetime/pointer width is not a bound.',
          'Actual root/caller/fixture/compiler/build/session/executable binding is not selected; the latent prepaid route is analyzed despite the current quote refusal.',
          'Path/OsStr and io::Error backing remain opaque native allowances; L_str does not close them.',
          'The remaining14-interface amendment is context only; no root whole expression or account is selected.',
          'Compiler, binary, runtime, native/device, UI/capture, OTA, immutable external FieldLog and GA gates remain pending.'],
       'independent_harness_history':'One retained initial parser assertion failed; local parser refinements and a recorder directory-allocation race were corrected with prior receipts/snapshots preserved. These are distinct from six current producer adverse-test failures.'}
    assert review['formulas_checked']['shell']==4236953+4376*5080 and review['formulas_checked']['whole_L_str_addition']==67424*5080
    write('review.json',review)
    print(json.dumps({'status':review['status'],'source_tree_sha256':correction['source_tree_sha256'],'independent_bodies':525,'new_edges':29,'new_transfers':2,'producer_adverse_failures':6,'selected':False},sort_keys=True))
if __name__=='__main__':main()
