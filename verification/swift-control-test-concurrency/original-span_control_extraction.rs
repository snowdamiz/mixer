#![cfg(feature = "experimental-span-execution")]
mod common;
use common::*;
use mixer_vm::experimental::{cache::*, execution::*, validate_spans, ValidationBudget};
use mixer_vm::{Cancellation, Limits, Profile, Type, Value};
#[path = "common/allocation_observer.rs"]
mod allocation_observer;
use allocation_observer::{
    begin, Background, Observed, Ownership, CALLS, LIVE, PEAK, REALLOCATIONS,
};
use std::sync::atomic::Ordering::SeqCst;

#[global_allocator]
static ALLOCATOR: Observed = Observed;

struct Case {
    name: &'static str,
    bytes: Vec<u8>,
    args: Vec<Value>,
    expected: Option<Value>,
}
fn case(name: &'static str, result: bool, code: Vec<u8>, expected: Option<Value>) -> Case {
    Case {
        name,
        bytes: Spec::one(vec![], result.then_some(Type::I32), code).bytes(),
        args: vec![],
        expected,
    }
}
fn cases() -> Vec<Case> {
    let mut cases = vec![
        case(
            "block-empty",
            false,
            vec![2, 0x40, 0x0c, 0, 0, 0x0b, 0x0b],
            None,
        ),
        case(
            "block-result",
            true,
            vec![2, 0x7f, 0x41, 17, 0x0c, 0, 0, 0x0b, 0x0b],
            Some(Value::I32(17)),
        ),
        case("function-empty", false, vec![0x0c, 0, 0, 0x0b], None),
        case(
            "function-result",
            true,
            vec![0x41, 19, 0x0c, 0, 0, 0x0b],
            Some(Value::I32(19)),
        ),
        case(
            "end-result",
            true,
            vec![2, 0x7f, 0x41, 23, 0x0b, 0x0b],
            Some(Value::I32(23)),
        ),
        case(
            "br-if-false",
            true,
            vec![
                2, 0x7f, 0x41, 11, 0x41, 0, 0x0d, 0, 0x1a, 0x41, 13, 0x0b, 0x0b,
            ],
            Some(Value::I32(13)),
        ),
        case(
            "br-if-true",
            true,
            vec![
                2, 0x7f, 0x41, 11, 0x41, 1, 0x0d, 0, 0x1a, 0x41, 13, 0x0b, 0x0b,
            ],
            Some(Value::I32(11)),
        ),
        case(
            "if-false",
            true,
            vec![0x41, 0, 4, 0x7f, 0x41, 31, 5, 0x41, 37, 0x0b, 0x0b],
            Some(Value::I32(37)),
        ),
        case(
            "if-true",
            true,
            vec![0x41, 1, 4, 0x7f, 0x41, 31, 5, 0x41, 37, 0x0b, 0x0b],
            Some(Value::I32(31)),
        ),
    ];
    for (name, selector, expected) in [
        ("table-chosen", 0, 18),
        ("table-default", 1, 17),
        ("table-negative", 0x7f, 17),
    ] {
        cases.push(case(
            name,
            true,
            vec![
                2, 0x7f, 2, 0x7f, 0x41, 17, 0x41, selector, 0x0e, 1, 0, 1, 0x0b, 0x41, 1, 0x6a,
                0x0b, 0x0b,
            ],
            Some(Value::I32(expected)),
        ));
    }
    for (name, result) in [("loop-empty", false), ("loop-result", true)] {
        let mut code = vec![
            3,
            if result { 0x7f } else { 0x40 },
            0x20,
            0,
            0x41,
            1,
            0x6b,
            0x22,
            0,
            0x0d,
            0,
        ];
        if result {
            code.extend([0x41, 29]);
        }
        code.extend([0x0b, 0x0b]);
        cases.push(Case {
            name,
            bytes: Spec::one(vec![Type::I32], result.then_some(Type::I32), code).bytes(),
            args: vec![Value::I32(2)],
            expected: result.then_some(Value::I32(29)),
        });
    }
    let mut spec = Spec::one(
        vec![],
        Some(Type::I32),
        vec![2, 0x7f, 0x10, 1, 0x0c, 0, 0, 0x0b, 0x0b],
    );
    spec.functions.push(Function::new(
        vec![],
        Some(Type::I32),
        vec![0x41, 31, 0x0c, 0, 0, 0x0b],
    ));
    cases.push(Case {
        name: "nested-function",
        bytes: spec.bytes(),
        args: vec![],
        expected: Some(Value::I32(31)),
    });
    cases
}
#[derive(Clone)]
struct Config {
    limits: Limits,
    budget: ExecutionBudget,
    cache: CacheBudget,
    cancelled: bool,
    fail: usize,
    cancel_at: usize,
}
impl Default for Config {
    fn default() -> Self {
        Self {
            limits: Limits {
                profile: Profile::TableMemoryV3,
                operand_stack: 16,
                call_depth: 8,
                control_depth: 8,
                fuel: 1000,
                ..Limits::default()
            },
            budget: ExecutionBudget {
                live_values: 64,
                live_controls: 32,
                work_credits: 1_000_000,
                ..ExecutionBudget::default()
            },
            cache: CacheBudget::default(),
            cancelled: false,
            fail: 0,
            cancel_at: 0,
        }
    }
}
fn make(case: &Case, config: Config, token: &Cancellation) -> SpanInstance {
    let proof = validate_spans(
        &case.bytes,
        config.limits.clone(),
        ValidationBudget::default(),
        token,
    )
    .unwrap();
    let cache = FunctionCache::new(proof, config.cache, token).unwrap();
    SpanInstance::new(cache, config.budget, token.clone()).unwrap()
}
fn clean(span: &SpanInstance) {
    let usage = span.usage();
    assert_eq!(
        (
            usage.frames,
            usage.live_values,
            usage.live_controls,
            usage.active_pins
        ),
        (0, 0, 0, 0)
    );
    assert_eq!(span.cache_usage().active_pins, 0);
}
// Exact output is compared between independently built archived baseline and
// candidate. The assertion here also binds each successful hand-authored result.
fn trace(
    case: &Case,
    config: Config,
) -> (
    Result<Option<Value>, ExecutionFailure>,
    ExecutionUsage,
    usize,
) {
    let token = Cancellation::default();
    let proof = validate_spans(
        &case.bytes,
        config.limits.clone(),
        ValidationBudget::default(),
        &token,
    )
    .unwrap();
    let cache = FunctionCache::new(proof, config.cache, &token).unwrap();
    let interval = begin(0, 0, &token);
    let built = SpanInstance::new(cache, config.budget, token.clone());
    let baseline = interval.finish();
    let construction = (
        CALLS.load(SeqCst),
        REALLOCATIONS.load(SeqCst),
        PEAK.load(SeqCst) - baseline,
    );
    let mut span = match built {
        Ok(span) => span,
        Err(error) => {
            println!("control_trace {} config={:?}/{:?}/{:?}/{}/{}/{} constructor={error:?} allocations={construction:?}", case.name, config.limits, config.budget, config.cache, config.cancelled, config.fail, config.cancel_at);
            return (Err(error), error.usage, 0);
        }
    };
    let initial = span.usage();
    if config.cancelled {
        token.cancel();
    }
    let interval = begin(config.fail, config.cancel_at, &token);
    let first = span.invoke("run", &case.args);
    let baseline = interval.finish();
    let cold = (
        CALLS.load(SeqCst),
        REALLOCATIONS.load(SeqCst),
        PEAK.load(SeqCst) - baseline,
    );
    assert_eq!(cold.1, 0);
    clean(&span);
    if let Ok(value) = first {
        assert_eq!(value, case.expected, "{}", case.name);
    }
    let first_usage = span.usage();
    let first_cache = span.cache_usage();
    if let Err(error) = first {
        let interval = begin(1, 0, &token);
        let second = span.invoke("run", &case.args);
        interval.finish();
        assert_eq!(second, Err(error));
        assert_eq!(span.usage(), first_usage);
        assert_eq!(span.cache_usage(), first_cache);
        assert_eq!((CALLS.load(SeqCst), REALLOCATIONS.load(SeqCst)), (0, 0));
    }
    println!("control_trace {} config={:?}/{:?}/{:?}/{}/{}/{} initial={initial:?} first={first:?} final={first_usage:?} cache={first_cache:?} allocations={construction:?}/{cold:?}", case.name, config.limits, config.budget, config.cache, config.cancelled, config.fail, config.cancel_at);
    (first, first_usage, cold.0)
}

#[test]
fn shared_control_public_parity_trace() {
    let _ownership = Ownership::new();
    for case in cases() {
        assert!(trace(&case, Config::default()).0.is_ok());
    }
    let trap = case("unreachable", false, vec![2, 0x40, 0, 0x0b, 0x0b], None);
    assert_eq!(
        trace(&trap, Config::default()).0.unwrap_err().kind,
        ExecutionFailureKind::GuestTrap
    );
}

#[test]
fn shared_control_close_partial_effects() {
    let _ownership = Ownership::new();
    // These public fixtures exercise End, saved-result close, and conditional
    // selector pops at every attainable work refusal. Private malformed-state
    // order is separately tested by an explicitly labelled archived unit overlay.
    for case in cases()
        .into_iter()
        .filter(|case| matches!(case.name, "end-result" | "br-if-false" | "block-result"))
    {
        let used = trace(&case, Config::default()).1.work_used;
        for work in 0..=used + 1 {
            let mut config = Config::default();
            config.budget.work_credits = work;
            let _ = trace(&case, config);
        }
    }
}

#[test]
fn shared_control_branch_targets_and_frame_boundary() {
    let _ownership = Ownership::new();
    for case in cases().into_iter().filter(|case| {
        case.name.starts_with("loop")
            || case.name.starts_with("function")
            || case.name.starts_with("table")
            || case.name == "nested-function"
    }) {
        assert!(trace(&case, Config::default()).0.is_ok());
    }
}

#[test]
fn shared_control_work_and_fuel_prefixes() {
    let _ownership = Ownership::new();
    let mut fixtures = cases();
    fixtures.push(case(
        "unreachable",
        false,
        vec![2, 0x40, 0, 0x0b, 0x0b],
        None,
    ));
    for case in fixtures {
        let usage = trace(&case, Config::default()).1;
        for work in 0..=usage.work_used + 1 {
            let mut config = Config::default();
            config.budget.work_credits = work;
            let _ = trace(&case, config);
        }
        for fuel in 0..=usage.instructions + 1 {
            let mut config = Config::default();
            config.limits.fuel = fuel;
            let _ = trace(&case, config);
        }
    }
}

#[test]
fn shared_control_warm_dispatch_allocation_free() {
    let background = Background::new();
    let _ownership = Ownership::new();
    background.check_observer();
    for case in cases() {
        let token = Cancellation::default();
        let mut span = make(&case, Config::default(), &token);
        assert_eq!(span.invoke("run", &case.args).unwrap(), case.expected);
        let reservation = span.usage().state_reserved;
        let cache_reservation = span.cache_usage().peak_cache_reserved;
        let interval = begin(1, 0, &token);
        let result = span.invoke("run", &case.args);
        let baseline = interval.finish();
        let allocations = (
            CALLS.load(SeqCst),
            REALLOCATIONS.load(SeqCst),
            PEAK.load(SeqCst) - baseline,
        );
        assert_eq!(result.unwrap(), case.expected);
        assert_eq!(allocations, (0, 0, 0));
        assert_eq!(span.usage().state_reserved, reservation);
        assert_eq!(span.cache_usage().peak_cache_reserved, cache_reservation);
        clean(&span);
        println!(
            "control_warm {} usage={:?} cache={:?} allocations={allocations:?}",
            case.name,
            span.usage(),
            span.cache_usage()
        );
        // Decode allocations are cold-cache effects, outside the zero-allocation
        // claim. Refuse and cancel each actually observed allocation ordinal.
        let allocations = trace(&case, Config::default()).2;
        for ordinal in 1..=allocations {
            let before = LIVE.load(SeqCst);
            let config = Config {
                fail: ordinal,
                ..Config::default()
            };
            let failure = trace(&case, config).0.unwrap_err();
            assert_eq!(failure.kind, ExecutionFailureKind::Cache);
            assert_eq!(
                failure.cache_failure.unwrap().kind,
                CacheFailureKind::AllocationFailure
            );
            assert_eq!(LIVE.load(SeqCst), before);
            let config = Config {
                cancel_at: ordinal,
                ..Config::default()
            };
            let failure = trace(&case, config).0.unwrap_err();
            assert!(
                failure.kind == ExecutionFailureKind::Cancelled
                    || failure
                        .cache_failure
                        .is_some_and(|e| e.kind == CacheFailureKind::Cancelled)
            );
            assert_eq!(LIVE.load(SeqCst), before);
        }
    }
}

#[test]
fn shared_control_cancellation_and_limits() {
    let _ownership = Ownership::new();
    for case in cases() {
        let config = Config {
            cancelled: true,
            ..Config::default()
        };
        assert_eq!(
            trace(&case, config).0.unwrap_err().kind,
            ExecutionFailureKind::Cancelled
        );
    }
    let mut recursive = Spec::one(
        vec![Type::I32],
        Some(Type::I32),
        vec![
            0x20, 0, 0x45, 4, 0x7f, 0x41, 1, 5, 0x20, 0, 0x20, 0, 0x41, 1, 0x6b, 0x10, 0, 0x6c,
            0x0b, 0x0b,
        ],
    );
    recursive.functions[0].locals = vec![Type::I64];
    let recursive = Case {
        name: "recursive",
        bytes: recursive.bytes(),
        args: vec![Value::I32(4)],
        expected: Some(Value::I32(24)),
    };
    let usage = trace(&recursive, Config::default()).1;
    for (values, controls, expected) in [
        (usage.peak_live_values, usage.peak_live_controls, None),
        (
            usage.peak_live_values - 1,
            usage.peak_live_controls,
            Some(ExecutionFailureKind::ValueExhausted),
        ),
        (
            usage.peak_live_values,
            usage.peak_live_controls - 1,
            Some(ExecutionFailureKind::ControlExhausted),
        ),
    ] {
        let mut config = Config::default();
        config.budget.live_values = values;
        config.budget.live_controls = controls;
        let result = trace(&recursive, config).0;
        if let Some(kind) = expected {
            assert_eq!(result.unwrap_err().kind, kind);
        } else {
            assert!(result.is_ok());
        }
    }
    for (label, code) in [
        ("operand", "profile_operand_limit"),
        ("control", "profile_control_limit"),
    ] {
        let mut config = Config::default();
        if label == "operand" {
            config.limits.operand_stack = 1;
        } else {
            config.limits.control_depth = 1;
        }
        let token = Cancellation::default();
        let failure = validate_spans(
            &recursive.bytes,
            config.limits,
            ValidationBudget::default(),
            &token,
        )
        .err()
        .unwrap();
        assert_eq!(failure.code, code);
        println!("control_validation_ceiling {label} failure={failure:?}");
    }
    for (label, expected) in [
        ("frame", ExecutionFailureKind::CallDepthExceeded),
        ("pin", ExecutionFailureKind::Cache),
    ] {
        let mut config = Config::default();
        if label == "frame" {
            config.limits.call_depth = 2;
        } else {
            config.cache.max_pins = 2;
        }
        assert_eq!(trace(&recursive, config).0.unwrap_err().kind, expected);
    }
}
