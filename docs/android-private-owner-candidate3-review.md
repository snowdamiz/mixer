# Private Android owner independent candidate-3 review

Candidate 3 is **rejected** for a confirmed concrete-gate boundary defect after a
successful lifecycle-only dirty operation. This review preserves the candidate-2
rejection and the repaired candidate-3 controls. The full site matrix remains
pending; producer test counts receive no independent credit.

The admitted manifest is
`c5bed3d89498abe0f9d9ee2547e74f4b26d2f29a05c9744e09b61d47259ecb6b`
(1,215 members, 11,798,221 bytes). Root admission
`81f9a86838a060063db5ffa5abd9ee63581e5032a9899a68e88165f03c5e7378`
and subsequent gate finding/CLI hold
`e215582b755848778b125c77dc73eb64e0195db33d8768e5e936c02daecb79cb`
are retained. Native source was read only from the immutable snapshot. No evolving
producer source, producer runner/model execution or root CLI lane was accessed.

At actual `NativeBridge.prepareV2` entry, the independent witness calls actual
`owner.onPause()`. This dirties the real core without changing Observer generation.
The real coordinator correctly commits and finishes; `core.complete(..., true, ...)`
leaves the core LIVE/dirty and queues one later drain. At that drain's actual
`Handler.post` entry, shared draw/input authority is false but the actual current
`Gate.open` is **true**. `finishV2` reopened it; owner completion processes the queue
before `publish`, and the dirty publication branch does not seal concrete gates.
This violates C1 concrete gate closure at callback entry. It does not demonstrate
shared authority reopening or an extra engine operation.

Frozen source anchors are `NativeRenderer.java:403` and
`NativeOwnerV2.java:316–331`. [The failed witness](../verification/android-private-owner-independent-review/implementation-review-2/targeted-6/03-active-lifecycle-dirty.stdout)
and assertion failure are preserved. Its independent mini-seal
`f0bf0150fed64e0e3b47da17e7432ffa1d32d1ae34f2c678b478fc6429e9f1e2`
binds 128 exact source/input/evidence members, 1,396,374 bytes. Root independently
verified that closure. Repair must preserve successful lifecycle-dirty completion,
close concrete gates before completion bookkeeping/queue callbacks, and publish
only for a clean/current actual core completion. All such work belongs outside
the successful commit-to-finish interval. No repaired bytes were inspected here.

The earlier findings have bounded corrected evidence:

| Earlier finding | Candidate-3 independent evidence and limit |
| --- | --- |
| Returned input cancellation mislabeled while active | The failing lifecycle-dirty witness separately confirms actual cancellation is `RETURNED` while the real coordinator remains busy. |
| Fresh input focus/core work before sealing; ignored nonterminal SEAL | Retained fresh-focus witness now sees all shared/current flags closed at `Handler.post`. Source implements capture-before-seal and cancellation-specific admission checks. |
| Readiness probes after terminal cancellation reentry | Actual `Gate.invalidate → owner.close` onResume witness now stops ordinary readiness probes. Separate start/Work entry controls remain pending. |
| Renderer-only fixture/factory unwind | Frozen source independently catches observer, renderer, core and parent cleanup failures, retaining first primary/fatal. This remains source-only; no native fixture fault execution occurred. |
| Explicit immutable scope propagation | Frozen helpers and renderer/recursive/live callers now use explicit scope parameters with save/restore. Full live recursive positive behavior remains pending. |
| Lost Work identity after post enqueues then throws | Retained witness now removes exact Work once and leaves zero queued work. Three added entry/before-return controls retain the real core cancel token while posting, complete it only after removal, and preserve fatal/uncertain removal with inert stale delivery. |
| CLEANUP accepted as ordinary helper authority | All 13 actual ordinary helper families reject both an actual stale-live scope and CLEANUP before any native leaf: 26 refusals. No tokens or successful expected product behavior were fabricated. |

Three additional actual-source controls pass:

- Actual Observer invalidation during prepare advances generation 1→2, rejects
  the stale capture, retires the operation, aborts once, destroys once and never
  commits. All eight Observer cleanup slots return. This is distinct from the
  lifecycle-only dirty case above and preserves the selected clarification.
- Environment refresh retains the exact coordinator byte-array identity and
  packet revision while publishing a new real presentation. It performs zero
  additional JNI create/prepare/commit/abort work.
- A fatal actual current check through Gate draw reports `CURRENT_CHECK_FATAL`,
  retains/escapes the same Error, defers disposal during the report frame, posts
  one terminal tail and destroys once after unwind. The exact core close token
  completes only after that tail.

The retained completed-successor IME positive still returns the delegate's true
result across real synchronous successor publication. Actual descriptor/packet
decoders consume independently authored inputs. Two initial helper-fixture
failures reused a generation across multiple nodes and were rejected by actual
`UiPacket`. Their exact bad packet, authored sources, diagnostics and raw failures
are preserved as reviewer setup failures. The corrected helper packet uses unique
generations and publishes through the actual owner before negative helper calls.

Compilation uses exact selected 14 production subjects, 73 admitted mechanical
Android/JNI substitutes, leaf-3 probe and one independent driver; no product source
overlay. Core hash remains
`4282e8284212fb042a139f597d9f34f061f6f27673e918a52f1f784e6fe9ebb6`.
All historical driver/runner versions and input data are retained.
[Runtime identity bindings](../verification/android-private-owner-independent-review/implementation-review-2/runtime-frame-bindings.json)
bind all 38 retained Site frames to actual source hashes, compiled class hashes,
JVM descriptors, bytecode instructions and line tables. They do not replace full
site inventory/discrimination.

Root additionally authorized three frozen historical host test sources solely to
enumerate/map 133/141/173 migration obligations. Their exact hashes and a source
index are retained; none was compiled, imported, executed or used as expected
behavior oracle. The migration obligation remains pending. A portion of the core
test body was visible during source enumeration; expected outcomes here continue
to come from the sealed contracts and independently authored preaccess cases.

Official local OpenJDK 27 compiles with `--release 17`, debug line tables, strict
warnings, disabled annotation processing, empty class/source paths and an explicit
source list. Runtime is JDK 27, not a JDK 17 qualification. Every observed child
returned, was reaped, and exclusive scratch was removed; 120-second, 2-MiB-stream,
one-child bounds and Java 256-MiB heap remain. Exact commands, tools, source/class
hashes and raw outputs are retained. No native/UI/capture/process discovery ran.

This packet contains 14 distinct targeted controls, 13 passing and one confirmed
boundary failure, plus two preserved reviewer setup failures. It does **not**
complete any universal seven-case site matrix. All 184 baseline sites plus newly
introduced sites (root/producer report 189 total), all seven cases, five V1
positives, full actual Closure A/B coverage, historical vector migration and
remaining source/caller/helper-return obligations remain mandatory. CLI validation
is held; device/native, public V2 and GA qualification remain pending. Candidate 4
requires a separate root admission and independent review packet.
