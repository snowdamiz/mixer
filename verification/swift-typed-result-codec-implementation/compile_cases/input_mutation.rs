use super::diagnostic_result_v1::*;
fn mutate(input: &mut [u8]) -> usize {
    let view = decode_result_v1(input).unwrap();
    input.fill(0);
    view.encoded().len()
}
