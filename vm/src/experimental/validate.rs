use super::*;
use crate::{BlockKind, Type};
use metadata::{Metadata, Signature};
use reader::Reader;

#[derive(Clone, Copy)]
struct Control {
    kind: BlockKind,
    height: usize,
    result: Option<Type>,
    unreachable: bool,
    has_else: bool,
}
pub(super) struct BodyState {
    locals: Buffer<Type>,
    operands: Buffer<Option<Type>>,
    controls: Buffer<Control>,
    cursor: Cursor,
    max: usize,
}
impl BodyState {
    fn new(function: u32, offset: usize, max: usize) -> Self {
        Self {
            locals: Buffer::new(Resource::Scratch),
            operands: Buffer::new(Resource::Scratch),
            controls: Buffer::new(Resource::Scratch),
            cursor: Cursor {
                function: Some(function),
                offset,
            },
            max,
        }
    }
    fn error(&self, meter: &Meter<'_>, code: &'static str) -> Failure {
        meter.error(FailureKind::Validation, code, self.cursor)
    }
    fn pop_any(&mut self, meter: &mut Meter<'_>) -> Result<Option<Type>, Failure> {
        meter.work(1, self.cursor)?;
        let control = self
            .controls
            .last()
            .ok_or_else(|| self.error(meter, "after_function_end"))?;
        if self.operands.len() == control.height && control.unreachable {
            return Ok(None);
        }
        if self.operands.len() <= control.height {
            return Err(self.error(meter, "operand_underflow"));
        }
        Ok(self.operands.pop().unwrap())
    }
    fn pop(&mut self, expected: Type, meter: &mut Meter<'_>) -> Result<(), Failure> {
        if self
            .pop_any(meter)?
            .is_some_and(|actual| actual != expected)
        {
            return Err(self.error(meter, "operand_type"));
        }
        Ok(())
    }
    fn push(&mut self, ty: Option<Type>, meter: &mut Meter<'_>) -> Result<(), Failure> {
        if self.operands.len() >= self.max {
            return Err(meter
                .error(
                    FailureKind::ResourceExhausted,
                    "profile_operand_limit",
                    self.cursor,
                )
                .resource(
                    Resource::Profile,
                    self.operands.len() as u64 + 1,
                    self.max as u64,
                ));
        }
        self.operands.push(ty, meter, self.cursor)
    }
    fn result(&mut self, ty: Option<Type>, meter: &mut Meter<'_>) -> Result<(), Failure> {
        if let Some(ty) = ty {
            self.pop(ty, meter)?;
        }
        Ok(())
    }
    fn unreachable(&mut self, meter: &mut Meter<'_>) -> Result<(), Failure> {
        meter.work(1, self.cursor)?;
        let height = self
            .controls
            .last()
            .ok_or_else(|| self.error(meter, "missing_control"))?
            .height;
        self.operands.truncate(height);
        self.controls.last_mut().unwrap().unreachable = true;
        Ok(())
    }
    fn label(&self, depth: u32, meter: &mut Meter<'_>) -> Result<Option<Type>, Failure> {
        meter.work(1, self.cursor)?;
        let index = (depth as usize)
            .checked_add(1)
            .and_then(|n| self.controls.len().checked_sub(n))
            .ok_or_else(|| self.error(meter, "branch_depth"))?;
        let control = self.controls.get(index).unwrap();
        Ok(if control.kind == BlockKind::Loop {
            None
        } else {
            control.result
        })
    }
    fn call(
        &mut self,
        signature: Signature,
        m: &Metadata,
        meter: &mut Meter<'_>,
    ) -> Result<(), Failure> {
        for ty in m.params(signature).iter().rev() {
            self.pop(*ty, meter)?;
        }
        if let Some(result) = signature.result {
            self.push(Some(result), meter)?;
        }
        Ok(())
    }
    fn dispose(self, meter: &mut Meter<'_>) {
        self.locals.dispose(meter);
        self.operands.dispose(meter);
        self.controls.dispose(meter);
    }
}
pub(super) fn all(
    source: &[u8],
    limits: &Limits,
    m: &mut Metadata,
    meter: &mut Meter<'_>,
) -> Result<(), Failure> {
    let mut total = 0usize;
    for defined in 0..m.functions.len() {
        let function = u32::try_from(m.imports.len() + defined).map_err(|_| {
            meter.error(
                FailureKind::ResourceExhausted,
                "function_index_overflow",
                Cursor::default(),
            )
        })?;
        let f = *m.functions.get(defined).unwrap();
        let signature = *m.signatures.get(f.type_index as usize).unwrap();
        let mut r = Reader::new(f.body.slice(source), f.body.offset as usize);
        r.function = Some(function);
        let mut state = BodyState::new(function, r.cursor().offset, limits.operand_stack);
        for ty in m.params(signature) {
            state.locals.push(*ty, meter, r.cursor())?;
        }
        for _ in 0..r.count(limits.locals, meter)? {
            let n = r.count(limits.locals.saturating_sub(state.locals.len()), meter)?;
            let ty = r.ty(limits.profile, meter)?;
            for _ in 0..n {
                state.locals.push(ty, meter, r.cursor())?;
            }
        }
        state.controls.push(
            Control {
                kind: BlockKind::Function,
                height: 0,
                result: signature.result,
                unreachable: false,
                has_else: false,
            },
            meter,
            r.cursor(),
        )?;
        loop {
            state.cursor = r.cursor();
            if state.controls.len() == 0 {
                return Err(state.error(meter, "after_function_end"));
            }
            let opcode = r.byte(meter)?;
            total = total.checked_add(1).ok_or_else(|| {
                meter.error(
                    FailureKind::ResourceExhausted,
                    "instruction_count_overflow",
                    state.cursor,
                )
            })?;
            if total > limits.instructions {
                return Err(meter
                    .error(
                        FailureKind::ResourceExhausted,
                        "profile_instruction_limit",
                        state.cursor,
                    )
                    .resource(Resource::Profile, total as u64, limits.instructions as u64));
            }
            match opcode {
                0 => state.unreachable(meter)?,
                1 => {}
                2..=4 => {
                    let result = match r.byte(meter)? {
                        0x40 => None,
                        0x7f => Some(Type::I32),
                        0x7e => Some(Type::I64),
                        0x7d if limits.profile.floats() => Some(Type::F32),
                        0x7c if limits.profile.floats() => Some(Type::F64),
                        _ => return Err(r.error(meter, FailureKind::Unsupported, "block_type")),
                    };
                    if state.controls.len() >= limits.control_depth {
                        return Err(meter
                            .error(
                                FailureKind::ResourceExhausted,
                                "profile_control_limit",
                                state.cursor,
                            )
                            .resource(
                                Resource::Profile,
                                state.controls.len() as u64 + 1,
                                limits.control_depth as u64,
                            ));
                    }
                    let kind = match opcode {
                        2 => BlockKind::Block,
                        3 => BlockKind::Loop,
                        _ => BlockKind::If,
                    };
                    if kind == BlockKind::If {
                        state.pop(Type::I32, meter)?;
                    }
                    state.controls.push(
                        Control {
                            kind,
                            height: state.operands.len(),
                            result,
                            unreachable: false,
                            has_else: false,
                        },
                        meter,
                        state.cursor,
                    )?;
                }
                5 => {
                    let control = *state.controls.last().unwrap();
                    if control.kind != BlockKind::If || control.has_else {
                        return Err(state.error(meter, "unmatched_else"));
                    }
                    state.result(control.result, meter)?;
                    if state.operands.len() != control.height {
                        return Err(state.error(meter, "if_arm_extra_values"));
                    }
                    let control = state.controls.last_mut().unwrap();
                    control.unreachable = false;
                    control.has_else = true;
                }
                0x0b => {
                    let control = *state.controls.last().unwrap();
                    if control.kind == BlockKind::If
                        && control.result.is_some()
                        && !control.has_else
                    {
                        return Err(state.error(meter, "if_result_without_else"));
                    }
                    state.result(control.result, meter)?;
                    if state.operands.len() != control.height {
                        return Err(state.error(meter, "control_extra_values"));
                    }
                    state.controls.pop();
                    if let Some(ty) = control.result {
                        state.push(Some(ty), meter)?;
                    }
                    if state.controls.len() == 0 {
                        r.end(meter)?;
                        break;
                    }
                }
                0x0c => {
                    let depth = r.uint(meter)?;
                    let ty = state.label(depth, meter)?;
                    state.result(ty, meter)?;
                    state.unreachable(meter)?;
                }
                0x0d => {
                    let depth = r.uint(meter)?;
                    state.pop(Type::I32, meter)?;
                    let ty = state.label(depth, meter)?;
                    state.result(ty, meter)?;
                    if let Some(ty) = ty {
                        state.push(Some(ty), meter)?;
                    }
                }
                0x0e => {
                    let count = r.count(limits.instructions, meter)?;
                    state.pop(Type::I32, meter)?;
                    let mut expected = None;
                    for _ in 0..count {
                        let depth = r.uint(meter)?;
                        let ty = state.label(depth, meter)?;
                        if expected.is_some_and(|expected| expected != ty) {
                            return Err(state.error(meter, "branch_table_types"));
                        }
                        expected = Some(ty);
                    }
                    let depth = r.uint(meter)?;
                    let default = state.label(depth, meter)?;
                    if expected.is_some_and(|expected| expected != default) {
                        return Err(state.error(meter, "branch_table_types"));
                    }
                    state.result(default, meter)?;
                    state.unreachable(meter)?;
                }
                0x0f => {
                    state.result(signature.result, meter)?;
                    state.unreachable(meter)?;
                }
                0x10 => {
                    let index = r.uint(meter)?;
                    let called = m
                        .signature(index)
                        .ok_or_else(|| state.error(meter, "call_index"))?;
                    state.call(called, m, meter)?;
                }
                0x11 if limits.profile == Profile::TableMemoryV3 => {
                    let ty = r.uint(meter)?;
                    if r.uint(meter)? != 0 {
                        return Err(state.error(meter, "indirect_table_index"));
                    }
                    if m.table.is_none() {
                        return Err(state.error(meter, "indirect_without_table"));
                    }
                    let signature = m
                        .signatures
                        .get(ty as usize)
                        .copied()
                        .ok_or_else(|| state.error(meter, "indirect_type_index"))?;
                    state.pop(Type::I32, meter)?;
                    state.call(signature, m, meter)?;
                }
                0x1a => {
                    state.pop_any(meter)?;
                }
                0x1b => {
                    state.pop(Type::I32, meter)?;
                    let b = state.pop_any(meter)?;
                    let a = state.pop_any(meter)?;
                    if a.is_some() && b.is_some() && a != b {
                        return Err(state.error(meter, "select_types"));
                    }
                    state.push(a.or(b), meter)?;
                }
                0x20..=0x22 => {
                    let index = r.uint(meter)? as usize;
                    let ty = *state
                        .locals
                        .get(index)
                        .ok_or_else(|| state.error(meter, "local_index"))?;
                    if opcode != 0x20 {
                        state.pop(ty, meter)?;
                    }
                    if opcode != 0x21 {
                        state.push(Some(ty), meter)?;
                    }
                }
                0x23..=0x24 => {
                    let index = r.uint(meter)? as usize;
                    let global = m
                        .globals
                        .get(index)
                        .ok_or_else(|| state.error(meter, "global_index"))?;
                    if opcode == 0x24 {
                        if !global.mutable {
                            return Err(state.error(meter, "immutable_global"));
                        }
                        state.pop(global.ty, meter)?;
                    } else {
                        state.push(Some(global.ty), meter)?;
                    }
                }
                0x28..=0x35 => {
                    if [0x2a, 0x2b].contains(&opcode) && !limits.profile.floats() {
                        return Err(r.error(meter, FailureKind::Unsupported, "float_load"));
                    }
                    let alignment = r.uint(meter)?;
                    let natural = match opcode {
                        0x28 | 0x2a | 0x34 | 0x35 => 2,
                        0x29 | 0x2b => 3,
                        0x2e | 0x2f | 0x32 | 0x33 => 1,
                        _ => 0,
                    };
                    if alignment > natural {
                        return Err(state.error(meter, "load_alignment"));
                    }
                    r.uint(meter)?;
                    if m.memory.is_none() {
                        return Err(state.error(meter, "load_without_memory"));
                    }
                    state.pop(Type::I32, meter)?;
                    let ty = match opcode {
                        0x2a => Type::F32,
                        0x2b => Type::F64,
                        0x29 | 0x30..=0x35 => Type::I64,
                        _ => Type::I32,
                    };
                    state.push(Some(ty), meter)?;
                }
                0x36..=0x3e => {
                    if [0x38, 0x39].contains(&opcode) && !limits.profile.floats() {
                        return Err(r.error(meter, FailureKind::Unsupported, "float_store"));
                    }
                    let alignment = r.uint(meter)?;
                    let natural = match opcode {
                        0x36 | 0x38 | 0x3e => 2,
                        0x37 | 0x39 => 3,
                        0x3b | 0x3d => 1,
                        _ => 0,
                    };
                    if alignment > natural {
                        return Err(state.error(meter, "store_alignment"));
                    }
                    r.uint(meter)?;
                    if m.memory.is_none() {
                        return Err(state.error(meter, "store_without_memory"));
                    }
                    let ty = match opcode {
                        0x38 => Type::F32,
                        0x39 => Type::F64,
                        0x37 | 0x3c..=0x3e => Type::I64,
                        _ => Type::I32,
                    };
                    state.pop(ty, meter)?;
                    state.pop(Type::I32, meter)?;
                }
                0x3f | 0x40 => {
                    if r.byte(meter)? != 0 {
                        return Err(r.error(meter, FailureKind::Unsupported, "memory_index"));
                    }
                    if m.memory.is_none() {
                        return Err(state.error(meter, "memory_instruction_without_memory"));
                    }
                    if opcode == 0x40 {
                        state.pop(Type::I32, meter)?;
                    }
                    state.push(Some(Type::I32), meter)?;
                }
                0x41 => {
                    r.signed(32, meter)?;
                    state.push(Some(Type::I32), meter)?;
                }
                0x42 => {
                    r.signed(64, meter)?;
                    state.push(Some(Type::I64), meter)?;
                }
                0x43 if limits.profile.floats() => {
                    r.take(4, meter)?;
                    state.push(Some(Type::F32), meter)?;
                }
                0x44 if limits.profile.floats() => {
                    r.take(8, meter)?;
                    state.push(Some(Type::F64), meter)?;
                }
                0x45..=0xc4 => {
                    let floating = matches!(opcode,0x5b..=0x66|0x8b..=0xa6|0xa8..=0xab|0xae..=0xbf);
                    if floating && !limits.profile.floats() {
                        return Err(r.error(meter, FailureKind::Unsupported, "float_numeric"));
                    }
                    let (input, count, output) = crate::validate::numeric_type(opcode);
                    for _ in 0..count {
                        state.pop(input, meter)?;
                    }
                    state.push(Some(output), meter)?;
                }
                0xfc if limits.profile.floats() => {
                    let sub = r.uint(meter)?;
                    match sub {
                        0..=7 => {
                            let (input, output) = crate::float::saturating_shape(sub as u8);
                            state.pop(input, meter)?;
                            state.push(Some(output), meter)?;
                        }
                        10 | 11 if limits.profile == Profile::TableMemoryV3 => {
                            if r.uint(meter)? != 0 || (sub == 10 && r.uint(meter)? != 0) {
                                return Err(state.error(meter, "bulk_memory_index"));
                            }
                            if m.memory.is_none() {
                                return Err(state.error(meter, "bulk_without_memory"));
                            }
                            for _ in 0..3 {
                                state.pop(Type::I32, meter)?;
                            }
                        }
                        _ => {
                            return Err(r.error(meter, FailureKind::Unsupported, "extended_opcode"))
                        }
                    }
                }
                _ => return Err(r.error(meter, FailureKind::Unsupported, "opcode")),
            }
        }
        state.dispose(meter);
    }
    m.instructions = total;
    Ok(())
}
