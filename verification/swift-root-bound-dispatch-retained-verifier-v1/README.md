# Retained-configuration region verifier candidate

This isolated candidate adapts accepted physical-evidence v2 to exactly the
alternate diagnostic capture with `-C link-dead-code=yes`. The original verifier
and all earlier packets remain unchanged. This directory is not canonical product
source, and no actual geometry input has been passed to this verifier.

The binding is fixed to source tree
`91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f`,
compiler commit `b940084d7eb6a299eb4bfeb8e34901bc051e7ac4`, target
`aarch64-apple-darwin`, the same four features, fixture cfg, opt/MIR levels,
overflow checks, unwind mode, codegen units and debug info as v2. Only the selected
capture/argv identities change:

| Identity | Original v2 | Retained candidate |
| --- | --- | --- |
| Capture plan | `bed9476b169810452ac0932605784125365f57c897d1e3bf74cd9eaa6ebb8184` | `15413684daf6815fbc9773c7fecf669f035768116524e567a841bd571c3f31c8` |
| Canonical argv | `4022ae1057439fe5ae31d18675a884b2dc3e56f317a8ddced08bfb163a410aaa` | `799f61fd0bff3d5eba3849b784e7bc7b699a5ee84a2a814f298f407befb28e75` |

`CURRENT_BINDING` matches the immutable retained plan's `verifier_binding`
exactly, including `link_dead_code=true` and
`alternate_diagnostic_configuration_only=true`. Its observation grammar matches
the existing immutable capture observation: alternate scope is repeated at the
top level with `original_capture_qualified=false` and
`runtime_admission_accepted=false`; retention remains in its binding. No capture
receipt rewrite or new capture is required by this schema adaptation.

The new certificate, capture-acceptance, independent-review, independent-seal and
trusted-root-approval envelopes explicitly require all four fixed scope fields.
Every success, incomplete and invalid result emits those same four fields, plus
`local_geometry_only=true` and `complete_capacity_accepted=false`. Missing,
unknown, incorrectly typed or contradictory scope/build fields refuse, including
review/seal scope when no approval is supplied. The
certificate cannot select an arbitrary build, choose synthetic mode or supply its
own trusted approval digest. Synthetic fixtures can replace only `source_tree`;
that exception cannot pass actual mode.

The complete `geometry` function, including all physical-congruence, unknown and
capacity rules, is byte-identical to accepted v2. The sixteen P01–P16 test bodies
are also byte-identical; only shared synthetic-envelope construction and scoped
result assertions change. Seven additional B01–B07 methods exercise exact actual
binding validation without geometry execution, original/cross-build refusal,
every source/compiler/target/flag pin, missing/false/incorrectly typed retention,
scope laundering, freshly rejoined review/seal/approval scope and scoped invalid
or incomplete outcomes. All artifact bytes used by tests are synthetic. The
private regular-file/symlink test cleans its own temporary files.

`freeze/host-controls.json` records the selected bounded Python `-B` control run,
before/after input and tool pins, command, output and cleanup. No external child,
compiler, model/product/native runtime, version/process probe, UI automation,
screen capture or network call is part of it. The Python version is attributed to
the existing retained-plan receipt rather than a new version query. A prior
passing run before tightening unapproved review/seal scope is preserved in
`freeze/attempt-1/`, with its reconstructable source delta. The changed source
received a fresh run; neither run retried automatically.
`freeze/source-delta.patch` and `freeze/change-inventory.json` show the limited
adaptation. `freeze/seal.json` binds the final candidate and evidence files.

Root's retained identity acceptance covers capture custody and the four native
identities only. Actual semantic-map review, trusted approval construction and
actual-input execution remain pending. No real geometry, capacity, prices,
physical backing/destruction bounds, root funding, runtime admission, canonical
integration, FieldLog, OTA or GA acceptance follows from these controls. The
original capture remains unqualified. Native/UI and local-custody Unit A holds
remain in force.
