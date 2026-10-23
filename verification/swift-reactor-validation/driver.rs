//! Explicit local qualification driver. It never instantiates or executes Wasm.
use mixer_vm::experimental_swift_reactor::{validate_swift_reactor, SwiftValidationBudget};
use mixer_vm::Cancellation;
use std::io::Write;
use std::process::{Command, Stdio};

fn main() {
    let path = std::env::args_os().nth(1).expect("artifact path required");
    let input = std::fs::read(path).expect("read retained artifact");
    let length = input.len();
    let capacity = input.capacity();
    assert_eq!(length, 53_777_114, "exact target length");
    // Hash the actual retained immutable allocation passed to validation. A file
    // hash performed before a second read would not bind these bytes.
    let mut hash = Command::new("/usr/bin/shasum")
        .args(["-a", "256"])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .spawn()
        .expect("shasum");
    hash.stdin
        .take()
        .unwrap()
        .write_all(&input)
        .expect("hash immutable input");
    let hash = hash.wait_with_output().expect("hash result");
    assert!(hash.status.success());
    assert_eq!(
        std::str::from_utf8(&hash.stdout)
            .unwrap()
            .split_whitespace()
            .next(),
        Some("24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994")
    );
    let result = validate_swift_reactor(
        &input,
        SwiftValidationBudget::default(),
        &Cancellation::default(),
    );
    match result {
        Ok(proof) => {
            assert_eq!(
                proof.source(),
                input.as_slice(),
                "proof retained the hashed input"
            );
            let usage = proof.usage();
            let o = proof.observations();
            let overlap = capacity.checked_add(usage.total_peak_reserved).unwrap();
            // Keep the real external allocation alive through validation and
            // byte equality. Capacity overlap is not allocator overhead or RSS.
            drop(input);
            assert_eq!(o.defined_functions, 79_832);
            assert_eq!(o.validated_bodies, 79_832);
            for absolute in [24_208, 24_280, 33_106, 33_107, 53_196, 68_133] {
                assert!(proof.function_body(absolute - 34).is_some());
            }
            println!("{{\"valid\":true,\"executed\":false,\"policy\":\"{}\",\"validator_revision\":{},\"input_length\":{},\"input_capacity\":{},\"runner_input_internal_reservation_peak_overlap\":{},\"source_reserved\":{},\"metadata_reserved\":{},\"metadata_peak_reserved\":{},\"scratch_peak_reserved\":{},\"internal_total_peak_reserved\":{},\"work_used\":{},\"elapsed_micros\":{},\"deadline_ms\":{},\"types\":{},\"type_parameters\":{},\"imports\":{},\"defined_functions\":{},\"validated_bodies\":{},\"instructions\":{},\"globals\":{},\"data_segments\":{},\"element_segments\":{},\"max_parameters_plus_locals\":{},\"max_operand_values\":{},\"max_control_depth\":{},\"previously_rejected_absolute_functions_fully_validated\":[24208,24280,33106,33107,53196,68133],\"rss_measured\":false}}",
                proof.policy_identity(), proof_revision(), length, capacity, overlap,
                usage.source_bytes, usage.metadata_reserved, usage.metadata_peak_reserved,
                usage.scratch_peak_reserved, usage.total_peak_reserved, usage.work_used,
                usage.elapsed_micros, usage.deadline_ms, o.types, o.type_parameters,
                o.imported_functions, o.defined_functions, o.validated_bodies, o.instructions,
                o.globals, o.data_segments, o.element_segments, o.max_parameters_plus_locals,
                o.max_operand_values, o.max_control_depth);
        }
        Err(e) => {
            let overlap = capacity.checked_add(e.usage.total_peak_reserved).unwrap();
            drop(input);
            let function = e
                .function
                .map(|f| f.to_string())
                .unwrap_or_else(|| "null".to_owned());
            println!("{{\"valid\":false,\"executed\":false,\"failure_kind\":\"{:?}\",\"failure_code\":\"{}\",\"resource\":\"{:?}\",\"function\":{},\"absolute_offset\":{},\"attempted\":{},\"limit\":{},\"input_length\":{},\"input_capacity\":{},\"runner_input_internal_reservation_peak_overlap\":{},\"source_reserved\":{},\"metadata_reserved\":{},\"metadata_peak_reserved\":{},\"scratch_peak_reserved\":{},\"internal_total_peak_reserved\":{},\"work_used\":{},\"elapsed_micros\":{},\"deadline_ms\":{}}}",
                e.kind,e.code,e.resource,function,e.offset,e.attempted,e.limit,length,capacity,overlap,
                e.usage.source_bytes,e.usage.metadata_reserved,e.usage.metadata_peak_reserved,e.usage.scratch_peak_reserved,
                e.usage.total_peak_reserved,e.usage.work_used,e.usage.elapsed_micros,e.usage.deadline_ms);
            std::process::exit(1);
        }
    }
}
fn proof_revision() -> u32 {
    mixer_vm::experimental_swift_reactor::ValidatedSwiftReactor::VALIDATOR_REVISION
}
