//! Implementation stays inside the private validator boundary.
use super::descriptors::{
    FunctionSpanView, GlobalView, MemoryExecutionView, SegmentExecutionView, SignatureView,
    TableExecutionView,
};
use super::*;
use crate::experimental_wasi::WasiFunction;
use crate::Type;
type SwiftMetadata = Metadata<metadata::SwiftDeclaration>;
use std::time::{Duration, Instant};

/// Independent narrowing-only budgets. Zero is an exhausted budget.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct SwiftValidationBudget {
    pub source_bytes: usize,
    pub metadata_bytes: usize,
    pub scratch_bytes: usize,
    pub work_credits: u64,
    pub deadline_ms: u64,
}
impl Default for SwiftValidationBudget {
    fn default() -> Self {
        Self {
            source_bytes: 64 * 1024 * 1024,
            metadata_bytes: 16 * 1024 * 1024,
            scratch_bytes: 1024 * 1024,
            work_credits: 512_000_000,
            deadline_ms: 120_000,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SwiftValidationFailureKind {
    Malformed,
    Unsupported,
    Validation,
    AbiShape,
    ResourceExhausted,
    Cancelled,
    Deadline,
    InvalidBudget,
    AllocationFailure,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SwiftValidationResource {
    Source,
    Metadata,
    Scratch,
    Work,
    StaticPolicy,
}

/// Internal simultaneous reservations, including fixed state and growth overlap.
/// Input visible bytes are not a measurement of external allocation capacity.
/// None of these values is RSS or includes allocator overhead.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct SwiftValidationUsage {
    pub input_visible_bytes: usize,
    pub source_bytes: usize,
    pub metadata_reserved: usize,
    pub scratch_reserved: usize,
    pub metadata_peak_reserved: usize,
    pub scratch_peak_reserved: usize,
    pub total_peak_reserved: usize,
    pub work_used: u64,
    pub elapsed_micros: u64,
    pub deadline_ms: u64,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct SwiftValidationFailure {
    pub kind: SwiftValidationFailureKind,
    pub code: &'static str,
    /// Absolute function index, including the 34 imports, when in a body.
    pub function: Option<u32>,
    /// Absolute source byte offset.
    pub offset: usize,
    pub resource: Option<SwiftValidationResource>,
    pub attempted: u64,
    pub limit: u64,
    pub usage: SwiftValidationUsage,
}
impl std::fmt::Display for SwiftValidationFailure {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{} at byte {}", self.code, self.offset)
    }
}
impl std::error::Error for SwiftValidationFailure {}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct SwiftReactorObservations {
    pub types: usize,
    pub type_parameters: usize,
    pub imported_functions: usize,
    pub defined_functions: usize,
    pub validated_bodies: usize,
    pub instructions: usize,
    pub globals: usize,
    pub exports: usize,
    pub data_segments: usize,
    pub element_segments: usize,
    pub max_parameters_plus_locals: usize,
    pub max_operand_values: usize,
    pub max_control_depth: usize,
    pub memory_minimum: u32,
    pub memory_declared_maximum: Option<u32>,
    pub memory_host_maximum: u32,
    pub table_minimum: u32,
    pub table_declared_maximum: Option<u32>,
}

/// Complete validation under a fixed experimental policy and exact structural ABI.
/// It does not attest a digest, origin, behavior, package admission or execution.
/// There is no mutable accessor, Clone, deserializer or executable conversion.
///
/// A proof cannot be fabricated:
/// ```compile_fail
/// use mixer_vm::experimental_swift_reactor::ValidatedSwiftReactor;
/// let proof = ValidatedSwiftReactor {};
/// ```
/// It cannot be used by the legacy executable cache:
/// ```compile_fail
/// use mixer_vm::experimental::ValidatedSpans;
/// use mixer_vm::experimental_swift_reactor::ValidatedSwiftReactor;
/// fn needs_legacy(_: ValidatedSpans) {}
/// fn forbidden(proof: ValidatedSwiftReactor) { needs_legacy(proof); }
/// ```
/// The immutable source cannot be changed:
/// ```compile_fail
/// use mixer_vm::experimental_swift_reactor::ValidatedSwiftReactor;
/// fn forbidden(proof: ValidatedSwiftReactor) { proof.source()[0] = 1; }
/// ```
/// The authority is not cloneable:
/// ```compile_fail
/// use mixer_vm::experimental_swift_reactor::ValidatedSwiftReactor;
/// fn forbidden(proof: ValidatedSwiftReactor) { let _ = proof.clone(); }
/// ```
/// Its source borrow cannot escape its owner:
/// ```compile_fail
/// use mixer_vm::experimental_swift_reactor::ValidatedSwiftReactor;
/// fn forbidden(proof: ValidatedSwiftReactor) -> &'static [u8] { proof.source() }
/// ```
pub struct ValidatedSwiftReactor {
    source: Box<[u8]>,
    metadata: SwiftMetadata,
    policy: policy::Policy<'static>,
    imports: [WasiFunction; 34],
    usage: SwiftValidationUsage,
    observations: SwiftReactorObservations,
}
impl ValidatedSwiftReactor {
    pub const VALIDATOR_REVISION: u32 = 1;
    pub fn source(&self) -> &[u8] {
        &self.source
    }
    pub fn policy_identity(&self) -> &'static str {
        match self.policy {
            policy::Policy::SwiftReactorExperimentV1 => "swift-reactor-experiment-v1",
            policy::Policy::Frozen(_) => unreachable!("sealed Swift policy"),
        }
    }
    pub fn usage(&self) -> SwiftValidationUsage {
        self.usage
    }
    pub fn observations(&self) -> SwiftReactorObservations {
        self.observations
    }
    pub fn resolved_import(&self, index: usize) -> Option<WasiFunction> {
        self.imports.get(index).copied()
    }
    pub fn function_body(&self, defined: usize) -> Option<&[u8]> {
        Some(
            self.metadata
                .functions
                .get(defined)?
                .body
                .slice(&self.source),
        )
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

// These borrows preserve the sealed owner and its original metadata/source.
// They are not a second validation or execution authority. Consumers charge
// their own bounded work before scans; individual descriptor lookups allocate
// nothing and do not change validation usage.
#[allow(dead_code)] // Prerequisite for the later private execution/cache stage.
impl ValidatedSwiftReactor {
    pub(crate) fn execution_signature(&self, absolute: u32) -> Option<SignatureView<'_>> {
        let signature = self.metadata.signature(absolute)?;
        Some(SignatureView {
            params: self.metadata.params(signature),
            result: signature.result,
        })
    }

    pub(crate) fn execution_type(&self, type_index: u32) -> Option<SignatureView<'_>> {
        let signature = *self.metadata.signatures.get(type_index as usize)?;
        Some(SignatureView {
            params: self.metadata.params(signature),
            result: signature.result,
        })
    }

    pub(crate) fn execution_function(&self, absolute: u32) -> Option<FunctionSpanView<'_>> {
        let defined = absolute.checked_sub(self.imports.len() as u32)?;
        let function = self.metadata.functions.get(defined as usize)?;
        Some(FunctionSpanView {
            absolute_index: absolute,
            type_index: function.type_index,
            body_offset: function.body.offset as usize,
            body: function.body.slice(&self.source),
        })
    }

    pub(crate) fn execution_global_count(&self) -> usize {
        self.metadata.globals.len()
    }

    pub(crate) fn execution_global(&self, index: usize) -> Option<GlobalView<'_>> {
        let global = self.metadata.globals.get(index)?;
        Some(GlobalView {
            ty: global.ty,
            mutable: global.mutable,
            initializer: global.initializer.slice(&self.source),
        })
    }

    pub(crate) fn execution_global_initializer_offset(&self, index: usize) -> Option<usize> {
        Some(self.metadata.globals.get(index)?.initializer.offset as usize)
    }

    pub(crate) fn execution_data_count(&self) -> usize {
        self.metadata.data.len()
    }

    pub(crate) fn execution_data(&self, index: usize) -> Option<SegmentExecutionView<'_>> {
        Some(self.execution_segment(self.metadata.data.get(index)?))
    }

    pub(crate) fn execution_element_count(&self) -> usize {
        self.metadata.elements.len()
    }

    pub(crate) fn execution_element(&self, index: usize) -> Option<SegmentExecutionView<'_>> {
        Some(self.execution_segment(self.metadata.elements.get(index)?))
    }

    fn execution_segment(&self, segment: &metadata::Segment) -> SegmentExecutionView<'_> {
        SegmentExecutionView {
            destination: segment.destination,
            count: segment.count,
            payload_offset: segment.payload.offset as usize,
            encoded_payload: segment.payload.slice(&self.source),
        }
    }

    pub(crate) fn execution_memory(&self) -> Option<MemoryExecutionView> {
        let (minimum, host_maximum) = self.metadata.memory?;
        Some(MemoryExecutionView {
            minimum,
            declared_maximum: self.metadata.declarations.memory_maximum,
            host_maximum,
        })
    }

    pub(crate) fn execution_table(&self) -> Option<TableExecutionView> {
        let (minimum, host_maximum) = self.metadata.table?;
        Some(TableExecutionView {
            minimum,
            declared_maximum: self.metadata.declarations.table_maximum,
            host_maximum,
        })
    }

    pub(crate) fn execution_imports(&self) -> &[WasiFunction; 34] {
        &self.imports
    }

    pub(crate) fn decode_policy(&self) -> &policy::Policy<'static> {
        &self.policy
    }
}

fn usage(raw: Usage, input: usize, started: Instant, deadline_ms: u64) -> SwiftValidationUsage {
    SwiftValidationUsage {
        input_visible_bytes: input,
        source_bytes: raw.source_bytes,
        metadata_reserved: raw.metadata_reserved,
        scratch_reserved: raw.scratch_reserved,
        metadata_peak_reserved: raw.metadata_peak_reserved,
        scratch_peak_reserved: raw.scratch_peak_reserved,
        total_peak_reserved: raw.total_peak_reserved,
        work_used: raw.work_used,
        elapsed_micros: u64::try_from(started.elapsed().as_micros()).unwrap_or(u64::MAX),
        deadline_ms,
    }
}
fn failure(
    raw: Failure,
    input: usize,
    started: Instant,
    deadline_ms: u64,
) -> SwiftValidationFailure {
    let kind = match raw.code {
        "swift_deadline" => SwiftValidationFailureKind::Deadline,
        "swift_import_count" | "swift_import_order" | "swift_import_abi" | "swift_memory_shape"
        | "swift_table_shape" | "swift_export_count" | "swift_export_abi" => {
            SwiftValidationFailureKind::AbiShape
        }
        _ => match raw.kind {
            FailureKind::Malformed => SwiftValidationFailureKind::Malformed,
            FailureKind::Unsupported => SwiftValidationFailureKind::Unsupported,
            FailureKind::Validation => SwiftValidationFailureKind::Validation,
            FailureKind::ResourceExhausted => SwiftValidationFailureKind::ResourceExhausted,
            FailureKind::Cancelled => SwiftValidationFailureKind::Cancelled,
            FailureKind::AllocationFailure => SwiftValidationFailureKind::AllocationFailure,
            FailureKind::InvalidLimits | FailureKind::InvalidBudget => {
                SwiftValidationFailureKind::InvalidBudget
            }
        },
    };
    SwiftValidationFailure {
        kind,
        code: raw.code,
        function: raw.function,
        offset: raw.offset,
        resource: raw.resource.map(|r| match r {
            Resource::Source => SwiftValidationResource::Source,
            Resource::Metadata => SwiftValidationResource::Metadata,
            Resource::Scratch => SwiftValidationResource::Scratch,
            Resource::Work => SwiftValidationResource::Work,
            Resource::Profile => SwiftValidationResource::StaticPolicy,
        }),
        attempted: raw.attempted,
        limit: raw.limit,
        usage: usage(raw.usage, input, started, deadline_ms),
    }
}

/// Validate every body, then seal one immutable non-executable owner. Checks and
/// deadline are cooperative; one allocator operation cannot be preempted.
#[allow(clippy::result_large_err)] // Inline diagnostics must survive allocation failure.
pub fn validate_swift_reactor(
    input: &[u8],
    budget: SwiftValidationBudget,
    cancellation: &Cancellation,
) -> Result<ValidatedSwiftReactor, SwiftValidationFailure> {
    let started = Instant::now();
    validate(input, budget, cancellation, started)
        .map_err(|raw| failure(raw, input.len(), started, budget.deadline_ms))
}

fn validate(
    input: &[u8],
    budget: SwiftValidationBudget,
    cancellation: &Cancellation,
    started: Instant,
) -> Result<ValidatedSwiftReactor, Failure> {
    let max = SwiftValidationBudget::default();
    let deadline = started.checked_add(Duration::from_millis(budget.deadline_ms));
    // No allocation, source read or work takes place before rejecting widening.
    if budget.source_bytes > max.source_bytes
        || budget.metadata_bytes > max.metadata_bytes
        || budget.scratch_bytes > max.scratch_bytes
        || budget.work_credits > max.work_credits
        || budget.deadline_ms > max.deadline_ms
        || deadline.is_none()
    {
        return Err(Failure {
            kind: FailureKind::InvalidBudget,
            code: "invalid_swift_validation_budget",
            function: None,
            offset: 0,
            resource: None,
            attempted: 0,
            limit: 0,
            usage: Usage::default(),
        });
    }
    let mut meter = Meter::swift(
        ValidationBudget {
            metadata_bytes: budget.metadata_bytes,
            scratch_bytes: budget.scratch_bytes,
            work_credits: budget.work_credits,
        },
        budget.source_bytes,
        cancellation,
        deadline.unwrap(),
    );
    let cursor = Cursor::default();
    meter.check(cursor)?;
    let policy = policy::Policy::swift();
    let scratch_fixed = std::mem::size_of::<Meter<'_, account::SwiftControl>>()
        + 3 * std::mem::size_of::<reader::Reader<'_>>()
        + std::mem::size_of::<validate::BodyState>()
        + std::mem::size_of::<Buffer<u32>>()
        + 2 * std::mem::size_of::<SwiftValidationFailure>()
        + std::mem::size_of::<policy::Policy<'_>>()
        + 256;
    meter.reserve(Resource::Scratch, scratch_fixed, cursor)?;
    if input.len() > budget.source_bytes {
        return Err(meter
            .error(FailureKind::ResourceExhausted, "module_bytes", cursor)
            .resource(
                Resource::Source,
                input.len() as u64,
                budget.source_bytes as u64,
            ));
    }
    meter.reserve(
        Resource::Metadata,
        std::mem::size_of::<ValidatedSwiftReactor>(),
        cursor,
    )?;
    meter.check(cursor)?;
    meter.reserve(Resource::Source, input.len(), cursor)?;
    let mut source = Vec::new();
    // Work is charged before the corresponding bounded copy. Capacity is reserved
    // before allocator entry, and overlap belongs to the caller's runner category.
    meter.work(0, cursor)?;
    source
        .try_reserve_exact(input.len())
        .map_err(|_| meter.error(FailureKind::AllocationFailure, "source_allocation", cursor))?;
    if source.capacity() != input.len() {
        return Err(meter.error(FailureKind::AllocationFailure, "source_capacity", cursor));
    }
    for (chunk_index, chunk) in input.chunks(16 * 1024).enumerate() {
        let cursor = Cursor {
            function: None,
            offset: chunk_index * 16 * 1024,
        };
        meter.work(chunk.len() as u64, cursor)?;
        source.extend_from_slice(chunk);
        meter.check(Cursor {
            offset: cursor.offset + chunk.len(),
            ..cursor
        })?;
    }
    meter.check(cursor)?;
    let source = source.into_boxed_slice(); // exact capacity: no shrink allocation
    let mut metadata: SwiftMetadata = metadata::read(&source, &policy, &mut meter)?;
    let imports = exact_abi(&source, &metadata, &mut meter)?;
    segments_fit(&metadata, &mut meter)?;
    validate::all(&source, &policy, &mut metadata, &mut meter)?;
    meter.check(cursor)?;
    let memory = metadata.memory.unwrap();
    let table = metadata.table.unwrap();
    let observations = SwiftReactorObservations {
        types: metadata.signatures.len(),
        type_parameters: metadata.parameters.len(),
        imported_functions: metadata.imports.len(),
        defined_functions: metadata.functions.len(),
        validated_bodies: meter.control.observations.validated_bodies,
        instructions: metadata.instructions,
        globals: metadata.globals.len(),
        exports: metadata.exports.len(),
        data_segments: metadata.data.len(),
        element_segments: metadata.elements.len(),
        max_parameters_plus_locals: meter.control.observations.max_parameters_plus_locals,
        max_operand_values: meter.control.observations.max_operand_values,
        max_control_depth: meter.control.observations.max_control_depth,
        memory_minimum: memory.0,
        memory_declared_maximum: metadata.declarations.memory_maximum,
        memory_host_maximum: memory.1,
        table_minimum: table.0,
        table_declared_maximum: metadata.declarations.table_maximum,
    };
    meter.check(cursor)?;
    meter.release(Resource::Scratch, scratch_fixed);
    let usage = usage(meter.usage(), input.len(), started, budget.deadline_ms);
    Ok(ValidatedSwiftReactor {
        source,
        metadata,
        policy,
        imports,
        usage,
        observations,
    })
}

fn exact_abi(
    source: &[u8],
    m: &SwiftMetadata,
    meter: &mut Meter<'_, account::SwiftControl>,
) -> Result<[WasiFunction; 34], Failure> {
    let cursor = Cursor::default();
    meter.work(1, cursor)?;
    if m.imports.len() != 34 {
        return Err(meter.error(FailureKind::Validation, "swift_import_count", cursor));
    }
    let mut resolved = WasiFunction::ALL;
    for (index, expected) in WasiFunction::ALL.into_iter().enumerate() {
        let import = m.imports.get(index).unwrap();
        let cursor = Cursor {
            function: Some(index as u32),
            offset: import.module.offset as usize,
        };
        let signature = *m.signatures.get(import.type_index as usize).unwrap();
        let result = signature.result;
        let results = result.as_slice();
        meter.work(
            (import.module.bytes + import.name.bytes + signature.count + 34) as u64,
            cursor,
        )?;
        let actual = WasiFunction::resolve(
            import.module.slice(source),
            import.name.slice(source),
            m.params(signature),
            results,
        )
        .map_err(|_| meter.error(FailureKind::Validation, "swift_import_abi", cursor))?;
        if actual != expected {
            return Err(meter.error(FailureKind::Validation, "swift_import_order", cursor));
        }
        resolved[index] = actual;
    }
    if m.memory != Some((584, 768)) || m.declarations.memory_maximum.is_some() {
        return Err(meter.error(
            FailureKind::Validation,
            "swift_memory_shape",
            Cursor {
                offset: m.declarations.memory_offset,
                ..cursor
            },
        ));
    }
    if m.table != Some((46_713, 46_713)) || m.declarations.table_maximum != Some(46_713) {
        return Err(meter.error(
            FailureKind::Validation,
            "swift_table_shape",
            Cursor {
                offset: m.declarations.table_offset,
                ..cursor
            },
        ));
    }
    if m.exports.len() != 3 {
        return Err(meter.error(FailureKind::Validation, "swift_export_count", cursor));
    }
    for (name, kind, index, result) in [
        (b"memory".as_slice(), 2, 0, None),
        (b"_initialize".as_slice(), 0, 35, None),
        (
            b"mixer_fieldlog_corpus_v1".as_slice(),
            0,
            62,
            Some(Type::I32),
        ),
    ] {
        let mut found = false;
        for export in m.exports.as_slice() {
            let cursor = Cursor {
                function: None,
                offset: export.name.offset as usize,
            };
            meter.work(export.name.bytes as u64 + 1, cursor)?;
            if export.name.slice(source) != name {
                continue;
            }
            found = true;
            if export.kind != kind
                || export.index != index
                || (kind == 0
                    && !m
                        .signature(index)
                        .is_some_and(|s| s.count == 0 && s.result == result))
            {
                return Err(meter.error(FailureKind::Validation, "swift_export_abi", cursor));
            }
        }
        if !found {
            return Err(meter.error(FailureKind::Validation, "swift_export_abi", cursor));
        }
    }
    Ok(resolved)
}

fn segments_fit(
    m: &SwiftMetadata,
    meter: &mut Meter<'_, account::SwiftControl>,
) -> Result<(), Failure> {
    let memory_bytes = u64::from(m.memory.unwrap().0).checked_mul(65_536).unwrap();
    let table_elements = u64::from(m.table.unwrap().0);
    for (segments, extent, code) in [
        (&m.data, memory_bytes, "swift_data_segment_fit"),
        (&m.elements, table_elements, "swift_element_segment_fit"),
    ] {
        for segment in segments.as_slice() {
            let cursor = Cursor {
                function: None,
                offset: segment.payload.offset as usize,
            };
            meter.work(1, cursor)?;
            if u64::from(segment.destination)
                .checked_add(u64::from(segment.count))
                .is_none_or(|end| end > extent)
            {
                return Err(meter.error(FailureKind::Validation, code, cursor));
            }
        }
    }
    Ok(())
}

// Const-only inventory of the retained getters reached AFTER constructor phase
// admission. Concrete class indices map to the independently reviewed named
// source/callsite positions in candidate2-api/positive-accounting-map.json under
// verification/swift-executor-construction-independent-review. No inventory is
// instantiated and no descriptor/metadata visibility is widened. The execution
// layer adds this whole positive bound; historical allowances are not reused.
#[allow(dead_code)]
struct ConstructionPositiveDescriptor {
    class_0: [usize; 42],
    class_1:
        [&'static crate::experimental::account::Buffer<crate::experimental::metadata::Global>; 8],
    class_2: [&'static std::vec::Vec<crate::experimental::metadata::Global>; 4],
    class_3:
        [&'static crate::experimental::account::Buffer<crate::experimental::metadata::Segment>; 10],
    class_4: [&'static std::vec::Vec<crate::experimental::metadata::Segment>; 4],
    class_5:
        [&'static crate::experimental::account::Buffer<crate::experimental::metadata::Import>; 8],
    class_6: [&'static std::vec::Vec<crate::experimental::metadata::Import>; 4],
    class_7: [&'static [Type]; 5],
    class_8: [&'static crate::experimental::account::Buffer<Type>; 3],
    class_9: [&'static std::vec::Vec<Type>; 2],
    class_10: [std::option::Option<&'static crate::experimental::metadata::Global>; 5],
    class_11: [&'static [crate::experimental::metadata::Global]; 2],
    class_12: [std::option::Option<&'static crate::experimental::metadata::Segment>; 5],
    class_13: [&'static [crate::experimental::metadata::Segment]; 2],
    class_14: [std::option::Option<&'static crate::experimental::metadata::Signature>; 3],
    class_15: [&'static crate::experimental::account::Buffer<
        crate::experimental::metadata::Signature,
    >; 3],
    class_16: [&'static [crate::experimental::metadata::Signature]; 2],
    class_17: [&'static std::vec::Vec<crate::experimental::metadata::Signature>; 2],
    class_18: [std::option::Option<&'static crate::experimental::metadata::Function>; 3],
    class_19:
        [&'static crate::experimental::account::Buffer<crate::experimental::metadata::Function>; 3],
    class_20: [&'static [crate::experimental::metadata::Function]; 2],
    class_21: [&'static std::vec::Vec<crate::experimental::metadata::Function>; 2],
    class_22: [std::option::Option<&'static crate::experimental::metadata::Import>; 3],
    class_23: [&'static [crate::experimental::metadata::Import]; 2],
    class_24: [&'static [u8]; 9],
    class_25: [crate::experimental::metadata::Span; 5],
    class_26: [std::ops::Range<usize>; 4],
    class_27: [u32; 19],
    class_28: [(usize, bool); 3],
    class_29: [std::option::Option<crate::experimental::metadata::Signature>; 3],
    class_30: [&'static crate::experimental::metadata::Metadata<
        crate::experimental::metadata::SwiftDeclaration,
    >; 6],
    class_31: [bool; 2],
    class_32: [std::ops::ControlFlow<
        std::option::Option<std::convert::Infallible>,
        &'static crate::experimental::metadata::Import,
    >; 1],
    class_33: [isize; 9],
    class_34: [&'static crate::experimental::metadata::Import; 1],
    class_35: [std::ops::ControlFlow<
        std::option::Option<std::convert::Infallible>,
        &'static crate::experimental::metadata::Function,
    >; 1],
    class_36: [&'static crate::experimental::metadata::Function; 1],
    class_37: [Option<std::convert::Infallible>; 9],
    class_38: [crate::experimental::metadata::Signature; 3],
    class_39: [std::option::Option<crate::experimental::descriptors::SignatureView<'static>>; 1],
    class_40: [&'static ValidatedSwiftReactor; 13],
    class_41: [std::ops::ControlFlow<
        std::option::Option<std::convert::Infallible>,
        crate::experimental::metadata::Signature,
    >; 1],
    class_42: [crate::experimental::descriptors::SignatureView<'static>; 1],
    class_43: [std::option::Option<Type>; 1],
    class_44: [std::option::Option<crate::experimental::descriptors::GlobalView<'static>>; 1],
    class_45: [std::ops::ControlFlow<
        std::option::Option<std::convert::Infallible>,
        &'static crate::experimental::metadata::Global,
    >; 2],
    class_46: [&'static crate::experimental::metadata::Global; 2],
    class_47: [crate::experimental::descriptors::GlobalView<'static>; 1],
    class_48: [Type; 1],
    class_49: [&'static std::boxed::Box<[u8]>; 2],
    class_50: [std::boxed::Box<[u8]>; 2],
    class_51: [*const [u8]; 2],
    class_52: [std::option::Option<usize>; 1],
    class_53:
        [std::option::Option<crate::experimental::descriptors::SegmentExecutionView<'static>>; 2],
    class_54: [crate::experimental::descriptors::SegmentExecutionView<'static>; 3],
    class_55: [std::ops::ControlFlow<
        std::option::Option<std::convert::Infallible>,
        &'static crate::experimental::metadata::Segment,
    >; 2],
    class_56: [&'static crate::experimental::metadata::Segment; 5],
    class_57: [std::option::Option<crate::experimental::descriptors::MemoryExecutionView>; 1],
    class_58: [std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, (u32, u32)>; 2],
    class_59: [std::option::Option<(u32, u32)>; 4],
    class_60: [(u32, u32); 2],
    class_61: [crate::experimental::descriptors::MemoryExecutionView; 1],
    class_62: [std::option::Option<u32>; 2],
    class_63: [std::option::Option<crate::experimental::descriptors::TableExecutionView>; 1],
    class_64: [crate::experimental::descriptors::TableExecutionView; 1],
}
pub(crate) const CONSTRUCTION_POSITIVE_DESCRIPTOR_BYTES: usize =
    std::mem::size_of::<ConstructionPositiveDescriptor>();

#[allow(dead_code)]
pub(crate) mod snapshot_encoder_v2 {
// Guard-derived logical encoding only. No operational storage/work/IO authority.
use super::*;
use crate::experimental_swift_reactor::{InitialProfileBorrowV1, LoaderProvenanceV1};
use std::mem::{align_of, size_of};
pub(crate) const SNAPSHOT_TRANSFER_BYTES_V2: usize = 4096;
const HEADER: usize = 2560;
const CAPS: [u64; 9] = [67108864, 512, 8192, 34, 79966, 8192, 4096, 4096, 4096];
const WIDTHS: [u64; 9] = [0, 3, 1, 5, 3, 4, 4, 4, 4];
const NATIVE: [u64; 9] = [1, 12, 1, 20, 12, 12, 16, 16, 16];
const MAXIMUM: u64 = 69765152;
#[derive(Debug, PartialEq, Eq)]
pub(crate) enum SnapshotEncodeErrorV2 {
    MissingSelectedProvenance,
    UnsupportedLayout,
    UnsupportedPolicy,
    Arithmetic,
    InternalField { code: u32, section: u32, index: u64 },
}
pub(crate) struct SnapshotViewV2<'guard> {
    initial: &'guard InitialProfileBorrowV1<'guard>,
    proof: &'guard ValidatedSwiftReactor,
    provenance: &'guard LoaderProvenanceV1,
}
pub(crate) struct SnapshotCursorV2<'guard> {
    view: SnapshotViewV2<'guard>,
    header: [u8; HEADER],
    extent: u64,
    emitted: u64,
}
pub(crate) struct SnapshotBlockV2<'block> {
    bytes: &'block [u8],
    offset: u64,
    final_block: bool,
}
impl SnapshotBlockV2<'_> {
    pub(crate) fn bytes(&self) -> &[u8] {
        self.bytes
    }
    pub(crate) fn offset(&self) -> u64 {
        self.offset
    }
    pub(crate) fn is_final(&self) -> bool {
        self.final_block
    }
}
fn field(code: u32, section: usize, index: usize) -> SnapshotEncodeErrorV2 {
    SnapshotEncodeErrorV2::InternalField {
        code,
        section: section as u32,
        index: index as u64,
    }
}
fn require(ok: bool, code: u32, section: usize, index: usize) -> Result<(), SnapshotEncodeErrorV2> {
    if ok {
        Ok(())
    } else {
        Err(field(code, section, index))
    }
}
fn word(n: usize) -> Result<u64, SnapshotEncodeErrorV2> {
    u64::try_from(n).map_err(|_| SnapshotEncodeErrorV2::Arithmetic)
}
fn put(h: &mut [u8], at: usize, n: u64) {
    h[at..at + 8].copy_from_slice(&n.to_le_bytes());
}
fn get(h: &[u8], at: usize) -> u64 {
    u64::from_le_bytes(h[at..at + 8].try_into().expect("fixed header word"))
}
fn words(h: &mut [u8], at: usize, v: &[u64]) {
    for (i, n) in v.iter().enumerate() {
        put(h, at + i * 8, *n);
    }
}
fn optional(v: Option<u32>) -> [u64; 2] {
    match v {
        None => [0, 0],
        Some(n) => [1, u64::from(n)],
    }
}
fn type_id(t: Type) -> u64 {
    match t {
        Type::I32 => 1,
        Type::I64 => 2,
        Type::F32 => 3,
        Type::F64 => 4,
    }
}
fn result_id(t: Option<Type>) -> u64 {
    match t {
        None => 0,
        Some(t) => type_id(t),
    }
}
struct SpanCheckV2 {
    source: usize,
    section: usize,
    index: usize,
}
impl SpanCheckV2 {
    fn check(&self, s: metadata::Span) -> Result<(), SnapshotEncodeErrorV2> {
        require(
            (s.offset as usize)
                .checked_add(s.bytes as usize)
                .is_some_and(|end| end <= self.source),
            15,
            self.section,
            self.index,
        )
    }
}
fn wasi_id(t: WasiFunction) -> u64 {
    match t {
        WasiFunction::ArgsGet => 1,
        WasiFunction::ArgsSizesGet => 2,
        WasiFunction::EnvironGet => 3,
        WasiFunction::EnvironSizesGet => 4,
        WasiFunction::ClockResGet => 5,
        WasiFunction::ClockTimeGet => 6,
        WasiFunction::FdClose => 7,
        WasiFunction::FdFdstatGet => 8,
        WasiFunction::FdFdstatSetFlags => 9,
        WasiFunction::FdFilestatGet => 10,
        WasiFunction::FdFilestatSetSize => 11,
        WasiFunction::FdFilestatSetTimes => 12,
        WasiFunction::FdPread => 13,
        WasiFunction::FdPrestatGet => 14,
        WasiFunction::FdPrestatDirName => 15,
        WasiFunction::FdRead => 16,
        WasiFunction::FdReaddir => 17,
        WasiFunction::FdSeek => 18,
        WasiFunction::FdSync => 19,
        WasiFunction::FdTell => 20,
        WasiFunction::FdWrite => 21,
        WasiFunction::PathCreateDirectory => 22,
        WasiFunction::PathFilestatGet => 23,
        WasiFunction::PathFilestatSetTimes => 24,
        WasiFunction::PathLink => 25,
        WasiFunction::PathOpen => 26,
        WasiFunction::PathReadlink => 27,
        WasiFunction::PathRemoveDirectory => 28,
        WasiFunction::PathRename => 29,
        WasiFunction::PathSymlink => 30,
        WasiFunction::PathUnlinkFile => 31,
        WasiFunction::PollOneoff => 32,
        WasiFunction::ProcExit => 33,
        WasiFunction::RandomGet => 34,
    }
}
pub(crate) fn borrow_snapshot_v2<'guard>(
    initial: &'guard InitialProfileBorrowV1<'_>,
) -> Result<SnapshotViewV2<'guard>, SnapshotEncodeErrorV2> {
    let provenance = initial
        .snapshot_selected_v2()
        .ok_or(SnapshotEncodeErrorV2::MissingSelectedProvenance)?;
    Ok(SnapshotViewV2 {
        initial,
        proof: initial.snapshot_proof_v2(),
        provenance,
    })
}
impl<'guard> SnapshotViewV2<'guard> {
    pub(crate) fn into_cursor(self) -> Result<SnapshotCursorV2<'guard>, SnapshotEncodeErrorV2> {
        if size_of::<usize>() != 8
            || !cfg!(target_endian = "little")
            || !cfg!(target_arch = "aarch64")
            || !cfg!(target_os = "macos")
            || size_of::<ValidatedSwiftReactor>() != 664
        {
            return Err(SnapshotEncodeErrorV2::UnsupportedLayout);
        }
        match self.proof.policy {
            policy::Policy::SwiftReactorExperimentV1 => (),
            policy::Policy::Frozen(_) => return Err(SnapshotEncodeErrorV2::UnsupportedPolicy),
        }
        let mut h = [0u8; HEADER];
        h[..8].copy_from_slice(b"MIXSNB02");
        let p = self.proof;
        let m = &p.metadata;
        let u = p.usage;
        let o = p.observations;
        let source = word(p.source.len())?;
        words(
            &mut h,
            8,
            &[
                2,
                2560,
                0,
                9,
                1,
                1,
                34,
                source,
                word(m.instructions)?,
                8,
                664,
            ],
        );
        self.provenance
            .snapshot_encode_v2(
                (&mut h[512..1088])
                    .try_into()
                    .expect("fixed provenance region"),
            )
            .map_err(|_| SnapshotEncodeErrorV2::Arithmetic)?;
        for i in 0..5 {
            let n = get(&h, 544 + i * 8);
            put(&mut h, 96 + i * 8, n);
        }
        require(get(&h, 536) == source && get(&h, 792) == source, 1, 0, 0)?;
        words(
            &mut h,
            144,
            &[
                word(u.input_visible_bytes)?,
                word(u.source_bytes)?,
                word(u.metadata_reserved)?,
                word(u.scratch_reserved)?,
                word(u.metadata_peak_reserved)?,
                word(u.scratch_peak_reserved)?,
                word(u.total_peak_reserved)?,
                u.work_used,
                u.elapsed_micros,
                u.deadline_ms,
            ],
        );
        let mm = optional(o.memory_declared_maximum);
        let tm = optional(o.table_declared_maximum);
        words(
            &mut h,
            224,
            &[
                word(o.types)?,
                word(o.type_parameters)?,
                word(o.imported_functions)?,
                word(o.defined_functions)?,
                word(o.validated_bodies)?,
                word(o.instructions)?,
                word(o.globals)?,
                word(o.exports)?,
                word(o.data_segments)?,
                word(o.element_segments)?,
                word(o.max_parameters_plus_locals)?,
                word(o.max_operand_values)?,
                word(o.max_control_depth)?,
                u64::from(o.memory_minimum),
                mm[0],
                mm[1],
                u64::from(o.memory_host_maximum),
                u64::from(o.table_minimum),
                tm[0],
                tm[1],
            ],
        );
        let memory = m.memory.ok_or_else(|| field(2, 0, 0))?;
        let table = m.table.ok_or_else(|| field(3, 0, 0))?;
        let md = optional(m.declarations.memory_maximum);
        let td = optional(m.declarations.table_maximum);
        words(
            &mut h,
            384,
            &[
                1,
                u64::from(memory.0),
                u64::from(memory.1),
                1,
                u64::from(table.0),
                u64::from(table.1),
                md[0],
                md[1],
                td[0],
                td[1],
                word(m.declarations.memory_offset)?,
                word(m.declarations.table_offset)?,
                word(m.instructions)?,
            ],
        );
        self.initial
            .snapshot_runtime_v2(
                (&mut h[1088..1600])
                    .try_into()
                    .expect("fixed runtime region"),
            )
            .map_err(|_| SnapshotEncodeErrorV2::Arithmetic)?;
        require(
            u.input_visible_bytes == p.source.len()
                && u.source_bytes == p.source.len()
                && source <= get(&h, 96)
                && u.deadline_ms == get(&h, 128),
            4,
            0,
            0,
        )?;
        let validation_caps = [67108864, 16777216, 1048576, 512000000, 120000];
        for (i, cap) in validation_caps.iter().enumerate() {
            require(get(&h, 96 + i * 8) <= *cap, 5, 0, i)?;
        }
        require(
            ValidatedSwiftReactor::VALIDATOR_REVISION == 1
                && o.imported_functions == 34
                && o.defined_functions == o.validated_bodies
                && o.imported_functions
                    .checked_add(o.defined_functions)
                    .is_some_and(|n| n <= 80000)
                && o.instructions == m.instructions
                && m.instructions <= 8000000
                && o.max_parameters_plus_locals <= 256
                && o.max_operand_values <= 128
                && o.max_control_depth <= 512,
            6,
            0,
            0,
        )?;
        require(
            memory.0 == o.memory_minimum
                && memory.1 == o.memory_host_maximum
                && table.0 == o.table_minimum
                && md == mm
                && td == tm
                && memory.1 == m.declarations.memory_maximum.unwrap_or(768)
                && table.1 == m.declarations.table_maximum.unwrap_or(65536)
                && memory.0 <= memory.1
                && memory.1 <= 768
                && table.0 <= table.1
                && table.1 <= 65536
                && m.declarations.memory_offset <= p.source.len()
                && m.declarations.table_offset <= p.source.len(),
            7,
            0,
            0,
        )?;
        let mut at = 2560u64;
        let mut charged = 664u64;
        for sid in 0..9 {
            let inventory = self.inventory(sid)?;
            let (count, capacity, native, charge, category) = inventory;
            require(
                count <= CAPS[sid]
                    && count <= capacity
                    && native == NATIVE[sid]
                    && capacity.checked_mul(native) == Some(charge)
                    && category == if sid == 0 { 1 } else { 2 },
                8,
                sid,
                0,
            )?;
            let bytes = if sid == 0 {
                count
            } else {
                count
                    .checked_mul(WIDTHS[sid] * 8)
                    .ok_or(SnapshotEncodeErrorV2::Arithmetic)?
            };
            require(
                charge <= if sid == 0 { 67108864 } else { 16777216 },
                9,
                sid,
                0,
            )?;
            if sid == 0 {
                require(
                    count == source && capacity == source && charge == source,
                    10,
                    sid,
                    0,
                )?;
            } else {
                charged = charged
                    .checked_add(charge)
                    .ok_or(SnapshotEncodeErrorV2::Arithmetic)?;
                let observation = [0usize, 0, 1, 2, 3, 6, 7, 8, 9][sid];
                require(count == get(&h, 224 + observation * 8), 11, sid, 0)?;
            }
            words(
                &mut h,
                1600 + sid * 64,
                &[
                    sid as u64, count, capacity, native, charge, category, at, bytes,
                ],
            );
            at = at
                .checked_add(bytes)
                .ok_or(SnapshotEncodeErrorV2::Arithmetic)?;
        }
        require(
            charged == word(u.metadata_reserved)? && charged <= get(&h, 104) && at <= MAXIMUM,
            12,
            0,
            0,
        )?;
        for (i, resolved) in p.imports.iter().enumerate() {
            put(&mut h, 2176 + i * 8, wasi_id(*resolved));
        }
        validate_runtime(&h, source, word(o.types)?, word(o.defined_functions)?)?;
        put(&mut h, 24, at);
        Ok(SnapshotCursorV2 {
            view: self,
            header: h,
            extent: at,
            emitted: 0,
        })
    }
    fn inventory(&self, sid: usize) -> Result<(u64, u64, u64, u64, u64), SnapshotEncodeErrorV2> {
        if sid == 0 {
            let n = word(self.proof.source.len())?;
            return Ok((n, n, 1, word(self.proof.usage.source_bytes)?, 1));
        }
        let m = &self.proof.metadata;
        let (n, c, s, b, r) = match sid {
            1 => m.signatures.snapshot_inventory_v2(),
            2 => m.parameters.snapshot_inventory_v2(),
            3 => m.imports.snapshot_inventory_v2(),
            4 => m.functions.snapshot_inventory_v2(),
            5 => m.globals.snapshot_inventory_v2(),
            6 => m.exports.snapshot_inventory_v2(),
            7 => m.data.snapshot_inventory_v2(),
            8 => m.elements.snapshot_inventory_v2(),
            _ => return Err(field(13, sid, 0)),
        };
        require(matches!(r, Resource::Metadata), 14, sid, 0)?;
        Ok((word(n)?, word(c)?, word(s)?, word(b)?, 2))
    }
    fn record_word(
        &self,
        sid: usize,
        index: usize,
        within: usize,
    ) -> Result<u64, SnapshotEncodeErrorV2> {
        let m = &self.proof.metadata;
        let source = self.proof.source.len();
        let span = SpanCheckV2 {
            source,
            section: sid,
            index,
        };
        macro_rules! entry {
            ($field:ident) => {
                m.$field.get(index).ok_or_else(|| field(16, sid, index))?
            };
        }
        let v = match sid {
            1 => {
                let s = entry!(signatures);
                require(
                    (s.first as usize)
                        .checked_add(s.count as usize)
                        .is_some_and(|n| n <= m.parameters.len()),
                    17,
                    sid,
                    index,
                )?;
                [
                    u64::from(s.first),
                    u64::from(s.count),
                    result_id(s.result),
                    0,
                    0,
                ]
            }
            2 => [type_id(*entry!(parameters)), 0, 0, 0, 0],
            3 => {
                let i = entry!(imports);
                span.check(i.module)?;
                span.check(i.name)?;
                require((i.type_index as usize) < m.signatures.len(), 18, sid, index)?;
                [
                    u64::from(i.module.offset),
                    u64::from(i.module.bytes),
                    u64::from(i.name.offset),
                    u64::from(i.name.bytes),
                    u64::from(i.type_index),
                ]
            }
            4 => {
                let f = entry!(functions);
                span.check(f.body)?;
                require((f.type_index as usize) < m.signatures.len(), 18, sid, index)?;
                [
                    u64::from(f.body.offset),
                    u64::from(f.body.bytes),
                    u64::from(f.type_index),
                    0,
                    0,
                ]
            }
            5 => {
                let g = entry!(globals);
                span.check(g.initializer)?;
                [
                    type_id(g.ty),
                    u64::from(g.mutable),
                    u64::from(g.initializer.offset),
                    u64::from(g.initializer.bytes),
                    0,
                ]
            }
            6 => {
                let e = entry!(exports);
                span.check(e.name)?;
                require(e.kind <= 3, 19, sid, index)?;
                [
                    u64::from(e.name.offset),
                    u64::from(e.name.bytes),
                    u64::from(e.kind),
                    u64::from(e.index),
                    0,
                ]
            }
            7 | 8 => {
                let s = if sid == 7 {
                    entry!(data)
                } else {
                    entry!(elements)
                };
                span.check(s.payload)?;
                [
                    u64::from(s.payload.offset),
                    u64::from(s.payload.bytes),
                    u64::from(s.destination),
                    u64::from(s.count),
                    0,
                ]
            }
            _ => return Err(field(20, sid, index)),
        };
        v.get(within).copied().ok_or_else(|| field(21, sid, index))
    }
}
fn validate_runtime(
    h: &[u8; HEADER],
    source: u64,
    types: u64,
    defined: u64,
) -> Result<(), SnapshotEncodeErrorV2> {
    let caps = [
        67108864, 16777216, 16777216, 8388608, 64, 64, 64000000, 64, 16384, 4096, 768, 134217728,
        268435456, 100000000, 1000000000, 32768, 30000,
    ];
    for (i, cap) in caps.iter().enumerate() {
        require(get(h, 1128 + i * 8) <= *cap, 22, 0, i)?;
    }
    let wasi_caps = [32768, 4194304, 32000000, 65536, 64, 65536, 30000];
    for (i, cap) in wasi_caps.iter().enumerate() {
        require(get(h, 1264 + i * 8) <= *cap, 23, 0, i)?;
    }
    let presence = get(h, 1112);
    require(presence <= 1 && get(h, 1120) != 0, 24, 0, 0)?;
    for i in 0..5 {
        require(get(h, 1320 + i * 8) <= 1, 25, 0, i)?;
    }
    if presence == 0 {
        for i in 0..12 {
            require(get(h, 1264 + i * 8) == 0, 26, 0, i)?;
        }
    }
    require(
        get(h, 1360) == source
            && get(h, 1368) == types
            && types <= u32::MAX as u64
            && get(h, 1376) == get(h, 1160).min(defined)
            && (1..=64).contains(&get(h, 1376))
            && get(h, 1384) == get(h, 1168)
            && (1..=64).contains(&get(h, 1384))
            && get(h, 1392) == 1
            && get(h, 1400) <= get(h, 1408)
            && get(h, 1408) == get(h, 1144)
            && get(h, 1416) == get(h, 1152),
        27,
        0,
        0,
    )
}
impl SnapshotCursorV2<'_> {
    pub(crate) fn encoded_extent(&self) -> u64 {
        self.extent
    }
    pub(crate) fn emitted_extent(&self) -> u64 {
        self.emitted
    }
    pub(crate) fn next_block<'block>(
        &mut self,
        transfer: &'block mut [u8; SNAPSHOT_TRANSFER_BYTES_V2],
    ) -> Result<Option<SnapshotBlockV2<'block>>, SnapshotEncodeErrorV2> {
        if self.emitted == self.extent {
            return Ok(None);
        }
        let base = self.emitted;
        let mut at = base;
        let mut filled = 0usize;
        // At most 4096 output-byte progress steps. Metadata steps emit the remainder
        // of one8-byte word: at most513 record visits, with at most9 directory probes.
        while filled < SNAPSHOT_TRANSFER_BYTES_V2 && at < self.extent {
            if at < HEADER as u64 {
                let n = (HEADER - at as usize).min(SNAPSHOT_TRANSFER_BYTES_V2 - filled);
                transfer[filled..filled + n]
                    .copy_from_slice(&self.header[at as usize..at as usize + n]);
                filled += n;
                at += n as u64;
                continue;
            }
            let mut found = None;
            for sid in 0..9 {
                let start = get(&self.header, 1600 + sid * 64 + 48);
                let bytes = get(&self.header, 1600 + sid * 64 + 56);
                if at >= start && at - start < bytes {
                    found = Some((sid, start, bytes));
                    break;
                }
            }
            let (sid, start, bytes) = found.ok_or_else(|| field(28, 0, 0))?;
            let relative = at - start;
            if sid == 0 {
                let n = usize::try_from(
                    (bytes - relative).min((SNAPSHOT_TRANSFER_BYTES_V2 - filled) as u64),
                )
                .map_err(|_| SnapshotEncodeErrorV2::Arithmetic)?;
                let offset =
                    usize::try_from(relative).map_err(|_| SnapshotEncodeErrorV2::Arithmetic)?;
                transfer[filled..filled + n]
                    .copy_from_slice(&self.view.proof.source[offset..offset + n]);
                filled += n;
                at += n as u64;
            } else {
                let row_bytes = WIDTHS[sid] * 8;
                let index = usize::try_from(relative / row_bytes)
                    .map_err(|_| SnapshotEncodeErrorV2::Arithmetic)?;
                let within = ((relative % row_bytes) / 8) as usize;
                let skip = (relative % 8) as usize;
                let value = self.view.record_word(sid, index, within)?.to_le_bytes();
                let n = (8 - skip).min(SNAPSHOT_TRANSFER_BYTES_V2 - filled);
                transfer[filled..filled + n].copy_from_slice(&value[skip..skip + n]);
                filled += n;
                at += n as u64;
            }
        }
        self.emitted = at;
        Ok(Some(SnapshotBlockV2 {
            bytes: &transfer[..filled],
            offset: base,
            final_block: at == self.extent,
        }))
    }
}

// All newly concrete interface and aggregate shapes used by later admission.
// Counts are conservative named source places, not a granted floor or RSS.
struct EncoderInitPlacesV2<'g> {
    initial: &'g InitialProfileBorrowV1<'g>,
    view: SnapshotViewV2<'g>,
    view_return: Result<SnapshotViewV2<'g>, SnapshotEncodeErrorV2>,
    cursor_return: Result<SnapshotCursorV2<'g>, SnapshotEncodeErrorV2>,
    header: [u8; HEADER],
    usage: SwiftValidationUsage,
    observations: SwiftReactorObservations,
    inventory: (u64, u64, u64, u64, u64),
    words: [u64; 20],
    directory: [u64; 8],
    options: [[u64; 2]; 4],
    validation_caps: [u64; 5],
    memory_table: [(u32, u32); 2],
    scalars: [u64; 8],
    validation_budget: SwiftValidationBudget,
    runtime_budget: crate::experimental_swift_reactor::control::SwiftRunBudget,
    wasi: Option<(
        crate::experimental_wasi::WasiBudget,
        crate::experimental_wasi::WasiGrants,
    )>,
}
struct EncoderBlockPlacesV2<'g> {
    cursor: &'g mut SnapshotCursorV2<'g>,
    transfer: &'g mut [u8; 4096],
    block_return: Result<Option<SnapshotBlockV2<'g>>, SnapshotEncodeErrorV2>,
    found: Option<(usize, u64, u64)>,
    words: [u64; 5],
    word: [u8; 8],
    span: metadata::Span,
    record_return: Result<u64, SnapshotEncodeErrorV2>,
    span_result: Result<(), SnapshotEncodeErrorV2>,
}
struct EncoderCallerPlacesV2<'g> {
    view: Option<SnapshotViewV2<'g>>,
    cursor: Option<SnapshotCursorV2<'g>>,
    transfer: [u8; 4096],
    view_move: SnapshotViewV2<'g>,
    cursor_move: SnapshotCursorV2<'g>,
    cursor_result: Result<SnapshotCursorV2<'g>, SnapshotEncodeErrorV2>,
    block: Option<SnapshotBlockV2<'g>>,
    block_result: Result<Option<SnapshotBlockV2<'g>>, SnapshotEncodeErrorV2>,
    error: SnapshotEncodeErrorV2,
    returned_error: Result<(), SnapshotEncodeErrorV2>,
}
pub(crate) fn snapshot_layouts_v2() -> [(&'static str, usize, usize); 52] {
    macro_rules! l {
        ($t:ty) => {
            (stringify!($t), size_of::<$t>(), align_of::<$t>())
        };
    }
    [
        l!(SnapshotViewV2<'static>),
        l!(SnapshotCursorV2<'static>),
        l!(SnapshotBlockV2<'static>),
        l!(SnapshotEncodeErrorV2),
        l!(Result<SnapshotViewV2<'static>, SnapshotEncodeErrorV2>),
        l!(Result<SnapshotCursorV2<'static>, SnapshotEncodeErrorV2>),
        l!(Result<Option<SnapshotBlockV2<'static>>, SnapshotEncodeErrorV2>),
        l!(Option<SnapshotViewV2<'static>>),
        l!(Option<SnapshotCursorV2<'static>>),
        l!(Option<SnapshotBlockV2<'static>>),
        l!(EncoderInitPlacesV2<'static>),
        l!(EncoderBlockPlacesV2<'static>),
        l!(EncoderCallerPlacesV2<'static>),
        l!((usize, usize, usize, usize, Resource)),
        l!((u64, u64, u64, u64, u64)),
        l!([u8; 4096]),
        l!([u8; 2560]),
        l!([u8; 576]),
        l!([u8; 512]),
        l!([u8; 64]),
        l!([u8; 8]),
        l!([u64; 20]),
        l!([u64; 17]),
        l!([u64; 13]),
        l!([u64; 12]),
        l!([u64; 10]),
        l!([u64; 8]),
        l!([u64; 7]),
        l!([u64; 5]),
        l!([u64; 4]),
        l!([u64; 2]),
        l!(Result<u64,SnapshotEncodeErrorV2>),
        l!(Result<(),SnapshotEncodeErrorV2>),
        l!(Result<(),()>),
        l!(Result<u64,()>),
        l!(Option<(usize, u64, u64)>),
        l!(metadata::Span),
        l!(SwiftValidationUsage),
        l!(SwiftReactorObservations),
        l!(SwiftValidationBudget),
        l!(crate::experimental_swift_reactor::control::SwiftRunBudget),
        l!(
            Option<(
                crate::experimental_wasi::WasiBudget,
                crate::experimental_wasi::WasiGrants
            )>
        ),
        l!([&'static [u8; 32]; 6]),
        l!(std::iter::Enumerate<std::slice::Iter<'static, u64>>),
        l!(std::iter::Enumerate<std::slice::Iter<'static, WasiFunction>>),
        l!(std::iter::Enumerate<std::slice::Iter<'static, &'static [u8; 32]>>),
        l!(std::slice::Iter<'static, u64>),
        l!(SpanCheckV2),
        l!(Result<(u64,u64,u64,u64,u64),SnapshotEncodeErrorV2>),
        l!(Result<usize,SnapshotEncodeErrorV2>),
        l!(Option<&'static LoaderProvenanceV1>),
        l!(Result<u64,std::num::TryFromIntError>),
    ]
}
#[cfg(any(test, mixer_snapshot_encoder_host))]
pub(crate) fn oracle_inventory_v2(initial: &InitialProfileBorrowV1<'_>) -> String {
    let p = initial.snapshot_proof_v2();
    let m = &p.metadata;
    let mut out = String::new();
    for (i, v) in [
        m.signatures.snapshot_inventory_v2(),
        m.parameters.snapshot_inventory_v2(),
        m.imports.snapshot_inventory_v2(),
        m.functions.snapshot_inventory_v2(),
        m.globals.snapshot_inventory_v2(),
        m.exports.snapshot_inventory_v2(),
        m.data.snapshot_inventory_v2(),
        m.elements.snapshot_inventory_v2(),
    ]
    .iter()
    .enumerate()
    {
        out.push_str(&format!("BUFFER\t{}\t{:?}\n", i + 1, v));
    }
    out
}
#[cfg(test)]
mod encoder_unit {
    use super::*;
    #[test]
    fn finite_enum_and_option_mappings_v2() {
        assert_eq!(
            [
                type_id(Type::I32),
                type_id(Type::I64),
                type_id(Type::F32),
                type_id(Type::F64)
            ],
            [1, 2, 3, 4]
        );
        assert_eq!(result_id(None), 0);
        for t in [Type::I32, Type::I64, Type::F32, Type::F64] {
            assert_eq!(result_id(Some(t)), type_id(t));
        }
        for (i, t) in WasiFunction::ALL.into_iter().enumerate() {
            assert_eq!(wasi_id(t), i as u64 + 1);
        }
        assert_eq!(optional(None), [0, 0]);
        assert_eq!(optional(Some(0)), [1, 0]);
        assert_eq!(optional(Some(u32::MAX)), [1, u32::MAX as u64]);
    }
    #[test]
    fn span_checks_refuse_bounds_v2() {
        let check = SpanCheckV2 {
            source: 8,
            section: 3,
            index: 7,
        };
        assert!(check
            .check(metadata::Span {
                offset: 6,
                bytes: 2
            })
            .is_ok());
        assert!(check
            .check(metadata::Span {
                offset: 8,
                bytes: 0
            })
            .is_ok());
        assert_eq!(
            check.check(metadata::Span {
                offset: 8,
                bytes: 1
            }),
            Err(field(15, 3, 7))
        );
        assert_eq!(
            check.check(metadata::Span {
                offset: u32::MAX,
                bytes: u32::MAX
            }),
            Err(field(15, 3, 7))
        );
    }
}

}

// Independent actual proof observation, appended only to the owned review copy.
// No encoder helper, record_word, mapping, inventory or serialized bytes used.
#[cfg(any(test,mixer_snapshot_encoder_host))]
pub(crate) fn independent_snapshot_fields(initial:&crate::experimental_swift_reactor::InitialProfileBorrowV1<'_>)->String {
 let p=initial.snapshot_proof_v2();let m=&p.metadata;let u=&p.usage;let o=&p.observations;
 let array=|v:&[u64]|format!("{:?}",v);
 let pair=|v:Option<u32>|match v{None=>[0u64,0],Some(n)=>[1,n as u64]};
 let mut rows:Vec<String>=Vec::new();
 let mut part=Vec::new();for i in 0..m.signatures.len(){let v=m.signatures.get(i).unwrap();part.push(format!("[{}, {}, \"{:?}\"]",v.first,v.count,v.result));}rows.push(format!("[{}]",part.join(",")));
 let mut part=Vec::new();for i in 0..m.parameters.len(){part.push(format!("[\"{:?}\"]",m.parameters.get(i).unwrap()));}rows.push(format!("[{}]",part.join(",")));
 let mut part=Vec::new();for i in 0..m.imports.len(){let v=m.imports.get(i).unwrap();part.push(array(&[v.module.offset as u64,v.module.bytes as u64,v.name.offset as u64,v.name.bytes as u64,v.type_index as u64]));}rows.push(format!("[{}]",part.join(",")));
 let mut part=Vec::new();for i in 0..m.functions.len(){let v=m.functions.get(i).unwrap();part.push(array(&[v.body.offset as u64,v.body.bytes as u64,v.type_index as u64]));}rows.push(format!("[{}]",part.join(",")));
 let mut part=Vec::new();for i in 0..m.globals.len(){let v=m.globals.get(i).unwrap();part.push(format!("[\"{:?}\",{},{},{}]",v.ty,u8::from(v.mutable),v.initializer.offset,v.initializer.bytes));}rows.push(format!("[{}]",part.join(",")));
 let mut part=Vec::new();for i in 0..m.exports.len(){let v=m.exports.get(i).unwrap();part.push(array(&[v.name.offset as u64,v.name.bytes as u64,v.kind as u64,v.index as u64]));}rows.push(format!("[{}]",part.join(",")));
 for buffer in [&m.data,&m.elements]{let mut part=Vec::new();for i in 0..buffer.len(){let v=buffer.get(i).unwrap();part.push(array(&[v.payload.offset as u64,v.payload.bytes as u64,v.destination as u64,v.count as u64]));}rows.push(format!("[{}]",part.join(",")));}
 let inventories=[m.signatures.independent_inventory(),m.parameters.independent_inventory(),m.imports.independent_inventory(),m.functions.independent_inventory(),m.globals.independent_inventory(),m.exports.independent_inventory(),m.data.independent_inventory(),m.elements.independent_inventory()];
 let inventories:Vec<String>=inventories.iter().map(|v|format!("[{},{},{},{},\"{:?}\"]",v.0,v.1,v.2,v.3,v.4)).collect();
 let usage=array(&[u.input_visible_bytes as u64,u.source_bytes as u64,u.metadata_reserved as u64,u.scratch_reserved as u64,u.metadata_peak_reserved as u64,u.scratch_peak_reserved as u64,u.total_peak_reserved as u64,u.work_used,u.elapsed_micros,u.deadline_ms]);
 let mm=pair(o.memory_declared_maximum);let tm=pair(o.table_declared_maximum);
 let observations=array(&[o.types as u64,o.type_parameters as u64,o.imported_functions as u64,o.defined_functions as u64,o.validated_bodies as u64,o.instructions as u64,o.globals as u64,o.exports as u64,o.data_segments as u64,o.element_segments as u64,o.max_parameters_plus_locals as u64,o.max_operand_values as u64,o.max_control_depth as u64,o.memory_minimum as u64,mm[0],mm[1],o.memory_host_maximum as u64,o.table_minimum as u64,tm[0],tm[1]]);
 let memory=m.memory.unwrap();let table=m.table.unwrap();let mm=pair(m.declarations.memory_maximum);let tm=pair(m.declarations.table_maximum);
 let metadata=array(&[1,memory.0 as u64,memory.1 as u64,1,table.0 as u64,table.1 as u64,mm[0],mm[1],tm[0],tm[1],m.declarations.memory_offset as u64,m.declarations.table_offset as u64,m.instructions as u64]);
 let resolved:Vec<String>=p.imports.iter().map(|v|format!("\"{:?}\"",v)).collect();
 format!("\"source\":\"{}\",\"sections\":[{}],\"inventories\":[{}],\"instructions\":{},\"usage\":{},\"observations\":{},\"metadata\":{},\"resolved_names\":[{}],\"policy\":\"{}\"",p.source.iter().map(|v|format!("{v:02x}")).collect::<String>(),rows.join(","),inventories.join(","),m.instructions,usage,observations,metadata,resolved.join(","),p.policy_identity())
}
