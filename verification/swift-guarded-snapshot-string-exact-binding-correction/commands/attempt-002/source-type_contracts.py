"""Finite source146 compiler spelling aliases and structural type equations.

Aliases enumerate exact path tokens. There is no basename stripping, suffix
comparison, arbitrary receiver binding or namespace-wide replacement. Generic
bindings are consistent across all arguments and the result, then frozen as
exact per-target signatures by prepare_authored.py.
"""
import re
from mir_graph import require,split_operands
ALIASES={}
def group(module,names,short=True,prefix=None):
    for name in names.split():
        canonical=module+'::'+name
        if short:ALIASES[name]=canonical
        if prefix:ALIASES[prefix+'::'+name]=canonical

group('std::option','Option');group('std::result','Result');group('std::vec','Vec')
group('std::time','Duration Instant');group('std::alloc','Layout');group('std::sync::atomic','Atomic')
group('experimental::account','BodyObservations SwiftControl')
group('experimental::validate','BodyState')
group('experimental::metadata','Export Function Global Import Segment Signature SwiftDeclaration')
group('experimental::cache::decode','Patch')
group('experimental_wasi','WasiContext WasiBudget WasiGrants')
group('experimental_wasi::accounted','AccountedWasi',prefix='accounted')
group('experimental_wasi::descriptor','WasiFunction ResolveError',prefix='descriptor')
group('experimental::descriptors','FunctionSpanView',False,'descriptors')
group('experimental::swift','ValidatedSwiftReactor SwiftValidationFailure SwiftValidationBudget SwiftValidationUsage SwiftReactorObservations',prefix='swift')
group('experimental_swift_reactor::control','AdoptedProof Cursor Fault Live ReservationTicket RuntimeControl SwiftReservationCategory SwiftReservationUsage SwiftReservations SwiftRunBudget SwiftRunFailure SwiftRunFailureKind SwiftRunResource SwiftRunUsage SwiftLiveUsage SwiftCleanupInvariant Work',False,'control')
group('experimental_swift_reactor::control','SnapshotRunV1 SnapshotScopeBorrowV1 SnapshotScopeFinishV1 SnapshotScopeV1 SnapshotStopV1 SnapshotPreScopeFailureV1 SnapshotAdmissionErrorV1')
group('experimental_swift_reactor::retained_profile_loader_v1','AdoptionBodyV1 LoaderProvenanceV1 ReturnedLoaderFilesV1 FileIdentityV1 LoaderOutcomeV1 SelectedSnapshotBodyV1 SelectedValidatedProfileV1 BuildView SessionView Section',prefix='retained_profile_loader_v1')
group('experimental_swift_reactor::retained_profile_loader_v1','Bytes LoaderFailureV1 LoaderUsageV1 Refusal Role',False,'retained_profile_loader_v1')
group('experimental::swift::snapshot_encoder_v2','SnapshotBlockV2 SnapshotCursorV2 SnapshotViewV2 SpanCheckV2 SnapshotEncodeErrorV2')
group('experimental_swift_reactor::cache::initial_profile_v1','SnapshotAccessV1 SnapshotBranchV1 SnapshotPhaseStorageV1 SnapshotAttemptV1 SnapshotOuterV1 SnapshotPlanV1 SnapshotShapeV1 SnapshotWriterV1 SnapshotCauseV1 SnapshotExportErrorV1 SnapshotPrimaryRetirementV1')
group('experimental_swift_reactor::cache::initial_profile_v1','InitialProfileBorrowV1 SelectedInitialProfileV1 SelectedLocalStructureV1 UnverifiedProfileDigestBytesV1 ProfileHeaderErrorV1 InitialProfileConstructionOutcomeV1 InitialProfileScalarsV1 ProfileAdmissionFailureV1 UnverifiedProfileHeaderV1',False,'initial_profile_v1')
group('experimental_swift_reactor::diagnostic_profile','ProfileRowV1 ProfileRowsObservationV1 ProfileAdapterErrorV1',prefix='diagnostic_profile')
group('experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1','ReviewedFixtureBindingV1 FrozenFixtureV1 OwnedFixtureOutcomeV1 SetupOutcomeV1')
group('experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1::host_account_v1','PrepaidOwnedV1 DestroyedStorageV1 ReservationV1 RefusalV1 ReviewedWholeQuoteV1 TrustedHostAccountV1')
PATH=re.compile(r'(?<![\w:])[A-Za-z_]\w*(?:::[A-Za-z_]\w*)*')

# These are the caller-contract specializations, not arbitrary trait impls.
# Only exact tokens below change; Foreign, foreign::MeterControl, etc. survive
# unchanged and cannot match any declaration or finite target contract.
SPECIALIZATIONS={
    'B':"experimental_swift_reactor::cache::initial_profile_v1::SnapshotBranchV1<'_>",
    'C':'experimental::account::SwiftControl',
    'D':'experimental::metadata::SwiftDeclaration',
    'impl MeterControl':'experimental::account::SwiftControl',
    'impl metadata::Declaration':'experimental::metadata::SwiftDeclaration',
    '<B as ClosedBranchV1>::Access': 'experimental_swift_reactor::cache::initial_profile_v1::SnapshotAccessV1',
    '<B as ClosedBranchV1>::Storage':'experimental_swift_reactor::cache::initial_profile_v1::SnapshotPhaseStorageV1',
    '<B as ClosedBranchV1>::Attempt':'experimental_swift_reactor::cache::initial_profile_v1::SnapshotAttemptV1',
    '<B as ClosedBranchV1>::Output':'experimental_swift_reactor::cache::initial_profile_v1::SnapshotOuterV1',
    '<B as experimental_swift_reactor::cache::initial_profile_v1::ClosedBranchV1>::Access':'experimental_swift_reactor::cache::initial_profile_v1::SnapshotAccessV1',
    '<B as experimental_swift_reactor::cache::initial_profile_v1::ClosedBranchV1>::Storage':'experimental_swift_reactor::cache::initial_profile_v1::SnapshotPhaseStorageV1',
    '<B as experimental_swift_reactor::cache::initial_profile_v1::ClosedBranchV1>::Attempt':'experimental_swift_reactor::cache::initial_profile_v1::SnapshotAttemptV1',
    '<B as experimental_swift_reactor::cache::initial_profile_v1::ClosedBranchV1>::Output':'experimental_swift_reactor::cache::initial_profile_v1::SnapshotOuterV1',
    '<P as ClosedAdoptionV1>::Failure':'experimental_swift_reactor::control::SnapshotPreScopeFailureV1',
    '<P as experimental_swift_reactor::control::ClosedAdoptionV1>::Failure':'experimental_swift_reactor::control::SnapshotPreScopeFailureV1',
    '<P as experimental_swift_reactor::control::ClosedAdoptionV1>::Retirement':'std::result::Result<(), experimental_swift_reactor::control::SwiftRunFailure>',
}
CONSTANT_TYPES={
 'core::num::<impl u64>::MAX':'u64','core::num::<impl usize>::MAX':'usize',
 'experimental_swift_reactor::cache::initial_profile_v1::CONSTRUCTION_CURSOR_V1':'experimental_swift_reactor::control::Cursor',
 '<P as experimental_swift_reactor::control::ClosedAdoptionV1>::FIXED_EXECUTION_WORK_V1':'u64',
 'experimental_swift_reactor::cache::PLAN_CELL_CREDITS':'u64',
 'experimental_swift_reactor::retained_profile_loader_v1::ATTEMPTS':'u32',
}
for name in ('PATCH_CAPACITY','PLAN_CAPACITY','RESIDENT_INDEX_BYTES'):CONSTANT_TYPES['experimental_swift_reactor::cache::'+name]='usize'
for name in ('BUILD_CAP','ENTRY_CAP','SESSION_CAP','SOURCE_CAP','STR_CAP'):CONSTANT_TYPES['experimental_swift_reactor::retained_profile_loader_v1::'+name]='usize'

def canonical(typ,bindings=None):
    if typ.startswith('exact-compiler-constant:'):
        atom=typ[len('exact-compiler-constant:'):]
        require(atom in CONSTANT_TYPES,'unreviewed-authored-constant-type:'+atom)
        typ=CONSTANT_TYPES[atom]
    # Associated types must be handled before their receiver variable.
    for name in sorted(SPECIALIZATIONS,key=len,reverse=True):
        if name in ('B','C','D'):continue
        typ=typ.replace(name,SPECIALIZATIONS[name])
    typ=PATH.sub(lambda m:ALIASES.get(m[0],SPECIALIZATIONS.get(m[0],m[0])),typ)
    if bindings:
        typ=PATH.sub(lambda m:bindings.get(m[0],m[0]),typ)
    return re.sub(r'\s+','',typ)

def unify(template,actual,bindings):
    """Solve T/R/N only as complete structural subterms; no text wildcards."""
    a=canonical(template,bindings);b=canonical(actual)
    if a==b:return
    # This finite generic set is independently recorded per target. Its solved
    # values are checked against explicit turbofish args in prepare_authored.
    if a in ('T','R','N'):
        require(a not in bindings,'inconsistent-generic:'+a)
        bindings[a]=b;return
    # Structural recursion retains every nested tuple/array/generic boundary.
    if a.startswith('&mut') and b.startswith('&mut'):return unify(a[4:],b[4:],bindings)
    if a.startswith('&') and b.startswith('&') and not a.startswith('&mut') and not b.startswith('&mut'):return unify(a[1:],b[1:],bindings)
    if a.startswith('[') and b.startswith('[') and a.endswith(']') and b.endswith(']'):
        aa=a[1:-1].split(';');bb=b[1:-1].split(';');require(len(aa)==len(bb),'array-kind-mismatch')
        for x,y in zip(aa,bb):unify(x,y,bindings)
        return
    if a.startswith('(') and b.startswith('(') and a.endswith(')') and b.endswith(')'):
        aa=split_operands(a[1:-1]);bb=split_operands(b[1:-1]);require(len(aa)==len(bb),'tuple-arity-mismatch')
        for x,y in zip(aa,bb):unify(x,y,bindings)
        return
    aa=a.find('<');bb=b.find('<')
    if aa>0 and bb>0 and a[:aa]==b[:bb] and a.endswith('>') and b.endswith('>'):
        xs=split_operands(a[aa+1:-1]);ys=split_operands(b[bb+1:-1]);require(len(xs)==len(ys),'generic-arity-mismatch')
        for x,y in zip(xs,ys):unify(x,y,bindings)
        return
    require(False,'incompatible-authored-type:'+template+' != '+actual)
