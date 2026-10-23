//! Owned execution of a sealed, lazily decoded snapshot. Rust experiment only.
//! Mutable arenas are reserved once; dispatch never grows a host collection.
//!
//! Execution requires ownership of a sealed cache, never raw bytes:
//! ```compile_fail
//! use mixer_vm::{Cancellation};
//! use mixer_vm::experimental::execution::{SpanInstance, ExecutionBudget};
//! let _ = SpanInstance::new(b"\0asm\x01\0\0\0", ExecutionBudget::default(), Cancellation::default());
//! ```
//! The owned cache and mutable memory are not public authority escapes:
//! ```compile_fail
//! use mixer_vm::experimental::execution::SpanInstance;
//! fn modify(instance: &mut SpanInstance) { instance.memory()[0] = 1; }
//! ```
//! ```compile_fail
//! use mixer_vm::experimental::execution::SpanInstance;
//! fn take(instance: &mut SpanInstance) { let _ = instance.cache_usage().pin(0); }
//! ```
#![allow(clippy::result_large_err)]
#[cfg_attr(not(feature = "experimental-span-execution"), allow(unused_imports))]
use super::cache::{CacheFailure, CacheUsage, ControlKind, FunctionCache, FunctionPin, Operation};
use crate::{Cancellation, Value};
#[cfg(feature = "experimental-span-execution")]
use std::mem::size_of;

#[cfg_attr(not(feature = "experimental-span-execution"), allow(dead_code))]
const PAGE: usize = 65536;
#[cfg_attr(not(feature = "experimental-span-execution"), allow(dead_code))]
const CHUNK: usize = 4096;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ExecutionBudget {
    pub state_bytes: usize,
    pub live_values: usize,
    pub live_controls: usize,
    pub work_credits: u64,
}
impl Default for ExecutionBudget {
    fn default() -> Self {
        Self {
            state_bytes: 16 * 1024 * 1024,
            live_values: 16384,
            live_controls: 4096,
            work_credits: 64_000_000,
        }
    }
}
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct ExecutionUsage {
    pub state_reserved: usize,
    pub peak_state_reserved: usize,
    pub source_bytes: usize,
    pub validation_metadata_bytes: usize,
    pub validation_work_used: u64,
    pub instructions: u64,
    /// Includes the frozen interpreter's extra bulk-memory fuel.
    pub fuel_used: u64,
    pub host_calls: u64,
    pub work_used: u64,
    pub frames: usize,
    pub peak_frames: usize,
    /// All live locals and operands together, across every frame.
    pub live_values: usize,
    pub peak_live_values: usize,
    pub live_controls: usize,
    pub peak_live_controls: usize,
    pub memory_pages: u32,
    pub active_pins: usize,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[cfg_attr(not(feature = "experimental-span-execution"), allow(dead_code))]
pub enum ExecutionFailureKind {
    InvalidBudget,
    UnknownExport,
    InvalidArguments,
    Cancelled,
    StateExhausted,
    ValueExhausted,
    ControlExhausted,
    WorkExhausted,
    FuelExhausted,
    HostCallLimit,
    CallDepthExceeded,
    AllocationFailure,
    Cache,
    GuestTrap,
    UnsupportedEnvironment,
    Invariant,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ExecutionFailure {
    pub kind: ExecutionFailureKind,
    pub code: &'static str,
    pub function: Option<u32>,
    pub offset: usize,
    pub attempted: u64,
    pub limit: u64,
    pub usage: ExecutionUsage,
    pub cache_failure: Option<CacheFailure>,
}
impl std::fmt::Display for ExecutionFailure {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{} at byte {}", self.code, self.offset)
    }
}
impl std::error::Error for ExecutionFailure {}

#[derive(Clone, Copy, PartialEq, Eq)]
#[cfg_attr(not(feature = "experimental-span-execution"), allow(dead_code))]
enum Kind {
    Function,
    Block,
    Loop,
    If,
}
#[derive(Clone, Copy)]
#[cfg_attr(not(feature = "experimental-span-execution"), allow(dead_code))]
pub(crate) struct Control {
    kind: Kind,
    start: usize,
    end: usize,
    height: usize,
    result: bool,
}
#[cfg_attr(not(feature = "experimental-span-execution"), allow(dead_code))]
pub(crate) struct Frame {
    function: u32,
    pc: usize,
    base: usize,
    operands: usize,
    controls: usize,
    result: bool,
    pin: FunctionPin,
}
/// Owns the cache; neither cache pins nor mutable guest storage escape this owner.
/// Fuel, host calls and work accumulate for the lifetime. Every error is terminal.
#[cfg_attr(not(feature = "experimental-span-execution"), allow(dead_code))]
pub struct SpanInstance {
    cache: FunctionCache,
    budget: ExecutionBudget,
    cancellation: Cancellation,
    usage: ExecutionUsage,
    failure: Option<ExecutionFailure>,
    memory: Vec<u8>,
    table: Vec<Option<u32>>,
    globals: Vec<Value>,
    values: Vec<Value>,
    controls: Vec<Control>,
    frames: Vec<Frame>,
    function: Option<u32>,
    offset: usize,
}
#[cfg(feature = "experimental-span-execution")]
impl SpanInstance {
    pub fn new(
        cache: FunctionCache,
        budget: ExecutionBudget,
        cancellation: Cancellation,
    ) -> Result<Self, ExecutionFailure> {
        let validation = cache.spans().usage();
        let usage = ExecutionUsage {
            source_bytes: validation.source_bytes,
            validation_metadata_bytes: validation.metadata_reserved,
            validation_work_used: validation.work_used,
            ..ExecutionUsage::default()
        };
        let mut this = Self {
            cache,
            budget,
            cancellation,
            usage,
            failure: None,
            memory: Vec::new(),
            table: Vec::new(),
            globals: Vec::new(),
            values: Vec::new(),
            controls: Vec::new(),
            frames: Vec::new(),
            function: None,
            offset: 0,
        };
        let result = this.initialize();
        if let Err(mut error) = result {
            this.cleanup();
            // Construction returns no live owner: all mutable reservations drop.
            this.usage.state_reserved = 0;
            this.usage.memory_pages = 0;
            this.usage.active_pins = 0;
            error.usage = this.usage;
            return Err(error);
        }
        Ok(this)
    }
    pub fn memory(&self) -> &[u8] {
        &self.memory
    }
    pub fn usage(&self) -> ExecutionUsage {
        self.usage
    }
    pub fn cache_usage(&self) -> CacheUsage {
        self.cache.usage()
    }
    pub fn cancellation(&self) -> Cancellation {
        self.cancellation.clone()
    }
    fn error(
        &self,
        kind: ExecutionFailureKind,
        code: &'static str,
        attempted: u64,
        limit: u64,
    ) -> ExecutionFailure {
        ExecutionFailure {
            kind,
            code,
            function: self.function,
            offset: self.offset,
            attempted,
            limit,
            usage: self.usage,
            cache_failure: None,
        }
    }
    fn invariant(&self) -> ExecutionFailure {
        self.error(ExecutionFailureKind::Invariant, "execution_invariant", 0, 0)
    }
    fn trap(&self, code: &'static str) -> ExecutionFailure {
        self.error(ExecutionFailureKind::GuestTrap, code, 0, 0)
    }
    fn check(&self) -> Result<(), ExecutionFailure> {
        if self.cancellation.is_cancelled() {
            Err(self.error(ExecutionFailureKind::Cancelled, "cancelled", 0, 0))
        } else {
            Ok(())
        }
    }
    fn work(&mut self, amount: usize) -> Result<(), ExecutionFailure> {
        self.check()?;
        let next = self
            .usage
            .work_used
            .checked_add(amount as u64)
            .ok_or_else(|| {
                self.error(
                    ExecutionFailureKind::WorkExhausted,
                    "work_overflow",
                    u64::MAX,
                    self.budget.work_credits,
                )
            })?;
        if next > self.budget.work_credits {
            return Err(self.error(
                ExecutionFailureKind::WorkExhausted,
                "execution_work",
                next,
                self.budget.work_credits,
            ));
        }
        self.usage.work_used = next;
        Ok(())
    }
    fn reserve(&mut self, bytes: usize) -> Result<(), ExecutionFailure> {
        self.check()?;
        let next = self
            .usage
            .state_reserved
            .checked_add(bytes)
            .ok_or_else(|| {
                self.error(
                    ExecutionFailureKind::StateExhausted,
                    "state_overflow",
                    u64::MAX,
                    self.budget.state_bytes as u64,
                )
            })?;
        if next > self.budget.state_bytes {
            return Err(self.error(
                ExecutionFailureKind::StateExhausted,
                "state_bytes",
                next as u64,
                self.budget.state_bytes as u64,
            ));
        }
        self.usage.state_reserved = next;
        self.usage.peak_state_reserved = self.usage.peak_state_reserved.max(next);
        Ok(())
    }
    fn allocation<T>(&mut self, capacity: usize) -> Result<Vec<T>, ExecutionFailure> {
        let bytes = capacity.checked_mul(size_of::<T>()).ok_or_else(|| {
            self.error(
                ExecutionFailureKind::StateExhausted,
                "capacity_overflow",
                u64::MAX,
                self.budget.state_bytes as u64,
            )
        })?;
        self.reserve(bytes)?;
        let mut vec = Vec::new();
        if vec.try_reserve_exact(capacity).is_err() {
            self.usage.state_reserved -= bytes;
            return Err(self.error(
                ExecutionFailureKind::AllocationFailure,
                "state_allocation",
                capacity as u64,
                0,
            ));
        }
        if vec.capacity() != capacity {
            self.usage.state_reserved -= bytes;
            return Err(self.error(
                ExecutionFailureKind::AllocationFailure,
                "state_capacity",
                vec.capacity() as u64,
                capacity as u64,
            ));
        }
        Ok(vec)
    }
    fn initialize(&mut self) -> Result<(), ExecutionFailure> {
        let d = ExecutionBudget::default();
        if self.budget.state_bytes > d.state_bytes
            || self.budget.live_values > d.live_values
            || self.budget.live_controls > d.live_controls
            || self.budget.work_credits > d.work_credits
        {
            return Err(self.error(
                ExecutionFailureKind::InvalidBudget,
                "invalid_execution_budget",
                0,
                0,
            ));
        }
        self.check()?;
        if self.cache.usage().active_pins != 0 {
            return Err(self.error(
                ExecutionFailureKind::Invariant,
                "preexisting_cache_pins",
                self.cache.usage().active_pins as u64,
                0,
            ));
        }
        // Cache state is accounted separately. Fixed stack scratch includes scalar
        // instruction copies, initializer decoding and bounded copy temporaries.
        self.reserve(
            size_of::<Self>() - size_of::<FunctionCache>()
                + 3 * size_of::<ExecutionFailure>()
                + 2 * size_of::<CacheFailure>()
                + size_of::<super::cache::DecodedInstruction>()
                + size_of::<Control>()
                + size_of::<ScalarReader<'_>>()
                + 512,
        )?;
        self.values = self.allocation(self.budget.live_values)?;
        self.controls = self.allocation(self.budget.live_controls)?;
        self.frames = self.allocation(self.cache.spans().limits().call_depth)?;
        let bytes = self
            .cache
            .spans()
            .execution_memory()
            .map_or(0, |m| m.0 as usize * PAGE);
        let table = self
            .cache
            .spans()
            .execution_table()
            .map_or(0, |t| t.0 as usize);
        let globals = self.cache.spans().execution_global_count();
        self.memory = self.allocation(bytes)?;
        self.table = self.allocation(table)?;
        self.globals = self.allocation(globals)?;
        self.work(
            bytes
                .checked_add(table)
                .and_then(|v| v.checked_add(globals))
                .ok_or_else(|| self.invariant())?,
        )?;
        for end in (0..bytes).step_by(CHUNK) {
            self.check()?;
            self.memory.resize((end + CHUNK).min(bytes), 0);
        }
        for _ in 0..table {
            self.check()?;
            self.table.push(None);
        }
        for index in 0..globals {
            self.work(16)?;
            let global = self
                .cache
                .spans()
                .execution_global(index)
                .ok_or_else(|| self.invariant())?;
            let value = initializer(global.initializer)
                .filter(|v| v.ty() == global.ty)
                .ok_or_else(|| self.invariant())?;
            self.globals.push(value);
        }
        // Check every segment before copying any active payload.
        for index in 0..self.cache.spans().execution_data_count() {
            self.work(1)?;
            let segment = self
                .cache
                .spans()
                .data_segment(index)
                .ok_or_else(|| self.invariant())?;
            if (segment.destination as usize)
                .checked_add(segment.count as usize)
                .is_none_or(|end| end > bytes)
            {
                return Err(self.trap("memory_out_of_bounds"));
            }
        }
        for index in 0..self.cache.spans().execution_element_count() {
            self.work(1)?;
            let segment = self
                .cache
                .spans()
                .element_segment(index)
                .ok_or_else(|| self.invariant())?;
            if (segment.destination as usize)
                .checked_add(segment.count as usize)
                .is_none_or(|end| end > table)
            {
                return Err(self.trap("table_out_of_bounds"));
            }
        }
        for index in 0..self.cache.spans().execution_data_count() {
            let len = self
                .cache
                .spans()
                .data_segment(index)
                .ok_or_else(|| self.invariant())?
                .count as usize;
            self.work(len)?;
            let segment = self
                .cache
                .spans()
                .data_segment(index)
                .ok_or_else(|| self.invariant())?;
            for (part, data) in segment.encoded_payload.chunks(CHUNK).enumerate() {
                if self.cancellation.is_cancelled() {
                    return Err(self.error(ExecutionFailureKind::Cancelled, "cancelled", 0, 0));
                }
                let start = segment.destination as usize + part * CHUNK;
                self.memory[start..start + data.len()].copy_from_slice(data);
            }
        }
        for index in 0..self.cache.spans().execution_element_count() {
            let len = self
                .cache
                .spans()
                .element_segment(index)
                .ok_or_else(|| self.invariant())?
                .encoded_payload
                .len();
            self.work(len)?;
            let segment = self
                .cache
                .spans()
                .element_segment(index)
                .ok_or_else(|| self.invariant())?;
            let mut reader = ScalarReader {
                bytes: segment.encoded_payload,
                at: 0,
            };
            for slot in 0..segment.count as usize {
                if self.cancellation.is_cancelled() {
                    return Err(self.error(ExecutionFailureKind::Cancelled, "cancelled", 0, 0));
                }
                let function = reader.uint().ok_or_else(|| self.invariant())?;
                self.table[segment.destination as usize + slot] = Some(function);
            }
        }
        self.usage.memory_pages = (bytes / PAGE) as u32;
        self.check()
    }
    fn observe(&mut self) {
        self.usage.frames = self.frames.len();
        self.usage.peak_frames = self.usage.peak_frames.max(self.frames.len());
        self.usage.live_values = self.values.len();
        self.usage.peak_live_values = self.usage.peak_live_values.max(self.values.len());
        self.usage.live_controls = self.controls.len();
        self.usage.peak_live_controls = self.usage.peak_live_controls.max(self.controls.len());
        self.usage.active_pins = self.cache.usage().active_pins;
    }
    fn cleanup(&mut self) {
        while let Some(frame) = self.frames.pop() {
            // Tokens are private, owned once, and always returned to their owner.
            // release performs neither allocation, decoding nor metering.
            let _ = self.cache.release(frame.pin);
        }
        self.values.clear();
        self.controls.clear();
        self.observe();
    }
    fn terminal(&mut self, mut error: ExecutionFailure) -> ExecutionFailure {
        self.cleanup();
        error.usage = self.usage;
        if let Some(cache_error) = &mut error.cache_failure {
            cache_error.usage = self.cache.usage();
        }
        self.failure = Some(error);
        error
    }
    fn cache_error(&self, error: CacheFailure) -> ExecutionFailure {
        let mut failure = self.error(
            ExecutionFailureKind::Cache,
            error.code,
            error.attempted,
            error.limit,
        );
        if self.function.is_none() {
            failure.function = error.function;
            failure.offset = error.offset;
        }
        failure.cache_failure = Some(error);
        failure
    }
    fn room_values(&self, additional: usize) -> Result<(), ExecutionFailure> {
        let next = self
            .values
            .len()
            .checked_add(additional)
            .ok_or_else(|| self.invariant())?;
        if next > self.budget.live_values {
            return Err(self.error(
                ExecutionFailureKind::ValueExhausted,
                "live_values",
                next as u64,
                self.budget.live_values as u64,
            ));
        }
        Ok(())
    }
    fn room_control(&self) -> Result<(), ExecutionFailure> {
        if self.controls.len() == self.budget.live_controls {
            return Err(self.error(
                ExecutionFailureKind::ControlExhausted,
                "live_controls",
                self.controls.len() as u64 + 1,
                self.budget.live_controls as u64,
            ));
        }
        Ok(())
    }
    fn push(&mut self, value: Value) -> Result<(), ExecutionFailure> {
        self.work(1)?;
        self.room_values(1)?;
        if let Some(frame) = self.frames.last() {
            if self.values.len() - frame.operands >= self.cache.spans().limits().operand_stack {
                return Err(self.error(
                    ExecutionFailureKind::ValueExhausted,
                    "operand_stack_exceeded",
                    (self.values.len() - frame.operands + 1) as u64,
                    self.cache.spans().limits().operand_stack as u64,
                ));
            }
        }
        self.values.push(value);
        self.observe();
        Ok(())
    }
    fn pop(&mut self) -> Result<Value, ExecutionFailure> {
        self.work(1)?;
        let base = self.frames.last().map_or(0, |f| f.operands);
        if self.values.len() <= base {
            return Err(self.invariant());
        }
        let value = self.values.pop().ok_or_else(|| self.invariant())?;
        self.observe();
        Ok(value)
    }
    fn pop32(&mut self) -> Result<i32, ExecutionFailure> {
        match self.pop()? {
            Value::I32(value) => Ok(value),
            _ => Err(self.invariant()),
        }
    }
    fn charge(&mut self, amount: u64, instruction: bool) -> Result<(), ExecutionFailure> {
        self.check()?;
        let limit = self.cache.spans().limits().fuel;
        let next = self
            .usage
            .fuel_used
            .checked_add(amount)
            .ok_or_else(|| self.invariant())?;
        if next > limit {
            self.usage.fuel_used = limit;
            return Err(self.error(
                ExecutionFailureKind::FuelExhausted,
                "fuel_exhausted",
                next,
                limit,
            ));
        }
        self.usage.fuel_used = next;
        if instruction {
            self.usage.instructions += 1;
        }
        Ok(())
    }
    pub fn invoke(
        &mut self,
        name: &str,
        args: &[Value],
    ) -> Result<Option<Value>, ExecutionFailure> {
        if let Some(error) = self.failure {
            return Err(error);
        }
        self.function = None;
        self.offset = 0;
        match self.invoke_inner(name, args) {
            Ok(value) => Ok(value),
            Err(error) => Err(self.terminal(error)),
        }
    }
    fn invoke_inner(
        &mut self,
        name: &str,
        args: &[Value],
    ) -> Result<Option<Value>, ExecutionFailure> {
        self.check()?;
        let exports = self.cache.spans().execution_export_count();
        self.work(
            name.len()
                .checked_mul(exports)
                .and_then(|n| n.checked_add(exports))
                .ok_or_else(|| self.invariant())?,
        )?;
        if self.cache.spans().profile().floats() {
            crate::float::environment_check().map_err(|_| {
                self.error(
                    ExecutionFailureKind::UnsupportedEnvironment,
                    "unsupported_float_environment",
                    0,
                    0,
                )
            })?;
        }
        let (kind, function) = self.cache.spans().execution_export(name).ok_or_else(|| {
            self.error(ExecutionFailureKind::UnknownExport, "unknown_export", 0, 0)
        })?;
        if kind != 0 {
            return Err(self.error(
                ExecutionFailureKind::InvalidArguments,
                "invalid_arguments",
                0,
                0,
            ));
        }
        self.function = Some(function);
        self.work(args.len())?;
        let sig = self
            .cache
            .spans()
            .execution_signature(function)
            .ok_or_else(|| self.invariant())?;
        if args.len() != sig.params.len() || args.iter().zip(sig.params).any(|(a, t)| a.ty() != *t)
        {
            return Err(self.error(
                ExecutionFailureKind::InvalidArguments,
                "invalid_arguments",
                args.len() as u64,
                sig.params.len() as u64,
            ));
        }
        if self.cache.spans().execution_import(function).is_some() {
            self.charge(1, true)?;
            return self.import(function);
        }
        self.room_values(args.len())?;
        self.values.extend_from_slice(args);
        self.observe();
        self.enter(function)?;
        self.run()
    }
    fn enter(&mut self, function: u32) -> Result<(), ExecutionFailure> {
        if self.frames.len() >= self.cache.spans().limits().call_depth {
            return Err(self.error(
                ExecutionFailureKind::CallDepthExceeded,
                "call_depth_exceeded",
                self.frames.len() as u64 + 1,
                self.cache.spans().limits().call_depth as u64,
            ));
        }
        self.work(1)?;
        let sig = self
            .cache
            .spans()
            .execution_signature(function)
            .ok_or_else(|| self.invariant())?;
        let params = sig.params.len();
        let result = sig.result.is_some();
        let pin = self
            .cache
            .pin(function, &self.cancellation)
            .map_err(|error| self.cache_error(error))?;
        let build = (|| {
            let view = self
                .cache
                .view(&pin)
                .map_err(|error| self.cache_error(error))?;
            let locals = view.locals.len();
            let end = view
                .instructions
                .len()
                .checked_sub(1)
                .ok_or_else(|| self.invariant())?;
            let base = self
                .values
                .len()
                .checked_sub(params)
                .ok_or_else(|| self.invariant())?;
            self.room_values(locals)?;
            self.room_control()?;
            self.work(locals.checked_add(1).ok_or_else(|| self.invariant())?)?;
            let view = self
                .cache
                .view(&pin)
                .map_err(|error| self.cache_error(error))?;
            for ty in view.locals {
                self.values.push(Value::zero(*ty));
            }
            let operands = self.values.len();
            let controls = self.controls.len();
            self.controls.push(Control {
                kind: Kind::Function,
                start: 0,
                end,
                height: operands,
                result,
            });
            Ok((base, operands, controls, result))
        })();
        match build {
            Ok((base, operands, controls, result)) => {
                self.frames.push(Frame {
                    function,
                    pc: 0,
                    base,
                    operands,
                    controls,
                    result,
                    pin,
                });
                self.observe();
                Ok(())
            }
            Err(error) => {
                let _ = self.cache.release(pin);
                Err(error)
            }
        }
    }
    fn import(&mut self, function: u32) -> Result<Option<Value>, ExecutionFailure> {
        self.check()?;
        self.work(1)?;
        let limit = self.cache.spans().limits().host_calls;
        if self.usage.host_calls >= limit {
            return Err(self.error(
                ExecutionFailureKind::HostCallLimit,
                "host_call_limit",
                self.usage.host_calls + 1,
                limit,
            ));
        }
        self.usage.host_calls += 1;
        let import = self
            .cache
            .spans()
            .execution_import(function)
            .ok_or_else(|| self.invariant())?;
        if import.module != b"mixer" {
            return Err(self.invariant());
        }
        match import.name {
            b"checkpoint" => Ok(None),
            b"abort" => Err(self.trap("host_abort")),
            _ => Err(self.invariant()),
        }
    }
    fn call(&mut self, function: u32) -> Result<(), ExecutionFailure> {
        let params = self
            .cache
            .spans()
            .execution_signature(function)
            .ok_or_else(|| self.invariant())?
            .params
            .len();
        self.work(params)?;
        let base = self
            .values
            .len()
            .checked_sub(params)
            .ok_or_else(|| self.invariant())?;
        let frame = self.frames.last().ok_or_else(|| self.invariant())?;
        if base < frame.operands {
            return Err(self.invariant());
        }
        if self.cache.spans().execution_import(function).is_some() {
            // The Call instruction was already charged, exactly as in eager.
            let value = self.import(function)?;
            self.values.truncate(base);
            self.observe();
            if let Some(value) = value {
                self.push(value)?;
            }
            Ok(())
        } else {
            self.enter(function)
        }
    }
    fn close_control(&mut self, control: Control) -> Result<(), ExecutionFailure> {
        let value = if control.result {
            Some(self.pop()?)
        } else {
            None
        };
        if control.height > self.values.len() {
            return Err(self.invariant());
        }
        self.work(self.values.len() - control.height + 1)?;
        self.values.truncate(control.height);
        self.observe();
        if let Some(value) = value {
            self.push(value)?;
        }
        Ok(())
    }
    fn branch(&mut self, depth: u32) -> Result<bool, ExecutionFailure> {
        let frame = self.frames.last().ok_or_else(|| self.invariant())?;
        let index = self
            .controls
            .len()
            .checked_sub(depth as usize + 1)
            .filter(|i| *i >= frame.controls)
            .ok_or_else(|| self.invariant())?;
        let mut control = self.controls[index];
        self.work(self.controls.len() - index)?;
        if control.kind == Kind::Loop {
            control.result = false;
        }
        self.close_control(control)?;
        self.controls.truncate(if control.kind == Kind::Loop {
            index + 1
        } else {
            index
        });
        let pc = if control.kind == Kind::Loop {
            control.start
        } else {
            control.end + 1
        };
        self.frames.last_mut().ok_or_else(unreachable_failure)?.pc = pc;
        self.observe();
        Ok(control.kind == Kind::Function)
    }
    fn finish(&mut self) -> Result<Option<Value>, ExecutionFailure> {
        let result = self.frames.last().ok_or_else(|| self.invariant())?.result;
        let value = if result { Some(self.pop()?) } else { None };
        let base = self.frames.last().ok_or_else(|| self.invariant())?.base;
        let controls = self.frames.last().ok_or_else(|| self.invariant())?.controls;
        self.work(self.values.len() - base + self.controls.len() - controls + 1)?;
        let frame = self.frames.pop().ok_or_else(|| self.invariant())?;
        self.values.truncate(base);
        self.controls.truncate(controls);
        self.cache
            .release(frame.pin)
            .map_err(|error| self.cache_error(error.failure))?;
        self.observe();
        if !self.frames.is_empty() {
            if let Some(value) = value {
                self.push(value)?;
            }
        }
        Ok(value)
    }
    fn run(&mut self) -> Result<Option<Value>, ExecutionFailure> {
        loop {
            let frame = self.frames.last().ok_or_else(|| self.invariant())?;
            let view = self
                .cache
                .view(&frame.pin)
                .map_err(|error| self.cache_error(error))?;
            let instruction = *view
                .instructions
                .get(frame.pc)
                .ok_or_else(|| self.invariant())?;
            // Copy one selected br_table scalar before ending the cache borrow.
            let target = if let Operation::BrTable {
                first,
                count,
                default,
            } = instruction.operation
            {
                let selector = match self.values.last() {
                    Some(Value::I32(n)) => *n as u32 as usize,
                    _ => return Err(self.invariant()),
                };
                Some(if selector < count {
                    *view
                        .branch_targets
                        .get(first + selector)
                        .ok_or_else(|| self.invariant())?
                } else {
                    default
                })
            } else {
                None
            };
            self.function = Some(frame.function);
            self.offset = instruction.offset;
            self.charge(1, true)?;
            self.work(1)?;
            self.frames.last_mut().ok_or_else(unreachable_failure)?.pc += 1;
            let mut finished = false;
            match instruction.operation {
                Operation::Unreachable => return Err(self.trap("unreachable")),
                Operation::Nop => {}
                Operation::Const(value) => self.push(value)?,
                Operation::Drop => {
                    self.pop()?;
                }
                Operation::Select => {
                    let cond = self.pop32()?;
                    let b = self.pop()?;
                    let a = self.pop()?;
                    self.push(if cond != 0 { a } else { b })?;
                }
                Operation::LocalGet(index) => {
                    let frame = self.frames.last().ok_or_else(|| self.invariant())?;
                    let value = *self
                        .values
                        .get(frame.base + index as usize)
                        .filter(|_| frame.base + (index as usize) < frame.operands)
                        .ok_or_else(|| self.invariant())?;
                    self.push(value)?;
                }
                Operation::LocalSet(index) | Operation::LocalTee(index) => {
                    let value = if matches!(instruction.operation, Operation::LocalTee(_)) {
                        self.work(1)?;
                        *self.values.last().ok_or_else(|| self.invariant())?
                    } else {
                        self.pop()?
                    };
                    let frame = self.frames.last().ok_or_else(|| self.invariant())?;
                    let slot = frame.base + index as usize;
                    if slot >= frame.operands {
                        return Err(self.invariant());
                    }
                    self.values[slot] = value;
                }
                Operation::GlobalGet(index) => {
                    let value = *self
                        .globals
                        .get(index as usize)
                        .ok_or_else(|| self.invariant())?;
                    self.push(value)?;
                }
                Operation::GlobalSet(index) => {
                    let value = self.pop()?;
                    let desc = self
                        .cache
                        .spans()
                        .execution_global(index as usize)
                        .ok_or_else(|| self.invariant())?;
                    if !desc.mutable || value.ty() != desc.ty {
                        return Err(self.invariant());
                    }
                    self.globals[index as usize] = value;
                }
                Operation::Block {
                    kind,
                    result,
                    end,
                    alternative,
                } => {
                    let cond = if kind == ControlKind::If {
                        self.pop32()? != 0
                    } else {
                        true
                    };
                    self.room_control()?;
                    self.work(1)?;
                    let frame = self.frames.last().ok_or_else(|| self.invariant())?;
                    if self.controls.len() - frame.controls
                        >= self.cache.spans().limits().control_depth
                    {
                        return Err(self.error(
                            ExecutionFailureKind::ControlExhausted,
                            "control_depth_exceeded",
                            (self.controls.len() - frame.controls + 1) as u64,
                            self.cache.spans().limits().control_depth as u64,
                        ));
                    }
                    self.controls.push(Control {
                        kind: match kind {
                            ControlKind::Block => Kind::Block,
                            ControlKind::Loop => Kind::Loop,
                            ControlKind::If => Kind::If,
                        },
                        start: frame.pc,
                        end,
                        height: self.values.len(),
                        result: result.is_some(),
                    });
                    if !cond {
                        self.frames.last_mut().ok_or_else(unreachable_failure)?.pc =
                            alternative.map_or(end, |v| v + 1);
                    }
                    self.observe();
                }
                Operation::Else { end } => {
                    self.frames.last_mut().ok_or_else(unreachable_failure)?.pc = end
                }
                Operation::End => {
                    self.work(1)?;
                    let control = self.controls.pop().ok_or_else(|| self.invariant())?;
                    self.close_control(control)?;
                    finished = control.kind == Kind::Function;
                    self.observe();
                }
                Operation::Br(depth) => finished = self.branch(depth)?,
                Operation::BrIf(depth) => {
                    if self.pop32()? != 0 {
                        finished = self.branch(depth)?;
                    }
                }
                Operation::BrTable { .. } => {
                    self.pop32()?;
                    finished = self.branch(target.ok_or_else(|| self.invariant())?)?;
                }
                Operation::Return => finished = true,
                Operation::Call(function) => self.call(function)?,
                Operation::CallIndirect(index) => {
                    let selector = self.pop32()? as u32 as usize;
                    let function = self
                        .table
                        .get(selector)
                        .ok_or_else(|| self.trap("table_out_of_bounds"))?
                        .ok_or_else(|| self.trap("indirect_call_null"))?;
                    let expected = self
                        .cache
                        .spans()
                        .execution_type(index)
                        .ok_or_else(|| self.invariant())?;
                    let actual = self
                        .cache
                        .spans()
                        .execution_signature(function)
                        .ok_or_else(|| self.invariant())?;
                    let scan = expected
                        .params
                        .len()
                        .checked_add(actual.params.len())
                        .ok_or_else(|| self.invariant())?;
                    self.work(scan)?;
                    if self.cache.spans().execution_type(index)
                        != self.cache.spans().execution_signature(function)
                    {
                        return Err(self.trap("indirect_call_type_mismatch"));
                    }
                    self.call(function)?;
                }
                Operation::MemorySize => self.push(Value::I32(self.usage.memory_pages as i32))?,
                Operation::MemoryGrow => self.grow()?,
                Operation::MemoryCopy => self.copy()?,
                Operation::MemoryFill => self.fill()?,
                Operation::Load { opcode, offset } => self.load(opcode, offset)?,
                Operation::Store { opcode, offset } => self.store(opcode, offset)?,
                Operation::Numeric(opcode) => self.numeric(opcode, false)?,
                Operation::Saturating(opcode) => self.numeric(opcode, true)?,
            }
            if finished {
                let result = self.finish()?;
                if self.frames.is_empty() {
                    return Ok(result);
                }
            }
        }
    }
    fn numeric(&mut self, opcode: u8, saturating: bool) -> Result<(), ExecutionFailure> {
        let (ty, count, _) = if saturating {
            let (a, b) = crate::float::saturating_shape(opcode);
            (a, 1, b)
        } else {
            crate::float::shape(opcode).unwrap_or_else(|| crate::validate::numeric_type(opcode))
        };
        let frame = self.frames.last().ok_or_else(|| self.invariant())?;
        if self.values.len() - frame.operands < count
            || self.values[self.values.len() - count..]
                .iter()
                .any(|v| v.ty() != ty)
        {
            return Err(self.invariant());
        }
        // Every numeric helper consumes at least one value and emits exactly one.
        // Existing capacity therefore covers its only push, including traps.
        self.work(count + 1)?;
        let result = if saturating {
            crate::float::saturating(opcode, &mut self.values);
            Ok(())
        } else if crate::float::shape(opcode).is_some() {
            crate::float::numeric(opcode, &mut self.values)
        } else {
            crate::execute::numeric(opcode, &mut self.values)
        };
        self.observe();
        result.map_err(|code| self.trap(code))
    }
    fn range(
        &self,
        address: usize,
        len: usize,
    ) -> Result<std::ops::Range<usize>, ExecutionFailure> {
        let end = address
            .checked_add(len)
            .filter(|end| *end <= self.memory.len())
            .ok_or_else(|| self.trap("memory_out_of_bounds"))?;
        Ok(address..end)
    }
    fn bulk(&mut self, len: usize) -> Result<(), ExecutionFailure> {
        self.charge(len.div_ceil(64) as u64, false)?;
        self.work(len)
    }
    fn copy(&mut self) -> Result<(), ExecutionFailure> {
        let len = self.pop32()? as u32 as usize;
        let src = self.pop32()? as u32 as usize;
        let dst = self.pop32()? as u32 as usize;
        self.range(src, len)?;
        self.range(dst, len)?;
        self.bulk(len)?;
        if dst > src {
            let mut left = len;
            while left != 0 {
                self.check()?;
                let n = left.min(CHUNK);
                left -= n;
                self.memory
                    .copy_within(src + left..src + left + n, dst + left);
            }
        } else {
            for at in (0..len).step_by(CHUNK) {
                self.check()?;
                let n = (len - at).min(CHUNK);
                self.memory.copy_within(src + at..src + at + n, dst + at);
            }
        }
        Ok(())
    }
    fn fill(&mut self) -> Result<(), ExecutionFailure> {
        let len = self.pop32()? as u32 as usize;
        let value = self.pop32()? as u8;
        let dst = self.pop32()? as u32 as usize;
        let range = self.range(dst, len)?;
        self.bulk(len)?;
        for start in (range.start..range.end).step_by(CHUNK) {
            self.check()?;
            let end = (start + CHUNK).min(range.end);
            self.memory[start..end].fill(value);
        }
        Ok(())
    }
    fn grow(&mut self) -> Result<(), ExecutionFailure> {
        let delta = self.pop32()? as u32;
        let old = self.usage.memory_pages;
        let maximum = self
            .cache
            .spans()
            .execution_memory()
            .ok_or_else(|| self.invariant())?
            .1
            .min(self.cache.spans().limits().memory_pages);
        let Some(next) = old.checked_add(delta).filter(|next| *next <= maximum) else {
            return self.push(Value::I32(-1));
        };
        if delta == 0 {
            return self.push(Value::I32(old as i32));
        }
        let bytes = (next as usize)
            .checked_mul(PAGE)
            .ok_or_else(|| self.invariant())?;
        self.work(
            bytes
                .checked_add(self.memory.len())
                .ok_or_else(|| self.invariant())?,
        )?;
        let mut memory = self.allocation(bytes)?;
        let result = (|| {
            for at in (0..bytes).step_by(CHUNK) {
                self.check()?;
                memory.resize((at + CHUNK).min(bytes), 0);
            }
            for at in (0..self.memory.len()).step_by(CHUNK) {
                self.check()?;
                let end = (at + CHUNK).min(self.memory.len());
                memory[at..end].copy_from_slice(&self.memory[at..end]);
            }
            self.check()
        })();
        if let Err(error) = result {
            drop(memory);
            self.usage.state_reserved -= bytes;
            return Err(error);
        }
        let old_bytes = self.memory.len();
        self.memory = memory;
        self.usage.state_reserved -= old_bytes;
        self.usage.memory_pages = next;
        self.push(Value::I32(old as i32))
    }
    fn load(&mut self, opcode: u8, offset: u32) -> Result<(), ExecutionFailure> {
        let address = self.pop32()? as u32 as usize;
        let width = width(opcode);
        let start = address
            .checked_add(offset as usize)
            .ok_or_else(|| self.trap("memory_out_of_bounds"))?;
        let range = self.range(start, width)?;
        self.work(width)?;
        let mut padded = [0; 8];
        padded[..width].copy_from_slice(&self.memory[range]);
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
            _ => return Err(self.invariant()),
        };
        self.push(value)
    }
    fn store(&mut self, opcode: u8, offset: u32) -> Result<(), ExecutionFailure> {
        let value = self.pop()?;
        let address = self.pop32()? as u32 as usize;
        let width = width(opcode);
        let start = address
            .checked_add(offset as usize)
            .ok_or_else(|| self.trap("memory_out_of_bounds"))?;
        let range = self.range(start, width)?;
        self.work(width)?;
        let bits = match value {
            Value::I32(x) => x as u32 as u64,
            Value::I64(x) => x as u64,
            Value::F32(x) => x as u64,
            Value::F64(x) => x,
        };
        self.memory[range].copy_from_slice(&bits.to_le_bytes()[..width]);
        Ok(())
    }
}
#[cfg(feature = "experimental-span-execution")]
impl Drop for SpanInstance {
    fn drop(&mut self) {
        self.cleanup();
    }
}
#[cfg_attr(not(feature = "experimental-span-execution"), allow(dead_code))]
fn width(op: u8) -> usize {
    match op {
        0x28 | 0x2a | 0x34 | 0x35 | 0x36 | 0x38 | 0x3e => 4,
        0x29 | 0x2b | 0x37 | 0x39 => 8,
        0x2e | 0x2f | 0x32 | 0x33 | 0x3b | 0x3d => 2,
        _ => 1,
    }
}
// Unreachable mutable-borrow guards retain allocation-free diagnostics too.
#[cfg_attr(not(feature = "experimental-span-execution"), allow(dead_code))]
fn unreachable_failure() -> ExecutionFailure {
    ExecutionFailure {
        kind: ExecutionFailureKind::Invariant,
        code: "execution_invariant",
        function: None,
        offset: 0,
        attempted: 0,
        limit: 0,
        usage: ExecutionUsage::default(),
        cache_failure: None,
    }
}
#[cfg_attr(not(feature = "experimental-span-execution"), allow(dead_code))]
struct ScalarReader<'a> {
    bytes: &'a [u8],
    at: usize,
}
#[cfg_attr(not(feature = "experimental-span-execution"), allow(dead_code))]
impl ScalarReader<'_> {
    fn byte(&mut self) -> Option<u8> {
        let b = *self.bytes.get(self.at)?;
        self.at += 1;
        Some(b)
    }
    fn uint(&mut self) -> Option<u32> {
        let mut n = 0;
        for i in 0..5 {
            let b = self.byte()?;
            n |= (b as u32 & 127) << (7 * i);
            if b & 128 == 0 {
                return Some(n);
            }
        }
        None
    }
    fn signed(&mut self) -> Option<i64> {
        let mut n = 0u64;
        for i in 0..10 {
            let b = self.byte()?;
            n |= (b as u64 & 127).wrapping_shl(7 * i);
            if b & 128 == 0 {
                let shift = 7 * (i + 1);
                if shift < 64 && b & 64 != 0 {
                    n |= u64::MAX << shift;
                }
                return Some(n as i64);
            }
        }
        None
    }
}
#[cfg_attr(not(feature = "experimental-span-execution"), allow(dead_code))]
fn initializer(bytes: &[u8]) -> Option<Value> {
    let mut reader = ScalarReader { bytes, at: 0 };
    let value = match reader.byte()? {
        0x41 => Value::I32(reader.signed()? as i32),
        0x42 => Value::I64(reader.signed()?),
        0x43 => Value::F32(u32::from_le_bytes(bytes.get(1..5)?.try_into().ok()?)),
        0x44 => Value::F64(u64::from_le_bytes(bytes.get(1..9)?.try_into().ok()?)),
        _ => return None,
    };
    Some(value)
}

#[cfg(feature = "experimental-swift-reactor")]
pub(crate) mod borrowed;
