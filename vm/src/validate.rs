use crate::*;

struct Control {
    kind: BlockKind,
    height: usize,
    result: Option<Type>,
    unreachable: bool,
    has_else: bool,
}
struct Validator {
    stack: Vec<Option<Type>>,
    controls: Vec<Control>,
    function: u32,
    offset: usize,
    max: usize,
}
impl Validator {
    fn error(&self, m: impl Into<String>) -> Error {
        Error::new("validation", m, Some(self.function), self.offset)
    }
    fn pop_any(&mut self) -> Result<Option<Type>, Error> {
        let c = self
            .controls
            .last()
            .ok_or_else(|| self.error("instruction follows function end"))?;
        if self.stack.len() == c.height && c.unreachable {
            return Ok(None);
        }
        if self.stack.len() <= c.height {
            return Err(self.error("operand stack underflow"));
        }
        Ok(self.stack.pop().unwrap())
    }
    fn pop(&mut self, t: Type) -> Result<(), Error> {
        if let Some(actual) = self.pop_any()? {
            if actual != t {
                return Err(self.error(format!("expected {}, found {}", t.name(), actual.name())));
            }
        }
        Ok(())
    }
    fn push(&mut self, t: Option<Type>) -> Result<(), Error> {
        if self.stack.len() >= self.max {
            return Err(Error::new(
                "limit",
                "validated operand stack exceeds limit",
                Some(self.function),
                self.offset,
            ));
        }
        self.stack.push(t);
        Ok(())
    }
    fn result(&mut self, t: Option<Type>) -> Result<(), Error> {
        if let Some(t) = t {
            self.pop(t)?;
        }
        Ok(())
    }
    fn unreachable(&mut self) {
        let c = self.controls.last_mut().unwrap();
        self.stack.truncate(c.height);
        c.unreachable = true;
    }
    fn label(&self, n: u32) -> Result<Option<Type>, Error> {
        let i = self
            .controls
            .len()
            .checked_sub(n as usize + 1)
            .ok_or_else(|| self.error("branch depth exceeds control stack"))?;
        let c = &self.controls[i];
        Ok(if c.kind == BlockKind::Loop {
            None
        } else {
            c.result
        })
    }
}
pub(crate) fn module(m: &Module, limits: &Limits) -> Result<(), Error> {
    if m.profile != limits.profile {
        return Err(Error::new(
            "invalid_limits",
            "module and instance profiles differ",
            None,
            0,
        ));
    }
    if m.types.iter().any(|s| s.params.len() > limits.locals) {
        return Err(Error::new(
            "limit",
            "signature parameters exceed local limit",
            None,
            0,
        ));
    }
    for import in &m.imports {
        let sig = m
            .types
            .get(import.type_index as usize)
            .ok_or_else(|| Error::new("validation", "import type index out of bounds", None, 0))?;
        let allowed = import.module == "mixer"
            && match import.name.as_str() {
                "checkpoint" => sig.params.is_empty() && sig.result.is_none(),
                "abort" => sig.params == [Type::I32] && sig.result.is_none(),
                _ => false,
            };
        if !allowed {
            return Err(Error::new(
                "unsupported",
                format!("unapproved import {}.{}", import.module, import.name),
                None,
                0,
            ));
        }
    }
    for (name, (kind, index)) in &m.exports {
        let valid = match kind {
            0 => (*index as usize) < m.function_count(),
            2 => *index == 0 && m.memory.is_some(),
            3 => (*index as usize) < m.globals.len(),
            _ => false,
        };
        if !valid {
            return Err(Error::new(
                "validation",
                format!("invalid or unsupported export {name}"),
                None,
                0,
            ));
        }
    }
    if !m.data.is_empty() && m.memory.is_none() {
        return Err(Error::new(
            "validation",
            "data segment has no memory",
            None,
            0,
        ));
    }
    for (i, f) in m.functions.iter().enumerate() {
        let function = (m.imports.len() + i) as u32;
        let sig = m.types.get(f.type_index as usize).ok_or_else(|| {
            Error::new(
                "validation",
                "function type index out of bounds",
                Some(function),
                f.offset,
            )
        })?;
        let mut locals = sig.params.clone();
        locals.extend_from_slice(&f.locals);
        if locals.len() > limits.locals {
            return Err(Error::new(
                "limit",
                "parameters plus locals exceed limit",
                Some(function),
                f.offset,
            ));
        }
        let mut v = Validator {
            stack: vec![],
            controls: vec![Control {
                kind: BlockKind::Function,
                height: 0,
                result: sig.result,
                unreachable: false,
                has_else: false,
            }],
            function,
            offset: f.offset,
            max: limits.operand_stack,
        };
        for ins in &f.code {
            v.offset = ins.offset;
            if v.controls.is_empty() {
                return Err(v.error("instruction follows function end"));
            }
            match &ins.op {
                Op::Unreachable => v.unreachable(),
                Op::Nop => {}
                Op::Block { kind, result, .. } => {
                    if v.controls.len() >= limits.control_depth {
                        return Err(Error::new(
                            "limit",
                            "control depth exceeds instance limit",
                            Some(function),
                            v.offset,
                        ));
                    }
                    if *kind == BlockKind::If {
                        v.pop(Type::I32)?;
                    }
                    v.controls.push(Control {
                        kind: *kind,
                        height: v.stack.len(),
                        result: *result,
                        unreachable: false,
                        has_else: false,
                    });
                }
                Op::Else { .. } => {
                    let c = v.controls.last().unwrap();
                    let (height, result, kind) = (c.height, c.result, c.kind);
                    if kind != BlockKind::If {
                        return Err(v.error("else outside if"));
                    }
                    v.result(result)?;
                    if v.stack.len() != height {
                        return Err(v.error("extra values at end of if arm"));
                    }
                    let c = v.controls.last_mut().unwrap();
                    c.unreachable = false;
                    c.has_else = true;
                }
                Op::End => {
                    let c = v.controls.last().unwrap();
                    let (height, result, missing_else) = (
                        c.height,
                        c.result,
                        c.kind == BlockKind::If && !c.has_else && c.result.is_some(),
                    );
                    if missing_else {
                        return Err(v.error("result-producing if requires else"));
                    }
                    v.result(result)?;
                    if v.stack.len() != height {
                        return Err(v.error("extra values at control end"));
                    }
                    v.controls.pop();
                    if let Some(t) = result {
                        v.push(Some(t))?;
                    }
                }
                Op::Br(n) => {
                    let t = v.label(*n)?;
                    v.result(t)?;
                    v.unreachable();
                }
                Op::BrIf(n) => {
                    v.pop(Type::I32)?;
                    let t = v.label(*n)?;
                    v.result(t)?;
                    if let Some(t) = t {
                        v.push(Some(t))?;
                    }
                }
                Op::BrTable(labels, default) => {
                    v.pop(Type::I32)?;
                    let t = v.label(*default)?;
                    for n in labels {
                        if v.label(*n)? != t {
                            return Err(v.error("br_table targets have different label types"));
                        }
                    }
                    v.result(t)?;
                    v.unreachable();
                }
                Op::Return => {
                    v.result(sig.result)?;
                    v.unreachable();
                }
                Op::Call(index) => {
                    let called = m
                        .signature(*index)
                        .ok_or_else(|| v.error("call index out of bounds"))?;
                    for t in called.params.iter().rev() {
                        v.pop(*t)?;
                    }
                    if let Some(t) = called.result {
                        v.push(Some(t))?;
                    }
                }
                Op::Drop => {
                    v.pop_any()?;
                }
                Op::Select => {
                    v.pop(Type::I32)?;
                    let b = v.pop_any()?;
                    let a = v.pop_any()?;
                    if a.is_some() && b.is_some() && a != b {
                        return Err(v.error("select operands have different types"));
                    }
                    v.push(a.or(b))?;
                }
                Op::LocalGet(i) | Op::LocalSet(i) | Op::LocalTee(i) => {
                    let t = *locals
                        .get(*i as usize)
                        .ok_or_else(|| v.error("local index out of bounds"))?;
                    if !matches!(ins.op, Op::LocalGet(_)) {
                        v.pop(t)?;
                    }
                    if !matches!(ins.op, Op::LocalSet(_)) {
                        v.push(Some(t))?;
                    }
                }
                Op::GlobalGet(i) | Op::GlobalSet(i) => {
                    let g = m
                        .globals
                        .get(*i as usize)
                        .ok_or_else(|| v.error("global index out of bounds"))?;
                    if matches!(ins.op, Op::GlobalSet(_)) {
                        if !g.mutable {
                            return Err(v.error("global is immutable"));
                        }
                        v.pop(g.value.ty())?;
                    } else {
                        v.push(Some(g.value.ty()))?;
                    }
                }
                Op::Const(value) => v.push(Some(value.ty()))?,
                Op::Load { opcode, .. } => {
                    if m.memory.is_none() {
                        return Err(v.error("load has no memory"));
                    }
                    v.pop(Type::I32)?;
                    v.push(Some(match opcode {
                        0x2a => Type::F32,
                        0x2b => Type::F64,
                        0x29 | 0x30..=0x35 => Type::I64,
                        _ => Type::I32,
                    }))?;
                }
                Op::Store { opcode, .. } => {
                    if m.memory.is_none() {
                        return Err(v.error("store has no memory"));
                    }
                    v.pop(match opcode {
                        0x38 => Type::F32,
                        0x39 => Type::F64,
                        0x37 | 0x3c..=0x3e => Type::I64,
                        _ => Type::I32,
                    })?;
                    v.pop(Type::I32)?;
                }
                Op::MemorySize | Op::MemoryGrow => {
                    if m.memory.is_none() {
                        return Err(v.error("memory instruction has no memory"));
                    }
                    if matches!(ins.op, Op::MemoryGrow) {
                        v.pop(Type::I32)?;
                    }
                    v.push(Some(Type::I32))?;
                }
                Op::Saturating(sub) => {
                    let (input, output) = crate::float::saturating_shape(*sub);
                    v.pop(input)?;
                    v.push(Some(output))?;
                }
                Op::Numeric(o) => {
                    let (input, count, output) = numeric_type(*o);
                    for _ in 0..count {
                        v.pop(input)?;
                    }
                    v.push(Some(output))?;
                }
            }
        }
        if !v.controls.is_empty() {
            return Err(v.error("unterminated control stack"));
        }
    }
    Ok(())
}
pub(crate) fn numeric_type(o: u8) -> (Type, usize, Type) {
    use Type::*;
    match o {
        0x45 => (I32, 1, I32),
        0x46..=0x4f => (I32, 2, I32),
        0x50 => (I64, 1, I32),
        0x51..=0x5a => (I64, 2, I32),
        0x67..=0x69 | 0xc0 | 0xc1 => (I32, 1, I32),
        0x6a..=0x78 => (I32, 2, I32),
        0x79..=0x7b | 0xc2..=0xc4 => (I64, 1, I64),
        0x7c..=0x8a => (I64, 2, I64),
        0xa7 => (I64, 1, I32),
        0xac | 0xad => (I32, 1, I64),
        _ => crate::float::shape(o).expect("decoder admitted known numeric opcode"),
    }
}
