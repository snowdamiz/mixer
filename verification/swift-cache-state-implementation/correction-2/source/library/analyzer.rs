//! Fixture-only framing foundation. No semantic replay or acceptance authority.
#![forbid(unsafe_code)]
use std::collections::TryReserveError;
use std::fs::File;
use std::io::{self, Read, Seek, Write};
use std::os::unix::fs::MetadataExt;

pub const ARENA_BYTES: usize = 8_388_608;
pub const TRANSIENT_CAP: usize = 65_536;
pub const STEP_LIMIT: u64 = 268_435_456;
pub const REPORT_BYTES: usize = 49_152;
pub const AGGREGATE_REPORT_CAP: usize = 65_536;
const REPORT_RESERVE: u64 = 3_000_000;
const IO_RESERVE: u64 = 263_584;
const SETUP_CAP: u64 = 65_536;
const RECORD_PREFLIGHT: u64 = 8_192;
const RECORD_STEPS: u64 = 22;
const ABSENT: u64 = u64::MAX;
const MAX_RECORDS: u64 = 4_194_304;
const STREAM_CAP: u64 = 536_871_936;
const PROFILE_BYTES: u64 = 2_560_512;
const CONTEXT_BYTES: u64 = 8_192;
const HEADER_MAGIC: u64 = 0x3152_4452_4f58_494d;
const FOOTER_MAGIC: u64 = 0x3144_4e45_4f58_494d;
const PROFILE_MAGIC: u64 = u64::from_le_bytes(*b"MIXPRF01");
const FIXTURE_MAGIC: u64 = u64::from_le_bytes(*b"MIXFIX01");
const REPORT_MAGIC: u64 = u64::from_le_bytes(*b"MIXANL01");

/// Fixed failure observation. No error text, original-result substitution or heap owner.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(C)]
pub struct AnalyzerError { pub code: u32, pub stage: u32, pub offset: u64, pub record: u64, pub reserved: u64 }
fn error(code: u32, stage: u32, offset: u64, record: u64) -> AnalyzerError {
    AnalyzerError { code, stage, offset, record, reserved: 0 }
}
const BOUNDS: u32 = 1;
const ALLOCATION: u32 = 2;
const CAPACITY: u32 = 3;
const BUDGET: u32 = 4;
const INPUT: u32 = 5;
const IO_ERROR: u32 = 6;
const IO_EXHAUSTED: u32 = 7;
const IO_ZERO: u32 = 8;
const IO_OVERREPORTED: u32 = 9;
const SCHEMA: u32 = 10;
const IDENTITY: u32 = 11;
const COORDINATE: u32 = 12;
const FLAGS: u32 = 13;
const DRIFT: u32 = 14;
const BINDING: u32 = 15;
const OUTPUT: u32 = 16;
const INTERNAL: u32 = 17;
const ARENA_STAGE: u32 = 1;
const ADMISSION_STAGE: u32 = 2;
const CONTEXT_STAGE: u32 = 3;
const PROFILE_STAGE: u32 = 4;
const HEADER_STAGE: u32 = 5;
const RECORD_STAGE: u32 = 6;
const FOOTER_STAGE: u32 = 7;
const OUTPUT_STAGE: u32 = 8;

/// Uses only existing design decision IDs. There is deliberately no accepted variant.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u64)]
pub enum Decision { Invalid = 3, AnalysisLimited = 4, Unavailable = 5 }
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(C)]
pub struct ReplayOutcome {
    pub decision: Decision,
    /// Closed syntactic framing count; never an accepted semantic record count.
    pub framed_records: u64,
    pub physical_records: u64,
    pub report_bytes: u64,
    pub steps_used: u64,
    pub input_bytes_read: u64,
    pub input_attempts: u64,
    pub output_attempts: u64,
    pub observation: AnalyzerError,
    fixture_framing: u64,
}
impl ReplayOutcome {
    pub const fn fixture_framing_observed(&self) -> bool { self.fixture_framing == 1 }
    pub const fn stored_prefix_validated(&self) -> bool { false }
    pub const fn full_replay_accepted(&self) -> bool { false }
}

#[derive(Clone, Copy)]
struct Region { base: usize, rows: usize, stride: usize }
const FUNCTION: Region = Region { base: 0, rows: 80_000, stride: 96 };
const RESIDENT: Region = Region { base: 7_680_000, rows: 64, stride: 64 };
const PIN: Region = Region { base: 7_684_096, rows: 64, stride: 48 };
const PLAN: Region = Region { base: 7_687_168, rows: 512, stride: 40 };
const RECENCY: Region = Region { base: 7_707_648, rows: 64, stride: 8 };
const WINDOW: Region = Region { base: 7_708_160, rows: 128, stride: 128 };
const HISTOGRAM: Region = Region { base: 7_724_544, rows: 396, stride: 8 };
const TOP: Region = Region { base: 7_727_712, rows: 32, stride: 64 };
const SCALAR: Region = Region { base: 7_729_760, rows: 512, stride: 8 };
const CONTEXT: Region = Region { base: 7_733_856, rows: 1024, stride: 8 };
const BLOCK: Region = Region { base: 7_742_048, rows: 1, stride: 65_536 };
const REPORT: Region = Region { base: 7_807_584, rows: 8192, stride: 8 };
const REGIONS: [Region; 12] = [FUNCTION, RESIDENT, PIN, PLAN, RECENCY, WINDOW, HISTOGRAM, TOP, SCALAR, CONTEXT, BLOCK, REPORT];

struct Arena { bytes: Vec<u8> }
impl Arena {
    fn new(budget: &mut Budget) -> Result<Self, AnalyzerError> {
        Self::new_with(budget, |v, n| v.try_reserve_exact(n))
    }
    fn new_with(budget: &mut Budget, reserve: fn(&mut Vec<u8>, usize) -> Result<(), TryReserveError>) -> Result<Self, AnalyzerError> {
        let mut bytes = Vec::new();
        reserve(&mut bytes, ARENA_BYTES).map_err(|_| error(ALLOCATION, ARENA_STAGE, 0, 0))?;
        if bytes.capacity() != ARENA_BYTES { return Err(error(CAPACITY, ARENA_STAGE, 0, 0)); }
        let zero = [0u8; 8];
        for _ in 0..ARENA_BYTES / 8 {
            budget.replay(1)?;
            bytes.extend_from_slice(&zero);
        }
        let mut end = 0usize;
        for region in REGIONS {
            budget.setup(1)?;
            let next = region.rows.checked_mul(region.stride).and_then(|n| region.base.checked_add(n)).ok_or(error(BOUNDS, ARENA_STAGE, 0, 0))?;
            if region.base != end || next > ARENA_BYTES { return Err(error(BOUNDS, ARENA_STAGE, 0, 0)); }
            end = next;
        }
        let mut arena = Self { bytes };
        for i in 0..64 { budget.setup(1)?; arena.put64(RESIDENT, i, 8, ABSENT)?; arena.put64(PIN, i, 0, ABSENT)?; arena.put64(RECENCY, i, 0, ABSENT)?; }
        for i in 0..512 { budget.setup(1)?; arena.put64(PLAN, i, 0, ABSENT)?; }
        for i in 0..128 { budget.setup(1)?; arena.put64(WINDOW, i, 14 * 8, ABSENT)?; }
        for i in 0..32 { budget.setup(1)?; arena.put64(TOP, i, 0, ABSENT)?; }
        Ok(arena)
    }
    fn range(region: Region, index: usize, field: usize, width: usize) -> Result<std::ops::Range<usize>, AnalyzerError> {
        let fail = error(BOUNDS, ARENA_STAGE, 0, 0);
        if index >= region.rows || field.checked_add(width).is_none_or(|n| n > region.stride) { return Err(fail); }
        let start = index.checked_mul(region.stride).and_then(|n| region.base.checked_add(n)).and_then(|n| n.checked_add(field)).ok_or(fail)?;
        let end = start.checked_add(width).ok_or(fail)?;
        let region_end = region.rows.checked_mul(region.stride).and_then(|n| region.base.checked_add(n)).ok_or(fail)?;
        if end > region_end || region_end > ARENA_BYTES { return Err(fail); }
        Ok(start..end)
    }
    fn get64(&self, region: Region, row: usize, field: usize) -> Result<u64, AnalyzerError> {
        let bytes = self.bytes.get(Self::range(region, row, field, 8)?).ok_or(error(BOUNDS, ARENA_STAGE, 0, 0))?;
        let mut value = [0; 8]; value.copy_from_slice(bytes); Ok(u64::from_le_bytes(value))
    }
    fn put64(&mut self, region: Region, row: usize, field: usize, value: u64) -> Result<(), AnalyzerError> {
        let bytes = self.bytes.get_mut(Self::range(region, row, field, 8)?).ok_or(error(BOUNDS, ARENA_STAGE, 0, 0))?;
        bytes.copy_from_slice(&value.to_le_bytes()); Ok(())
    }
    fn get32(&self, region: Region, row: usize, field: usize) -> Result<u32, AnalyzerError> {
        let bytes = self.bytes.get(Self::range(region, row, field, 4)?).ok_or(error(BOUNDS, ARENA_STAGE, 0, 0))?;
        let mut value = [0; 4]; value.copy_from_slice(bytes); Ok(u32::from_le_bytes(value))
    }
    fn put32(&mut self, region: Region, row: usize, field: usize, value: u32) -> Result<(), AnalyzerError> {
        let bytes = self.bytes.get_mut(Self::range(region, row, field, 4)?).ok_or(error(BOUNDS, ARENA_STAGE, 0, 0))?;
        bytes.copy_from_slice(&value.to_le_bytes()); Ok(())
    }
}

#[derive(Clone, Copy, Debug)]
struct Budget { limit: u64, replay_left: u64, replay_spent: u64, io_spent: u64, setup_spent: u64, report_spent: u64, read_bytes: u64 }
impl Budget {
    fn new(limit: u64) -> Result<Self, AnalyzerError> {
        if limit > STEP_LIMIT { return Err(error(BUDGET, ARENA_STAGE, 0, 0)); }
        let replay_left = limit.checked_sub(REPORT_RESERVE + IO_RESERVE).ok_or(error(BUDGET, ARENA_STAGE, 0, 0))?;
        Ok(Self { limit, replay_left, replay_spent: 0, io_spent: 0, setup_spent: 0, report_spent: 0, read_bytes: 0 })
    }
    fn replay(&mut self, n: u64) -> Result<(), AnalyzerError> {
        self.replay_left = self.replay_left.checked_sub(n).ok_or(error(BUDGET, RECORD_STAGE, 0, 0))?;
        self.replay_spent += n; Ok(())
    }
    fn setup(&mut self, n: u64) -> Result<(), AnalyzerError> {
        if self.setup_spent.checked_add(n).is_none_or(|v| v > SETUP_CAP) { return Err(error(BUDGET, ADMISSION_STAGE, 0, 0)); }
        self.replay(n)?; self.setup_spent += n; Ok(())
    }
    fn io(&mut self) -> Result<(), AnalyzerError> {
        if self.io_spent == IO_RESERVE { return Err(error(BUDGET, ADMISSION_STAGE, 0, 0)); }
        self.io_spent += 1; Ok(())
    }
    fn report(&mut self, n: u64) -> Result<(), AnalyzerError> {
        if self.report_spent.checked_add(n).is_none_or(|v| v > REPORT_RESERVE) { return Err(error(BUDGET, OUTPUT_STAGE, 0, 0)); }
        self.report_spent += n; Ok(())
    }
    fn used(&self) -> u64 { self.replay_spent + self.io_spent + self.report_spent }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(C)]
struct Stamp { fields: [u64; 8], regular: u64 }
impl Stamp { fn len(self) -> u64 { self.fields[3] } }
trait InputFile: Read { fn stamp(&mut self) -> io::Result<Stamp>; fn position(&mut self) -> io::Result<u64>; }
trait OutputFile: Write { fn stamp(&mut self) -> io::Result<Stamp>; fn position(&mut self) -> io::Result<u64>; }
fn file_stamp(file: &File) -> io::Result<Stamp> {
    let m = file.metadata()?;
    Ok(Stamp { fields: [m.dev(), m.ino(), u64::from(m.mode()), m.len(), m.mtime() as u64, m.mtime_nsec() as u64, m.ctime() as u64, m.ctime_nsec() as u64], regular: u64::from(m.is_file()) })
}
impl InputFile for File { fn stamp(&mut self) -> io::Result<Stamp> { file_stamp(self) } fn position(&mut self) -> io::Result<u64> { self.stream_position() } }
impl OutputFile for File { fn stamp(&mut self) -> io::Result<Stamp> { file_stamp(self) } fn position(&mut self) -> io::Result<u64> { self.stream_position() } }

/// Each assembled input block and each EOF probe gets at most 32 attempts.
fn bounded_read<T: Read>(input: &mut T, out: &mut [u8], budget: &mut Budget, stage: u32, offset: u64) -> Result<(), AnalyzerError> {
    let mut done = 0usize;
    for _ in 0..32 {
        budget.io()?;
        let result = input.read(&mut out[done..]);
        match result {
            Ok(0) => return Err(error(IO_ZERO, stage, offset + done as u64, 0)),
            Ok(n) => { if n > out.len() - done { return Err(error(IO_OVERREPORTED, stage, offset + done as u64, 0)); } budget.read_bytes += n as u64; done += n; if done == out.len() { return Ok(()); } }
            Err(e) => { if e.kind() != io::ErrorKind::Interrupted { return Err(error(IO_ERROR, stage, offset + done as u64, 0)); } }
        }
    }
    Err(error(IO_EXHAUSTED, stage, offset + done as u64, 0))
}
fn eof<T: Read>(input: &mut T, budget: &mut Budget, stage: u32, offset: u64) -> Result<(), AnalyzerError> {
    let mut byte = [0; 1];
    for _ in 0..32 {
        budget.io()?;
        match input.read(&mut byte) {
            Ok(0) => return Ok(()),
            Ok(1) => { budget.read_bytes += 1; return Err(error(INPUT, stage, offset, 0)); }
            Ok(_) => return Err(error(IO_OVERREPORTED, stage, offset, 0)),
            Err(e) => if e.kind() != io::ErrorKind::Interrupted { return Err(error(IO_ERROR, stage, offset, 0)); },
        }
    }
    Err(error(IO_EXHAUSTED, stage, offset, 0))
}
#[derive(Clone, Copy)]
struct Reader { length: u64, loaded: u64, consumed: u64, used: usize, cursor: usize, stage: u32 }
impl Reader {
    fn new(length: u64, stage: u32) -> Self { Self { length, loaded: 0, consumed: 0, used: 0, cursor: 0, stage } }
    fn take<T: InputFile>(&mut self, input: &mut T, arena: &mut Arena, out: &mut [u8], budget: &mut Budget) -> Result<(), AnalyzerError> {
        if self.consumed.checked_add(out.len() as u64).is_none_or(|v| v > self.length) { return Err(error(INPUT, self.stage, self.consumed, 0)); }
        let mut done = 0usize;
        // Caller requests <=512 bytes. At most two buffer slices/refills.
        if out.len() > 512 { return Err(error(INTERNAL, self.stage, self.consumed, 0)); }
        for _ in 0..2 {
            if self.cursor == self.used {
                let n = (self.length - self.loaded).min(65_536) as usize;
                if n == 0 { return Err(error(INPUT, self.stage, self.consumed, 0)); }
                let block = arena.bytes.get_mut(BLOCK.base..BLOCK.base + n).ok_or(error(BOUNDS, ARENA_STAGE, 0, 0))?;
                bounded_read(input, block, budget, self.stage, self.loaded)?;
                self.loaded += n as u64; self.used = n; self.cursor = 0;
            }
            let n = (out.len() - done).min(self.used - self.cursor);
            out[done..done + n].copy_from_slice(&arena.bytes[BLOCK.base + self.cursor..BLOCK.base + self.cursor + n]);
            done += n; self.cursor += n; self.consumed += n as u64;
            if done == out.len() { return Ok(()); }
        }
        Err(error(INTERNAL, self.stage, self.consumed, 0))
    }
    fn words<T: InputFile>(&mut self, input: &mut T, arena: &mut Arena, budget: &mut Budget, words: &mut [u64]) -> Result<(), AnalyzerError> {
        if words.len() > 64 { return Err(error(INTERNAL, self.stage, self.consumed, 0)); }
        let mut raw = [0u8; 512];
        self.take(input, arena, &mut raw[..words.len() * 8], budget)?;
        for (i, word) in words.iter_mut().enumerate() {
            let mut value = [0; 8]; value.copy_from_slice(&raw[8 * i..8 * i + 8]); *word = u64::from_le_bytes(value);
        }
        Ok(())
    }
}

#[derive(Clone, Copy)]
struct Fixture { cap: u64, mask: u64, extent: u64, types: u64, slots: u64, pins: u64, base: u64, capacity: u64, entry: u64 }
fn fixture_context<T: InputFile>(input: &mut T, arena: &mut Arena, budget: &mut Budget) -> Result<Fixture, AnalyzerError> {
    let mut reader = Reader::new(CONTEXT_BYTES, CONTEXT_STAGE);
    for i in 0..1024 {
        budget.setup(1)?;
        let mut word = [0;1]; reader.words(input, arena, budget, &mut word)?;
        arena.put64(CONTEXT, i, 0, word[0])?;
    }
    eof(input, budget, CONTEXT_STAGE, CONTEXT_BYTES)?;
    let mut words = [0u64; 16];
    for (i, v) in words.iter_mut().enumerate() { budget.setup(1)?; *v = arena.get64(CONTEXT, i, 0)?; }
    // This is explicitly a NEW finite-fixture schema, never VerifiedBindingView.
    if words[0] != FIXTURE_MAGIC { return Err(error(BINDING, CONTEXT_STAGE, 0, 0)); }
    if words[1..4] != [1, CONTEXT_BYTES, 1] || words[4] == 0 || words[4] > MAX_RECORDS || words[5] >= 64 || words[5] & 33 != 33 || words[6] == ABSENT || words[7] > u32::MAX as u64 || !(1..=64).contains(&words[8]) || !(1..=64).contains(&words[9]) || words[10] != 1 || words[11] == ABSENT || words[12] == ABSENT || words[11] > words[12] || words[13] == ABSENT || words[14..16] != [0, 0] { return Err(error(SCHEMA, CONTEXT_STAGE, 0, 0)); }
    // Words16..47 are eight opaque fixture digest echoes; remainder is reserved.
    for i in 48..1024 { budget.setup(1)?; if arena.get64(CONTEXT, i, 0)? != 0 { return Err(error(SCHEMA, CONTEXT_STAGE, i as u64 * 8, 0)); } }
    Ok(Fixture { cap: words[4], mask: words[5], extent: words[6], types: words[7], slots: words[8], pins: words[9], base: words[11], capacity: words[12], entry: words[13] })
}
fn profile<T: InputFile>(input: &mut T, arena: &mut Arena, budget: &mut Budget, f: Fixture) -> Result<(), AnalyzerError> {
    let mut reader = Reader::new(PROFILE_BYTES, PROFILE_STAGE);
    let mut header = [0;64]; reader.words(input, arena, budget, &mut header)?;
    budget.setup(64)?;
    let expected = [PROFILE_MAGIC, 1, 512, 32, 80_000, f.extent, f.types, f.slots, f.pins, 1, f.base, f.capacity, f.entry, 0, 0, 0];
    if header[..16] != expected || header[48..64] != [0; 16] { return Err(error(SCHEMA, PROFILE_STAGE, 0, 0)); }
    // Baseline/candidate/schema must match explicit fixture echoes. Other profile
    // digest slots are opaque and unverified; this foundation has no hash authority.
    for (p, c) in [(16usize, 40usize), (20, 44), (28, 20)] {
        for i in 0..4 { budget.setup(1)?; if header[p + i] != arena.get64(CONTEXT, c + i, 0)? { return Err(error(IDENTITY, PROFILE_STAGE, (p + i) as u64 * 8, 0)); } }
    }
    for row in 0..80_000 {
        budget.replay(8)?;
        let mut w = [0;4]; reader.words(input, arena, budget, &mut w)?;
        let defined = w[0] as u32; let ty = w[0] >> 32;
        if defined > 1 || w[3] != 0 || (defined == 0 && (ty != u32::MAX as u64 || w[1] != ABSENT || w[2] != 0)) || (defined == 1 && (ty >= f.types || w[1] == ABSENT || w[2] == ABSENT || w[1].checked_add(w[2]).is_none_or(|end| end > f.extent))) { return Err(error(SCHEMA, PROFILE_STAGE, 512 + row as u64 * 32, 0)); }
        arena.put64(FUNCTION, row, 0, w[1])?; arena.put64(FUNCTION, row, 8, w[2])?;
        arena.put32(FUNCTION, row, 16, ty as u32)?; arena.put32(FUNCTION, row, 20, defined)?;
        arena.put32(FUNCTION, row, 40, u32::MAX)?;
    }
    eof(input, budget, PROFILE_STAGE, PROFILE_BYTES)
}

fn header(arena: &Arena, h: &[u64; 64], f: Fixture, budget: &mut Budget) -> Result<(), AnalyzerError> {
    budget.setup(64)?;
    if h[..10] != [HEADER_MAGIC, 1, 512, 128, 512, f.cap, 80_000, 64, 512, f.mask] || h[10..16] != [0; 6] || h[32..64] != [0; 32] { return Err(error(SCHEMA, HEADER_STAGE, 0, 0)); }
    // selection/schema/baseline/candidate, all explicitly synthetic echoes.
    for (p, c) in [(16usize, 16usize), (20, 20), (24, 40), (28, 44)] {
        for i in 0..4 { budget.setup(1)?; if h[p + i] != arena.get64(CONTEXT, c + i, 0)? { return Err(error(IDENTITY, HEADER_STAGE, (p + i) as u64 * 8, 0)); } }
    }
    Ok(())
}
fn full_identity(arena: &Arena, w: &[u64; 16], f: Fixture, release: bool) -> bool {
    let function = w[6];
    if function >= 80_000 || w[7] == ABSENT || w[9] >= f.types || w[9] > u32::MAX as u64 { return false; }
    let row = function as usize;
    if arena.get32(FUNCTION, row, 20) != Ok(1) || arena.get64(FUNCTION, row, 0) != Ok(w[7]) || arena.get32(FUNCTION, row, 16) != Ok(w[9] as u32) { return false; }
    if release { w[8] == ABSENT }
    else { w[8] != ABSENT && arena.get64(FUNCTION, row, 8) == Ok(w[8]) && w[7].checked_add(w[8]).is_some_and(|n| n <= f.extent) }
}
/// Closed field validation and immutable-profile join ONLY. This is no FSM.
fn record_fields(arena: &Arena, w: &[u64; 16], f: Fixture) -> bool {
    if w[0] == 0 || !(1..=14).contains(&w[1]) || w[2] > 5 { return false; }
    let absent_body = w[7..10] == [ABSENT; 3];
    let no_slots = w[10] == ABSENT && w[11] == ABSENT && w[12] == 0;
    let operation_body = w[3] > 0 && full_identity(arena, w, f, false);
    match w[1] {
        1 => w[3] > 0 && w[6] < 80_000 && absent_body && no_slots && w[13..16] == [0; 3],
        2 => operation_body && w[11] == ABSENT && w[12] == 0 && w[13] <= 1 && w[14..16] == [0; 2] && if w[13] == 0 { w[10] == ABSENT } else { w[10] < f.slots },
        3 => operation_body && no_slots && w[13..15] == [0; 2] && w[15] == w[6] & 511,
        4 => operation_body && no_slots && w[13] <= 2 && (if w[13] == 1 { w[14] < 80_000 && w[14] != w[6] } else { w[14] == ABSENT }) && w[15] == w[6] & 511,
        5 => operation_body && no_slots && w[13] > 0 && w[13] <= f.entry && w[14] == f.base && w[15] == f.capacity && w[14].checked_add(w[13]).is_some_and(|n| n <= w[15]),
        6..=8 => operation_body && w[10] < f.slots && w[11] == ABSENT && w[12] == 0 && w[13] > 0 && w[14..16] == [0; 2],
        9 | 10 => operation_body && no_slots && w[13] > 0 && w[13] <= f.entry && w[14..16] == [0; 2],
        11 => operation_body && w[10] < f.slots && w[11] < f.pins && w[12] > 0 && w[13] <= 1 && w[14] > 0 && (1..=f.pins).contains(&w[15]),
        12 => w[3] == 0 && full_identity(arena, w, f, true) && w[10] < f.slots && w[11] < f.pins && w[12] > 0 && w[13] > 0 && w[14] == 0 && w[15] < f.pins,
        13 => w[3] == 0 && w[6] == ABSENT && absent_body && no_slots && w[13] == w[2] && w[14..16] == [0; 2],
        14 => absent_body && (w[6] == ABSENT || w[6] < 80_000) && no_slots && (1..=21).contains(&w[13]) && (1..=24).contains(&w[14]) && (1..=6).contains(&w[15]),
        _ => false,
    }
}
#[derive(Clone, Copy)]
struct Framing {
    framed: u64, physical: u64, last_work: u64, last_instructions: u64,
    last_operation: u64, phase: u64, mask: u64, flags: u64,
    footer_stored: u64, complete: bool, limited: bool,
}
impl Framing {
    fn new(physical: u64) -> Self { Self { framed: 0, physical, last_work: 0, last_instructions: 0, last_operation: 0, phase: 0, mask: 1, flags: 0, footer_stored: 0, complete: false, limited: false } }
    fn coordinate(&mut self, w: &[u64; 16]) -> bool {
        if w[0] != self.framed + 1 || w[4] < self.last_work || w[5] < self.last_instructions { return false; }
        if w[1] == 13 {
            if w[2] <= self.phase || self.mask & (1 << w[2]) != 0 { return false; }
            self.phase = w[2]; self.mask |= 1 << w[2];
        } else if w[2] != self.phase { return false; }
        // This checks only the writer's operation coordinates, not stage ordering.
        if w[1] == 1 {
            if self.last_operation.checked_add(1) != Some(w[3]) { return false; }
            self.last_operation = w[3];
        } else if ![12, 13, 14].contains(&w[1]) && w[3] != self.last_operation { return false; }
        else if w[1] == 14 && w[3] != 0 && w[3] != self.last_operation { return false; }
        self.last_work = w[4]; self.last_instructions = w[5]; self.framed += 1; true
    }
}
fn footer(h: &[u64; 64], w: &[u64; 64], length: u64, s: &mut Framing, budget: &mut Budget) -> Result<(), AnalyzerError> {
    budget.setup(64)?;
    s.footer_stored = w[2]; s.flags = w[9];
    let fail = error(SCHEMA, FOOTER_STAGE, length - 512, 0);
    if w[0] != FOOTER_MAGIC || w[1] != 1 || w[2] > h[5] || w[2] != s.physical || w[5] != w[2] || w[2].checked_add(w[4]) != Some(w[3]) || w[9] >= 512 || w[35] != h[5] || w[34] > 4_194_336 || w[10] < w[6] || w[11] < w[7] || w[15] >= 64 || w[33] > 5 || w[31] > 5 || w[32] > 1 || w[44..64] != [0; 20] || w[36..44] != h[16..24] || w[2].checked_mul(128).and_then(|n| n.checked_add(1024)) != Some(length) { return Err(fail); }
    if w[12] == 0 {
        if w[13] != 0 || w[14] != ABSENT || w[32] != 0 { return Err(fail); }
    } else if w[12] > 21 || w[13] > 24 || (w[13] == 0 && w[9] & 128 == 0) || !(1..=6).contains(&w[14]) || w[32] != 1 { return Err(fail); }
    if w[9] & !1 != 0 { return Err(error(FLAGS, FOOTER_STAGE, length - 512 + 72, 0)); }
    if w[9] == 0 {
        if w[4] != 0 || w[15] != h[9] || w[33] != 5 { return Err(fail); }
    } else if w[2] != h[5] || w[3] <= w[2] || w[4] == 0 || w[15] != h[9] || w[33] != 5 { return Err(fail); }
    if !s.limited {
        if w[6] != s.last_work || w[7] != s.last_instructions || w[8] != s.last_operation { return Err(error(COORDINATE, FOOTER_STAGE, length - 512, 0)); }
        if w[9] == 0 && (w[33] != s.phase || w[15] != s.mask) { return Err(error(COORDINATE, FOOTER_STAGE, length - 512, 0)); }
        if w[9] == 1 && (s.phase > w[33] || s.mask & !w[15] != 0) { return Err(error(COORDINATE, FOOTER_STAGE, length - 512, 0)); }
    }
    Ok(())
}
fn walk<T: InputFile>(input: &mut T, arena: &mut Arena, budget: &mut Budget, f: Fixture, length: u64, s: &mut Framing) -> Result<(), AnalyzerError> {
    let mut reader = Reader::new(length, HEADER_STAGE);
    let mut h = [0;64]; reader.words(input, arena, budget, &mut h)?;
    header(arena, &h, f, budget)?;
    reader.stage = RECORD_STAGE;
    for index in 0..s.physical {
        if budget.replay_left < RECORD_PREFLIGHT { s.limited = true; break; }
        budget.replay(RECORD_STEPS)?;
        let mut w = [0;16]; reader.words(input, arena, budget, &mut w)?;
        let offset = 512 + index * 128;
        if !record_fields(arena, &w, f) { return Err(error(SCHEMA, RECORD_STAGE, offset, index + 1)); }
        if !s.coordinate(&w) { return Err(error(COORDINATE, RECORD_STAGE, offset, index + 1)); }
    }
    if s.limited {
        // Drain record bytes only. The footer is still independently checked.
        let target = length - 512;
        while reader.consumed < target {
            budget.setup(1)?;
            let available = (reader.used - reader.cursor) as u64;
            let n = available.min(target - reader.consumed);
            reader.cursor += n as usize; reader.consumed += n;
            if reader.consumed == target { break; }
            if reader.cursor != reader.used { return Err(error(INTERNAL, RECORD_STAGE, reader.consumed, 0)); }
            let count = (reader.length - reader.loaded).min(65_536) as usize;
            bounded_read(input, &mut arena.bytes[BLOCK.base..BLOCK.base + count], budget, RECORD_STAGE, reader.loaded)?;
            reader.loaded += count as u64; reader.used = count; reader.cursor = 0;
        }
    }
    reader.stage = FOOTER_STAGE;
    let mut foot = [0;64]; reader.words(input, arena, budget, &mut foot)?;
    footer(&h, &foot, length, s, budget)?;
    eof(input, budget, FOOTER_STAGE, length)?;
    s.complete = !s.limited;
    Ok(())
}

fn initial<I: InputFile>(input: &mut I, budget: &mut Budget) -> Result<Stamp, AnalyzerError> {
    budget.setup(2)?;
    let stamp = input.stamp().map_err(|_| error(IO_ERROR, ADMISSION_STAGE, 0, 0))?;
    let position = input.position().map_err(|_| error(IO_ERROR, ADMISSION_STAGE, 0, 0))?;
    if stamp.regular != 1 || position != 0 { return Err(error(INPUT, ADMISSION_STAGE, position, 0)); }
    Ok(stamp)
}
fn stable<I: InputFile>(input: &mut I, before: Stamp, budget: &mut Budget) -> Result<(), AnalyzerError> {
    budget.setup(1)?;
    if input.stamp().map_err(|_| error(IO_ERROR, ADMISSION_STAGE, 0, 0))? != before { return Err(error(DRIFT, ADMISSION_STAGE, 0, 0)); }
    Ok(())
}
fn output_safety<S: InputFile, P: InputFile, C: InputFile, O: OutputFile>(stream: &mut S, profile: &mut P, context: &mut C, output: &mut O, budget: &mut Budget) -> Result<Stamp, AnalyzerError> {
    budget.setup(15)?; // four metadata, position, four outer/six pairwise loops
    let a = stream.stamp().map_err(|_| error(IO_ERROR, ADMISSION_STAGE, 0, 0))?;
    let b = profile.stamp().map_err(|_| error(IO_ERROR, ADMISSION_STAGE, 0, 0))?;
    let c = context.stamp().map_err(|_| error(IO_ERROR, ADMISSION_STAGE, 0, 0))?;
    let d = output.stamp().map_err(|_| error(IO_ERROR, OUTPUT_STAGE, 0, 0))?;
    let pos = output.position().map_err(|_| error(IO_ERROR, OUTPUT_STAGE, 0, 0))?;
    if d.regular != 1 || d.len() != 0 || pos != 0 { return Err(error(OUTPUT, OUTPUT_STAGE, pos, 0)); }
    let all = [a,b,c,d];
    for i in 0..4 {
        if all[i].fields[1] == 0 { return Err(error(BINDING, ADMISSION_STAGE, 0, 0)); }
        for j in i+1..4 { if all[i].fields[..2] == all[j].fields[..2] { return Err(error(BINDING, ADMISSION_STAGE, 0, 0)); } }
    }
    Ok(d)
}
fn write_report<O: OutputFile>(output: &mut O, output_initial: Stamp, arena: &mut Arena, budget: &mut Budget, outcome: &mut ReplayOutcome, s: Framing) -> Result<(), AnalyzerError> {
    // Semantic metrics, digests unavailable without fixture context, and all
    // reserved bytes stay zero. No semantic arena rows are copied to the report.
    let mut header = [0u64; 32];
    header[0] = REPORT_MAGIC; header[1] = 1; header[2] = REPORT_BYTES as u64;
    header[3] = outcome.decision as u64; header[4] = 0; header[5] = 0;
    header[6] = s.physical; header[7] = s.footer_stored;
    header[10] = match outcome.decision { Decision::Invalid => if outcome.observation.code == FLAGS { 9 } else { 8 }, Decision::AnalysisLimited => 1, Decision::Unavailable => 7 };
    header[14] = s.flags; header[15] = outcome.fixture_framing;
    header[22] = ABSENT; header[29] = if (IO_ERROR..=IO_OVERREPORTED).contains(&outcome.observation.code) { outcome.observation.code as u64 } else { 0 };
    header[30] = outcome.observation.record;
    // Count all 6144 fixed 8-byte serializations, including the reserved zeros.
    for row in 0..REPORT_BYTES / 8 { budget.report(1)?; arena.put64(REPORT, row, 0, 0)?; }
    for (i, value) in header.iter().enumerate() { budget.report(1)?; arena.put64(REPORT, i, 0, *value)?; }
    // Explicit opaque echoes. They are never validated cryptographic bindings.
    for i in 0..32 { budget.report(1)?; let value = arena.get64(CONTEXT, 16 + i, 0)?; arena.put64(REPORT, 32 + i, 0, value)?; }
    let output_before = output.stamp().map_err(|_| error(IO_ERROR, OUTPUT_STAGE, 0, 0))?;
    let output_position = output.position().map_err(|_| error(IO_ERROR, OUTPUT_STAGE, 0, 0))?;
    budget.report(2)?;
    if output_before != output_initial || output_before.regular != 1 || output_before.len() != 0 || output_position != 0 { return Err(error(OUTPUT, OUTPUT_STAGE, output_position, 0)); }
    // Reserve all 32 attempts before encoding the final steps field: steps_used
    // is the conservative consumed/reserved authored cost, not a measured count.
    budget.report(35)?; // final step-field encode, <=32 writes, two post-write calls
    outcome.steps_used = budget.used();
    arena.put64(REPORT, 9, 0, outcome.steps_used)?;
    let bytes = &arena.bytes[REPORT.base..REPORT.base + REPORT_BYTES];
    let mut done = 0usize;
    for _ in 0..32 {
        outcome.output_attempts += 1;
        match output.write(&bytes[done..]) {
            Ok(0) => return Err(error(IO_ZERO, OUTPUT_STAGE, done as u64, 0)),
            Ok(n) => { if n > bytes.len() - done { return Err(error(IO_OVERREPORTED, OUTPUT_STAGE, done as u64, 0)); } done += n; if done == bytes.len() { break; } }
            Err(e) => if e.kind() != io::ErrorKind::Interrupted { return Err(error(IO_ERROR, OUTPUT_STAGE, done as u64, 0)); },
        }
    }
    if done != REPORT_BYTES { return Err(error(IO_EXHAUSTED, OUTPUT_STAGE, done as u64, 0)); }
    let after = output.stamp().map_err(|_| error(IO_ERROR, OUTPUT_STAGE, done as u64, 0))?;
    let position = output.position().map_err(|_| error(IO_ERROR, OUTPUT_STAGE, done as u64, 0))?;
    if after.regular != 1 || after.len() != REPORT_BYTES as u64 || after.fields[..3] != output_before.fields[..3] || position != REPORT_BYTES as u64 { return Err(error(DRIFT, OUTPUT_STAGE, done as u64, 0)); }
    outcome.report_bytes = REPORT_BYTES as u64;
    Ok(())
}

/// All four arguments are safe borrows of already-open files. The caller owns
/// their lifetime and must supply distinct, quiescent regular files at offset0;
/// output is an empty exclusive file. This library does not prove host custody.
/// Only MIXFIX01 fixture contexts are supported. Real adapters are unavailable.
pub fn analyze_fixture(stream: &mut File, profile_file: &mut File, context: &mut File, output: &mut File) -> Result<ReplayOutcome, AnalyzerError> {
    analyze_core(stream, profile_file, context, output, STEP_LIMIT)
}
fn observe_inputs<S: InputFile, P: InputFile, C: InputFile>(stream: &mut S, profile_file: &mut P, context: &mut C, arena: &mut Arena, budget: &mut Budget, s: &mut Framing) -> Result<bool, AnalyzerError> {
    let before_s = initial(stream, budget)?;
    let before_p = initial(profile_file, budget)?;
    let before_c = initial(context, budget)?;
    if before_s.len() < 1024 || before_s.len() > STREAM_CAP || (before_s.len() - 1024) % 128 != 0 || before_p.len() != PROFILE_BYTES || before_c.len() != CONTEXT_BYTES { return Err(error(INPUT, ADMISSION_STAGE, 0, 0)); }
    s.physical = (before_s.len() - 1024) / 128;
    let f = fixture_context(context, arena, budget)?;
    profile(profile_file, arena, budget, f)?;
    walk(stream, arena, budget, f, before_s.len(), s)?;
    stable(stream, before_s, budget)?; stable(profile_file, before_p, budget)?; stable(context, before_c, budget)?;
    Ok(s.complete)
}
fn analyze_core<S: InputFile, P: InputFile, C: InputFile, O: OutputFile>(stream: &mut S, profile_file: &mut P, context: &mut C, output: &mut O, limit: u64) -> Result<ReplayOutcome, AnalyzerError> {
    let mut budget = Budget::new(limit)?;
    // No report is attempted unless a fresh, distinct output can be established.
    // Existing File borrows do not by themselves establish inode/OFD ownership.
    let output_initial = output_safety(stream, profile_file, context, output, &mut budget)?;
    let mut arena = Arena::new(&mut budget)?;
    let mut s = Framing::new(0);
    let mut observation = error(BINDING, CONTEXT_STAGE, 0, 0);
    let mut decision = Decision::Unavailable;
    let mut framed = false;
    let result = observe_inputs(stream, profile_file, context, &mut arena, &mut budget, &mut s);
    if let Err(e) = result {
        observation = e;
        decision = if e.code == BINDING { Decision::Unavailable } else if e.code == BUDGET { Decision::AnalysisLimited } else { Decision::Invalid };
    } else if s.limited { observation = error(BUDGET, RECORD_STAGE, 512 + s.framed * 128, s.framed + 1); decision = Decision::AnalysisLimited; }
    else { framed = result.unwrap_or(false); }
    let mut outcome = ReplayOutcome { decision, framed_records: s.framed, physical_records: s.physical, report_bytes: 0, steps_used: 0, input_bytes_read: budget.read_bytes, input_attempts: budget.io_spent, output_attempts: 0, observation, fixture_framing: u64::from(framed) };
    write_report(output, output_initial, &mut arena, &mut budget, &mut outcome, s)?;
    if budget.used() > budget.limit { return Err(error(BUDGET, OUTPUT_STAGE, 0, 0)); }
    Ok(outcome)
}

#[cfg(test)]
#[path = "../tests/fixture_tests.rs"]
mod tests;

#[path = "envelope.rs"]
mod fixture_envelope;
#[cfg_attr(test, allow(unused_imports))]
pub use fixture_envelope::{analyze_fixture_envelope_v1, FixtureEnvelopeBoundaryV1, FixtureEnvelopeReasonV1, FixtureEnvelopeObservationV1, FixtureEnvelopeOutcomeV1};
pub use fixture_envelope::{analyze_fixture_cache_state_v1, FixtureCacheStateBoundaryV1, FixtureCacheStateReasonV1, FixtureCacheStateObservationV1, FixtureCacheStateOutcomeV1};
#[cfg(all(test, inherited_transport))]
include!("../regression/private_io_tests.rs");
