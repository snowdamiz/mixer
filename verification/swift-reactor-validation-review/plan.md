# Independent Swift reactor validation review plan

Review scope: the accepted `docs/swift-reactor-validation-stage-design.md`, the private policy/shared validator, and the non-executable Swift proof boundary. Review owns only this evidence directory. Implementation and tests are active; no compile or test will run against their moving source. Coordinate freeze with `swift_reactor_validation`, snapshot all relevant source, retain an archive/manifest and before/after digest, and use an external target directory.

Independent original probe plan:

1. Encode a small valid module from the retained 34-import descriptor ABI, independent of the implementation lane's fixture builder and `WasiFunction::ALL`. Keep the exact memory/table/export declarations and all 29 defined bodies.
2. Alter each import's signature and name/order/count; exercise optional-maximum distinction, export names/kinds/indices/signatures, imported resource kinds, start section, malformed names, section order, unsupported forms and instruction families.
3. Alter uncalled and unreachable bodies, control results/branches/branch-table target types, local/global indices, indirect calls, memory alignments and numeric operand types. Require complete body count for valid fixtures.
4. Check unsigned data/element destination+length against exact initial extents, including empty boundary segments, negative i32 constants interpreted unsigned, explicit nonzero target indices, bad element function indices and overlapping ordered segments.
5. Check input/source ownership, narrowing/exact/zero/widened budgets, pre-cancellation, allocation failure/cancellation ordinals and allocation-free cleanup. If timed probes are used, state their observed stage and avoid claiming a deterministic stage from elapsed time alone.
6. Compile negative proof-authority snippets: fabrication, mutation, clone, conversion to legacy proof/cache/eager module. No target execution or device access.
7. Compare frozen `validate_spans` behavior at exact legacy metadata/scratch/work boundaries against an immutable pre-change baseline, then with the frozen shared implementation and feature combinations. Added layout fields are a source-level compatibility risk until measured; do not call them a confirmed regression without the comparison.
8. Inspect immutable target qualification receipts and independently check retained target size/SHA if needed; complete validation evidence must identify all bodies, six formerly deep bodies, source/caller overlap, work, peaks, deadline and source snapshot. Validation is not execution, package publication, device qualification or a GA gate.

Initial source review finds explicit private policy identity, distinct non-executable proof fields, preservation of optional declared maxima, exact ordered adapter resolution, all-body operand/control typing, and checked unsigned initial-segment bounds. This is preliminary inspection, not frozen-source verification or final approval.
