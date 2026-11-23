use std::{fs::File, io::Read, time::Instant};

use mixer_vm::experimental_swift_reactor::{
    validate_swift_ui, validate_swift_ui_6_3_3, PersistentSwiftUIOwner, SwiftRunBudget,
    SwiftUICloseOutcome, SwiftValidationBudget,
};
use mixer_vm::experimental_wasi::{WasiBudget, WasiGrants};
use mixer_vm::Cancellation;

fn observe_close(outcome: SwiftUICloseOutcome) -> bool {
    match outcome {
        SwiftUICloseOutcome::Clean { usage, failure } => {
            eprintln!("clean={usage:?}; failure={failure:?}");
            failure.is_none()
        }
        frozen @ SwiftUICloseOutcome::Frozen { .. } => {
            std::mem::forget(frozen);
            eprintln!("Frozen UI owner. Preserve this run's scratch.");
            std::process::exit(74);
        }
    }
}

fn main() {
    let mut args = std::env::args_os().skip(1);
    let path = args.next().expect("Wasm reactor path");
    let profile = args.next().expect("validation profile");
    let suite = args.next().expect("replay suite");
    let events = match suite.to_str() {
        Some("standalone") => 1..=14,
        Some("screen") => 1..=13,
        Some("rollback") => 14..=14,
        Some("s2") => 15..=20,
        _ => panic!("unknown replay suite"),
    };
    let turns = events.clone().count() + 1;
    let validate = match profile.to_str() {
        Some("fixed34") => validate_swift_ui,
        Some("swift633") => validate_swift_ui_6_3_3,
        _ => panic!("unknown validation profile"),
    };
    assert!(args.next().is_none());

    let validation_budget = SwiftValidationBudget::default();
    let mut input = Vec::new();
    File::open(path)
        .expect("open reactor")
        .take(64 * 1024 * 1024 + 1)
        .read_to_end(&mut input)
        .expect("read reactor");
    assert!(input.len() <= 64 * 1024 * 1024);
    let cancellation = Cancellation::default();
    let now = Instant::now();
    let proof = match validate(&input, validation_budget, &cancellation) {
        Ok(proof) => proof,
        Err(error) => {
            eprintln!("validation={error:?}");
            std::process::exit(10);
        }
    };
    eprintln!(
        "policy={}; validation={:?}; validation_elapsed={:?}; validation_usage={:?}",
        proof.policy_identity(),
        proof.observations(),
        now.elapsed(),
        proof.usage()
    );
    drop(input);
    if profile == "fixed34" {
        return;
    }

    let budget = SwiftRunBudget {
        frames: 256,
        active_pins: 256,
        cache_entries: 256,
        ..SwiftRunBudget::default()
    };
    let grants = WasiGrants {
        secure_random: true,
        monotonic: true,
        ..WasiGrants::default()
    };
    let wasi_budget = WasiBudget::default();
    eprintln!("run_budget={budget:?}; wasi_budget={wasi_budget:?}");
    let now = Instant::now();
    let mut owner =
        match PersistentSwiftUIOwner::construct(proof, budget, grants, wasi_budget, cancellation) {
            Ok(owner) => owner,
            Err(error) => {
                eprintln!("construct={:?}", error.failure);
                observe_close(error.close);
                std::process::exit(20);
            }
        };
    eprintln!("construction_elapsed={:?}", now.elapsed());

    let mut frames = Vec::new();
    for step in std::iter::once(0).chain(events) {
        let now = Instant::now();
        let frame = if step == 0 {
            owner.initialize_and_start()
        } else {
            owner.event(&[step])
        };
        eprintln!(
            "step={step}; elapsed={:?}; usage={:?}",
            now.elapsed(),
            owner.usage()
        );
        match frame {
            Ok(frame) => frames.push(frame),
            Err(error) => {
                eprintln!("failure={error:?}");
                break;
            }
        }
    }

    let closed = observe_close(owner.consume());
    for frame in &frames {
        println!("{}", std::str::from_utf8(frame).expect("UTF-8 checkpoint"));
    }
    if !closed || frames.len() != turns {
        std::process::exit(20);
    }
}
