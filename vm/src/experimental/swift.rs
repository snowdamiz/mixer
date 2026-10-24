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
