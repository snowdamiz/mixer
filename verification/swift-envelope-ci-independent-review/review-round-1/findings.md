# Independent round 1: runner acceptance withheld

Reviewed runner `4f5c6d64cb821b3fc1984794c96f81c8610c441ec47e3ff37cabb95b01fb43f1`
with pinned manifest `4800e90fa39b81d0e6514afa087a77b93f838204883974df7fbbec4c69a21b9a`.
All execution used byte-identical portable copies inside this review packet.
The live candidate and its source pack were not changed.

Two acceptance blockers are independently reproduced:

1. `rustc_identity`, lines 269–275, silently overwrites duplicate identity fields
   and permits missing commit identity. Contradictory host/release fields passed
   the full runner; separate missing-field and duplicate-field controls reached
   library compilation instead of refusing identity. Require one complete,
   coherent set of compiler fields before tuple selection, with no last-value
   overwrite of contradictory or duplicate entries.
2. `verify_negative`, lines 360–365, accepts any nonempty in-range byte span in the
   correct file. The real compiler's eight intended negative diagnostics were
   independently interposed so each primary span became byte0..1, the unrelated
   leading `u` in `use`. The runner still returned `passed-host-fixture-check`,
   exit0, 23 commands and no errors. Bind primary spans to the selected probe's
   actual refused item/trait/field at its expected source location. Preserve code,
   target and abnormal-failure checks.

The compound interposer retained original real compiler output and every span
change separately. It delegated compilation to actual Rust1.99.0, but its result
is adverse runner evidence and cannot qualify a compiler or product run.

A separate clean actual Rust1.99.0 Applearm invocation passed in50.671087 seconds:
78 producer and14 independent methods from both listing and execution, API1+8,
21,714 comparisons and32 layouts. Its 23 command records, raw streams, source
snapshots and92 retained test files are preserved. Independent reconciliation
checks the complete actual-File report set and lossless retained bytes. The
initial PATH-missing attempt remains failed rather than being reclassified.

The 33 independently authored early fault invocations produced31 expected
refusals and the two identity acceptance failures above. They cover pack/member
mutation, hidden extras, links/FIFO, optimized-mode pack refusal, output/unknown
option refusal, tuple selection, environment scrubbing, compile/spawn failures,
scratch ownership, postflight mutations, an owned descendant timeout and a real
retention interruption. The latter left its complete64MiB sparse source
recoverable. Synthetic special objects were journaled and removed by the
reviewer only after preserving runner refusal evidence; the runner did not
remove them. No unrelated process discovery or termination occurred.

The52 frozen controls remain a plan inventory, not52 passed tests. Strict bad
method/listing/layout response controls, additional negative-diagnostic false
positives, optimized-mode diagnostic refusal and remaining timing/launcher
variants are pending the selected parser correction. This round stops at the
requested finding handoff. Root withholds acceptance and CI wiring.

Rust1.98.1 envelope CI qualification remains pending. Framing44 and its workflow,
hosted/native paths, capture/UI and phones were not used. No toolchain was
installed or fetched. Semantic/full replay, native/device, signing/store,
FieldLog, operational and GA qualification remain false or pending. The
preaccess, lint and compiler freezes remain unchanged.
