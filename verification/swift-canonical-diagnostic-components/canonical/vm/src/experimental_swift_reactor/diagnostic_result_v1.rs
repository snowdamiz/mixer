//! Private logical typed-result codec. Every decoded reference and result is unverified.
//! No owner authority, runtime operation, allocation, I/O, hashing or environment access.
#![forbid(unsafe_code)]
// This uninvoked diagnostic module is intentionally private and presently unused
// by production routes. Operational storage admission remains separate work.
#![allow(dead_code)]
use super::control::{
    SwiftCleanupInvariant, SwiftDeadlineOrigin, SwiftLiveUsage, SwiftReservationCategory,
    SwiftReservationUsage, SwiftReservations, SwiftRunFailure, SwiftRunFailureKind,
    SwiftRunResource, SwiftRunStage, SwiftRunUsage,
};
use crate::experimental::swift::SwiftValidationUsage;
use crate::experimental_wasi::{Resource, WasiFailure, WasiReservations, WasiUsage};

pub(crate) const USAGE_BYTES_V1: usize = 512;
pub(crate) const FAILURE_SCALAR_BYTES_V1: usize = 256;
pub(crate) const RESULT_BYTES_V1: usize = 2048;
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum CodecRefusalV1 {
    Extent,
    UnsupportedHostWidth,
    Malformed(&'static str),
}
type Refusal = CodecRefusalV1;
fn exact(bytes: &[u8], size: usize) -> Result<(), Refusal> {
    if bytes.len() == size {
        Ok(())
    } else {
        Err(CodecRefusalV1::Extent)
    }
}
fn supported_host() -> Result<(), Refusal> {
    if usize::BITS <= 64 {
        Ok(())
    } else {
        Err(CodecRefusalV1::UnsupportedHostWidth)
    }
}
fn write_words(output: &mut [u8], words: &[u64]) {
    for (slot, word) in output.as_chunks_mut::<8>().0.iter_mut().zip(words) {
        slot.copy_from_slice(&word.to_le_bytes());
    }
}
macro_rules! closed_enum {
    ($encode:ident, $decode:ident, $ty:ident, {$($name:ident = $id:literal),+ $(,)?}) => {
        fn $encode(value:$ty)->u64 {match value {$($ty::$name=>$id),+}}
        fn $decode(value:u64)->Result<$ty,Refusal> {match value {$($id=>Ok($ty::$name)),+, _=>Err(CodecRefusalV1::Malformed("unknown enum"))}}
    }
}
closed_enum!(category_word, word_category, SwiftReservationCategory, {
    RetainedSource=1,RetainedMetadata=2,Cache=3,State=4,Wasi=5,Shared=6,Construction=7
});
closed_enum!(stage_word, word_stage, SwiftRunStage, {
    Adoption=1,Cache=2,Initialization=3,Invocation=4,Wasi=5,Cleanup=6
});
closed_enum!(kind_word, word_kind, SwiftRunFailureKind, {
    InvalidBudget=1,Cancelled=2,Deadline=3,Allocation=4,Adoption=5,
    CategoryExhausted=6,CombinedExhausted=7,ResourceExhausted=8,FuelExhausted=9,
    WorkExhausted=10,HostCallLimit=11,PinLimit=12,FrameLimit=13,ValueLimit=14,
    ControlLimit=15,DecoderMismatch=16,UnsupportedEnvironment=17,GuestTrap=18,
    GuestExit=19,Wasi=20,Invariant=21
});
closed_enum!(cleanup_word, word_cleanup, SwiftCleanupInvariant, {
    ReservationOwner=1,ReservationUnderflow=2,MissingConstruction=3,ConstructionBound=4,LiveUnderflow=5
});
closed_enum!(origin_word, word_origin, SwiftDeadlineOrigin, {Run=1,Wasi=2});
closed_enum!(wasi_resource_word, word_wasi_resource, Resource, {
    Calls=1,Transfer=2,TransferSize=3,Work=4,Iovecs=5
});
fn resource_words(value: SwiftRunResource) -> (u64, u64) {
    match value {
        SwiftRunResource::Reservation(c) => (1, category_word(c)),
        SwiftRunResource::Combined => (2, 0),
        SwiftRunResource::CacheEntryBytes => (3, 0),
        SwiftRunResource::CacheEntries => (4, 0),
        SwiftRunResource::ActivePins => (5, 0),
        SwiftRunResource::Frames => (6, 0),
        SwiftRunResource::Values => (7, 0),
        SwiftRunResource::Controls => (8, 0),
        SwiftRunResource::MemoryPages => (9, 0),
        SwiftRunResource::CacheWork => (10, 0),
        SwiftRunResource::ExecutionWork => (11, 0),
        SwiftRunResource::InstructionFuel => (12, 0),
        SwiftRunResource::HostCalls => (13, 0),
        SwiftRunResource::Deadline => (14, 0),
        SwiftRunResource::TicketInventory => (15, 0),
        SwiftRunResource::OwnerIdentity => (16, 0),
        SwiftRunResource::ExactCapacity => (17, 0),
    }
}
fn words_resource(tag: u64, payload: u64) -> Result<SwiftRunResource, Refusal> {
    use SwiftRunResource::*;
    if tag == 1 {
        return Ok(Reservation(word_category(payload)?));
    }
    if payload != 0 {
        return Err(CodecRefusalV1::Malformed("inactive reservation payload"));
    }
    Ok(match tag {
        2 => Combined,
        3 => CacheEntryBytes,
        4 => CacheEntries,
        5 => ActivePins,
        6 => Frames,
        7 => Values,
        8 => Controls,
        9 => MemoryPages,
        10 => CacheWork,
        11 => ExecutionWork,
        12 => InstructionFuel,
        13 => HostCalls,
        14 => Deadline,
        15 => TicketInventory,
        16 => OwnerIdentity,
        17 => ExactCapacity,
        _ => return Err(CodecRefusalV1::Malformed("unknown resource")),
    })
}
fn wasi_words(value: WasiFailure) -> (u64, u64) {
    match value {
        WasiFailure::InvalidBudget => (1, 0),
        WasiFailure::Allocation => (2, 0),
        WasiFailure::InvalidArguments => (3, 0),
        WasiFailure::InvalidMemory => (4, 0),
        WasiFailure::Budget(r) => (5, wasi_resource_word(r)),
        WasiFailure::Cancelled => (6, 0),
        WasiFailure::Deadline => (7, 0),
        WasiFailure::Invariant => (8, 0),
    }
}
fn words_wasi(tag: u64, payload: u64) -> Result<WasiFailure, Refusal> {
    if tag == 5 {
        return Ok(WasiFailure::Budget(word_wasi_resource(payload)?));
    }
    if payload != 0 {
        return Err(CodecRefusalV1::Malformed("inactive WASI payload"));
    }
    Ok(match tag {
        1 => WasiFailure::InvalidBudget,
        2 => WasiFailure::Allocation,
        3 => WasiFailure::InvalidArguments,
        4 => WasiFailure::InvalidMemory,
        6 => WasiFailure::Cancelled,
        7 => WasiFailure::Deadline,
        8 => WasiFailure::Invariant,
        _ => return Err(CodecRefusalV1::Malformed("unknown WASI failure")),
    })
}
fn words<const N: usize>(bytes: &[u8]) -> [u64; N] {
    std::array::from_fn(|i| u64::from_le_bytes(bytes[i * 8..i * 8 + 8].try_into().unwrap()))
}
fn widen(n: usize) -> Result<u64, Refusal> {
    u64::try_from(n).map_err(|_| CodecRefusalV1::Malformed("usize exceeds wire"))
}
fn narrow(n: u64) -> Result<usize, Refusal> {
    usize::try_from(n).map_err(|_| CodecRefusalV1::Malformed("wire exceeds usize"))
}

// Exact 64-word logical encoding; no Rust memory representation is copied.
fn usage_words(u: &SwiftRunUsage) -> Result<[u64; 64], Refusal> {
    supported_host()?;
    let mut w = [0u64; 64];
    let r = &u.reservations;
    for (i, v) in [
        r.retained_source,
        r.retained_metadata,
        r.cache,
        r.state,
        r.wasi,
        r.shared,
        r.construction,
        r.combined,
    ]
    .iter()
    .enumerate()
    {
        w[i * 2] = widen(v.current)?;
        w[i * 2 + 1] = widen(v.peak)?;
    }
    w[16] = widen(r.live_tickets)?;
    w[17] = widen(r.peak_tickets)?;
    let l = &u.live;
    for (i, v) in [
        l.cache_entries,
        l.active_pins,
        l.frames,
        l.values,
        l.controls,
        l.memory_pages,
    ]
    .iter()
    .enumerate()
    {
        w[18 + i * 2] = widen(v.current)?;
        w[19 + i * 2] = widen(v.peak)?;
    }
    w[30..35].copy_from_slice(&[
        u.cache_work,
        u.execution_work,
        u.instruction_fuel,
        u.instructions,
        u.host_calls,
    ]);
    w[35] = u.cleanup_invariant.map_or(0, cleanup_word);
    w[36..40].copy_from_slice(&[
        u.elapsed_micros,
        u.deadline_ms,
        origin_word(u.deadline_origin),
        u.deadline_overshoot_micros,
    ]);
    let v = &u.validation;
    w[40..50].copy_from_slice(&[
        widen(v.input_visible_bytes)?,
        widen(v.source_bytes)?,
        widen(v.metadata_reserved)?,
        widen(v.scratch_reserved)?,
        widen(v.metadata_peak_reserved)?,
        widen(v.scratch_peak_reserved)?,
        widen(v.total_peak_reserved)?,
        v.work_used,
        v.elapsed_micros,
        v.deadline_ms,
    ]);
    if let Some(v) = u.wasi {
        let r = v.reservations;
        w[50] = 1;
        w[51..64].copy_from_slice(&[
            v.calls,
            v.work,
            v.transfer_bytes,
            v.random_bytes,
            v.log_bytes,
            v.failures,
            r.fixed_state_bytes,
            r.staging_bytes,
            r.rollback_bytes,
            r.stdout_bytes,
            r.stderr_bytes,
            r.current_bytes,
            r.peak_bytes,
        ]);
    }
    Ok(w)
}
pub(crate) fn decode_usage_v1(raw: &[u8]) -> Result<SwiftRunUsage, Refusal> {
    exact(raw, USAGE_BYTES_V1)?;
    supported_host()?;
    let w = words::<64>(raw);
    let pair = |i| -> Result<SwiftReservationUsage, Refusal> {
        Ok(SwiftReservationUsage {
            current: narrow(w[i])?,
            peak: narrow(w[i + 1])?,
        })
    };
    let v = SwiftValidationUsage {
        input_visible_bytes: narrow(w[40])?,
        source_bytes: narrow(w[41])?,
        metadata_reserved: narrow(w[42])?,
        scratch_reserved: narrow(w[43])?,
        metadata_peak_reserved: narrow(w[44])?,
        scratch_peak_reserved: narrow(w[45])?,
        total_peak_reserved: narrow(w[46])?,
        work_used: w[47],
        elapsed_micros: w[48],
        deadline_ms: w[49],
    };
    let wasi = match w[50] {
        0 => {
            if w[51..64].iter().any(|n| *n != 0) {
                return Err(CodecRefusalV1::Malformed("absent WASI bytes"));
            }
            None
        }
        1 => Some(WasiUsage {
            calls: w[51],
            work: w[52],
            transfer_bytes: w[53],
            random_bytes: w[54],
            log_bytes: w[55],
            failures: w[56],
            reservations: WasiReservations {
                fixed_state_bytes: w[57],
                staging_bytes: w[58],
                rollback_bytes: w[59],
                stdout_bytes: w[60],
                stderr_bytes: w[61],
                current_bytes: w[62],
                peak_bytes: w[63],
            },
        }),
        _ => return Err(CodecRefusalV1::Malformed("WASI presence")),
    };
    Ok(SwiftRunUsage {
        reservations: SwiftReservations {
            retained_source: pair(0)?,
            retained_metadata: pair(2)?,
            cache: pair(4)?,
            state: pair(6)?,
            wasi: pair(8)?,
            shared: pair(10)?,
            construction: pair(12)?,
            combined: pair(14)?,
            live_tickets: narrow(w[16])?,
            peak_tickets: narrow(w[17])?,
        },
        live: SwiftLiveUsage {
            cache_entries: pair(18)?,
            active_pins: pair(20)?,
            frames: pair(22)?,
            values: pair(24)?,
            controls: pair(26)?,
            memory_pages: pair(28)?,
        },
        cache_work: w[30],
        execution_work: w[31],
        instruction_fuel: w[32],
        instructions: w[33],
        host_calls: w[34],
        cleanup_invariant: if w[35] == 0 {
            None
        } else {
            Some(word_cleanup(w[35])?)
        },
        elapsed_micros: w[36],
        deadline_ms: w[37],
        deadline_origin: word_origin(w[38])?,
        deadline_overshoot_micros: w[39],
        validation: v,
        wasi,
    })
}

// The source's &'static code is encoded exactly. Decoder borrows bytes and never
// constructs a fake &'static string or a source-authoritative failure owner.
fn failure_words(f: &SwiftRunFailure) -> Result<[u64; 16], Refusal> {
    supported_host()?;
    if f.code.is_empty() || f.code.len() > 128 || !f.code.bytes().all(|c| (32..=126).contains(&c)) {
        return Err(CodecRefusalV1::Malformed("code extent/ASCII"));
    }
    let mut w = [0u64; 16];
    w[0] = stage_word(f.stage);
    w[1] = kind_word(f.kind);
    w[3] = widen(f.code.len())?;
    if let Some(n) = f.function {
        w[2] |= 1;
        w[4] = u64::from(n);
    }
    if let Some(n) = f.offset {
        w[2] |= 2;
        w[5] = widen(n)?;
    }
    if let Some(r) = f.resource {
        w[2] |= 4;
        (w[6], w[7]) = resource_words(r);
    }
    w[8] = f.attempted;
    w[9] = f.limit;
    if let Some(n) = f.observed_capacity {
        w[2] |= 8;
        w[10] = widen(n)?;
    }
    w[11] = origin_word(f.deadline_origin);
    if let Some(v) = f.wasi_failure {
        w[2] |= 16;
        (w[12], w[13]) = wasi_words(v);
    }
    if let Some(n) = f.guest_exit {
        w[2] |= 32;
        w[14] = u64::from(n);
    }
    Ok(w)
}
#[derive(Debug, PartialEq, Eq)]
pub(crate) struct UnverifiedFailureScalarsV1<'a> {
    stage: SwiftRunStage,
    kind: SwiftRunFailureKind,
    code: &'a str,
    function: Option<u32>,
    offset: Option<usize>,
    resource: Option<SwiftRunResource>,
    attempted: u64,
    limit: u64,
    observed_capacity: Option<usize>,
    deadline_origin: SwiftDeadlineOrigin,
    wasi_failure: Option<WasiFailure>,
    guest_exit: Option<u32>,
}
pub(crate) fn decode_failure_scalar_v1(
    raw: &[u8],
) -> Result<UnverifiedFailureScalarsV1<'_>, Refusal> {
    exact(raw, FAILURE_SCALAR_BYTES_V1)?;
    supported_host()?;
    let w = words::<16>(&raw[..128]);
    if w[2] > 63 || w[3] == 0 || w[3] > 128 || w[15] != 0 {
        return Err(CodecRefusalV1::Malformed("failure framing"));
    }
    let len = narrow(w[3])?;
    if !raw[128..128 + len].iter().all(|c| (32..=126).contains(c))
        || raw[128 + len..].iter().any(|c| *c != 0)
    {
        return Err(CodecRefusalV1::Malformed("code padding/ASCII"));
    }
    for (bit, indices) in [
        (1, &[4][..]),
        (2, &[5][..]),
        (4, &[6, 7][..]),
        (8, &[10][..]),
        (16, &[12, 13][..]),
        (32, &[14][..]),
    ] {
        if w[2] & bit == 0 && indices.iter().any(|i| w[*i] != 0) {
            return Err(CodecRefusalV1::Malformed("inactive optional payload"));
        }
    }
    Ok(UnverifiedFailureScalarsV1 {
        stage: word_stage(w[0])?,
        kind: word_kind(w[1])?,
        code: std::str::from_utf8(&raw[128..128 + len])
            .map_err(|_| CodecRefusalV1::Malformed("code utf8"))?,
        function: if w[2] & 1 == 0 {
            None
        } else {
            Some(u32::try_from(w[4]).map_err(|_| CodecRefusalV1::Malformed("function width"))?)
        },
        offset: if w[2] & 2 == 0 {
            None
        } else {
            Some(narrow(w[5])?)
        },
        resource: if w[2] & 4 == 0 {
            None
        } else {
            Some(words_resource(w[6], w[7])?)
        },
        attempted: w[8],
        limit: w[9],
        observed_capacity: if w[2] & 8 == 0 {
            None
        } else {
            Some(narrow(w[10])?)
        },
        deadline_origin: word_origin(w[11])?,
        wasi_failure: if w[2] & 16 == 0 {
            None
        } else {
            Some(words_wasi(w[12], w[13])?)
        },
        guest_exit: if w[2] & 32 == 0 {
            None
        } else {
            Some(u32::try_from(w[14]).map_err(|_| CodecRefusalV1::Malformed("guest exit width"))?)
        },
    })
}

impl<'a> UnverifiedFailureScalarsV1<'a> {
    pub(crate) fn code(&self) -> &'a str {
        self.code
    }
}

/// Encodes only logical observations. The authentic source object remains borrowed.
pub(crate) fn encode_usage_v1(value: &SwiftRunUsage, output: &mut [u8]) -> Result<(), Refusal> {
    exact(output, USAGE_BYTES_V1)?;
    let words = usage_words(value)?;
    write_words(output, &words);
    Ok(())
}
pub(crate) fn encode_failure_scalar_v1(
    value: &SwiftRunFailure,
    output: &mut [u8],
) -> Result<(), Refusal> {
    exact(output, FAILURE_SCALAR_BYTES_V1)?;
    let words = failure_words(value)?;
    output.fill(0);
    write_words(&mut output[..128], &words);
    output[128..128 + value.code.len()].copy_from_slice(value.code.as_bytes());
    Ok(())
}

/// Opaque claimed bytes, never a file, digest verifier or admission handle.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct UnverifiedResultReferencesV1<'a> {
    pub(crate) raw_original_bytes: u64,
    pub(crate) constructor_tag: u64,
    pub(crate) constructor_bytes: u64,
    pub(crate) raw_original_digest: &'a [u8; 32],
    pub(crate) constructor_digest: &'a [u8; 32],
    pub(crate) session_digest: &'a [u8; 32],
    pub(crate) typed_result_schema_digest: &'a [u8; 32],
    pub(crate) writer_digest: &'a [u8; 32],
}
impl UnverifiedResultReferencesV1<'_> {
    fn validate(&self) -> Result<(), Refusal> {
        match self.constructor_tag {
            0 if self.constructor_bytes == 0 && self.constructor_digest.iter().all(|b| *b == 0) => {
                Ok(())
            }
            1..=8 if (1..=65536).contains(&self.constructor_bytes) => Ok(()),
            _ => Err(CodecRefusalV1::Malformed("constructor reference")),
        }
    }
}
/// after_cleanup is obtained exclusively from the borrowed original failure.
#[derive(Clone, Copy, Debug)]
pub(crate) struct ResultObservationV1<'a> {
    pub(crate) failure: Option<&'a SwiftRunFailure>,
    pub(crate) final_consuming: Option<&'a SwiftRunUsage>,
    pub(crate) references: UnverifiedResultReferencesV1<'a>,
}

/// All fields are private. This view borrows its immutable complete wire input.
/// It does not construct SwiftRunFailure or provide an authority/admission getter.
#[derive(Debug)]
pub(crate) struct UnverifiedResultViewV1<'a> {
    input: &'a [u8],
    references: UnverifiedResultReferencesV1<'a>,
    failure: Option<UnverifiedFailureScalarsV1<'a>>,
    at_failure: Option<SwiftRunUsage>,
    after_cleanup: Option<SwiftRunUsage>,
    final_consuming: Option<SwiftRunUsage>,
}
impl<'a> UnverifiedResultViewV1<'a> {
    pub(crate) fn encoded(&self) -> &'a [u8] {
        self.input
    }
    pub(crate) fn references(&self) -> &UnverifiedResultReferencesV1<'a> {
        &self.references
    }
    pub(crate) fn failure_scalars(&self) -> Option<&UnverifiedFailureScalarsV1<'a>> {
        self.failure.as_ref()
    }
    pub(crate) fn at_failure(&self) -> Option<&SwiftRunUsage> {
        self.at_failure.as_ref()
    }
    pub(crate) fn after_cleanup(&self) -> Option<&SwiftRunUsage> {
        self.after_cleanup.as_ref()
    }
    pub(crate) fn final_consuming(&self) -> Option<&SwiftRunUsage> {
        self.final_consuming.as_ref()
    }
}

pub(crate) fn encode_result_v1(
    value: ResultObservationV1<'_>,
    output: &mut [u8],
) -> Result<(), Refusal> {
    exact(output, RESULT_BYTES_V1)?;
    supported_host()?;
    value.references.validate()?;
    // Every fallible conversion happens before the first caller-buffer write.
    // These fixed-size local word arrays are data storage, not reserved runtime state.
    let scalar = value.failure.map(failure_words).transpose()?;
    let at = value
        .failure
        .map(|f| usage_words(&f.at_failure))
        .transpose()?;
    let after = value
        .failure
        .and_then(|f| f.after_cleanup.as_ref())
        .map(usage_words)
        .transpose()?;
    let final_words = value.final_consuming.map(usage_words).transpose()?;
    let mask = u64::from(scalar.is_some())
        | (u64::from(after.is_some()) << 1)
        | (u64::from(final_words.is_some()) << 2);
    let refs = value.references;
    output.fill(0);
    output[..8].copy_from_slice(b"MIXRES01");
    write_words(
        &mut output[8..64],
        &[
            1,
            2048,
            1,
            mask,
            refs.constructor_tag,
            refs.raw_original_bytes,
            refs.constructor_bytes,
        ],
    );
    for (start, digest) in [
        (64, refs.raw_original_digest),
        (96, refs.constructor_digest),
        (128, refs.session_digest),
        (160, refs.typed_result_schema_digest),
        (192, refs.writer_digest),
    ] {
        output[start..start + 32].copy_from_slice(digest);
    }
    if let (Some(words), Some(failure)) = (scalar.as_ref(), value.failure) {
        write_words(&mut output[256..384], words);
        output[384..384 + failure.code.len()].copy_from_slice(failure.code.as_bytes());
    }
    for (start, data) in [
        (512, at.as_ref()),
        (1024, after.as_ref()),
        (1536, final_words.as_ref()),
    ] {
        if let Some(words) = data {
            write_words(&mut output[start..start + 512], words);
        }
    }
    Ok(())
}

fn require_zero(bytes: &[u8]) -> Result<(), Refusal> {
    if bytes.iter().all(|b| *b == 0) {
        Ok(())
    } else {
        Err(CodecRefusalV1::Malformed("inactive or reserved bytes"))
    }
}
pub(crate) fn decode_result_v1(input: &[u8]) -> Result<UnverifiedResultViewV1<'_>, Refusal> {
    exact(input, RESULT_BYTES_V1)?;
    supported_host()?;
    if &input[..8] != b"MIXRES01" {
        return Err(CodecRefusalV1::Malformed("result magic"));
    }
    let header = words::<8>(&input[..64]);
    if (header[1], header[2], header[3]) != (1, 2048, 1) {
        return Err(CodecRefusalV1::Malformed("result header"));
    }
    let mask = header[4];
    if !matches!(mask, 0 | 1 | 3 | 4 | 5 | 7) {
        return Err(CodecRefusalV1::Malformed("result presence"));
    }
    require_zero(&input[224..256])?;
    // Fixed extents were checked above; these slices are exactly 32 bytes.
    let references = UnverifiedResultReferencesV1 {
        raw_original_bytes: header[6],
        constructor_tag: header[5],
        constructor_bytes: header[7],
        raw_original_digest: input[64..96].try_into().unwrap(),
        constructor_digest: input[96..128].try_into().unwrap(),
        session_digest: input[128..160].try_into().unwrap(),
        typed_result_schema_digest: input[160..192].try_into().unwrap(),
        writer_digest: input[192..224].try_into().unwrap(),
    };
    references.validate()?;
    let (failure, at_failure) = if mask & 1 != 0 {
        (
            Some(decode_failure_scalar_v1(&input[256..512])?),
            Some(decode_usage_v1(&input[512..1024])?),
        )
    } else {
        require_zero(&input[256..1024])?;
        (None, None)
    };
    let after_cleanup = if mask & 2 != 0 {
        Some(decode_usage_v1(&input[1024..1536])?)
    } else {
        require_zero(&input[1024..1536])?;
        None
    };
    let final_consuming = if mask & 4 != 0 {
        Some(decode_usage_v1(&input[1536..2048])?)
    } else {
        require_zero(&input[1536..2048])?;
        None
    };
    Ok(UnverifiedResultViewV1 {
        input,
        references,
        failure,
        at_failure,
        after_cleanup,
        final_consuming,
    })
}

#[cfg(test)]
#[path = "diagnostic_result_v1_tests.rs"]
mod tests;
