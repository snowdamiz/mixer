# Private Android owner correction: independent contract review

**Correction 1 still needs a versioned contract correction before selection.**
The cancellation bridge, terminal-report plumbing, focus mapping and executable
concrete-subject requirement resolve the original missing seams. One remaining
roster contradiction imposes V2 fence semantics on five unchanged V1 call sites.
This is a source-contract recommendation, not implementation acceptance.

Root authorized access to correction manifest
`1479c098f5721cc80e0c82f8699d1482a30f71ad241fa06cfe2c6902255bec08`
(48 members, 974,667 bytes), including
[`android-private-owner-effect-integration-correction.md`](android-private-owner-effect-integration-correction.md),
SHA-256 `0df969beb88bce09af83b12bf9789f14ee65f1d09105a1c0300c0f42a8e4f895`.
Independent custody verified every member and all 189 baseline source
line/expression/column anchors. The immutable preaccess plan has 28 obligations,
sealed by
`638028e6531f4846d5d68e8979b24a0742d243207e54d184addc14bd2246923c`.
Original review/proposal and corrected candidate bytes remain unchanged.

## R1: distinguish legacy V1 baselines from mandatory V2 semantic barriers

Correction lines 349–359 require every selected barrier to execute clean,
terminal/dirty reentry and ordinary/fatal throw cases, with actual V2 shared/
current/pending gates observed and terminal reentry stopping the next forbidden
Mixer mutation. The machine-readable roster selects these five additional sites
in `NativeRenderer.java`:

| Exact frozen ID | Line | Expression | Actual enclosing path |
| --- | --- | --- | --- |
| `NativeRenderer:L60:C234:1` | 60 | `parent.removeViewAt(` | Legacy `children(...)`, reached by V1 `apply(...)` |
| `NativeRenderer:L61:C242:1` | 61 | `parent.addView(` | Same V1 helper |
| `NativeRenderer:L62:C149:1` | 62 | `view.setLayoutParams(` | Same V1 helper |
| `NativeRenderer:L62:C454:2` | 62 | `lp.setMarginEnd(` | Same V1 helper |
| `NativeRenderer:L62:C509:3` | 62 | `view.setLayoutParams(` | Same V1 helper |

The frozen real source makes that distinction concrete: V1 `apply` calls
`children` at lines 21–27; the private V2 section starts at line 65 and uses
`NativeAppearanceViewsV2.installChildren/layoutRoot` instead. V1 `apply` rejects
an owner with V2 installed/environment/plan/pending state. These five helper
calls therefore cannot be exercised as the new V2 transaction/terminal fences
without selecting V1 behavior changes or constructing a production bypass.
Correction lines 23–25 and 409–411 explicitly preserve public V1.

Complete-source compilation justifies the V1 Android types in the leaf roster;
it does not make these legacy calls V2 semantic barrier subjects. Because every
listed barrier is mandatory with no discretionary subset, an implementer cannot
silently ignore or reinterpret these five entries.

The minimum next correction is a **new versioned roster/contract amendment**
that classifies legacy V1 compile/baseline subjects separately from V2 semantic
barrier subjects and defines each class's assertions. Preserve this correction's
189-entry inventory as historical evidence. There are 184 entries in the V2
source regions and these five in the V1 helper. It is reasonable to retain the
five as V1 baseline/compile checks, provided the new version removes their V2
fence obligations and explicitly preserves V1 behavior. No V1 implementation
change is requested or selected.

This single blocker affects preaccess obligations C3.3, C3.6 and P7. The other
25 obligations have explicit coherent source-contract support; none represents
an executed implementation test.

## Resolved contracts and retained acceptance work

| Area | Independent source-contract conclusion |
| --- | --- |
| C1 active-safe bridge | `cancelInputFromOwner(long)` reaches the bound renderer without operation entry, session mutation or disposal (lines 126–130). Scalar shared/current/pending flags close first. Fixed indexed current/target/detached rosters, stable pass snapshots, per-record claims and no nested transaction close the mutable-collection/reentry gap (143–157). |
| C1 failures and exhaustion | Serial begins at 1, never wraps or resets, and MAX terminally seals with a retained owner cause/core close (117–124). In-progress/consumed claims precede callbacks; newer recursive serials do not recurse/rebuild/restart (132–141). Each native pressed/invalidate/parent-release attempt and remaining record continues after ordinary/fatal failure (159–175). First ordinary and first fatal are bounded fields. |
| C1 disposition ownership | Cancellation is distinct from Handler CANCEL_QUEUED. Active operations may complete cancellation/unregister while coordinator disposition remains deferred; operation/cancellation/report frames must unwind (170–177). Late-acquired ownership and never-returned pending outcomes remain explicit original requirements. |
| C2 typed cause/fatal route | `rendererTerminal(renderer, cause, primary, firstFatal)` and matching Observer Sink/owner signatures preserve a separate Error reference end to end (lines 34–37, 56–65, 181–202). Exact bound identities and a separate terminalProcessed claim prevent an already-set shared terminal flag from swallowing core transition. Core CLOSED keeps its meaning while the adapter retains detail. |
| C2 retirement/failure families | Interaction exhaustion, installed/environment capture errors, failed rollback and fatal current/draw/input capture checks have named routes (204–225). Foreign live reports reject without accepting diagnostics; main checks precede stale/repeated guards. Actual newly observed cleanup Errors remain retained and rethrown even when a later report is inert. |
| C2 report/disposal reentry | Report/cancellation/operation busy frames prevent early nonreentrant disposal. Outside an owner effect, one typed TERMINAL_CLOSE tail uses the same owned Handler slot after the callback stack unwinds (228–244). Exact token/resource, stale delivery and false/throwing post behavior remain explicit; unsafe reclamation is never fabricated. |
| Successful commit/finish | Direct scalar commitFinish marking and trusted checks preserve the successful no-callback/capture/allocation/native-mutation interval. Deferred failure reporting occurs after its finally clears the flag (246–255), then exact completion/publication follows finish and active=false. Required bytecode/source guards supplement future execution. |
| Mandatory concrete closure | Closure B has 14 actual production source subjects, 73 unique substitutes: 72 Android FQCNs and only NativeBridge outside Android. No renderer/view/decoder/capture substitute is allowed. Closure A separately has 10 actual subjects and 74 substitutes including its scoped renderer leaf. Both remain unrun (313–347). |
| Concrete callback boundaries | Prepublication constructors/defaults, early virtual calls, all multi-setter helpers, hierarchy/layout/restore, switch overrides, live scrolling, Gate/Input/IME/accessibility and real report/cancellation paths are mandatory (288–311, 362–387). Subject/domain classification for the five R1 entries still needs correction. |
| Valid ordinary callbacks | Transaction mutations retain exact operation scope. Ordinary native scrolling/layout/input captures live-presentation scope with no fabricated non-null operation token. Cleanup scope cannot bind/layout/reopen/send input (279–311). Positive ordinary scrolling/gesture/IME controls are explicitly required. |
| Focus/lifecycle mapping | Initial seeding, observer invalidations and fresh delivered probes read actual root focus and call real core.focusChanged on initial/changed focus, with focusKnown/lastFocus state (259–268). Resume/pause/stop/detach/registration/adapter failure routes are explicit (270–277). WindowFacts is never treated as carrying focus. |
| Original requirements | Stored-before-register observer, eight exact uncertain acquisition/removal slots, one-shot binding, inert coordinator, exact unchanged moved core/tokens, exact-packet zero-engine refresh, synchronous unbuffered input, per-token single owned work, tuple mismatch invalidation, profile authority/migration and private caller/inset ownership remain mandatory (102–113, 398–417 plus unchanged original proposal). |

The mandatory roster covers 189 baseline sites with seven named future cases per
site. This review verifies their custody and actual source anchors; it does not
claim those future cases executed or constitute 1,323 behavioral passes. New
calls in the same selected V2 regions must receive additional mandatory IDs.

## Evidence, limitations and handoff

The independent packet is
[`correction-1/review/`](../verification/android-private-owner-effect-contract-review/correction-1/review/README.md),
with exact candidate snapshots, root admission, tool/revision/tree context,
independent roster inventory, per-obligation judgments and retained command
streams. The original 77 review members and preaccess five-member seal were
reverified without editing them. Two retained reviewer custody-helper attempts
corrected a comparison of stripped anchor text versus original indented column
coordinates; neither was a producer defect or a product test.

The producer's **666 reported checks are custody/coverage checks only**. This
review read their declared scope and did not execute the producer verifier,
import producer helpers or count those checks as implementation evidence. Both
host closures, cross-compilation, profile migration and native tests remain
unrun. No product/profile/metadata/CI edit, commit, hosted harness access,
network/install, credential/signing, process discovery, native runtime, UI or
capture action occurred in this lane.

Root should request the one bounded versioned R1 roster correction, preserve all
existing packet bytes, then obtain independent verification of that correction
before selecting implementation. Host development may continue once selected;
the active native/capture/UI pause and disconnected phones remain binding.
Physical/device/accessibility/performance, separate-repository immutable published
FieldLog, public V2/API28–35 support, signing/store/operational and accountable GA
qualification remain pending. No source-contract outcome grants OTA authority.

The immutable preaccess obligations and original method are retained at
[`preaccess/review-plan.md`](../verification/android-private-owner-effect-contract-review/correction-1/preaccess/review-plan.md).
