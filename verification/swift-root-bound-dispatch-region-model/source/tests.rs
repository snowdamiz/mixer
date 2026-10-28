use super::*;

fn drive(trace: &mut TraceState, events: &[Event]) {
    for event in events { assert_eq!(trace.apply(*event), Ok(()), "event {event:?} at {:?}", trace.phase()); }
}
fn atomic_refusal(trace: &mut TraceState, event: Event) {
    let before = trace.clone(); assert!(trace.apply(event).is_err()); assert_eq!(*trace, before);
}
fn scoped() -> TraceState {
    let mut trace = TraceState::new(AcquisitionId(1), ChildId(7)); drive(&mut trace, &[Event::ScopeIssue, Event::SplitScopePair]); trace
}
fn setup() -> TraceState {
    let mut trace = scoped(); drive(&mut trace, &[Event::ParentReady, Event::QuoteReady, Event::ReserveSuccess,
        Event::ClosureConstruct, Event::ClosureConsume, Event::RootCapture]); trace
}
fn loading() -> TraceState {
    let mut trace = setup(); for stage in 0..5 { drive(&mut trace, &[Event::SetupOpened(stage)]); }
    drive(&mut trace, &[Event::SetupReady, Event::LoaderBegin]); trace
}
fn correlated(selection: Selection, outcome: Correlation) -> TraceState {
    let mut trace = loading(); drive(&mut trace, &[Event::LoaderReturned { selected: selection, executable: true },
        Event::Correlate { expected_root: AcquisitionId(1), output_root: AcquisitionId(1), outcome }, Event::PrepareArguments]); trace
}
fn returned() -> TraceState {
    let mut trace = correlated(Selection::Proof, Correlation::Correlated);
    drive(&mut trace, &[Event::LeafStart, Event::LeafScopeReady, Event::LeafConstruct, Event::LeafOuterBorrow,
        Event::LeafFinish { failures_retained: false }, Event::BoundReturn, Event::ChildWrap]); trace
}
fn payload_dropping() -> TraceState {
    let mut trace = returned(); drive(&mut trace, &[Event::DestroyBegin, Event::TakePayload, Event::StartPayloadDrop]); trace
}
fn wrapper_gone(trace: &mut TraceState) {
    drive(trace, &[Event::DestroyBegin, Event::TakePayload, Event::StartPayloadDrop, Event::CompletePayloadDrop,
        Event::TakeReservation, Event::StartWrapperDrop, Event::CompleteWrapperDrop]);
}
fn normal() -> TraceState {
    let mut trace = returned(); drive(&mut trace, &[Event::ObserveBegin, Event::ObserveEnd]); wrapper_gone(&mut trace);
    drive(&mut trace, &[Event::TokenReturnSome, Event::ReleaseChild(ChildId(7)), Event::RetireAcquisition]); trace
}
fn origin(id: u64) -> EvidenceOrigin { EvidenceOrigin::Synthetic(Evidence { id: EvidenceId(id), binding: Binding::CURRENT }) }
fn bound(bytes: u64) -> CapacityEvidence { CapacityEvidence { origin: origin(1), bound: Bytes(bytes) } }
fn priced(work: u64) -> WorkEvidence { WorkEvidence { origin: origin(1), bound: Work(work) } }
fn funding(owner: ValueId) -> Funding { match owner {
    ValueId::Ledger | ValueId::AcquisitionOwner => Funding::Acquisition,
    ValueId::Parent | ValueId::ScopePair | ValueId::Expected | ValueId::Attempt | ValueId::Fixture | ValueId::View | ValueId::PrimaryView | ValueId::Token => Funding::P0,
    ValueId::Closure => Funding::Child(Component::C2), ValueId::Body | ValueId::Leaf | ValueId::UnwindRetained => Funding::Child(Component::C4),
    _ => Funding::Child(Component::C5),
} }
fn declarations(trace: &TraceState) -> Declarations {
    // Deliberately hypothetical synthetic physical arenas, not a product map.
    // All extents cover the full model horizon, a conservative synthetic case.
    let mut d = Declarations { arenas: Vec::new(), disjoint: Vec::new(), inline: Vec::new(), backing: Vec::new(), quote: vec![
        QuoteTerm::AcquisitionOperation(priced(10)), QuoteTerm::AcquisitionCleanup(priced(10)),
        QuoteTerm::AcquisitionStorage(bound(1_000_000)), QuoteTerm::P0 { work: priced(10), storage: bound(1_000_000) }] };
    for component in COMPONENTS { d.quote.push(QuoteTerm::Child { component, work: priced(10), storage: bound(1_000_000) }); }
    for (index, owner) in trace.ever_values().into_iter().enumerate() {
        let arena = PhysicalArenaId(index as u64 + 1); let shape = CurrentShape::for_owner(owner);
        d.arenas.push(ArenaDecl { id: arena, identity: IdentityEvidence { origin: origin(1), object: arena.0 } });
        d.inline.push(InlineDecl { id: RegionId(index as u64 + 1), owner, shape, arena, offset: Bytes(0),
            capacity: bound(shape.observed_size().unwrap_or(Bytes(8)).0), alignment: Bytes(8),
            live: Interval { begin: 0, end: End::At(trace.horizon()) }, parent: None, funding: funding(owner) });
    }
    for (index, key) in trace.ever_backings().into_iter().enumerate() {
        let arena = PhysicalArenaId(index as u64 + 1000);
        d.arenas.push(ArenaDecl { id: arena, identity: IdentityEvidence { origin: origin(1), object: arena.0 } });
        d.backing.push(BackingDecl { key, id: BackingId(index as u64 + 1), arena, capacity: bound(8), completion: origin(1), funding: backing_funding(key) });
    }
    for i in 0..d.arenas.len() { for j in i + 1..d.arenas.len() {
        d.disjoint.push(DisjointDecl { left: d.arenas[i].id, right: d.arenas[j].id, evidence: origin(1) });
    } }
    d
}
fn peak(trace: &TraceState, d: &Declarations) -> u64 {
    let result = assess_capacity(trace, d, Bytes(10_000_000)); assert!(result.is_model_only());
    match result.outcome { AssessmentOutcome::ModelFitsCapacity { peak, retained_child_storage_sum, retained_child_work_sum, retained_acquisition_work_sum } => {
        assert_eq!(retained_child_storage_sum, Bytes(6_000_000)); assert_eq!(retained_child_work_sum, Work(60));
        assert_eq!(retained_acquisition_work_sum, Work(20)); peak.0
    }, other => panic!("synthetic complete declaration refused: {other:?}") }
}
fn rejected(trace: &TraceState, d: &Declarations) -> AssessmentOutcome {
    let result = assess_capacity(trace, d, Bytes(10_000_000)); assert!(result.is_model_only());
    assert!(!matches!(result.outcome, AssessmentOutcome::ModelFitsCapacity { .. })); result.outcome
}

#[test]
fn t01_selection_and_reservation_refusals_are_atomic() {
    for events in [vec![Event::ParentRefused], vec![Event::ParentReady, Event::QuoteRefused],
        vec![Event::ParentReady, Event::QuoteReady, Event::ReserveRefused]] {
        let mut trace = scoped(); drive(&mut trace, &events);
        assert!(!trace.charges().child_work_committed); assert!(!trace.charges().child_storage_retained);
        assert!(!trace.charges().child_peak_retained); assert!(trace.sticky());
        atomic_refusal(&mut trace, Event::ClosureConstruct); drive(&mut trace, &[Event::RetireAcquisition]);
        assert_eq!(trace.phase(), Phase::Terminal(Terminal::Refused));
    }
    let mut trace = scoped(); atomic_refusal(&mut trace, Event::ScopeIssue);
    assert!(trace.sticky()); atomic_refusal(&mut trace, Event::ReserveSuccess);
}
#[test]
fn t02_complete_normal_trace_is_model_only_and_root_stays_charged() {
    let trace = normal(); assert_eq!(trace.phase(), Phase::Terminal(Terminal::Released)); assert_eq!(trace.leaf_calls(), 1);
    assert_eq!(trace.charges(), Charges { acquisition_retained: true, child_work_committed: true, child_storage_retained: false, child_peak_retained: true });
    assert!(peak(&trace, &declarations(&trace)) > 13640);
}
#[test]
fn t03_all_five_partial_setup_prefixes_preserve_exact_owners() {
    for stage in 0..5 {
        let mut trace = setup(); for opened in 0..stage { drive(&mut trace, &[Event::SetupOpened(opened)]); }
        let mask = (1u8 << stage) - 1;
        atomic_refusal(&mut trace, Event::SetupRefused { stage, retained_mask: mask ^ 1 });
        drive(&mut trace, &[Event::SetupRefused { stage, retained_mask: mask }]);
        assert_eq!(trace.phase(), Phase::BodyReturned(Payload::SetupRefused(stage)));
        for file in 0..5 { assert_eq!(!trace.owners(BackingKey::File(file)).is_empty(), file < stage); }
        assert!(!trace.ever_backings().contains(&BackingKey::Cancellation)); assert_eq!(trace.leaf_calls(), 0);
        atomic_refusal(&mut trace, Event::LoaderBegin); drive(&mut trace, &[Event::ChildWrap]); wrapper_gone(&mut trace);
        drive(&mut trace, &[Event::TokenReturnSome, Event::ReleaseChild(ChildId(7)), Event::RetireAcquisition]);
        assert!(peak(&trace, &declarations(&trace)) > 0);
    }
}
#[test]
fn t04_invariant_fallback_preserves_observed_mask_without_ready_claim() {
    let mut trace = setup(); drive(&mut trace, &[Event::SetupOpened(0), Event::SetupOpened(1)]);
    atomic_refusal(&mut trace, Event::SetupReady);
    atomic_refusal(&mut trace, Event::SetupInvariantRefused { retained_mask: 7 });
    drive(&mut trace, &[Event::SetupInvariantRefused { retained_mask: 3 }, Event::ChildWrap]);
    assert_eq!(trace.phase(), Phase::Returned(Payload::InvariantRefused(3)));
    assert_eq!(trace.owners(BackingKey::File(0)), [ValueId::Child].into_iter().collect::<BTreeSet<_>>());
    assert_eq!(trace.owners(BackingKey::File(1)), [ValueId::Child].into_iter().collect::<BTreeSet<_>>());
    atomic_refusal(&mut trace, Event::SetupOpened(2));
}
#[test]
fn t05_correlation_and_both_leaf_results_keep_attempt_root() {
    for (selection, outcome, expected) in [(Selection::Failure, Correlation::LoaderRefused, Payload::LoaderRefused),
        (Selection::Proof, Correlation::Refused, Payload::CorrelationRefused)] {
        let mut trace = correlated(selection, outcome); drive(&mut trace, &[Event::BoundReturn, Event::ChildWrap]);
        assert_eq!(trace.phase(), Phase::Returned(expected)); assert_eq!(trace.leaf_calls(), 0);
    }
    let mut trace = correlated(Selection::Proof, Correlation::Correlated);
    drive(&mut trace, &[Event::LeafStart, Event::LeafScopeRefused, Event::BoundReturn, Event::ChildWrap]);
    assert_eq!(trace.phase(), Phase::Returned(Payload::PreScopeFailure));
    let mut trace = correlated(Selection::Proof, Correlation::Correlated);
    drive(&mut trace, &[Event::LeafStart, Event::LeafScopeReady, Event::LeafConstruct, Event::LeafOuterBorrow,
        Event::LeafFinish { failures_retained: true }, Event::BoundReturn, Event::ChildWrap]);
    assert_eq!(trace.phase(), Phase::Returned(Payload::Finished { failures_retained: true }));
    let mut foreign = loading(); drive(&mut foreign, &[Event::LoaderReturned { selected: Selection::Proof, executable: false }]);
    atomic_refusal(&mut foreign, Event::Correlate { expected_root: AcquisitionId(2), output_root: AcquisitionId(2), outcome: Correlation::Refused });
    atomic_refusal(&mut foreign, Event::Correlate { expected_root: AcquisitionId(2), output_root: AcquisitionId(1), outcome: Correlation::Correlated });
    drive(&mut foreign, &[Event::Correlate { expected_root: AcquisitionId(2), output_root: AcquisitionId(1), outcome: Correlation::Refused }]);
}
#[test]
fn t06_relocated_leaf_is_not_a_second_invocation() {
    let mut trace = correlated(Selection::Proof, Correlation::Correlated); drive(&mut trace, &[Event::LeafStart]);
    atomic_refusal(&mut trace, Event::LeafStart); assert_eq!(trace.leaf_calls(), 1);
    let mut refused = correlated(Selection::Failure, Correlation::LoaderRefused);
    atomic_refusal(&mut refused, Event::LeafStart); assert_eq!(refused.leaf_calls(), 0);
}
#[test]
fn t07_nested_representation_is_contained_not_added() {
    let trace = normal(); let mut d = declarations(&trace); let baseline = peak(&trace, &d);
    let parent = d.inline.iter().find(|r| r.owner == ValueId::Child).unwrap().clone();
    d.inline.push(InlineDecl { id: RegionId(900), owner: parent.owner, shape: CurrentShape::AdmittedOutcome,
        arena: parent.arena, offset: Bytes(0), capacity: bound(13624), alignment: Bytes(8), live: parent.live, parent: Some(parent.id), funding: parent.funding });
    let pair = d.inline.iter().find(|r| r.owner == ValueId::ScopePair).unwrap().clone();
    for (id, shape, offset, bytes) in [(901, CurrentShape::Correspondence, 0, 24), (902, CurrentShape::Attempt, 24, 32)] {
        d.inline.push(InlineDecl { id: RegionId(id), owner: pair.owner, shape, arena: pair.arena, offset: Bytes(offset),
            capacity: bound(bytes), alignment: Bytes(8), live: pair.live, parent: Some(pair.id), funding: pair.funding });
    }
    let closure = d.inline.iter().find(|r| r.owner == ValueId::Closure).unwrap().clone();
    d.inline.push(InlineDecl { id: RegionId(903), owner: closure.owner, shape: CurrentShape::Attempt, arena: closure.arena,
        offset: Bytes(0), capacity: bound(32), alignment: Bytes(8), live: closure.live, parent: Some(closure.id), funding: closure.funding });
    assert_eq!(peak(&trace, &d), baseline);
    d.inline.last_mut().unwrap().funding = Funding::P0;
    assert!(matches!(rejected(&trace, &d), AssessmentOutcome::InvalidTrace(_)));
    assert_eq!(CurrentShape::ScopePair.observed_size(), Some(Bytes(56)));
    assert_eq!(CurrentShape::DispatchClosure.observed_size(), Some(Bytes(48)));
}
#[test]
fn t08_moves_do_not_mint_physical_identity_or_overlap() {
    let trace = normal(); let mut d = declarations(&trace);
    d.disjoint.clear(); assert_eq!(rejected(&trace, &d), incomplete(MissingFact::Disjointness));
    let mut d = declarations(&trace); d.arenas[0].identity.origin = EvidenceOrigin::Missing;
    assert_eq!(rejected(&trace, &d), incomplete(MissingFact::Evidence));
    let mut d = declarations(&trace); d.inline.retain(|r| r.owner != ValueId::DestroyPayload);
    assert_eq!(rejected(&trace, &d), incomplete(MissingFact::OwnerRegion(ValueId::DestroyPayload)));
}
#[test]
fn t09_checked_union_handles_partial_contained_and_disjoint_spans() {
    assert_eq!(union_width(vec![(0, 48), (32, 80)]), Ok(80));
    assert_eq!(union_width(vec![(0, 48), (8, 16)]), Ok(48));
    assert_eq!(union_width(vec![(0, 48), (48, 80), (90, 100)]), Ok(90));
    assert!(union_width(vec![(8, 7)]).is_err());
}
#[test]
fn t10_missing_capacities_overflow_geometry_and_identity_refuse() {
    let trace = normal(); let baseline = declarations(&trace);
    let mut d = baseline.clone(); d.inline[0].capacity.origin = EvidenceOrigin::Missing;
    assert_eq!(rejected(&trace, &d), incomplete(MissingFact::Evidence));
    let mut d = baseline.clone(); d.backing[0].capacity = bound(0);
    assert_eq!(rejected(&trace, &d), incomplete(MissingFact::Capacity));
    let mut d = baseline.clone(); d.inline[0].offset = Bytes(u64::MAX);
    assert_eq!(rejected(&trace, &d), AssessmentOutcome::ArithmeticOverflow);
    let mut d = baseline.clone(); d.inline[0].alignment = Bytes(3); assert!(matches!(rejected(&trace, &d), AssessmentOutcome::InvalidTrace(_)));
    let mut d = baseline.clone(); let child = d.inline.iter_mut().find(|r| r.owner == ValueId::Child).unwrap(); child.capacity.bound = Bytes(1);
    assert!(matches!(rejected(&trace, &d), AssessmentOutcome::InvalidTrace(_)));
    let mut d = baseline.clone(); d.inline.push(d.inline[0].clone()); assert!(matches!(rejected(&trace, &d), AssessmentOutcome::InvalidTrace(_)));
    let mut d = baseline.clone(); d.arenas[1].identity = d.arenas[0].identity; assert!(matches!(rejected(&trace, &d), AssessmentOutcome::InvalidTrace(_)));
    let mut d = baseline.clone(); d.quote[0] = QuoteTerm::AcquisitionOperation(priced(u64::MAX));
    assert_eq!(rejected(&trace, &d), AssessmentOutcome::ArithmeticOverflow);
    let result = assess_capacity(&trace, &baseline, Bytes(1)); assert!(result.is_model_only());
    assert!(matches!(result.outcome, AssessmentOutcome::InsufficientCapacity { .. }));
}
#[test]
fn t11_cancellation_clone_has_one_backing_with_two_owners() {
    let mut trace = correlated(Selection::Proof, Correlation::Correlated); drive(&mut trace, &[Event::LeafStart]);
    assert_eq!(trace.owners(BackingKey::Cancellation), [ValueId::Body, ValueId::Leaf].into_iter().collect::<BTreeSet<_>>());
    drive(&mut trace, &[Event::LeafScopeReady, Event::LeafConstruct, Event::LeafOuterBorrow,
        Event::LeafFinish { failures_retained: false }]); assert_eq!(trace.owners(BackingKey::Cancellation), [ValueId::Body].into_iter().collect::<BTreeSet<_>>());
    drive(&mut trace, &[Event::BoundReturn, Event::ChildWrap]); wrapper_gone(&mut trace);
    assert!(trace.owners(BackingKey::Cancellation).is_empty());
    drive(&mut trace, &[Event::TokenReturnSome, Event::ReleaseChild(ChildId(7)), Event::RetireAcquisition]);
    let mut d = declarations(&trace); let before = peak(&trace, &d);
    d.backing.iter_mut().find(|b| b.key == BackingKey::Cancellation).unwrap().capacity = bound(16);
    assert_eq!(peak(&trace, &d), before + 8);
    let copy = d.backing.iter().find(|b| b.key == BackingKey::Cancellation).unwrap().clone(); d.backing.push(copy);
    assert!(matches!(rejected(&trace, &d), AssessmentOutcome::InvalidTrace(_)));
}
#[test]
fn t12_short_views_cannot_destroy_or_release_owned_pointees() {
    let mut trace = returned(); drive(&mut trace, &[Event::ObserveBegin]);
    atomic_refusal(&mut trace, Event::DestroyBegin); atomic_refusal(&mut trace, Event::ForgetChild);
    drive(&mut trace, &[Event::ObserveEnd]); atomic_refusal(&mut trace, Event::ObserveBegin);
    wrapper_gone(&mut trace); drive(&mut trace, &[Event::TokenReturnSome, Event::ReleaseChild(ChildId(7)), Event::RetireAcquisition]);
    let mut d = declarations(&trace); d.inline.iter_mut().find(|r| r.owner == ValueId::View).unwrap().shape = CurrentShape::AdmittedOutcome;
    assert!(matches!(rejected(&trace, &d), AssessmentOutcome::InvalidTrace(_)));
}
#[test]
fn t13_explicit_destroy_has_separate_payload_wrapper_and_token_phases() {
    let mut trace = returned(); drive(&mut trace, &[Event::DestroyBegin]);
    atomic_refusal(&mut trace, Event::TokenReturnSome); atomic_refusal(&mut trace, Event::TakeReservation);
    drive(&mut trace, &[Event::TakePayload, Event::StartPayloadDrop]); atomic_refusal(&mut trace, Event::TokenReturnSome);
    drive(&mut trace, &[Event::CompletePayloadDrop, Event::TakeReservation, Event::StartWrapperDrop]);
    atomic_refusal(&mut trace, Event::TokenReturnSome); drive(&mut trace, &[Event::CompleteWrapperDrop, Event::TokenReturnNone]);
    atomic_refusal(&mut trace, Event::ReleaseChild(ChildId(7))); drive(&mut trace, &[Event::RetireAcquisition]);
    assert!(trace.charges().child_storage_retained); assert_eq!(trace.phase(), Phase::Terminal(Terminal::NoToken));
}
#[test]
fn t14_ordinary_drop_never_returns_token_or_refunds_charge() {
    let mut trace = returned(); drive(&mut trace, &[Event::OrdinaryDropBegin, Event::TakePayload, Event::StartPayloadDrop,
        Event::CompletePayloadDrop, Event::StartWrapperDrop, Event::CompleteWrapperDrop]);
    atomic_refusal(&mut trace, Event::TokenReturnSome); atomic_refusal(&mut trace, Event::ReleaseChild(ChildId(7)));
    drive(&mut trace, &[Event::RetireAcquisition]); assert!(trace.charges().child_storage_retained);
    assert!(trace.charges().child_work_committed && trace.charges().child_peak_retained);
}
#[test]
fn t15_unwind_cleanup_is_separate_and_cannot_create_token() {
    let mut quote = scoped(); drive(&mut quote, &[Event::ParentReady]);
    let mut reserve = scoped(); drive(&mut reserve, &[Event::ParentReady, Event::QuoteReady]);
    let mut dispatch = scoped(); drive(&mut dispatch, &[Event::ParentReady, Event::QuoteReady, Event::ReserveSuccess, Event::ClosureConstruct]);
    let setup_trace = setup(); let mut setup_prefix = setup(); drive(&mut setup_prefix, &[Event::SetupOpened(0), Event::SetupOpened(1)]);
    let loader = loading(); let mut correlation = loading();
    drive(&mut correlation, &[Event::LoaderReturned { selected: Selection::Proof, executable: false }]);
    let mut leaf = correlated(Selection::Proof, Correlation::Correlated); drive(&mut leaf, &[Event::LeafStart]);
    let payload = payload_dropping(); let mut wrapper = payload.clone();
    drive(&mut wrapper, &[Event::CompletePayloadDrop, Event::TakeReservation, Event::StartWrapperDrop]);
    let mut ordinary_payload = returned(); drive(&mut ordinary_payload, &[Event::OrdinaryDropBegin, Event::TakePayload, Event::StartPayloadDrop]);
    let mut ordinary_wrapper = ordinary_payload.clone(); drive(&mut ordinary_wrapper, &[Event::CompletePayloadDrop, Event::StartWrapperDrop]);
    for (mut trace, site) in [(quote, UnwindSite::QuoteCall), (reserve, UnwindSite::ReserveCall), (dispatch, UnwindSite::DispatchCall),
        (setup_trace, UnwindSite::SetupCall), (setup_prefix, UnwindSite::SetupCall), (loader, UnwindSite::LoaderCall), (correlation, UnwindSite::CorrelationCall),
        (leaf, UnwindSite::LeafCall), (payload, UnwindSite::PayloadDrop), (wrapper, UnwindSite::WrapperDrop),
        (ordinary_payload, UnwindSite::PayloadDrop), (ordinary_wrapper, UnwindSite::WrapperDrop)] {
        drive(&mut trace, &[Event::Unwind(site)]); atomic_refusal(&mut trace, Event::TokenReturnSome);
        atomic_refusal(&mut trace, Event::UnwindResume);
        drive(&mut trace, &[Event::UnwindCleanupStart, Event::UnwindCleanupReturn, Event::UnwindResume, Event::RetireAcquisition]);
        assert_eq!(trace.phase(), Phase::Terminal(Terminal::Unwound)); assert!(trace.charges().acquisition_retained);
        assert_eq!(rejected(&trace, &declarations(&trace)), incomplete(MissingFact::UnreleasedOwner));
    }
    let mut capture = setup(); atomic_refusal(&mut capture, Event::Unwind(UnwindSite::CaptureMoves));
}
#[test]
fn t16_forget_keeps_child_backing_charge_and_root_barrier() {
    let mut trace = returned(); let files = trace.owners(BackingKey::File(0)); assert_eq!(files, [ValueId::Child].into_iter().collect::<BTreeSet<_>>());
    drive(&mut trace, &[Event::ForgetChild]); assert_eq!(trace.owners(BackingKey::File(0)), [ValueId::Forgotten].into_iter().collect::<BTreeSet<_>>());
    atomic_refusal(&mut trace, Event::DestroyBegin); atomic_refusal(&mut trace, Event::ReleaseChild(ChildId(7)));
    drive(&mut trace, &[Event::RetireAcquisition]); assert!(trace.sticky() && trace.charges().acquisition_retained && trace.charges().child_storage_retained);
    assert_eq!(rejected(&trace, &declarations(&trace)), incomplete(MissingFact::UnreleasedOwner));
}
#[test]
fn t17_child_token_identity_underflow_and_p0_funding_are_distinct() {
    let mut trace = returned(); wrapper_gone(&mut trace); drive(&mut trace, &[Event::TokenReturnSome]);
    atomic_refusal(&mut trace, Event::ReleaseChild(ChildId(1))); atomic_refusal(&mut trace, Event::RetireAcquisition);
    drive(&mut trace, &[Event::ReleaseChildUnderflow(ChildId(7))]); assert!(trace.charges().child_storage_retained);
    atomic_refusal(&mut trace, Event::ReleaseChild(ChildId(7))); drive(&mut trace, &[Event::RetireAcquisition]);
    assert_eq!(trace.phase(), Phase::Terminal(Terminal::ReleaseUnderflow)); assert!(trace.charges().acquisition_retained);
    let trace = normal(); let mut d = declarations(&trace);
    d.inline.iter_mut().find(|r| r.owner == ValueId::Token).unwrap().funding = Funding::Child(Component::C5);
    assert!(matches!(rejected(&trace, &d), AssessmentOutcome::InvalidTrace(_)));
    let mut d = declarations(&trace); d.backing[0].funding = Funding::Child(Component::C0);
    assert!(matches!(rejected(&trace, &d), AssessmentOutcome::InvalidTrace(_)));
}
#[test]
fn t18_every_retained_quote_term_and_positive_unit_is_required() {
    let trace = normal(); let baseline = declarations(&trace);
    for i in 0..10 { let mut d = baseline.clone(); d.quote.remove(i); assert_eq!(rejected(&trace, &d), incomplete(MissingFact::QuoteTerm)); }
    let mut d = baseline.clone(); d.quote[4] = QuoteTerm::Child { component: Component::C0, work: priced(0), storage: bound(1_000_000) };
    assert_eq!(rejected(&trace, &d), incomplete(MissingFact::Work));
    let mut d = baseline.clone(); d.quote[4] = QuoteTerm::Child { component: Component::C0, work: priced(10), storage: bound(0) };
    assert_eq!(rejected(&trace, &d), incomplete(MissingFact::Capacity));
    let mut d = baseline.clone(); d.quote.push(d.quote[4].clone()); assert!(matches!(rejected(&trace, &d), AssessmentOutcome::InvalidTrace(_)));
    let child_total = match assess_capacity(&trace, &baseline, Bytes(10_000_000)).outcome {
        AssessmentOutcome::ModelFitsCapacity { retained_child_storage_sum, .. } => retained_child_storage_sum, other => panic!("{other:?}") };
    assert_eq!(child_total, Bytes(6_000_000)); // Not replaced by the smaller union envelope.
}
fn reviewed(origin: EvidenceOrigin) -> EvidenceOrigin { match origin { EvidenceOrigin::Synthetic(e) => EvidenceOrigin::ReviewedBound(e), other => other } }
#[test]
fn t19_binding_drift_and_reviewed_looking_bounds_never_grant_authority() {
    let trace = normal(); let mut d = declarations(&trace);
    for arena in &mut d.arenas { arena.identity.origin = reviewed(arena.identity.origin); }
    for relation in &mut d.disjoint { relation.evidence = reviewed(relation.evidence); }
    for inline in &mut d.inline { inline.capacity.origin = reviewed(inline.capacity.origin); }
    for backing in &mut d.backing { backing.capacity.origin = reviewed(backing.capacity.origin); backing.completion = reviewed(backing.completion); }
    for term in &mut d.quote { match term {
        QuoteTerm::AcquisitionOperation(w) | QuoteTerm::AcquisitionCleanup(w) => w.origin = reviewed(w.origin),
        QuoteTerm::AcquisitionStorage(b) => b.origin = reviewed(b.origin),
        QuoteTerm::P0 { work, storage } | QuoteTerm::Child { work, storage, .. } => { work.origin = reviewed(work.origin); storage.origin = reviewed(storage.origin); }
    } }
    assert!(assess_capacity(&trace, &d, Bytes(10_000_000)).is_model_only()); assert!(peak(&trace, &d) > 0);
    let bad = Evidence { id: EvidenceId(99), binding: Binding { target: "different-target", ..Binding::CURRENT } };
    d.arenas[0].identity.origin = EvidenceOrigin::ReviewedBound(bad);
    let result = assess_capacity(&trace, &d, Bytes(10_000_000)); assert!(result.is_model_only()); assert!(matches!(result.outcome, AssessmentOutcome::InvalidTrace(_)));
}
#[test]
fn t20_capacity_is_maximum_over_all_segments_and_requires_completion() {
    let trace = normal(); let mut d = declarations(&trace); let old_peak = peak(&trace, &d);
    let index = d.inline.iter().position(|r| r.owner == ValueId::Parent).unwrap(); let mut late = d.inline[index].clone();
    d.inline[index].capacity = bound(10_000); d.inline[index].live.end = End::At(1);
    late.id = RegionId(999); late.live.begin = 1; d.inline.push(late);
    let result = assess_capacity(&trace, &d, Bytes(old_peak + 100)); assert!(result.is_model_only());
    assert!(matches!(result.outcome, AssessmentOutcome::InsufficientCapacity { .. }));
    let mut d = declarations(&trace); d.backing.iter_mut().find(|b| b.key == BackingKey::Cancellation).unwrap().completion = EvidenceOrigin::Missing;
    assert_eq!(rejected(&trace, &d), incomplete(MissingFact::FinalDestruction(BackingKey::Cancellation)));
}
