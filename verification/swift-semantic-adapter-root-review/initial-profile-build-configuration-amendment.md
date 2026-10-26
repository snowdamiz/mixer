# Selected finite host build configurations

Actual unit-test compilation includes the original `cfg(test)` WASI fields.
The frozen production local profile correctly refuses that layout with code 6.
Keep that observation and the selected production producer/comparator unchanged.

Select a separate, complete immutable unit-test profile from
`initial-profile-unit-test-local-structure.json`. It carries the same complete
17-field budget and local fields, with only the named byte-size differences:
AccountedWasi (ID 122) 1,496; WrapperCallerStorageV1 (ID 146) 12,360; and
Option<AccountedWasi> (ID 160) 1,496. Their alignments remain 8. It is a separately
named `cfg(test)` literal, never returned by `selected_initial_profile_v1`.
Do not construct expected values from fresh measurements. Before using it,
measure all 165 actual complete sizes and alignments in Debug and optimized
builds in both configurations. Any further difference stops this selection.
Explicitly test that the unchanged production profile refuses under `cfg(test)`.

The actual production-layout success route uses the custom host-only cfg
`mixer_initial_profile_component_host`. Within the six selected new files only,
fixed test modules/instrumentation may use
`cfg(any(test, mixer_initial_profile_component_host))` and methods may use
`cfg_attr(test, test)`. Original source is unchanged. The planned
`compile_contracts.rs` contains this test-only exported dispatcher:

```rust
#[cfg(mixer_initial_profile_component_host)]
#[no_mangle]
pub extern "C" fn mixer_initial_profile_component_host_v1(method: u32) -> u32
```

Its fixed integer roster is:

1. `selected_layout_and_places`
2. `fresh_header_rows_and_cleanup`
3. `same_control_wasi_and_unrelated_owners`
4. `complete17_drift_precedes_prepare`
5. `explicit_narrowed_budgets`
6. `header_retained_when_actual_row_file_refuses`
7. `all64_slot_pin_pairs_checked`
8. `local_structure_refusals`

Unknown methods return 64; completed methods return 0. A failed assertion or
abnormal child exit is a failure. The dispatcher accepts no owner, pointer,
reference, guard, proof, closure or callback and exposes none. It cannot call the
unit-test-only phase-fault helper. Its symbol and other custom test exports must
be absent from an ordinary build without either test configuration; verify the
ordinary artifact as well as source gating.

The declared runner alone starts bounded child Python invocations with argv
`[sys.executable, declared_runner, '--invoke-host-method', str(cdylib), fixed_id]`.
It accepts only the fixed roster, loads the exact owned hashed artifact, selects
only the exact symbol above, and uses uint32 argument/result types. No arbitrary
symbol or callback argument is admitted. Each child has a 30-second bound and
retained output/exit status; remove owned artifacts and scratch after evidence.
This is macOS host component execution, not a native mobile runtime test.

The exact 140 distribution plus eleven support input paths remain fixed. Retain
each source/cfg/target/tool/artifact/argv/environment manifest and both build-mode
results. Unit-test fault outcomes do not qualify production-layout success;
custom host success does not substitute for the original typed failure matrix.
Preserve original actual fault authority and cleanup, with no fabricated marker,
ledger repair, refund, first-failure erasure or layout bypass. The complete actual
place/lifetime/heap/work/I/O/cleanup accounting must close separately in both
configurations under unchanged reservations, limits and deadlines. Layout table
agreement alone does not close that proof or accept the component.
