# Independent proposal audit, 2026-10-23

Recommendation: accept a distinct fixed Rust-only Swift policy and a validator-only
first slice after the clarifications below. Do not approve runtime composition as
part of that slice. The proposal's frozen Profile/Limits/native-route boundary and
its refusal to treat the diagnostic as admission are correct.

This review changes no engine code. `receipt.json` binds the reviewed sources,
artifact, tools, commands and compiler output. The current revision was
`92e93b21add0d2f41cd43037b48c181f35d9f293`. The target was independently hashed as
53,777,114 bytes, SHA-256
`24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994`.
`valid=false` and `authorization=false` remain deliberate. No Wasm body was
validated, admitted, instantiated or executed by these probes.

## Changes needed before implementation approval

1. **Make the proof's authority unambiguous.** Proposal lines100-108 permit other
   bytes under the fixed policy, while lines187-201 describe an exact target
   contract and a separate private fixture policy. These can coexist only if the
   result has a precise meaning: complete validation under a fixed grammar,
   resource and import/shape policy is distinct from attestation of the pinned
   artifact. A module with matching imports/exports/memory/table may have different
   function bodies. The runner must bind the immutable bytes actually validated;
   no shape check or policy name proves their SHA-256. Choose either (a) the public
   constructor always checks the stated target shape and private unit helpers
   test smaller shapes without producing that public proof, or (b) two distinct
   sealed proof types with an explicit reviewed attestation transition. Option(a)
   is the smaller first slice. Do not expose a shape-bypass flag, configurable
   resolver or test-policy constructor to an external Rust consumer. Fixture
   success cannot be relabeled exact-reactor qualification.

2. **Preserve declared limit forms before normalization.**
   `experimental/metadata.rs:182-205` currently replaces an absent maximum with
   the host maximum and retains only `(min,max)`. After this, the specified memory
   with no maximum cannot be distinguished from an explicit maximum768, and a
   table minimum46,713 with no maximum cannot be distinguished from a fixed table
   if its host cap is46,713. Check or retain the declaration flags before sealing.
   Preserve separate declared minimum/optional maximum/resolved host maximum,
   require a declared fixed table46,713/46,713, and reject a declared memory maximum
   for this exact shape. This should be private metadata; existing public views
   continue returning their frozen resolved pairs.

3. **Split the signature and local ceilings.** The table proposes parameters per
   signature128 and parameters plus locals256. Current metadata uses
   `policy.locals` for signature parameter count (`metadata.rs:247`), and complete
   validation uses the same field for local groups/expanded combined locals
   (`validate.rs:146-154`). Setting one field256 does not implement the128 rule.
   Resolve explicit `parameters_per_signature`, `type_parameters_total`,
   `local_groups_per_function`, and `parameters_plus_locals` limits. Check the
   aggregate before expansion/reservation. Keep existing legacy meanings intact.

4. **The earliest execution deadline needs an internal adapter seam.** The new
   outer deadline starts before cache/state construction; existing WASI starts a
   private later deadline in `WasiContext::new` (`experimental_wasi/mod.rs:187`).
   An outer check before/after `dispatch` cannot enforce the earlier deadline
   inside an OS service or before the adapter commits guest output. Require an
   internal constructor accepting an already selected absolute deadline (or an
   equally closed internal control object) so the adapter's existing `check()`
   uses `min(outer, its own narrowing deadline)` before services and commits.
   Keep public `WasiContext::new` and its standalone semantics unchanged. No
   public callback, caller clock or mutable deadline is required. This is a
   prerequisite for phase2, not work for validator-only phase1.

5. **Specify a real reservation authority and ownership transfer.** Validation,
   cache and execution currently have independent meters; WASI allocates four
   buffers before returning its reservation report (`experimental_wasi/mod.rs:190-
   216`). Summing usage snapshots after construction cannot enforce a shared
   ceiling before allocation. A private ledger must debit an allocation before
   it is attempted, release only after the old allocation is dropped, and travel
   with the sealed owner across stage transfers. WASI needs a private accounted
   construction path in phase2 or pre-reserved exact-capacity allocation tickets;
   its existing reporting constructor is not that path. Define whether the
   qualifying runner's input is inside the256MiB bound or a separately named
   process/harness category, and report both simultaneous peaks. Use actual
   input capacity, including its overlap with the retained copy. Do not sum
   `CacheUsage.peak_total_reserved` with source/metadata again; pinned bytes are a
   subset of resident bytes. Decide which category owns embedded fixed headers,
   ledger/control state and the shared cancellation allocation exactly once.
   Reservation accounting remains distinct from allocator overhead and RSS.

6. **Keep new diagnostics outside frozen error contracts.** Current validation,
   cache and execution `check()` methods check cancellation only; their public
   failure enums have no deadline/combined-resource variant. The new route needs
   typed stage/deadline/combined-limit failures with the first exhaustion's
   cursor, attempted amount, limit and usage. Prefer a Swift-specific public
   failure wrapper plus private shared control state rather than widening old
   public enums, changing old error precedence or adding deadlines to old routes.

7. **Distinguish type validation from active-segment instantiation bounds.**
   Existing metadata checks offset expression types and segment indices, but
   bounds against initial memory/table extents are checked by
   `execution/mod.rs:386-413` during construction. If the phase1 proof promises
   that active segments fit, add checked destination plus count against the
   initial extent to this private Swift policy before sealing. Otherwise state
   explicitly that an otherwise validated module can still trap at phase2
   instantiation. Do not apply new instantiation restrictions to frozen legacy
   validation merely through a shared refactor.

## Resource arithmetic

The compiler probe builds the unmodified VM using the installed rustc1.99.0,
`RUSTC_BOOTSTRAP=1 -Zprint-type-sizes`; this is layout diagnostics only. No nightly
toolchain, dependency or implementation source was downloaded or added.
`layout.stdout` is the complete compiler output; `layout-sizes.json` selects the
relevant current layouts.

| Dimension | Current-source arithmetic | Conclusion |
| --- | ---: | --- |
| Target owned source | 53,777,114 < 67,108,864 bytes | 64MiB contains these bytes; both source meter and span checks must change privately |
| Functions, controls, memory | 79,866 <80,000; 378+function=379 <512; 626 reference pages <768 | Plausible static/reference sizing inputs, not proof of complete validation or runtime fit |
| Target retained metadata with current buffers/layout | 1,036,952 bytes | Includes current520-byte wrapper and8192-byte parameter capacity; excludes future sealed import/policy/ledger additions |
| Conservative metadata envelope for proposed counts in current representation | 1,913,864 bytes | Includes12,288-byte parameter growth overlap and80,000*max(Import20,Function12);16MiB has substantial headroom |
| Conservative scratch sum in current representation | 29,992 bytes | Includes fixed744, local384, operand192, control12,288 and export-sort16,384; stages need not peak together;1MiB has substantial headroom |
| Source copy + top-section payload work | 107,554,182 credits | Independently recomputed from actual framing; excludes inner-section/body parsing, pushes/pops, scans, growth copies and deadline checks |
| Largest successful positive growth possible at768 cap | (767+768)*65,536 =100,597,760 bytes | Approximately95.94MiB before any other mutable state;128MiB state is a bound, not measured demand |
| Loose twice-memory upper bound | 100,663,296 bytes | The proposal's “almost96MiB” explanation is sound |
| Sum of stage partition caps after caller input drop | 235,144,496 bytes | 64+16+16+128MiB plus current four65,536-byte WASI buffers and1328-byte context; below256MiB, assuming cache capacity includes construction/scratch and all categories are covered |
| Validation partition caps including one64MiB caller input | 152,043,520 bytes | 64+64+16+1MiB; before future fixed-ledger additions; report input overlap explicitly |
| Current span decoder Patch / PassState | 32 /4,128 bytes | The legacy diagnostic's24-byte decoder control is not this decoder;512 patches alone would be16,384 bytes |

The16MiB/1MiB budgets are reasonable first-attempt ceilings with these present
representations. Their future measured fit remains unverified. The512,000,000
validation-work ceiling is also an acceptable bounded attempt, but this audit
does not prove it sufficient. The diagnostic's6,505,659 scalar-arity instructions
and67-slot height do not establish type validity, exact work or future layouts.
The16MiB cache,64M cache lifetime work,64 frames/pins,16,384 values,4,096 controls,
100M fuel,1B execution work,32,768 host calls and30-second lifetime remain entirely
unqualified runtime budgets until composition is measured. A cap need not admit
every otherwise valid module; exhaustion must retain no proof/Ready owner.

## Smallest safe phase1 contract

- Add one nondefault Rust entry point for complete Swift-policy validation. Its
  only inputs are immutable bytes, a narrowing Swift validation budget and
  cancellation. A private absolute validation deadline is created at entry,
  capped at120seconds; it is checked by reader/meter work and bounded copies.
  No elapsed-time success or diagnostic fallback can seal a proof.
- Use a crate-private fixed policy with distinct identity and grammar predicates,
  independent count/stack/source/memory/table/validation limits and a closed
  import policy. Legacy entry points resolve to the exact current values and
  import checks. `Profile`, `Limits`, public cache identity, fingerprints and C/
  native routes remain unchanged. Do not represent the new policy as v3 Limits.
- Return an opaque non-Clone `ValidatedSwiftReactor` only after every body and
  all structural/type/index/initializer/import/target-shape checks succeed.
  Retain one immutable source, complete metadata, sealed absolute-index
  `WasiFunction` resolutions, policy identity, validator revision and accounting.
  Expose only copied usage/count/identity diagnostics and immutable source views
  needed for the harness to bind the bytes. No public conversion, deserialize,
  arbitrary proof construction or legacy cache acceptance exists.
- Validate the exact34 imports, their order/module/name/complete signatures,
  no start, the declared memory/table forms, and the three exact exports/index/
  signatures during sealing. Store the resolved enum; runtime must not reinterpret
  names or receive a resolver. A retained JSON descriptor is evidence, never
  trusted input to validation.
- Define a Swift-specific failure with stage/resource/cursor/attempt/limit/current
  and peak reservations/work. No partial owner escapes any allocation, resource,
  cancellation, timeout, malformed or unsupported failure. Transfer the retained
  reservation authority into the proof. There is no cache, instance, initializer,
  corpus invocation, WASI dispatch or execution conversion in phase1.
- One bounded validator lane owns `experimental/{mod,account,metadata,reader,
  validate}.rs` and the new proof module/tests. Root owns Cargo/lib wiring and
  policy approval. Leave cache/decode/execution and standalone WASI unchanged for
  this slice; coordinate any private snapshot accessor changes before touching
  their files. Runtime core/adapter/ledger composition is a later accepted slice.

Phase1 acceptance requires original boundary/type/uncalled-body/unreachable-body,
allocation ordinal, narrowing, cancellation/deadline and compile-fail authority
tests; exact import/order/shape/declared-limit tests; frozen-feature Debug/Release
regression receipts; and one actual complete validation receipt for the pinned
artifact. That receipt must cover all79,832 bodies including the six formerly
rejected functions, bind tool/source/bytes, and retain first failure if a budget
is insufficient. Success would prove complete validation only. Device, published
FieldLog package, runtime, product and GA gates stay pending.
