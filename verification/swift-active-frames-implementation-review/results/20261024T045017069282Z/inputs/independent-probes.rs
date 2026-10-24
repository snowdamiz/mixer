//! Independently authored original-owner host probes. Appended only to an exact
//! archived candidate under a separate cfg(test) module and separate target.
use super::*;
use crate::experimental_swift_reactor::allocation_tests::measure_extended;
use crate::experimental_swift_reactor::{validate_swift_reactor, SwiftValidationBudget};
use crate::experimental_swift_reactor::execution_tests::construction_finish;
use crate::experimental_wasi::WasiFunction;
use crate::Cancellation;
use crate::experimental::cache::borrowed::PinToken;

fn cursor() -> Cursor {
    Cursor { stage: SwiftRunStage::Invocation, function: Some(34), offset: Some(771) }
}
fn uint(mut n: u32, bytes: &mut Vec<u8>) {
    loop {
        let low = (n & 127) as u8;
        n >>= 7;
        bytes.push(low | if n != 0 { 128 } else { 0 });
        if n == 0 { break; }
    }
}
fn text(value: &[u8], bytes: &mut Vec<u8>) {
    uint(value.len() as u32, bytes);
    bytes.extend_from_slice(value);
}
fn section(kind: u8, payload: &[u8], bytes: &mut Vec<u8>) {
    bytes.push(kind);
    uint(payload.len() as u32, bytes);
    bytes.extend_from_slice(payload);
}
fn tag(ty: Type) -> u8 {
    match ty { Type::I32 => 0x7f, Type::I64 => 0x7e, Type::F32 => 0x7d, Type::F64 => 0x7c }
}
fn fixture() -> Vec<u8> {
    // Preserve the validated Swift corpus ABI. Only this review's definition34
    // has parameters and declared locals;35 remains the actual initializer.
    let mut bytes = b"\0asm\x01\0\0\0".to_vec();
    let mut types = vec![37];
    for function in WasiFunction::ALL {
        types.push(0x60);
        uint(function.parameters().len() as u32, &mut types);
        types.extend(function.parameters().iter().copied().map(tag));
        uint(function.results().len() as u32, &mut types);
        types.extend(function.results().iter().copied().map(tag));
    }
    types.extend_from_slice(&[0x60, 0, 0, 0x60, 0, 1, 0x7f, 0x60, 4, 0x7f, 0x7e, 0x7d, 0x7c, 0]);
    section(1, &types, &mut bytes);
    let mut imports = vec![34];
    for (index, function) in WasiFunction::ALL.into_iter().enumerate() {
        text(b"wasi_snapshot_preview1", &mut imports);
        text(function.name(), &mut imports);
        imports.push(0);
        uint(index as u32, &mut imports);
    }
    section(2, &imports, &mut bytes);
    let mut definitions = vec![29];
    for index in 0..29 {
        definitions.push(if index == 0 { 36 } else if index == 3 || index == 28 { 35 } else { 34 });
    }
    section(3, &definitions, &mut bytes);
    let mut table = vec![1, 0x70, 1];
    uint(46713, &mut table); uint(46713, &mut table);
    section(4, &table, &mut bytes);
    let mut memory = vec![1, 0]; uint(584, &mut memory);
    section(5, &memory, &mut bytes);
    let mut exports = vec![3];
    for (name, kind, index) in [
        (b"memory".as_slice(), 2, 0),
        (b"_initialize".as_slice(), 0, 35),
        (b"mixer_fieldlog_corpus_v1".as_slice(), 0, 62),
    ] {
        text(name, &mut exports); exports.push(kind); uint(index, &mut exports);
    }
    section(7, &exports, &mut bytes);
    let mut code = vec![29];
    for index in 0..29 {
        let body: &[u8] = if index == 0 {
            &[4, 1, 0x7f, 1, 0x7e, 1, 0x7d, 1, 0x7c, 0x0b]
        } else if index == 3 || index == 28 { &[0, 0x41, 0, 0x0b] } else { &[0, 0x0b] };
        uint(body.len() as u32, &mut code); code.extend_from_slice(body);
    }
    section(10, &code, &mut bytes);
    bytes
}
fn owner() -> SwiftReactorInstance {
    let proof = validate_swift_reactor(&fixture(), SwiftValidationBudget::default(), &Cancellation::default()).unwrap();
    let pair = RuntimeControl::adopt(proof, SwiftRunBudget::default(), Instant::now(), Cancellation::default()).unwrap();
    let mut pair = Some(pair);
    let owner = SwiftReactorInstance::construct(&mut pair, WasiGrants::default(), WasiBudget { one_transfer_bytes: 64, log_bytes: 64, ..WasiBudget::default() }, Instant::now(), cursor()).unwrap();
    assert!(pair.is_none());
    owner
}
fn usage(owner: &SwiftReactorInstance) -> SwiftRunUsage {
    owner.control.as_ref().unwrap().usage(Some(owner.wasi.as_ref().unwrap().usage()))
}
fn closed<'a>(phase: FrameOperationPhase<'a>, preparation: Option<Result<FrameOperationPhase<'a>, SwiftRunFailure>>) {
    let completion = phase.complete(FrameOperationStorage { preparation, entry: None, returned: None, drained: None });
    assert!(matches!(completion, FrameCompletion::Completed));
}

#[test]
fn independent_af_actual_nested_parameter_suffix_and_zero_bits() {
    let mut owner = owner();
    let original_values = owner.state.as_ref().unwrap().values.as_ptr();
    let original_frames = owner.state.as_ref().unwrap().frames.as_ptr();
    let mut preparation = Some(owner.prepare_frames(cursor()));
    let mut phase = preparation.take().unwrap().unwrap();
    phase.enter(35).unwrap();
    let caller = [Value::I32(77), Value::I32(-9), Value::I64(i64::MIN), Value::F32(0x7fc0_1234), Value::F64(0x8000_0000_0000_0000)];
    for value in caller { phase.phase.push_value(value).unwrap(); }
    phase.enter(34).unwrap();
    assert_eq!(phase.phase.parts.values.as_ptr(), original_values);
    assert_eq!(phase.phase.parts.frames.as_ptr(), original_frames);
    assert_eq!(phase.phase.parts.frames.len(), 2);
    assert_eq!(phase.phase.parts.cache.usage().active_pins, 2);
    assert_eq!(phase.phase.parts.frames[1].base, 1);
    assert_eq!(phase.phase.parts.frames[1].operands, 9);
    assert_eq!(&phase.phase.parts.values[..5], &caller);
    assert_eq!(&phase.phase.parts.values[5..], &[Value::I32(0), Value::I64(0), Value::F32(0), Value::F64(0)]);
    phase.phase.push_value(Value::I64(18)).unwrap();
    assert!(matches!(phase.finish().unwrap(), FrameReturn::CallerContinues));
    assert_eq!(phase.phase.parts.values.as_slice(), &[Value::I32(77)]);
    assert_eq!(phase.phase.parts.cache.usage().active_pins, 1);
    assert!(matches!(phase.finish().unwrap(), FrameReturn::Outermost(None)));
    closed(phase, preparation);
    assert!(matches!(owner.lifecycle, Lifecycle::Uninitialized));
    construction_finish(owner);
}

#[test]
fn independent_af_result_return_every_work_prefix() {
    for extra in 0..=4 {
        let mut owner = owner();
        let mut preparation = Some(owner.prepare_frames(cursor()));
        let mut phase = preparation.take().unwrap().unwrap();
        phase.enter(35).unwrap(); phase.enter(37).unwrap();
        phase.phase.push_value(Value::I32(418)).unwrap();
        let before = phase.phase.operation.control.usage(Some(phase.phase.operation.wasi.usage())).execution_work;
        let old = phase.phase.operation.control.test_replace_execution_work_limit(before + extra);
        let returned = phase.finish();
        phase.phase.operation.control.test_replace_execution_work_limit(old);
        let after = phase.phase.operation.control.usage(Some(phase.phase.operation.wasi.usage())).execution_work;
        let delta = [0, 1, 1, 3, 4][extra as usize];
        assert_eq!(after - before, delta, "extra={extra}");
        if extra == 4 {
            assert!(matches!(returned.unwrap(), FrameReturn::CallerContinues));
            assert_eq!(phase.phase.parts.values.as_slice(), &[Value::I32(418)]);
            assert_eq!(phase.phase.parts.frames.len(), 1);
            assert_eq!(phase.phase.parts.cache.usage().active_pins, 1);
        } else {
            let failure = returned.unwrap_err();
            assert_eq!(failure.resource, Some(SwiftRunResource::ExecutionWork));
            assert_eq!(failure.function, cursor().function);
            assert_eq!(failure.offset, cursor().offset);
            assert_eq!(phase.phase.parts.frames.len(), if extra == 3 { 1 } else { 2 });
            assert_eq!(phase.phase.parts.values.len(), usize::from(extra == 0));
            let drained = phase.drain();
            assert_eq!(drained.usage.execution_work, after);
            assert_eq!(drained.first_failure.unwrap().code, failure.code);
        }
        if extra == 4 { phase.drain(); }
        closed(phase, preparation);
        construction_finish(owner);
    }
}

#[test]
fn independent_af_zero_ledger_underflow_latch_is_irreversible() {
    for resource in [Live::Values, Live::Controls, Live::Frames] {
        let mut owner = owner();
        let before = usage(&owner).reservations.construction.current;
        let mut preparation = Some(owner.prepare_frames(cursor()));
        let mut phase = preparation.take().unwrap().unwrap();
        phase.enter(35).unwrap(); phase.phase.push_value(Value::I32(17)).unwrap();
        phase.phase.operation.control.remove_live_with_wasi(resource, 1, Some(phase.phase.operation.wasi.usage())).unwrap();
        let report = phase.drain();
        assert!(report.live_unreconciled);
        assert_eq!(report.retained_frames, 0);
        assert_eq!(report.cache.active_pins, 0);
        assert_eq!(report.live.values.current, 0);
        assert_eq!(report.live.controls.current, 0);
        assert_eq!(report.live.frames.current, 0);
        let completion = phase.complete(FrameOperationStorage { preparation, entry: None, returned: None, drained: Some(report) });
        assert!(matches!(completion, FrameCompletion::Retained(_)));
        assert!(usage(&owner).reservations.construction.current > before);
        let mut preparation = Some(owner.resume_frame_cleanup());
        let mut resumed = preparation.take().unwrap().unwrap();
        assert!(resumed.drain().live_unreconciled);
        assert!(matches!(resumed.complete(FrameOperationStorage { preparation, entry: None, returned: None, drained: None }), FrameCompletion::Retained(_)));
        assert!(owner.prepare_value_operation(cursor()).is_err());
        let mut owned = Some(owner);
        assert!(SwiftReactorInstance::cleanup_owned(&mut owned).is_err());
        assert!(owned.is_some());
        // This intentionally inconsistent owner remains charged; there is no
        // ledger repair, consuming cleanup pass or zero-reservation claim.
    }
}

#[test]
fn independent_af_fresh_entry_agreement_failure_is_terminal_without_rollback() {
    let mut owner = owner();
    let mut preparation = Some(owner.prepare_frames(cursor()));
    let mut phase = preparation.take().unwrap().unwrap();
    phase.enter(35).unwrap();
    phase.phase.operation.control.remove_live(Live::Controls, 1).unwrap();
    let failure = phase.enter(36).unwrap_err();
    assert_eq!(failure.code, "swift_frame_live_mismatch");
    assert!(matches!(*phase.lifecycle, Lifecycle::Terminal));
    assert_eq!(phase.cleanup.disposition, FrameDisposition::Draining);
    assert_eq!(phase.cleanup.unvisited, 1);
    assert!(phase.cleanup.entry.is_none());
    assert_eq!(phase.phase.parts.controls.len(), 1);
    assert_eq!(phase.phase.parts.frames.len(), 1);
    assert!(phase.drain().live_unreconciled);
    assert!(matches!(phase.complete(FrameOperationStorage { preparation, entry: None, returned: None, drained: None }), FrameCompletion::Retained(_)));
}

#[test]
fn independent_af_dropped_active_resume_is_cleanup_only_and_preserves_wasi() {
    let mut owner = owner();
    let c = cursor();
    owner.wasi.as_mut().unwrap().dispatch(owner.control.as_mut().unwrap(), WasiFunction::ArgsSizesGet, &[Value::I32(0), Value::I32(4)], &mut owner.state.as_mut().unwrap().memory, c).unwrap();
    let actual_wasi = owner.wasi.as_ref().unwrap().usage();
    assert_eq!(actual_wasi.calls, 1);
    let mut preparation = Some(owner.prepare_frames(c));
    let mut phase = preparation.take().unwrap().unwrap();
    phase.enter(35).unwrap(); phase.enter(36).unwrap(); phase.phase.push_value(Value::I32(71)).unwrap();
    drop(phase); drop(preparation);
    let admitted = usage(&owner);
    owner.control.as_ref().unwrap().cancellation().cancel();
    let mut preparation = Some(owner.resume_frame_cleanup());
    let mut phase = preparation.take().unwrap().unwrap();
    assert!(phase.enter(36).is_err());
    assert!(phase.finish().is_err());
    assert_eq!(phase.phase.parts.frames.len(), 2);
    assert_eq!(phase.phase.parts.values.as_slice(), &[Value::I32(71)]);
    let report = phase.drain();
    assert_eq!(report.usage.execution_work, admitted.execution_work);
    assert_eq!(report.usage.wasi, Some(actual_wasi));
    assert_eq!(report.first_failure.unwrap().at_failure.wasi, Some(actual_wasi));
    assert_eq!(report.first_failure.unwrap().after_cleanup.unwrap().wasi, Some(actual_wasi));
    closed(phase, preparation);
    construction_finish(owner);
}

#[test]
fn independent_af_same_owner_different_layout_rejects_all_admission_paths() {
    for path in 0..4 {
        // A fresh first_failure per path prevents a previous provenance fault
        // from satisfying a later admission check only at ordinary enlarge.
        let mut owner = owner();
        if path == 3 { drop(owner.prepare_frames(cursor()).unwrap()); }
        let before = usage(&owner).reservations.construction.current;
        let memory = owner.state.as_ref().unwrap().memory.as_ptr();
        owner.state.as_mut().unwrap().buffers.swap(0, 1);
        let failure = match path {
            0 => owner.prepare_frames(cursor()).err().unwrap(),
            1 => owner.prepare_value_operation(cursor()).err().unwrap(),
            2 => {
                let mut owned = Some(owner);
                let failure = SwiftReactorInstance::cleanup_owned(&mut owned).err().unwrap();
                owner = owned.take().expect("cleanup must retain actual owner");
                failure
            }
            _ => owner.resume_frame_cleanup().err().unwrap(),
        };
        assert_eq!(failure.code, "swift_execution_layout_overflow");
        assert_eq!(usage(&owner).reservations.construction.current, before);
        assert_eq!(owner.state.as_ref().unwrap().memory.as_ptr(), memory);
        owner.state.as_mut().unwrap().buffers.swap(0, 1);
        if path == 3 {
            let mut preparation = Some(owner.resume_frame_cleanup());
            let mut phase = preparation.take().unwrap().unwrap();
            phase.drain(); closed(phase, preparation);
        }
        construction_finish(owner);
    }
}

fn retire_with_expected_diagnostic(owner: SwiftReactorInstance) {
    let expected = usage(&owner).cleanup_invariant;
    let mut owned = Some(owner);
    let mut returned = Some(SwiftReactorInstance::cleanup_owned(&mut owned));
    let tail = returned.take().unwrap().unwrap();
    let mut failure = None;
    let mut observation = None;
    tail.complete((owned, returned), &mut failure, &mut observation);
    let observation = observation.unwrap();
    assert_eq!(observation.cleanup_invariant, expected);
    assert_eq!(observation.reservations.combined.current, 0);
    assert_eq!(observation.reservations.live_tickets, 0);
    assert_eq!(observation.live.memory_pages.current, 0);
    assert_eq!(observation.live.values.current, 0);
    assert_eq!(observation.live.controls.current, 0);
    assert_eq!(observation.live.frames.current, 0);
    assert_eq!(observation.live.active_pins.current, 0);
    assert!(failure.is_some());
}

#[test]
fn independent_af_actual_construction_provenance_rejects_before_state_effects() {
    for path in 0..4 {
        for corruption in 0..3 {
            let mut owner = owner();
            let mut foreign = if corruption == 1 { Some(self::owner()) } else { None };
            if path == 3 {
                let mut preparation = Some(owner.prepare_frames(cursor()));
                let mut phase = preparation.take().unwrap().unwrap();
                phase.enter(35).unwrap(); phase.phase.push_value(Value::I32(92)).unwrap();
                drop(phase); drop(preparation);
            }
            let state = owner.state.as_ref().unwrap();
            let pointers = (state.memory.as_ptr(), state.values.as_ptr(), state.controls.as_ptr(), state.frames.as_ptr());
            let lengths = (state.values.len(), state.controls.len(), state.frames.len());
            let ids: Vec<_> = state.frames.iter().map(|frame| (frame.function, frame.pin.owner(), frame.pin.slot(), frame.pin.nonce())).collect();
            let disposition = state.frame_cleanup.disposition;
            let bound = state.frame_cleanup.bound.map(|bound| (bound.previous, bound.admitted));
            let before = usage(&owner);
            let original = owner.control.as_mut().unwrap().test_replace_construction(None).unwrap();
            let mut original = Some(original);
            if corruption == 1 {
                let replacement = foreign.as_mut().unwrap().control.as_mut().unwrap().test_replace_construction(None);
                assert!(owner.control.as_mut().unwrap().test_replace_construction(replacement).is_none());
            } else if corruption == 2 {
                let replacement = owner.state.as_mut().unwrap().buffers[0].replace(original.take().unwrap()).unwrap();
                assert!(owner.control.as_mut().unwrap().test_replace_construction(Some(replacement)).is_none());
            }
            let failure = match path {
                0 => owner.prepare_frames(cursor()).err().unwrap(),
                1 => owner.prepare_value_operation(cursor()).err().unwrap(),
                2 => {
                    let mut owned = Some(owner);
                    let failure = SwiftReactorInstance::cleanup_owned(&mut owned).err().unwrap();
                    owner = owned.take().expect("corrupt construction must preserve actual owner");
                    failure
                }
                _ => owner.resume_frame_cleanup().err().unwrap(),
            };
            assert_eq!(failure.code, ["swift_run_missing_construction", "swift_run_construction_owner", "swift_run_construction_layout"][corruption]);
            assert_eq!(failure.at_failure.wasi, before.wasi);
            let state = owner.state.as_ref().unwrap();
            assert_eq!((state.memory.as_ptr(), state.values.as_ptr(), state.controls.as_ptr(), state.frames.as_ptr()), pointers);
            assert_eq!((state.values.len(), state.controls.len(), state.frames.len()), lengths);
            assert_eq!(state.frame_cleanup.disposition, disposition);
            assert_eq!(state.frame_cleanup.bound.map(|bound| (bound.previous, bound.admitted)), bound);
            assert_eq!(state.frames.iter().map(|frame| (frame.function, frame.pin.owner(), frame.pin.slot(), frame.pin.nonce())).collect::<Vec<_>>(), ids);
            assert!(matches!(owner.lifecycle, Lifecycle::Uninitialized));
            assert_eq!(usage(&owner).reservations.construction.current, before.reservations.construction.current);
            let replaced = owner.control.as_mut().unwrap().test_replace_construction(None);
            if corruption == 1 {
                assert!(foreign.as_mut().unwrap().control.as_mut().unwrap().test_replace_construction(replaced).is_none());
            } else if corruption == 2 {
                original = owner.state.as_mut().unwrap().buffers[0].replace(replaced.unwrap());
            } else { assert!(replaced.is_none()); }
            assert!(owner.control.as_mut().unwrap().test_replace_construction(original).is_none());
            if path == 3 {
                let mut preparation = Some(owner.resume_frame_cleanup());
                let mut phase = preparation.take().unwrap().unwrap();
                phase.drain(); closed(phase, preparation);
            }
            retire_with_expected_diagnostic(owner);
            if let Some(foreign) = foreign { construction_finish(foreign); }
        }
    }
}

#[test]
fn independent_af_warm_actual_entry_return_and_drain_refuse_allocation() {
    let mut owner = owner();
    // Warm both actual definitions using the actual cache phase and release.
    for function in [35, 36] {
        let control = owner.control.as_mut().unwrap();
        let wasi = owner.wasi.as_ref().unwrap();
        let cache = owner.cache.as_mut().unwrap();
        let mut preparation = Some(cache.prepare_operation(control, Some(wasi), cursor()));
        let mut phase = preparation.take().unwrap().unwrap();
        let mut returned = Some(phase.pin(cache, function));
        let pin = returned.take().unwrap().unwrap();
        phase.complete((preparation, returned)).unwrap();
        cache.release(pin, control, Some(wasi)).unwrap();
    }
    let mut preparation = Some(owner.prepare_frames(cursor()));
    let mut phase = preparation.take().unwrap().unwrap();
    let (result, stats) = measure_extended(Some(0), || {
        phase.enter(35)?; phase.enter(36)?;
        phase.finish()?;
        Ok::<_, SwiftRunFailure>(phase.drain())
    });
    assert_eq!(stats.attempts, 0);
    assert_eq!(result.unwrap().retained_frames, 0);
    let ((), stats) = measure_extended(Some(0), || closed(phase, preparation));
    assert_eq!(stats.attempts, 0);
    construction_finish(owner);
}
