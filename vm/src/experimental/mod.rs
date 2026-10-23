//! Complete validation experiment. No executable Module/Instance or C ABI route.
mod account;
mod metadata;
mod reader;
mod validate;

use crate::{Cancellation, Limits, Profile};
use account::{Buffer, Cursor, Meter};
use metadata::Metadata;

/// Additional validation-only ceilings; execution Limits can only narrow frozen profiles.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ValidationBudget {
    pub metadata_bytes: usize,
    pub scratch_bytes: usize,
    pub work_credits: u64,
}
impl Default for ValidationBudget {
    fn default() -> Self {
        Self {
            metadata_bytes: 4 * 1024 * 1024,
            scratch_bytes: 64 * 1024,
            work_credits: 64_000_000,
        }
    }
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Resource {
    Source,
    Metadata,
    Scratch,
    Work,
    /// An unchanged executable-profile count/stack/table/memory ceiling.
    Profile,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum FailureKind {
    Malformed,
    Unsupported,
    Validation,
    ResourceExhausted,
    Cancelled,
    AllocationFailure,
    InvalidLimits,
    InvalidBudget,
}
/// Reservation accounting, including fixed state and growth overlap. These are
/// not OS RSS or directly measured allocator observations.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct Usage {
    pub source_bytes: usize,
    pub metadata_reserved: usize,
    pub scratch_reserved: usize,
    pub metadata_peak_reserved: usize,
    pub scratch_peak_reserved: usize,
    pub total_peak_reserved: usize,
    pub work_used: u64,
}
/// Allocation-free error state. Formatting by the caller is outside validation.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Failure {
    pub kind: FailureKind,
    pub code: &'static str,
    pub function: Option<u32>,
    pub offset: usize,
    pub resource: Option<Resource>,
    pub attempted: u64,
    pub limit: u64,
    pub usage: Usage,
}
impl std::fmt::Display for Failure {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{} at byte {}", self.code, self.offset)
    }
}
impl std::error::Error for Failure {}

/// Sealed validation-only spans, permanently coupled to their private bytes.
/// No Clone, mutation, retargeting, deserialization or executable conversion exists.
///
/// Borrowed spans cannot outlive the owner:
/// ```compile_fail
/// use mixer_vm::{Cancellation, Limits};
/// use mixer_vm::experimental::{validate_spans, ValidationBudget};
/// let proof = validate_spans(b"\0asm\x01\0\0\0", Limits::default(),
///     ValidationBudget::default(), &Cancellation::default()).unwrap();
/// let bytes = proof.source();
/// drop(proof);
/// println!("{}", bytes.len());
/// ```
/// The retained snapshot has no mutable accessor:
/// ```compile_fail
/// use mixer_vm::{Cancellation, Limits};
/// use mixer_vm::experimental::{validate_spans, ValidationBudget};
/// let proof = validate_spans(b"\0asm\x01\0\0\0", Limits::default(),
///     ValidationBudget::default(), &Cancellation::default()).unwrap();
/// proof.source()[0] = 1;
/// ```
pub struct ValidatedSpans {
    source: Box<[u8]>,
    metadata: Metadata,
    limits: Limits,
    usage: Usage,
}
/// Borrowed initializer descriptor, not an instantiated memory/table.
pub struct SegmentView<'a> {
    pub destination: u32,
    pub count: u32,
    /// Data bytes, or the encoded u32 function indices for an element segment.
    pub encoded_payload: &'a [u8],
}
impl ValidatedSpans {
    pub const VALIDATOR_REVISION: u32 = 1;
    pub fn source(&self) -> &[u8] {
        &self.source
    }
    pub fn profile(&self) -> Profile {
        self.limits.profile
    }
    pub fn limits(&self) -> &Limits {
        &self.limits
    }
    pub fn usage(&self) -> Usage {
        self.usage
    }
    pub fn function_count(&self) -> usize {
        self.metadata.imports.len() + self.metadata.functions.len()
    }
    pub fn defined_function_count(&self) -> usize {
        self.metadata.functions.len()
    }
    pub fn instruction_count(&self) -> usize {
        self.metadata.instructions
    }
    pub fn function_body(&self, defined: usize) -> Option<&[u8]> {
        let body = self.metadata.functions.get(defined)?.body;
        let end = (body.offset as usize).checked_add(body.bytes as usize)?;
        self.source.get(body.offset as usize..end)
    }
    pub fn global_initializer(&self, index: usize) -> Option<&[u8]> {
        Some(
            self.metadata
                .globals
                .get(index)?
                .initializer
                .slice(&self.source),
        )
    }
    pub fn data_segment(&self, index: usize) -> Option<SegmentView<'_>> {
        Some(self.segment(self.metadata.data.get(index)?))
    }
    pub fn element_segment(&self, index: usize) -> Option<SegmentView<'_>> {
        Some(self.segment(self.metadata.elements.get(index)?))
    }
    fn segment(&self, segment: &metadata::Segment) -> SegmentView<'_> {
        SegmentView {
            destination: segment.destination,
            count: segment.count,
            encoded_payload: segment.payload.slice(&self.source),
        }
    }
}

/// Fully validate all bodies under frozen profile ceilings and explicit validation
/// budgets. Resource exhaustion/cancellation never yields partial proof state.
pub fn validate_spans(
    input: &[u8],
    limits: Limits,
    budget: ValidationBudget,
    cancellation: &Cancellation,
) -> Result<ValidatedSpans, Failure> {
    let mut meter = Meter::new(budget, cancellation)?;
    let cursor = Cursor::default();
    let scratch_fixed = std::mem::size_of::<Meter<'_>>()
        + 3 * std::mem::size_of::<reader::Reader<'_>>()
        + std::mem::size_of::<validate::BodyState>()
        + std::mem::size_of::<Buffer<u32>>()
        + 2 * std::mem::size_of::<Failure>()
        + 128;
    meter.reserve(Resource::Scratch, scratch_fixed, cursor)?;
    // Match Limits::check without constructing its allocating String error.
    // A failure path must remain usable even when the source allocation fails.
    if !valid_limits(&limits) {
        return Err(meter.error(FailureKind::InvalidLimits, "invalid_limits", cursor));
    }
    if input.len() > limits.module_bytes {
        return Err(meter
            .error(FailureKind::ResourceExhausted, "module_bytes", cursor)
            .resource(
                Resource::Source,
                input.len() as u64,
                limits.module_bytes as u64,
            ));
    }
    meter.reserve(
        Resource::Metadata,
        std::mem::size_of::<ValidatedSpans>(),
        cursor,
    )?;
    meter.check(cursor)?;
    meter.work(input.len() as u64, cursor)?;
    meter.reserve(Resource::Source, input.len(), cursor)?;
    let mut source = Vec::new();
    source
        .try_reserve_exact(input.len())
        .map_err(|_| meter.error(FailureKind::AllocationFailure, "source_allocation", cursor))?;
    if source.capacity() != input.len() {
        return Err(meter.error(FailureKind::AllocationFailure, "source_capacity", cursor));
    }
    source.extend_from_slice(input); // bounded nonpreemptible copy; exact capacity
    meter.check(cursor)?;
    let source = source.into_boxed_slice(); // capacity == length: no shrink allocation
    let mut metadata = metadata::read(&source, &limits, &mut meter)?;
    validate::all(&source, &limits, &mut metadata, &mut meter)?;
    meter.check(cursor)?;
    meter.release(Resource::Scratch, scratch_fixed);
    let usage = meter.usage();
    Ok(ValidatedSpans {
        source,
        metadata,
        limits,
        usage,
    })
}
fn valid_limits(limits: &Limits) -> bool {
    let d = Limits::default();
    limits.table_elements <= d.table_elements
        && limits.module_bytes != 0
        && limits.module_bytes <= d.module_bytes
        && limits.functions != 0
        && limits.functions <= d.functions
        && limits.types != 0
        && limits.types <= d.types
        && limits.instructions != 0
        && limits.instructions <= d.instructions
        && limits.locals <= d.locals
        && limits.operand_stack != 0
        && limits.operand_stack <= d.operand_stack
        && limits.call_depth != 0
        && limits.call_depth <= d.call_depth
        && limits.control_depth != 0
        && limits.control_depth <= d.control_depth
        && limits.memory_pages <= d.memory_pages
        && limits.fuel <= d.fuel
        && limits.host_calls <= d.host_calls
}
impl Failure {
    fn resource(mut self, resource: Resource, attempted: u64, limit: u64) -> Self {
        self.resource = Some(resource);
        self.attempted = attempted;
        self.limit = limit;
        self
    }
}
