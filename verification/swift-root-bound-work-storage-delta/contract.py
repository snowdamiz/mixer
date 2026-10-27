"""Finite, hand-reviewed delta contract; no executable product or price model."""

BASE = 'verification/swift-guarded-snapshot-actual-owner-rust-retirement-correction'
CAND = 'verification/swift-guarded-snapshot-root-result-lifetime-implementation'
REVIEW = 'verification/swift-guarded-snapshot-root-result-lifetime-independent/source-review.json'
BASE_TREE = 'c3a33b76eef6bf9ad86ef1cb0320e94bcefa5a0609ec1a30872a9d83371bd0db'
CAND_TREE = '91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f'
CAND_SEAL = '7efe39286257be85d0e91f4bdd80b6098d24d7d2f446dcdc2e8dd7adb0159fa4'
LOADER = 'src/experimental_swift_reactor/retained_profile_loader_v1.rs'
CACHE = 'src/experimental_swift_reactor/cache/initial_profile_v1.rs'
CHILD = 'src/experimental_swift_reactor/cache/initial_profile_v1/host_account_v1.rs'

# Positive obligations, never zero defaults. Existing means a dependency to rebind,
# not that an old numerical quote/layout is valid for this source tree.
OBLIGATIONS = {
 'W01': ('NEW', 'scope/root accessor work', 'Copy actual reservation root into both association inputs; accessor return; preserve sticky scope barrier.'),
 'W02': ('NEW', 'root-aware correlation and branch envelopes', 'Live/association checks plus new ptr::eq root check; both provenance outcomes; all Result/tuple wrapper construction/destructure/move/discriminant/return places.'),
 'W03': ('NEW', 'complete File facade and selected transitions', 'All File/Option/array reconstruction, retained-selection replacement/drop, opaque variant and bound selected conversions; both success and refusal paths.'),
 'W04': ('REBIND', 'fixed fixture raw leaf sequence', 'Existing cancellation clone, scope adoption, construct, outer, finish work now executes inside the fixed loader frame. Rebind changed arguments/returns and both leaf results; do not pay the same leaf invocation twice.'),
 'W05': ('NEW', 'fixture envelope assembly', 'Consume whole correlation and args; move/destructure every field and branch tuple; assemble complete final payload with original root.'),
 'W06': ('NEW', 'short primary and usage observation', 'Discriminants, shared reference construction, scalar usage copy, admitted observation branches; no payload cloning implied.'),
 'W07': ('NEW', 'admitted wrapper and dispatch capture delta', 'Root accessor before setup, both setup-refusal/loaded wrappers, FnOnce closure construction/moves/call, Result/Option child wrapping.'),
 'W08': ('REBIND', 'setup and loader dependent work', 'Existing actual File setup/partial-prefix cleanup, load, claims copy, time read and Cancellation construction remain required; changed result instantiations must be rebound.'),
 'W09': ('NEW', 'destruction and unwind instantiation', 'Normal and cleanup drops for all newly instantiated payloads, variants and children; stdlib File/io-error/Arc/Vec/proof destruction and unwind behavior remain unpriced inputs.'),
 'W10': ('REBIND', 'child account token protocol', 'Generic dispatch/inspect/destroy/Drop now instantiated with AdmittedFixtureOutcome<root>; token/release bodies remain child-only and need parent frame work. No acquisition release authority.'),
 'W11': ('REBIND', 'outer ordering', 'Observe admitted child, destroy complete child, release child-only token, retire acquisition owner, return scalar. Existing helper identity/preimage closure remains unchanged.'),
 'W12': ('NEW', 'private pair partition', 'RootBound tuple split constructs two complete wrappers sharing original root. Production source generic item; no product callsite, existing tests only. No zero-cost assumption for any later admitted use.'),
 'S01': ('NEW', 'association root representations', 'AdmittedLoaderCorrespondence/PrepaidCorrelationAttempt added root field; scope tuple/Result, args, temporaries, returns and closure-captured attempt need exact new layouts.'),
 'S02': ('NEW', 'generic bound representations', 'RootBound<T>, Result<RootBound<T>,RootBound<E>>, tuple partitions; root field/local/reference return representations, discriminants and temporaries. A reference is not backing storage.'),
 'S03': ('NEW', 'selected/correlation representations', 'RawSelectedBundle; private correlated/selected wrappers; RawCorrelationOutcome variants; opaque OwnedCorrelationOutcome; core/facade reconstruction locals and return envelopes.'),
 'S04': ('NEW', 'fixture frame and result representations', 'FixtureLeafArguments; RawFixturePrimary/RawFixtureResult; root-bound fixture result; branch tuples; scope/run/finish and return places. Re-evaluate simultaneous lifetimes, no sum of all MIR slots as a peak.'),
 'S05': ('NEW', 'admitted and child representations', 'AdmittedFixtureOutcome payload plus outer root; Loaded also owns nested bound root. Exact enum/Option/Result/PrepaidOwned instantiations and all return places need layouts, including setup refusal.'),
 'S06': ('NEW', 'actual dispatch closure representation', 'Exact closure fields are fixture by value, attempt by value, expected shared reference. Root reference in captured attempt changes closure; expected does not own its pointee. Measure actual anonymous closure, not proxy sum.'),
 'S07': ('NEW', 'short inspection representations', 'RootBoundPrimaryBorrow enum/shared refs, LoaderUsage scalar copies, Option shared child view, observation discriminants and parent token/return places.'),
 'S08': ('REBIND', 'carried payload backing lifetime', 'Original SelectedValidatedProfile proof/source backing, LoaderFailure/original io-error, three required File owners plus optional executable, usage and retained selection remain owned through envelope destruction. Moving/borrowing root does not fund these.'),
 'S09': ('REBIND', 'fixture/setup carried backing', 'Complete setup refusal owns original partial File prefix/io-error; loaded result owns rows/snapshot, Cancellation shared backing/clone, claims and either scope-failure/finish payload. Keep backing until final destruction, including cleanup edges.'),
 'S10': ('REBIND', 'root acquisition backing and sticky retirement', 'IR01 full acquisition charge stays retained after scope issue regardless of matched/refused/unused/destroyed/forgotten result. Raw ledger reference is neither that charge nor durable root custody. No useful joint retirement/shutdown proof.'),
 'S11': ('NEW', 'drop/unwind simultaneous storage', 'Retained inputs, variant partial moves, drop flags, cleanup blocks and generic child destruction places coexist until proven dead. No release on panic; compiled MIR is preparation for backing/layout review.'),
 'S12': ('REBIND', 'child token and parent storage', 'Child account and root are distinct. After complete payload destruction, DestroyedStorage carries only child reservation. Keep independently provisioned parent token/frame storage; token cannot release root acquisition charge.'),
}

# Every changed/new production type; unchanged semantic payload types are named
# explicitly where formatting/relocation appears in the source delta.
# (name, source, first, last, status, fields, obligations)
TYPES = [
 ('AdmittedLoaderCorrespondenceV1', LOADER,1963,1966,'CHANGED',['owner_data: owner shared provenance','association: u64','root: original-root shared ledger'],['W01','S01','S10']),
 ('PrepaidCorrelationAttemptV1',LOADER,1967,1970,'CHANGED',['expected: owner shared provenance','live: owner shared Cell<bool>','association: u64','root: original-root shared ledger'],['W01','S01','S10']),
 ('RootBoundV1',LOADER,2020,2020,'NEW',['payload: T (first field, dropped before root field)','root: original-root shared ledger'],['W02','S02','S08','S10','S11']),
 ('RawSelectedBundleV1',LOADER,2038,2040,'NEW',['selected: complete SelectedValidatedProfileV1','files: complete ReturnedLoaderFilesV1','usage: LoaderUsageV1'],['W03','S03','S08']),
 ('CorrelatedSelectedProfileV1',LOADER,2041,2041,'CHANGED',['0: complete RootBound<RawSelectedBundle>'],['W03','S03','S08']),
 ('RootBoundSelectedProfileV1',LOADER,2042,2042,'NEW',['0: complete RootBound<RawSelectedBundle>'],['W03','S03','S08']),
 ('OriginalCorrelationRefusalV1',LOADER,2046,2048,'UNCHANGED_FIELDS_RELOCATED',['kind: BootstrapFailureV1','retained_selection: Option<Result<SelectedValidatedProfileV1,LoaderFailureV1>>'],['W03','W09','S03','S08']),
 ('RawCorrelationOutcomeV1',LOADER,2049,2053,'NEW_SHAPE_FROM_OLD_ENUM',['Correlated: selected/files/usage','LoaderRefused: original LoaderFailure/files/usage','Refused: complete OriginalCorrelationRefusal/files/usage'],['W03','S03','S08']),
 ('OwnedCorrelationOutcomeV1',LOADER,2054,2054,'CHANGED',['0: complete RootBound<RawCorrelationOutcome>'],['W03','S03','S08','S10']),
 ('FixtureLeafArgumentsV1',LOADER,2057,2064,'NEW',['rows: File','snapshot: File','cancellation: Cancellation','claims: UnverifiedProfileDigestBytesV1','budget: SwiftRunBudget','started: Instant'],['W05','W08','S04','S09']),
 ('RawFixturePrimaryV1',LOADER,2066,2070,'NEW',['LoaderRefused: LoaderFailureV1','CorrelationRefused: OriginalCorrelationRefusalV1','Leaf: Result<SnapshotScopeFinishV1,SnapshotPreScopeFailureV1>'],['W05','W09','S04','S08','S09']),
 ('RawFixtureResultV1',LOADER,2072,2076,'NEW',['primary: RawFixturePrimaryV1','original_files: ReturnedLoaderFilesV1','original_loader_usage: LoaderUsageV1','rows: File','snapshot: File','cancellation_owner: Cancellation','claims_owner: UnverifiedProfileDigestBytesV1'],['W05','W09','S04','S08','S09','S11']),
 ('RootBoundFixtureOutcomeV1',LOADER,2078,2078,'NEW',['0: complete RootBound<RawFixtureResult>'],['W05','S04','S08','S09','S10']),
 ('RootBoundPrimaryBorrowV1',LOADER,2080,2084,'NEW',['LoaderRefused: short shared LoaderFailure','CorrelationRefused: short shared OriginalCorrelationRefusal','Leaf: short shared Result<SnapshotScopeFinish,SnapshotPreScopeFailure>'],['W06','S07']),
 ('AdmittedFixtureOutcomeV1',CACHE,845,848,'NEW',['payload: AdmittedFixturePayload<root>','root: original-root shared ledger'],['W07','W09','S05','S08','S09','S10']),
 ('AdmittedFixturePayloadV1',CACHE,849,852,'NEW',['SetupRefused: complete SetupOutcomeV1','Loaded: complete RootBoundFixtureOutcome<root>'],['W07','W09','S05','S08','S09']),
]

# Unique MIR function selector, source span, old unique function selector or None,
# classification, obligations. Constructors are added independently from exact
# producer roster and retain each compiler-emitted occurrence, even duplicates.
FUNCTIONS = [
 ('original_root_v1',LOADER,1971,1975,None,'NEW',['W01','S01','S02','S10']),
 ('correlation_scope_core_v1',LOADER,1976,1988,'correlation_scope_core_v1','CHANGED',['W01','S01','S10']),
 ('correlation_scope_v1',LOADER,2001,2005,'correlation_scope_v1','CHANGED',['W01','S01','S10']),
 ('into_result_v1',LOADER,2021,2030,None,'NEW',['W02','W09','S02','S03','S08','S11']),
 ('split_pair_v1',LOADER,2031,2037,None,'NEW_TEST_CALLS_ONLY',['W12','W09','S02','S08','S11']),
 ('into_selected_v1',LOADER,2043,2045,'into_selected_v1','CHANGED',['W03','S02','S03','S08']),
 ('primary_v1',LOADER,2086,2093,None,'NEW',['W06','S04','S07']),
 ('usage_v1',LOADER,2094,2094,None,'NEW',['W06','S04','S07']),
 ('run_fixture_once_v1',LOADER,2096,2136,None,'NEW_RELOCATED_LEAF_WORK',['W04','W05','W09','S02','S03','S04','S08','S09','S10','S11']),
 ('correlate_core_v1',LOADER,2146,2166,'correlate_core_v1','CHANGED',['W02','W09','S01','S02','S03','S08','S10','S11']),
 ('correlate_admitted_loader_v1',LOADER,2167,2190,'correlate_admitted_loader_v1','CHANGED',['W02','W03','W09','S01','S02','S03','S08','S10','S11']),
 ('run_one_admitted_fixture_v1',CACHE,853,862,'run_one_admitted_fixture_v1','CHANGED',['W07','W10','S01','S05','S06','S10','S12']),
 ('run_one_admitted_fixture_v1::{closure#0}',CACHE,861,861,'run_one_admitted_fixture_v1::{closure#0}','CHANGED_CAPTURE',['W07','W10','S01','S05','S06','S10']),
 ('run_prepaid_admitted_fixture_v1',CACHE,863,883,'run_prepaid_admitted_fixture_v1','CHANGED',['W04','W05','W07','W08','W09','S01','S03','S04','S05','S08','S09','S10','S11']),
 ('destroy_returned_admitted_fixture_v1',CACHE,884,889,'destroy_returned_fixture_v1','NEW_REBIND_GENERIC',['W09','W10','S05','S08','S09','S11','S12']),
 ('observe_admitted_originals_v1',CACHE,1080,1111,None,'NEW_REBIND_BORROWED_OBSERVER',['W06','W10','S05','S07','S08','S09']),
 ('consume_admitted_owner_once_v1',CACHE,1180,1224,'consume_admitted_owner_once_v1','CHANGED',['W06','W09','W10','W11','S01','S05','S07','S08','S09','S10','S11','S12']),
 ('dispatch_v1',CHILD,133,141,'dispatch_v1','UNCHANGED_GENERIC_NEW_T',['W07','W09','W10','S05','S06','S08','S09','S11','S12']),
 ('inspect_v1',CHILD,150,150,'inspect_v1','UNCHANGED_GENERIC_NEW_T',['W06','W10','S05','S07']),
 ('destroy_owned_v1',CHILD,151,163,'destroy_owned_v1','UNCHANGED_GENERIC_NEW_T',['W09','W10','S05','S08','S09','S11','S12']),
 ('drop(_1: &mut PrepaidOwnedV1',CHILD,168,175,'drop(_1: &mut PrepaidOwnedV1','UNCHANGED_GENERIC_NEW_T',['W09','W10','S05','S08','S09','S11','S12']),
 ('release_destroyed_v1',CHILD,179,190,'release_destroyed_v1','UNCHANGED_CHILD_ONLY',['W10','S07','S12']),
 ('release_after_retirement_v1',CACHE,774,776,'release_after_retirement_v1','UNCHANGED_CHILD_ONLY',['W10','S07','S12']),
 ('invoke_loaded_leaf_once_v1',CACHE,906,916,'invoke_loaded_leaf_once_v1','UNCHANGED_DONOR_FOR_RELOCATION',['W04','W09','S04','S08','S09','S11']),
]

REVIEW_CLASSES = [
 ('root references in correspondence, attempt and root-bound envelopes',['W01','S01','S02','S10']),
 ('RootBoundV1 Result/tuple destructures and branch return envelopes',['W02','W12','S02','S11']),
 ('RawSelectedBundleV1 and both private selected envelopes',['W03','S03','S08']),
 ('opaque correlation raw variants and File facade reconstruction locals',['W03','W09','S03','S08','S11']),
 ('FixtureLeafArgumentsV1, raw fixture primary/result, root-bound fixture result, primary view',['W05','W06','S04','S07','S09']),
 ('fixed synchronous frame payload/argument destructures, branch tuple, selected conversion and raw adoption/scope/run/finish places',['W04','W05','W09','S04','S08','S09','S11']),
 ('AdmittedFixtureOutcomeV1/payload/root, setup and loaded return places',['W07','W08','S05','S08','S09','S10']),
 ('run_one_admitted_fixture_v1 dispatch closure captures and separate child wrapper',['W07','W10','S05','S06','S12']),
 ('admitted inspection and child destruction/token argument/return places',['W06','W09','W10','S05','S07','S11','S12']),
]

LIMITS = {
 'source_inventory_preparation_only': True,
 'compiler_or_runtime_run_by_this_lane': False,
 'layout_or_price_accepted': False,
 'total_funding_accepted': False,
 'full_ownership_or_forgotten_root_funding_accepted': False,
 'OTA_FieldLog_GA_or_native_accepted': False,
 'no_previous_prices_or_layouts_reused': True,
}
