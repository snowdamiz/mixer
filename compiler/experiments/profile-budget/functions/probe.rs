//! Non-authorizing per-function diagnostics in an immutable test-only VM export.
use crate::*;
use std::alloc::{GlobalAlloc, Layout, System};
use std::sync::atomic::{AtomicUsize, Ordering};
static LIVE: AtomicUsize = AtomicUsize::new(0);
static COUNT: AtomicUsize = AtomicUsize::new(0);
static PEAK: AtomicUsize = AtomicUsize::new(0);
static PEAK_COUNT: AtomicUsize = AtomicUsize::new(0);
struct Tracking;
fn add(bytes: usize, allocation: bool) {
    let live = LIVE.fetch_add(bytes, Ordering::Relaxed) + bytes;
    PEAK.fetch_max(live, Ordering::Relaxed);
    if allocation {
        let count = COUNT.fetch_add(1, Ordering::Relaxed) + 1;
        PEAK_COUNT.fetch_max(count, Ordering::Relaxed);
    }
}
unsafe impl GlobalAlloc for Tracking {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        let p = unsafe { System.alloc(layout) };
        if !p.is_null() {
            add(layout.size(), true);
        }
        p
    }
    unsafe fn alloc_zeroed(&self, layout: Layout) -> *mut u8 {
        let p = unsafe { System.alloc_zeroed(layout) };
        if !p.is_null() {
            add(layout.size(), true);
        }
        p
    }
    unsafe fn dealloc(&self, p: *mut u8, layout: Layout) {
        unsafe { System.dealloc(p, layout) };
        LIVE.fetch_sub(layout.size(), Ordering::Relaxed);
        COUNT.fetch_sub(1, Ordering::Relaxed);
    }
    unsafe fn realloc(&self, p: *mut u8, layout: Layout, next: usize) -> *mut u8 {
        let result = unsafe { System.realloc(p, layout, next) };
        if !result.is_null() {
            if next >= layout.size() {
                add(next - layout.size(), false);
            } else {
                LIVE.fetch_sub(layout.size() - next, Ordering::Relaxed);
            }
        }
        result
    }
}
#[global_allocator]
static ALLOCATOR: Tracking = Tracking;
#[derive(Clone, Copy)]
struct Phase {
    name: &'static str,
    live: usize,
    count: usize,
    peak: usize,
    peak_count: usize,
}
fn snapshot(name: &'static str) -> Phase {
    Phase {
        name,
        live: LIVE.load(Ordering::Relaxed),
        count: COUNT.load(Ordering::Relaxed),
        peak: PEAK.load(Ordering::Relaxed),
        peak_count: PEAK_COUNT.load(Ordering::Relaxed),
    }
}
use crate::decode::Reader;
use std::io::{BufWriter, Write};

// Diagnostic descriptors only: not a Module, proof token or production cache.
#[repr(C)]
#[derive(Clone, Copy)]
struct Span {
    offset: u32,
    bytes: u32,
}
#[repr(C)]
struct SignatureIndex {
    first: u32,
    count: u32,
    result: Option<Type>,
}
#[repr(C)]
struct ImportIndex {
    module: Span,
    name: Span,
    type_index: u32,
}
#[repr(C)]
struct GlobalIndex {
    initializer: Span,
    ty: Type,
    mutable: bool,
}
#[repr(C)]
struct FunctionIndex {
    body: Span,
    type_index: u32,
    first_group: u32,
    groups: u32,
    locals: u32,
}
#[repr(C)]
struct LocalGroup {
    count: u32,
    ty: Type,
}
#[repr(C)]
struct ExportIndex {
    name: Span,
    kind: u8,
    index: u32,
}
#[repr(C)]
struct SegmentIndex {
    payload: Span,
    index: u32,
    destination: u32,
    entries: u32,
}
#[derive(Default)]
struct Metadata {
    signatures: Vec<SignatureIndex>,
    parameters: Vec<Type>,
    imports: Vec<ImportIndex>,
    globals: Vec<GlobalIndex>,
    functions: Vec<FunctionIndex>,
    groups: Vec<LocalGroup>,
    exports: Vec<ExportIndex>,
    data: Vec<SegmentIndex>,
    elements: Vec<SegmentIndex>,
    memory: Option<(u32, Option<u32>)>,
    table: Option<(u32, Option<u32>)>,
    start: Option<u32>,
}
fn scalar(r: &mut Reader<'_>) -> Result<Type, Error> {
    match r.byte()? {
        0x7f => Ok(Type::I32),
        0x7e => Ok(Type::I64),
        0x7d => Ok(Type::F32),
        0x7c => Ok(Type::F64),
        _ => Err(r.err("unsupported", "diagnostic scalar type unsupported")),
    }
}
fn narrow(r: &Reader<'_>, value: usize) -> Result<u32, Error> {
    u32::try_from(value).map_err(|_| r.err("limit", "diagnostic offset/count exceeds u32"))
}
fn name(r: &mut Reader<'_>) -> Result<Span, Error> {
    let n = r.count(4096)?;
    let offset = narrow(r, r.offset())?;
    std::str::from_utf8(r.take(n)?).map_err(|_| r.err("malformed", "diagnostic name not UTF8"))?;
    Ok(Span {
        offset,
        bytes: n as u32,
    })
}
fn bounds(r: &mut Reader<'_>) -> Result<(u32, Option<u32>), Error> {
    let flags = r.u32()?;
    if flags > 1 {
        return Err(r.err(
            "unsupported",
            "diagnostic shared/memory64 limits unsupported",
        ));
    }
    let minimum = r.u32()?;
    let maximum = if flags == 1 { Some(r.u32()?) } else { None };
    if maximum.is_some_and(|max| minimum > max) {
        return Err(r.err("malformed", "limits minimum exceeds maximum"));
    }
    Ok((minimum, maximum))
}
fn constant(r: &mut Reader<'_>) -> Result<(Type, Option<u32>), Error> {
    let value = match r.byte()? {
        0x41 => (Type::I32, Some(r.signed(32)? as u32)),
        0x42 => {
            r.signed(64)?;
            (Type::I64, None)
        }
        0x43 => {
            r.take(4)?;
            (Type::F32, None)
        }
        0x44 => {
            r.take(8)?;
            (Type::F64, None)
        }
        _ => return Err(r.err("unsupported", "diagnostic constant expression unsupported")),
    };
    if r.byte()? != 0x0b {
        return Err(r.err("unsupported", "diagnostic extended constant unsupported"));
    }
    Ok(value)
}
fn destination(r: &mut Reader<'_>) -> Result<u32, Error> {
    constant(r)?
        .1
        .ok_or_else(|| r.err("unsupported", "diagnostic destination must be i32"))
}
fn metadata(bytes: &[u8]) -> Result<Metadata, Error> {
    // Inventory-only quotas; do not modify or call any executable-profile check.
    if bytes.len() > 64 * 1024 * 1024 {
        return Err(Error::new("limit", "diagnostic source ceiling", None, 0));
    }
    let mut r = Reader::at(bytes, 0);
    if r.take(8)? != b"\0asm\x01\0\0\0" {
        return Err(r.err("malformed", "diagnostic Wasm header"));
    }
    let mut m = Metadata::default();
    let mut defined = Vec::new();
    let mut seen = [false; 12];
    let mut last = 0;
    while r.pos < bytes.len() {
        let id = r.byte()?;
        let n = r.u32()? as usize;
        let base = r.offset();
        let payload = r.take(n)?;
        if id == 0 {
            continue;
        }
        if id > 11 || seen[id as usize] || id < last {
            return Err(r.err("malformed", "diagnostic unknown/duplicate/ordered section"));
        }
        seen[id as usize] = true;
        last = id;
        let mut s = Reader::at(payload, base);
        match id {
            1 => {
                let n = s.count(512)?;
                m.signatures = Vec::with_capacity(n);
                for _ in 0..n {
                    if s.byte()? != 0x60 {
                        return Err(s.err("unsupported", "diagnostic nonfunction type"));
                    }
                    let count = s.count(4096)?;
                    let first = narrow(&s, m.parameters.len())?;
                    if m.parameters
                        .len()
                        .checked_add(count)
                        .is_none_or(|v| v > 1_048_576)
                    {
                        return Err(s.err("limit", "diagnostic parameter storage ceiling"));
                    }
                    for _ in 0..count {
                        m.parameters.push(scalar(&mut s)?);
                    }
                    let results = s.count(1)?;
                    let result = if results == 1 {
                        Some(scalar(&mut s)?)
                    } else {
                        None
                    };
                    m.signatures.push(SignatureIndex {
                        first,
                        count: count as u32,
                        result,
                    });
                }
            }
            2 => {
                let n = s.count(4096)?;
                m.imports = Vec::with_capacity(n);
                for _ in 0..n {
                    let module = name(&mut s)?;
                    let name = name(&mut s)?;
                    if s.byte()? != 0 {
                        return Err(s.err("unsupported", "diagnostic nonfunction import"));
                    }
                    let type_index = s.u32()?;
                    if type_index as usize >= m.signatures.len() {
                        return Err(s.err("malformed", "diagnostic import type bounds"));
                    }
                    m.imports.push(ImportIndex {
                        module,
                        name,
                        type_index,
                    });
                }
            }
            3 => {
                let n = s.count(100_000)?;
                defined = Vec::with_capacity(n);
                for _ in 0..n {
                    let ty = s.u32()?;
                    if ty as usize >= m.signatures.len() {
                        return Err(s.err("malformed", "diagnostic function type bounds"));
                    }
                    defined.push(ty);
                }
            }
            4 => {
                if s.count(1)? == 1 {
                    if s.byte()? != 0x70 {
                        return Err(s.err("unsupported", "diagnostic table type"));
                    }
                    m.table = Some(bounds(&mut s)?);
                }
            }
            5 => {
                if s.count(1)? == 1 {
                    m.memory = Some(bounds(&mut s)?);
                }
            }
            6 => {
                let n = s.count(16384)?;
                m.globals = Vec::with_capacity(n);
                for _ in 0..n {
                    let ty = scalar(&mut s)?;
                    let mutable = match s.byte()? {
                        0 => false,
                        1 => true,
                        _ => return Err(s.err("malformed", "diagnostic global mutability")),
                    };
                    let begin = s.offset();
                    let (actual, _) = constant(&mut s)?;
                    if actual != ty {
                        return Err(s.err("malformed", "diagnostic initializer scalar mismatch"));
                    }
                    m.globals.push(GlobalIndex {
                        initializer: Span {
                            offset: narrow(&s, begin)?,
                            bytes: narrow(&s, s.offset() - begin)?,
                        },
                        ty,
                        mutable,
                    });
                }
            }
            7 => {
                let n = s.count(4096)?;
                m.exports = Vec::with_capacity(n);
                for _ in 0..n {
                    m.exports.push(ExportIndex {
                        name: name(&mut s)?,
                        kind: s.byte()?,
                        index: s.u32()?,
                    });
                }
            }
            8 => {
                m.start = Some(s.u32()?);
            }
            9 | 11 => {
                let n = s.count(4096)?;
                for _ in 0..n {
                    let flags = s.u32()?;
                    if flags != 0 && flags != 2 {
                        return Err(s.err("unsupported", "diagnostic passive/reference segment"));
                    }
                    let index = if flags == 2 { s.u32()? } else { 0 };
                    let destination = destination(&mut s)?;
                    if id == 9 && flags == 2 && s.byte()? != 0 {
                        return Err(s.err("unsupported", "diagnostic element kind"));
                    }
                    let entries = s.u32()?;
                    let begin = s.offset();
                    if id == 9 {
                        if entries > 65_536 {
                            return Err(s.err("limit", "diagnostic element entries ceiling"));
                        }
                        for _ in 0..entries {
                            s.u32()?;
                        }
                    } else {
                        s.take(entries as usize)?;
                    }
                    let item = SegmentIndex {
                        payload: Span {
                            offset: narrow(&s, begin)?,
                            bytes: narrow(&s, s.offset() - begin)?,
                        },
                        index,
                        destination,
                        entries,
                    };
                    if id == 9 {
                        m.elements.push(item);
                    } else {
                        m.data.push(item);
                    }
                }
            }
            10 => {
                let n = s.count(100_000)?;
                if n != defined.len() {
                    return Err(s.err("malformed", "diagnostic body/declaration count mismatch"));
                }
                m.functions = Vec::with_capacity(n);
                for type_index in &defined {
                    let n = s.u32()? as usize;
                    let offset = s.offset();
                    let body = s.take(n)?;
                    let mut b = Reader::at(body, offset);
                    let groups = b.count(4096)?;
                    let first_group = narrow(&b, m.groups.len())?;
                    let mut locals = 0u32;
                    for _ in 0..groups {
                        let count = b.u32()?;
                        let ty = scalar(&mut b)?;
                        locals = locals
                            .checked_add(count)
                            .ok_or_else(|| b.err("malformed", "diagnostic local sum overflow"))?;
                        if m.groups.len() >= 1_048_576 {
                            return Err(b.err("limit", "diagnostic local-group storage ceiling"));
                        }
                        m.groups.push(LocalGroup { count, ty });
                    }
                    // Remaining instructions are intentionally not validated here.
                    m.functions.push(FunctionIndex {
                        body: Span {
                            offset: narrow(&b, offset)?,
                            bytes: narrow(&b, n)?,
                        },
                        type_index: *type_index,
                        first_group,
                        groups: groups as u32,
                        locals,
                    });
                }
            }
            _ => unreachable!(),
        }
        s.end()?;
    }
    if !defined.is_empty() && !seen[10] {
        return Err(r.err("malformed", "diagnostic declarations lack bodies"));
    }
    Ok(m)
}
fn body_shape(code: &[Instruction]) -> (usize, usize, usize) {
    let mut targets = 0;
    let mut capacity = 0;
    let mut nesting = 0usize;
    let mut maximum = 0;
    for ins in code {
        match &ins.op {
            Op::BrTable(v, _) => {
                targets += v.len();
                capacity += v.capacity() * std::mem::size_of::<u32>();
            }
            Op::Block { .. } => {
                nesting += 1;
                maximum = maximum.max(nesting);
            }
            Op::End => {
                nesting = nesting.saturating_sub(1);
            }
            _ => {}
        }
    }
    (targets, capacity, maximum)
}
// Constant-space structural inventory, deliberately separate from body admission.
#[derive(Default)]
struct RawShape {
    instructions: usize,
    branch_targets: usize,
    branch_tables: usize,
    nesting: usize,
    immediate_bytes: usize,
    code_bytes: usize,
}
fn raw_shape(body: &[u8], base: usize) -> Result<RawShape, Error> {
    let mut r = Reader::at(body, base);
    for _ in 0..r.count(4096)? {
        r.u32()?;
        scalar(&mut r)?;
    }
    let start = r.pos;
    let mut shape = RawShape::default();
    let mut depth = 0usize;
    loop {
        let begin = r.pos;
        let opcode = r.byte()?;
        shape.instructions += 1;
        match opcode {
            0..=1 | 5 | 0x0f | 0x1a | 0x1b | 0x45..=0xc4 => {}
            2..=4 => {
                let ty = r.byte()?;
                if ![0x40, 0x7f, 0x7e, 0x7d, 0x7c].contains(&ty) {
                    return Err(r.err("unsupported", "raw indexed/multi-result block type"));
                }
                depth += 1;
                shape.nesting = shape.nesting.max(depth);
            }
            0x0b => {
                if depth == 0 {
                    shape.code_bytes = r.pos - start;
                    r.end()?;
                    break;
                }
                depth -= 1;
            }
            0x0c | 0x0d | 0x10 | 0x20..=0x24 => {
                r.u32()?;
            }
            0x0e => {
                let n = r.count(body.len())?;
                shape.branch_targets += n;
                shape.branch_tables += 1;
                for _ in 0..n {
                    r.u32()?;
                }
                r.u32()?;
            }
            0x11 | 0x28..=0x3e => {
                r.u32()?;
                r.u32()?;
            }
            0x3f | 0x40 => {
                if r.byte()? != 0 {
                    return Err(r.err("unsupported", "raw memory index"));
                }
            }
            0x41 => {
                r.signed(32)?;
            }
            0x42 => {
                r.signed(64)?;
            }
            0x43 => {
                r.take(4)?;
            }
            0x44 => {
                r.take(8)?;
            }
            0xfc => match r.u32()? {
                0..=7 => {}
                10 => {
                    r.u32()?;
                    r.u32()?;
                }
                11 => {
                    r.u32()?;
                }
                _ => return Err(r.err("unsupported", "raw extended opcode")),
            },
            _ => return Err(r.err("unsupported", "raw opcode unsupported")),
        }
        shape.immediate_bytes += r.pos - begin - 1;
    }
    assert_eq!(shape.code_bytes, shape.instructions + shape.immediate_bytes);
    Ok(shape)
}
// Static scalar-arity/control-height inventory only. This does not compare
// operand types, approve imports, instantiate a Module, or authorize a profile.
// The separate diagnostic control ceiling does not widen the frozen decoder.
#[derive(Clone, Copy)]
struct HeightControl {
    kind: u8,
    height: usize,
    result: bool,
    unreachable: bool,
    has_else: bool,
}
const EMPTY_HEIGHT: HeightControl = HeightControl {
    kind: 0,
    height: 0,
    result: false,
    unreachable: false,
    has_else: false,
};
struct Heights {
    controls: [HeightControl; 1024],
    depth: usize,
    stack: usize,
    maximum: usize,
}
impl Heights {
    fn pop(&mut self, r: &Reader<'_>, count: usize) -> Result<(), Error> {
        let control = self.controls[self.depth - 1];
        for _ in 0..count {
            if self.stack == control.height && control.unreachable {
                continue; // Polymorphic unreachable operands have no stored slot.
            }
            if self.stack <= control.height {
                return Err(r.err("validation", "diagnostic operand height underflow"));
            }
            self.stack -= 1;
        }
        Ok(())
    }
    fn push(&mut self, r: &Reader<'_>, count: usize) -> Result<(), Error> {
        self.stack = self
            .stack
            .checked_add(count)
            .filter(|n| *n <= 1_048_576)
            .ok_or_else(|| r.err("limit", "diagnostic operand height ceiling"))?;
        self.maximum = self.maximum.max(self.stack);
        Ok(())
    }
    fn dead(&mut self) {
        let control = &mut self.controls[self.depth - 1];
        self.stack = control.height;
        control.unreachable = true;
    }
    fn label(&self, r: &Reader<'_>, index: u32) -> Result<usize, Error> {
        let index = self
            .depth
            .checked_sub(index as usize + 1)
            .ok_or_else(|| r.err("validation", "diagnostic branch depth"))?;
        let control = self.controls[index];
        Ok(usize::from(control.kind != 3 && control.result)) // loop branches have no input.
    }
}
fn numeric_arity(r: &Reader<'_>, opcode: u8) -> Result<usize, Error> {
    match opcode {
        0x45 | 0x50 | 0x67..=0x69 | 0x79..=0x7b | 0x8b..=0x91 | 0x99..=0x9f | 0xa7..=0xc4 => Ok(1),
        0x46..=0x4f | 0x51..=0x66 | 0x6a..=0x78 | 0x7c..=0x8a | 0x92..=0x98 | 0xa0..=0xa6 => Ok(2),
        _ => Err(r.err("unsupported", "diagnostic numeric arity")),
    }
}
fn operand_height(
    body: &[u8],
    base: usize,
    m: &Metadata,
    function: &FunctionIndex,
) -> Result<usize, Error> {
    let mut r = Reader::at(body, base);
    for _ in 0..r.count(4096)? {
        r.u32()?;
        scalar(&mut r)?;
    }
    let signature = &m.signatures[function.type_index as usize];
    let mut h = Heights {
        controls: [EMPTY_HEIGHT; 1024],
        depth: 1,
        stack: 0,
        maximum: 0,
    };
    h.controls[0].result = signature.result.is_some();
    loop {
        let opcode = r.byte()?;
        match opcode {
            0 => h.dead(),
            1 => {}
            2..=4 => {
                let ty = r.byte()?;
                if ![0x40, 0x7f, 0x7e, 0x7d, 0x7c].contains(&ty) {
                    return Err(r.err("unsupported", "diagnostic block result"));
                }
                if opcode == 4 {
                    h.pop(&r, 1)?;
                }
                if h.depth == h.controls.len() {
                    return Err(r.err("limit", "diagnostic control height ceiling"));
                }
                h.controls[h.depth] = HeightControl {
                    kind: opcode,
                    height: h.stack,
                    result: ty != 0x40,
                    unreachable: false,
                    has_else: false,
                };
                h.depth += 1;
            }
            5 | 0x0b => {
                let c = h.controls[h.depth - 1];
                if opcode == 5 && (c.kind != 4 || c.has_else) {
                    return Err(r.err("validation", "diagnostic unexpected else"));
                }
                if opcode == 0x0b && c.kind == 4 && c.result && !c.has_else {
                    return Err(r.err("validation", "diagnostic missing result else"));
                }
                h.pop(&r, usize::from(c.result))?;
                if h.stack != c.height {
                    return Err(r.err("validation", "diagnostic extra values at control end"));
                }
                if opcode == 5 {
                    h.controls[h.depth - 1].unreachable = false;
                    h.controls[h.depth - 1].has_else = true;
                } else {
                    h.depth -= 1;
                    h.push(&r, usize::from(c.result))?;
                    if h.depth == 0 {
                        r.end()?;
                        return Ok(h.maximum);
                    }
                }
            }
            0x0c | 0x0d => {
                let target = r.u32()?;
                if opcode == 0x0d {
                    h.pop(&r, 1)?;
                }
                let count = h.label(&r, target)?;
                h.pop(&r, count)?;
                if opcode == 0x0d {
                    h.push(&r, count)?;
                } else {
                    h.dead();
                }
            }
            0x0e => {
                let count = r.count(body.len())?;
                let mut arity = None;
                for _ in 0..=count {
                    let index = r.u32()?;
                    let next = h.label(&r, index)?;
                    if arity.is_some_and(|previous| previous != next) {
                        return Err(r.err("validation", "diagnostic branch arity mismatch"));
                    }
                    arity = Some(next);
                }
                h.pop(&r, 1 + arity.unwrap())?;
                h.dead();
            }
            0x0f => {
                h.pop(&r, usize::from(h.controls[0].result))?;
                h.dead();
            }
            0x10 | 0x11 => {
                let index = r.u32()? as usize;
                let type_index = if opcode == 0x11 {
                    if r.u32()? != 0 || m.table.is_none() {
                        return Err(r.err("validation", "diagnostic indirect table"));
                    }
                    h.pop(&r, 1)?;
                    index
                } else if index < m.imports.len() {
                    m.imports[index].type_index as usize
                } else {
                    m.functions
                        .get(index - m.imports.len())
                        .ok_or_else(|| r.err("validation", "diagnostic call index"))?
                        .type_index as usize
                };
                let sig = m
                    .signatures
                    .get(type_index)
                    .ok_or_else(|| r.err("validation", "diagnostic call signature"))?;
                h.pop(&r, sig.count as usize)?;
                h.push(&r, usize::from(sig.result.is_some()))?;
            }
            0x1a => h.pop(&r, 1)?,
            0x1b => {
                h.pop(&r, 3)?;
                h.push(&r, 1)?;
            }
            0x20..=0x24 => {
                let index = r.u32()? as usize;
                if opcode <= 0x22 && index >= signature.count as usize + function.locals as usize {
                    return Err(r.err("validation", "diagnostic local index"));
                }
                if opcode >= 0x23 && index >= m.globals.len() {
                    return Err(r.err("validation", "diagnostic global index"));
                }
                match opcode {
                    0x20 | 0x23 => h.push(&r, 1)?,
                    0x21 | 0x24 => h.pop(&r, 1)?,
                    _ => {
                        h.pop(&r, 1)?;
                        h.push(&r, 1)?;
                    }
                }
            }
            0x28..=0x3e => {
                r.u32()?;
                r.u32()?;
                h.pop(&r, if opcode <= 0x35 { 1 } else { 2 })?;
                if opcode <= 0x35 {
                    h.push(&r, 1)?;
                }
            }
            0x3f | 0x40 => {
                if r.byte()? != 0 {
                    return Err(r.err("unsupported", "diagnostic memory index"));
                }
                if opcode == 0x40 {
                    h.pop(&r, 1)?;
                }
                h.push(&r, 1)?;
            }
            0x41 => {
                r.signed(32)?;
                h.push(&r, 1)?;
            }
            0x42 => {
                r.signed(64)?;
                h.push(&r, 1)?;
            }
            0x43 => {
                r.take(4)?;
                h.push(&r, 1)?;
            }
            0x44 => {
                r.take(8)?;
                h.push(&r, 1)?;
            }
            0x45..=0xc4 => {
                let count = numeric_arity(&r, opcode)?;
                h.pop(&r, count)?;
                h.push(&r, 1)?;
            }
            0xfc => match r.u32()? {
                0..=7 => {
                    h.pop(&r, 1)?;
                    h.push(&r, 1)?;
                }
                sub @ (10 | 11) => {
                    if r.u32()? != 0 || (sub == 10 && r.u32()? != 0) {
                        return Err(r.err("unsupported", "diagnostic bulk memory index"));
                    }
                    h.pop(&r, 3)?;
                }
                _ => return Err(r.err("unsupported", "diagnostic extended arity")),
            },
            _ => return Err(r.err("unsupported", "diagnostic opcode arity")),
        }
    }
}
#[test]
fn measure_candidate() {
    let path = std::env::var("MIXER_FUNCTION_SOURCE").unwrap();
    let csv_path = std::env::var("MIXER_FUNCTION_CSV").unwrap();
    let mut output = BufWriter::with_capacity(65_536, std::fs::File::create(csv_path).unwrap());
    let mut baseline = snapshot("baseline");
    baseline.peak = baseline.live;
    baseline.peak_count = baseline.count;
    PEAK.store(baseline.live, Ordering::Relaxed);
    PEAK_COUNT.store(baseline.count, Ordering::Relaxed);
    let source = std::fs::read(&path).unwrap();
    let expected_bytes = std::env::var("MIXER_FUNCTION_EXPECTED_BYTES")
        .map(|value| value.parse::<usize>().unwrap())
        .unwrap_or(52_008_982);
    assert_eq!(source.len(), expected_bytes);
    let source_bytes = source.len();
    let read = snapshot("source_read");
    let m = metadata(&source).unwrap();
    let indexed = snapshot("diagnostic_indexed");
    let mut maximum_peak = indexed.peak;
    let mut maximum_count = indexed.peak_count;
    let limits = Limits {
        profile: Profile::TableMemoryV3,
        ..Limits::default()
    };
    writeln!(output,"function,defined,type_index,body_offset,wire_bytes,local_groups,declared_locals,parameters,raw_instructions,raw_branch_targets,raw_branch_tables,raw_max_block_nesting,raw_immediate_bytes,raw_code_wire_bytes,raw_max_operand_height,status,error_offset,error_message_utf8_hex,instructions,instruction_capacity_bytes,branch_targets,branch_capacity_bytes,locals_capacity_bytes,max_block_nesting,retained_requested_above_baseline,peak_requested_above_baseline,peak_live_allocations_above_baseline,maximum_live_allocation_count").unwrap();
    let mut successful = 0;
    for (defined, function) in m.functions.iter().enumerate() {
        let index = m.imports.len() + defined;
        let body = &source
            [function.body.offset as usize..(function.body.offset + function.body.bytes) as usize];
        let raw = raw_shape(body, function.body.offset as usize).unwrap();
        let operands = operand_height(body, function.body.offset as usize, &m, function).unwrap();
        let before = snapshot("before_body");
        PEAK.store(before.live, Ordering::Relaxed);
        PEAK_COUNT.store(before.count, Ordering::Relaxed);
        let mut inv = Inventory::default();
        let result = crate::decode::measurement_decode_body(
            body,
            function.body.offset as usize,
            index as u32,
            &limits,
            &mut inv,
        );
        let measured = snapshot("body_decoded");
        maximum_peak = maximum_peak.max(measured.peak);
        maximum_count = maximum_count.max(measured.peak_count);
        write!(
            output,
            "{index},{defined},{},{},{},{},{},{},",
            function.type_index,
            function.body.offset,
            function.body.bytes,
            function.groups,
            function.locals,
            m.signatures[function.type_index as usize].count
        )
        .unwrap();
        write!(
            output,
            "{},{},{},{},{},{},{},",
            raw.instructions,
            raw.branch_targets,
            raw.branch_tables,
            raw.nesting,
            raw.immediate_bytes,
            raw.code_bytes,
            operands
        )
        .unwrap();
        match &result {
            Ok((locals, code)) => {
                successful += 1;
                let shape = body_shape(code);
                assert_eq!(
                    (code.len(), shape.0, shape.2),
                    (raw.instructions, raw.branch_targets, raw.nesting)
                );
                write!(
                    output,
                    "decoded,,,{},{},{},{},{},{},",
                    code.len(),
                    code.capacity() * std::mem::size_of::<Instruction>(),
                    shape.0,
                    shape.1,
                    locals.capacity() * std::mem::size_of::<Type>(),
                    shape.2
                )
                .unwrap();
            }
            Err(error) => {
                write!(output, "{},{},", error.code, error.offset).unwrap();
                for byte in error.message.as_bytes() {
                    write!(output, "{byte:02x}").unwrap();
                }
                write!(output, ",,,,,,,").unwrap();
            }
        }
        writeln!(
            output,
            "{},{},{},{}",
            measured.live - before.live,
            measured.peak - before.live,
            measured.peak_count - before.count,
            measured.peak_count
        )
        .unwrap();
        drop(result);
        drop(inv);
        assert_eq!(
            LIVE.load(Ordering::Relaxed),
            before.live,
            "one-body allocation did not return to baseline"
        );
        assert_eq!(COUNT.load(Ordering::Relaxed), before.count);
    }
    output.flush().unwrap();
    let capacities = m.signatures.capacity() * std::mem::size_of::<SignatureIndex>()
        + m.parameters.capacity() * std::mem::size_of::<Type>()
        + m.imports.capacity() * std::mem::size_of::<ImportIndex>()
        + m.globals.capacity() * std::mem::size_of::<GlobalIndex>()
        + m.functions.capacity() * std::mem::size_of::<FunctionIndex>()
        + m.groups.capacity() * std::mem::size_of::<LocalGroup>()
        + m.exports.capacity() * std::mem::size_of::<ExportIndex>()
        + m.data.capacity() * std::mem::size_of::<SegmentIndex>()
        + m.elements.capacity() * std::mem::size_of::<SegmentIndex>();
    let counts = (
        m.signatures.len(),
        m.parameters.len(),
        m.imports.len(),
        m.globals.len(),
        m.functions.len(),
        m.groups.len(),
        m.exports.len(),
        m.data.len(),
        m.elements.len(),
    );
    let global_initializers: usize = m.globals.iter().map(|x| x.initializer.bytes as usize).sum();
    let maximum_parameters = m.signatures.iter().map(|x| x.count).max().unwrap_or(0);
    let maximum_locals = m
        .functions
        .iter()
        .map(|x| x.locals + m.signatures[x.type_index as usize].count)
        .max()
        .unwrap_or(0);
    let memory = m.memory;
    let table = m.table;
    let layout = crate::validate::measurement_validator_layout();
    drop(m);
    let released = snapshot("index_dropped");
    drop(source);
    let done = snapshot("source_dropped");
    println!("RESOURCE_JSON {{\"memory\":{{\"minimum\":{},\"maximum\":{}}},\"table\":{{\"minimum\":{},\"maximum\":{}}}}}",memory.unwrap().0,memory.unwrap().1.map(|v|v.to_string()).unwrap_or_else(||"null".into()),table.unwrap().0,table.unwrap().1.map(|v|v.to_string()).unwrap_or_else(||"null".into()));
    println!("SUMMARY_JSON {{\"authorization\":false,\"source_bytes\":{source_bytes},\"successful_bodies\":{successful},\"types\":{},\"parameters\":{},\"imports\":{},\"globals\":{},\"functions\":{},\"local_groups\":{},\"exports\":{},\"data_segments\":{},\"element_segments\":{},\"global_initializer_wire_bytes\":{global_initializers},\"maximum_parameters\":{maximum_parameters},\"maximum_parameters_plus_locals\":{maximum_locals},\"diagnostic_index_capacity_bytes\":{capacities},\"maximum_observed_requested_bytes\":{maximum_peak},\"maximum_observed_live_allocation_count\":{maximum_count},\"layout\":{{\"instruction\":{},\"function\":{},\"signature_index\":{},\"function_index\":{},\"local_group\":{},\"global_index\":{},\"import_index\":{},\"export_index\":{},\"segment_index\":{},\"validator_control\":{},\"validator_state\":{},\"validator_operand\":{},\"decoder_control\":{}}},\"phases\":[{}]}}",counts.0,counts.1,counts.2,counts.3,counts.4,counts.5,counts.6,counts.7,counts.8,
        std::mem::size_of::<Instruction>(),std::mem::size_of::<Function>(),std::mem::size_of::<SignatureIndex>(),std::mem::size_of::<FunctionIndex>(),std::mem::size_of::<LocalGroup>(),std::mem::size_of::<GlobalIndex>(),std::mem::size_of::<ImportIndex>(),std::mem::size_of::<ExportIndex>(),std::mem::size_of::<SegmentIndex>(),layout.0,layout.1,std::mem::size_of::<Option<Type>>(),std::mem::size_of::<(usize,Option<usize>)>(),
        [baseline,read,indexed,released,done].iter().map(|p|format!("{{\"name\":\"{}\",\"live_requested_bytes\":{},\"live_allocations\":{},\"peak_requested_bytes\":{},\"peak_live_allocations\":{}}}",p.name,p.live,p.count,p.peak,p.peak_count)).collect::<Vec<_>>().join(","));
    assert_eq!(done.live, baseline.live);
    assert_eq!(done.count, baseline.count);
}

#[cfg(test)]
mod tests {
    use super::*;
    fn leb(mut n: usize) -> Vec<u8> {
        let mut b = vec![];
        loop {
            let x = (n & 127) as u8;
            n >>= 7;
            b.push(x | if n == 0 { 0 } else { 128 });
            if n == 0 {
                return b;
            }
        }
    }
    fn section(m: &mut Vec<u8>, id: u8, b: &[u8]) {
        m.push(id);
        m.extend(leb(b.len()));
        m.extend(b);
    }
    fn fixture(body: &[u8]) -> Vec<u8> {
        let mut b = b"\0asm\x01\0\0\0".to_vec();
        section(&mut b, 1, &[1, 0x60, 0, 1, 0x7f]);
        section(&mut b, 3, &[1, 0]);
        let mut c = vec![1];
        c.extend(leb(body.len()));
        c.extend(body);
        section(&mut b, 10, &c);
        b
    }
    #[test]
    fn truncated_and_oversized_section_fail() {
        let b = fixture(&[0, 0x41, 0, 0x0b]);
        for n in 0..b.len() {
            assert!(metadata(&b[..n]).is_err() || n == 8 || n == 15 || n == 19);
        }
        let mut b = b"\0asm\x01\0\0\0".to_vec();
        b.extend([1, 0xff, 0xff, 0xff, 0xff, 0x0f]);
        assert!(metadata(&b).is_err());
    }
    #[test]
    fn unknown_duplicate_section_and_type_fail() {
        let mut b = fixture(&[0, 0x41, 0, 0x0b]);
        section(&mut b, 1, &[0]);
        assert!(metadata(&b).is_err());
        let mut b = b"\0asm\x01\0\0\0".to_vec();
        section(&mut b, 12, &[0]);
        assert!(metadata(&b).is_err());
        let mut b = b"\0asm\x01\0\0\0".to_vec();
        section(&mut b, 1, &[1, 0x60, 1, 0x7b, 0]);
        assert!(metadata(&b).is_err());
    }
    #[test]
    fn local_sum_overflow_and_body_count_fail() {
        let mut body = vec![2];
        body.extend(leb(u32::MAX as usize));
        body.push(0x7f);
        body.extend([1, 0x7f, 0x0b]);
        assert!(metadata(&fixture(&body)).is_err());
        let mut b = b"\0asm\x01\0\0\0".to_vec();
        section(&mut b, 1, &[1, 0x60, 0, 0]);
        section(&mut b, 3, &[1, 0]);
        section(&mut b, 10, &[0]);
        assert!(metadata(&b).is_err());
    }
    #[test]
    fn body_profile_ceiling_is_unchanged() {
        let limits = Limits {
            profile: Profile::TableMemoryV3,
            ..Limits::default()
        };
        let mut body = vec![0];
        for _ in 0..128 {
            body.extend([2, 0x40]);
        }
        body.extend(std::iter::repeat_n(0x0b, 129));
        let mut inv = Inventory::default();
        assert!(crate::decode::measurement_decode_body(&body, 0, 0, &limits, &mut inv).is_err());
        let mut body = vec![1];
        body.extend(leb(4097));
        body.extend([0x7f, 0x0b]);
        assert!(crate::decode::measurement_decode_body(&body, 0, 0, &limits, &mut inv).is_err());
    }
    #[test]
    fn raw_control_inventory_is_not_body_admission() {
        let mut body = vec![0];
        for _ in 0..140 {
            body.extend([2, 0x40]);
        }
        body.extend(std::iter::repeat_n(0x0b, 141));
        let raw = raw_shape(&body, 0).unwrap();
        assert_eq!(raw.nesting, 140);
        let limits = Limits {
            profile: Profile::TableMemoryV3,
            ..Limits::default()
        };
        let mut inv = Inventory::default();
        let error =
            crate::decode::measurement_decode_body(&body, 0, 0, &limits, &mut inv).unwrap_err();
        assert_eq!(error.message, "control nesting exceeds profile");
        assert!(raw_shape(&[0, 0xff, 0x0b], 0).is_err());
        assert!(raw_shape(&[0, 0x0e, 0xff], 0).is_err());
    }
    #[test]
    fn body_diagnostic_does_not_claim_type_validation() {
        let body = [0, 1, 0x0b];
        let b = fixture(&body);
        let m = metadata(&b).unwrap();
        assert_eq!(m.signatures[0].result, Some(Type::I32));
        let limits = Limits {
            profile: Profile::TableMemoryV3,
            ..Limits::default()
        };
        let mut inv = Inventory::default();
        let (_, code) =
            crate::decode::measurement_decode_body(&body, 0, 0, &limits, &mut inv).unwrap();
        assert_eq!(code.len(), 2);
        assert!(matches!(code[0].op, Op::Nop)); /* no i32 result, despite diagnostic success */
    }
    fn height(body: &[u8]) -> Result<usize, Error> {
        let bytes = fixture(body);
        let m = metadata(&bytes)?;
        operand_height(body, 0, &m, &m.functions[0])
    }
    #[test]
    fn static_height_arithmetic_control_and_unreachable_polymorphism() {
        assert_eq!(height(&[0, 0x41, 1, 0x41, 2, 0x6a, 0x0b]).unwrap(), 2);
        assert_eq!(
            height(&[0, 0x41, 1, 4, 0x7f, 0x41, 2, 5, 0x41, 3, 0x0b, 0x0b]).unwrap(),
            1
        );
        assert_eq!(height(&[0, 0, 0x7c, 0x1a, 0x41, 1, 0x0b]).unwrap(), 1);
        // An outer retained value remains part of total per-frame stack height.
        assert_eq!(
            height(&[0, 0x41, 1, 2, 0x40, 0x41, 2, 0x41, 3, 0x6a, 0x1a, 0x0b, 0x0b]).unwrap(),
            3
        );
        assert!(height(&[0, 0x1a, 0x0b]).is_err());
        assert!(height(&[0, 0x41, 1, 4, 0x7f, 0x41, 2, 0x0b, 0x0b]).is_err());
        assert!(height(&[0, 0x0c, 1, 0x0b]).is_err());
    }
    #[test]
    fn static_height_calls_indirect_calls_and_local_slots() {
        let body = [0, 0x41, 1, 0x41, 2, 0x10, 0, 0x0b];
        let bytes = fixture(&body);
        let mut m = metadata(&bytes).unwrap();
        m.signatures.push(SignatureIndex {
            first: 0,
            count: 2,
            result: Some(Type::I32),
        });
        m.imports.push(ImportIndex {
            module: Span {
                offset: 0,
                bytes: 0,
            },
            name: Span {
                offset: 0,
                bytes: 0,
            },
            type_index: 1,
        });
        assert_eq!(operand_height(&body, 0, &m, &m.functions[0]).unwrap(), 2);
        m.table = Some((1, Some(1)));
        let indirect = [0, 0x41, 1, 0x41, 2, 0x41, 0, 0x11, 1, 0, 0x0b];
        assert_eq!(
            operand_height(&indirect, 0, &m, &m.functions[0]).unwrap(),
            3
        );
        let local = [1, 1, 0x7f, 0x41, 4, 0x22, 0, 0x20, 0, 0x6a, 0x0b];
        assert_eq!(height(&local).unwrap(), 2);
    }
    #[test]
    fn static_height_branch_results_tables_and_loop_labels() {
        assert_eq!(
            height(&[0, 2, 0x7f, 0x41, 1, 0x0c, 0, 0x0b, 0x0b]).unwrap(),
            1
        );
        assert_eq!(
            height(&[0, 2, 0x7f, 0x41, 1, 0x41, 0, 0x0d, 0, 0x0b, 0x0b]).unwrap(),
            2
        );
        assert_eq!(
            height(&[0, 2, 0x7f, 0x41, 1, 0x41, 0, 0x0e, 1, 0, 0, 0x0b, 0x0b]).unwrap(),
            2
        );
        assert_eq!(
            height(&[0, 3, 0x40, 0x0c, 0, 0x0b, 0x41, 1, 0x0b]).unwrap(),
            1
        );
        assert_eq!(height(&[0, 0x41, 1, 0x0f, 0x0b]).unwrap(), 1);
    }
    #[test]
    fn static_height_inventory_covers_deep_bodies_without_admission_or_type_claim() {
        let mut body = vec![0];
        for _ in 0..140 {
            body.extend([2, 0x40]);
        }
        body.extend(std::iter::repeat_n(0x0b, 140));
        body.extend([0x41, 1, 0x0b]);
        assert_eq!(height(&body).unwrap(), 1);
        // f64 result in an i32 signature: correct arity, deliberately unchecked type.
        assert_eq!(height(&[0, 0x44, 0, 0, 0, 0, 0, 0, 0, 0, 0x0b]).unwrap(), 1);
        for opcode in 0x45..=0xc4 {
            assert_eq!(
                numeric_arity(&Reader::at(&[], 0), opcode).unwrap(),
                crate::validate::numeric_type(opcode).1
            );
        }
    }
    #[test]
    fn static_operand_ceiling_inventory_agrees_with_frozen_acceptance_boundary() {
        let limits = Limits {
            profile: Profile::TableMemoryV3,
            ..Limits::default()
        };
        for count in [4096, 4097] {
            let mut body = vec![0];
            for _ in 0..count {
                body.extend([0x41, 1]);
            }
            body.extend(std::iter::repeat_n(0x1a, count - 1));
            body.push(0x0b);
            assert_eq!(height(&body).unwrap(), count);
            let bytes = fixture(&body);
            let result = Module::decode(&bytes, &limits);
            if count == 4096 {
                assert!(result.is_ok());
            } else {
                assert_eq!(
                    result.err().unwrap().message,
                    "validated operand stack exceeds limit"
                );
            }
        }
        let type_wrong = fixture(&[0, 0x44, 0, 0, 0, 0, 0, 0, 0, 0, 0x0b]);
        assert!(Module::decode(&type_wrong, &limits).is_err());
    }
}
