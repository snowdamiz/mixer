        // Independent desired-property witness. Test-only construction uses the
        // frozen candidate's real admitted core and real validator-created proof.
        // All ownership/correlation/retirement functions remain production code.
        #[test]
        fn independent_result_live_acquisition_retirement_v1() {
            let r = root();
            let trace = Rc::new(Trace::default());
            let owner = admitted(&r, &trace);
            let (expected, attempt) = owner.correlation_scope_core_v1().unwrap();
            let supplied = carrier(&owner.expected, &trace);
            let proof_pointer = supplied.selected.as_ref().unwrap().proof.source().as_ptr();
            let retained_result = match correlate_core_v1(attempt, supplied, &expected) {
                Ok(original) => original,
                Err(_) => panic!("positive control unexpectedly refused"),
            };
            drop(expected);
            let before = r.usage.get();
            let AdmittedImmutableOwnerCoreV1 { owned, .. } = owner;
            let token = match retire_acquired_owner_core_v1(owned, &mut bridge(&trace)) {
                AcquisitionRetirementOutcomeV1::Complete(token) => token,
                AcquisitionRetirementOutcomeV1::Retained(_) => {
                    // Retention is a valid fail-closed desired outcome.
                    assert_eq!(r.usage.get().storage, before.storage);
                    return;
                }
            };
            let while_token_owned = r.usage.get();
            token.release_v1();
            let after_release = r.usage.get();
            let live_proof = &retained_result.selected.as_ref().unwrap().proof;
            assert_eq!(live_proof.source().as_ptr(), proof_pointer);
            assert_eq!(live_proof.source().len(), 1947);
            assert_eq!(retained_result.files.each_ref().map(|guard| guard.tag), [20, 21, 22]);
            assert_eq!(retained_result.executable.as_ref().unwrap().tag, 23);
            assert_eq!(*trace.drops.borrow(), (0..13).collect::<Vec<_>>());
            eprintln!("INDEPENDENT_RETIREMENT_WITNESS before_storage={} token_storage={} released_storage={} live_proof_bytes={} live_loader_tags=20,21,22,23 acquisition_drops={:?}",
                before.storage, while_token_owned.storage, after_release.storage,
                live_proof.source().len(), trace.drops.borrow());
            // Required PA06/H11 property: complete acquisition release must not
            // discharge its fixed correlation/result/proof overlap while live.
            assert_eq!(after_release.storage, before.storage,
                "desired property failed: acquisition storage released while actual correlated proof and four original guard resources remain live");
            drop(retained_result);
        }
