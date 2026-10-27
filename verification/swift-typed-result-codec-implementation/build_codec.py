from pathlib import Path
import re
H=Path(__file__).resolve().parent
ROOT=H.parents[1]
P=ROOT/'verification/swift-retained-profile-real-binding-preparation/typed_wire_proposal.rs'
p=P.read_text()
# Mappings and logical field order originate in the selected frozen authored proposal.
s=p[p.index('macro_rules! closed_enum'):p.index('fn ledger(')]
s=s[:s.index('\n#[derive(Debug)]')] + s[s.index('\n#[derive(Debug)]'):]
s=s.replace('fn bytes<const N:usize>(words:&[u64])->[u8;N] {\n    let mut out=[0;N];for (i,w) in words.iter().enumerate(){out[i*8..i*8+8].copy_from_slice(&w.to_le_bytes());}out\n}\n','')
s=s.replace('fn encode_usage(u:&SwiftRunUsage)->Result<[u8;512],Refusal> {','fn usage_words(u:&SwiftRunUsage)->Result<[u64;64],Refusal> {\n    supported_host()?;')
s=s.replace('Ok(bytes(&w))','Ok(w)')
s=s.replace('fn decode_usage(raw:&[u8;512])->Result<SwiftRunUsage,Refusal> {','pub(crate) fn decode_usage_v1(raw:&[u8])->Result<SwiftRunUsage,Refusal> {\n    exact(raw, USAGE_BYTES_V1)?; supported_host()?;')
s=s.replace('fn encode_failure_meta(f:&SwiftRunFailure)->Result<[u8;256],Refusal> {','fn failure_words(f:&SwiftRunFailure)->Result<[u64;16],Refusal> {\n    supported_host()?;')
s=s.replace('    let mut out=[0;256];out[..128].copy_from_slice(&bytes::<128>(&w));out[128..128+f.code.len()].copy_from_slice(f.code.as_bytes());Ok(out)','    Ok(w)')
s=s.replace('f.code.len() as u64', 'widen(f.code.len())?').replace('let len=w[3] as usize;', 'let len=narrow(w[3])?;')
s=s.replace('DecodedFailure','UnverifiedFailureScalarsV1')
s=s.replace('#[derive(Debug)]\nstruct UnverifiedFailureScalarsV1', '#[derive(Debug, PartialEq, Eq)]\npub(crate) struct UnverifiedFailureScalarsV1')
s=s.replace('fn decode_failure_meta(raw:&[u8;256])->Result<UnverifiedFailureScalarsV1<\'_>,Refusal> {','pub(crate) fn decode_failure_scalar_v1(raw:&[u8])->Result<UnverifiedFailureScalarsV1<\'_>,Refusal> {\n    exact(raw, FAILURE_SCALAR_BYTES_V1)?; supported_host()?;')
s=re.sub(r'Err\("([^"\n]*)"\)',r'Err(CodecRefusalV1::Malformed("\1"))',s)
s=re.sub(r'map_err\(\|_\|"([^"\n]*)"\)',r'map_err(|_|CodecRefusalV1::Malformed("\1"))',s)
prefix='''//! Private logical typed-result codec. Every decoded reference and result is unverified.
//! No owner authority, runtime operation, allocation, I/O, hashing or environment access.
#![forbid(unsafe_code)]
// This uninvoked diagnostic module is intentionally private and presently unused
// by production routes. Operational storage admission remains separate work.
#![allow(dead_code)]
use super::control::{SwiftCleanupInvariant, SwiftDeadlineOrigin, SwiftLiveUsage,
    SwiftReservationCategory, SwiftReservationUsage, SwiftReservations, SwiftRunFailure,
    SwiftRunFailureKind, SwiftRunResource, SwiftRunStage, SwiftRunUsage};
use crate::experimental::swift::SwiftValidationUsage;
use crate::experimental_wasi::{Resource, WasiFailure, WasiReservations, WasiUsage};

pub(crate) const USAGE_BYTES_V1: usize = 512;
pub(crate) const FAILURE_SCALAR_BYTES_V1: usize = 256;
pub(crate) const RESULT_BYTES_V1: usize = 2048;
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum CodecRefusalV1 { Extent, UnsupportedHostWidth, Malformed(&'static str) }
type Refusal = CodecRefusalV1;
fn exact(bytes: &[u8], size: usize) -> Result<(), Refusal> {
    if bytes.len() == size { Ok(()) } else { Err(CodecRefusalV1::Extent) }
}
fn supported_host() -> Result<(), Refusal> {
    if usize::BITS <= 64 { Ok(()) } else { Err(CodecRefusalV1::UnsupportedHostWidth) }
}
fn write_words(output: &mut [u8], words: &[u64]) {
    for (slot, word) in output.chunks_exact_mut(8).zip(words) {
        slot.copy_from_slice(&word.to_le_bytes());
    }
}
'''
suffix='''
impl<'a> UnverifiedFailureScalarsV1<'a> {
    pub(crate) fn code(&self) -> &'a str { self.code }
}

/// Encodes only logical observations. The authentic source object remains borrowed.
pub(crate) fn encode_usage_v1(value: &SwiftRunUsage, output: &mut [u8]) -> Result<(), Refusal> {
    exact(output, USAGE_BYTES_V1)?;
    let words = usage_words(value)?;
    write_words(output, &words);
    Ok(())
}
pub(crate) fn encode_failure_scalar_v1(value: &SwiftRunFailure, output: &mut [u8]) -> Result<(), Refusal> {
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
            0 if self.constructor_bytes == 0 && self.constructor_digest.iter().all(|b| *b == 0) => Ok(()),
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
    pub(crate) fn encoded(&self) -> &'a [u8] { self.input }
    pub(crate) fn references(&self) -> &UnverifiedResultReferencesV1<'a> { &self.references }
    pub(crate) fn failure_scalars(&self) -> Option<&UnverifiedFailureScalarsV1<'a>> { self.failure.as_ref() }
    pub(crate) fn at_failure(&self) -> Option<&SwiftRunUsage> { self.at_failure.as_ref() }
    pub(crate) fn after_cleanup(&self) -> Option<&SwiftRunUsage> { self.after_cleanup.as_ref() }
    pub(crate) fn final_consuming(&self) -> Option<&SwiftRunUsage> { self.final_consuming.as_ref() }
}

pub(crate) fn encode_result_v1(value: ResultObservationV1<'_>, output: &mut [u8]) -> Result<(), Refusal> {
    exact(output, RESULT_BYTES_V1)?;
    supported_host()?;
    value.references.validate()?;
    // Every fallible conversion happens before the first caller-buffer write.
    // These fixed-size local word arrays are data storage, not reserved runtime state.
    let scalar = value.failure.map(failure_words).transpose()?;
    let at = value.failure.map(|f| usage_words(&f.at_failure)).transpose()?;
    let after = value.failure.and_then(|f| f.after_cleanup.as_ref()).map(usage_words).transpose()?;
    let final_words = value.final_consuming.map(usage_words).transpose()?;
    let mask = u64::from(scalar.is_some()) | (u64::from(after.is_some()) << 1) | (u64::from(final_words.is_some()) << 2);
    let refs = value.references;
    output.fill(0);
    output[..8].copy_from_slice(b"MIXRES01");
    write_words(&mut output[8..64], &[1, 2048, 1, mask, refs.constructor_tag, refs.raw_original_bytes, refs.constructor_bytes]);
    for (start, digest) in [(64,refs.raw_original_digest),(96,refs.constructor_digest),(128,refs.session_digest),(160,refs.typed_result_schema_digest),(192,refs.writer_digest)] {
        output[start..start+32].copy_from_slice(digest);
    }
    if let (Some(words), Some(failure)) = (scalar.as_ref(), value.failure) {
        write_words(&mut output[256..384], words);
        output[384..384+failure.code.len()].copy_from_slice(failure.code.as_bytes());
    }
    for (start, data) in [(512, at.as_ref()), (1024, after.as_ref()), (1536, final_words.as_ref())] {
        if let Some(words) = data { write_words(&mut output[start..start+512], words); }
    }
    Ok(())
}

fn require_zero(bytes: &[u8]) -> Result<(), Refusal> {
    if bytes.iter().all(|b| *b == 0) { Ok(()) } else { Err(CodecRefusalV1::Malformed("inactive or reserved bytes")) }
}
pub(crate) fn decode_result_v1(input: &[u8]) -> Result<UnverifiedResultViewV1<'_>, Refusal> {
    exact(input, RESULT_BYTES_V1)?;
    supported_host()?;
    if &input[..8] != b"MIXRES01" { return Err(CodecRefusalV1::Malformed("result magic")); }
    let header = words::<8>(&input[..64]);
    if (header[1],header[2],header[3]) != (1,2048,1) { return Err(CodecRefusalV1::Malformed("result header")); }
    let mask = header[4];
    if !matches!(mask, 0 | 1 | 3 | 4 | 5 | 7) { return Err(CodecRefusalV1::Malformed("result presence")); }
    require_zero(&input[224..256])?;
    // Fixed extents were checked above; these slices are exactly 32 bytes.
    let references = UnverifiedResultReferencesV1 {
        raw_original_bytes: header[6], constructor_tag: header[5], constructor_bytes: header[7],
        raw_original_digest: input[64..96].try_into().unwrap(),
        constructor_digest: input[96..128].try_into().unwrap(),
        session_digest: input[128..160].try_into().unwrap(),
        typed_result_schema_digest: input[160..192].try_into().unwrap(),
        writer_digest: input[192..224].try_into().unwrap(),
    };
    references.validate()?;
    let (failure, at_failure) = if mask & 1 != 0 {
        (Some(decode_failure_scalar_v1(&input[256..512])?), Some(decode_usage_v1(&input[512..1024])?))
    } else { require_zero(&input[256..1024])?; (None,None) };
    let after_cleanup = if mask & 2 != 0 { Some(decode_usage_v1(&input[1024..1536])?) }
        else { require_zero(&input[1024..1536])?; None };
    let final_consuming = if mask & 4 != 0 { Some(decode_usage_v1(&input[1536..2048])?) }
        else { require_zero(&input[1536..2048])?; None };
    Ok(UnverifiedResultViewV1 { input, references, failure, at_failure, after_cleanup, final_consuming })
}

#[cfg(test)]
#[path = "diagnostic_result_v1_tests.rs"]
mod tests;
'''
module=H/'source/vm/src/experimental_swift_reactor/diagnostic_result_v1.rs'
module.write_text(prefix+s+suffix)
mod=module.parent/'mod.rs'
mod.write_text(mod.read_text()+'\n// Pure unverified typed-result data; no public export or runtime route.\nmod diagnostic_result_v1;\n')
print('actual module written')
