use super::*;
use crate::Limits;

pub(super) struct Reader<'a> {
    bytes: &'a [u8],
    position: usize,
    base: usize,
}
impl Reader<'_> {
    fn byte(&mut self, meter: &mut Meter<'_>) -> Result<u8, CacheFailure> {
        meter.offset = self.base + self.position;
        meter.work(1)?;
        let value = *self
            .bytes
            .get(self.position)
            .ok_or_else(|| meter.error(CacheFailureKind::DecoderMismatch, "decode_end"))?;
        self.position += 1;
        Ok(value)
    }
    fn take(&mut self, count: usize, meter: &mut Meter<'_>) -> Result<&[u8], CacheFailure> {
        meter.offset = self.base + self.position;
        meter.work(count as u64)?;
        let end = self
            .position
            .checked_add(count)
            .filter(|end| *end <= self.bytes.len())
            .ok_or_else(|| meter.error(CacheFailureKind::DecoderMismatch, "decode_length"))?;
        let bytes = &self.bytes[self.position..end];
        self.position = end;
        Ok(bytes)
    }
    fn uint(&mut self, meter: &mut Meter<'_>) -> Result<u32, CacheFailure> {
        let mut value = 0u32;
        for index in 0..5 {
            let byte = self.byte(meter)?;
            if index == 4 && byte & 0xf0 != 0 {
                return Err(meter.error(CacheFailureKind::DecoderMismatch, "decode_u32"));
            }
            value |= ((byte & 127) as u32) << (7 * index);
            if byte & 128 == 0 {
                return Ok(value);
            }
        }
        Err(meter.error(CacheFailureKind::DecoderMismatch, "decode_u32"))
    }
    fn signed(&mut self, bits: u32, meter: &mut Meter<'_>) -> Result<i64, CacheFailure> {
        let maximum = bits.div_ceil(7);
        let mut value = 0u64;
        for index in 0..maximum {
            let byte = self.byte(meter)?;
            let part = byte & 127;
            if index == maximum - 1 {
                let used = bits - 7 * index;
                let positive = (1u8 << (used - 1)) - 1;
                let negative = 127 ^ positive;
                if byte & 128 != 0 || (part > positive && part < negative) {
                    return Err(meter.error(CacheFailureKind::DecoderMismatch, "decode_signed"));
                }
            }
            value |= (part as u64).wrapping_shl(7 * index);
            if byte & 128 == 0 {
                let shift = 7 * (index + 1);
                if shift < 64 && byte & 64 != 0 {
                    value |= u64::MAX << shift;
                }
                return Ok(if bits == 32 {
                    value as i32 as i64
                } else {
                    value as i64
                });
            }
        }
        Err(meter.error(CacheFailureKind::DecoderMismatch, "decode_signed"))
    }
    fn ty(&mut self, profile: Profile, meter: &mut Meter<'_>) -> Result<Type, CacheFailure> {
        match self.byte(meter)? {
            0x7f => Ok(Type::I32),
            0x7e => Ok(Type::I64),
            0x7d if profile.floats() => Ok(Type::F32),
            0x7c if profile.floats() => Ok(Type::F64),
            _ => Err(meter.error(CacheFailureKind::DecoderMismatch, "decode_type")),
        }
    }
    fn zero(&mut self, meter: &mut Meter<'_>) -> Result<(), CacheFailure> {
        if self.uint(meter)? == 0 {
            Ok(())
        } else {
            Err(meter.error(CacheFailureKind::DecoderMismatch, "decode_zero"))
        }
    }
}
#[derive(Clone, Copy, Default, Debug, PartialEq, Eq)]
pub(super) struct Counts {
    locals: usize,
    instructions: usize,
    targets: usize,
}
impl Counts {
    pub fn bytes(self, meter: &Meter<'_>) -> Result<usize, CacheFailure> {
        self.locals
            .checked_mul(std::mem::size_of::<Type>())
            .and_then(|n| {
                self.instructions
                    .checked_mul(std::mem::size_of::<DecodedInstruction>())
                    .and_then(|code| n.checked_add(code))
            })
            .and_then(|n| {
                self.targets
                    .checked_mul(std::mem::size_of::<u32>())
                    .and_then(|targets| n.checked_add(targets))
            })
            .ok_or_else(|| meter.error(CacheFailureKind::Capacity, "entry_size_overflow"))
    }
}
#[derive(Clone, Copy)]
struct Patch {
    start: usize,
    alternative: Option<usize>,
    kind: ControlKind,
}
const EMPTY_PATCH: Patch = Patch {
    start: 0,
    alternative: None,
    kind: ControlKind::Block,
};
pub(super) struct PassState {
    controls: [Patch; 128],
    depth: usize,
    counts: Counts,
}
fn push<T>(values: &mut Vec<T>, value: T, meter: &mut Meter<'_>) -> Result<(), CacheFailure> {
    meter.work(1)?;
    if values.len() == values.capacity() {
        return Err(meter.error(CacheFailureKind::DecoderMismatch, "decode_capacity"));
    }
    values.push(value);
    Ok(())
}
pub(super) fn scan(
    body: &[u8],
    base: usize,
    limits: &Limits,
    meter: &mut Meter<'_>,
    mut output: Option<&mut DecodedFunction>,
) -> Result<Counts, CacheFailure> {
    let mut reader = Reader {
        bytes: body,
        position: 0,
        base,
    };
    let mut state = PassState {
        controls: [EMPTY_PATCH; 128],
        depth: 0,
        counts: Counts::default(),
    };
    let groups = reader.uint(meter)? as usize;
    if groups > limits.locals {
        return Err(meter.error(CacheFailureKind::DecoderMismatch, "decode_local_groups"));
    }
    for _ in 0..groups {
        meter.work(1)?;
        let count = reader.uint(meter)? as usize;
        let ty = reader.ty(limits.profile, meter)?;
        state.counts.locals = state
            .counts
            .locals
            .checked_add(count)
            .filter(|n| *n <= limits.locals)
            .ok_or_else(|| meter.error(CacheFailureKind::DecoderMismatch, "decode_locals"))?;
        // Count expansion work before it occurs, including first-pass preflight.
        for _ in 0..count {
            meter.work(1)?;
            if let Some(entry) = output.as_deref_mut() {
                push(&mut entry.locals, ty, meter)?;
            }
        }
    }
    loop {
        let offset = base + reader.position;
        let opcode = reader.byte(meter)?;
        let index = state.counts.instructions;
        state.counts.instructions = index
            .checked_add(1)
            .filter(|n| *n <= limits.instructions)
            .ok_or_else(|| meter.error(CacheFailureKind::DecoderMismatch, "decode_instructions"))?;
        let mut ended = false;
        let operation = match opcode {
            0 => Operation::Unreachable,
            1 => Operation::Nop,
            2..=4 => {
                let result = match reader.byte(meter)? {
                    0x40 => None,
                    0x7f => Some(Type::I32),
                    0x7e => Some(Type::I64),
                    0x7d if limits.profile.floats() => Some(Type::F32),
                    0x7c if limits.profile.floats() => Some(Type::F64),
                    _ => {
                        return Err(
                            meter.error(CacheFailureKind::DecoderMismatch, "decode_block_type")
                        )
                    }
                };
                if state.depth + 1 >= limits.control_depth || state.depth >= state.controls.len() {
                    return Err(meter.error(CacheFailureKind::DecoderMismatch, "decode_controls"));
                }
                let kind = match opcode {
                    2 => ControlKind::Block,
                    3 => ControlKind::Loop,
                    _ => ControlKind::If,
                };
                meter.work(1)?;
                state.controls[state.depth] = Patch {
                    start: index,
                    alternative: None,
                    kind,
                };
                state.depth += 1;
                Operation::Block {
                    kind,
                    result,
                    end: 0,
                    alternative: None,
                }
            }
            5 => {
                meter.work(1)?;
                let control = state
                    .depth
                    .checked_sub(1)
                    .map(|n| &mut state.controls[n])
                    .ok_or_else(|| meter.error(CacheFailureKind::DecoderMismatch, "decode_else"))?;
                if control.kind != ControlKind::If || control.alternative.is_some() {
                    return Err(meter.error(CacheFailureKind::DecoderMismatch, "decode_else"));
                }
                control.alternative = Some(index);
                Operation::Else { end: 0 }
            }
            0x0b => {
                if state.depth == 0 {
                    ended = true;
                } else {
                    meter.work(1)?;
                    state.depth -= 1;
                    let control = state.controls[state.depth];
                    if let Some(entry) = output.as_deref_mut() {
                        meter.work(1)?;
                        let start = entry.instructions.get_mut(control.start).ok_or_else(|| {
                            meter.error(CacheFailureKind::DecoderMismatch, "decode_patch")
                        })?;
                        match &mut start.operation {
                            Operation::Block {
                                end, alternative, ..
                            } => {
                                *end = index;
                                *alternative = control.alternative;
                            }
                            _ => {
                                return Err(
                                    meter.error(CacheFailureKind::DecoderMismatch, "decode_patch")
                                )
                            }
                        }
                        if let Some(alternative) = control.alternative {
                            meter.work(1)?;
                            entry
                                .instructions
                                .get_mut(alternative)
                                .ok_or_else(|| {
                                    meter.error(CacheFailureKind::DecoderMismatch, "decode_patch")
                                })?
                                .operation = Operation::Else { end: index };
                        }
                    }
                }
                Operation::End
            }
            0x0c => Operation::Br(reader.uint(meter)?),
            0x0d => Operation::BrIf(reader.uint(meter)?),
            0x0e => {
                let count = reader.uint(meter)? as usize;
                if count > limits.instructions {
                    return Err(
                        meter.error(CacheFailureKind::DecoderMismatch, "decode_branch_count")
                    );
                }
                let first = state.counts.targets;
                state.counts.targets = first.checked_add(count).ok_or_else(|| {
                    meter.error(CacheFailureKind::Capacity, "decode_branch_overflow")
                })?;
                for _ in 0..count {
                    let target = reader.uint(meter)?;
                    meter.work(1)?;
                    if let Some(entry) = output.as_deref_mut() {
                        push(&mut entry.branch_targets, target, meter)?;
                    }
                }
                Operation::BrTable {
                    first,
                    count,
                    default: reader.uint(meter)?,
                }
            }
            0x0f => Operation::Return,
            0x10 => Operation::Call(reader.uint(meter)?),
            0x11 if limits.profile == Profile::TableMemoryV3 => {
                let ty = reader.uint(meter)?;
                reader.zero(meter)?;
                Operation::CallIndirect(ty)
            }
            0x1a => Operation::Drop,
            0x1b => Operation::Select,
            0x20 => Operation::LocalGet(reader.uint(meter)?),
            0x21 => Operation::LocalSet(reader.uint(meter)?),
            0x22 => Operation::LocalTee(reader.uint(meter)?),
            0x23 => Operation::GlobalGet(reader.uint(meter)?),
            0x24 => Operation::GlobalSet(reader.uint(meter)?),
            0x28..=0x35 => {
                reader.uint(meter)?;
                Operation::Load {
                    opcode,
                    offset: reader.uint(meter)?,
                }
            }
            0x36..=0x3e => {
                reader.uint(meter)?;
                Operation::Store {
                    opcode,
                    offset: reader.uint(meter)?,
                }
            }
            0x3f | 0x40 => {
                if reader.byte(meter)? != 0 {
                    return Err(
                        meter.error(CacheFailureKind::DecoderMismatch, "decode_memory_zero")
                    );
                }
                if opcode == 0x3f {
                    Operation::MemorySize
                } else {
                    Operation::MemoryGrow
                }
            }
            0x41 => Operation::Const(Value::I32(reader.signed(32, meter)? as i32)),
            0x42 => Operation::Const(Value::I64(reader.signed(64, meter)?)),
            0x43 if limits.profile.floats() => Operation::Const(Value::F32(u32::from_le_bytes(
                reader
                    .take(4, meter)?
                    .try_into()
                    .map_err(|_| meter.error(CacheFailureKind::DecoderMismatch, "decode_f32"))?,
            ))),
            0x44 if limits.profile.floats() => Operation::Const(Value::F64(u64::from_le_bytes(
                reader
                    .take(8, meter)?
                    .try_into()
                    .map_err(|_| meter.error(CacheFailureKind::DecoderMismatch, "decode_f64"))?,
            ))),
            0x45..=0x5a | 0x67..=0x8a | 0xa7 | 0xac | 0xad | 0xc0..=0xc4 => {
                Operation::Numeric(opcode)
            }
            0x5b..=0x66 | 0x8b..=0xa6 | 0xa8..=0xab | 0xae..=0xbf if limits.profile.floats() => {
                Operation::Numeric(opcode)
            }
            0xfc if limits.profile.floats() => match reader.uint(meter)? {
                sub @ 0..=7 => Operation::Saturating(sub as u8),
                10 if limits.profile == Profile::TableMemoryV3 => {
                    reader.zero(meter)?;
                    reader.zero(meter)?;
                    Operation::MemoryCopy
                }
                11 if limits.profile == Profile::TableMemoryV3 => {
                    reader.zero(meter)?;
                    Operation::MemoryFill
                }
                _ => return Err(meter.error(CacheFailureKind::DecoderMismatch, "decode_extended")),
            },
            _ => return Err(meter.error(CacheFailureKind::DecoderMismatch, "decode_opcode")),
        };
        meter.work(1)?;
        if let Some(entry) = output.as_deref_mut() {
            push(
                &mut entry.instructions,
                DecodedInstruction { operation, offset },
                meter,
            )?;
        }
        if ended {
            if reader.position != body.len() {
                return Err(meter.error(CacheFailureKind::DecoderMismatch, "decode_trailing"));
            }
            meter.check()?;
            return Ok(state.counts);
        }
    }
}
pub(super) fn build(
    body: &[u8],
    base: usize,
    type_index: u32,
    function: u32,
    limits: &Limits,
    counts: Counts,
    meter: &mut Meter<'_>,
) -> Result<DecodedFunction, CacheFailure> {
    let bytes = counts.bytes(meter)?;
    let locals = allocate(counts.locals, meter)?;
    let instructions = allocate(counts.instructions, meter)?;
    let branch_targets = allocate(counts.targets, meter)?;
    let mut entry = DecodedFunction {
        function,
        type_index,
        body_offset: base,
        locals,
        instructions,
        branch_targets,
        bytes,
    };
    let actual = scan(body, base, limits, meter, Some(&mut entry))?;
    if actual != counts {
        return Err(meter.error(CacheFailureKind::DecoderMismatch, "decode_count_mismatch"));
    }
    meter.check()?;
    Ok(entry)
}
