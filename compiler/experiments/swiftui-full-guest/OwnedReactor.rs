use std::{fs::File, io::Read, time::Instant};

use mixer_vm::experimental_swift_reactor::{
    validate_swift_ui, validate_swift_ui_6_3_3, PersistentSwiftUIOwner, SwiftRunBudget, SwiftUICloseOutcome,
    SwiftValidationBudget,
};
use mixer_vm::experimental_wasi::{WasiBudget, WasiGrants};
use mixer_vm::Cancellation;

fn main() {
    let mut args = std::env::args_os().skip(1);
    let path = args.next().expect("Wasm reactor path");
    let profile = args.next();
    let mut budget = SwiftRunBudget::default();
    let validate = match profile.as_ref().map(|value| value.to_str().expect("UTF-8 profile")) {
        None => validate_swift_ui,
        Some("--swift-6.3.3") => validate_swift_ui_6_3_3,
        Some("--swift-6.3.3-ui256") => {
            budget.frames = 256;
            budget.cache_entries = 256;
            budget.active_pins = 256;
            validate_swift_ui_6_3_3
        }
        Some(_) => panic!("unknown profile"),
    };
    assert!(args.next().is_none());
    let mut input = Vec::new();
    File::open(path)
        .expect("open reactor")
        .take(64 * 1024 * 1024 + 1)
        .read_to_end(&mut input)
        .expect("read reactor");
    assert!(input.len() <= 64 * 1024 * 1024);
    let cancellation = Cancellation::default();
    let validation_started = Instant::now();
    let proof = match validate(&input, SwiftValidationBudget::default(), &cancellation) {
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
        validation_started.elapsed(),
        proof.usage(),
    );
    drop(input);

    eprintln!("run_budget={budget:?}; wasi_budget={:?}", WasiBudget::default());
    let construction_started = Instant::now();
    let mut owner = match PersistentSwiftUIOwner::construct(
        proof,
        budget,
        WasiGrants { secure_random: true, monotonic: true, ..WasiGrants::default() },
        WasiBudget::default(),
        cancellation,
    ) {
        Ok(owner) => owner,
        Err(error) => {
            eprintln!("construct={:?}", error.failure);
            match error.close {
                SwiftUICloseOutcome::Clean { usage, .. } => eprintln!("clean={usage:?}"),
                SwiftUICloseOutcome::Frozen { .. } => std::process::exit(74),
            }
            std::process::exit(20);
        }
    };
    eprintln!("construction_elapsed={:?}; usage={:?}", construction_started.elapsed(), owner.usage());

    let mut succeeded = true;
    for step in 0..=5 {
        let started = Instant::now();
        let frame = if step == 0 {
            owner.initialize_and_start()
        } else {
            owner.event(&[step])
        };
        eprintln!("step={step}; elapsed={:?}; usage={:?}", started.elapsed(), owner.usage());
        match frame {
            Ok(frame) => println!("{}", String::from_utf8(frame).expect("UTF-8 spike frame")),
            Err(error) => {
                eprintln!("failure={error:?}");
                succeeded = false;
                break;
            }
        }
    }

    match owner.consume() {
        SwiftUICloseOutcome::Clean { usage, failure } => {
            eprintln!("clean={usage:?}; failure={failure:?}");
            if !succeeded || failure.is_some() {
                std::process::exit(20);
            }
        }
        SwiftUICloseOutcome::Frozen { .. } => std::process::exit(74),
    }
}
