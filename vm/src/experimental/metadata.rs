use super::*;
use crate::Type;
use reader::Reader;
use std::cmp::Ordering;

#[derive(Clone, Copy, Debug, Default)]
pub(super) struct Span {
    pub offset: u32,
    pub bytes: u32,
}
impl Span {
    pub fn slice(self, source: &[u8]) -> &[u8] {
        // Private spans are created only after Reader::take bounds checks and
        // span()'s checked end calculation under the 4MiB source ceiling.
        &source[self.offset as usize..self.offset as usize + self.bytes as usize]
    }
}
#[derive(Clone, Copy)]
pub(super) struct Signature {
    pub first: u32,
    pub count: u32,
    pub result: Option<Type>,
}
#[derive(Clone, Copy)]
pub(super) struct Import {
    module: Span,
    name: Span,
    pub type_index: u32,
}
#[derive(Clone, Copy)]
pub(super) struct Function {
    pub body: Span,
    pub type_index: u32,
}
#[derive(Clone, Copy)]
pub(super) struct Global {
    pub ty: Type,
    pub mutable: bool,
    pub initializer: Span,
}
#[derive(Clone, Copy)]
pub(super) struct Export {
    name: Span,
    kind: u8,
    index: u32,
}
#[derive(Clone, Copy)]
pub(super) struct Segment {
    pub payload: Span,
    pub destination: u32,
    pub count: u32,
}
pub(super) struct Metadata {
    pub signatures: Buffer<Signature>,
    pub parameters: Buffer<Type>,
    pub imports: Buffer<Import>,
    pub functions: Buffer<Function>,
    pub globals: Buffer<Global>,
    pub exports: Buffer<Export>,
    pub data: Buffer<Segment>,
    pub elements: Buffer<Segment>,
    pub memory: Option<(u32, u32)>,
    pub table: Option<(u32, u32)>,
    pub instructions: usize,
}
impl Metadata {
    fn new() -> Self {
        Self {
            signatures: Buffer::new(Resource::Metadata),
            parameters: Buffer::new(Resource::Metadata),
            imports: Buffer::new(Resource::Metadata),
            functions: Buffer::new(Resource::Metadata),
            globals: Buffer::new(Resource::Metadata),
            exports: Buffer::new(Resource::Metadata),
            data: Buffer::new(Resource::Metadata),
            elements: Buffer::new(Resource::Metadata),
            memory: None,
            table: None,
            instructions: 0,
        }
    }
    pub fn signature(&self, function: u32) -> Option<Signature> {
        let index = function as usize;
        let ty = if index < self.imports.len() {
            self.imports.get(index)?.type_index
        } else {
            self.functions.get(index - self.imports.len())?.type_index
        };
        self.signatures.get(ty as usize).copied()
    }
    pub fn params(&self, signature: Signature) -> &[Type] {
        &self.parameters.as_slice()
            [signature.first as usize..signature.first as usize + signature.count as usize]
    }
}
fn u32_offset(value: usize, meter: &Meter<'_>, cursor: Cursor) -> Result<u32, Failure> {
    u32::try_from(value)
        .map_err(|_| meter.error(FailureKind::ResourceExhausted, "offset_overflow", cursor))
}
fn span(offset: usize, bytes: usize, meter: &Meter<'_>, cursor: Cursor) -> Result<Span, Failure> {
    offset
        .checked_add(bytes)
        .filter(|end| *end <= 4 * 1024 * 1024)
        .ok_or_else(|| meter.error(FailureKind::Malformed, "span_overflow", cursor))?;
    Ok(Span {
        offset: u32_offset(offset, meter, cursor)?,
        bytes: u32_offset(bytes, meter, cursor)?,
    })
}
fn utf8(bytes: &[u8], base: usize, meter: &mut Meter<'_>) -> Result<(), Failure> {
    let mut i = 0;
    while i < bytes.len() {
        let cursor = Cursor {
            function: None,
            offset: base + i,
        };
        meter.work(1, cursor)?;
        let lead = bytes[i];
        let (width, minimum, mut code) = match lead {
            0..=0x7f => (1, 0, lead as u32),
            0xc2..=0xdf => (2, 0x80, (lead & 31) as u32),
            0xe0..=0xef => (3, 0x800, (lead & 15) as u32),
            0xf0..=0xf4 => (4, 0x10000, (lead & 7) as u32),
            _ => return Err(meter.error(FailureKind::Malformed, "name_utf8", cursor)),
        };
        for j in 1..width {
            meter.work(
                1,
                Cursor {
                    function: None,
                    offset: base + i + j,
                },
            )?;
            let b = *bytes
                .get(i + j)
                .ok_or_else(|| meter.error(FailureKind::Malformed, "name_utf8", cursor))?;
            if b & 0xc0 != 0x80 {
                return Err(meter.error(FailureKind::Malformed, "name_utf8", cursor));
            }
            code = (code << 6) | (b & 63) as u32;
        }
        if code < minimum || (0xd800..=0xdfff).contains(&code) || code > 0x10ffff {
            return Err(meter.error(FailureKind::Malformed, "name_utf8", cursor));
        }
        i += width;
    }
    Ok(())
}
fn name(r: &mut Reader<'_>, meter: &mut Meter<'_>) -> Result<Span, Failure> {
    let n = r.count(4096, meter)?;
    let base = r.cursor().offset;
    let bytes = r.take(n, meter)?;
    utf8(bytes, base, meter)?;
    span(base, n, meter, r.cursor())
}
fn constant(
    r: &mut Reader<'_>,
    profile: Profile,
    meter: &mut Meter<'_>,
) -> Result<(Type, Option<u32>), Failure> {
    let result = match r.byte(meter)? {
        0x41 => (Type::I32, Some(r.signed(32, meter)? as u32)),
        0x42 => {
            r.signed(64, meter)?;
            (Type::I64, None)
        }
        0x43 if profile.floats() => {
            r.take(4, meter)?;
            (Type::F32, None)
        }
        0x44 if profile.floats() => {
            r.take(8, meter)?;
            (Type::F64, None)
        }
        _ => return Err(r.error(meter, FailureKind::Unsupported, "constant_expression")),
    };
    if r.byte(meter)? != 0x0b {
        return Err(r.error(meter, FailureKind::Unsupported, "extended_constant"));
    }
    Ok(result)
}
fn limits(r: &mut Reader<'_>, maximum: u32, meter: &mut Meter<'_>) -> Result<(u32, u32), Failure> {
    let flags = r.byte(meter)?;
    if flags > 1 {
        return Err(r.error(meter, FailureKind::Unsupported, "limits_form"));
    }
    let min = r.uint(meter)?;
    let max = if flags == 1 { r.uint(meter)? } else { maximum };
    if min > max {
        return Err(r.error(
            meter,
            FailureKind::Validation,
            "limit_minimum_exceeds_maximum",
        ));
    }
    if max > maximum {
        return Err(r
            .error(
                meter,
                FailureKind::ResourceExhausted,
                "profile_memory_table_limit",
            )
            .resource(Resource::Profile, max as u64, maximum as u64));
    }
    Ok((min, max))
}

pub(super) fn read(
    source: &[u8],
    policy: &Limits,
    meter: &mut Meter<'_>,
) -> Result<Metadata, Failure> {
    let mut r = Reader::new(source, 0);
    if r.take(8, meter)? != b"\0asm\x01\0\0\0" {
        return Err(r.error(meter, FailureKind::Malformed, "wasm_header"));
    }
    let mut m = Metadata::new();
    let mut seen = [false; 12];
    let mut last = 0;
    let mut code_seen = false;
    while r.position < r.bytes.len() {
        let id = r.byte(meter)?;
        let size = r.uint(meter)? as usize;
        let base = r.cursor().offset;
        let data = r.take(size, meter)?;
        let mut s = Reader::new(data, base);
        if id == 0 {
            name(&mut s, meter)?;
            continue;
        }
        if id > 11 {
            return Err(s.error(meter, FailureKind::Unsupported, "section"));
        }
        if seen[id as usize] || id < last {
            return Err(s.error(meter, FailureKind::Malformed, "section_order"));
        }
        seen[id as usize] = true;
        last = id;
        match id {
            1 => {
                let count = s.count(policy.types, meter)?;
                m.signatures.reserve(count, meter, s.cursor())?;
                for _ in 0..count {
                    if s.byte(meter)? != 0x60 {
                        return Err(s.error(meter, FailureKind::Unsupported, "function_type"));
                    }
                    let count = s.count(policy.locals, meter)?;
                    let first = u32_offset(m.parameters.len(), meter, s.cursor())?;
                    for _ in 0..count {
                        let ty = s.ty(policy.profile, meter)?;
                        m.parameters.push(ty, meter, s.cursor())?;
                    }
                    let result = if s.count(1, meter)? == 1 {
                        Some(s.ty(policy.profile, meter)?)
                    } else {
                        None
                    };
                    m.signatures.push(
                        Signature {
                            first,
                            count: count as u32,
                            result,
                        },
                        meter,
                        s.cursor(),
                    )?;
                }
            }
            2 => {
                let count = s.count(policy.functions, meter)?;
                m.imports.reserve(count, meter, s.cursor())?;
                for _ in 0..count {
                    let module = name(&mut s, meter)?;
                    let name = name(&mut s, meter)?;
                    if s.byte(meter)? != 0 {
                        return Err(s.error(meter, FailureKind::Unsupported, "import_kind"));
                    }
                    let type_index = s.uint(meter)?;
                    m.imports.push(
                        Import {
                            module,
                            name,
                            type_index,
                        },
                        meter,
                        s.cursor(),
                    )?;
                }
            }
            3 => {
                let count = s.count(policy.functions.saturating_sub(m.imports.len()), meter)?;
                m.functions.reserve(count, meter, s.cursor())?;
                for _ in 0..count {
                    let type_index = s.uint(meter)?;
                    m.functions.push(
                        Function {
                            type_index,
                            body: Span::default(),
                        },
                        meter,
                        s.cursor(),
                    )?;
                }
            }
            4 if policy.profile == Profile::TableMemoryV3 => {
                if s.count(1, meter)? == 1 {
                    if s.byte(meter)? != 0x70 {
                        return Err(s.error(meter, FailureKind::Unsupported, "table_type"));
                    }
                    m.table = Some(limits(&mut s, policy.table_elements as u32, meter)?);
                }
            }
            5 => {
                if s.count(1, meter)? == 1 {
                    m.memory = Some(limits(&mut s, policy.memory_pages, meter)?);
                }
            }
            6 => {
                let count = s.count(1024, meter)?;
                m.globals.reserve(count, meter, s.cursor())?;
                for _ in 0..count {
                    let ty = s.ty(policy.profile, meter)?;
                    let mutable = match s.byte(meter)? {
                        0 => false,
                        1 => true,
                        _ => {
                            return Err(s.error(meter, FailureKind::Malformed, "global_mutability"))
                        }
                    };
                    let offset = s.cursor().offset;
                    let (actual, _) = constant(&mut s, policy.profile, meter)?;
                    if actual != ty {
                        return Err(s.error(
                            meter,
                            FailureKind::Validation,
                            "global_initializer_type",
                        ));
                    }
                    let initializer = span(offset, s.cursor().offset - offset, meter, s.cursor())?;
                    m.globals.push(
                        Global {
                            ty,
                            mutable,
                            initializer,
                        },
                        meter,
                        s.cursor(),
                    )?;
                }
            }
            7 => {
                let count = s.count(4096, meter)?;
                m.exports.reserve(count, meter, s.cursor())?;
                for _ in 0..count {
                    let name = name(&mut s, meter)?;
                    let kind = s.byte(meter)?;
                    let index = s.uint(meter)?;
                    m.exports
                        .push(Export { name, kind, index }, meter, s.cursor())?;
                }
            }
            9 if policy.profile == Profile::TableMemoryV3 => {
                let mut total = 0;
                let count = s.count(4096, meter)?;
                m.elements.reserve(count, meter, s.cursor())?;
                for _ in 0..count {
                    let flags = s.uint(meter)?;
                    if ![0, 2].contains(&flags) {
                        return Err(s.error(meter, FailureKind::Unsupported, "element_form"));
                    }
                    if flags == 2 && s.uint(meter)? != 0 {
                        return Err(s.error(meter, FailureKind::Validation, "element_table"));
                    }
                    let (_, destination) = constant(&mut s, policy.profile, meter)?;
                    let destination = destination
                        .ok_or_else(|| s.error(meter, FailureKind::Validation, "element_offset"))?;
                    if flags == 2 && s.byte(meter)? != 0 {
                        return Err(s.error(meter, FailureKind::Unsupported, "element_type"));
                    }
                    let count = s.count(policy.table_elements.saturating_sub(total), meter)?;
                    total = total.checked_add(count).ok_or_else(|| {
                        s.error(
                            meter,
                            FailureKind::ResourceExhausted,
                            "element_count_overflow",
                        )
                    })?;
                    let offset = s.cursor().offset;
                    for _ in 0..count {
                        let function = s.uint(meter)?;
                        if function as usize >= m.imports.len() + m.functions.len() {
                            return Err(s.error(
                                meter,
                                FailureKind::Validation,
                                "element_function",
                            ));
                        }
                    }
                    let payload = span(offset, s.cursor().offset - offset, meter, s.cursor())?;
                    m.elements.push(
                        Segment {
                            payload,
                            destination,
                            count: count as u32,
                        },
                        meter,
                        s.cursor(),
                    )?;
                }
            }
            4 | 8 | 9 => return Err(s.error(meter, FailureKind::Unsupported, "profile_section")),
            10 => {
                code_seen = true;
                let count = s.count(policy.functions, meter)?;
                if count != m.functions.len() {
                    return Err(s.error(meter, FailureKind::Validation, "function_code_count"));
                }
                for index in 0..count {
                    let size = s.uint(meter)? as usize;
                    let offset = s.cursor().offset;
                    s.take(size, meter)?;
                    m.functions.get_mut(index).unwrap().body =
                        span(offset, size, meter, s.cursor())?;
                }
            }
            11 => {
                let count = s.count(4096, meter)?;
                m.data.reserve(count, meter, s.cursor())?;
                for _ in 0..count {
                    let flags = s.uint(meter)?;
                    if ![0, 2].contains(&flags) {
                        return Err(s.error(meter, FailureKind::Unsupported, "data_form"));
                    }
                    if flags == 2 && s.uint(meter)? != 0 {
                        return Err(s.error(meter, FailureKind::Validation, "data_memory"));
                    }
                    let (_, destination) = constant(&mut s, policy.profile, meter)?;
                    let destination = destination
                        .ok_or_else(|| s.error(meter, FailureKind::Validation, "data_offset"))?;
                    let size = s.count(policy.module_bytes, meter)?;
                    let offset = s.cursor().offset;
                    s.take(size, meter)?;
                    let payload = span(offset, size, meter, s.cursor())?;
                    m.data.push(
                        Segment {
                            payload,
                            destination,
                            count: size as u32,
                        },
                        meter,
                        s.cursor(),
                    )?;
                }
            }
            _ => return Err(s.error(meter, FailureKind::Malformed, "unknown_section")),
        }
        s.end(meter)?;
    }
    if !m.functions.as_slice().is_empty() && !code_seen {
        return Err(r.error(meter, FailureKind::Validation, "missing_code"));
    }
    for import in m.imports.as_slice() {
        meter.work(18, r.cursor())?;
        let sig = m
            .signatures
            .get(import.type_index as usize)
            .ok_or_else(|| r.error(meter, FailureKind::Validation, "import_type"))?;
        let allowed = import.module.slice(source) == b"mixer"
            && match import.name.slice(source) {
                b"checkpoint" => sig.count == 0 && sig.result.is_none(),
                b"abort" => sig.count == 1 && m.params(*sig) == [Type::I32] && sig.result.is_none(),
                _ => false,
            };
        if !allowed {
            return Err(r.error(meter, FailureKind::Unsupported, "unapproved_import"));
        }
    }
    for f in m.functions.as_slice() {
        meter.work(1, r.cursor())?;
        if f.type_index as usize >= m.signatures.len() {
            return Err(r.error(meter, FailureKind::Validation, "function_type_index"));
        }
    }
    for export in m.exports.as_slice() {
        meter.work(1, r.cursor())?;
        let valid = match export.kind {
            0 => (export.index as usize) < m.imports.len() + m.functions.len(),
            1 => export.index == 0 && m.table.is_some(),
            2 => export.index == 0 && m.memory.is_some(),
            3 => (export.index as usize) < m.globals.len(),
            _ => false,
        };
        if !valid {
            return Err(r.error(meter, FailureKind::Validation, "export_index"));
        }
    }
    if m.data.len() != 0 && m.memory.is_none() {
        return Err(r.error(meter, FailureKind::Validation, "data_without_memory"));
    }
    if m.elements.len() != 0 && m.table.is_none() {
        return Err(r.error(meter, FailureKind::Validation, "elements_without_table"));
    }
    duplicate_exports(source, &m.exports, meter, r.cursor())?;
    Ok(m)
}
fn compare_names(
    a: u32,
    b: u32,
    source: &[u8],
    exports: &Buffer<Export>,
    meter: &mut Meter<'_>,
    cursor: Cursor,
) -> Result<Ordering, Failure> {
    let a = exports.get(a as usize).unwrap().name.slice(source);
    let b = exports.get(b as usize).unwrap().name.slice(source);
    for (a, b) in a.iter().zip(b) {
        meter.work(1, cursor)?;
        let order = a.cmp(b);
        if order != Ordering::Equal {
            return Ok(order);
        }
    }
    meter.work(1, cursor)?;
    Ok(a.len().cmp(&b.len()))
}
fn sift(
    indices: &mut Buffer<u32>,
    mut root: usize,
    end: usize,
    source: &[u8],
    exports: &Buffer<Export>,
    meter: &mut Meter<'_>,
    cursor: Cursor,
) -> Result<(), Failure> {
    loop {
        meter.work(1, cursor)?;
        let child = root
            .checked_mul(2)
            .and_then(|v| v.checked_add(1))
            .ok_or_else(|| meter.error(FailureKind::ResourceExhausted, "sort_index", cursor))?;
        if child >= end {
            return Ok(());
        }
        let mut greater = child;
        if child + 1 < end
            && compare_names(
                *indices.get(child).unwrap(),
                *indices.get(child + 1).unwrap(),
                source,
                exports,
                meter,
                cursor,
            )? == Ordering::Less
        {
            greater += 1;
        }
        if compare_names(
            *indices.get(root).unwrap(),
            *indices.get(greater).unwrap(),
            source,
            exports,
            meter,
            cursor,
        )? != Ordering::Less
        {
            return Ok(());
        }
        indices.swap(root, greater);
        root = greater;
    }
}
fn duplicate_exports(
    source: &[u8],
    exports: &Buffer<Export>,
    meter: &mut Meter<'_>,
    cursor: Cursor,
) -> Result<(), Failure> {
    let count = exports.len();
    let mut indices = Buffer::new(Resource::Scratch);
    indices.reserve(count, meter, cursor)?;
    for i in 0..count {
        indices.push(i as u32, meter, cursor)?;
    }
    for i in (0..count / 2).rev() {
        sift(&mut indices, i, count, source, exports, meter, cursor)?;
    }
    for end in (1..count).rev() {
        meter.work(1, cursor)?;
        indices.swap(0, end);
        sift(&mut indices, 0, end, source, exports, meter, cursor)?;
    }
    for i in 1..count {
        if compare_names(
            *indices.get(i - 1).unwrap(),
            *indices.get(i).unwrap(),
            source,
            exports,
            meter,
            cursor,
        )? == Ordering::Equal
        {
            return Err(meter.error(FailureKind::Validation, "duplicate_export", cursor));
        }
    }
    indices.dispose(meter);
    Ok(())
}
