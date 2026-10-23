use crate::*;
use std::sync::{
    atomic::{AtomicBool, Ordering},
    Arc,
};

/// Cloneable cooperative cancellation flag, checked before each instruction/import.
#[derive(Clone, Default)]
pub struct Cancellation(Arc<AtomicBool>);
impl Cancellation {
    pub fn cancel(&self) {
        self.0.store(true, Ordering::Relaxed);
    }
    pub fn is_cancelled(&self) -> bool {
        self.0.load(Ordering::Relaxed)
    }
}
pub struct Instance {
    module: Module,
    limits: Limits,
    memory: Vec<u8>,
    table: Vec<Option<u32>>,
    globals: Vec<Value>,
    cancellation: Cancellation,
    pub fuel_remaining: u64,
    pub host_calls_used: u64,
}
struct Label {
    kind: BlockKind,
    start: usize,
    end: usize,
    height: usize,
    result: bool,
}
struct Frame {
    function: u32,
    pc: usize,
    locals: Vec<Value>,
    stack: Vec<Value>,
    labels: Vec<Label>,
}
struct ImportContext<'a> {
    #[cfg(feature = "experimental-capability-guest")]
    guest: Option<&'a crate::experimental_capability_guest::GuestImports<'a>>,
    _lifetime: std::marker::PhantomData<&'a ()>,
}
impl ImportContext<'_> {
    fn legacy() -> Self {
        Self {
            #[cfg(feature = "experimental-capability-guest")]
            guest: None,
            _lifetime: std::marker::PhantomData,
        }
    }
    fn check(&self, _function: u32, _offset: usize) -> Result<(), Error> {
        #[cfg(feature = "experimental-capability-guest")]
        if let Some(guest) = self.guest {
            guest.check(_function, _offset)?;
        }
        Ok(())
    }
}
enum Entry<'a> {
    Export(&'a str),
    #[cfg(feature = "experimental-capability-guest")]
    Function(u32),
}
impl Instance {
    pub fn new(module: Module, limits: Limits) -> Result<Self, Error> {
        Self::new_with_admission(module, limits, ImportAdmission::Legacy)
    }
    #[cfg(feature = "experimental-capability-guest")]
    pub(crate) fn new_capability(module: Module, limits: Limits) -> Result<Self, Error> {
        Self::new_with_admission(module, limits, ImportAdmission::ExperimentalCapabilityV1)
    }
    fn new_with_admission(
        module: Module,
        limits: Limits,
        admission: ImportAdmission,
    ) -> Result<Self, Error> {
        // A module decoded with wider limits is revalidated against this instance's limits.
        limits.check()?;
        match admission {
            ImportAdmission::Legacy => crate::validate::module(&module, &limits)?,
            #[cfg(feature = "experimental-capability-guest")]
            ImportAdmission::ExperimentalCapabilityV1 => {
                crate::validate::module_with_admission(&module, &limits, admission)?
            }
        }
        if module.source_bytes > limits.module_bytes {
            return Err(Error::new(
                "limit",
                "instance module byte limit exceeded",
                None,
                0,
            ));
        }
        if module.function_count() > limits.functions || module.types.len() > limits.types {
            return Err(Error::new(
                "limit",
                "instance limits narrower than module",
                None,
                0,
            ));
        }
        if module.functions.iter().map(|f| f.code.len()).sum::<usize>() > limits.instructions {
            return Err(Error::new("limit", "instruction limit exceeded", None, 0));
        }
        let pages = module.memory.map(|m| m.0).unwrap_or(0);
        if module
            .memory
            .is_some_and(|(min, max)| min > limits.memory_pages || max > limits.memory_pages)
        {
            return Err(Error::new(
                "limit",
                "instance memory limit exceeded",
                None,
                0,
            ));
        }
        let bytes = pages as usize * 65536;
        let mut memory = vec![];
        memory
            .try_reserve_exact(bytes)
            .map_err(|_| Error::new("allocation", "cannot allocate initial memory", None, 0))?;
        memory.resize(bytes, 0);
        for (offset, data) in &module.data {
            let start = *offset as usize;
            let end = start
                .checked_add(data.len())
                .filter(|v| *v <= memory.len())
                .ok_or_else(|| {
                    Error::new(
                        "memory_out_of_bounds",
                        "active data segment exceeds initial memory",
                        None,
                        0,
                    )
                })?;
            memory[start..end].copy_from_slice(data);
        }
        let count = module.table.map(|(min, _)| min as usize).unwrap_or(0);
        let mut table = Vec::new();
        table
            .try_reserve_exact(count)
            .map_err(|_| Error::new("allocation", "cannot allocate table", None, 0))?;
        table.resize(count, None);
        for (offset, functions) in &module.elements {
            let start = *offset as usize;
            let end = start
                .checked_add(functions.len())
                .filter(|n| *n <= table.len())
                .ok_or_else(|| {
                    Error::new(
                        "table_out_of_bounds",
                        "active element segment exceeds initial table",
                        None,
                        0,
                    )
                })?;
            for (slot, function) in table[start..end].iter_mut().zip(functions) {
                *slot = Some(*function);
            }
        }
        let globals = module.globals.iter().map(|g| g.value).collect();
        let fuel = limits.fuel;
        Ok(Self {
            module,
            globals,
            memory,
            table,
            limits,
            cancellation: Cancellation::default(),
            fuel_remaining: fuel,
            host_calls_used: 0,
        })
    }
    pub fn cancellation(&self) -> Cancellation {
        self.cancellation.clone()
    }
    pub fn memory(&self) -> &[u8] {
        &self.memory
    }
    /// Host transfer only; callers must serialize access and bound transfer size.
    pub(crate) fn write_memory(&mut self, offset: u32, bytes: &[u8]) -> Result<(), Error> {
        let start = offset as usize;
        let end = start
            .checked_add(bytes.len())
            .filter(|n| *n <= self.memory.len())
            .ok_or_else(|| {
                Error::new(
                    "memory_out_of_bounds",
                    "host transfer exceeds memory",
                    None,
                    0,
                )
            })?;
        self.memory[start..end].copy_from_slice(bytes);
        Ok(())
    }
    pub fn invoke(&mut self, name: &str, args: &[Value]) -> Result<Option<Value>, Error> {
        self.invoke_inner(Entry::Export(name), args, ImportContext::legacy())
    }
    #[cfg(feature = "experimental-capability-guest")]
    pub(crate) fn invoke_capability(
        &mut self,
        index: u32,
        args: &[Value],
        guest: &crate::experimental_capability_guest::GuestImports<'_>,
    ) -> Result<Option<Value>, Error> {
        self.invoke_inner(
            Entry::Function(index),
            args,
            ImportContext {
                guest: Some(guest),
                _lifetime: std::marker::PhantomData,
            },
        )
    }
    #[cfg(feature = "experimental-capability-guest")]
    pub(crate) fn invoke_capability_export(
        &mut self,
        name: &str,
        args: &[Value],
        guest: &crate::experimental_capability_guest::GuestImports<'_>,
    ) -> Result<Option<Value>, Error> {
        self.invoke_inner(
            Entry::Export(name),
            args,
            ImportContext {
                guest: Some(guest),
                _lifetime: std::marker::PhantomData,
            },
        )
    }
    fn invoke_inner(
        &mut self,
        entry: Entry<'_>,
        args: &[Value],
        imports: ImportContext<'_>,
    ) -> Result<Option<Value>, Error> {
        self.fuel_remaining = self.limits.fuel;
        self.host_calls_used = 0;
        if self.limits.profile.floats() {
            crate::float::environment()?;
        }
        let index = match entry {
            Entry::Export(name) => {
                let (kind, index) = *self.module.exports.get(name).ok_or_else(|| {
                    Error::new("unknown_export", format!("unknown export {name}"), None, 0)
                })?;
                if kind != 0 {
                    return Err(Error::new(
                        "invalid_arguments",
                        "export is not a function",
                        None,
                        0,
                    ));
                }
                index
            }
            #[cfg(feature = "experimental-capability-guest")]
            Entry::Function(index) => index,
        };
        let sig = self.module.signature(index).expect("validated signature");
        if args.len() != sig.params.len() || args.iter().zip(&sig.params).any(|(a, t)| a.ty() != *t)
        {
            return Err(Error::new(
                "invalid_arguments",
                "arguments do not match exported function signature",
                Some(index),
                0,
            ));
        }
        if (index as usize) < self.module.imports.len() {
            self.charge(index, 0)?;
            return self.import(index, args, index, 0, &imports);
        }
        let mut frames = vec![self.frame(index, args.to_vec())?];
        loop {
            let frame = frames.last_mut().expect("active frame");
            let func = &self.module.functions[frame.function as usize - self.module.imports.len()];
            let ins = &func.code[frame.pc];
            let function = frame.function;
            let offset = ins.offset;
            if self.cancellation.is_cancelled() {
                return Err(Error::new(
                    "cancelled",
                    "execution cancelled",
                    Some(function),
                    offset,
                ));
            }
            imports.check(function, offset)?;
            if self.fuel_remaining == 0 {
                return Err(Error::new(
                    "fuel_exhausted",
                    "instruction fuel exhausted",
                    Some(function),
                    offset,
                ));
            }
            self.fuel_remaining -= 1;
            frame.pc += 1;
            let trap = |code, message| Error::new(code, message, Some(function), offset);
            let mut finished = false;
            match &ins.op {
                Op::Unreachable => {
                    return Err(trap("unreachable", "unreachable instruction executed"))
                }
                Op::Nop => {}
                Op::Const(v) => frame.stack.push(*v),
                Op::Drop => {
                    frame.stack.pop().expect("validated operand");
                }
                Op::Select => {
                    let c = pop32(&mut frame.stack);
                    let b = frame.stack.pop().unwrap();
                    let a = frame.stack.pop().unwrap();
                    frame.stack.push(if c != 0 { a } else { b });
                }
                Op::LocalGet(i) => frame.stack.push(frame.locals[*i as usize]),
                Op::LocalSet(i) => frame.locals[*i as usize] = frame.stack.pop().unwrap(),
                Op::LocalTee(i) => frame.locals[*i as usize] = *frame.stack.last().unwrap(),
                Op::GlobalGet(i) => frame.stack.push(self.globals[*i as usize]),
                Op::GlobalSet(i) => self.globals[*i as usize] = frame.stack.pop().unwrap(),
                Op::Block {
                    kind,
                    result,
                    end,
                    alternative,
                } => {
                    let cond = if *kind == BlockKind::If {
                        pop32(&mut frame.stack) != 0
                    } else {
                        true
                    };
                    frame.labels.push(Label {
                        kind: *kind,
                        start: frame.pc,
                        end: *end,
                        height: frame.stack.len(),
                        result: result.is_some(),
                    });
                    if !cond {
                        frame.pc = alternative.map(|p| p + 1).unwrap_or(*end);
                    }
                }
                Op::Else { end } => frame.pc = *end,
                Op::End => {
                    let label = frame.labels.pop().unwrap();
                    finish_label(frame, &label);
                    if label.kind == BlockKind::Function {
                        finished = true;
                    }
                }
                Op::Br(n) => finished = branch(frame, *n),
                Op::BrIf(n) => {
                    if pop32(&mut frame.stack) != 0 {
                        finished = branch(frame, *n);
                    }
                }
                Op::BrTable(labels, default) => {
                    let n = pop32(&mut frame.stack) as u32 as usize;
                    finished = branch(frame, labels.get(n).copied().unwrap_or(*default));
                }
                Op::Return => {
                    let result = self.module.signature(function).unwrap().result.is_some();
                    let value = if result { frame.stack.pop() } else { None };
                    frame.stack.clear();
                    frame.stack.extend(value);
                    finished = true;
                }
                Op::Call(index) => {
                    let sig = self.module.signature(*index).unwrap();
                    let split = frame.stack.len() - sig.params.len();
                    let args = frame.stack.split_off(split);
                    if (*index as usize) < self.module.imports.len() {
                        let result = self.import(*index, &args, function, offset, &imports)?;
                        frame.stack.extend(result);
                    } else {
                        if frames.len() >= self.limits.call_depth {
                            return Err(trap("call_depth_exceeded", "call depth limit exceeded"));
                        }
                        let f = self.frame(*index, args)?;
                        frames.push(f);
                    }
                    continue;
                }
                Op::CallIndirect(type_index) => {
                    let selector = pop32(&mut frame.stack) as u32 as usize;
                    let target = self
                        .table
                        .get(selector)
                        .ok_or_else(|| {
                            trap("table_out_of_bounds", "indirect call index exceeds table")
                        })?
                        .ok_or_else(|| {
                            trap("indirect_call_null", "indirect call selected a null entry")
                        })?;
                    let expected = &self.module.types[*type_index as usize];
                    let actual = self.module.signature(target).unwrap();
                    if actual != expected {
                        return Err(trap(
                            "indirect_call_type_mismatch",
                            "indirect call signature mismatch",
                        ));
                    }
                    let args = frame
                        .stack
                        .split_off(frame.stack.len() - expected.params.len());
                    if (target as usize) < self.module.imports.len() {
                        let result = self.import(target, &args, function, offset, &imports)?;
                        frame.stack.extend(result);
                    } else {
                        if frames.len() >= self.limits.call_depth {
                            return Err(trap("call_depth_exceeded", "call depth limit exceeded"));
                        }
                        frames.push(self.frame(target, args)?);
                    }
                    continue;
                }
                Op::MemoryCopy => {
                    let len = pop32(&mut frame.stack) as u32 as usize;
                    let src = pop32(&mut frame.stack) as u32 as usize;
                    let dst = pop32(&mut frame.stack) as u32 as usize;
                    let src_end = src
                        .checked_add(len)
                        .filter(|end| *end <= self.memory.len())
                        .ok_or_else(|| {
                            trap("memory_out_of_bounds", "memory.copy source exceeds memory")
                        })?;
                    dst.checked_add(len)
                        .filter(|end| *end <= self.memory.len())
                        .ok_or_else(|| {
                            trap(
                                "memory_out_of_bounds",
                                "memory.copy destination exceeds memory",
                            )
                        })?;
                    self.bulk_fuel(len, function, offset)?;
                    self.memory.copy_within(src..src_end, dst);
                }
                Op::MemoryFill => {
                    let len = pop32(&mut frame.stack) as u32 as usize;
                    let value = pop32(&mut frame.stack) as u8;
                    let dst = pop32(&mut frame.stack) as u32 as usize;
                    let end = dst
                        .checked_add(len)
                        .filter(|end| *end <= self.memory.len())
                        .ok_or_else(|| {
                            trap(
                                "memory_out_of_bounds",
                                "memory.fill destination exceeds memory",
                            )
                        })?;
                    self.bulk_fuel(len, function, offset)?;
                    self.memory[dst..end].fill(value);
                }
                Op::MemorySize => frame
                    .stack
                    .push(Value::I32((self.memory.len() / 65536) as i32)),
                Op::MemoryGrow => {
                    let delta = pop32(&mut frame.stack) as u32;
                    let old = (self.memory.len() / 65536) as u32;
                    let max = self.module.memory.unwrap().1;
                    let next = old
                        .checked_add(delta)
                        .filter(|n| *n <= max && *n <= self.limits.memory_pages);
                    let result = if let Some(next) = next {
                        let bytes = next as usize * 65536;
                        if self
                            .memory
                            .try_reserve_exact(bytes - self.memory.len())
                            .is_ok()
                        {
                            self.memory.resize(bytes, 0);
                            old as i32
                        } else {
                            -1
                        }
                    } else {
                        -1
                    };
                    frame.stack.push(Value::I32(result));
                }
                Op::Load {
                    opcode,
                    offset: imm,
                } => {
                    let address = pop32(&mut frame.stack) as u32;
                    let width = memory_width(*opcode);
                    let start = (address as usize)
                        .checked_add(*imm as usize)
                        .ok_or_else(|| {
                            trap(
                                "memory_out_of_bounds",
                                "load effective address exceeds host address space",
                            )
                        })?;
                    let end = start
                        .checked_add(width)
                        .filter(|n| *n <= self.memory.len())
                        .ok_or_else(|| {
                            trap("memory_out_of_bounds", "load exceeds linear memory")
                        })?;
                    let b = &self.memory[start..end];
                    let mut padded = [0u8; 8];
                    padded[..width].copy_from_slice(b);
                    let x = u64::from_le_bytes(padded);
                    let value = match opcode {
                        0x28 => Value::I32(x as i32),
                        0x29 => Value::I64(x as i64),
                        0x2a => Value::F32(x as u32),
                        0x2b => Value::F64(x),
                        0x2c => Value::I32(x as i8 as i32),
                        0x2d => Value::I32(x as u8 as i32),
                        0x2e => Value::I32(x as i16 as i32),
                        0x2f => Value::I32(x as u16 as i32),
                        0x30 => Value::I64(x as i8 as i64),
                        0x31 => Value::I64(x as u8 as i64),
                        0x32 => Value::I64(x as i16 as i64),
                        0x33 => Value::I64(x as u16 as i64),
                        0x34 => Value::I64(x as i32 as i64),
                        0x35 => Value::I64(x as u32 as i64),
                        _ => unreachable!(),
                    };
                    frame.stack.push(value);
                }
                Op::Store {
                    opcode,
                    offset: imm,
                } => {
                    let value = frame.stack.pop().unwrap();
                    let address = pop32(&mut frame.stack) as u32;
                    let width = memory_width(*opcode);
                    let start = (address as usize)
                        .checked_add(*imm as usize)
                        .ok_or_else(|| {
                            trap(
                                "memory_out_of_bounds",
                                "store effective address exceeds host address space",
                            )
                        })?;
                    let end = start
                        .checked_add(width)
                        .filter(|n| *n <= self.memory.len())
                        .ok_or_else(|| {
                            trap("memory_out_of_bounds", "store exceeds linear memory")
                        })?;
                    let x = match value {
                        Value::I32(v) => v as u32 as u64,
                        Value::I64(v) => v as u64,
                        Value::F32(v) => v as u64,
                        Value::F64(v) => v,
                    };
                    self.memory[start..end].copy_from_slice(&x.to_le_bytes()[..width]);
                }
                Op::Saturating(sub) => crate::float::saturating(*sub, &mut frame.stack),
                Op::Numeric(o) if crate::float::shape(*o).is_some() => {
                    crate::float::numeric(*o, &mut frame.stack).map_err(|code| {
                        trap(code, "floating-point to integer conversion trapped")
                    })?
                }
                Op::Numeric(o) => numeric(*o, &mut frame.stack).map_err(|code| {
                    trap(
                        code,
                        if code == "integer_divide_by_zero" {
                            "integer division by zero"
                        } else {
                            "signed integer division overflow"
                        },
                    )
                })?,
            }
            if frame.stack.len() > self.limits.operand_stack {
                return Err(trap(
                    "operand_stack_exceeded",
                    "operand stack limit exceeded",
                ));
            }
            if finished {
                let f = frames.pop().unwrap();
                let value = f.stack.last().copied();
                if let Some(caller) = frames.last_mut() {
                    caller.stack.extend(value);
                } else {
                    return Ok(value);
                }
            }
        }
    }
    fn bulk_fuel(&mut self, len: usize, function: u32, offset: usize) -> Result<(), Error> {
        if self.cancellation.is_cancelled() {
            return Err(Error::new(
                "cancelled",
                "bulk operation cancelled before mutation",
                Some(function),
                offset,
            ));
        }
        let extra = len.div_ceil(64) as u64;
        if self.fuel_remaining < extra {
            self.fuel_remaining = 0;
            return Err(Error::new(
                "fuel_exhausted",
                "bulk byte fuel exhausted before mutation",
                Some(function),
                offset,
            ));
        }
        self.fuel_remaining -= extra;
        Ok(())
    }
    fn charge(&mut self, function: u32, offset: usize) -> Result<(), Error> {
        if self.cancellation.is_cancelled() {
            return Err(Error::new(
                "cancelled",
                "execution cancelled",
                Some(function),
                offset,
            ));
        }
        if self.fuel_remaining == 0 {
            return Err(Error::new(
                "fuel_exhausted",
                "instruction fuel exhausted",
                Some(function),
                offset,
            ));
        }
        self.fuel_remaining -= 1;
        Ok(())
    }
    fn import(
        &mut self,
        index: u32,
        args: &[Value],
        caller: u32,
        offset: usize,
        imports: &ImportContext<'_>,
    ) -> Result<Option<Value>, Error> {
        imports.check(caller, offset)?;
        if self.cancellation.is_cancelled() {
            return Err(Error::new(
                "cancelled",
                "execution cancelled",
                Some(caller),
                offset,
            ));
        }
        if self.host_calls_used >= self.limits.host_calls {
            return Err(Error::new(
                "host_call_limit",
                "host call limit exceeded",
                Some(caller),
                offset,
            ));
        }
        self.host_calls_used += 1;
        #[cfg(feature = "experimental-capability-guest")]
        if self.module.imports[index as usize].module
            == crate::experimental_capability_guest::IMPORT_MODULE
        {
            let guest = imports.guest.ok_or_else(|| {
                Error::new(
                    "unsupported",
                    "capability import requires its private guest wrapper",
                    Some(caller),
                    offset,
                )
            })?;
            return guest.import(
                &self.module.imports[index as usize].name,
                args,
                &mut self.memory,
                &mut self.fuel_remaining,
                caller,
                offset,
            );
        }
        match self.module.imports[index as usize].name.as_str() {
            "checkpoint" => Ok(None),
            "abort" => Err(Error::new(
                "host_abort",
                format!("guest requested abort: {:?}", args[0]),
                Some(caller),
                offset,
            )),
            _ => unreachable!("validated import"),
        }
    }
    fn frame(&self, function: u32, args: Vec<Value>) -> Result<Frame, Error> {
        let f = &self.module.functions[function as usize - self.module.imports.len()];
        let sig = self.module.signature(function).unwrap();
        let mut locals = args;
        locals.extend(f.locals.iter().map(|t| Value::zero(*t)));
        Ok(Frame {
            function,
            pc: 0,
            locals,
            stack: vec![],
            labels: vec![Label {
                kind: BlockKind::Function,
                start: 0,
                end: f.code.len() - 1,
                height: 0,
                result: sig.result.is_some(),
            }],
        })
    }
}
fn finish_label(frame: &mut Frame, label: &Label) {
    let value = if label.result {
        frame.stack.pop()
    } else {
        None
    };
    frame.stack.truncate(label.height);
    frame.stack.extend(value);
}
fn branch(frame: &mut Frame, depth: u32) -> bool {
    let index = frame.labels.len() - depth as usize - 1;
    let label = &frame.labels[index];
    let kind = label.kind;
    let height = label.height;
    let pc = if kind == BlockKind::Loop {
        label.start
    } else {
        label.end + 1
    };
    let result = label.result && kind != BlockKind::Loop;
    let value = if result { frame.stack.pop() } else { None };
    frame.stack.truncate(height);
    frame.stack.extend(value);
    frame.labels.truncate(if kind == BlockKind::Loop {
        index + 1
    } else {
        index
    });
    frame.pc = pc;
    kind == BlockKind::Function
}
fn pop32(s: &mut Vec<Value>) -> i32 {
    match s.pop().expect("validated i32") {
        Value::I32(x) => x,
        _ => unreachable!("validated type"),
    }
}
fn pop64(s: &mut Vec<Value>) -> i64 {
    match s.pop().expect("validated i64") {
        Value::I64(x) => x,
        _ => unreachable!("validated type"),
    }
}
fn memory_width(o: u8) -> usize {
    match o {
        0x28 | 0x2a | 0x34 | 0x35 | 0x36 | 0x38 | 0x3e => 4,
        0x29 | 0x2b | 0x37 | 0x39 => 8,
        0x2e | 0x2f | 0x32 | 0x33 | 0x3b | 0x3d => 2,
        _ => 1,
    }
}
fn numeric(o: u8, s: &mut Vec<Value>) -> Result<(), &'static str> {
    use Value::*;
    let (t, count, out) = crate::validate::numeric_type(o);
    if t == Type::I32 {
        let b = if count == 2 { pop32(s) } else { 0 };
        let a = pop32(s);
        let x = match o {
            0x45 => (a == 0) as i32,
            0x46 => (a == b) as i32,
            0x47 => (a != b) as i32,
            0x48 => (a < b) as i32,
            0x49 => ((a as u32) < (b as u32)) as i32,
            0x4a => (a > b) as i32,
            0x4b => ((a as u32) > (b as u32)) as i32,
            0x4c => (a <= b) as i32,
            0x4d => ((a as u32) <= (b as u32)) as i32,
            0x4e => (a >= b) as i32,
            0x4f => ((a as u32) >= (b as u32)) as i32,
            0x67 => a.leading_zeros() as i32,
            0x68 => a.trailing_zeros() as i32,
            0x69 => a.count_ones() as i32,
            0x6a => a.wrapping_add(b),
            0x6b => a.wrapping_sub(b),
            0x6c => a.wrapping_mul(b),
            0x6d => {
                if b == 0 {
                    return Err("integer_divide_by_zero");
                }
                a.checked_div(b).ok_or("integer_overflow")?
            }
            0x6e => {
                if b == 0 {
                    return Err("integer_divide_by_zero");
                }
                ((a as u32) / (b as u32)) as i32
            }
            0x6f => {
                if b == 0 {
                    return Err("integer_divide_by_zero");
                }
                a.wrapping_rem(b)
            }
            0x70 => {
                if b == 0 {
                    return Err("integer_divide_by_zero");
                }
                ((a as u32) % (b as u32)) as i32
            }
            0x71 => a & b,
            0x72 => a | b,
            0x73 => a ^ b,
            0x74 => a.wrapping_shl(b as u32),
            0x75 => a.wrapping_shr(b as u32),
            0x76 => (a as u32).wrapping_shr(b as u32) as i32,
            0x77 => a.rotate_left(b as u32),
            0x78 => a.rotate_right(b as u32),
            0xc0 => a as i8 as i32,
            0xc1 => a as i16 as i32,
            0xac | 0xad => a,
            _ => unreachable!(),
        };
        if out == Type::I64 {
            s.push(I64(if o == 0xac { a as i64 } else { a as u32 as i64 }));
        } else {
            s.push(I32(x));
        }
    } else {
        let b = if count == 2 { pop64(s) } else { 0 };
        let a = pop64(s);
        let x = match o {
            0x50 => (a == 0) as i64,
            0x51 => (a == b) as i64,
            0x52 => (a != b) as i64,
            0x53 => (a < b) as i64,
            0x54 => ((a as u64) < (b as u64)) as i64,
            0x55 => (a > b) as i64,
            0x56 => ((a as u64) > (b as u64)) as i64,
            0x57 => (a <= b) as i64,
            0x58 => ((a as u64) <= (b as u64)) as i64,
            0x59 => (a >= b) as i64,
            0x5a => ((a as u64) >= (b as u64)) as i64,
            0x79 => a.leading_zeros() as i64,
            0x7a => a.trailing_zeros() as i64,
            0x7b => a.count_ones() as i64,
            0x7c => a.wrapping_add(b),
            0x7d => a.wrapping_sub(b),
            0x7e => a.wrapping_mul(b),
            0x7f => {
                if b == 0 {
                    return Err("integer_divide_by_zero");
                }
                a.checked_div(b).ok_or("integer_overflow")?
            }
            0x80 => {
                if b == 0 {
                    return Err("integer_divide_by_zero");
                }
                ((a as u64) / (b as u64)) as i64
            }
            0x81 => {
                if b == 0 {
                    return Err("integer_divide_by_zero");
                }
                a.wrapping_rem(b)
            }
            0x82 => {
                if b == 0 {
                    return Err("integer_divide_by_zero");
                }
                ((a as u64) % (b as u64)) as i64
            }
            0x83 => a & b,
            0x84 => a | b,
            0x85 => a ^ b,
            0x86 => a.wrapping_shl(b as u32),
            0x87 => a.wrapping_shr(b as u32),
            0x88 => (a as u64).wrapping_shr(b as u32) as i64,
            0x89 => a.rotate_left(b as u32),
            0x8a => a.rotate_right(b as u32),
            0xa7 => a as i32 as i64,
            0xc2 => a as i8 as i64,
            0xc3 => a as i16 as i64,
            0xc4 => a as i32 as i64,
            _ => unreachable!(),
        };
        if out == Type::I32 {
            s.push(I32(x as i32));
        } else {
            s.push(I64(x));
        }
    }
    Ok(())
}
