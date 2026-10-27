#![cfg(feature = "experimental-swift-reactor")]
#![allow(dead_code)]
//! Original small modules with the complete public fixed structural ABI.
use crate::experimental_wasi::WasiFunction;
use crate::Type;

pub fn uint(mut value: u32) -> Vec<u8> {
    let mut bytes = Vec::new();
    loop {
        let mut byte = (value & 127) as u8;
        value >>= 7;
        if value != 0 {
            byte |= 128;
        }
        bytes.push(byte);
        if value == 0 {
            return bytes;
        }
    }
}
pub fn section(module: &mut Vec<u8>, id: u8, payload: Vec<u8>) {
    module.push(id);
    module.extend(uint(payload.len() as u32));
    module.extend(payload);
}
pub fn name(value: &[u8]) -> Vec<u8> {
    let mut bytes = uint(value.len() as u32);
    bytes.extend(value);
    bytes
}
pub fn type_byte(ty: Type) -> u8 {
    match ty {
        Type::I32 => 0x7f,
        Type::I64 => 0x7e,
        Type::F32 => 0x7d,
        Type::F64 => 0x7c,
    }
}
pub fn signature(params: &[Type], result: &[Type]) -> Vec<u8> {
    let mut bytes = vec![0x60];
    bytes.extend(uint(params.len() as u32));
    bytes.extend(params.iter().copied().map(type_byte));
    bytes.extend(uint(result.len() as u32));
    bytes.extend(result.iter().copied().map(type_byte));
    bytes
}
pub struct Fixture {
    pub types: Vec<Vec<u8>>,
    pub imports: Vec<(Vec<u8>, Vec<u8>, u8, u32)>,
    pub function_types: Vec<u32>,
    pub bodies: Vec<Vec<u8>>,
    pub memory: Vec<u8>,
    pub table: Vec<u8>,
    pub globals: Vec<Vec<u8>>,
    pub exports: Vec<(Vec<u8>, u8, u32)>,
    pub elements: Vec<Vec<u8>>,
    pub data: Vec<Vec<u8>>,
    pub custom_name: Option<Vec<u8>>,
    pub custom_payload: Vec<u8>,
    pub start: Option<u32>,
}
impl Default for Fixture {
    fn default() -> Self {
        let types = WasiFunction::ALL
            .into_iter()
            .map(|f| signature(f.parameters(), f.results()))
            .chain([signature(&[], &[]), signature(&[], &[Type::I32])])
            .collect();
        let imports = WasiFunction::ALL
            .into_iter()
            .enumerate()
            .map(|(i, f)| {
                (
                    b"wasi_snapshot_preview1".to_vec(),
                    f.name().to_vec(),
                    0,
                    i as u32,
                )
            })
            .collect();
        let mut bodies = vec![vec![0, 0x0b]; 29];
        bodies[28] = vec![0, 0x41, 0, 0x0b];
        let mut function_types = vec![34; 29];
        function_types[28] = 35;
        let mut memory = vec![1, 0]; // one memory, absent maximum
        memory.extend(uint(584));
        let mut table = vec![1, 0x70, 1]; // one funcref table, declared fixed range
        table.extend(uint(46_713));
        table.extend(uint(46_713));
        Self {
            types,
            imports,
            function_types,
            bodies,
            memory,
            table,
            globals: vec![],
            exports: vec![
                (b"memory".to_vec(), 2, 0),
                (b"_initialize".to_vec(), 0, 35),
                (b"mixer_fieldlog_corpus_v1".to_vec(), 0, 62),
            ],
            elements: vec![],
            data: vec![],
            custom_name: None,
            custom_payload: vec![],
            start: None,
        }
    }
}
impl Fixture {
    pub fn bytes(&self) -> Vec<u8> {
        let mut module = b"\0asm\x01\0\0\0".to_vec();
        if let Some(custom) = &self.custom_name {
            let mut payload = name(custom);
            payload.extend(&self.custom_payload);
            section(&mut module, 0, payload);
        }
        let mut types = uint(self.types.len() as u32);
        for ty in &self.types {
            types.extend(ty);
        }
        section(&mut module, 1, types);
        let mut imports = uint(self.imports.len() as u32);
        for (namespace, field, kind, index) in &self.imports {
            imports.extend(name(namespace));
            imports.extend(name(field));
            imports.push(*kind);
            imports.extend(uint(*index));
        }
        section(&mut module, 2, imports);
        let mut functions = uint(self.function_types.len() as u32);
        for ty in &self.function_types {
            functions.extend(uint(*ty));
        }
        section(&mut module, 3, functions);
        section(&mut module, 4, self.table.clone());
        section(&mut module, 5, self.memory.clone());
        if !self.globals.is_empty() {
            let mut globals = uint(self.globals.len() as u32);
            for global in &self.globals {
                globals.extend(global);
            }
            section(&mut module, 6, globals);
        }
        let mut exports = uint(self.exports.len() as u32);
        for (field, kind, index) in &self.exports {
            exports.extend(name(field));
            exports.push(*kind);
            exports.extend(uint(*index));
        }
        section(&mut module, 7, exports);
        if let Some(function) = self.start {
            section(&mut module, 8, uint(function));
        }
        if !self.elements.is_empty() {
            let mut elements = uint(self.elements.len() as u32);
            for element in &self.elements {
                elements.extend(element);
            }
            section(&mut module, 9, elements);
        }
        let mut code = uint(self.bodies.len() as u32);
        for body in &self.bodies {
            code.extend(uint(body.len() as u32));
            code.extend(body);
        }
        section(&mut module, 10, code);
        if !self.data.is_empty() {
            let mut data = uint(self.data.len() as u32);
            for segment in &self.data {
                data.extend(segment);
            }
            section(&mut module, 11, data);
        }
        module
    }
    pub fn block_body(nested: usize) -> Vec<u8> {
        let mut body = vec![0];
        for _ in 0..nested {
            body.extend([2, 0x40]);
        }
        body.extend(vec![0x0b; nested + 1]);
        body
    }
    pub fn operand_body(values: usize) -> Vec<u8> {
        let mut body = vec![0];
        for _ in 0..values {
            body.extend([0x41, 0]);
        }
        body.extend(vec![0x1a; values]);
        body.push(0x0b);
        body
    }
}
pub fn data_segment(offset: i32, payload: &[u8]) -> Vec<u8> {
    let mut data = vec![0, 0x41];
    data.extend(signed(offset));
    data.push(0x0b);
    data.extend(uint(payload.len() as u32));
    data.extend(payload);
    data
}
pub fn element_segment(offset: i32, functions: &[u32]) -> Vec<u8> {
    let mut data = vec![0, 0x41];
    data.extend(signed(offset));
    data.push(0x0b);
    data.extend(uint(functions.len() as u32));
    for function in functions {
        data.extend(uint(*function));
    }
    data
}
pub fn signed(mut value: i32) -> Vec<u8> {
    let mut bytes = Vec::new();
    loop {
        let byte = (value & 127) as u8;
        value >>= 7;
        let done = (value == 0 && byte & 64 == 0) || (value == -1 && byte & 64 != 0);
        bytes.push(if done { byte } else { byte | 128 });
        if done {
            return bytes;
        }
    }
}
