//! Archived-source unit overlay only: never included by product source.
//! Normal cache construction and enter acquire every actual frame/pin. Invalid
//! height/type/depth mutations below are derived invariant probes, not valid
//! public execution paths or new runtime authority.
use super::*;
use crate::experimental::{validate_spans, ValidationBudget};
use crate::{Limits, Profile};

fn prepared(result: bool, code: Vec<u8>) -> SpanInstance {
    // One original independently authored WebAssembly fixture, encoded directly.
    // All section/body sizes here fit a single unsigned LEB byte.
    assert!(code.len() < 120);
    let mut bytes = b"\0asm\x01\0\0\0".to_vec();
    bytes.extend([1, 4 + u8::from(result), 1, 0x60, 0, u8::from(result)]);
    if result {
        bytes.push(0x7f);
    }
    bytes.extend([3, 2, 1, 0, 7, 7, 1, 3, b'r', b'u', b'n', 0, 0]);
    bytes.extend([10, code.len() as u8 + 3, 1, code.len() as u8 + 1, 0]);
    bytes.extend(code);
    let token = Cancellation::default();
    let proof = validate_spans(
        &bytes,
        Limits {
            profile: Profile::TableMemoryV3,
            operand_stack: 8,
            control_depth: 8,
            call_depth: 4,
            ..Limits::default()
        },
        ValidationBudget::default(),
        &token,
    )
    .unwrap();
    let cache =
        FunctionCache::new(proof, super::super::cache::CacheBudget::default(), &token).unwrap();
    let mut owner = SpanInstance::new(
        cache,
        ExecutionBudget {
            live_values: 16,
            live_controls: 16,
            ..ExecutionBudget::default()
        },
        token,
    )
    .unwrap();
    owner.enter(0).unwrap();
    owner
}
fn pinned(owner: &SpanInstance) {
    assert_eq!(
        (owner.frames.len(), owner.cache_usage().active_pins),
        (1, 1)
    );
}
fn finish_probe(mut owner: SpanInstance) {
    owner.cleanup();
    assert_eq!(
        (
            owner.frames.len(),
            owner.values.len(),
            owner.controls.len(),
            owner.cache_usage().active_pins
        ),
        (0, 0, 0, 0)
    );
}
#[test]
fn control_probe_close_effect_and_failure_order() {
    // Deliberately invalid height: result pop must precede invariant checking.
    let mut owner = prepared(true, vec![0x41, 7, 0x0b]);
    owner.push(Value::I32(7)).unwrap();
    let mut control = owner.controls[0];
    control.height = 1;
    let work = owner.usage.work_used;
    assert_eq!(
        owner.close_control(control).unwrap_err().kind,
        ExecutionFailureKind::Invariant
    );
    assert_eq!((owner.values.len(), owner.usage.work_used), (0, work + 1));
    pinned(&owner);
    finish_probe(owner);
    // Each attainable refusal stage: pop; close work; post-truncate saved push.
    for allowance in 0..=5 {
        let mut owner = prepared(true, vec![0x41, 7, 0x0b]);
        for value in [1, 2, 3] {
            owner.push(Value::I32(value)).unwrap();
        }
        let control = owner.controls[0];
        let work = owner.usage.work_used;
        let capacities = (
            owner.values.capacity(),
            owner.controls.capacity(),
            owner.frames.capacity(),
            owner.usage.state_reserved,
        );
        owner.budget.work_credits = work + allowance;
        let result = owner.close_control(control);
        let (len, debit) = match allowance {
            0 => (3, 0),
            1..=3 => (2, 1),
            4 => (0, 4),
            _ => (1, 5),
        };
        assert_eq!(
            (owner.values.len(), owner.usage.work_used - work),
            (len, debit)
        );
        assert_eq!(result.is_ok(), allowance == 5);
        if let Err(error) = result {
            assert_eq!(error.kind, ExecutionFailureKind::WorkExhausted);
        }
        assert_eq!(
            (
                owner.values.capacity(),
                owner.controls.capacity(),
                owner.frames.capacity(),
                owner.usage.state_reserved
            ),
            capacities
        );
        println!("control_probe close allowance={allowance} result={result:?} values={:?} controls={} work={} usage={:?}", owner.values, owner.controls.len(), owner.usage.work_used-work, owner.usage);
        pinned(&owner);
        finish_probe(owner);
    }
    // Deliberately invalid selector type: pop32 must consume before invariant.
    let mut owner = prepared(false, vec![0x0b]);
    owner.push(Value::I64(9)).unwrap();
    let work = owner.usage.work_used;
    assert_eq!(
        owner.pop32().unwrap_err().kind,
        ExecutionFailureKind::Invariant
    );
    assert_eq!((owner.values.len(), owner.usage.work_used), (0, work + 1));
    pinned(&owner);
    finish_probe(owner);
    // Real End dispatch: fixed credit and removal precede close work failure.
    let mut owner = prepared(false, vec![0x0b]);
    let work = owner.usage.work_used;
    owner.budget.work_credits = work + 2;
    assert_eq!(
        owner.run().unwrap_err().kind,
        ExecutionFailureKind::WorkExhausted
    );
    assert_eq!(
        (
            owner.controls.len(),
            owner.usage.work_used - work,
            owner.usage.instructions,
            owner.usage.fuel_used
        ),
        (0, 2, 1, 1)
    );
    assert_eq!(owner.usage.live_controls, 1); // Original observer has not run yet.
    pinned(&owner);
    finish_probe(owner);
}

fn stopped_at_block(looping: bool, result: bool) -> SpanInstance {
    let mut code = vec![
        if looping { 3 } else { 2 },
        if result { 0x7f } else { 0x40 },
    ];
    if result {
        code.extend([0x41, 7]);
    }
    code.extend([0x0b, 0x0b]);
    let mut owner = prepared(result, code);
    let unlimited = owner.budget.work_credits;
    owner.budget.work_credits = owner.usage.work_used + 2;
    // Block dispatch ran normally; next dispatch work fails before its pc moves.
    assert_eq!(
        owner.run().unwrap_err().kind,
        ExecutionFailureKind::WorkExhausted
    );
    owner.budget.work_credits = unlimited;
    assert_eq!(owner.controls.len(), 2);
    owner
}
#[test]
fn control_probe_branch_targets_boundaries_and_cancellation() {
    for looping in [false, true] {
        for result in [false, true] {
            let mut owner = stopped_at_block(looping, result);
            let control = owner.controls[1];
            if result {
                owner.push(Value::I32(7)).unwrap();
            }
            let reserved = owner.usage.state_reserved;
            assert!(!owner.branch(0).unwrap());
            assert_eq!(owner.controls.len(), if looping { 2 } else { 1 });
            assert_eq!(
                owner.frames[0].pc,
                if looping {
                    control.start
                } else {
                    control.end + 1
                }
            );
            assert_eq!(owner.values.len(), usize::from(result && !looping));
            if looping {
                assert_eq!(owner.controls[1].result, result);
            }
            assert_eq!(owner.usage.state_reserved, reserved);
            pinned(&owner);
            println!("control_probe branch loop={looping} result={result} pc={} controls={} values={:?} usage={:?}", owner.frames[0].pc, owner.controls.len(), owner.values, owner.usage);
            finish_probe(owner);
        }
    }
    // Successful close is the boundary before control truncation and pc write.
    for allowance in 0..=6 {
        let mut owner = stopped_at_block(false, true);
        for value in [1, 2, 3] {
            owner.push(Value::I32(value)).unwrap();
        }
        let work = owner.usage.work_used;
        let pc = owner.frames[0].pc;
        let end = owner.controls[1].end;
        owner.budget.work_credits = work + allowance;
        let result = owner.branch(0);
        let (values, debit) = match allowance {
            0 => (3, 0),
            1 => (3, 1),
            2..=4 => (2, 2),
            5 => (0, 5),
            _ => (1, 6),
        };
        assert_eq!(
            (owner.values.len(), owner.usage.work_used - work),
            (values, debit)
        );
        assert_eq!(owner.controls.len(), if allowance == 6 { 1 } else { 2 });
        assert_eq!(
            owner.frames[0].pc,
            if allowance == 6 { end + 1 } else { pc }
        );
        assert_eq!(result.is_ok(), allowance == 6);
        println!("control_probe branch allowance={allowance} result={result:?} pc={} controls={} values={:?} usage={:?}", owner.frames[0].pc, owner.controls.len(), owner.values, owner.usage);
        pinned(&owner);
        finish_probe(owner);
    }
    let mut owner = prepared(false, vec![0x0b]);
    assert!(owner.branch(0).unwrap());
    assert_eq!(owner.controls.len(), 0);
    pinned(&owner);
    finish_probe(owner);
    // Actual recursive enter creates the callee and second original cache pin.
    let mut owner = prepared(false, vec![0x10, 0, 0x0b]);
    owner.enter(0).unwrap();
    let work = owner.usage.work_used;
    assert_eq!(
        owner.branch(1).unwrap_err().kind,
        ExecutionFailureKind::Invariant
    );
    assert_eq!(
        (
            owner.frames.len(),
            owner.controls.len(),
            owner.cache_usage().active_pins,
            owner.usage.work_used
        ),
        (2, 2, 2, work)
    );
    finish_probe(owner);
    // Deterministic cancellation at the existing entry to each helper: no
    // timing race or new cancellation hook changes their original schedules.
    for helper in ["pop", "close", "branch"] {
        let mut owner = prepared(false, vec![0x0b]);
        owner.push(Value::I32(7)).unwrap();
        let work = owner.usage.work_used;
        let pc = owner.frames[0].pc;
        let control = owner.controls[0];
        owner.cancellation.cancel();
        let error = match helper {
            "pop" => owner.pop32().unwrap_err(),
            "close" => owner.close_control(control).unwrap_err(),
            _ => owner.branch(0).unwrap_err(),
        };
        assert_eq!(error.kind, ExecutionFailureKind::Cancelled);
        assert_eq!(
            (
                owner.values.len(),
                owner.controls.len(),
                owner.frames[0].pc,
                owner.usage.work_used
            ),
            (1, 1, pc, work)
        );
        pinned(&owner);
        finish_probe(owner);
    }
}
