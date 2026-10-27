// Derived by exact recorded replacements from accepted original adopt_body.
#[cfg(test)]
impl RuntimeControl {
    pub(super) fn correction_probe_adopt_body_v1(
        body: AdoptionBodyV1,
        budget: SwiftRunBudget,
        started: Instant,
        cancellation: Cancellation,
        boundary:CorrectionBoundaryV1,
        storage:CorrectionEarlyStorageV1,
    ) -> CorrectionCoreReturnV1 {
        let validation = body.proof().usage();
        let mut control = Self {
            owner: 0,
            budget,
            started,
            deadline: started,
            deadline_origin: SwiftDeadlineOrigin::Run,
            cancellation,
            validation,
            reservations: SwiftReservations::default(),
            live: SwiftLiveUsage::default(),
            cache_work: 0,
            execution_work: 0,
            instruction_fuel: 0,
            instructions: 0,
            host_calls: 0,
            cleanup_invariant: None,
            first_failure: None,
            control_header: None,
            cancellation_backing: None,
            construction: None,
        };
        let cursor = Cursor::adoption();
        let mut source = None;
        let mut metadata = None;
        let result = (|| {
            control.check_budget(cursor)?;
            control.deadline = started
                .checked_add(Duration::from_millis(budget.deadline_ms))
                .ok_or_else(|| {
                    control.fail(
                        cursor,
                        Fault::new(
                            SwiftRunFailureKind::InvalidBudget,
                            "swift_run_deadline_overflow",
                        ),
                        None,
                    )
                })?;
            control.check(cursor)?;
            control.owner = NEXT_OWNER
                .try_update(Ordering::Relaxed, Ordering::Relaxed, |n| n.checked_add(1))
                .map_err(|_| {
                    control.fail(
                        cursor,
                        Fault::new(SwiftRunFailureKind::Invariant, "swift_run_owner_exhausted")
                            .limit(SwiftRunResource::OwnerIdentity, u64::MAX, u64::MAX - 1),
                        None,
                    )
                })?;
            source = Some(control.admit(
                SwiftReservationCategory::RetainedSource,
                validation.source_bytes,
                cursor,
            )?);
            metadata = Some(control.admit(
                SwiftReservationCategory::RetainedMetadata,
                validation.metadata_reserved,
                cursor,
            )?);
            control.control_header =
                Some(control.admit(SwiftReservationCategory::Shared, size_of::<Self>(), cursor)?);
            control.cancellation_backing = Some(control.admit(
                SwiftReservationCategory::Shared,
                Cancellation::requested_backing_layout().size(),
                cursor,
            )?);
            let construction = foundation_construction_bytes().and_then(|base|base.checked_add(size_of::<CorrectionPreScopePlacesV1>())).ok_or_else(|| {
                control.fail(
                    cursor,
                    Fault::new(SwiftRunFailureKind::Invariant, "swift_run_layout_overflow"),
                    None,
                )
            })?;
            control.construction = Some(control.admit(
                SwiftReservationCategory::Construction,
                construction,
                cursor,
            )?);
            // Test-only event at the exact original post-Construction final check.
            match boundary {
                CorrectionBoundaryV1::FinalCancel=>control.cancellation.cancel(),
                CorrectionBoundaryV1::FinalDeadline=>control.deadline=Instant::now(),
                CorrectionBoundaryV1::None=>{},
            }
            control.check(cursor)
        })();
        if let Err(mut failure) = result {
            // Actual storage destruction precedes every proof refund. Refunding
            // control's own headers is possible only by consuming/dropping the
            // entire closure below; no admission can follow that operation.
            drop(body);
            let retirement=storage.retire(&mut control);
            if let Some(ticket) = source {
                let _ = control.refund(ticket);
            }
            if let Some(ticket) = metadata {
                let _ = control.refund(ticket);
            }
            failure.after_cleanup = Some(control.finish_owned_cleanup(None));
            return Err(CorrectionPreScopeFailureV1 {primary:failure,retirement});
        }
        Ok((
            control,
            AdoptedProof {
                body,
                source: source.expect("successful sealed adoption owns source ticket"),
                metadata: metadata.expect("successful sealed adoption owns metadata ticket"),
            },
        ))
    }

}
