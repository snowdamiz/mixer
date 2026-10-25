// Isolated test-only caller. Included after the unchanged lifecycle_tests.rs.
// This observer has no production accounting or caller-stack acceptance claim.
mod work_attribution_diagnostic {
    use super::*;
    use crate::experimental_swift_reactor::{
        SwiftReactorObservations, SwiftValidationFailure, SwiftValidationUsage,
    };
    use crate::experimental_wasi::{WasiReservations, WasiUsage};
    use std::io::Write;

    thread_local! { static OBSERVER_VALID: std::cell::Cell<bool> = const { std::cell::Cell::new(true) }; }
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
    object!(crate::experimental_swift_reactor::cache::SwiftCacheUsage; fixed_reserved,
        resident_bytes, pinned_bytes, construction_bytes, peak_resident_bytes,
        peak_pinned_bytes, peak_construction_bytes, active_pins, hits, misses, decodes, evictions);

    // A bounded, flat JSON observation decoder for this diagnostic only. It is
    // independent of the VM validator and never supplies execution authority.
    struct Observation<'a> { bytes: &'a [u8], at: usize }
    impl Observation<'_> {
        fn space(&mut self) { while self.at < self.bytes.len() && matches!(self.bytes[self.at], b' ' | b'\t' | b'\r' | b'\n') { self.at += 1; } }
        fn take(&mut self, b: u8) -> bool {
            self.space();
            if self.bytes.get(self.at) == Some(&b) { self.at += 1; true } else { false }
        }
        fn string(&mut self) -> Option<String> {
            if !self.take(b'"') { return None; }
            let mut value = String::new();
            loop {
                let next = *self.bytes.get(self.at)?;
                self.at += 1;
                match next {
                    b'"' => return Some(value),
                    b'\\' => {
                        let escaped = *self.bytes.get(self.at)?;
                        self.at += 1;
                        let c = match escaped {
                            b'"'=> '"', b'\\'=>'\\', b'/'=>'/', b'b'=>'\u{8}', b'f'=>'\u{c}',
                            b'n'=>'\n', b'r'=>'\r', b't'=>'\t',
                            b'u'=> {
                                let digits = self.bytes.get(self.at..self.at + 4)?;
                                let code = u32::from_str_radix(std::str::from_utf8(digits).ok()?, 16).ok()?;
                                self.at += 4;
                                char::from_u32(code)?
                            }
                            _ => return None,
                        };
                        value.push(c);
                    }
                    0..=31 => return None,
                    32..=126 => value.push(next as char),
                    _ => return None, // All exact expected keys/values are ASCII.
                }
            }
        }
    }
    fn native_equal(bytes: &[u8]) -> bool {
        if bytes.len() > 65_536 { return false; }
        let fields = [
            ("codableRoundTrip", "true"), ("committedEntries", "1"),
            ("completionBasisPoints", "5000"), ("emptyTitleRejected", "true"),
            ("pendingChanges", "1503"), ("reordered", "true"),
            ("repeatedCommitRejected", "true"), ("reportIncludesEntry", "true"),
            ("status", "passed"), ("taskCount", "1000"), ("unicodePreserved", "true"),
        ];
        let mut parser = Observation { bytes, at: 0 };
        let mut seen = [false; 11];
        if !parser.take(b'{') { return false; }
        for n in 0..11 {
            if n > 0 && !parser.take(b',') { return false; }
            let Some(key) = parser.string() else { return false; };
            let Some(index) = fields.iter().position(|(name, _)| *name == key) else { return false; };
            if seen[index] || !parser.take(b':') { return false; }
            seen[index] = true;
            if key == "status" {
                if parser.string().as_deref() != Some(fields[index].1) { return false; }
            } else {
                parser.space();
                let literal = fields[index].1.as_bytes();
                if parser.bytes.get(parser.at..parser.at + literal.len()) != Some(literal) { return false; }
                parser.at += literal.len();
            }
        }
        if !parser.take(b'}') { return false; }
        parser.space();
        parser.at == bytes.len() && seen.into_iter().all(|value| value)
    }
    fn hex(bytes: &[u8]) -> String {
        let mut output = String::with_capacity(bytes.len() * 2);
        for byte in bytes { use std::fmt::Write; write!(&mut output, "{byte:02x}").unwrap(); }
        output
    }

    fn emit(event: &str, payload: String) {
        // Every event is a complete standalone JSON object. Flush before continuing.
        println!("MIXER_EXACT {{\"event\":{},\"payload\":{}}}", quote(event), payload);
        std::io::stdout().flush().expect("flush diagnostic evidence");
    }
    fn attribution_snapshot(event: &str, usage: &SwiftRunUsage, cache: Option<&crate::experimental_swift_reactor::cache::SwiftCacheUsage>) -> bool {
        let (json, valid) = crate::experimental_swift_reactor::cache_tests::attribution_json(usage.cache_work, cache);
        emit(&format!("attribution_{event}"), json);
        OBSERVER_VALID.with(|state| state.set(state.get() && valid));
        valid
    }
    fn snapshot(event: &str, owner: &SwiftReactorInstance) {
        attribution_snapshot(event, &observed(owner), owner.cache.as_ref().map(|cache| cache.usage()).as_ref());
        let state = owner.state.as_ref().expect("actual state");
        let wasi = owner.wasi.as_ref().expect("actual WASI");
        emit(event, format!("{{\"usage\":{},\"lifecycle\":{},\"memory_bytes\":{},\"stdout\":{},\"stderr\":{},\"stdout_hex\":{},\"stderr_hex\":{},\"cache\":{}}}",
            observed(owner).json(),
            quote(match owner.lifecycle { Lifecycle::Uninitialized=>"Uninitialized", Lifecycle::Ready=>"Ready", Lifecycle::Terminal=>"Terminal" }),
            state.memory.len(), std::str::from_utf8(wasi.stdout()).ok().json(),
            std::str::from_utf8(wasi.stderr()).ok().json(), quote(&hex(wasi.stdout())),
            quote(&hex(wasi.stderr())), owner.cache.as_ref().unwrap().usage().json()));
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
    fn phase(owner: &mut SwiftReactorInstance, selected: Request, name: &str, compare_native: bool) -> bool {
        emit("phase_begin", quote(name));
        let before_stdout = owner.wasi.as_ref().unwrap().stdout().len();
        let ok = match request(owner, selected) {
            Completion::Completed(reply) => {
                emit("phase_reply", quote(&format!("{:?}", reply)));
                matches!((selected, reply), (Request::Initialize, Reply::Initialized) | (Request::Corpus, Reply::Corpus(0)))
            }
            Completion::PreparationFailed(failure) => { emit("runtime_failure", failure.json()); attribution_snapshot("first_runtime_failure", &failure.at_failure, None); false }
            Completion::Failed { failure, cleanup } => {
                emit("runtime_failure", failure.json());
                if let Some(failure) = failure.as_ref() { attribution_snapshot("first_runtime_failure", &failure.at_failure, None); }
                let _ = completion(cleanup);
                false
            }
            Completion::Rejected(rejection) => { emit("unexpected_rejection", quote(&format!("{:?}", rejection))); false }
            Completion::BlockedTerminal => { emit("unexpected_terminal", "true".into()); false }
        };
        snapshot(name, owner);
        if ok && compare_native && matches!(selected, Request::Corpus) {
            let suffix = &owner.wasi.as_ref().unwrap().stdout()[before_stdout..];
            let equal = native_equal(suffix);
            emit(if equal { "guest_output_native_equal" } else { "guest_output_failure" }, quote(name));
            return equal;
        }
        if !ok { emit("phase_failed", quote(name)); }
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
        let observer_valid = attribution_snapshot("final_cleanup", &u, None);
        let reservations = u.reservations;
        let empty_reservations = [reservations.retained_source.current,
            reservations.retained_metadata.current, reservations.cache.current,
            reservations.state.current, reservations.wasi.current, reservations.shared.current,
            reservations.construction.current, reservations.combined.current,
            reservations.live_tickets].into_iter().all(|current| current == 0);
        let empty_live = [u.live.cache_entries.current, u.live.values.current,
            u.live.controls.current, u.live.frames.current, u.live.active_pins.current,
            u.live.memory_pages.current].into_iter().all(|current| current == 0);
        emit("cleanup_reservations_and_live_empty", (empty_reservations && empty_live).json());
        let clean = empty_reservations && empty_live && failure.is_none() && u.cleanup_invariant.is_none();
        emit("observer_final_reconciled", observer_valid.json());
        emit("cleanup_empty", clean.json());
        clean
    }
    fn diagnostic(input: Vec<u8>, compare_native: bool) -> bool {
        crate::experimental_swift_reactor::cache_tests::attribution_reset();
        OBSERVER_VALID.with(|state| state.set(true));
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
                let final_usage = control.finish_owned_cleanup(None);
                emit("final_cleanup_usage", final_usage.json());
                attribution_snapshot("construction_failure_cleanup", &final_usage, None);
                return false;
            }
            Err(crate::experimental_swift_reactor::execution::ConstructionFailure::Cleanup(tail)) => {
                let mut failure = None;
                let mut usage = None;
                tail.complete((pair, returned), &mut failure, &mut usage);
                emit("construction_failure", failure.json());
                emit("final_cleanup_usage", usage.json());
                if let Some(usage) = usage.as_ref() { attribution_snapshot("construction_failure_cleanup", usage, None); }
                return false;
            }
        };
        drop((pair, returned));
        snapshot("constructed", &owner);
        let success = phase(&mut owner, Request::Initialize, "initialize", compare_native)
            && phase(&mut owner, Request::Corpus, "corpus_1", compare_native)
            && phase(&mut owner, Request::Corpus, "corpus_2", compare_native);
        // Short circuit preserves the first failure and skips all dependent phases.
        let clean = cleanup(owner);
        let observer_valid = OBSERVER_VALID.with(std::cell::Cell::get);
        emit("observer_all_snapshots_reconciled", observer_valid.json());
        emit("diagnostic_execution_complete", (success && clean && observer_valid).json());
        success && clean && observer_valid
    }

    #[test]
    fn attribution_reactor_harness_control() {
        let native = b"{\"codableRoundTrip\":true,\"committedEntries\":1,\"completionBasisPoints\":5000,\"emptyTitleRejected\":true,\"pendingChanges\":1503,\"reordered\":true,\"repeatedCommitRejected\":true,\"reportIncludesEntry\":true,\"status\":\"passed\",\"taskCount\":1000,\"unicodePreserved\":true}\n";
        assert!(native_equal(native));
        assert!(!native_equal(b"{}"));
        assert!(!native_equal(&[native.as_slice(), b"{}"].concat()));
        let duplicate = String::from_utf8(native.to_vec()).unwrap().replace("\"committedEntries\":1", "\"codableRoundTrip\":true");
        assert!(!native_equal(duplicate.as_bytes()));
        let wrong_type = String::from_utf8(native.to_vec()).unwrap().replace("\"taskCount\":1000", "\"taskCount\":\"1000\"");
        assert!(!native_equal(wrong_type.as_bytes()));
        assert!(!native_equal(&[native.as_slice(), &[0xff]].concat()));
        // Existing independent synthetic construction proves only wiring/cleanup.
        let (bytes, _) = module(&[], &[]);
        assert!(diagnostic(bytes, false));
    }

    #[test]
    fn attribution_reactor_target_once() {
        let path = std::env::var("MIXER_EXACT_REACTOR_INPUT").expect("external binding required");
        let metadata = std::fs::metadata(&path).expect("bound target file");
        assert_eq!(metadata.len(), 53_777_114, "exact target byte length");
        let input = std::fs::read(&path).expect("bound immutable target bytes");
        assert_eq!(input.len(), 53_777_114);
        assert!(diagnostic(input, true), "exact bounded target did not complete; preserve first diagnostic");
    }
}
