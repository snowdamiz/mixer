//! Owned bounded WebAssembly profiles. No production runtime dependencies.
mod decode;
mod execute;
#[cfg(feature = "experimental-stream-validation")]
pub mod experimental;
mod ffi;
mod float;
mod inspect;
mod session;
mod validate;

pub use decode::{validation_inventory, Inventory, Module};
pub use execute::{Cancellation, Instance};
pub use ffi::*;
pub use inspect::inventory;
pub use session::*;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Type {
    I32,
    I64,
    F32,
    F64,
}
impl Type {
    pub fn name(self) -> &'static str {
        match self {
            Self::I32 => "i32",
            Self::I64 => "i64",
            Self::F32 => "f32",
            Self::F64 => "f64",
        }
    }
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Value {
    I32(i32),
    I64(i64),
    /// Raw IEEE-754 bits preserve signed zero and NaN payloads.
    F32(u32),
    F64(u64),
}
impl Value {
    pub fn ty(self) -> Type {
        match self {
            Self::I32(_) => Type::I32,
            Self::I64(_) => Type::I64,
            Self::F32(_) => Type::F32,
            Self::F64(_) => Type::F64,
        }
    }
    pub fn zero(t: Type) -> Self {
        match t {
            Type::I32 => Self::I32(0),
            Type::I64 => Self::I64(0),
            Type::F32 => Self::F32(0),
            Type::F64 => Self::F64(0),
        }
    }
    pub fn json(self) -> String {
        match self {
            Self::I32(v) => format!("{{\"type\":\"i32\",\"value\":{v}}}"),
            Self::I64(v) => format!("{{\"type\":\"i64\",\"value\":\"{v}\"}}"),
            Self::F32(bits) => format!(
                "{{\"type\":\"f32\",\"bits\":\"0x{bits:08x}\",\"value\":{}}}",
                json_string(&f32::from_bits(bits).to_string())
            ),
            Self::F64(bits) => format!(
                "{{\"type\":\"f64\",\"bits\":\"0x{bits:016x}\",\"value\":{}}}",
                json_string(&f64::from_bits(bits).to_string())
            ),
        }
    }
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum Profile {
    #[default]
    IntegerV1,
    NumericV2,
    TableMemoryV3,
}
impl Profile {
    pub fn name(self) -> &'static str {
        match self {
            Self::IntegerV1 => "mixer-integer-v1",
            Self::NumericV2 => "mixer-numeric-v2",
            Self::TableMemoryV3 => "mixer-table-memory-v3",
        }
    }
    pub(crate) fn floats(self) -> bool {
        self != Self::IntegerV1
    }
}

#[derive(Clone, Debug)]
pub struct Limits {
    pub profile: Profile,
    pub table_elements: usize,
    pub module_bytes: usize,
    pub functions: usize,
    pub types: usize,
    pub instructions: usize,
    pub locals: usize,
    pub operand_stack: usize,
    pub call_depth: usize,
    pub control_depth: usize,
    pub memory_pages: u32,
    pub fuel: u64,
    pub host_calls: u64,
}
impl Default for Limits {
    fn default() -> Self {
        Self {
            profile: Profile::IntegerV1,
            table_elements: 65_536,
            module_bytes: 4 * 1024 * 1024,
            functions: 2048,
            types: 512,
            instructions: 200_000,
            locals: 4096,
            operand_stack: 4096,
            call_depth: 64,
            control_depth: 128,
            memory_pages: 64,
            fuel: 1_000_000,
            host_calls: 1024,
        }
    }
}
impl Limits {
    pub fn check(&self) -> Result<(), Error> {
        let d = Self::default();
        if self.table_elements > d.table_elements
            || self.module_bytes == 0
            || self.module_bytes > d.module_bytes
            || self.functions == 0
            || self.functions > d.functions
            || self.types == 0
            || self.types > d.types
            || self.instructions == 0
            || self.instructions > d.instructions
            || self.locals > d.locals
            || self.operand_stack == 0
            || self.operand_stack > d.operand_stack
            || self.call_depth == 0
            || self.call_depth > d.call_depth
            || self.control_depth == 0
            || self.control_depth > d.control_depth
            || self.memory_pages > d.memory_pages
            || self.fuel > d.fuel
            || self.host_calls > d.host_calls
        {
            return Err(Error::new(
                "invalid_limits",
                "limits may only narrow the published profile ceilings",
                None,
                0,
            ));
        }
        Ok(())
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Error {
    pub code: &'static str,
    pub message: String,
    pub function: Option<u32>,
    pub offset: usize,
}
impl Error {
    pub fn new(
        code: &'static str,
        message: impl Into<String>,
        function: Option<u32>,
        offset: usize,
    ) -> Self {
        Self {
            code,
            message: message.into(),
            function,
            offset,
        }
    }
    pub fn json(&self) -> String {
        format!(
            "{{\"code\":{},\"message\":{},\"function\":{},\"offset\":{}}}",
            json_string(self.code),
            json_string(&self.message),
            self.function
                .map(|v| v.to_string())
                .unwrap_or_else(|| "null".into()),
            self.offset
        )
    }
}
impl std::fmt::Display for Error {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{} at byte {}: {}", self.code, self.offset, self.message)
    }
}
impl std::error::Error for Error {}
pub fn json_string(s: &str) -> String {
    let mut out = String::from("\"");
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if c < ' ' => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct Signature {
    pub params: Vec<Type>,
    pub result: Option<Type>,
}
#[derive(Clone, Debug)]
pub(crate) struct Function {
    pub type_index: u32,
    pub locals: Vec<Type>,
    pub code: Vec<Instruction>,
    pub offset: usize,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum BlockKind {
    Block,
    Loop,
    If,
    Function,
}
#[derive(Clone, Debug)]
pub(crate) enum Op {
    Unreachable,
    Nop,
    Block {
        kind: BlockKind,
        result: Option<Type>,
        end: usize,
        alternative: Option<usize>,
    },
    Else {
        end: usize,
    },
    End,
    Br(u32),
    BrIf(u32),
    BrTable(Vec<u32>, u32),
    Return,
    Call(u32),
    CallIndirect(u32),
    MemoryCopy,
    MemoryFill,
    Drop,
    Select,
    LocalGet(u32),
    LocalSet(u32),
    LocalTee(u32),
    GlobalGet(u32),
    GlobalSet(u32),
    Load {
        opcode: u8,
        offset: u32,
    },
    Store {
        opcode: u8,
        offset: u32,
    },
    MemorySize,
    MemoryGrow,
    Const(Value),
    Numeric(u8),
    Saturating(u8),
}
#[derive(Clone, Debug)]
pub(crate) struct Instruction {
    pub op: Op,
    pub offset: usize,
}
#[derive(Clone, Debug)]
pub(crate) struct Global {
    pub value: Value,
    pub mutable: bool,
}
#[derive(Clone, Debug)]
pub(crate) struct Import {
    pub module: String,
    pub name: String,
    pub type_index: u32,
}
