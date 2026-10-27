use super::diagnostic_result_v1::*;
fn escape(input: &[u8]) -> UnverifiedResultViewV1<'static> {
    decode_result_v1(input).unwrap()
}
