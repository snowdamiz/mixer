// Independent additions inside the existing private guard-test module.
// These call the actual production core. No substitute leaf/ownership machine.
fn independent_shape_carrier_v1(
    expected: &LoaderProvenanceV1, trace: &Rc<Trace>, has_executable: bool,
) -> LoaderCarrierCoreV1<Guard> {
    let mut supplied = carrier(expected, trace);
    if !has_executable { drop(supplied.executable.take()); }
    supplied
}

fn independent_resource_tags_v1(has_executable: bool) -> Vec<usize> {
    if has_executable { vec![20, 21, 22, 23] } else { vec![20, 21, 22] }
}

fn independent_initial_drop_tags_v1(has_executable: bool) -> Vec<usize> {
    if has_executable { Vec::new() } else { vec![23] }
}

fn independent_inspect_matched_v1(
    held: &RootBoundV1<'_, LoaderCarrierCoreV1<Guard>>,
    original_root: &BootstrapLedgerV1,
    pointer: *const u8,
    has_executable: bool,
    original_usage: LoaderUsageV1,
) {
    assert!(std::ptr::eq(held.root, original_root));
    let selected = held.payload.selected.as_ref().unwrap();
    assert_eq!(selected.proof.source().as_ptr(), pointer);
    assert_eq!(selected.proof.source().len(), 1947);
    assert_eq!(selected.proof.source(), wasm_source());
    assert_eq!(held.payload.files.each_ref().map(|guard| guard.tag), [20, 21, 22]);
    assert_eq!(held.payload.executable.as_ref().map(|guard| guard.tag), has_executable.then_some(23));
    assert_eq!(held.payload.usage, original_usage);
}

#[test]
fn independent_ir02_h01_matched_some_none_and_both_destruction_orders_v1() {
    let mut count = 0;
    for has_executable in [false, true] {
        for result_before_owner in [false, true] {
            let original_root = root();
            let trace = Rc::new(Trace::default());
            let owner = admitted(&original_root, &trace);
            let (held, pointer, original_usage) = {
                let (expected, attempt) = owner.correlation_scope_core_v1().unwrap();
                let supplied = independent_shape_carrier_v1(&owner.expected, &trace, has_executable);
                let pointer = supplied.selected.as_ref().unwrap().proof.source().as_ptr();
                let usage = supplied.usage;
                let held = match correlate_core_v1(attempt, supplied, &expected).into_result_v1() {
                    Ok(held) => held, Err(_) => panic!("independent matched refusal"),
                };
                (held, pointer, usage)
            };
            let usage_before = original_root.usage.get();
            let retained = assert_correlation_barrier_v1(owner, &trace);
            let mut expected_drops = independent_initial_drop_tags_v1(has_executable);
            assert_eq!(*trace.drops.borrow(), expected_drops);
            if result_before_owner {
                independent_inspect_matched_v1(&held, &original_root, pointer, has_executable, original_usage);
                drop(held);
                expected_drops.extend(independent_resource_tags_v1(has_executable));
                assert_eq!(*trace.drops.borrow(), expected_drops);
                drop(retained);
                expected_drops.extend(0..13);
            } else {
                drop(retained);
                expected_drops.extend(0..13);
                assert_eq!(*trace.drops.borrow(), expected_drops);
                independent_inspect_matched_v1(&held, &original_root, pointer, has_executable, original_usage);
                drop(held);
                expected_drops.extend(independent_resource_tags_v1(has_executable));
            }
            assert_eq!(*trace.drops.borrow(), expected_drops);
            assert_eq!(original_root.usage.get(), usage_before);
            assert!(original_root.reserved.get());
            count += 1;
            eprintln!("INDEPENDENT_IR02 matched has_executable={has_executable} result_before_owner={result_before_owner} original_root_live=true original_proof_bytes=1947 original_usage={original_usage:?} root_usage={usage_before:?} drops={expected_drops:?} product_leaf_calls=0");
        }
    }
    assert_eq!(count, 4);
}

#[test]
fn independent_ir02_h02_original_io_and_validation_some_none_v1() {
    let mut count = 0;
    for has_executable in [false, true] {
        for io_failure in [false, true] {
            let original_root = root();
            let trace = Rc::new(Trace::default());
            let owner = admitted(&original_root, &trace);
            let marker_drops = std::sync::Arc::new(std::sync::atomic::AtomicUsize::new(0));
            let (held, pointer, original_validation) = {
                let (expected, attempt) = owner.correlation_scope_core_v1().unwrap();
                let mut supplied = independent_shape_carrier_v1(&owner.expected, &trace, has_executable);
                let validation = validate_swift_reactor(b"invalid", owner.expected.validation_budget, &Cancellation::default()).err().unwrap();
                let original_io = io_failure.then(|| io::Error::new(io::ErrorKind::Other, OriginalIoMarkerV1 { id: 0x27102, drops: marker_drops.clone() }));
                let pointer = original_io.as_ref().map(|error| error.get_ref().unwrap().downcast_ref::<OriginalIoMarkerV1>().unwrap() as *const OriginalIoMarkerV1);
                supplied.selected = Err(LoaderFailureV1 {
                    io: original_io, validation: (!io_failure).then_some(validation),
                    ..LoaderFailureV1::new(if io_failure { Refusal::Io } else { Refusal::Validation }, Role::Build, 37, 7)
                });
                let held = match correlate_core_v1(attempt, supplied, &expected).into_result_v1() {
                    Ok(held) => held, Err(_) => panic!("independent loader error correlation"),
                };
                (held, pointer, validation)
            };
            let usage_before = original_root.usage.get();
            drop(assert_correlation_barrier_v1(owner, &trace));
            let failure = held.payload.selected.as_ref().err().unwrap();
            assert_eq!(failure.role, Role::Build);
            assert_eq!(failure.offset, 37); assert_eq!(failure.attempts, 7);
            if io_failure {
                let marker = failure.original_io().unwrap().get_ref().unwrap().downcast_ref::<OriginalIoMarkerV1>().unwrap();
                assert_eq!(Some(marker as *const OriginalIoMarkerV1), pointer);
                assert_eq!(marker.id, 0x27102);
                assert_eq!(marker_drops.load(std::sync::atomic::Ordering::SeqCst), 0);
                assert!(failure.original_validation().is_none());
            } else {
                // SwiftValidationFailure is entirely Copy scalar data; this
                // verifies every original field, not imaginary heap identity.
                assert_eq!(failure.original_validation(), Some(&original_validation));
                assert!(failure.original_io().is_none());
            }
            assert!(std::ptr::eq(held.root, &original_root));
            assert_eq!(held.payload.files.each_ref().map(|guard| guard.tag), [20, 21, 22]);
            assert_eq!(held.payload.executable.as_ref().map(|guard| guard.tag), has_executable.then_some(23));
            assert_eq!(held.payload.usage.hash_bytes, 912);
            assert_eq!(held.payload.usage.source_equality_bytes, 1947);
            drop(held);
            assert_eq!(marker_drops.load(std::sync::atomic::Ordering::SeqCst), usize::from(io_failure));
            let mut drops = independent_initial_drop_tags_v1(has_executable);
            drops.extend(0..13); drops.extend(independent_resource_tags_v1(has_executable));
            assert_eq!(*trace.drops.borrow(), drops);
            assert_eq!(original_root.usage.get(), usage_before);
            count += 1;
            eprintln!("INDEPENDENT_IR02 diagnostic has_executable={has_executable} io_failure={io_failure} original_io_pointer_preserved={} validation_all_fields_equal={} root_usage={usage_before:?} drops={drops:?} product_leaf_calls=0", io_failure, !io_failure);
        }
    }
    assert_eq!(count, 4);
}

#[test]
fn independent_ir02_h03_refused_originals_some_none_v1() {
    let mut count = 0;
    for has_executable in [false, true] {
        for kind in 0..3 {
            let original_root = root(); let foreign_root = root();
            let trace = Rc::new(Trace::default());
            let foreign_trace = Rc::new(Trace::default());
            let owner = admitted(&original_root, &trace);
            let foreign_owner = admitted(&foreign_root, &foreign_trace);
            let marker_drops = std::sync::Arc::new(std::sync::atomic::AtomicUsize::new(0));
            let (held, pointer, io_pointer, validation_original) = {
                let (mut expected, attempt) = owner.correlation_scope_core_v1().unwrap();
                let (foreign, _foreign_attempt) = foreign_owner.correlation_scope_core_v1().unwrap();
                let mut supplied = independent_shape_carrier_v1(&owner.expected, &trace, has_executable);
                let pointer = supplied.selected.as_ref().unwrap().proof.source().as_ptr();
                let validation = validate_swift_reactor(b"invalid", owner.expected.validation_budget, &Cancellation::default()).err().unwrap();
                let mut io_pointer = None;
                if kind == 0 { supplied.selected.as_mut().unwrap().provenance.source[0] ^= 1; }
                if kind == 1 {
                    expected.association += 1;
                    let original = io::Error::new(io::ErrorKind::Other, OriginalIoMarkerV1 { id: 0x27103, drops: marker_drops.clone() });
                    io_pointer = Some(original.get_ref().unwrap().downcast_ref::<OriginalIoMarkerV1>().unwrap() as *const OriginalIoMarkerV1);
                    supplied.selected = Err(LoaderFailureV1 { io: Some(original), validation: Some(validation), ..LoaderFailureV1::new(Refusal::Validation, Role::Source, 53, 11) });
                }
                let held = correlate_core_v1(attempt, supplied, if kind == 2 { &foreign } else { &expected });
                (held, pointer, io_pointer, validation)
            };
            assert!(std::ptr::eq(held.root, &original_root));
            assert!(!std::ptr::eq(held.root, &foreign_root));
            let before = original_root.usage.get(); let foreign_before = foreign_root.usage.get();
            drop(assert_correlation_barrier_v1(owner, &trace));
            drop(assert_correlation_barrier_v1(foreign_owner, &foreign_trace));
            let held = held.into_result_v1().err().unwrap();
            let (failure, carrier) = &held.payload;
            assert_eq!(failure.kind, if kind == 0 { BootstrapFailureV1::Correlation(0) } else { BootstrapFailureV1::LiveOwner });
            if kind == 1 {
                let failure = carrier.selected.as_ref().err().unwrap();
                assert_eq!(failure.role, Role::Source); assert_eq!(failure.offset, 53); assert_eq!(failure.attempts, 11);
                assert_eq!(failure.original_validation(), Some(&validation_original));
                let marker = failure.original_io().unwrap().get_ref().unwrap().downcast_ref::<OriginalIoMarkerV1>().unwrap();
                assert_eq!(Some(marker as *const OriginalIoMarkerV1), io_pointer); assert_eq!(marker.id, 0x27103);
                assert_eq!(marker_drops.load(std::sync::atomic::Ordering::SeqCst), 0);
            } else {
                let proof = &carrier.selected.as_ref().unwrap().proof;
                assert_eq!(proof.source().as_ptr(), pointer); assert_eq!(proof.source().len(), 1947);
            }
            assert_eq!(carrier.files.each_ref().map(|guard| guard.tag), [20,21,22]);
            assert_eq!(carrier.executable.as_ref().map(|guard|guard.tag), has_executable.then_some(23));
            assert_eq!(carrier.usage.hash_bytes, 912); assert_eq!(carrier.usage.source_equality_bytes, 1947);
            drop(held);
            assert_eq!(marker_drops.load(std::sync::atomic::Ordering::SeqCst), usize::from(kind == 1));
            let mut drops = independent_initial_drop_tags_v1(has_executable);
            drops.extend(0..13); drops.extend(independent_resource_tags_v1(has_executable));
            assert_eq!(*trace.drops.borrow(), drops); assert_eq!(*foreign_trace.drops.borrow(), (0..13).collect::<Vec<_>>());
            assert_eq!(original_root.usage.get(), before); assert_eq!(foreign_root.usage.get(), foreign_before);
            count += 1;
            eprintln!("INDEPENDENT_IR02 refused has_executable={has_executable} kind={kind} original_attempt_root=true original_usage={before:?} foreign_usage={foreign_before:?} drops={drops:?} product_leaf_calls=0");
        }
    }
    assert_eq!(count, 6);
}

#[test]
fn independent_ir02_h04_forget_scoped_barrier_some_none_v1() {
    let mut count = 0;
    for has_executable in [false, true] {
        for kind in 0..4 {
            let original_root = root(); let trace = Rc::new(Trace::default());
            let owner = admitted(&original_root, &trace);
            let held = {
                let (mut expected, attempt) = owner.correlation_scope_core_v1().unwrap();
                let mut supplied = independent_shape_carrier_v1(&owner.expected, &trace, has_executable);
                match kind {
                    1 => supplied.selected = Err(LoaderFailureV1::new(Refusal::Io, Role::Build, 61, 13)),
                    2 => supplied.selected.as_mut().unwrap().provenance.source[0] ^= 1,
                    3 => expected.association += 1,
                    _ => (),
                }
                correlate_core_v1(attempt, supplied, &expected)
            };
            let before = original_root.usage.get();
            assert!(std::ptr::eq(held.root, &original_root));
            std::mem::forget(held);
            drop(assert_correlation_barrier_v1(owner, &trace));
            let mut drops = independent_initial_drop_tags_v1(has_executable); drops.extend(0..13);
            assert_eq!(*trace.drops.borrow(), drops); assert_eq!(original_root.usage.get(), before); assert!(original_root.reserved.get());
            count += 1;
            eprintln!("INDEPENDENT_IR02 forgotten has_executable={has_executable} kind={kind} original_root_still_observable=true usage={before:?} drops={drops:?} durable_post_root_funding_proved=false product_leaf_calls=0");
        }
    }
    assert_eq!(count, 8);
}
