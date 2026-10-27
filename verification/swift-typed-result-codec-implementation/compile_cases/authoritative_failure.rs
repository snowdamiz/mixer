use super::diagnostic_result_v1::*;
fn forge(input: &[u8], mut original: super::control::SwiftRunFailure) -> super::control::SwiftRunFailure {
    original.code = decode_failure_scalar_v1(input).unwrap().code();
    original
}
