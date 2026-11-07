//! Original compact Wasm builder shared only by the new native-boundary tests.
fn u32leb(mut n: u32) -> Vec<u8> {
    let mut b = Vec::new();
    loop {
        let c = (n & 127) as u8;
        n >>= 7;
        b.push(c | if n == 0 { 0 } else { 128 });
        if n == 0 {
            return b;
        }
    }
}
fn section(m: &mut Vec<u8>, id: u8, payload: Vec<u8>) {
    m.push(id);
    m.extend(u32leb(payload.len() as u32));
    m.extend(payload);
}
fn name(n: &str) -> Vec<u8> {
    let mut b = u32leb(n.len() as u32);
    b.extend(n.as_bytes());
    b
}
pub(super) fn wasm() -> Vec<u8> {
    wasm_with_memory(1)
}
pub(super) fn wasm_with_memory(pages: u8) -> Vec<u8> {
    let mut m = b"\0asm\x01\0\0\0".to_vec();
    section(
        &mut m,
        1,
        vec![
            4, 0x60, 3, 0x7f, 0x7f, 0x7f, 1, 0x7f, 0x60, 1, 0x7e, 1, 0x7f, 0x60, 4, 0x7e, 0x7f,
            0x7f, 0x7f, 1, 0x7f, 0x60, 0, 0,
        ],
    );
    let mut imports = vec![3];
    for (i, n) in ["storage_get", "cancel", "poll"].iter().enumerate() {
        imports.extend(name("mixer.capability.v1"));
        imports.extend(name(n));
        imports.extend([0, i as u8]);
    }
    section(&mut m, 2, imports);
    section(&mut m, 3, vec![3, 3, 3, 3]);
    section(&mut m, 5, vec![1, 1, pages, pages]);
    let mut exports = vec![6];
    for (i, n) in [
        "get",
        "cancel",
        "poll",
        "start",
        "mixer_guest_capability_ready_v1",
        "trap",
    ]
    .iter()
    .enumerate()
    {
        exports.extend(name(n));
        exports.extend([0, i as u8]);
    }
    section(&mut m, 7, exports);
    section(&mut m, 10, vec![3, 2, 0, 0x0b, 2, 0, 0x0b, 3, 0, 0, 0x0b]);
    let mut data = vec![1, 0, 0x41, 0, 0x0b, 4];
    data.extend(b"args");
    section(&mut m, 11, data);
    m
}
