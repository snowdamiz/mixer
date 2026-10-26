# Private Android owner correction: independent review plan

This is the frozen preaccess plan for reviewing one versioned correction to
the private Android owner proposal. **The correction candidate has not been
opened.** Review may begin only after root supplies its exact frozen seal and
authorizes access. The outcome will be recorded in this document and a separate
`correction-1/review/` receipt after that boundary. The preaccess snapshot in
`correction-1/preaccess/` remains immutable.

The baseline is the original independent review,
[`android-private-owner-effect-contract-review.md`](android-private-owner-effect-contract-review.md),
sealed by manifest
`8f84a627384e42a5695a52b266f420cb4a26e7c670982266432a022ef1071d58`
(77 members, 1,426,839 bytes). Its original 77 member identities were independently
reverified before this plan was written. The original proposal remains
`7547220cc7f1ba6648ca2cbb3fdf96e402b5b3af9abf68906263be57688838a7`,
and its accepted source bindings remain the review basis. No original review or
proposal member will be rewritten or resealed.

## Access and review method

1. Before authorization, read only the original review and its accepted frozen
   source/context bindings. Freeze these obligations, tool identity, exact
   commands/results and source revision/tree context. Do not enumerate, open,
   hash, import or execute any new correction candidate file.
2. After root supplies the exact candidate path, manifest/seal digest and access
   authorization, independently verify manifest identity and the finite member
   set using standard-library hashing. Retain byte-for-byte snapshots of the
   authorized inputs. A mismatch stops candidate review and is reported to root;
   do not seek replacement files or silently refresh inputs.
3. Read the exact corrected proposal and receipt. Compare every obligation below
   to concrete named signatures, entry mapping, ordering, state/ledger semantics
   and future executable subjects. A keyword, broad promise or producer coverage
   count is insufficient. Record supporting line ranges or a concrete missing
   boundary. Do not use the producer checker as an oracle.
4. Check that the correction preserves the other accepted proposal requirements
   and identifies all changed private seams as one coherent implementation
   closure. This is a contract review; do not implement or accept product code,
   select profile literals, run native tests, run CI, commit or change metadata.
5. Report `selection-ready-contract` only if C1–C3 and the preserved requirements
   are explicit and mutually implementable. Otherwise report
   `needs-contract-correction` with the smallest concrete missing contract.
   Neither outcome is implementation, native-runtime, OTA or GA acceptance.

The scope allows small source-only custody/inventory checks. It excludes product
test execution, imported candidate helpers, frozen hosted harnesses, hosted code,
network/install, process discovery, credentials/signing, simulator/emulator/UI or
capture use. Phones remain disconnected. The pause does not prevent later
selected host implementation or cross-compilation.

## C1: cancellation bridge and bounded ownership

| ID | Required independent review obligation |
| --- | --- |
| C1.1 | Name an owner-callable coordinator input-cancellation method that reaches the actual renderer while an operation is active. It must not use the normal operation-entry or idle-disposal path. Ordinary input, engine create/prepare/commit/abort/destroy, renderer disposal and transaction completion are forbidden in this bridge. |
| C1.2 | State that shared terminal/draw/input authority and actual current/pending gate flags close before any cancellation callback, native setter, core allocation, queue removal or cleanup. Terminal sealing sets terminal first; dirty sealing must not terminally retire a healthy lifetime. The scalar barrier has no callback, allocation, collection walk or sink dispatch. |
| C1.3 | Freeze the bounded record roster being cancelled and when that roster becomes owned. Account for current records, pending targets/detached records, shared identities and a candidate under preparation before publication. A fixed-roster claim cannot mean a mutable live collection that reentry replaces, an unbounded history, or a list constructed after a fatal allocation failure. State which prepublication records can own active input and why excluded records cannot. |
| C1.4 | Publish in-progress/claimed/consumed ownership before callbacks. Reentrant dirty or terminal notifications cannot recursively traverse the same roster, restart consumed cancellation or skip independently owned resources. State how an invalidation during cancellation remains dirty and receives at most one later drain. If counters/generations are introduced, exhaustion fails closed before wrap; do not invent accepted core tokens or require a new counter when flags suffice. |
| C1.5 | Retain attempted/returned/failed/deferred/uncertain outcomes and first ordinary failure plus first fatal Error in bounded preallocated diagnostics. Attempt remaining owned cancellation positions after a failure. Fatal discovery cannot depend on allocating suppression-graph traversal. Ordinary cancellation failure terminally retires the lifetime; fatal Error escapes after independent cleanup attempts. Keep toggle cancellation distinct from Handler CANCEL_QUEUED. |
| C1.6 | No early native disposal: active operations may receive scalar sealing/cancellation, while coordinator renderer/session disposition waits for actual operation return. Late-acquired handles/coordinators are accounted for once; a never-returned operation remains explicitly pending. A shared opening/adopted coordinator identity must not receive duplicate dispositions. Internally retired coordinator outcomes must be borrowed rather than repeated. |
| C1.7 | Require future executable actual-subject controls for first/middle/last cancellation positions, ordinary then fatal failure, combined independent cleanup failures, reentry at setter/parent callbacks, exhausted introduced counters, stale callbacks, late acquisition and never-returned pending state. Actual flags are observed before callback bodies; a scripted renderer leaf cannot prove concrete flags. |

## C2: exact renderer terminal route and causes

| ID | Required independent review obligation |
| --- | --- |
| C2.1 | Freeze one explicit renderer terminal-report method through the exact bound Observer and its sole owner Sink. State the signature, exact renderer identity check and change/cause representation; ordinary invalidate is insufficient. No second readiness listener owner or production bypass may be added. |
| C2.2 | Renderer scalar authority closes before terminal report dispatch. Observer retirement/publication occurs before owner Sink callbacks/removal callbacks. Define first ordinary and first fatal cause retention across renderer, observer, coordinator and outer cleanup diagnostics. Correctly retain the concrete cause even when core.close(lifetime) records only CLOSED. |
| C2.3 | Real interaction exhaustion, committed capture failure, failed rollback and fatal concrete current/capture checks all have a route to terminal outer/core state. A draw/input predicate throwing Error must not leave the core LIVE or merely dirty. Preserve exact lifetime/coordinator identity and unchanged accepted core behavior; do not manufacture more specific core terminal reasons. |
| C2.4 | Main-thread enforcement occurs before stale/repeated guards. A foreign reporter cannot mutate the bound lifetime. Retired, repeated, delayed and cleanup-reentered terminal reports are inert after the check, while already retained failures remain observable. State any ordinary-vs-fatal return/throw behavior explicitly. |
| C2.5 | No report, Sink, core call, cleanup, capture, callback predicate, allocation helper or native mutation is added to successful engine commit -> renderer finish. Direct trusted scalar/reference checks remain permitted. Any failure reporting occurs on the failure path outside that interval. |
| C2.6 | Require future executable production renderer + real observer/owner route controls for exact/foreign identity, repeated/stale reports, ordinary then fatal failures, callback reentry and each real retirement family. Assertions observe terminal core state, exact cause/fatal, sealed current/pending gates, inert new input/drains and exactly one eventual/deferred disposition. |

## C3: executable concrete subjects and every callback boundary

| ID | Required independent review obligation |
| --- | --- |
| C3.1 | The actual selected NativeRenderer and actual NativeAppearanceViewsV2 methods are mandatory executable host subjects, together with the needed actual observer/owner/core/coordinator route. Only an explicit finite Android/JNI leaf list is substituted for those concrete renderer/native-view controls. Name each real subject and substituted leaf; a renderer-shaped double, translated model, source scan or compile-only closure cannot satisfy this obligation. |
| C3.2 | Keep the owner/core/coordinator/observer join's separately scoped renderer/JNI leaves truthful. Assertions about its decision/engine ordering must not be presented as concrete Gate/Input/Record behavior. Full pinned-SDK Java/D8 and ordinary app-owned Swift/JNI cross-compilation remain additional checks, not behavioral proof. |
| C3.3 | Freeze all prepublication constructor/default paths, nested hierarchy additions, Record.bind, text/title helpers, installChildren, root/group/title layout, attach, restore/rollback and candidate/precommit checks. Direct nonterminal/exact-operation authority must be rechecked after each callback-capable setter and before the next transaction mutation, including a callback before a native constructor/helper returns. |
| C3.4 | Include NativeSwitch setEnabled/setFrame and other overrides where cancellation callbacks precede superclass mutation, plus scroll-driven navigation relayout. Valid ordinary native callbacks outside a transaction use current clean live presentation/lifetime authority; they cannot universally require a non-null operation token or silently disable legitimate scrolling/focus/paint. Callback reentry that seals the lifetime must stop the next forbidden mutation. |
| C3.5 | Exercise actual scalar current/pending Gate flags, Gate draw/touch/key checks, Input current-record/enabled/attached/shown/focus/capture/toggle checks, sealed new IME refusal before superclass acquisition, retained IME edit rejection, accessibility and native input routing. Include both corrected cancellation/report seams. |
| C3.6 | Require closed leaf hooks to inject terminal/dirty/ordinary/fatal reentry at the named boundaries and observe actual flags before callback work. Preserve existing exact installed/capture/current-record/interaction/journal validation and fail-closed unsupported native operations. Source/bytecode guards only supplement behavior and do not prove platform framework or JNI purity. |

## Preserved entry mapping and shared requirements

| ID | Required independent review obligation |
| --- | --- |
| P1 | Actual root window focus must seed/update unchanged core.focusChanged; reading focus into WindowFacts is insufficient because that record has no focus field. Freeze start/registration callback/drain/lifecycle/observer entry mapping. Foreground and focus govern input; positive geometry/insets/attachment govern readiness. |
| P2 | Every entry, including stale deliveries, repeated close/report/cancel and foreign identities, checks actual main Looper before state. Scalar trusted internal reads are explicitly separated from callback-capable thread-check abstractions. |
| P3 | Observer is allocated/stored before one-shot register, with all callback fields initialized before first add. Preserve accepted eight acquisition/removal slots, exact targets, before-add claims, partial/reentrant acquisition unwind, deferred unregister completion while registering, generation exhaustion and one-shot exact renderer binding. |
| P4 | Coordinator construction is inert allocation/binding; the owner holds its identity before renderInitial session acquisition. Same shared fence and exact accepted core operation token reach coordinator and Candidate. Completion uses exact operation/coordinator after finish and active-operation finally; terminal/OOM paths retain independent bookkeeping without fabricated tokens. |
| P5 | Move the one accepted unchanged core source into export exactly once; no second canonical core. Preserve exact Window/token identity, fresh readiness probes, no polling, per-token owned Handler runnable and stale slot protection, false/throwing post terminal behavior, effect recheck after reentry and no input buffering/replay. |
| P6 | Refresh uses the coordinator's exact retained packet reference/bytes with zero engine create/prepare/commit/abort/dispatch/effects and no Swift revision advance. Synchronous tuple mismatch seals then dirties through the bound observer. Dirty during opening/input/refresh/cancellation stays dirty and yields at most one later owned drain. |
| P7 | Public MixerActivity remains V1, with separate padding inset ownership. Private caller/instrumentation migrates coherently to owner readiness/lifecycle/input. Renderer-only fixtures use the real core for tokens and distinct dedicated roots with sole inset setters; replacements/finally retain explicit cleanup. |
| P8 | Root alone selects future fixed source-profile literals against frozen candidate bytes; one compiled authority projects into the rendered driver. Preserve 22 SDK/default descriptor/wire identities unless an explicitly reviewed change is selected. Reject old/edited/recomputed locks without silent refresh; adding owner/moved core changes the adapter closure coherently. |
| P9 | Newly unrun native checks remain pending under the pause; do not reopen instances or ask for phones. Host/source/compile evidence cannot imply physical Android/iOS, public V2, API28-35 support, OTA authorization, resource reclamation, immutable published separate-repository FieldLog, signing/store or accountable GA qualification. |

The future review records each obligation as explicit/coherent, missing,
contradictory or outside the authorized correction. It separates source-contract
support from promised future executable evidence and currently unrun product
tests. This plan creates no new implementation or release authorization.
