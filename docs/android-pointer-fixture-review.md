# Private Android pointer fixture review

The frozen candidate-4 build passes independent host build and packaging review.
Its runner/oracle packet is **rejected for native dispatch** because five finite
adversarial controls survive the oracle. Root accepted these findings as blocking
and selected a bounded repair. This review authorizes no native run.

The reviewed APK is
`ac791015118ed259ff29b67f1e8140b27d2111b9df807c2b7e211b952fed70a4`,
from archive
`54f8ecc577727dbbae00fcc39b20841a71ba593a657f99bdff0d4da54ed74974`
and 105-input closure
`93a7796153dfd94904c28169ab13f66516ad87d6e2341b93e89d51f6eb91efd4`.
Its fixture hash is
`c230ebb07206f60b02ef6d622e369a184c6d8338943dad33a206edafc43cb59f`.

The independent [build replay](../verification/android-pointer-fixture-review/build-review-3/receipt.json)
rechecked the accepted predecessor and candidate recursive seals, all frozen
inputs and archived artifacts, then recompiled the four private Java class files
and complete DEX byte for byte. The 155 production class files, 18 native
libraries, installed appearance descriptor and Android manifest are identical to
the accepted predecessor. The only changed source inputs are the two private
harness files and operations asset. DEX additions remain within those two
harness families, including D8's generated Instrumentation members.

Independent ZIP local-header/central-directory comparison, CRC validation,
stored `resources.arsc` with 4-byte alignment, and all 18 stored arm64 libraries
with 16 KiB ZIP alignment and compatible ELF LOAD alignment passed. Official
zipalign and apksigner replay passed for the exact extracted APK. The signer is
the candidate's disposable private debug certificate; this is no signed OTA
authority. The review's extraction and recompilation scratch was removed after
an empty holder check. The initial review-tool failure about D8 anonymous-class
naming is retained in
[build-review-1](../verification/android-pointer-fixture-review/build-review-1/reviewer-failure.json),
with its original script, partial receipt, and cleanup evidence.
The passed candidate-3 interim replay remains separately retained in
`build-review-2`; candidate-4 adds only the agreed across-refresh identity check
and independently exported pre-/post-retirement packet evidence.

The final producer packet's original 507 bindings were checked twice and remain
unchanged. Its root seal is
`317de5fb8a7e8ac7249bbb0fc49a17ba2f38a048ab6edfc1b27e24abc5ae6b52`,
packet hash
`34e5c0108d65ee714a02891370d58ad2e6790fad4afd5d2793cb2eff6cab9d37`,
and concrete runner hash
`30386d63319168afb0a6e3b1ea05b991a5a5a965087efda27d1bc25e5ef74ca9`.
The runner preserves the accepted exact owned PID/process-group/AVD/tool and
Wi-Fi flag checks, serial-only targeting, source and packaging checks before
dispatch and installation, installed APK hash check, bounded logs, private
exports, new process-group cleanup and inode/membership/holder-checked extraction
cleanup. The preinstall source and signature rechecks are present. No native
command was executed by this review.

The independent [host replay](../verification/android-pointer-fixture-review/host-review-1/receipt.json)
ran all 22 producer host tests successfully, then ran seven finite synthetic
controls against the unchanged oracle. Synthetic data supplies parser evidence
only. Duplicate acknowledgement and changed saved-retirement-packet controls
were rejected. The following five inconsistent observations were accepted:

| Finding | Accepted inconsistent observation | Binding requirement and repair |
| --- | --- | --- |
| F01 | Actual Activity entry/exit events marked `flags=1` (obscured). | Reject obscured/clipped/unfocused/out-of-window input. Reject obscured and partially obscured flags; also validate action index. |
| F02 | Actual MOVE pointer pressure changed to zero. | One touchscreen pointer uses pressure 1 until release. Compare observed pressure with each sealed action. |
| F03 | MOVE history at unplanned time `down+17`, local coordinates `(999999,-999999)`. | Preserve and validate actual historical MOVE samples against the immutable path/timing. Map historical local coordinates through the observed raw/local offset and require strictly ordered sealed MOVE times/coordinates. |
| F04 | All eight P03 Activity MOVE entries/exits removed, with no history, leaving only DOWN/UP while worker sends remain. | Different delivered-event counts are allowed for batching, but some actual MOVE sample must establish the final MOVE endpoint before the terminal hold. Require that endpoint in an event or history without equating requested and delivered event counts. |
| F05 | A worker send finishes `999999 ms` after its start while the receipt still claims a passing action. | The action including hold/settle is bounded to 5 seconds. A fresh harness must export action start/end/duration, and the oracle must bound worker and Activity timestamps within that interval. |

The [machine-readable findings](../verification/android-pointer-fixture-review/findings.json)
bind the tested source and outcomes. Root selected a fresh candidate-5 harness
for action-interval evidence plus a bounded oracle repair, including a valid
coalesced positive control. That repair is outside this immutable review. The
original producer packet and all review failures remain retained.

The frozen harness calls `Instrumentation.sendPointerSync` from the worker.
Its Activity records observations around exactly one superclass dispatch,
preserving the result and exception. It changes no product listeners, touch
handling, widget checked/text state, authored appearance or shared geometry.
Each action exports its complete immutable geometry, thresholds and timed
sequence before DOWN. The selected successful run requests 124 events over
20 actions; cleanup CANCEL is separate and cannot qualify a failed action.
All supplied budgets fail by throwing, rather than truncating a pass.

The source distinguishes actual Activity delivery from authoritative UInt64
revision acknowledgements and leaves `directNativeCallbackCount` null. It checks
native checked values against packet values, exact no-commit packet identity,
record/view/generation identity, editor buffer/Editable/selection/composition
identity, closed/current/retired gates and contained failures. Scroll setup uses
36 logged ordinary reducer dispatches and requires 20 tasks with actual overflow;
these setup commits supply no pointer-delivery evidence. Real Activity delivery,
native widget gesture semantics and the observed environment tuple still need
the coordinator's explicitly dispatched runtime receipt.

Physical phones, real system IME, accessibility, broader native lifecycle/fault
coverage, iOS/Android design parity, public V2 integration, signed OTA authority,
immutable published FieldLog packages from a separate repository, stores,
customers, operations and accountable GA acceptance remain pending.
