use super::diagnostic_result_v1::*;
fn escape(input: &[u8]) -> &'static str {
    decode_result_v1(input).unwrap().failure_scalars().unwrap().code()
}
