//! Independently authored, deterministic Wasm binary encoding for guest-UI tests.
//! Based on the core Wasm binary format; no runtime/other fixture builder is used.
pub const NAMES: [&str; 3] = [
    "mixer_guest_ui_start_v1",
    "mixer_guest_ui_event_v1",
    "mixer_guest_capability_ready_v1",
];
pub struct Program {
    pub functions: Vec<(u8, Vec<u8>)>,
    pub exports: Vec<(String, u8, u32)>,
    pub memory: Option<Vec<u8>>,
    pub unknown_import: bool,
    pub start_section: bool,
}
impl Default for Program {
    fn default() -> Self {
        Self {
            functions: vec![
                (0, vec![0, 0x41, 0, 0x0b]),
                (1, vec![0, 0x20, 0, 0x0b]),
                (2, vec![0, 0x0b]),
            ],
            // Two unused approved imports precede the defined functions.
            exports: NAMES
                .iter()
                .enumerate()
                .map(|(i, n)| (n.to_string(), 0, i as u32 + 2))
                .collect(),
            memory: Some(vec![1, 1, 1, 1]),
            unknown_import: false,
            start_section: false,
        }
    }
}
fn leb(mut n: u32, out: &mut Vec<u8>) {
    loop {
        let byte = (n & 127) as u8;
        n >>= 7;
        out.push(byte | if n == 0 { 0 } else { 128 });
        if n == 0 {
            break;
        }
    }
}
fn name(s: &str, out: &mut Vec<u8>) {
    leb(s.len() as u32, out);
    out.extend(s.as_bytes());
}
fn section(id: u8, data: Vec<u8>, out: &mut Vec<u8>) {
    out.push(id);
    leb(data.len() as u32, out);
    out.extend(data);
}
impl Program {
    pub fn bytes(&self) -> Vec<u8> {
        let mut out = b"\0asm\x01\0\0\0".to_vec();
        section(
            1,
            vec![
                7, 0x60, 0, 1, 0x7f, // 0: () -> i32
                0x60, 1, 0x7f, 1, 0x7f, // 1: (i32) -> i32
                0x60, 0, 0, // 2: () -> ()
                0x60, 0, 1, 0x7e, // 3: () -> i64
                0x60, 1, 0x7e, 1, 0x7f, // 4: (i64) -> i32
                0x60, 1, 0x7f, 0, // 5: (i32) -> ()
                0x60, 3, 0x7f, 0x7f, 0x7f, 1, 0x7f, // 6: storage_get
            ],
            &mut out,
        );
        let mut imports = vec![2];
        name("mixer", &mut imports);
        name("checkpoint", &mut imports);
        imports.extend([0, 2]);
        name("mixer.capability.v1", &mut imports);
        name(
            if self.unknown_import {
                "unknown"
            } else {
                "storage_get"
            },
            &mut imports,
        );
        imports.extend([0, 6]);
        section(2, imports, &mut out);
        let mut functions = Vec::new();
        leb(self.functions.len() as u32, &mut functions);
        functions.extend(self.functions.iter().map(|(t, _)| *t));
        section(3, functions, &mut out);
        if let Some(memory) = &self.memory {
            section(5, memory.clone(), &mut out);
        }
        let mut exports = Vec::new();
        leb(self.exports.len() as u32, &mut exports);
        for (label, kind, index) in &self.exports {
            name(label, &mut exports);
            exports.push(*kind);
            leb(*index, &mut exports);
        }
        section(7, exports, &mut out);
        if self.start_section {
            section(8, vec![4], &mut out);
        }
        let mut code = Vec::new();
        leb(self.functions.len() as u32, &mut code);
        for (_, body) in &self.functions {
            leb(body.len() as u32, &mut code);
            code.extend(body);
        }
        section(10, code, &mut out);
        out
    }
}
