#!/usr/bin/env python3
"""Write/pin a source-only contract. No checker, model, product or child run."""
from pathlib import Path
import datetime
import hashlib
import json
import sys
import time

D=Path(__file__).resolve().parent;R=D.parents[1]
S=R/'verification/swift-guarded-snapshot-root-result-lifetime-implementation/source/vm'
C=S/'src/experimental_swift_reactor/cache/initial_profile_v1.rs'
L=S/'src/experimental_swift_reactor/retained_profile_loader_v1.rs'
H=S/'src/experimental_swift_reactor/cache/initial_profile_v1/host_account_v1.rs'
M=R/'verification/swift-root-bound-work-storage-delta-independent/candidate-selected-complete.mir'

def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(obj):return json.dumps(obj,sort_keys=True,separators=(',',':')).encode()
def row(path,base=R):
    assert path.is_file() and not path.is_symlink();raw=path.read_bytes()
    return {'path':path.relative_to(base).as_posix() if path.is_relative_to(base) else str(path),'bytes':len(raw),'sha256':sha(raw)}
def put(name,obj):
    with (D/name).open('x') as out:json.dump(obj,out,indent=2,sort_keys=True);out.write('\n')
def block(path,first,last):
    raw=b''.join(path.read_bytes().splitlines(keepends=True)[first-1:last])
    return {'path':path.relative_to(R).as_posix(),'first_line':first,'last_line':last,'bytes':len(raw),'sha256':sha(raw)}

def main():
    start=time.monotonic();assert not (D/'seal.json').exists()
    acceptance=R/'verification/swift-semantic-adapter-root-review/layout-accounting-join-acceptance.json'
    layout=R/'verification/swift-semantic-adapter-root-review/root-bound-layout-observation-acceptance.json'
    join=R/'verification/swift-root-bound-layout-accounting-join'
    inventory=R/'verification/swift-root-bound-work-storage-delta/delta-inventory.json'
    inv=json.loads(inventory.read_bytes());a=json.loads(acceptance.read_bytes())['acceptance']
    assert a['status']=='accepted-finite-source-data-layout-accounting-prerequisite'
    assert a['producer_seal']['sha256']=='8a3fd8e76d2826e53aecdf0399773d03c301e2610714d3ebb11f50b949ed0520'
    inputs=[acceptance,layout,join/'seal.json',join/'next-contract.json',join/'layout-crosswalk.json',join/'input-manifest.json']
    assert row(join/'seal.json')['sha256']==a['producer_seal']['sha256']
    assert row(join/'next-contract.json')['sha256']==a['next_contract']['sha256']
    inputs += [inventory,R/'verification/swift-root-bound-work-storage-delta/seal.json',
        R/'verification/swift-root-bound-work-storage-delta-independent/seal.json',M,
        S.parent.parent/'source-manifest.json',C,L,H,S/'src/experimental_swift_reactor/control.rs',S/'src/execute.rs']
    events=[
      ('E00','AcquisitionAlreadyReserved','Existing original ledger/owner','IR01 A.work/A.cleanup/A.storage already separate; no new child authority.','source-only dependency'),
      ('E01','ScopeIssue','A owner accessible','Set retirement barrier before attempt-taken check; success creates correspondence/attempt under exact original root. Reissue refuses and does not clear barrier.','source+accepted MIR'),
      ('E02','ParentReadyOrRefused','Scope issued','Current selector refuses RootPolicyPending. Conditional ready state requires separately provisioned P0/account; refusal creates no child.','source-only selector; outer MIR call context'),
      ('E03','QuoteReadyOrRefused','Conditional parent ready','Current selector refuses WholeQuotePending; conditional quote must cover all six positive work/storage terms. No closure or File on refusal.','source+entry MIR call order'),
      ('E04','ChildReserveOrRefused','Conditional complete quote','Checked work/storage additions and limits before one usage commit; refusal leaves usage/peak unchanged. Success commits work/current/peak and one reservation.','source+entry MIR call order'),
      ('E05','ClosureConstructAndConsume','One successful child reservation','Fixture/attempt move by value; expected is shared. Actual48-byte closure called once by consumed reservation. No second attempt.','source+accepted MIR+accepted layout'),
      ('E06','RootCapture','Entered prepaid body','Copy attempt.original_root before setup. Output uses this root even for foreign expected comparison. Reference does not own root backing.','source+accepted MIR'),
      ('E07','SetupRefused(k)','k in0..4; exact successful prefix','Retain k File owners plus original io::Error and slot array; return admitted setup-refused payload. No loader/cancellation/leaf follows.','source setup; retained caller MIR'),
      ('E08','SetupReadyOrInvariantRefused','Five setup stages completed','Ready owns source/build/session/rows/snapshot. Fallback preserves actual Option<File> array; no fabricated Ready.','source setup; retained caller MIR'),
      ('E09','LoaderReturn','Ready setup only','Retain complete selected proof or loader failure, source/build/session/optional executable and usage; rows/snapshot remain owned. Cancellation default and claims backing remain separate.','source+accepted MIR; backing capacities pending'),
      ('E10','Correlate','Complete carrier plus consumed attempt and borrowed expected','Live/association/root/provenance branches preserve complete selected/failure carrier and consumed attempt root; no File/proof extraction loses custody.','source+accepted MIR'),
      ('E11','FixedFramePrimary','Correlated raw outcome and all FixtureLeafArguments','LoaderRefused or CorrelationRefused bypass leaf. Correlated invokes existing scope/construct/outer/finish sequence once; both prescope failure and complete finish result retained.','source+accepted MIR'),
      ('E12','BoundReturnAndChildWrap','Prepaid body returned whole admitted outcome','Inner bound result plus outer admitted root enclosed; dispatch wraps T and reservation in Options, then returns complete13640-byte child. Physical call/return overlap unresolved.','source+accepted MIR+accepted layout'),
      ('E13','ObserveBeginEnd','Complete live child','Option<&admitted> and primary borrow view end before consuming child; scalar observation contains no extracted owned payload.','source+accepted MIR'),
      ('E14','DestroyBegin','Complete child consumed; no live shared view','Option<T>::take, drop complete T, then take reservation. Interrupted payload drop cannot pass token creation.','source+accepted MIR'),
      ('E15','WrapperDropComplete','Payload drop returned; reservation taken','drop emptied self; only after return construct child-only DestroyedStorage token.','source+accepted MIR'),
      ('E16','TokenReturnSomeOrNone','Destroy frame returned','Some contains child reservation only; None grants no release. Parent return/token storage already provisioned in P0.','source+accepted MIR'),
      ('E17','P0ChildRelease','One normal Some token in P0','Checked subtract child reserved storage once; work/peak unchanged. Underflow retains charge. Never subtract original acquisition.','source+accepted MIR'),
      ('E18','OrdinaryChildDrop','Returned child not explicitly destroyed','Take/drop payload; no release call. Implicit reservation field drop refunds nothing.','source+accepted MIR'),
      ('E19','Unwind(site)','Finite site set in prospective-tests','Existing cleanup edges may destroy owned prefixes/temporaries; no token on incomplete destroy, no work/storage refund. stdlib/drop-glue completion and double-panic abort not qualified.','source+accepted MIR edges; runtime completion pending'),
      ('E20','ForgetChild','Returned complete child','No payload/wrapper Drop or token; retain child/backing obligation. Does not prove durable root custody after root ledger ends.','Rust ownership contract/source boundary; no runtime evidence'),
      ('E21','RootRetireRetained','Any scope issue, including refusal/drop/forget','Sticky IR01 check returns Retained before cleanup. Outer drops retained original owner; original storage charge is not refunded. Physical cleanup/healthy close and durable funding are separate.','source-only root-retirement body; accepted IR01 dependency'),
    ]
    put('events.json',{'schema':1,'status':'CONDITIONAL_SOURCE_CONTRACT_NOT_EXECUTED','events':[{'id':i,'event':n,'precondition':p,'effect':e,'evidence':v} for i,n,p,e,v in events],
      'setup_prefixes':[{'stage':k,'owned_file_indices':list(range(k)),'owned_mask':(1<<k)-1,'attempted_role':['source','build','session','rows','snapshot'][k]} for k in range(5)],
      'leaf_invocations_per_fixed_frame':'0 on loader/correlation refusal;1 on correlated path, with prescope failure or complete finish result; not dynamic work price',
      'forbidden_events':['retry setup/dispatch','token on payload-drop unwind','ordinary Drop refund','forget refund','child token refunds acquisition','root Complete after scope','selected production grant from model evidence'],
      'current_production_dispatch_reachable':False})
    regions=[
      ('A0','Original acquisition identity','BootstrapLedgerV1;AcquisitionReservationV1;PrepaidInputOwnerV1;AdmittedImmutableOwnerV1','Acquisition','Before scope until original owner retirement/drop; ledger charge remains sticky afterward','A-input13,A-path10,A-claims-error','No child/P0 token authority; accessible root reference is not durable funding.'),
      ('P0','Preexisting parent/bookkeeping','TrustedRootPolicyV1;TrustedHostAccountV1;ReviewedFixtureBindingV1;PreexistingImmutableBindingV1;AdmittedOuterResultV1','P0','Before P1 through child destruction/token release/final scalar return','P0-binding/preimages/paths/claims;account/quote/token/frame','Not funded after the fact from child storage; concrete capacities/frames unpriced.'),
      ('V1','Scope pair','(AdmittedLoaderCorrespondenceV1,PrepaidCorrelationAttemptV1)','P0 pre-child caller coverage','Scope result until semantic split/moves and last borrowed expected view','Borrowed original root/provenance only','56 bytes includes24+32; physical parent/capture overlap unproved;cannot borrow a not-yet-reserved child grant.'),
      ('V2','Actual dispatch closure','Exact run_one_admitted_fixture_v1 closure','Child dispatch component with caller coverage retained','Closure construct through FnOnce consumption/call cleanup','Contains fixture+attempt;borrows expected and P0 binding','48/align8; do not add captured attempt32 again or assign this to the1187-line closure.'),
      ('V3','In-flight fixed frame','LoaderCarrierCore<File>;RootBound variants;RawCorrelationOutcome;FixtureLeafArguments;RawFixturePrimary;RawFixtureResult;RootBoundFixtureOutcome','Existing P1/P2/P3/P4/P5 coverage, no duplicate leaf','Setup ready/loader through complete admitted return or unwind','F0..F4,F-exec,ProofChild,ErrorChild,Cancel1,ClaimsChild','Moves preserve resource IDs; call/return/branch/drop-slot physical overlap remains unresolved.'),
      ('V4','Returned complete child','PrepaidOwnedV1<AdmittedFixtureOutcomeV1>','Child P5 with existing earlier components retained','ChildWrap through explicit destroy, ordinary Drop, unwind or unreleased forget','Contains13624 admitted,13616 payload and nested bound result','13640/align8 outer extent once; nested fields not separate allocations.'),
      ('V5','Short views','Option<&AdmittedFixtureOutcomeV1>;RootBoundPrimaryBorrowV1;LoaderUsageV1 scalar copy','P0 observation frame plus retained child','ObserveBegin..ObserveEnd','Borrows V4;never owns original payload','Observed8/16 only for exact views; other scalar/frame widths remain missing.'),
      ('V6','Destroy frame and moved payload','PrepaidOwned<T> argument;Option<T>::take temp;T drop argument;emptied self','Retained child P5 work and separately provisioned P0 caller/frame','DestroyBegin through returned token or unwind','Same complete payload/backing transferred until final destruction','Cannot add all argument/take/drop slots or assume physical alias; T-drop completion required.'),
      ('V7','Returned child token','DestroyedStorageV1;Option<DestroyedStorageV1>;ReservationV1;release args/return','P0','After payload+wrapper destroy returned through checked child release','Child reservation/account reference only;no File/proof/payload','Standalone token/Reservation/parent frame layout unobserved;16-byte wrapper difference is not its quote.'),
    ]
    backing=[
      ('A-input13','IR01 retained identity inputs','13 ActualInputSlot/RetainedIdentityFile owners and optional immutable bodies','Acquisition','Semantic original owner destruction/retirement; sticky charge independently retained','Not deduplicated with newly opened child Files merely by path/inode.'),
      ('A-path10','IR01 native/retained paths','5 native+5 retained ImmutableOwnedBytes slots;claims/original errors separate','Acquisition','Original owner destruction/retirement; complete capacity bounds required','Reference/borrow fields do not replace these capacities.'),
      ('F0..F4','Child setup owners','Successful File::open/create_new instances for source,build,session,rows,snapshot','Child P1 setup/P5 retention','Exact prefix on refusal, otherwise move same IDs through returned child until destruction','Five successful ownership instances; no fresh ID on move;healthy OS close not source-proven.'),
      ('F-exec','Optional executable owner','ReturnedLoaderFilesV1.executable','Child loader/P5','Loader result through final payload destruction','Capacity/resource bound unknown; optional absence must be branch-backed, not default zero.'),
      ('ProofChild','Loader/leaf original proof and source backing','SelectedValidatedProfileV1 -> selected body/scope/run/finish or retained refusal','Child P1 loader/P4/P5','Follow actual owning result/drop graph, including failed cleanup','Opaque allocation graph/capacities unresolved; no pointer-layout funding.'),
      ('ErrorChild','Original failure backing','Setup io::Error,LoaderFailureV1,OriginalCorrelationRefusalV1 and leaf failure/retirement records','Child producing component/P5','Retained in exact typed branch through complete final destruction','Do not format/coerce error into scalar or assume boxed/dynamic capacity zero.'),
      ('Cancel1','One shared cancellation allocation','Cancellation(Arc<AtomicBool>) default;clone consumed by scope;owner retained in raw result','Child P1/P2/P4/P5','Until last actual Arc-owning instance destroyed;clone shares same backing ID','Requested backing layout is a qualified-toolchain model, not allocator/RSS or capacity receipt.'),
      ('ClaimsChild','Copied claims and rows/snapshot retained state','UnverifiedProfileDigestBytesV1 and F3/F4 owners','Child P2/P4/P5','Arguments through full result destruction','Fixed claims inline is contained; file/OS/output capacity is not inferred from claims or product caps.'),
    ]
    put('regions.json',{'schema':1,'regions':[{'id':i,'role':n,'current_types':t,'funding':f,'semantic_interval':iv,'backing_or_containment':b,'overlap_limit':o} for i,n,t,f,iv,b,o in regions],
      'backing_identities':[{'id':i,'name':n,'owners':o,'funding':f,'end_condition':e,'capacity_limit':l} for i,n,o,f,e,l in backing],
      'physical_region_map_complete':False,'numeric_grant':None,'critical_possible_overlaps':['scope pair versus closure argument/capture buffers','closure argument versus callee/return admitted result','admitted return/Option<T>/child construction buffers','full child versus destroy argument/taken payload/drop argument/emptied self','payload-drop/unwind temporaries versus P0 token return frame'],
      'source_only_proofs':['nested containment','semantic transfers retain backing identity','borrow ends before consuming outer child','payload drop returns before token construction','original root and child reservation are distinct'],
      'not_source_proofs':['physical alias/disjointness or stack peak','actual allocator/File/OS capacity','drop-glue healthy completion','durable forgotten-root funding']})
    quote=[
      ('A-operation','Original acquisition work','acquisition_work plus per-effect operation_left','metadata,offset,allocation,read,hash_per_byte,path_per_byte,correlation and correlation_storage admission debit','Original ledger/root;never child/P0 refund','No numeric quote selected; preserve existing identity acquisition/validation/correlation coverage.'),
      ('A-cleanup','Original acquisition cleanup','cleanup_work;cleanup_left;bridge.retirement','Retirement of up to13 owned slots,10 path backing slots,actual claims/errors and final carrier on unissued-scope complete route','Original ledger/root','After scope sticky return happens before any of these effects; do not count child destruction as this completion.'),
      ('A-storage','Original acquisition storage','peak_storage;original_storage;storage_left','Owned input bodies/path backings/claims/original errors,acquisition caller/result/refusal overlap and policy capacities','Original ledger/root','Full charge remains after any scope issue,including unused/refused/dropped/forgotten results.'),
      ('P0','Preexisting parent allocation','TrustedRootPolicyV1.p0_preexisting_allocation','Root policy/account/quote variables,immutable paths/claims/identity preimages,outer caller/control/result/observation,scope pair,late destroy/token/release args/return bookkeeping','Separately provisioned before P1','No child-grant borrowing; standalone token and parent physical storage remain missing.'),
      ('C0','P1 setup','Child component0','Five setup attempts/partial prefix/original io errors;create_new outputs;all setup ownership retained','Child complete quote','No retry or truncate;refusal retains original prefix;P5 destruction coverage must rebind existing term,not duplicate.'),
      ('C1','P1 loader','Child component1','Actual loader/read/hash/provenance/source and separately priced original validation;complete selected/failure/File results and root-aware correlation/facade transfers','Child complete quote','Original validator separate from product VM budget;retain current callee evidence and backing limits. Do not duplicate original acquisition admission correlation debit.'),
      ('C2','P2 arguments','Child component2','FixtureLeafArguments rows/snapshot/cancellation/claims/budget/Instant and post-reservation fixture/attempt/expected closure argument/capture construction/transfers','Child complete quote','Proposed incremental assignment;contained fields/moves do not mint new backing or erase old quote terms. Quote/reserve work before commit stays P0.'),
      ('C3','P3 pre-store shell','Child component3','Current authentic adoption/scope/shell caller/control/borrow/return setup before selected route','Child complete quote','Keep existing dependencies and generic File/stdlib interfaces;no pointer-only substitution.'),
      ('C4','P4 selected route','Child component4','One relocated fixed scope/construct/outer/finish sequence with retained original VM/product/callee work and new root-bound envelopes','Child complete quote','Do not add old helper plus fixed frame as two leaf invocations;do not borrow product limits to fund host work.'),
      ('C5','P5 originals and destruction','Child component5','Complete setup or loaded payload/original diagnostics and File/proof/error/cancellation/claims retention;normal and cleanup/drop work through full child destruction','Child complete quote','Parent token/release frame stays P0;ordinary Drop/unwind returns no refund;File Drop is not healthy-close evidence.'),
    ]
    put('quote-partitions.json',{'schema':1,'components':[{'id':i,'name':n,'source_field_or_component':s,'retained_coverage':c,'funding_identity':f,'rule':r} for i,n,s,c,f,r in quote],
      'existing_child_quote_rule':'Exactly six positive work/storage CostV1 components;checked sums in ReviewedWholeQuoteV1::checked_components_v1. Preserve this source until a reviewed pricing amendment;model does not replace it with global peak.',
      'required_model_output':'Coverage assessment against every retained term plus missing-evidence list;no numeric work price or storage grant.',
      'incremental_assignment_proposal':{'P0':'Scope pair/sticky-issue caller work before child reserve;quote/account/reserve bookkeeping;late destroy caller,token,release,outer scalar bookkeeping.',
        'C0':'Root accessor before setup and root-bearing setup-refusal construction,plus existing setup work.',
        'C1':'New root-aware correlation/complete File facade and selected/refusal envelope transfers,plus existing loader/validation once.',
        'C2':'Post-reservation actual closure capture/argument construction and FixtureLeafArguments production/transfers.',
        'C3':'Existing pre-store adoption/shell call contexts,rebinding changed arguments/returns without duplicate callee work.',
        'C4':'One fixed consuming leaf sequence and its new branch/final envelopes;old helper relocation is not another leaf.',
        'C5':'Complete returned payload/owner retention and destruction,including new admitted nested-root shapes and normal/unwind drops.',
        'physical_attribution_gate':'These are proposed work/ownership coverage labels,not proof that caller/return/token regions are disjoint. Before prices,choose one physical charge owner for every extent and explicitly reconcile existing P0/C5 return-carrier coverage;do not charge complete nested aggregates twice.'},
      'forbidden_deductions':['duplicate relocated leaf charge','omitted P0 token/frame','child refund of acquisition','missing capacity defaults zero','root reference substitutes original backing','existing overlapping conservative terms silently discarded']})
    tests=[
      ('T01','Current selectors/refusals','Parent/quote refusal and each checked reserve refusal has no child/closure/setup effect or partial accounting commit.'),
      ('T02','Single normal trace','One scope,one reservation,one closure call,whole returned child,shared view ends,complete destroy,one P0 child token release,sticky root remains.'),
      ('T03','Five partial setup cases','For k=0..4 retain exactly prefix mask(1<<k)-1 and original error;no loader/leaf or retry;all original prefix identities remain through child destruction.'),
      ('T04','Invariant setup branch','Preserve actual five Option<File> slots and refuse fabricated Ready;do not assert real-world reachability.'),
      ('T05','All correlation/leaf branches','LoaderRefused,CorrelationRefused,Leaf(Err prescope),Leaf(Ok complete finish),including foreign expected root and failure-carrying finish.'),
      ('T06','Relocated leaf identity','0 leaf calls on loader/correlation refusal;1 on correlated route;old donor is not a second invocation or a duplicate quote term.'),
      ('T07','Payload and child nesting','13640 contains13624/13616;48 closure contains attempt;56 pair contains24+32;contained extents never create distinct backing charges.'),
      ('T08','Transfer with unknown physical buffers','Semantic move preserves resource IDs but gives IncompleteEvidence for unproven source/destination overlap;no allocation inference.'),
      ('T09','Union arithmetic','Synthetic evidenced arena intervals[0,48),[32,80) union80,not96 or48;contained[8,16) adds0;disjoint arenas require evidence.'),
      ('T10','Capacity/overflow','Unknown capacity,offset+capacity overflow,union sum overflow,invalid alignment,undersized extent,duplicate conflicting IDs and insufficient limit refuse without partial state changes.'),
      ('T11','Shared cancellation backing','Default backing plus clone use one BackingId with two owners;do not free on first owner drop;missing final-owner evidence refuses completion.'),
      ('T12','Shared views','Borrow8/16-byte views never own or release pointee backing;destroy while view live refuses;other closure and aggregate-to-reference substitutions refuse.'),
      ('T13','Explicit destruction order','Token cannot exist before payload drop and empty wrapper drop return;Some token consumed once;None permits no release/retry.'),
      ('T14','Ordinary Drop','Payload destruction may complete but child storage/work/peak not refunded and no token appears.'),
      ('T15','Unwind matrix','Inject abstract unwind only at retained call/setup/loader/correlation/leaf/drop cleanup edges;incomplete destroy never yields token;retained charges and unresolved backing persist. Reject an invented unwind edge between pure capture field moves.'),
      ('T16','Forgotten child','No Drop/token/refund;leaked backing obligation remains and root retirement stays sticky;root-ledger death cannot be certified as durable funding.'),
      ('T17','Funding identities','Child token cannot reduce acquisition ledger;P0 token/frame cannot be paid out of released child;duplicate token/underflow remains charged.'),
      ('T18','Quote completeness','Omitting A,P0 or anyC0..C5 term refuses;0-byte type uplift never makes a work/storage component0;product limits do not fund host work.'),
      ('T19','Source/config evidence binding','CurrentShape binds exact accepted input rows;wrong source/target/cfg or generic normalizer match refuses;synthetic evidence cannot authorize production.'),
      ('T20','Normal versus exceptional peak','Take checked maximum over all evidenced event segments including refusal/unwind,not only happy-path boundary values;unresolved segments return incomplete.'),
    ]
    put('prospective-tests.json',{'schema':1,'status':'NOT_IMPLEMENTED_NOT_EXECUTED','tests':[{'id':i,'family':n,'expected':e} for i,n,e in tests],
      'first_future_scope':'Pure isolated model host tests only;no engine/File/allocator/native execution. Separate root-selected command and bounded receipt required.',
      'does_not_qualify':['actual physical regions','allocator/OS capacities','monomorphized destructor completion','root funding','native/FieldLog/OTA/GA']})
    selectors=['correlation_scope_core_v1','correlation_scope_v1','run_one_admitted_fixture_v1','run_one_admitted_fixture_v1::{closure#0}',
      'run_prepaid_admitted_fixture_v1','correlate_core_v1','correlate_admitted_loader_v1','run_fixture_once_v1','observe_admitted_originals_v1',
      'dispatch_v1','inspect_v1','destroy_owned_v1','drop(_1: &mut PrepaidOwnedV1','destroy_returned_admitted_fixture_v1','release_destroyed_v1','release_after_retirement_v1','consume_admitted_owner_once_v1']
    methods=[]
    for selector in selectors:
        fn=next(f for f in inv['functions_and_constructor_occurrences'] if f['selector']==selector)
        methods.append({'selector':selector,'source':fn['source'],'accepted_MIR_item':fn['MIR'],'scope':'Ownership/control-flow evidence,not physical-region or work price.'})
    mir_lines=M.read_bytes().splitlines(keepends=True);examples=[]
    for n in [221,240,248,310,329,355,367,395,397,409,413,441,459,485,689,725,788,816,851]:
        raw=mir_lines[n-1];examples.append({'retained_file_line':n,'raw_line_sha256':sha(raw),'code':raw.decode().split('//',1)[0].strip()})
    source_blocks=[('root quote+reservations',L,1456,1525),('original backing owners',L,1532,1572),('prepublication correlation debit',L,1909,1937),
      ('sticky scope and association',L,1963,1988),('bound ownership and fixed frame',L,2020,2136),('correlation complete carrier',L,2146,2190),
      ('root sticky retirement',L,2192,2259),('child complete quote/account/reserve',H,1,126),('child dispatch/destroy/drop/token',H,128,192),
      ('setup source-only',C,719,798),('admitted wrapper/dispatch/prepaid/destruction',C,845,889),('shared observation',C,1080,1111),
      ('outer order',C,1180,1224),('leaf explicit finish dependency',S/'src/experimental_swift_reactor/control.rs',1905,2036),('Cancellation shared backing declaration',S/'src/execute.rs',1,34)]
    put('source-frontier.json',{'schema':1,'selected_methods':methods,'source_blocks':[{'name':n,**block(p,f,l)} for n,p,f,l in source_blocks],
      'MIR_file':row(M),'critical_MIR_rows':examples,'source_only_dependencies':['setup_files_once_v1 implementation','root reserve/admission/retirement internals','selected parent/quote/root policy bodies','SnapshotRun::finish and Cancellation backing dependencies'],
      'evidence_limits':'Accepted selected MIR establishes typed moves/drop/unwind edges only. No replay,physical frame reconstruction,full drop-glue/capacity or runtime completion proof.'})
    put('input-manifest.json',{'schema':1,'inputs':[row(p) for p in inputs],'source146_tree':inv['candidate_source146_tree'],
      'root_join_acceptance':row(acceptance),'next_contract':row(join/'next-contract.json'),'root_layout_acceptance':row(layout),
      'source_identity_scope':'Five used original source files plus accepted inventory/selected MIR and root receipts;not a new full source/MIR checker or physical allocation proof.'})
    accepted_inputs=json.loads((join/'input-manifest.json').read_bytes())['inputs']
    accepted_mir=next(item for item in accepted_inputs if item['path']==M.relative_to(R).as_posix())
    assert row(M)['sha256']==accepted_mir['sha256']
    manifest=json.loads((S.parent.parent/'source-manifest.json').read_bytes())
    for path in [C,L,H,S/'src/experimental_swift_reactor/control.rs',S/'src/execute.rs']:
        expected=next(item for item in manifest['members'] if item['path']==path.relative_to(S).as_posix())
        actual=row(path);assert actual['bytes']==expected['bytes'] and actual['sha256']==expected['sha256']
    assert time.monotonic()-start<55
    summary={'source_contract_written':True,'events':len(events),'ownership_regions':len(regions),'quote_partitions':len(quote),'prospective_test_families':len(tests),'tests_executed':0,'model_implemented':False}
    (D/'stdout').write_text(json.dumps(summary,sort_keys=True)+'\n');(D/'stderr').write_bytes(b'')
    put('receipt.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'command':[str(Path(sys.executable).resolve()),'-B',str(Path(__file__).resolve())],'cwd':str(R),'python':sys.version,'python_tool':row(Path(sys.executable).resolve()),
      'writer_source':row(Path(__file__).resolve()),'input_manifest':row(D/'input-manifest.json'),
      'outputs':[row(D/'stdout'),row(D/'stderr')],
      'source146_tree':inv['candidate_source146_tree'],'elapsed_seconds':time.monotonic()-start,'wall_ceiling_seconds':55,
      'executed':'Pinned source/retained-MIR reading,JSON/document evidence writing and SHA256 only;no checker or prospective model/test execution.',
      'model_implemented':False,'tests_executed':0,'compiler_parser_runtime_child_checkers_version_commands':0,
      'new_process_inventory_native_UI_capture_network_devices':False,'price_grant_funding_authorized':False,'new_implementation_proposed_files':2})
    members=[row(p,D) for p in sorted(D.iterdir()) if p.is_file() and p.name!='seal.json']
    seal={'schema':1,'status':'FROZEN_SOURCE_ONLY_DISPATCH_LIFETIME_AND_MINIMUM_MODEL_CONTRACT_PROPOSAL',
      'members':members,'member_count':len(members),'member_bytes':sum(r['bytes'] for r in members),'tree_sha256':sha(canonical(members)),
      'root_join_acceptance_sha256':row(acceptance)['sha256'],'source146_tree':inv['candidate_source146_tree'],
      'events':len(events),'ownership_regions':len(regions),'backing_groups':len(backing),'quote_partitions':len(quote),'prospective_test_families':len(tests),
      'new_implementation_files_proposed':2,'implementation_tests_compiler_runtime_or_checker_executed':False,'numeric_grant_selected':False,
      'root_funding_full_ownership_native_FieldLog_OTA_GA_accepted':False}
    put('seal.json',seal)
    print(json.dumps({'status':seal['status'],'members':len(members),'seal_sha256':sha((D/'seal.json').read_bytes()),'tree_sha256':seal['tree_sha256'],
      'events':len(events),'quote_partitions':len(quote),'prospective_tests':len(tests),'new_model_implemented':False,'numeric_grant_selected':False}))
if __name__=='__main__':main()
