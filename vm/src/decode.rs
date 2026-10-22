use crate::*;
use std::collections::{BTreeMap, BTreeSet};

#[derive(Clone, Debug, Default)]
pub struct Inventory {
    pub profile: Profile,
    pub imports: Vec<(String, String, u32)>,
    pub exports: Vec<(String, u8, u32)>,
    pub opcodes: BTreeMap<u8, usize>,
    pub complete: bool,
    pub extended_opcodes: BTreeMap<String, usize>,
    pub inventory_error: Option<Error>,
    pub error: Option<Error>,
}
impl Inventory {
    pub fn json(&self) -> String {
        let imports = self
            .imports
            .iter()
            .map(|(m, n, t)| {
                format!(
                    "{{\"module\":{},\"name\":{},\"type_index\":{t}}}",
                    json_string(m),
                    json_string(n)
                )
            })
            .collect::<Vec<_>>()
            .join(",");
        let exports = self
            .exports
            .iter()
            .map(|(n, k, i)| format!("{{\"name\":{},\"kind\":{k},\"index\":{i}}}", json_string(n)))
            .collect::<Vec<_>>()
            .join(",");
        let ops = self
            .opcodes
            .iter()
            .map(|(o, c)| format!("{{\"opcode\":\"0x{o:02x}\",\"count\":{c}}}"))
            .collect::<Vec<_>>()
            .join(",");
        let extended = self
            .extended_opcodes
            .iter()
            .map(|(o, c)| format!("{{\"opcode\":{},\"count\":{c}}}", json_string(o)))
            .collect::<Vec<_>>()
            .join(",");
        format!("{{\"profile\":{},\"valid\":{},\"inventory_complete\":{},\"imports\":[{imports}],\"exports\":[{exports}],\"opcodes\":[{ops}],\"extended_opcodes\":[{extended}],\"error\":{},\"inventory_error\":{}}}",json_string(self.profile.name()),self.error.is_none(),self.complete,self.error.as_ref().map(Error::json).unwrap_or_else(||"null".into()),self.inventory_error.as_ref().map(Error::json).unwrap_or_else(||"null".into()))
    }
}
#[derive(Clone, Debug)]
pub struct Module {
    pub(crate) source_bytes: usize,
    pub(crate) profile: Profile,
    pub(crate) types: Vec<Signature>,
    pub(crate) imports: Vec<Import>,
    pub(crate) functions: Vec<Function>,
    pub(crate) globals: Vec<Global>,
    pub(crate) exports: BTreeMap<String, (u8, u32)>,
    pub(crate) memory: Option<(u32, u32)>,
    pub(crate) data: Vec<(u32, Vec<u8>)>,
    pub inventory: Inventory,
}
impl Module {
    pub fn decode(bytes: &[u8], limits: &Limits) -> Result<Self, Error> {
        let mut inv = Inventory {
            profile: limits.profile,
            ..Inventory::default()
        };
        parse(bytes, limits, &mut inv)
    }
    pub fn function_count(&self) -> usize {
        self.imports.len() + self.functions.len()
    }
    pub fn exports(&self) -> Vec<String> {
        self.exports.keys().cloned().collect()
    }
    pub(crate) fn signature(&self, index: u32) -> Option<&Signature> {
        let ty = if (index as usize) < self.imports.len() {
            self.imports[index as usize].type_index
        } else {
            self.functions
                .get(index as usize - self.imports.len())?
                .type_index
        };
        self.types.get(ty as usize)
    }
}
pub fn validation_inventory(bytes: &[u8], limits: &Limits) -> Inventory {
    let mut inv = Inventory {
        profile: limits.profile,
        ..Inventory::default()
    };
    if let Err(e) = parse(bytes, limits, &mut inv) {
        inv.error = Some(e);
    }
    inv
}

pub(crate) struct Reader<'a> {
    pub(crate) bytes: &'a [u8],
    pub(crate) pos: usize,
    base: usize,
    pub(crate) function: Option<u32>,
}
impl<'a> Reader<'a> {
    pub(crate) fn at(bytes: &'a [u8], base: usize) -> Self {
        Self {
            bytes,
            pos: 0,
            base,
            function: None,
        }
    }
    pub(crate) fn offset(&self) -> usize {
        self.base + self.pos
    }
    pub(crate) fn err(&self, code: &'static str, m: impl Into<String>) -> Error {
        Error::new(code, m, self.function, self.offset())
    }
    pub(crate) fn byte(&mut self) -> Result<u8, Error> {
        let b = *self
            .bytes
            .get(self.pos)
            .ok_or_else(|| self.err("malformed", "unexpected end of input"))?;
        self.pos += 1;
        Ok(b)
    }
    pub(crate) fn take(&mut self, n: usize) -> Result<&'a [u8], Error> {
        let end = self
            .pos
            .checked_add(n)
            .filter(|v| *v <= self.bytes.len())
            .ok_or_else(|| self.err("malformed", "declared length exceeds input"))?;
        let b = &self.bytes[self.pos..end];
        self.pos = end;
        Ok(b)
    }
    pub(crate) fn u32(&mut self) -> Result<u32, Error> {
        let mut value = 0u32;
        for i in 0..5 {
            let b = self.byte()?;
            if i == 4 && b & 0xf0 != 0 {
                return Err(self.err("malformed", "u32 LEB128 overflow"));
            }
            value |= ((b & 0x7f) as u32) << (7 * i);
            if b & 0x80 == 0 {
                return Ok(value);
            }
        }
        Err(self.err("malformed", "unterminated u32 LEB128"))
    }
    pub(crate) fn signed(&mut self, bits: u32) -> Result<i64, Error> {
        let max = bits.div_ceil(7);
        let mut value = 0u64;
        for i in 0..max {
            let b = self.byte()?;
            let p = b & 0x7f;
            if i == max - 1 {
                let used = bits - 7 * i;
                let positive_max = (1u8 << (used - 1)) - 1;
                let negative_min = 0x7f ^ positive_max;
                if b & 0x80 != 0 || (p > positive_max && p < negative_min) {
                    return Err(self.err("malformed", "signed LEB128 overflow"));
                }
            }
            value |= (p as u64).wrapping_shl(7 * i);
            if b & 0x80 == 0 {
                let shift = 7 * (i + 1);
                if shift < 64 && b & 0x40 != 0 {
                    value |= u64::MAX << shift;
                }
                return Ok(if bits == 32 {
                    value as i32 as i64
                } else {
                    value as i64
                });
            }
        }
        Err(self.err("malformed", "unterminated signed LEB128"))
    }
    pub(crate) fn count(&mut self, max: usize) -> Result<usize, Error> {
        let n = self.u32()? as usize;
        if n > max {
            return Err(self.err("limit", "vector count exceeds profile limit"));
        }
        Ok(n)
    }
    pub(crate) fn name(&mut self) -> Result<String, Error> {
        let n = self.count(4096)?;
        let b = self.take(n)?;
        std::str::from_utf8(b)
            .map(str::to_owned)
            .map_err(|_| self.err("malformed", "name is not UTF-8"))
    }
    fn ty(&mut self, profile: Profile) -> Result<Type, Error> {
        match self.byte()? {
            0x7f => Ok(Type::I32),
            0x7e => Ok(Type::I64),
            0x7d if profile.floats() => Ok(Type::F32),
            0x7c if profile.floats() => Ok(Type::F64),
            _ => Err(self.err("unsupported", "value type is outside the selected profile")),
        }
    }
    pub(crate) fn end(&self) -> Result<(), Error> {
        if self.pos != self.bytes.len() {
            Err(self.err("malformed", "trailing bytes in section or body"))
        } else {
            Ok(())
        }
    }
    fn constant(&mut self, profile: Profile) -> Result<Value, Error> {
        let v = match self.byte()? {
            0x41 => Value::I32(self.signed(32)? as i32),
            0x42 => Value::I64(self.signed(64)?),
            0x43 if profile.floats() => {
                Value::F32(u32::from_le_bytes(self.take(4)?.try_into().unwrap()))
            }
            0x44 if profile.floats() => {
                Value::F64(u64::from_le_bytes(self.take(8)?.try_into().unwrap()))
            }
            _ => {
                return Err(self.err(
                    "unsupported",
                    "constant expressions require one supported numeric constant",
                ))
            }
        };
        if self.byte()? != 0x0b {
            return Err(self.err("unsupported", "extended constant expression"));
        }
        Ok(v)
    }
}
fn parse(bytes: &[u8], limits: &Limits, inv: &mut Inventory) -> Result<Module, Error> {
    limits.check()?;
    if bytes.len() > limits.module_bytes {
        return Err(Error::new("limit", "module byte limit exceeded", None, 0));
    }
    let mut r = Reader::at(bytes, 0);
    if r.take(8)? != b"\0asm\x01\0\0\0" {
        return Err(r.err("malformed", "expected Wasm magic and version 1"));
    }
    let mut m = Module {
        source_bytes: bytes.len(),
        profile: limits.profile,
        types: vec![],
        imports: vec![],
        functions: vec![],
        globals: vec![],
        exports: BTreeMap::new(),
        memory: None,
        data: vec![],
        inventory: Inventory::default(),
    };
    let mut defined = vec![];
    let mut code_seen = false;
    let mut last = 0u8;
    let mut seen = BTreeSet::new();
    let mut instructions = 0;
    while r.pos < bytes.len() {
        let id = r.byte()?;
        let n = r.u32()? as usize;
        let base = r.offset();
        let data = r.take(n)?;
        let mut s = Reader::at(data, base);
        if id == 0 {
            s.name()?;
            continue;
        }
        if id > 11 {
            return Err(s.err(
                "unsupported",
                format!("section {id} is outside this profile"),
            ));
        }
        if id < last || !seen.insert(id) {
            return Err(s.err("malformed", "duplicate or out-of-order section"));
        }
        last = id;
        match id {
            1 => {
                for _ in 0..s.count(limits.types)? {
                    if s.byte()? != 0x60 {
                        return Err(s.err("unsupported", "non-function type"));
                    }
                    let mut params = vec![];
                    for _ in 0..s.count(limits.locals)? {
                        params.push(s.ty(limits.profile)?);
                    }
                    let results = s.count(1)?;
                    let result = if results == 1 {
                        Some(s.ty(limits.profile)?)
                    } else {
                        None
                    };
                    m.types.push(Signature { params, result });
                }
            }
            2 => {
                for _ in 0..s.count(limits.functions)? {
                    let module = s.name()?;
                    let name = s.name()?;
                    let kind = s.byte()?;
                    if kind != 0 {
                        return Err(s.err(
                            "unsupported",
                            "only explicit approved function imports are supported",
                        ));
                    }
                    let type_index = s.u32()?;
                    inv.imports.push((module.clone(), name.clone(), type_index));
                    m.imports.push(Import {
                        module,
                        name,
                        type_index,
                    });
                }
            }
            3 => {
                for _ in 0..s.count(limits.functions.saturating_sub(m.imports.len()))? {
                    defined.push(s.u32()?);
                }
            }
            4 | 8 | 9 => {
                return Err(s.err(
                    "unsupported",
                    format!("section {id} (tables/start/elements) is outside this profile"),
                ))
            }
            5 => {
                let n = s.count(1)?;
                if n == 1 {
                    let flags = s.byte()?;
                    if flags > 1 {
                        return Err(s.err("unsupported", "shared/memory64 memory is unsupported"));
                    }
                    let min = s.u32()?;
                    let max = if flags == 1 {
                        s.u32()?
                    } else {
                        limits.memory_pages
                    };
                    if min > max || max > limits.memory_pages {
                        return Err(s.err("limit", "memory bounds exceed profile"));
                    }
                    m.memory = Some((min, max));
                }
            }
            6 => {
                for _ in 0..s.count(1024)? {
                    let t = s.ty(limits.profile)?;
                    let mutable = match s.byte()? {
                        0 => false,
                        1 => true,
                        _ => return Err(s.err("malformed", "invalid global mutability")),
                    };
                    let value = s.constant(limits.profile)?;
                    if value.ty() != t {
                        return Err(s.err("validation", "global initializer type mismatch"));
                    }
                    m.globals.push(Global { value, mutable });
                }
            }
            7 => {
                for _ in 0..s.count(4096)? {
                    let name = s.name()?;
                    let kind = s.byte()?;
                    let index = s.u32()?;
                    if m.exports.insert(name.clone(), (kind, index)).is_some() {
                        return Err(s.err("validation", "duplicate export name"));
                    }
                    inv.exports.push((name, kind, index));
                }
            }
            10 => {
                code_seen = true;
                let count = s.count(limits.functions)?;
                if count != defined.len() {
                    return Err(s.err("validation", "function and code counts differ"));
                }
                for (i, type_index) in defined.iter().enumerate() {
                    let size = s.u32()? as usize;
                    let base = s.offset();
                    let body = s.take(size)?;
                    let mut b = Reader::at(body, base);
                    b.function = Some((m.imports.len() + i) as u32);
                    let mut locals = vec![];
                    for _ in 0..b.count(limits.locals)? {
                        let n = b.count(limits.locals.saturating_sub(locals.len()))?;
                        let t = b.ty(limits.profile)?;
                        locals.extend(std::iter::repeat_n(t, n));
                    }
                    let code = decode_code(&mut b, limits, inv, &mut instructions)?;
                    b.end()?;
                    m.functions.push(Function {
                        type_index: *type_index,
                        locals,
                        code,
                        offset: base,
                    });
                }
            }
            11 => {
                for _ in 0..s.count(4096)? {
                    let flags = s.u32()?;
                    if flags != 0 && flags != 2 {
                        return Err(s.err("unsupported", "passive data segments unsupported"));
                    }
                    if flags == 2 && s.u32()? != 0 {
                        return Err(s.err("validation", "memory index must be zero"));
                    }
                    let offset = match s.constant(limits.profile)? {
                        Value::I32(v) => v as u32,
                        _ => return Err(s.err("validation", "data offset must be i32")),
                    };
                    let n = s.count(limits.module_bytes)?;
                    m.data.push((offset, s.take(n)?.to_vec()));
                }
            }
            _ => return Err(s.err("malformed", "unknown section")),
        }
        s.end()?;
    }
    if !defined.is_empty() && !code_seen {
        return Err(r.err("validation", "functions have no code section"));
    }
    inv.complete = true;
    crate::validate::module(&m, limits)?;
    m.inventory = inv.clone();
    Ok(m)
}
fn decode_code(
    r: &mut Reader<'_>,
    limits: &Limits,
    inv: &mut Inventory,
    total: &mut usize,
) -> Result<Vec<Instruction>, Error> {
    let mut code: Vec<Instruction> = vec![];
    let mut controls: Vec<(usize, Option<usize>)> = vec![];
    loop {
        let offset = r.offset();
        let o = r.byte()?;
        *inv.opcodes.entry(o).or_default() += 1;
        *total += 1;
        if *total > limits.instructions {
            return Err(r.err("limit", "instruction count exceeds profile"));
        }
        let op = match o {
            0 => Op::Unreachable,
            1 => Op::Nop,
            2..=4 => {
                if controls.len() + 1 >= limits.control_depth {
                    return Err(r.err("limit", "control nesting exceeds profile"));
                }
                let t = r.byte()?;
                let result = match t {
                    0x40 => None,
                    0x7f => Some(Type::I32),
                    0x7e => Some(Type::I64),
                    0x7d if limits.profile.floats() => Some(Type::F32),
                    0x7c if limits.profile.floats() => Some(Type::F64),
                    _ => {
                        return Err(
                            r.err("unsupported", "indexed/multivalue block types unsupported")
                        )
                    }
                };
                controls.push((code.len(), None));
                Op::Block {
                    kind: match o {
                        2 => BlockKind::Block,
                        3 => BlockKind::Loop,
                        _ => BlockKind::If,
                    },
                    result,
                    end: 0,
                    alternative: None,
                }
            }
            5 => {
                let (start, alternative) = controls
                    .last_mut()
                    .ok_or_else(|| r.err("validation", "else without if"))?;
                if alternative.is_some()
                    || !matches!(
                        code[*start].op,
                        Op::Block {
                            kind: BlockKind::If,
                            ..
                        }
                    )
                {
                    return Err(r.err("validation", "else without unmatched if"));
                }
                *alternative = Some(code.len());
                Op::Else { end: 0 }
            }
            0x0b => {
                if let Some((start, alternative)) = controls.pop() {
                    let end = code.len();
                    if let Op::Block {
                        end: e,
                        alternative: a,
                        ..
                    } = &mut code[start].op
                    {
                        *e = end;
                        *a = alternative;
                    }
                    if let Some(i) = alternative {
                        code[i].op = Op::Else { end };
                    }
                    Op::End
                } else {
                    code.push(Instruction {
                        op: Op::End,
                        offset,
                    });
                    return Ok(code);
                }
            }
            0x0c => Op::Br(r.u32()?),
            0x0d => Op::BrIf(r.u32()?),
            0x0e => {
                let n = r.count(limits.instructions)?;
                let mut labels = vec![];
                for _ in 0..n {
                    labels.push(r.u32()?);
                }
                Op::BrTable(labels, r.u32()?)
            }
            0x0f => Op::Return,
            0x10 => Op::Call(r.u32()?),
            0x1a => Op::Drop,
            0x1b => Op::Select,
            0x20 => Op::LocalGet(r.u32()?),
            0x21 => Op::LocalSet(r.u32()?),
            0x22 => Op::LocalTee(r.u32()?),
            0x23 => Op::GlobalGet(r.u32()?),
            0x24 => Op::GlobalSet(r.u32()?),
            0x28..=0x35 => {
                if matches!(o, 0x2a | 0x2b) && !limits.profile.floats() {
                    return Err(Error::new(
                        "unsupported",
                        "float load outside integer profile",
                        r.function,
                        offset,
                    ));
                }
                let align = r.u32()?;
                let natural = match o {
                    0x28 | 0x2a | 0x34 | 0x35 => 2,
                    0x29 | 0x2b => 3,
                    0x2e | 0x2f | 0x32 | 0x33 => 1,
                    _ => 0,
                };
                if align > natural {
                    return Err(r.err("validation", "load alignment exceeds natural width"));
                }
                Op::Load {
                    opcode: o,
                    offset: r.u32()?,
                }
            }
            0x36..=0x3e => {
                if matches!(o, 0x38 | 0x39) && !limits.profile.floats() {
                    return Err(Error::new(
                        "unsupported",
                        "float store outside integer profile",
                        r.function,
                        offset,
                    ));
                }
                let align = r.u32()?;
                let natural = match o {
                    0x36 | 0x38 | 0x3e => 2,
                    0x37 | 0x39 => 3,
                    0x3b | 0x3d => 1,
                    _ => 0,
                };
                if align > natural {
                    return Err(r.err("validation", "store alignment exceeds natural width"));
                }
                Op::Store {
                    opcode: o,
                    offset: r.u32()?,
                }
            }
            0x3f | 0x40 => {
                if r.byte()? != 0 {
                    return Err(r.err("unsupported", "memory index must be canonical zero"));
                }
                if o == 0x3f {
                    Op::MemorySize
                } else {
                    Op::MemoryGrow
                }
            }
            0x41 => Op::Const(Value::I32(r.signed(32)? as i32)),
            0x42 => Op::Const(Value::I64(r.signed(64)?)),
            0x43 if limits.profile.floats() => Op::Const(Value::F32(u32::from_le_bytes(
                r.take(4)?.try_into().unwrap(),
            ))),
            0x44 if limits.profile.floats() => Op::Const(Value::F64(u64::from_le_bytes(
                r.take(8)?.try_into().unwrap(),
            ))),
            0x5b..=0x66 | 0x8b..=0xa6 | 0xa8..=0xab | 0xae..=0xbf if limits.profile.floats() => {
                Op::Numeric(o)
            }
            0xfc if limits.profile.floats() => {
                let sub = r.u32()?;
                if sub > 7 {
                    return Err(Error::new(
                        "unsupported",
                        format!("unsupported 0xfc subopcode {sub}"),
                        r.function,
                        offset,
                    ));
                }
                *inv.extended_opcodes
                    .entry(format!("0xfc:{sub}"))
                    .or_default() += 1;
                Op::Saturating(sub as u8)
            }
            0x45..=0x5a | 0x67..=0x8a | 0xa7 | 0xac | 0xad | 0xc0..=0xc4 => Op::Numeric(o),
            _ => {
                return Err(Error::new(
                    "unsupported",
                    format!("unsupported opcode 0x{o:02x}"),
                    r.function,
                    offset,
                ))
            }
        };
        code.push(Instruction { op, offset });
    }
}
