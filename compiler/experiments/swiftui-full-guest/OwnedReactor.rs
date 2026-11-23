use std::{fs::File, io::{self, Read, Write}, path::Path, time::{Duration, Instant}};

use mixer_vm::experimental_swift_reactor::{
    validate_swift_ui, validate_swift_ui_6_3_3, PersistentSwiftUIOwner, SwiftRunBudget, SwiftUICloseOutcome,
    SwiftValidationBudget,
};
use mixer_vm::experimental_wasi::{WasiBudget, WasiGrants};
use mixer_vm::Cancellation;

#[cfg(not(all(target_os = "ios", target_abi = "sim")))]
fn main() {
    let mut args = std::env::args_os().skip(1);
    let path = args.next().expect("Wasm reactor path");
    let profile = args.next();
    assert!(args.next().is_none());
    let status = replay(
        Path::new(&path),
        profile.as_ref().map(|value| value.to_str().expect("UTF-8 profile")),
        |_, _| {},
    );
    std::process::exit(status);
}

fn replay(path: &Path, profile: Option<&str>, milestone: impl Fn(&str, Duration)) -> i32 {
    let mut budget = SwiftRunBudget::default();
    let validate = match profile {
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
    let read_started = Instant::now();
    let mut input = Vec::new();
    let validation_budget = SwiftValidationBudget::default();
    let max_bytes = validation_budget.source_bytes;
    if let Err(error) = File::open(path).and_then(|file| {
        file.take(max_bytes as u64 + 1).read_to_end(&mut input)
    }) {
        eprintln!("read={error}");
        return 11;
    }
    if input.len() > max_bytes {
        eprintln!("read=source byte limit");
        return 11;
    }
    milestone("read", read_started.elapsed());
    let cancellation = Cancellation::default();
    let validation_started = Instant::now();
    let validation = validate(&input, validation_budget, &cancellation);
    let validation_elapsed = validation_started.elapsed();
    match &validation {
        Ok(_) => milestone("validate", validation_elapsed),
        Err(_) => milestone("validation_refused", validation_elapsed),
    }
    let proof = match validation {
        Ok(proof) => proof,
        Err(error) => {
            eprintln!("validation={error:?}");
            return 10;
        }
    };
    eprintln!(
        "policy={}; validation={:?}; validation_elapsed={:?}; validation_usage={:?}",
        proof.policy_identity(),
        proof.observations(),
        validation_elapsed,
        proof.usage(),
    );
    drop(input);

    eprintln!("run_budget={budget:?}; wasi_budget={:?}", WasiBudget::default());
    let construction_started = Instant::now();
    let construction = PersistentSwiftUIOwner::construct(
        proof,
        budget,
        WasiGrants { secure_random: true, monotonic: true, ..WasiGrants::default() },
        WasiBudget::default(),
        cancellation,
    );
    let construction_elapsed = construction_started.elapsed();
    milestone("construct", construction_elapsed);
    let mut owner = match construction {
        Ok(owner) => owner,
        Err(error) => {
            eprintln!("construct={:?}", error.failure);
            return close_status(error.close, false);
        }
    };
    eprintln!("construction_elapsed={construction_elapsed:?}; usage={:?}", owner.usage());

    const TURNS: [&str; 6] = ["first_snapshot", "load", "open", "blank_save", "save", "reopen"];
    let mut succeeded = true;
    for (step, label) in TURNS.iter().enumerate() {
        let started = Instant::now();
        let frame = if step == 0 {
            owner.initialize_and_start()
        } else {
            owner.event(&[step as u8])
        };
        let elapsed = started.elapsed();
        milestone(label, elapsed);
        eprintln!("step={step}; elapsed={elapsed:?}; usage={:?}", owner.usage());
        match frame {
            Ok(frame) => {
                let output = std::str::from_utf8(&frame).ok().is_some_and(|frame| {
                    let mut stream = io::stdout().lock();
                    writeln!(stream, "{frame}").and_then(|_| stream.flush()).is_ok()
                });
                if !output {
                    eprintln!("failure=invalid UTF-8 or snapshot output failure");
                    succeeded = false;
                    break;
                }
            }
            Err(error) => {
                eprintln!("failure={error:?}");
                succeeded = false;
                break;
            }
        }
    }

    #[cfg(all(target_os = "ios", target_abi = "sim"))]
    if succeeded {
        // Sample with the populated owner and its caches retained.
        std::thread::sleep(Duration::from_secs(1));
        milestone("steady", Duration::ZERO);
    }

    let started = Instant::now();
    let close = owner.consume();
    milestone("consume", started.elapsed());
    close_status(close, succeeded)
}

fn close_status(close: SwiftUICloseOutcome, succeeded: bool) -> i32 {
    match close {
        SwiftUICloseOutcome::Clean { usage, failure } => {
            eprintln!("clean={usage:?}; failure={failure:?}");
            if succeeded && failure.is_none() { 0 } else { 20 }
        }
        frozen @ SwiftUICloseOutcome::Frozen { usage, failure, .. } => {
            // The caller exits immediately. Do not try to drop a frozen owner.
            std::mem::forget(frozen);
            eprintln!("frozen={usage:?}; failure={failure:?}");
            74
        }
    }
}

#[cfg(all(target_os = "ios", target_abi = "sim"))]
mod ios_simulator {
    use super::*;
    use std::{ffi::{c_char, CStr, OsStr}, os::unix::ffi::OsStrExt};

    extern "C" {
        fn mixer_s2a_checkpoint(stage: *const u8, stage_len: usize, elapsed_micros: u64);
    }

    // The simulator app passes the NUL-terminated path of its bundled fixture.
    #[no_mangle]
    unsafe extern "C" fn mixer_s2a_replay(path: *const c_char, fixed34: bool) -> i32 {
        let path = Path::new(OsStr::from_bytes(CStr::from_ptr(path).to_bytes()));
        let profile = (!fixed34).then_some("--swift-6.3.3-ui256");
        replay(path, profile, |stage, elapsed| unsafe {
            mixer_s2a_checkpoint(stage.as_ptr(), stage.len(), elapsed.as_micros() as u64);
        })
    }
}
