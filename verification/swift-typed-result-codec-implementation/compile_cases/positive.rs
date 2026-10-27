use super::diagnostic_result_v1::*;
fn borrowed_view_and_code<'a>(input: &'a [u8]) -> (UnverifiedResultViewV1<'a>, &'a str) {
    let view = decode_result_v1(input).unwrap();
    let code = view.failure_scalars().unwrap().code();
    (view, code)
}
fn caller_retains_original(f: &super::control::SwiftRunFailure, output: &mut [u8]) -> (&'static str, bool) {
    let result = encode_failure_scalar_v1(f, output);
    (f.code, result.is_ok())
}
