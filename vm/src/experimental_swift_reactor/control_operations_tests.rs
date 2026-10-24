//! Bounded hand steps of original validated Wasm. This is a test caller boundary,
//! not a production dispatcher, owner, interpreter oracle or release receipt.
use super::*;
use crate::experimental::cache::DecodedInstruction;

#[derive(Clone, Copy)]
struct Case {
    name: &'static str,
    body: &'static [u8],
    result: bool,
    answer: Option<Value>,
    // Each tuple is (pc after helper, value height, control height, helper work).
    expected: &'static [(usize, usize, usize, u64)],
}
const CASES: &[Case] = &[
    Case {
        name: "empty_block",
        body: &[2, 0x40, 0x0b, 0x0b],
        result: false,
        answer: None,
        expected: &[(1, 0, 2, 1), (2, 0, 1, 2), (3, 0, 0, 2)],
    },
    Case {
        name: "result_block",
        body: &[2, 0x7f, 0x41, 7, 0x0b, 0x0b],
        result: true,
        answer: Some(Value::I32(7)),
        expected: &[(1, 0, 2, 1), (2, 1, 2, 1), (3, 1, 1, 4), (4, 1, 0, 4)],
    },
    Case {
        name: "empty_loop",
        body: &[3, 0x40, 0x0b, 0x0b],
        result: false,
        answer: None,
        expected: &[(1, 0, 2, 1), (2, 0, 1, 2), (3, 0, 0, 2)],
    },
    Case {
        name: "result_loop",
        body: &[3, 0x7f, 0x41, 8, 0x0b, 0x0b],
        result: true,
        answer: Some(Value::I32(8)),
        expected: &[(1, 0, 2, 1), (2, 1, 2, 1), (3, 1, 1, 4), (4, 1, 0, 4)],
    },
    Case {
        name: "if_true_else",
        body: &[0x41, 1, 4, 0x7f, 0x41, 9, 5, 0x41, 10, 0x0b, 0x0b],
        result: true,
        answer: Some(Value::I32(9)),
        expected: &[
            (1, 1, 1, 1),
            (2, 0, 2, 2),
            (3, 1, 2, 1),
            (5, 1, 2, 0),
            (6, 1, 1, 4),
            (7, 1, 0, 4),
        ],
    },
    Case {
        name: "if_false_else",
        body: &[0x41, 0, 4, 0x7f, 0x41, 9, 5, 0x41, 10, 0x0b, 0x0b],
        result: true,
        answer: Some(Value::I32(10)),
        expected: &[
            (1, 1, 1, 1),
            (4, 0, 2, 2),
            (5, 1, 2, 1),
            (6, 1, 1, 4),
            (7, 1, 0, 4),
        ],
    },
    Case {
        name: "if_false_no_else",
        body: &[0x41, 0, 4, 0x40, 1, 0x0b, 0x0b],
        result: false,
        answer: None,
        expected: &[(1, 1, 1, 1), (3, 0, 2, 2), (4, 0, 1, 2), (5, 0, 0, 2)],
    },
    Case {
        name: "nested_end",
        body: &[2, 0x40, 2, 0x40, 0x0b, 0x0b, 0x0b],
        result: false,
        answer: None,
        expected: &[
            (1, 0, 2, 1),
            (2, 0, 3, 1),
            (3, 0, 2, 2),
            (4, 0, 1, 2),
            (5, 0, 0, 2),
        ],
    },
    Case {
        name: "return_open",
        body: &[2, 0x40, 0x41, 11, 0x0f, 0x0b, 0x41, 0, 0x0b],
        result: true,
        answer: Some(Value::I32(11)),
        expected: &[(1, 0, 2, 1), (2, 1, 2, 1), (3, 1, 2, 0)],
    },
    Case {
        name: "br_block",
        body: &[2, 0x7f, 0x41, 12, 0x0c, 0, 0x0b, 0x0b],
        result: true,
        answer: Some(Value::I32(12)),
        expected: &[(1, 0, 2, 1), (2, 1, 2, 1), (4, 1, 1, 4), (5, 1, 0, 4)],
    },
    Case {
        name: "br_function",
        body: &[2, 0x40, 0x41, 13, 0x0c, 1, 0x0b, 0x41, 0, 0x0b],
        result: true,
        answer: Some(Value::I32(13)),
        expected: &[(1, 0, 2, 1), (2, 1, 2, 1), (6, 1, 0, 5)],
    },
    Case {
        name: "br_if_true",
        body: &[2, 0x7f, 0x41, 14, 0x41, 1, 0x0d, 0, 0x0b, 0x0b],
        result: true,
        answer: Some(Value::I32(14)),
        expected: &[
            (1, 0, 2, 1),
            (2, 1, 2, 1),
            (3, 2, 2, 1),
            (5, 1, 1, 5),
            (6, 1, 0, 4),
        ],
    },
    Case {
        name: "br_if_false",
        body: &[2, 0x7f, 0x41, 14, 0x41, 0, 0x0d, 0, 0x0b, 0x0b],
        result: true,
        answer: Some(Value::I32(14)),
        expected: &[
            (1, 0, 2, 1),
            (2, 1, 2, 1),
            (3, 2, 2, 1),
            (4, 1, 2, 1),
            (5, 1, 1, 4),
            (6, 1, 0, 4),
        ],
    },
    Case {
        name: "br_table_first",
        body: &[
            2, 0x7f, 2, 0x7f, 0x41, 15, 0x41, 0, 0x0e, 2, 0, 1, 1, 0x0b, 0x0b, 0x0b,
        ],
        result: true,
        answer: Some(Value::I32(15)),
        expected: &[
            (1, 0, 2, 1),
            (2, 0, 3, 1),
            (3, 1, 3, 1),
            (4, 2, 3, 1),
            (6, 1, 2, 5),
            (7, 1, 1, 4),
            (8, 1, 0, 4),
        ],
    },
    Case {
        name: "br_table_last",
        body: &[
            2, 0x7f, 2, 0x7f, 0x41, 16, 0x41, 1, 0x0e, 2, 0, 1, 1, 0x0b, 0x0b, 0x0b,
        ],
        result: true,
        answer: Some(Value::I32(16)),
        expected: &[
            (1, 0, 2, 1),
            (2, 0, 3, 1),
            (3, 1, 3, 1),
            (4, 2, 3, 1),
            (7, 1, 1, 6),
            (8, 1, 0, 4),
        ],
    },
    Case {
        name: "br_table_default_unsigned",
        body: &[
            2, 0x7f, 2, 0x7f, 0x41, 17, 0x41, 0x7f, 0x0e, 2, 0, 1, 1, 0x0b, 0x0b, 0x0b,
        ],
        result: true,
        answer: Some(Value::I32(17)),
        expected: &[
            (1, 0, 2, 1),
            (2, 0, 3, 1),
            (3, 1, 3, 1),
            (4, 2, 3, 1),
            (7, 1, 1, 6),
            (8, 1, 0, 4),
        ],
    },
];
fn var(bytes: &[u8], at: &mut usize) -> usize {
    let mut value = 0;
    let mut shift = 0;
    loop {
        let b = bytes[*at];
        *at += 1;
        value |= ((b & 127) as usize) << shift;
        if b & 128 == 0 {
            return value;
        }
        shift += 7;
    }
}
fn body_fixture(body: &[u8], result: bool, locals: &[Type]) -> Vec<u8> {
    // Reuse the independently authored accepted strict-reactor ABI scaffold.
    // Replace both original tested function bodies before real validation.
    let original = fixture(&Function {
        result: if result { Some(Type::I32) } else { None },
        locals: locals.to_vec(),
        ..Function::empty()
    });
    let mut at = 8;
    while at < original.len() {
        let start = at;
        let id = original[at];
        at += 1;
        let length = var(&original, &mut at);
        let payload = at;
        if id == 10 {
            let mut code = vec![29];
            for index in 0..29 {
                let mut bytes = vec![];
                if index == 0 || index == 2 {
                    uint(locals.len() as u32, &mut bytes);
                    for local in locals {
                        bytes.extend([1, ty(*local)]);
                    }
                    bytes.extend_from_slice(body);
                } else if index == 28 {
                    bytes.extend([0, 0x41, 0, 0x0b]);
                } else {
                    bytes.extend([0, 0x0b]);
                }
                uint(bytes.len() as u32, &mut code);
                code.extend(bytes);
            }
            let mut out = original[..start].to_vec();
            section(10, &code, &mut out);
            out.extend_from_slice(&original[payload + length..]);
            return out;
        }
        at += length;
    }
    unreachable!()
}
pub(in crate::experimental_swift_reactor::execution::frame_operations) fn body_owner(
    body: &[u8],
    result: bool,
    locals: &[Type],
    budget: SwiftRunBudget,
) -> SwiftReactorInstance {
    hooks(Hooks::default());
    let proof = validate_swift_reactor(
        &body_fixture(body, result, locals),
        SwiftValidationBudget::default(),
        &Cancellation::default(),
    )
    .unwrap();
    let mut pair = Some(
        RuntimeControl::adopt(proof, budget, Instant::now(), Cancellation::default()).unwrap(),
    );
    SwiftReactorInstance::construct(
        &mut pair,
        WasiGrants::default(),
        WasiBudget {
            one_transfer_bytes: 64,
            log_bytes: 64,
            ..WasiBudget::default()
        },
        Instant::now(),
        cursor(),
    )
    .unwrap()
}
fn observed(phase: &FrameOperationPhase<'_>) -> SwiftRunUsage {
    phase
        .phase
        .operation
        .control
        .usage(Some(phase.phase.operation.wasi.usage()))
}
fn fetched(phase: &mut FrameOperationPhase<'_>) -> (DecodedInstruction, Option<u32>) {
    let frame = phase.phase.parts.frames.last().unwrap();
    let view = phase
        .phase
        .parts
        .cache
        .view(
            &frame.pin,
            phase.phase.operation.control,
            Some(&*phase.phase.operation.wasi),
        )
        .unwrap();
    let instruction = view.instructions[frame.pc];
    let target = if let Operation::BrTable {
        first,
        count,
        default,
    } = instruction.operation
    {
        let selector = match phase.phase.parts.values.last().unwrap() {
            Value::I32(n) => *n as u32 as usize,
            _ => 0,
        };
        Some(if selector < count {
            view.branch_targets[first + selector]
        } else {
            default
        })
    } else {
        None
    };
    (instruction, target)
}
fn boundary(
    phase: &mut FrameOperationPhase<'_>,
    instruction: DecodedInstruction,
) -> Result<(), SwiftRunFailure> {
    // Exact precharged caller boundary, separate from the private control helper.
    let function = phase.phase.parts.frames.last().unwrap().function;
    let cursor = Cursor {
        stage: SwiftRunStage::Invocation,
        function: Some(function),
        offset: Some(instruction.offset),
    };
    phase.phase.operation.cursor = cursor;
    phase
        .phase
        .operation
        .control
        .instruction_with_wasi(cursor, Some(phase.phase.operation.wasi.usage()))?;
    phase.work(1)?;
    let frame = phase.phase.parts.frames.last_mut().unwrap();
    frame.pc = frame.pc.checked_add(1).unwrap();
    Ok(())
}
fn invoke(
    phase: &mut FrameOperationPhase<'_>,
    instruction: DecodedInstruction,
    target: Option<u32>,
) -> Result<bool, SwiftRunFailure> {
    let before = observed(phase);
    let answer = match instruction.operation {
        Operation::Const(value) => phase.phase.push_value(value).map(|()| false),
        Operation::Nop => Ok(false),
        operation => phase.control_operation(operation, target),
    };
    let after = observed(phase);
    assert_eq!(
        (after.instructions, after.instruction_fuel),
        (before.instructions, before.instruction_fuel)
    );
    answer
}
fn step(phase: &mut FrameOperationPhase<'_>) -> Result<bool, SwiftRunFailure> {
    let (instruction, target) = fetched(phase);
    if let Err(failure) = boundary(phase, instruction) {
        phase.terminal();
        return Err(failure);
    }
    invoke(phase, instruction, target)
}
fn run_case(case: Case) {
    let mut owner = body_owner(case.body, case.result, &[], SwiftRunBudget::default());
    let mut preparation = Some(owner.prepare_frames(cursor()));
    let mut phase = preparation.take().unwrap().unwrap();
    phase.enter(34).unwrap();
    let pin = pin_ids(&phase);
    let start = observed(&phase);
    let mut controlled = None;
    for (index, (pc, values, controls, work)) in case.expected.iter().enumerate() {
        let decoded = fetched(&mut phase).0;
        let previous_pc = phase.phase.parts.frames[0].pc;
        let before = observed(&phase);
        controlled = Some(step(&mut phase));
        let finished = controlled.take().unwrap().unwrap();
        assert_eq!(
            (
                phase.phase.parts.frames.last().unwrap().pc,
                phase.phase.parts.values.len(),
                phase.phase.parts.controls.len(),
                observed(&phase).execution_work - before.execution_work
            ),
            (*pc, *values, *controls, *work + 1),
            "{} step {}",
            case.name,
            index
        );
        assert_eq!(
            finished,
            index + 1 == case.expected.len(),
            "{} completion {}",
            case.name,
            index
        );
        if let Operation::Block {
            kind, result, end, ..
        } = decoded.operation
        {
            let control = phase.phase.parts.controls.last().unwrap();
            assert!(!control.is_function());
            assert_eq!(control.is_loop(), kind == ControlKind::Loop);
            assert_eq!(control.is_if(), kind == ControlKind::If);
            assert_eq!(
                (
                    control.start(),
                    control.end(),
                    control.height(),
                    control.result()
                ),
                (previous_pc + 1, end, *values, result.is_some())
            );
        }
        assert_eq!(pin_ids(&phase), pin);
        assert_eq!(observed(&phase).live.values.current, *values);
        assert_eq!(observed(&phase).live.controls.current, *controls);
    }
    assert_eq!(
        observed(&phase).instructions - start.instructions,
        case.expected.len() as u64
    );
    assert_eq!(
        observed(&phase).instruction_fuel - start.instruction_fuel,
        case.expected.len() as u64
    );
    assert_eq!(
        observed(&phase).live.controls.peak,
        case.expected.iter().map(|row| row.2).max().unwrap().max(1)
    );
    match phase.finish().unwrap() {
        FrameReturn::Outermost(value) => assert_eq!(value, case.answer, "{}", case.name),
        _ => panic!("outer result"),
    }
    assert_eq!(phase.phase.parts.cache.usage().active_pins, 0);
    assert!(controlled.is_none());
    assert!(matches!(
        phase.complete(FrameOperationStorage {
            preparation,
            entry: None,
            returned: None,
            drained: None,
            controlled
        }),
        FrameCompletion::Completed
    ));
    println!(
        "SC_TRACE {} steps={} expected={:?}",
        case.name,
        case.expected.len(),
        case.expected
    );
    retire(owner);
}
#[test]
fn sc01_decoded_block_loop_if() {
    for case in &CASES[..7] {
        run_case(*case)
    }
}
#[test]
fn sc02_end_else_return() {
    for index in [0, 4, 7, 8] {
        run_case(CASES[index])
    }
}
#[test]
fn sc03_branch_targets() {
    for case in &CASES[9..] {
        run_case(*case)
    }
    // Real result-loop br discards the result and keeps the original label.
    let mut owner = body_owner(
        &[3, 0x7f, 0x41, 23, 0x0c, 0, 0x0b, 0x0b],
        true,
        &[],
        SwiftRunBudget::default(),
    );
    let mut prep = Some(owner.prepare_frames(cursor()));
    let mut phase = prep.take().unwrap().unwrap();
    phase.enter(34).unwrap();
    assert!(!step(&mut phase).unwrap());
    assert!(!step(&mut phase).unwrap());
    let label = phase.phase.parts.controls[1];
    assert!(label.result());
    assert!(!step(&mut phase).unwrap());
    assert_eq!(
        (
            phase.phase.parts.frames[0].pc,
            phase.phase.parts.controls.len(),
            phase.phase.parts.values.len()
        ),
        (1, 2, 0)
    );
    assert!(phase.phase.parts.controls[1].result());
    phase.drain();
    complete_ok(phase, prep);
    retire(owner);
}

fn control_image(
    phase: &FrameOperationPhase<'_>,
) -> Vec<(bool, bool, bool, usize, usize, usize, bool)> {
    phase
        .phase
        .parts
        .controls
        .iter()
        .map(|c| {
            (
                c.is_function(),
                c.is_loop(),
                c.is_if(),
                c.start(),
                c.end(),
                c.height(),
                c.result(),
            )
        })
        .collect()
}
fn settle(
    phase: FrameOperationPhase<'_>,
    prep: Option<Result<FrameOperationPhase<'_>, SwiftRunFailure>>,
) {
    let mut phase = phase;
    let report = phase.drain();
    assert_eq!(report.retained_frames, 0);
    if report.live_unreconciled {
        assert!(matches!(
            complete(phase, prep),
            FrameCompletion::Retained(_)
        ))
    } else {
        complete_ok(phase, prep)
    }
}
#[test]
fn sc04_current_frame_floors() {
    for fault in 0..6 {
        let mut owner = body_owner(
            &[2, 0x7f, 0x41, 7, 0x0b, 0x0b],
            true,
            &[Type::I32],
            SwiftRunBudget::default(),
        );
        let mut prep = Some(owner.prepare_frames(cursor()));
        let mut phase = prep.take().unwrap().unwrap();
        phase.enter(34).unwrap();
        phase.phase.push_value(Value::I32(55)).unwrap();
        phase.enter(36).unwrap();
        let caller_values = phase.phase.parts.values[..2].to_vec();
        let caller_control = control_image(&phase)[..1].to_vec();
        let pins = pin_ids(&phase);
        if fault == 0 {
            phase.phase.push_value(Value::I32(91)).unwrap();
            let mut instruction = fetched(&mut phase).0;
            instruction.operation = Operation::Br(0);
            boundary(&mut phase, instruction).unwrap();
            assert!(invoke(&mut phase, instruction, None).unwrap());
            assert!(matches!(
                phase.finish().unwrap(),
                FrameReturn::CallerContinues
            ));
            assert_eq!(
                phase.phase.parts.values.as_slice(),
                [Value::I32(0), Value::I32(55), Value::I32(91)]
            );
        } else {
            let mut instruction = fetched(&mut phase).0;
            instruction.operation = match fault {
                1 => Operation::Br(1),
                2 => Operation::BrIf(0),
                3 | 4 => {
                    assert!(!step(&mut phase).unwrap());
                    let end = phase.phase.parts.controls.last().unwrap().end();
                    let operands = phase.phase.parts.frames.last().unwrap().operands;
                    let height = if fault == 3 { operands - 1 } else { operands };
                    *phase.phase.parts.controls.last_mut().unwrap() =
                        Control::decoded(ControlKind::Block, 1, end, height, true);
                    Operation::End
                }
                _ => {
                    phase.phase.parts.controls.pop().unwrap();
                    phase
                        .phase
                        .operation
                        .control
                        .remove_live(Live::Controls, 1)
                        .unwrap();
                    Operation::End
                }
            };
            boundary(&mut phase, instruction).unwrap();
            let failure = invoke(&mut phase, instruction, None).unwrap_err();
            assert_eq!(failure.kind, SwiftRunFailureKind::Invariant);
            assert_eq!(&phase.phase.parts.values[..2], caller_values.as_slice());
            assert_eq!(control_image(&phase)[..1], caller_control);
            assert_eq!(pin_ids(&phase), pins);
            assert!(matches!(phase.lifecycle, Lifecycle::Terminal));
        }
        settle(phase, prep);
        retire(owner);
    }
}
#[test]
fn sc05_control_limits() {
    let function = Function {
        blocks: 511,
        ..Function::empty()
    };
    for mode in 0..4 {
        let mut owner = owner_with(
            &function,
            SwiftRunBudget {
                controls: if mode == 2 { 512 } else { 4096 },
                ..SwiftRunBudget::default()
            },
        );
        let mut prep = Some(owner.prepare_frames(cursor()));
        let mut phase = prep.take().unwrap().unwrap();
        if mode >= 2 {
            for _ in 0..if mode == 2 { 1 } else { 8 } {
                phase.enter(34).unwrap();
                for _ in 0..if mode == 2 { 510 } else { 511 } {
                    assert!(!step(&mut phase).unwrap());
                }
            }
        } else {
            phase.enter(34).unwrap();
            for _ in 0..510 {
                step(&mut phase).unwrap();
            }
        }
        if mode == 3 {
            assert_eq!(phase.phase.parts.controls.len(), 4096);
            phase.phase.parts.frames.last_mut().unwrap().pc = 0;
        }
        if mode == 1 {
            step(&mut phase).unwrap();
            assert_eq!(phase.phase.parts.controls.len(), 512);
            phase.phase.parts.frames.last_mut().unwrap().pc = 0;
        }
        if mode == 2 {
            hooks(Hooks {
                predebit_resource: Some(1),
                ..Hooks::default()
            });
        }
        let previous = phase.phase.parts.controls.len();
        let before = observed(&phase);
        let (result, stats) = measure_extended(Some(0), || step(&mut phase));
        assert_eq!(stats.attempts, 0);
        if mode == 0 {
            assert!(!result.unwrap());
            assert_eq!(phase.phase.parts.controls.len(), 512);
            assert_eq!(observed(&phase).live.controls.peak, 512);
        } else {
            assert_eq!(result.unwrap_err().kind, SwiftRunFailureKind::ControlLimit);
            assert_eq!(phase.phase.parts.controls.len(), previous);
            assert_eq!(
                observed(&phase).live.controls.current,
                before.live.controls.current
            );
        }
        hooks(Hooks::default());
        settle(phase, prep);
        retire(owner);
    }
    let mut owner = body_owner(
        &[2, 0x40, 2, 0x40, 2, 0x40, 0x0b, 0x0b, 0x0b, 0x0b],
        false,
        &[],
        SwiftRunBudget {
            controls: 3,
            ..SwiftRunBudget::default()
        },
    );
    let mut prep = Some(owner.prepare_frames(cursor()));
    let mut phase = prep.take().unwrap().unwrap();
    phase.enter(34).unwrap();
    step(&mut phase).unwrap();
    let (result, stats) = measure_extended(Some(0), || step(&mut phase));
    assert!(!result.unwrap());
    assert_eq!(stats.attempts, 0);
    assert_eq!(phase.phase.parts.controls.len(), 3);
    let (result, stats) = measure_extended(Some(0), || step(&mut phase));
    assert_eq!(result.unwrap_err().code, "swift_control_capacity");
    assert_eq!(stats.attempts, 0);
    assert_eq!(phase.phase.parts.controls.len(), 3);
    settle(phase, prep);
    retire(owner);
    let invalid = Function {
        blocks: 512,
        ..Function::empty()
    };
    assert!(validate_swift_reactor(
        &fixture(&invalid),
        SwiftValidationBudget::default(),
        &Cancellation::default()
    )
    .is_err());
}
#[test]
fn sc06_value_limits_types() {
    for fault in 0..5 {
        let mut owner = body_owner(
            &[2, 0x7f, 0x41, 31, 0x41, 32, 0x0c, 0, 0x0b, 0x0b],
            true,
            &[],
            SwiftRunBudget::default(),
        );
        let mut prep = Some(owner.prepare_frames(cursor()));
        let mut phase = prep.take().unwrap().unwrap();
        phase.enter(34).unwrap();
        step(&mut phase).unwrap();
        step(&mut phase).unwrap();
        step(&mut phase).unwrap();
        let (mut instruction, target) = fetched(&mut phase);
        boundary(&mut phase, instruction).unwrap();
        let before = observed(&phase);
        let old = if fault == 0 {
            Some(
                phase
                    .phase
                    .operation
                    .control
                    .test_replace_live_limit(Live::Values, 0),
            )
        } else {
            None
        };
        if fault == 1 {
            HOOKS.with(|slot| {
                let mut h = slot.get();
                h.push_room_reject = true;
                slot.set(h)
            });
        }
        if fault >= 2 {
            instruction.operation = Operation::BrIf(0);
            phase.phase.pop_value().unwrap();
            if fault == 2 {
                phase.phase.pop_value().unwrap();
            } else {
                *phase.phase.parts.values.last_mut().unwrap() = Value::I64(31);
            }
        }
        let failure = invoke(&mut phase, instruction, target).unwrap_err();
        if let Some(old) = old {
            phase
                .phase
                .operation
                .control
                .test_replace_live_limit(Live::Values, old);
        }
        assert_eq!(phase.phase.parts.values.len(), 0);
        assert_eq!(observed(&phase).live.values.current, 0);
        assert!(!phase.cleanup.live_unreconciled);
        if fault < 2 {
            assert_eq!(failure.kind, SwiftRunFailureKind::ValueLimit);
            assert_eq!(phase.phase.parts.controls.len(), 2);
            assert_eq!(observed(&phase).execution_work - before.execution_work, 5);
        } else {
            assert_eq!(failure.kind, SwiftRunFailureKind::Invariant);
        }
        let first = failure;
        let later = phase
            .control_operation(Operation::Return, None)
            .unwrap_err();
        assert_eq!(
            (later.kind, later.code, later.function, later.offset),
            (first.kind, first.code, first.function, first.offset)
        );
        settle(phase, prep);
        retire(owner);
    }
}

// Finite fault windows for the hand-authored traces only. Rows name each
// pre-effect debit and the exact already-visible pop prefix at its rejection.
// They are assertions about these fixtures, never an executable guest model.
fn fixture_windows(
    instruction: Operation,
    helper_work: u64,
    controls: usize,
) -> Vec<(u64, usize, usize)> {
    match instruction {
        Operation::Const(_) => vec![(1, 0, 0)],
        Operation::Block {
            kind: ControlKind::If,
            ..
        } => vec![(1, 0, 0), (1, 1, 0)],
        Operation::Block { .. } => vec![(1, 0, 0)],
        Operation::End if helper_work == 4 => vec![(1, 0, 0), (1, 0, 1), (1, 1, 1), (1, 1, 1)],
        Operation::End => vec![(1, 0, 0), (1, 0, 1)],
        Operation::Br(_) => vec![(helper_work - 3, 0, 0), (1, 0, 0), (1, 1, 0), (1, 1, 0)],
        Operation::BrIf(_) if helper_work == 1 => vec![(1, 0, 0)],
        Operation::BrIf(_) | Operation::BrTable { .. } => vec![
            (1, 0, 0),
            (helper_work - 4, 1, 0),
            (1, 1, 0),
            (1, 2, 0),
            (1, 2, 0),
        ],
        Operation::Return | Operation::Else { .. } | Operation::Nop => vec![],
        _ => panic!("fixture finite table only {instruction:?} controls={controls}"),
    }
}
#[test]
fn sc07_exact_work_prefixes() {
    let mut runs = 0;
    for case in CASES {
        let total: u64 = case.expected.iter().map(|row| row.3 + 1).sum();
        for allowance in 0..=total {
            let mut owner = body_owner(case.body, case.result, &[], SwiftRunBudget::default());
            let mut prep = Some(owner.prepare_frames(cursor()));
            let mut phase = prep.take().unwrap().unwrap();
            phase.enter(34).unwrap();
            let start = observed(&phase);
            let old = phase
                .phase
                .operation
                .control
                .test_replace_execution_work_limit(start.execution_work + allowance);
            let mut spent = 0;
            let mut failed = false;
            for (ordinal, expected) in case.expected.iter().enumerate() {
                let (instruction, _) = fetched(&mut phase);
                let pc = phase.phase.parts.frames[0].pc;
                let values = phase.phase.parts.values.to_vec();
                let controls = control_image(&phase);
                let mut expected_pc = pc;
                let mut removed_values = 0;
                let mut removed_controls = 0;
                let mut debit_failure = false;
                if spent + 1 > allowance {
                    debit_failure = true;
                } else {
                    spent += 1;
                    expected_pc += 1;
                    for (charge, rv, rc) in
                        fixture_windows(instruction.operation, expected.3, controls.len())
                    {
                        if spent + charge > allowance {
                            removed_values = rv;
                            removed_controls = rc;
                            debit_failure = true;
                            break;
                        }
                        spent += charge;
                    }
                }
                let result = step(&mut phase);
                if debit_failure {
                    let failure = result.unwrap_err();
                    assert_eq!(
                        failure.kind,
                        SwiftRunFailureKind::WorkExhausted,
                        "{} budget {} step {}",
                        case.name,
                        allowance,
                        ordinal
                    );
                    assert_eq!(phase.phase.parts.frames[0].pc, expected_pc);
                    assert_eq!(
                        phase.phase.parts.values.as_slice(),
                        &values[..values.len() - removed_values],
                        "{} budget {} values",
                        case.name,
                        allowance
                    );
                    assert_eq!(
                        control_image(&phase),
                        controls[..controls.len() - removed_controls],
                        "{} budget {} controls",
                        case.name,
                        allowance
                    );
                    assert_eq!(
                        observed(&phase).execution_work - start.execution_work,
                        spent
                    );
                    assert_eq!(
                        observed(&phase).instructions - start.instructions,
                        ordinal as u64 + 1
                    );
                    assert_eq!(
                        observed(&phase).instruction_fuel - start.instruction_fuel,
                        ordinal as u64 + 1
                    );
                    assert_eq!(
                        observed(&phase).live.values.current,
                        phase.phase.parts.values.len()
                    );
                    assert_eq!(
                        observed(&phase).live.controls.current,
                        phase.phase.parts.controls.len()
                    );
                    assert_eq!(
                        failure.at_failure.execution_work,
                        start.execution_work + spent
                    );
                    failed = true;
                    break;
                } else {
                    assert_eq!(result.unwrap(), ordinal + 1 == case.expected.len());
                    assert_eq!(
                        (
                            phase.phase.parts.frames[0].pc,
                            phase.phase.parts.values.len(),
                            phase.phase.parts.controls.len()
                        ),
                        (expected.0, expected.1, expected.2)
                    );
                }
            }
            assert_eq!(failed, allowance < total);
            phase
                .phase
                .operation
                .control
                .test_replace_execution_work_limit(old);
            settle(phase, prep);
            retire(owner);
            runs += 1;
        }
    }
    for allowance in 0..=4 {
        let mut owner = body_owner(
            &[3, 0x7f, 0x41, 23, 0x0c, 0, 0x0b, 0x0b],
            true,
            &[],
            SwiftRunBudget::default(),
        );
        let mut prep = Some(owner.prepare_frames(cursor()));
        let mut phase = prep.take().unwrap().unwrap();
        phase.enter(34).unwrap();
        step(&mut phase).unwrap();
        step(&mut phase).unwrap();
        let before = observed(&phase);
        let old = phase
            .phase
            .operation
            .control
            .test_replace_execution_work_limit(before.execution_work + allowance);
        let result = step(&mut phase);
        if allowance == 4 {
            assert!(!result.unwrap());
            assert_eq!(
                (
                    phase.phase.parts.frames[0].pc,
                    phase.phase.parts.values.len(),
                    phase.phase.parts.controls.len()
                ),
                (1, 0, 2)
            );
        } else {
            assert_eq!(result.unwrap_err().kind, SwiftRunFailureKind::WorkExhausted);
            assert_eq!(phase.phase.parts.values.as_slice(), [Value::I32(23)]);
            assert_eq!(phase.phase.parts.controls.len(), 2);
            assert_eq!(
                phase.phase.parts.frames[0].pc,
                if allowance == 0 { 2 } else { 3 }
            );
        }
        assert_eq!(
            observed(&phase).execution_work - before.execution_work,
            if allowance < 2 {
                allowance
            } else if allowance < 4 {
                2
            } else {
                4
            }
        );
        phase
            .phase
            .operation
            .control
            .test_replace_execution_work_limit(old);
        settle(phase, prep);
        retire(owner);
        runs += 1;
    }
    println!("SC07 exhaustive fixture work prefixes={runs}");
}
fn fixture_windows_for_case(case: Case, index: usize) -> usize {
    match case.expected[index].3 {
        0 => 0,
        1 => 1,
        2 => 2,
        4 => 4,
        5 => {
            if case.name == "br_function" {
                4
            } else {
                5
            }
        }
        6 => 5,
        _ => unreachable!(),
    }
}
#[test]
fn sc08_cancellation_first_failure() {
    // Every trace boundary, including zero-helper-work Else/Return, is covered.
    let mut runs = 0;
    for case in CASES {
        for boundary_index in 0..case.expected.len() {
            let mut owner = body_owner(case.body, case.result, &[], SwiftRunBudget::default());
            owner
                .wasi
                .as_mut()
                .unwrap()
                .dispatch(
                    owner.control.as_mut().unwrap(),
                    WasiFunction::ArgsSizesGet,
                    &[Value::I32(0), Value::I32(4)],
                    &mut [0; 8],
                    cursor(),
                )
                .unwrap();
            let wasi = owner.wasi.as_ref().unwrap().usage();
            let mut prep = Some(owner.prepare_frames(cursor()));
            let mut phase = prep.take().unwrap().unwrap();
            phase.enter(34).unwrap();
            for _ in 0..boundary_index {
                assert!(!step(&mut phase).unwrap());
            }
            let values = phase.phase.parts.values.to_vec();
            let controls = control_image(&phase);
            let (instruction, _) = fetched(&mut phase);
            phase.phase.operation.control.cancellation().cancel();
            let failure = step(&mut phase).unwrap_err();
            assert_eq!(
                (
                    failure.kind,
                    failure.function,
                    failure.offset,
                    failure.at_failure.wasi
                ),
                (
                    SwiftRunFailureKind::Cancelled,
                    Some(34),
                    Some(instruction.offset),
                    Some(wasi)
                )
            );
            assert_eq!(phase.phase.parts.values.as_slice(), values);
            assert_eq!(control_image(&phase), controls);
            let later = phase
                .control_operation(Operation::Return, None)
                .unwrap_err();
            assert_eq!(
                (later.code, later.function, later.offset),
                (failure.code, failure.function, failure.offset)
            );
            let report = phase.drain();
            assert_eq!(report.first_failure.unwrap().code, failure.code);
            assert_eq!(report.usage.wasi, Some(wasi));
            complete_ok(phase, prep);
            retire(owner);
            runs += 1;
        }
    }
    let mut helper_runs = 0;
    for case in CASES {
        for step_index in 0..case.expected.len() {
            for checkpoint in 0..fixture_windows_for_case(*case, step_index) {
                let mut owner = body_owner(case.body, case.result, &[], SwiftRunBudget::default());
                let mut prep = Some(owner.prepare_frames(cursor()));
                let mut phase = prep.take().unwrap().unwrap();
                phase.enter(34).unwrap();
                for _ in 0..step_index {
                    step(&mut phase).unwrap();
                }
                let (instruction, target) = fetched(&mut phase);
                let windows = fixture_windows(
                    instruction.operation,
                    case.expected[step_index].3,
                    phase.phase.parts.controls.len(),
                );
                boundary(&mut phase, instruction).unwrap();
                let values = phase.phase.parts.values.to_vec();
                let controls = control_image(&phase);
                let before = observed(&phase);
                hooks(Hooks {
                    push_fault: 6,
                    cancel_local: Some(checkpoint),
                    ..Hooks::default()
                });
                let failure = invoke(&mut phase, instruction, target).unwrap_err();
                let (_, rv, rc) = windows[checkpoint];
                assert_eq!(failure.kind, SwiftRunFailureKind::Cancelled);
                assert_eq!(
                    phase.phase.parts.values.as_slice(),
                    &values[..values.len() - rv]
                );
                assert_eq!(control_image(&phase), controls[..controls.len() - rc]);
                assert_eq!(
                    observed(&phase).execution_work - before.execution_work,
                    windows[..checkpoint].iter().map(|r| r.0).sum::<u64>()
                );
                hooks(Hooks::default());
                settle(phase, prep);
                retire(owner);
                helper_runs += 1;
            }
        }
    }
    // Last fallible predebit after its successful work: no publication.
    for index in [0, 4, 5] {
        let case = CASES[index];
        let mut owner = body_owner(case.body, case.result, &[], SwiftRunBudget::default());
        let mut prep = Some(owner.prepare_frames(cursor()));
        let mut phase = prep.take().unwrap().unwrap();
        phase.enter(34).unwrap();
        if index != 0 {
            step(&mut phase).unwrap();
        }
        let (instruction, target) = fetched(&mut phase);
        boundary(&mut phase, instruction).unwrap();
        hooks(Hooks {
            push_fault: 7,
            ..Hooks::default()
        });
        let controls = phase.phase.parts.controls.len();
        let failure = invoke(&mut phase, instruction, target).unwrap_err();
        assert_eq!(failure.kind, SwiftRunFailureKind::Cancelled);
        assert_eq!(phase.phase.parts.controls.len(), controls);
        hooks(Hooks::default());
        settle(phase, prep);
        retire(owner);
    }
    af17_real_prior_wasi_effect_and_sticky_first_failure();
    println!("SC08 caller cancellation boundaries={runs} helper work checkpoints={helper_runs} control predebits=3");
}
#[test]
fn sc09_defensive_live_faults() {
    for fault in 0..9 {
        let mut owner = body_owner(
            &[2, 0x40, 0x0b, 0x0b],
            false,
            &[],
            SwiftRunBudget::default(),
        );
        let mut prep = Some(owner.prepare_frames(cursor()));
        let mut phase = prep.take().unwrap().unwrap();
        phase.enter(34).unwrap();
        let (mut instruction, _) = fetched(&mut phase);
        boundary(&mut phase, instruction).unwrap();
        match fault {
            0 => {
                phase
                    .phase
                    .operation
                    .control
                    .remove_live(Live::Controls, 1)
                    .unwrap();
            }
            1 => phase.phase.parts.frames[0].pc = usize::MAX,
            2 => instruction.operation = Operation::Br(u32::MAX),
            3 => {
                instruction.operation = Operation::Block {
                    kind: ControlKind::Block,
                    result: None,
                    end: usize::MAX,
                    alternative: None,
                }
            }
            4 => phase.phase.parts.frames[0].operands = 1,
            5 => instruction.operation = Operation::Nop,
            6 => {
                instruction.operation = Operation::BrTable {
                    first: 0,
                    count: 0,
                    default: 0,
                }
            }
            8 => {
                phase.phase.parts.controls[0] = Control::function_entry(usize::MAX, 0, false);
            }
            _ => {
                let end = phase.phase.parts.controls[0].end();
                phase.phase.parts.controls[0] =
                    Control::decoded(ControlKind::Block, 0, end, 0, false);
            }
        }
        let values = phase.phase.parts.values.to_vec();
        let controls = control_image(&phase);
        let pins = pin_ids(&phase);
        let failure = phase
            .control_operation(instruction.operation, None)
            .unwrap_err();
        assert_eq!(
            failure.kind,
            if fault == 5 {
                SwiftRunFailureKind::UnsupportedEnvironment
            } else {
                SwiftRunFailureKind::Invariant
            }
        );
        assert_eq!(phase.phase.parts.values.as_slice(), values);
        assert_eq!(control_image(&phase), controls);
        assert_eq!(pin_ids(&phase), pins);
        assert!(matches!(phase.lifecycle, Lifecycle::Terminal));
        let report = phase.drain();
        assert_eq!(report.first_failure.unwrap().code, failure.code);
        if fault == 0 {
            assert!(report.live_unreconciled);
            assert!(matches!(
                complete(phase, prep),
                FrameCompletion::Retained(_)
            ));
            drop(owner);
        } else {
            complete_ok(phase, prep);
            retire(owner);
        }
    }
    // Actual primitive after-pop rejection: each condition family plus a saved
    // result in close, using the approved one-shot original-ledger fault.
    for (case_index, steps) in [(4, 1), (11, 3), (13, 4), (1, 2)] {
        for enabled in [false, true] {
            let case = CASES[case_index];
            let mut owner = body_owner(case.body, case.result, &[], SwiftRunBudget::default());
            owner
                .wasi
                .as_mut()
                .unwrap()
                .dispatch(
                    owner.control.as_mut().unwrap(),
                    WasiFunction::ArgsSizesGet,
                    &[Value::I32(0), Value::I32(4)],
                    &mut [0; 8],
                    cursor(),
                )
                .unwrap();
            let actual_wasi = owner.wasi.as_ref().unwrap().usage();
            let mut prep = Some(owner.prepare_frames(cursor()));
            let mut phase = prep.take().unwrap().unwrap();
            phase.enter(34).unwrap();
            for _ in 0..steps {
                step(&mut phase).unwrap();
            }
            let (instruction, target) = fetched(&mut phase);
            boundary(&mut phase, instruction).unwrap();
            let previous_length = phase.phase.parts.values.len();
            hooks(Hooks {
                push_fault: if enabled { 5 } else { 0 },
                ..Hooks::default()
            });
            let result = invoke(&mut phase, instruction, target);
            hooks(Hooks::default());
            if enabled {
                let failure = result.unwrap_err();
                assert_eq!(failure.code, "swift_run_live_underflow");
                assert_eq!(failure.kind, SwiftRunFailureKind::Invariant);
                assert_eq!(failure.resource, None);
                assert_eq!(failure.stage, SwiftRunStage::Cleanup);
                assert_eq!(failure.function, None);
                assert_eq!(failure.offset, None);
                assert_eq!(failure.at_failure.wasi, Some(actual_wasi));
                assert_eq!(phase.phase.parts.values.len(), previous_length - 1);
                assert_eq!(observed(&phase).live.values.current, 0);
                assert!(phase.cleanup.live_unreconciled);
                assert!(matches!(phase.lifecycle, Lifecycle::Terminal));
                let later = phase
                    .control_operation(Operation::Return, None)
                    .unwrap_err();
                assert_eq!(
                    (later.code, later.function, later.offset),
                    (failure.code, failure.function, failure.offset)
                );
                phase.phase.operation.control.cancellation().cancel();
                let report = phase.drain();
                assert!(report.live_unreconciled);
                assert_eq!(report.first_failure.unwrap().code, failure.code);
                assert!(matches!(
                    complete(phase, prep),
                    FrameCompletion::Retained(_)
                ));
                assert!(owner.prepare_frames(cursor()).is_err());
                assert!(owner.prepare_value_operation(cursor()).is_err());
                let mut resumed = Some(owner.resume_frame_cleanup());
                let mut phase = resumed.take().unwrap().unwrap();
                assert!(phase.drain().live_unreconciled);
                assert!(matches!(
                    complete(phase, resumed),
                    FrameCompletion::Retained(_)
                ));
                let mut owned = Some(owner);
                assert!(SwiftReactorInstance::cleanup_owned(&mut owned).is_err());
                assert!(owned.is_some());
                drop(owned);
            } else {
                result.unwrap();
                assert!(!phase.cleanup.live_unreconciled);
                settle(phase, prep);
                retire(owner);
            }
        }
    }
    // Wrong original owner is rejected by real admission; restore both moved
    // owners before their original cleanup, never manufacture an authority.
    let mut first = owner();
    let mut second = owner();
    std::mem::swap(&mut first.wasi, &mut second.wasi);
    assert_eq!(
        first.prepare_frames(cursor()).err().unwrap().code,
        "swift_run_reservation_owner"
    );
    std::mem::swap(&mut first.wasi, &mut second.wasi);
    retire(first);
    retire(second);
}
#[test]
fn sc10_retained_cleanup() {
    for prefix in [0, 1, 2, 4] {
        let mut foreign = owner();
        let mut owner = body_owner(
            &[2, 0x7f, 0x41, 31, 0x41, 32, 0x0c, 0, 0x0b, 0x0b],
            true,
            &[],
            SwiftRunBudget::default(),
        );
        install_foreign(&mut foreign);
        let mut prep = Some(owner.prepare_frames(cursor()));
        let mut phase = prep.take().unwrap().unwrap();
        for function in [34, 36, 34, 36] {
            phase.enter(function).unwrap();
        }
        for _ in 0..3 {
            step(&mut phase).unwrap();
        }
        let before = observed(&phase).execution_work;
        let old = phase
            .phase
            .operation
            .control
            .test_replace_execution_work_limit(before + 1 + prefix);
        let failure = step(&mut phase).unwrap_err();
        let ids = pin_ids(&phase);
        phase.phase.operation.control.cancellation().cancel();
        hooks(Hooks {
            release_mask: 0b0101,
            ..Hooks::default()
        });
        let report = phase.drain();
        assert_eq!(report.retained_frames, 2);
        assert_eq!(pin_ids(&phase), vec![ids[1], ids[3]]);
        assert_eq!(HOOKS.with(|s| s.get().release_seen), 4);
        assert_eq!(report.first_failure.unwrap().code, failure.code);
        let second = phase.drain();
        assert_eq!(second.retained_frames, 2);
        assert_eq!(HOOKS.with(|s| s.get().release_seen), 4);
        phase
            .phase
            .operation
            .control
            .test_replace_execution_work_limit(old);
        assert!(matches!(
            complete(phase, prep),
            FrameCompletion::Retained(_)
        ));
        assert!(owner.prepare_frames(cursor()).is_err());
        assert!(owner.prepare_value_operation(cursor()).is_err());
        let mut owned = Some(owner);
        assert!(SwiftReactorInstance::cleanup_owned(&mut owned).is_err());
        owner = owned.take().unwrap();
        restore_foreign(&mut foreign);
        drain_complete(&mut owner);
        retire(owner);
        retire(foreign);
    }
    af09_real_pin_and_nested_completion_failure_coexist();
    af13_guard_and_multiple_frames_keep_independent_actual_pins();
}
#[test]
fn sc11_completion_accounting() {
    for reject in [false, true] {
        let mut owner = body_owner(&[0x0b], false, &[], SwiftRunBudget::default());
        let previous = usage(&owner).reservations.construction.current;
        let mut preparation = Some(owner.prepare_frames(cursor()));
        let mut phase = preparation.take().unwrap().unwrap();
        assert_eq!(
            phase.cleanup.bound.unwrap().admitted,
            previous + FRAME_OPERATION_BYTES.unwrap()
        );
        phase.enter(34).unwrap();
        let mut controlled = Some(step(&mut phase));
        assert!(controlled.take().unwrap().unwrap());
        let mut returned = Some(phase.finish());
        assert!(matches!(
            returned.take().unwrap().unwrap(),
            FrameReturn::Outermost(None)
        ));
        hooks(Hooks {
            reject_outer_restore: reject,
            ..Hooks::default()
        });
        let completion = phase.complete(FrameOperationStorage {
            preparation,
            entry: None,
            returned,
            drained: None,
            controlled,
        });
        if reject {
            assert!(matches!(completion, FrameCompletion::RestoreRejected(_)));
            assert!(usage(&owner).reservations.construction.current > previous);
            hooks(Hooks::default());
            drain_complete(&mut owner);
        } else {
            assert!(matches!(completion, FrameCompletion::Completed));
        }
        assert_eq!(usage(&owner).reservations.construction.current, previous);
        retire(owner);
    }
    for accepted in [false, true] {
        let mut owner = owner();
        let current = usage(&owner).reservations.combined.current;
        let ceiling = current + FRAME_OPERATION_BYTES.unwrap() - usize::from(!accepted);
        let old = owner
            .control
            .as_mut()
            .unwrap()
            .test_replace_combined_limit(ceiling);
        let previous = usage(&owner).reservations.construction.current;
        let mut preparation = Some(owner.prepare_frames(cursor()));
        if accepted {
            let phase = preparation.take().unwrap().unwrap();
            assert_eq!(
                phase.cleanup.bound.unwrap().admitted,
                previous + FRAME_OPERATION_BYTES.unwrap()
            );
            complete_ok(phase, preparation);
        } else {
            let failure = preparation.take().unwrap().err().unwrap();
            assert_eq!(failure.kind, SwiftRunFailureKind::CombinedExhausted);
            assert_eq!(failure.resource, Some(SwiftRunResource::Combined));
            assert_eq!(failure.attempted, ceiling as u64 + 1);
            assert_eq!(usage(&owner).reservations.construction.current, previous);
            assert!(owner.state.as_ref().unwrap().frame_cleanup.is_empty());
            assert!(owner.state.as_ref().unwrap().frames.is_empty());
        }
        owner
            .control
            .as_mut()
            .unwrap()
            .test_replace_combined_limit(old);
        retire(owner);
    }
    // Observe the actual constructor's header admission before its first arena:
    // below rejects the header; exact admits it, then rejects the next arena.
    for at in [false, true] {
        let header = execution_header_bytes().unwrap();
        let proof = validate_swift_reactor(
            &fixture(&Function::empty()),
            SwiftValidationBudget::default(),
            &Cancellation::default(),
        )
        .unwrap();
        let mut pair = Some(
            RuntimeControl::adopt(
                proof,
                SwiftRunBudget {
                    state_bytes: header - usize::from(!at),
                    ..SwiftRunBudget::default()
                },
                Instant::now(),
                Cancellation::default(),
            )
            .unwrap(),
        );
        let mut returned = Some(SwiftReactorInstance::construct(
            &mut pair,
            WasiGrants::default(),
            WasiBudget {
                one_transfer_bytes: 64,
                log_bytes: 64,
                ..WasiBudget::default()
            },
            Instant::now(),
            cursor(),
        ));
        let tail = match returned.take().unwrap() {
            Err(ConstructionFailure::Cleanup(tail)) => tail,
            _ => panic!("narrow original State budget"),
        };
        let mut failure = None;
        let mut usage = None;
        tail.complete((pair, returned), &mut failure, &mut usage);
        let failure = failure.unwrap();
        assert_eq!(failure.kind, SwiftRunFailureKind::CategoryExhausted);
        assert_eq!(
            failure.resource,
            Some(SwiftRunResource::Reservation(
                SwiftReservationCategory::State
            ))
        );
        assert_eq!(
            failure.at_failure.reservations.state.current,
            if at { header } else { 0 }
        );
        assert_eq!(usage.unwrap().reservations.combined.current, 0);
    }
    {
        let mut owner = body_owner(&[0x0b], false, &[], SwiftRunBudget::default());
        let before = usage(&owner).reservations.construction.current;
        let mut preparation = Some(owner.prepare_frames(cursor()));
        let mut phase = preparation.take().unwrap().unwrap();
        phase.enter(34).unwrap();
        let controlled = Some(step(&mut phase));
        assert!(controlled.as_ref().unwrap().as_ref().unwrap());
        phase.finish().unwrap();
        assert!(matches!(
            phase.complete(FrameOperationStorage {
                preparation,
                entry: None,
                returned: None,
                drained: None,
                controlled
            }),
            FrameCompletion::Retained(_)
        ));
        assert!(usage(&owner).reservations.construction.current > before);
        drain_complete(&mut owner);
        assert_eq!(usage(&owner).reservations.construction.current, before);
        retire(owner);
    }
    // Full original dropped-phase, nonempty/zero-frame and retained completion
    // barriers execute again inside this named group; no new storage authority.
    af18_dropped_phase_cleanup_resume_has_no_admission_work_or_value_access();
    af20_original_provenance_layout_and_consuming_barriers_preserve_owners();
    af22_frozen_accounting_and_value_phase_reservations_stay_distinct();
    println!(
        "SC11 header={} frame={} slot={} production/unit layouts separately measured",
        execution_header_bytes().unwrap(),
        FRAME_OPERATION_BYTES.unwrap(),
        size_of::<Option<Result<bool, SwiftRunFailure>>>()
    );
}
#[test]
fn sc12_allocation_shared_source() {
    for case in CASES {
        let mut owner = body_owner(case.body, case.result, &[], SwiftRunBudget::default());
        let mut prep = Some(owner.prepare_frames(cursor()));
        let mut phase = prep.take().unwrap().unwrap();
        let (_, cold) = measure_extended(None, || phase.enter(34).unwrap());
        assert!(cold.attempts > 0);
        for _ in 0..case.expected.len() {
            step(&mut phase).unwrap();
        }
        phase.finish().unwrap();
        complete_ok(phase, prep);
        let mut prep = Some(owner.prepare_frames(cursor()));
        let mut phase = prep.take().unwrap().unwrap();
        let (outcome, stats) = measure_extended(Some(0), || {
            phase.enter(34)?;
            let mut completed = false;
            for _ in 0..case.expected.len() {
                completed = step(&mut phase)?;
            }
            assert!(completed);
            let returned = phase.finish()?;
            Ok::<_, SwiftRunFailure>(((), returned))
        });
        let ((), returned) = outcome.unwrap();
        match returned {
            FrameReturn::Outermost(value) => assert_eq!(value, case.answer),
            _ => panic!("outer return"),
        };
        assert_eq!(
            (stats.attempts, stats.allocations, stats.reallocations),
            (0, 0, 0)
        );
        let (completed, completion_stats) = measure_extended(Some(0), || complete(phase, prep));
        assert!(matches!(completed, FrameCompletion::Completed));
        assert_eq!(completion_stats.attempts, 0);
        println!(
            "SC12 {} cold={} warm=0 completion=0",
            case.name, cold.attempts
        );
        retire(owner);
    }
}

pub(in crate::experimental_swift_reactor::execution::frame_operations) fn host_test_bytes(body:&[u8],result:bool,locals:&[Type])->Vec<u8>{body_fixture(body,result,locals)}
