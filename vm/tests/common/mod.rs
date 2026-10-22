#![allow(dead_code)]
use mixer_vm::{Type, Value};
pub fn u32leb(mut n: u32) -> Vec<u8> {
    let mut b = vec![];
    loop {
        let x = (n & 127) as u8;
        n >>= 7;
        b.push(x | if n != 0 { 128 } else { 0 });
        if n == 0 {
            return b;
        }
    }
}
pub fn signed(mut n: i64) -> Vec<u8> {
    let mut b = vec![];
    loop {
        let x = (n & 127) as u8;
        n >>= 7;
        let done = (n == 0 && x & 64 == 0) || (n == -1 && x & 64 != 0);
        b.push(x | if done { 0 } else { 128 });
        if done {
            return b;
        }
    }
}
pub fn section(m: &mut Vec<u8>, id: u8, b: Vec<u8>) {
    m.push(id);
    m.extend(u32leb(b.len() as u32));
    m.extend(b);
}
fn name(s: &str) -> Vec<u8> {
    let mut b = u32leb(s.len() as u32);
    b.extend_from_slice(s.as_bytes());
    b
}
fn typebyte(t: Type) -> u8 {
    match t {
        Type::I32 => 0x7f,
        Type::I64 => 0x7e,
        Type::F32 => 0x7d,
        Type::F64 => 0x7c,
    }
}
fn signature(p: &[Type], r: Option<Type>) -> Vec<u8> {
    let mut b = vec![0x60];
    b.extend(u32leb(p.len() as u32));
    b.extend(p.iter().map(|t| typebyte(*t)));
    b.push(r.is_some() as u8);
    b.extend(r.map(typebyte));
    b
}
pub fn constant(v: Value) -> Vec<u8> {
    let mut b = vec![];
    match v {
        Value::I32(x) => {
            b.push(0x41);
            b.extend(signed(x as i64));
        }
        Value::I64(x) => {
            b.push(0x42);
            b.extend(signed(x));
        }
        Value::F32(x) => {
            b.push(0x43);
            b.extend(x.to_le_bytes());
        }
        Value::F64(x) => {
            b.push(0x44);
            b.extend(x.to_le_bytes());
        }
    }
    b
}
#[derive(Clone)]
pub struct Function {
    pub params: Vec<Type>,
    pub result: Option<Type>,
    pub locals: Vec<Type>,
    pub code: Vec<u8>,
}
impl Function {
    pub fn new(params: Vec<Type>, result: Option<Type>, code: Vec<u8>) -> Self {
        Self {
            params,
            result,
            locals: vec![],
            code,
        }
    }
}
#[derive(Default)]
pub struct Spec {
    pub functions: Vec<Function>,
    pub imports: Vec<(String, Vec<Type>, Option<Type>)>,
    pub memory: Option<(u32, u32)>,
    pub table: Option<(u32, u32)>,
    pub elements: Vec<(u32, Vec<u32>)>,
    pub explicit_elements: bool,
    pub export_memory: bool,
    pub export_table: bool,
    pub globals: Vec<(Value, bool)>,
    pub data: Vec<(u32, Vec<u8>)>,
}
impl Spec {
    pub fn one(params: Vec<Type>, result: Option<Type>, code: Vec<u8>) -> Self {
        Self {
            functions: vec![Function::new(params, result, code)],
            ..Default::default()
        }
    }
    pub fn bytes(&self) -> Vec<u8> {
        let mut m = b"\0asm\x01\0\0\0".to_vec();
        let mut types = u32leb((self.imports.len() + self.functions.len()) as u32);
        for (_, p, r) in &self.imports {
            types.extend(signature(p, *r));
        }
        for f in &self.functions {
            types.extend(signature(&f.params, f.result));
        }
        section(&mut m, 1, types);
        if !self.imports.is_empty() {
            let mut b = u32leb(self.imports.len() as u32);
            for (i, (n, _, _)) in self.imports.iter().enumerate() {
                b.extend(name("mixer"));
                b.extend(name(n));
                b.push(0);
                b.extend(u32leb(i as u32));
            }
            section(&mut m, 2, b);
        }
        let mut f = u32leb(self.functions.len() as u32);
        for i in 0..self.functions.len() {
            f.extend(u32leb((self.imports.len() + i) as u32));
        }
        section(&mut m, 3, f);
        if let Some((min, max)) = self.table {
            let mut b = vec![1, 0x70, 1];
            b.extend(u32leb(min));
            b.extend(u32leb(max));
            section(&mut m, 4, b);
        }
        if let Some((min, max)) = self.memory {
            let mut b = vec![1, 1];
            b.extend(u32leb(min));
            b.extend(u32leb(max));
            section(&mut m, 5, b);
        }
        if !self.globals.is_empty() {
            let mut b = u32leb(self.globals.len() as u32);
            for (v, mutable) in &self.globals {
                b.push(typebyte(v.ty()));
                b.push(*mutable as u8);
                b.extend(constant(*v));
                b.push(0x0b);
            }
            section(&mut m, 6, b);
        }
        let mut e = u32leb(
            (self.functions.len()
                + usize::from(self.export_memory)
                + usize::from(self.export_table)) as u32,
        );
        for i in 0..self.functions.len() {
            let export = if i == 0 {
                "run".to_owned()
            } else {
                format!("other{i}")
            };
            e.extend(name(&export));
            e.push(0);
            e.extend(u32leb((self.imports.len() + i) as u32));
        }
        if self.export_memory {
            e.extend(name("memory"));
            e.extend([2, 0]);
        }
        if self.export_table {
            e.extend(name("table"));
            e.extend([1, 0]);
        }
        section(&mut m, 7, e);
        if !self.elements.is_empty() {
            let mut b = u32leb(self.elements.len() as u32);
            for (offset, functions) in &self.elements {
                b.push(if self.explicit_elements { 2 } else { 0 });
                if self.explicit_elements {
                    b.push(0);
                }
                b.extend(constant(Value::I32(*offset as i32)));
                b.push(0x0b);
                if self.explicit_elements {
                    b.push(0);
                }
                b.extend(u32leb(functions.len() as u32));
                for function in functions {
                    b.extend(u32leb(*function));
                }
            }
            section(&mut m, 9, b);
        }
        let mut c = u32leb(self.functions.len() as u32);
        for f in &self.functions {
            let mut b = u32leb(f.locals.len() as u32);
            for t in &f.locals {
                b.push(1);
                b.push(typebyte(*t));
            }
            b.extend_from_slice(&f.code);
            c.extend(u32leb(b.len() as u32));
            c.extend(b);
        }
        section(&mut m, 10, c);
        if !self.data.is_empty() {
            let mut b = u32leb(self.data.len() as u32);
            for (off, data) in &self.data {
                b.push(0);
                b.extend(constant(Value::I32(*off as i32)));
                b.push(0x0b);
                b.extend(u32leb(data.len() as u32));
                b.extend(data);
            }
            section(&mut m, 11, b);
        }
        m
    }
}
pub fn single(code: Vec<u8>, result: Option<Type>) -> Vec<u8> {
    Spec::one(vec![], result, code).bytes()
}
