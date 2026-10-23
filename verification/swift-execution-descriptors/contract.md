# Frozen borrowed-descriptor prerequisite

Root delegation, 2026-10-23, baseline
`bd8a8967d32692765de0d4dd14f5d88b7d5009ff`. Frozen before implementation.
This accepts only the descriptor prerequisite; the larger cache/execution proposal
remains under review. This is not executable authority or release qualification.

All new types, fields, modules and methods have visibility `pub(crate)` or
narrower. Every slice borrows the sealed proof's existing immutable storage.
No metadata exposure, source/metadata copy, allocation, mutation, constructor,
legacy conversion, new policy variant or public API is authorized.

```rust,ignore
SignatureView<'a> { params: &'a [Type], result: Option<Type> }
FunctionSpanView<'a> {
    absolute_index: u32, type_index: u32, body_offset: usize, body: &'a [u8]
}
GlobalView<'a> { ty: Type, mutable: bool, initializer: &'a [u8] }
SegmentExecutionView<'a> {
    destination: u32, count: u32, payload_offset: usize, encoded_payload: &'a [u8]
}
MemoryExecutionView { minimum: u32, declared_maximum: Option<u32>, host_maximum: u32 }
TableExecutionView { minimum: u32, declared_maximum: Option<u32>, host_maximum: u32 }

impl ValidatedSwiftReactor {
    fn execution_signature(&self, absolute: u32) -> Option<SignatureView<'_>>;
    fn execution_type(&self, type_index: u32) -> Option<SignatureView<'_>>;
    fn execution_function(&self, absolute: u32) -> Option<FunctionSpanView<'_>>;
    fn execution_global(&self, index: usize) -> Option<GlobalView<'_>>;
    fn execution_global_initializer_offset(&self, index: usize) -> Option<usize>;
    fn execution_data(&self, index: usize) -> Option<SegmentExecutionView<'_>>;
    fn execution_element(&self, index: usize) -> Option<SegmentExecutionView<'_>>;
    fn execution_global_count(&self) -> usize;
    fn execution_data_count(&self) -> usize;
    fn execution_element_count(&self) -> usize;
    fn execution_memory(&self) -> Option<MemoryExecutionView>;
    fn execution_table(&self) -> Option<TableExecutionView>;
    fn execution_imports(&self) -> &[WasiFunction; 34];
    fn decode_policy(&self) -> &Policy<'static>;
}
```

`execution_signature` covers every one of the 34 absolute imported functions and
every defined function. `execution_function` uses absolute indices and returns
`None` for all imports and out-of-range indices. Type lookup uses type indices.
Global initializer/body/payload offsets are absolute retained-module byte cursors.
No cursor is derived by pointer arithmetic or from the policy's source ceiling.
The exact source extent remains `source().len()`.

Memory reports minimum 584, no declared maximum, and effective stored host
maximum 768. Table reports minimum 46,713, declared maximum `Some(46_713)` and
effective stored host maximum 46,713, independently of the policy ceiling 65,536.
The descriptors preserve segment order, overlaps, zero-length segments and exact
encoded element LEB bytes without expansion. All failed lookups return `None`;
future consumers must map impossible failures to their typed invariant.

The literal fields/layouts of `ValidatedSpans`, `ValidatedSwiftReactor`, metadata,
`GlobalView`, public `SegmentView`, cache and execution owners remain unchanged.
Legacy getter behavior is unchanged. Policy visibility may widen only to
crate-private for the closed borrow; its variants/getters remain unchanged.

Acceptance: debug/release executable tests using original small modules passed
through the actual public validator; all import/defined mappings and range
boundaries; exact cursors including zero-length/overlapping payloads; declared
versus stored host maxima; unchanged source/usage; zero-allocation repeated
borrows; external compiler privacy and lifetime negatives; exact baseline source
and target layout comparisons; and relevant legacy validation/cache/execution
regressions. Record complete command output, versions, source digests and limits.
No full target instantiation, `_initialize`, corpus invoke, physical-device work,
publication, commit or push is included.
