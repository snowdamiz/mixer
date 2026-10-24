# Swift dispatch accounting checkpoint

The private calls and full-dispatch source has passed independent and root logical
accounting review. The accepted source closure is
`ba9231499244692bbed61f0566ec72864a979df9e3fc71511560ec66a2e00c70`, bound by
producer seal `7d5a043e7c982a84d5fe1a85444a6a492a40ebddf87a36e95ebdedde02593b15`.

The review covers 89,124 roles: 82,768 active and 6,356 permanent. Exactly 1,032
finite compiler-layout positions have individual identity/layout mappings; they
are not a type-wide exception. Eight final compiler contexts, sixteen paired
layouts, 524,512 compiled fields and thirteen independent rejecting mutation
controls support the decision. All 39 Frozen methods, its 2,912-byte bound,
original owner layouts, ticket maximum 86 and State/Combined ceilings remain
unchanged. These are logical object bounds, not stack or RSS measurements.

Root separately replayed all 11,404 producer seal bindings and the complete
accounting report, then verified the independent review's 39 sealed files and
report. The exact finite and temporal selection is recorded in
`verification/swift-calls-dispatch-root-review/v5-accounting-selection.json`.

The runtime preflight found an outdated original fixture expectation in
`frame_operations_tests.rs`: its sum excludes the new dispatch active component,
which the production formula already includes. This was found by source review;
no failed runtime is claimed. Root selected only the missing term in the existing
exact equality. The original sealed package remains unchanged. A separate source
revision must bind that one test expression and refresh its compiler-context
proof before qualified execution. See
`verification/swift-calls-dispatch-root-review/frame-bound-fixture-amendment.json`.

Four-configuration CD01–CD24 execution, full library and Frozen regressions,
allocation/admission checks and live integration remain pending. The separate
GitHub checkpoint `cf52825` has terminal success for Swift, VM and services; that
CI does not qualify these uncommitted private candidates. Full Swift lifecycle,
Ready, public invocation, native parity, immutable external FieldLog packages,
physical-phone acceptance, signing/store, OTA and GA remain open.
