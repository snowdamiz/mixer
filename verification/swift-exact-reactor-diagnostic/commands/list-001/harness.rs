// Isolated test-only caller. Included after the unchanged lifecycle_tests.rs.
// This observer has no production accounting or caller-stack acceptance claim.
mod exact_diagnostic {
    use super::*;
    use crate::experimental_swift_reactor::{
        SwiftReactorObservations, SwiftValidationFailure, SwiftValidationUsage,
    };
    use crate::experimental_wasi::{WasiReservations, WasiUsage};
    use std::io::Write;

    trait Json { fn json(&self) -> String; }
    fn quote(s: &str) -> String {
        let mut out = String::from("\"");
        for c in s.chars() {
            match c {
                '"' => out.push_str("\\\""),
                '\\' => out.push_str("\\\\"),
                '\n' => out.push_str("\\n"),
                '\r' => out.push_str("\\r"),
                '\t' => out.push_str("\\t"),
                c if (c as u32) < 32 => out.push_str(&format!("\\u{:04x}", c as u32)),
                c => out.push(c),
            }
        }
        out.push('"');
        out
    }
    impl Json for str { fn json(&self) -> String { quote(self) } }
    impl Json for &str { fn json(&self) -> String { quote(self) } }
    impl<T: Json> Json for Option<T> {
        fn json(&self) -> String { self.as_ref().map(Json::json).unwrap_or_else(|| "null".into()) }
    }
    macro_rules! numbers { ($($t:ty),*) => { $(impl Json for $t { fn json(&self)->String {self.to_string()} })* }; }
    numbers!(u32, u64, usize, i32, bool);
    macro_rules! enums { ($($t:ty),*) => { $(impl Json for $t { fn json(&self)->String { quote(&format!("{:?}", self)) } })* }; }
    enums!(SwiftRunStage, SwiftRunResource, SwiftRunFailureKind, SwiftCleanupInvariant,
        SwiftDeadlineOrigin, crate::experimental_wasi::WasiFailure,
        crate::experimental_swift_reactor::SwiftValidationFailureKind,
        crate::experimental_swift_reactor::SwiftValidationResource);
    macro_rules! object { ($t:ty; $($field:ident),+ $(,)?) => {
        impl Json for $t { fn json(&self) -> String {
            let fields = [$(format!("{}:{}", quote(stringify!($field)), self.$field.json())),+];
            format!("{{{}}}", fields.join(","))
        }}
    }; }
    object!(SwiftValidationBudget; source_bytes, metadata_bytes, scratch_bytes, work_credits, deadline_ms);
    object!(SwiftValidationUsage; input_visible_bytes, source_bytes, metadata_reserved,
        scratch_reserved, metadata_peak_reserved, scratch_peak_reserved, total_peak_reserved,
        work_used, elapsed_micros, deadline_ms);
    object!(SwiftValidationFailure; kind, code, function, offset, resource, attempted, limit, usage);
    object!(SwiftReactorObservations; types, type_parameters, imported_functions, defined_functions,
        validated_bodies, instructions, globals, exports, data_segments, element_segments,
        max_parameters_plus_locals, max_operand_values, max_control_depth, memory_minimum,
        memory_declared_maximum, memory_host_maximum, table_minimum, table_declared_maximum);
    object!(SwiftRunBudget; source_bytes, metadata_bytes, cache_bytes, cache_entry_bytes,
        cache_entries, active_pins, cache_work, frames, values, controls, memory_pages,
        state_bytes, combined_bytes, instruction_fuel, execution_work, host_calls, deadline_ms);
    object!(SwiftReservationUsage; current, peak);
    object!(SwiftReservations; retained_source, retained_metadata, cache, state, wasi, shared,
        construction, combined, live_tickets, peak_tickets);
    object!(SwiftLiveUsage; cache_entries, active_pins, frames, values, controls, memory_pages);
    object!(WasiBudget; calls, transfer_bytes, work, one_transfer_bytes, iovecs, log_bytes, deadline_ms);
    object!(WasiGrants; secure_random, realtime, monotonic, stdout, stderr);
    object!(WasiReservations; fixed_state_bytes, staging_bytes, rollback_bytes, stdout_bytes,
        stderr_bytes, current_bytes, peak_bytes);
    object!(WasiUsage; calls, work, transfer_bytes, random_bytes, log_bytes, failures, reservations);
    object!(SwiftRunUsage; reservations, live, cache_work, execution_work, instruction_fuel,
        instructions, host_calls, cleanup_invariant, elapsed_micros, deadline_ms, deadline_origin,
        deadline_overshoot_micros, validation, wasi);
    object!(SwiftRunFailure; stage, kind, code, function, offset, resource, attempted, limit,
        observed_capacity, deadline_origin, wasi_failure, guest_exit, at_failure, after_cleanup);

    fn emit(event: &str, payload: String) {
        // Every event is a complete standalone JSON object. Flush before continuing.
        println!("MIXER_EXACT {{\"event\":{},\"payload\":{}}}", quote(event), payload);
        std::io::stdout().flush().expect("flush diagnostic evidence");
    }
    fn snapshot(event: &str, owner: &SwiftReactorInstance) {
        let state = owner.state.as_ref().expect("actual state");
        let wasi = owner.wasi.as_ref().expect("actual WASI");
        emit(event, format!("{{\"usage\":{},\"lifecycle\":{},\"memory_bytes\":{},\"stdout\":{},\"stderr\":{},\"cache\":{}}}",
            observed(owner).json(),
            quote(match owner.lifecycle { Lifecycle::Uninitialized=>"Uninitialized", Lifecycle::Ready=>"Ready", Lifecycle::Terminal=>"Terminal" }),
            state.memory.len(), quote(&String::from_utf8_lossy(wasi.stdout())),
            quote(&String::from_utf8_lossy(wasi.stderr())), quote(&format!("{:?}", owner.cache.as_ref().unwrap().usage()))));
    }
    fn completion(completed: GrowthCompletion<'_>) -> bool {
        match completed {
            GrowthCompletion::Completed(FrameCompletion::Completed) => true,
            GrowthCompletion::Completed(FrameCompletion::Retained(report) | FrameCompletion::RestoreRejected(report)) => {
                emit("frame_cleanup_retained", quote(&format!("{:?}", report)));
                false
            }
            GrowthCompletion::Retained { mut phase, mut context, mut growth, mut storage, preparation } => {
                emit("growth_cleanup_retained", "true".into());
                // Only the actual original retaining route; no changed hook, budget or owner.
                let released = release_growth_pending(&mut phase, &mut context, &mut growth);
                if let Err(failure) = released { emit("growth_cleanup_failure", failure.json()); }
                storage.drained = Some(phase.drain());
                match complete_growth(phase, context, growth, storage, preparation) {
                    GrowthCompletion::Completed(FrameCompletion::Completed) => false,
                    GrowthCompletion::Completed(other) => {
                        emit("growth_cleanup_retry_incomplete", quote(&format!("{:?}", other)));
                        false
                    }
                    GrowthCompletion::Retained { .. } => {
                        // A retained authority is never reported cleaned. This unexpected
                        // branch is a diagnostic failure with OS process cleanup only.
                        emit("growth_cleanup_unresolved", "true".into());
                        panic!("original retained growth authority did not complete");
                    }
                }
            }
        }
    }
    fn phase(owner: &mut SwiftReactorInstance, selected: Request, name: &str) -> bool {
        emit("phase_begin", quote(name));
        let ok = match request(owner, selected) {
            Completion::Completed(reply) => {
                emit("phase_reply", quote(&format!("{:?}", reply)));
                matches!((selected, reply), (Request::Initialize, Reply::Initialized) | (Request::Corpus, Reply::Corpus(0)))
            }
            Completion::PreparationFailed(failure) => { emit("runtime_failure", failure.json()); false }
            Completion::Failed { failure, cleanup } => {
                emit("runtime_failure", failure.json());
                let _ = completion(cleanup);
                false
            }
            Completion::Rejected(rejection) => { emit("unexpected_rejection", quote(&format!("{:?}", rejection))); false }
            Completion::BlockedTerminal => { emit("unexpected_terminal", "true".into()); false }
        };
        snapshot(name, owner);
        ok
    }
    fn cleanup(mut owner: SwiftReactorInstance) -> bool {
        snapshot("before_cleanup", &owner);
        if owner.state.as_ref().unwrap().frame_cleanup.bound.is_some() {
            emit("resume_original_frame_cleanup", "true".into());
            let mut returned = Some(owner.resume_frame_cleanup());
            let mut phase = match returned.take().unwrap() {
                Ok(phase) => phase,
                Err(failure) => { emit("resume_cleanup_failure", failure.json()); return false; }
            };
            let report = phase.drain();
            emit("drain_report", quote(&format!("{:?}", report)));
            let done = phase.complete(FrameOperationStorage { preparation: returned, entry: None, returned: None, drained: Some(report), controlled: None });
            emit("resume_frame_completion", quote(&format!("{:?}", done)));
        }
        let mut owned = Some(owner);
        let mut returned = Some(SwiftReactorInstance::cleanup_owned(&mut owned));
        let tail = match returned.take().unwrap() {
            Ok(tail) => tail,
            Err(failure) => { emit("owned_cleanup_failure", failure.json()); return false; }
        };
        let mut failure = None;
        let mut usage = None;
        tail.complete((owned, returned), &mut failure, &mut usage);
        emit("final_failure", failure.json());
        emit("final_cleanup_usage", usage.json());
        let u = usage.expect("consuming cleanup observation");
        let clean = u.reservations.combined.current == 0 && u.reservations.live_tickets == 0
            && u.live.values.current + u.live.controls.current + u.live.frames.current
                + u.live.active_pins.current + u.live.memory_pages.current == 0;
        emit("cleanup_empty", clean.json());
        clean
    }
    fn diagnostic(input: Vec<u8>) -> bool {
        let validation_budget = SwiftValidationBudget::default();
        let run_budget = SwiftRunBudget::default();
        let wasi_budget = WasiBudget::default();
        let grants = WasiGrants { secure_random: true, realtime: true, monotonic: true, stdout: true, stderr: true };
        emit("validation_budget", validation_budget.json());
        emit("run_budget", run_budget.json());
        emit("wasi_budget", wasi_budget.json());
        emit("wasi_grants", grants.json());
        let input_capacity = input.capacity();
        emit("input", format!("{{\"visible_bytes\":{},\"external_capacity_bytes\":{},\"external_allocation_not_in_runtime_ledger\":true}}", input.len(), input_capacity));
        emit("phase_begin", quote("validation"));
        let proof = match validate_swift_reactor(&input, validation_budget, &Cancellation::default()) {
            Ok(proof) => proof,
            Err(failure) => {
                emit("validation_failure", failure.json());
                emit("input_overlap", format!("{{\"external_input_capacity\":{},\"internal_peak_reserved\":{},\"sum_excludes_allocator_overhead_and_RSS\":{}}}", input_capacity, failure.usage.total_peak_reserved, input_capacity + failure.usage.total_peak_reserved));
                drop(input);
                emit("external_input_dropped", "true".into());
                return false;
            }
        };
        emit("validation_usage", proof.usage().json());
        emit("validation_observations", proof.observations().json());
        emit("input_overlap", format!("{{\"external_input_capacity\":{},\"internal_peak_reserved\":{},\"sum_excludes_allocator_overhead_and_RSS\":{}}}", input_capacity, proof.usage().total_peak_reserved, input_capacity + proof.usage().total_peak_reserved));
        drop(input);
        emit("external_input_dropped", "true".into());
        let started = Instant::now();
        let mut pair = match RuntimeControl::adopt(proof, run_budget, started, Cancellation::default()) {
            Ok(pair) => Some(pair),
            Err(failure) => { emit("adoption_failure", failure.json()); return false; }
        };
        emit("adopted_usage", pair.as_ref().unwrap().0.usage(None).json());
        let mut returned = Some(SwiftReactorInstance::construct(&mut pair, grants, wasi_budget, started, Cursor { stage: SwiftRunStage::Initialization, function: Some(35), offset: None }));
        let mut owner = match returned.take().unwrap() {
            Ok(owner) => owner,
            Err(crate::experimental_swift_reactor::execution::ConstructionFailure::Rejected(failure)) => {
                emit("construction_failure", failure.json());
                let (mut control, proof) = pair.take().expect("rejected constructor retains original pair");
                let dropped = control.drop_proof(proof);
                if let Err(failure) = dropped { emit("drop_proof_failure", failure.json()); }
                drop((pair, returned));
                emit("final_cleanup_usage", control.finish_owned_cleanup(None).json());
                return false;
            }
            Err(crate::experimental_swift_reactor::execution::ConstructionFailure::Cleanup(tail)) => {
                let mut failure = None;
                let mut usage = None;
                tail.complete((pair, returned), &mut failure, &mut usage);
                emit("construction_failure", failure.json());
                emit("final_cleanup_usage", usage.json());
                return false;
            }
        };
        drop((pair, returned));
        snapshot("constructed", &owner);
        let success = phase(&mut owner, Request::Initialize, "initialize")
            && phase(&mut owner, Request::Corpus, "corpus_1")
            && phase(&mut owner, Request::Corpus, "corpus_2");
        // Short circuit preserves the first failure and skips all dependent phases.
        let clean = cleanup(owner);
        emit("diagnostic_execution_complete", (success && clean).json());
        success && clean
    }

    #[test]
    fn exact_reactor_harness_control() {
        // Existing independent synthetic construction proves only wiring/cleanup.
        let (bytes, _) = module(&[], &[]);
        assert!(diagnostic(bytes));
    }

    #[test]
    fn exact_reactor_target_once() {
        let path = std::env::var("MIXER_EXACT_REACTOR_INPUT").expect("external binding required");
        let metadata = std::fs::metadata(&path).expect("bound target file");
        assert_eq!(metadata.len(), 53_777_114, "exact target byte length");
        let input = std::fs::read(&path).expect("bound immutable target bytes");
        assert_eq!(input.len(), 53_777_114);
        assert!(diagnostic(input), "exact bounded target did not complete; preserve first diagnostic");
    }
}
