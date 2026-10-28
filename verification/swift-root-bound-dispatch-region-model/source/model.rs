//! Isolated finite source-contract model. No product authority or runtime probes.
//! All bounds, identities and completion records are hypotheses in this model.

use std::collections::{BTreeMap, BTreeSet};

pub const SOURCE: &str = "91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f";
pub const TARGET: &str = "aarch64-apple-darwin";
pub const COMPILER: &str = "b940084d7eb6a299eb4bfeb8e34901bc051e7ac4";
pub const CONFIG: &str = "experimental-swift-reactor;experimental-swift-wasi;experimental-stream-validation;experimental-function-cache;mixer_bootstrap_one_fixture_v1";
const MAX_EVENTS: usize = 128;
const MAX_DECLARATIONS: usize = 1024;

macro_rules! id {
    ($name:ident) => { #[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)] pub struct $name(pub u64); };
}
id!(AcquisitionId); id!(ChildId); id!(BackingId); id!(PhysicalArenaId); id!(RegionId); id!(EvidenceId);
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)] pub struct Bytes(pub u64);
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)] pub struct Work(pub u64);

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum ValueId { Ledger, AcquisitionOwner, Parent, ScopePair, Expected, Attempt, Fixture, Closure,
    Body, Leaf, Child, View, PrimaryView, DestroyWrapper, DestroyPayload, Token, Forgotten, UnwindRetained }
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum BackingKey { AcquisitionInputs, AcquisitionPaths, ParentBinding, File(u8), Executable, Proof, Error, Cancellation, Claims }
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum Component { C0, C1, C2, C3, C4, C5 }
pub const COMPONENTS: [Component; 6] = [Component::C0, Component::C1, Component::C2, Component::C3, Component::C4, Component::C5];
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum Funding { Acquisition, P0, Child(Component) }

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Payload { SetupRefused(u8), InvariantRefused(u8), LoaderRefused, CorrelationRefused, PreScopeFailure, Finished { failures_retained: bool } }
#[derive(Clone, Copy, Debug, PartialEq, Eq)] pub enum Selection { Proof, Failure }
#[derive(Clone, Copy, Debug, PartialEq, Eq)] pub enum Correlation { Correlated, LoaderRefused, Refused }
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum DestroyPhase { Entered, PayloadTaken, PayloadDropping, PayloadGone, ReservationTaken, WrapperDropping, WrapperGone }
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum OrdinaryPhase { Entered, PayloadTaken, PayloadDropping, PayloadGone, WrapperDropping }
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum UnwindSite { QuoteCall, ReserveCall, DispatchCall, SetupCall, LoaderCall, CorrelationCall, LeafCall, PayloadDrop, WrapperDrop, CaptureMoves }
#[derive(Clone, Copy, Debug, PartialEq, Eq)] pub enum UnwindPhase { Entered(UnwindSite), CleanupActive(UnwindSite), CleanupReturned(UnwindSite) }
#[derive(Clone, Copy, Debug, PartialEq, Eq)] pub enum Terminal { Refused, Released, ReleaseUnderflow, NoToken, OrdinaryDrop, Forgotten, Unwound }
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Phase {
    AcquisitionReserved, ScopePairReady, Scoped, ParentReady, Quoted, Reserved, ClosureReady, Entered,
    Setup { next: u8, mask: u8 }, SetupReady, Loading, LoaderReturned(Selection),
    RawRefusal(Payload), Correlated, LeafStarting, LeafScope, LeafConstructed, LeafObserved,
    LeafReturned(Payload), BodyReturned(Payload), Returned(Payload), Borrowing(Payload),
    Destroying(DestroyPhase), Ordinary(OrdinaryPhase), TokenReturned, NoToken,
    Released, ReleaseRetained, OrdinaryDone, Forgotten, EntryRefused, Unwinding(UnwindPhase), Unwound,
    Terminal(Terminal),
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Event {
    ScopeIssue, SplitScopePair, ParentReady, ParentRefused, QuoteReady, QuoteRefused, ReserveSuccess, ReserveRefused,
    ClosureConstruct, ClosureConsume, RootCapture, SetupOpened(u8), SetupRefused { stage: u8, retained_mask: u8 },
    SetupInvariantRefused { retained_mask: u8 }, SetupReady, LoaderBegin,
    LoaderReturned { selected: Selection, executable: bool },
    Correlate { expected_root: AcquisitionId, output_root: AcquisitionId, outcome: Correlation },
    PrepareArguments, LeafStart, LeafScopeRefused, LeafScopeReady, LeafConstruct, LeafOuterBorrow,
    LeafFinish { failures_retained: bool }, BoundReturn, ChildWrap, ObserveBegin, ObserveEnd,
    DestroyBegin, OrdinaryDropBegin, TakePayload, StartPayloadDrop, CompletePayloadDrop,
    TakeReservation, StartWrapperDrop, CompleteWrapperDrop, TokenReturnSome, TokenReturnNone,
    ReleaseChild(ChildId), ReleaseChildUnderflow(ChildId), ForgetChild, Unwind(UnwindSite), UnwindCleanupStart, UnwindCleanupReturn,
    UnwindResume, RetireAcquisition,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum TransitionRefusal { WrongPhase, WrongIdentity, WrongRoot, BadSetupPrefix, RepeatedScope, DuplicateLeaf, EventLimit }
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Charges { pub acquisition_retained: bool, pub child_work_committed: bool,
    pub child_storage_retained: bool, pub child_peak_retained: bool }

#[derive(Clone, Debug, PartialEq, Eq)]
struct Snapshot { values: BTreeSet<ValueId>, backings: BTreeMap<BackingKey, BTreeSet<ValueId>> }
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct TraceState {
    acquisition: AcquisitionId, child: ChildId, phase: Phase, sticky: bool,
    charges: Charges, values: BTreeSet<ValueId>, backings: BTreeMap<BackingKey, BTreeSet<ValueId>>,
    history: Vec<Snapshot>, leaf_calls: u8, observed: bool, arguments_prepared: bool,
}
impl TraceState {
    pub fn new(acquisition: AcquisitionId, child: ChildId) -> Self {
        let values = [ValueId::Ledger, ValueId::AcquisitionOwner, ValueId::Parent].into_iter().collect();
        let mut state = Self { acquisition, child, phase: Phase::AcquisitionReserved, sticky: false,
            charges: Charges { acquisition_retained: true, child_work_committed: false, child_storage_retained: false, child_peak_retained: false },
            values, backings: BTreeMap::new(), history: Vec::new(), leaf_calls: 0, observed: false, arguments_prepared: false };
        state.own(BackingKey::AcquisitionInputs, ValueId::AcquisitionOwner);
        state.own(BackingKey::AcquisitionPaths, ValueId::AcquisitionOwner);
        state.own(BackingKey::ParentBinding, ValueId::Parent);
        state.record(); state
    }
    pub fn phase(&self) -> Phase { self.phase }
    pub fn charges(&self) -> Charges { self.charges }
    pub fn sticky(&self) -> bool { self.sticky }
    pub fn leaf_calls(&self) -> u8 { self.leaf_calls }
    pub fn horizon(&self) -> u16 { self.history.len() as u16 }
    pub fn owners(&self, key: BackingKey) -> BTreeSet<ValueId> { self.backings.get(&key).cloned().unwrap_or_default() }
    pub fn ever_values(&self) -> BTreeSet<ValueId> { self.history.iter().flat_map(|s| s.values.iter().copied()).collect() }
    pub fn ever_backings(&self) -> BTreeSet<BackingKey> { self.history.iter().flat_map(|s| s.backings.keys().copied()).collect() }
    pub fn apply(&mut self, event: Event) -> Result<(), TransitionRefusal> {
        if self.history.len() >= MAX_EVENTS { return Err(TransitionRefusal::EventLimit); }
        let mut candidate = self.clone();
        candidate.step(event)?;
        candidate.record(); *self = candidate; Ok(())
    }
    fn record(&mut self) { self.history.push(Snapshot { values: self.values.clone(), backings: self.backings.clone() }); }
    fn own(&mut self, key: BackingKey, owner: ValueId) { self.backings.entry(key).or_default().insert(owner); }
    fn transfer(&mut self, from: ValueId, to: ValueId) {
        self.values.remove(&from); self.values.insert(to);
        for owners in self.backings.values_mut() { if owners.remove(&from) { owners.insert(to); } }
    }
    fn destroyed(&mut self, owner: ValueId) {
        self.values.remove(&owner);
        for owners in self.backings.values_mut() { owners.remove(&owner); }
    }
    fn valid_unwind(&self, site: UnwindSite) -> bool {
        match site {
            UnwindSite::QuoteCall => self.phase == Phase::ParentReady,
            UnwindSite::ReserveCall => self.phase == Phase::Quoted,
            UnwindSite::DispatchCall => matches!(self.phase, Phase::ClosureReady | Phase::Entered),
            UnwindSite::SetupCall => matches!(self.phase, Phase::Setup { .. }),
            UnwindSite::LoaderCall => self.phase == Phase::Loading,
            UnwindSite::CorrelationCall => matches!(self.phase, Phase::LoaderReturned(_)),
            UnwindSite::LeafCall => matches!(self.phase, Phase::LeafStarting | Phase::LeafScope | Phase::LeafConstructed | Phase::LeafObserved),
            UnwindSite::PayloadDrop => matches!(self.phase, Phase::Destroying(DestroyPhase::PayloadDropping) | Phase::Ordinary(OrdinaryPhase::PayloadDropping)),
            UnwindSite::WrapperDrop => matches!(self.phase, Phase::Destroying(DestroyPhase::WrapperDropping) | Phase::Ordinary(OrdinaryPhase::WrapperDropping)),
            UnwindSite::CaptureMoves => false,
        }
    }
    fn step(&mut self, event: Event) -> Result<(), TransitionRefusal> {
        use self::{Event as E, Phase as P};
        match (self.phase, event) {
            (P::AcquisitionReserved, E::ScopeIssue) => { self.sticky = true; self.values.insert(ValueId::ScopePair); self.phase = P::ScopePairReady; }
            (_, E::ScopeIssue) if self.sticky => return Err(TransitionRefusal::RepeatedScope),
            (P::ScopePairReady, E::SplitScopePair) => { self.destroyed(ValueId::ScopePair); self.values.extend([ValueId::Expected, ValueId::Attempt]); self.phase = P::Scoped; }
            (P::Scoped, E::ParentReady) => { self.values.insert(ValueId::Fixture); self.phase = P::ParentReady; }
            (P::Scoped, E::ParentRefused) | (P::ParentReady, E::QuoteRefused) | (P::Quoted, E::ReserveRefused) => {
                self.destroyed(ValueId::Attempt); self.destroyed(ValueId::Fixture); self.phase = P::EntryRefused;
            }
            (P::ParentReady, E::QuoteReady) => self.phase = P::Quoted,
            (P::Quoted, E::ReserveSuccess) => {
                self.charges.child_work_committed = true; self.charges.child_storage_retained = true; self.charges.child_peak_retained = true; self.phase = P::Reserved;
            }
            (P::Reserved, E::ClosureConstruct) => { self.destroyed(ValueId::Attempt); self.destroyed(ValueId::Fixture); self.values.insert(ValueId::Closure); self.phase = P::ClosureReady; }
            (P::ClosureReady, E::ClosureConsume) => { self.transfer(ValueId::Closure, ValueId::Body); self.phase = P::Entered; }
            (P::Entered, E::RootCapture) => self.phase = P::Setup { next: 0, mask: 0 },
            (P::Setup { next, mask }, E::SetupOpened(stage)) if stage == next && stage < 5 => {
                self.own(BackingKey::File(stage), ValueId::Body); self.phase = P::Setup { next: next + 1, mask: mask | (1 << stage) };
            }
            (P::Setup { next, mask }, E::SetupRefused { stage, retained_mask }) => {
                if stage != next || stage >= 5 || mask != retained_mask || mask != (1u8 << stage) - 1 { return Err(TransitionRefusal::BadSetupPrefix); }
                self.own(BackingKey::Error, ValueId::Body); self.phase = P::BodyReturned(Payload::SetupRefused(stage));
            }
            (P::Setup { mask, .. }, E::SetupInvariantRefused { retained_mask }) => {
                if mask != retained_mask || mask == 31 { return Err(TransitionRefusal::BadSetupPrefix); }
                // Conservative observation of the typed fallback, not proof that
                // normal File operations can reach an inconsistent slot array.
                self.phase = P::BodyReturned(Payload::InvariantRefused(mask));
            }
            (P::Setup { next: 5, mask: 31 }, E::SetupReady) => self.phase = P::SetupReady,
            (P::SetupReady, E::LoaderBegin) => { self.own(BackingKey::Cancellation, ValueId::Body); self.phase = P::Loading; }
            (P::Loading, E::LoaderReturned { selected, executable }) => {
                self.own(if selected == Selection::Proof { BackingKey::Proof } else { BackingKey::Error }, ValueId::Body);
                if executable { self.own(BackingKey::Executable, ValueId::Body); } self.phase = P::LoaderReturned(selected);
            }
            (P::LoaderReturned(selected), E::Correlate { expected_root, output_root, outcome }) => {
                if output_root != self.acquisition { return Err(TransitionRefusal::WrongRoot); }
                if expected_root != self.acquisition && outcome != Correlation::Refused { return Err(TransitionRefusal::WrongRoot); }
                self.phase = match outcome {
                    Correlation::Correlated if selected == Selection::Proof => P::Correlated,
                    Correlation::LoaderRefused if selected == Selection::Failure => P::RawRefusal(Payload::LoaderRefused),
                    Correlation::Refused => { self.own(BackingKey::Error, ValueId::Body); P::RawRefusal(Payload::CorrelationRefused) }
                    _ => return Err(TransitionRefusal::WrongPhase),
                };
            }
            (P::Correlated | P::RawRefusal(_), E::PrepareArguments) if !self.arguments_prepared => {
                self.arguments_prepared = true; self.own(BackingKey::Claims, ValueId::Body);
            }
            (P::Correlated, E::LeafStart) if self.arguments_prepared => {
                if self.leaf_calls != 0 { return Err(TransitionRefusal::DuplicateLeaf); }
                self.leaf_calls = 1; self.values.insert(ValueId::Leaf); self.own(BackingKey::Cancellation, ValueId::Leaf); self.phase = P::LeafStarting;
            }
            (P::LeafStarting, E::LeafScopeRefused) => { self.destroyed(ValueId::Leaf); self.own(BackingKey::Error, ValueId::Body); self.phase = P::LeafReturned(Payload::PreScopeFailure); }
            (P::LeafStarting, E::LeafScopeReady) => self.phase = P::LeafScope,
            (P::LeafScope, E::LeafConstruct) => self.phase = P::LeafConstructed,
            (P::LeafConstructed, E::LeafOuterBorrow) => self.phase = P::LeafObserved,
            (P::LeafObserved, E::LeafFinish { failures_retained }) => {
                self.destroyed(ValueId::Leaf); if failures_retained { self.own(BackingKey::Error, ValueId::Body); }
                self.phase = P::LeafReturned(Payload::Finished { failures_retained });
            }
            (P::RawRefusal(payload) | P::LeafReturned(payload), E::BoundReturn) if self.arguments_prepared => self.phase = P::BodyReturned(payload),
            (P::BodyReturned(payload), E::ChildWrap) => { self.transfer(ValueId::Body, ValueId::Child); self.phase = P::Returned(payload); }
            (P::Returned(payload), E::ObserveBegin) if !self.observed => {
                self.values.insert(ValueId::View);
                if !matches!(payload, Payload::SetupRefused(_) | Payload::InvariantRefused(_)) { self.values.insert(ValueId::PrimaryView); }
                self.phase = P::Borrowing(payload);
            }
            (P::Borrowing(payload), E::ObserveEnd) => { self.destroyed(ValueId::View); self.destroyed(ValueId::PrimaryView); self.observed = true; self.phase = P::Returned(payload); }
            (P::Returned(_), E::DestroyBegin) => { self.transfer(ValueId::Child, ValueId::DestroyWrapper); self.phase = P::Destroying(DestroyPhase::Entered); }
            (P::Returned(_), E::OrdinaryDropBegin) => { self.transfer(ValueId::Child, ValueId::DestroyWrapper); self.phase = P::Ordinary(OrdinaryPhase::Entered); }
            (P::Destroying(DestroyPhase::Entered), E::TakePayload) => { self.move_payload_out(); self.phase = P::Destroying(DestroyPhase::PayloadTaken); }
            (P::Ordinary(OrdinaryPhase::Entered), E::TakePayload) => { self.move_payload_out(); self.phase = P::Ordinary(OrdinaryPhase::PayloadTaken); }
            (P::Destroying(DestroyPhase::PayloadTaken), E::StartPayloadDrop) => self.phase = P::Destroying(DestroyPhase::PayloadDropping),
            (P::Ordinary(OrdinaryPhase::PayloadTaken), E::StartPayloadDrop) => self.phase = P::Ordinary(OrdinaryPhase::PayloadDropping),
            (P::Destroying(DestroyPhase::PayloadDropping), E::CompletePayloadDrop) => { self.destroyed(ValueId::DestroyPayload); self.phase = P::Destroying(DestroyPhase::PayloadGone); }
            (P::Ordinary(OrdinaryPhase::PayloadDropping), E::CompletePayloadDrop) => { self.destroyed(ValueId::DestroyPayload); self.phase = P::Ordinary(OrdinaryPhase::PayloadGone); }
            (P::Destroying(DestroyPhase::PayloadGone), E::TakeReservation) => self.phase = P::Destroying(DestroyPhase::ReservationTaken),
            (P::Destroying(DestroyPhase::ReservationTaken), E::StartWrapperDrop) => self.phase = P::Destroying(DestroyPhase::WrapperDropping),
            (P::Ordinary(OrdinaryPhase::PayloadGone), E::StartWrapperDrop) => self.phase = P::Ordinary(OrdinaryPhase::WrapperDropping),
            (P::Destroying(DestroyPhase::WrapperDropping), E::CompleteWrapperDrop) => { self.destroyed(ValueId::DestroyWrapper); self.phase = P::Destroying(DestroyPhase::WrapperGone); }
            (P::Ordinary(OrdinaryPhase::WrapperDropping), E::CompleteWrapperDrop) => { self.destroyed(ValueId::DestroyWrapper); self.phase = P::OrdinaryDone; }
            (P::Destroying(DestroyPhase::WrapperGone), E::TokenReturnSome) => { self.values.insert(ValueId::Token); self.phase = P::TokenReturned; }
            (P::Destroying(DestroyPhase::WrapperGone), E::TokenReturnNone) => self.phase = P::NoToken,
            (P::TokenReturned, E::ReleaseChild(child)) => {
                if child != self.child { return Err(TransitionRefusal::WrongIdentity); }
                self.destroyed(ValueId::Token); self.charges.child_storage_retained = false; self.phase = P::Released;
            }
            (P::TokenReturned, E::ReleaseChildUnderflow(child)) => {
                if child != self.child { return Err(TransitionRefusal::WrongIdentity); }
                self.destroyed(ValueId::Token); self.phase = P::ReleaseRetained;
            }
            (P::Returned(_), E::ForgetChild) => { self.transfer(ValueId::Child, ValueId::Forgotten); self.phase = P::Forgotten; }
            (_, E::Unwind(site)) if self.valid_unwind(site) => {
                for value in [ValueId::Closure, ValueId::Body, ValueId::Leaf, ValueId::Child, ValueId::DestroyWrapper, ValueId::DestroyPayload] {
                    if self.values.contains(&value) { self.transfer(value, ValueId::UnwindRetained); }
                }
                self.phase = P::Unwinding(UnwindPhase::Entered(site));
            }
            (P::Unwinding(UnwindPhase::Entered(site)), E::UnwindCleanupStart) => self.phase = P::Unwinding(UnwindPhase::CleanupActive(site)),
            (P::Unwinding(UnwindPhase::CleanupActive(site)), E::UnwindCleanupReturn) => self.phase = P::Unwinding(UnwindPhase::CleanupReturned(site)),
            (P::Unwinding(UnwindPhase::CleanupReturned(_)), E::UnwindResume) => self.phase = P::Unwound,
            (P::Released | P::ReleaseRetained | P::NoToken | P::OrdinaryDone | P::Forgotten | P::EntryRefused | P::Unwound, E::RetireAcquisition) => {
                let terminal = match self.phase { P::Released => Terminal::Released, P::ReleaseRetained => Terminal::ReleaseUnderflow, P::NoToken => Terminal::NoToken,
                    P::OrdinaryDone => Terminal::OrdinaryDrop, P::Forgotten => Terminal::Forgotten, P::Unwound => Terminal::Unwound, _ => Terminal::Refused };
                self.destroyed(ValueId::AcquisitionOwner); self.destroyed(ValueId::ScopePair); self.destroyed(ValueId::Expected); self.destroyed(ValueId::Attempt); self.destroyed(ValueId::Fixture);
                self.phase = P::Terminal(terminal);
            }
            _ => return Err(TransitionRefusal::WrongPhase),
        }
        Ok(())
    }
    fn move_payload_out(&mut self) {
        self.values.insert(ValueId::DestroyPayload);
        for owners in self.backings.values_mut() { if owners.remove(&ValueId::DestroyWrapper) { owners.insert(ValueId::DestroyPayload); } }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Binding { pub source: &'static str, pub target: &'static str, pub compiler: &'static str, pub config: &'static str }
impl Binding { pub const CURRENT: Self = Self { source: SOURCE, target: TARGET, compiler: COMPILER, config: CONFIG }; }
#[derive(Clone, Copy, Debug, PartialEq, Eq)] pub struct Evidence { pub id: EvidenceId, pub binding: Binding }
#[derive(Clone, Copy, Debug, PartialEq, Eq)] pub enum EvidenceOrigin { Missing, Synthetic(Evidence), ReviewedBound(Evidence) }
#[derive(Clone, Copy, Debug, PartialEq, Eq)] pub struct CapacityEvidence { pub origin: EvidenceOrigin, pub bound: Bytes }
#[derive(Clone, Copy, Debug, PartialEq, Eq)] pub struct WorkEvidence { pub origin: EvidenceOrigin, pub bound: Work }
#[derive(Clone, Copy, Debug, PartialEq, Eq)] pub struct IdentityEvidence { pub origin: EvidenceOrigin, pub object: u64 }
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum CurrentShape { Correspondence, Attempt, ScopePair, DispatchClosure, ReturnedChild, AdmittedOutcome, AdmittedPayload, SharedView, PrimaryView, UnobservedFrame(ValueId) }
impl CurrentShape {
    pub fn observed_size(self) -> Option<Bytes> { match self {
        Self::Correspondence => Some(Bytes(24)), Self::Attempt => Some(Bytes(32)), Self::ScopePair => Some(Bytes(56)),
        Self::DispatchClosure => Some(Bytes(48)), Self::ReturnedChild => Some(Bytes(13640)), Self::AdmittedOutcome => Some(Bytes(13624)),
        Self::AdmittedPayload => Some(Bytes(13616)), Self::SharedView => Some(Bytes(8)), Self::PrimaryView => Some(Bytes(16)), Self::UnobservedFrame(_) => None } }
    fn for_owner(owner: ValueId) -> Self { match owner { ValueId::ScopePair => Self::ScopePair, ValueId::Expected => Self::Correspondence, ValueId::Attempt => Self::Attempt,
        ValueId::Closure => Self::DispatchClosure, ValueId::Child | ValueId::Forgotten | ValueId::DestroyWrapper => Self::ReturnedChild,
        ValueId::DestroyPayload => Self::AdmittedOutcome, ValueId::View => Self::SharedView, ValueId::PrimaryView => Self::PrimaryView,
        other => Self::UnobservedFrame(other) } }
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)] pub enum End { At(u16), Retained }
#[derive(Clone, Copy, Debug, PartialEq, Eq)] pub struct Interval { pub begin: u16, pub end: End }
impl Interval { fn covers(self, at: usize, horizon: usize) -> bool { usize::from(self.begin) <= at && at < self.end_at(horizon) }
    fn end_at(self, horizon: usize) -> usize { match self.end { End::At(n) => usize::from(n), End::Retained => horizon } } }
#[derive(Clone, Debug, PartialEq, Eq)] pub struct ArenaDecl { pub id: PhysicalArenaId, pub identity: IdentityEvidence }
#[derive(Clone, Debug, PartialEq, Eq)] pub struct DisjointDecl { pub left: PhysicalArenaId, pub right: PhysicalArenaId, pub evidence: EvidenceOrigin }
#[derive(Clone, Debug, PartialEq, Eq)] pub struct InlineDecl { pub id: RegionId, pub owner: ValueId, pub shape: CurrentShape,
    pub arena: PhysicalArenaId, pub offset: Bytes, pub capacity: CapacityEvidence, pub alignment: Bytes,
    pub live: Interval, pub parent: Option<RegionId>, pub funding: Funding }
#[derive(Clone, Debug, PartialEq, Eq)] pub struct BackingDecl { pub key: BackingKey, pub id: BackingId, pub arena: PhysicalArenaId,
    pub capacity: CapacityEvidence, pub completion: EvidenceOrigin, pub funding: Funding }
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum QuoteTerm { AcquisitionOperation(WorkEvidence), AcquisitionCleanup(WorkEvidence), AcquisitionStorage(CapacityEvidence),
    P0 { work: WorkEvidence, storage: CapacityEvidence }, Child { component: Component, work: WorkEvidence, storage: CapacityEvidence } }
#[derive(Clone, Debug, PartialEq, Eq)] pub struct Declarations { pub arenas: Vec<ArenaDecl>, pub disjoint: Vec<DisjointDecl>,
    pub inline: Vec<InlineDecl>, pub backing: Vec<BackingDecl>, pub quote: Vec<QuoteTerm> }
#[derive(Clone, Debug, PartialEq, Eq)] pub enum MissingFact { TraceNotTerminal, Evidence, OwnerRegion(ValueId), Backing(BackingKey), Disjointness,
    QuoteTerm, Work, Capacity, FinalDestruction(BackingKey), UnreleasedOwner }
#[derive(Clone, Debug, PartialEq, Eq)] pub enum AssessmentOutcome { IncompleteEvidence(MissingFact), InvalidTrace(&'static str), ArithmeticOverflow,
    InsufficientCapacity { required: Bytes, limit: Bytes }, ModelFitsCapacity { peak: Bytes, retained_child_storage_sum: Bytes, retained_child_work_sum: Work, retained_acquisition_work_sum: Work } }
#[derive(Clone, Debug, PartialEq, Eq)] struct ModelOnly;
#[derive(Clone, Debug, PartialEq, Eq)] pub struct Assessment { pub outcome: AssessmentOutcome, marker: ModelOnly }
impl Assessment { pub fn is_model_only(&self) -> bool { true } }
type Checked<T> = Result<T, AssessmentOutcome>;
fn incomplete(fact: MissingFact) -> AssessmentOutcome { AssessmentOutcome::IncompleteEvidence(fact) }
fn evidence(origin: EvidenceOrigin) -> Checked<Evidence> {
    let e = match origin { EvidenceOrigin::Missing => return Err(incomplete(MissingFact::Evidence)), EvidenceOrigin::Synthetic(e) | EvidenceOrigin::ReviewedBound(e) => e };
    if e.id.0 == 0 || e.binding != Binding::CURRENT { return Err(AssessmentOutcome::InvalidTrace("evidence binding")); } Ok(e)
}
fn capacity(bound: CapacityEvidence) -> Checked<u64> { evidence(bound.origin)?; Ok(bound.bound.0) }
fn work(bound: WorkEvidence) -> Checked<u64> { evidence(bound.origin)?; if bound.bound.0 == 0 { return Err(incomplete(MissingFact::Work)); } Ok(bound.bound.0) }
fn add(left: u64, right: u64) -> Checked<u64> { left.checked_add(right).ok_or(AssessmentOutcome::ArithmeticOverflow) }
fn union_width(mut spans: Vec<(u64, u64)>) -> Checked<u64> {
    spans.sort_unstable(); let mut current: Option<(u64, u64)> = None; let mut total = 0;
    for (start, end) in spans { if end < start { return Err(AssessmentOutcome::InvalidTrace("reversed extent")); }
        match current { None => current = Some((start, end)), Some((a, b)) if start <= b => current = Some((a, b.max(end))),
            Some((a, b)) => { total = add(total, b - a)?; current = Some((start, end)); } }
    }
    if let Some((a, b)) = current { total = add(total, b - a)?; } Ok(total)
}
fn nested(parent: CurrentShape, child: CurrentShape) -> bool { matches!((parent, child),
    (CurrentShape::ReturnedChild, CurrentShape::AdmittedOutcome) | (CurrentShape::AdmittedOutcome, CurrentShape::AdmittedPayload) |
    (CurrentShape::ScopePair, CurrentShape::Correspondence) | (CurrentShape::ScopePair, CurrentShape::Attempt) |
    (CurrentShape::DispatchClosure, CurrentShape::Attempt)) }
fn owner_funding(owner: ValueId, funding: Funding) -> bool {
    match owner {
        ValueId::Ledger | ValueId::AcquisitionOwner => funding == Funding::Acquisition,
        ValueId::Parent | ValueId::ScopePair | ValueId::Expected | ValueId::Attempt | ValueId::Fixture | ValueId::View | ValueId::PrimaryView | ValueId::Token => funding == Funding::P0,
        ValueId::DestroyWrapper | ValueId::DestroyPayload | ValueId::UnwindRetained => matches!(funding, Funding::P0 | Funding::Child(_)),
        _ => matches!(funding, Funding::Child(_)),
    }
}
fn backing_funding(key: BackingKey) -> Funding {
    match key {
        BackingKey::AcquisitionInputs | BackingKey::AcquisitionPaths => Funding::Acquisition,
        BackingKey::ParentBinding => Funding::P0,
        BackingKey::File(_) => Funding::Child(Component::C0),
        BackingKey::Executable | BackingKey::Proof => Funding::Child(Component::C1),
        BackingKey::Cancellation | BackingKey::Claims => Funding::Child(Component::C2),
        BackingKey::Error => Funding::Child(Component::C5),
    }
}

pub fn assess_capacity(trace: &TraceState, declarations: &Declarations, limit: Bytes) -> Assessment {
    let outcome = match assess(trace, declarations, limit) { Ok(outcome) => outcome, Err(outcome) => outcome };
    Assessment { outcome, marker: ModelOnly }
}
fn assess(trace: &TraceState, d: &Declarations, limit: Bytes) -> Checked<AssessmentOutcome> {
    if !matches!(trace.phase, Phase::Terminal(_)) { return Err(incomplete(MissingFact::TraceNotTerminal)); }
    if matches!(trace.phase, Phase::Terminal(Terminal::Forgotten | Terminal::Unwound)) { return Err(incomplete(MissingFact::UnreleasedOwner)); }
    let declaration_count = [d.arenas.len(), d.disjoint.len(), d.inline.len(), d.backing.len()].into_iter()
        .try_fold(0usize, |total, count| total.checked_add(count)).ok_or(AssessmentOutcome::ArithmeticOverflow)?;
    if declaration_count > MAX_DECLARATIONS { return Err(AssessmentOutcome::InvalidTrace("declaration bound")); }
    if d.quote.len() > 10 { return Err(AssessmentOutcome::InvalidTrace("duplicate quote partition")); }
    let mut budgets = BTreeMap::new(); let mut seen_quote = BTreeSet::new(); let mut child_work = 0; let mut child_storage = 0; let mut acquisition_work = 0;
    for term in &d.quote {
        let key = match term {
            QuoteTerm::AcquisitionOperation(w) => { acquisition_work = add(acquisition_work, work(*w)?)?; 0u8 }
            QuoteTerm::AcquisitionCleanup(w) => { acquisition_work = add(acquisition_work, work(*w)?)?; 1 }
            QuoteTerm::AcquisitionStorage(b) => { budgets.insert(Funding::Acquisition, capacity(*b)?); 2 }
            QuoteTerm::P0 { work: w, storage } => { work(*w)?; budgets.insert(Funding::P0, capacity(*storage)?); 3 }
            QuoteTerm::Child { component, work: w, storage } => {
                child_work = add(child_work, work(*w)?)?; let bytes = capacity(*storage)?; child_storage = add(child_storage, bytes)?;
                budgets.insert(Funding::Child(*component), bytes); 4 + *component as u8
            }
        };
        if !seen_quote.insert(key) { return Err(AssessmentOutcome::InvalidTrace("duplicate quote partition")); }
    }
    if seen_quote != (0u8..10).collect::<BTreeSet<_>>() { return Err(incomplete(MissingFact::QuoteTerm)); }
    if budgets.values().any(|value| *value == 0) { return Err(incomplete(MissingFact::Capacity)); }
    let _retained_total = add(add(*budgets.get(&Funding::Acquisition).unwrap(), *budgets.get(&Funding::P0).unwrap())?, child_storage)?;
    let mut arenas = BTreeMap::new(); let mut identities = BTreeSet::new();
    for arena in &d.arenas {
        let e = evidence(arena.identity.origin)?;
        if arena.identity.object == 0 || !identities.insert((e.id, arena.identity.object)) || arenas.insert(arena.id, arena).is_some() { return Err(AssessmentOutcome::InvalidTrace("conflicting arena identity")); }
    }
    let mut disjoint = BTreeSet::new();
    for relation in &d.disjoint {
        evidence(relation.evidence)?;
        if relation.left == relation.right || !arenas.contains_key(&relation.left) || !arenas.contains_key(&relation.right) { return Err(AssessmentOutcome::InvalidTrace("invalid disjoint relation")); }
        disjoint.insert((relation.left.min(relation.right), relation.left.max(relation.right)));
    }
    let ever_values = trace.ever_values(); let ever_backings = trace.ever_backings(); let horizon = trace.history.len();
    let mut regions = BTreeMap::new();
    for region in &d.inline {
        if regions.insert(region.id, region).is_some() || !ever_values.contains(&region.owner) || !arenas.contains_key(&region.arena) { return Err(AssessmentOutcome::InvalidTrace("unbound inline identity")); }
        if !owner_funding(region.owner, region.funding) { return Err(AssessmentOutcome::InvalidTrace("incompatible inline funding")); }
        let bytes = capacity(region.capacity)?; let end = add(region.offset.0, bytes)?;
        if bytes == 0 || region.alignment.0 == 0 || !region.alignment.0.is_power_of_two() || region.offset.0 % region.alignment.0 != 0 || region.live.end_at(horizon) > horizon || usize::from(region.live.begin) >= region.live.end_at(horizon) { return Err(AssessmentOutcome::InvalidTrace("inline geometry")); }
        if region.parent.is_none() && region.shape != CurrentShape::for_owner(region.owner) { return Err(AssessmentOutcome::InvalidTrace("wrong current shape for owner")); }
        if let Some(minimum) = region.shape.observed_size() { if bytes < minimum.0 || region.alignment.0 < 8 { return Err(AssessmentOutcome::InvalidTrace("undersized accepted shape")); } }
        let _ = end;
    }
    for region in &d.inline {
        if let Some(parent_id) = region.parent {
            let parent = regions.get(&parent_id).ok_or(AssessmentOutcome::InvalidTrace("missing containing region"))?;
            if parent.id == region.id || parent.owner != region.owner || parent.arena != region.arena || parent.funding != region.funding || !nested(parent.shape, region.shape) ||
                region.offset.0 < parent.offset.0 || add(region.offset.0, capacity(region.capacity)?)? > add(parent.offset.0, capacity(parent.capacity)?)? ||
                region.live.begin < parent.live.begin || region.live.end_at(horizon) > parent.live.end_at(horizon) {
                return Err(AssessmentOutcome::InvalidTrace("invalid nested containment"));
            }
        }
    }
    let mut backing = BTreeMap::new(); let mut backing_ids = BTreeSet::new(); let mut backing_arenas = BTreeSet::new();
    for item in &d.backing {
        if !ever_backings.contains(&item.key) || !arenas.contains_key(&item.arena) || backing.insert(item.key, item).is_some() || !backing_ids.insert(item.id) || !backing_arenas.insert(item.arena) { return Err(AssessmentOutcome::InvalidTrace("conflicting backing identity")); }
        if item.funding != backing_funding(item.key) { return Err(AssessmentOutcome::InvalidTrace("incompatible backing funding")); }
        if capacity(item.capacity)? == 0 { return Err(incomplete(MissingFact::Capacity)); }
        if d.inline.iter().any(|region| region.arena == item.arena) { return Err(AssessmentOutcome::InvalidTrace("separate backing aliases inline arena")); }
        let last_live = trace.history.last().unwrap().backings.get(&item.key).is_some_and(|owners| !owners.is_empty());
        if !last_live { evidence(item.completion).map_err(|_| incomplete(MissingFact::FinalDestruction(item.key)))?; }
    }
    for key in &ever_backings { if !backing.contains_key(key) { return Err(incomplete(MissingFact::Backing(*key))); } }
    let mut peak = 0;
    for (segment, snapshot) in trace.history.iter().enumerate() {
        for owner in &snapshot.values {
            if !d.inline.iter().any(|region| region.owner == *owner && region.parent.is_none() && region.live.covers(segment, horizon)) { return Err(incomplete(MissingFact::OwnerRegion(*owner))); }
        }
        let mut spans: BTreeMap<PhysicalArenaId, Vec<(u64, u64, Funding)>> = BTreeMap::new(); let mut per_funding: BTreeMap<Funding, u64> = BTreeMap::new();
        for region in &d.inline { if region.live.covers(segment, horizon) {
            spans.entry(region.arena).or_default().push((region.offset.0, add(region.offset.0, capacity(region.capacity)?)?, region.funding));
        } }
        let mut active = spans.keys().copied().collect::<BTreeSet<_>>();
        for (key, owners) in &snapshot.backings { if !owners.is_empty() {
            let item = backing.get(key).ok_or(incomplete(MissingFact::Backing(*key)))?;
            active.insert(item.arena); let sum = per_funding.entry(item.funding).or_default(); *sum = add(*sum, capacity(item.capacity)?)?;
        } }
        let ids: Vec<_> = active.into_iter().collect();
        for (i, left) in ids.iter().enumerate() { for right in &ids[i + 1..] {
            if !disjoint.contains(&(*left, *right)) { return Err(incomplete(MissingFact::Disjointness)); }
        } }
        for entries in spans.values() {
            for (i, &(start, end, funding)) in entries.iter().enumerate() {
                for &(other_start, other_end, other_funding) in &entries[i + 1..] {
                    if funding != other_funding && start < other_end && other_start < end { return Err(AssessmentOutcome::InvalidTrace("overlap charged to two partitions")); }
                }
            }
            for funding in budgets.keys() {
                let width = union_width(entries.iter().filter(|entry| entry.2 == *funding).map(|entry| (entry.0, entry.1)).collect())?;
                let sum = per_funding.entry(*funding).or_default(); *sum = add(*sum, width)?;
            }
        }
        let mut total = 0;
        for (funding, required) in per_funding { let budget = *budgets.get(&funding).ok_or(incomplete(MissingFact::QuoteTerm))?;
            if required > budget { return Err(AssessmentOutcome::InsufficientCapacity { required: Bytes(required), limit: Bytes(budget) }); }
            total = add(total, required)?;
        }
        peak = peak.max(total);
    }
    if peak > limit.0 { return Err(AssessmentOutcome::InsufficientCapacity { required: Bytes(peak), limit }); }
    Ok(AssessmentOutcome::ModelFitsCapacity { peak: Bytes(peak), retained_child_storage_sum: Bytes(child_storage), retained_child_work_sum: Work(child_work), retained_acquisition_work_sum: Work(acquisition_work) })
}

#[cfg(test)]
#[path = "tests.rs"]
mod tests;
