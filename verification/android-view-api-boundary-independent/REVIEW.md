# Independent Android view API boundary review

**Accepted for source and focused test design only.** No open finding remains in
the selected API29/30 derivative after one narrow authority-order correction.
No Java compiler, JVM, product/test main, Node oracle, SDK/D8, native runtime,
UI/capture or phone test was executed by this review.

The reviewed producer freeze is
`c458497920a6cf454433f2f96bbcdf42fbf8b6945e55e5a76c813dddb00af8ff`;
its 115-member manifest is
`e52dd5bd9c415a68c843724a24fec03c72c64dbce7fae2d18377c646a4b35834`.
Independent checks match every member and total. The exact derivative product
tree is `d767f19554c88bd24f58663de268d7a80119522380cfeb4043c37d35b432a21e`
using the accepted compact source-identity-map JSON algorithm. The separately
named basename/NUL/hash/LF source projection is
`8bc11ed739833031a5fe87d71ea0872aee771354341dec834f747948933c1239`.

## Source correctness

The accepted editor16 input matches all sixteen hashes in the named current
source observation and its recorded product tree `a5e4888b...`. Exactly
`NativeAppearanceViewsV2.java` and `NativeRenderer.java` differ. The fourteen other
files, 86 designated mechanical host leaves and 9,587-byte descriptor match their
accepted bytes.

| Contract | Review result |
| --- | --- |
| Real API selection | View callers use actual `Build.VERSION.SDK_INT >=29` and `>=30`; no supplied SDK/configuration/support observation selects the helpers. |
| API29 field calls | `Api29.authoredSelection` retains cursor, center handle, left handle, right handle order, distinct drawable instances bound to the same Record, and the original Mutation postcheck immediately after every setter. |
| API30 value calls | V2 `Api30.stateDescription` retains the native call and immediate original-Mutation postcheck. The unsupported branch still performs the original no-call authority check. Renderer `Api30` isolates V1's existing call. |
| Refusal before effects | Direct constructor and bind validate original Mutation first, run the pure capability check second, then construct widgets or change scoped/editor/binding/native state. Renderer checks all resolved plan/node requirements before constructing any shadow Record. |
| Value distinctions | Present `accessibilityValue`, including `""`, refuses below30. Omission below30 remains no-op. On30+, absence supplies actual null for clearing and empty supplies actual `""`. Source decoding still rejects null scalar input. |
| Stale/reentry/throws | Helpers receive the original Mutation directly; no authority is reacquired. No catch/throw translation was added. The existing bind `finally` still restores changing/scoped values. |
| V1 and admission | V1 property-presence refusal and supported results retain their source behavior. The observer file and renderer `<36` guard are exact. Full renderer preparation remains denied below36. |
| Commit boundary | Coordinator bytes and renderer `finishV2` are exact. No new call moves into commitV2 through finishV2. |

The review caught the initial placement of capability checks before
`mutation.requireMutation()`. With stale or cleanup authority plus unsupported
API requirements, that changed the original refusal priority. The producer moved
the pure capability check after the original authority guard and added focused
entry tests. The initial source finding is retained under ignored `local/`; the
corrected bytes above are the accepted source. This was a source finding, not an
executed runtime failure.

## Focused test design

The single prepared actual-source main has thirteen groups. It uses the exact
sixteen product sources and mechanical Android/JNI leaves, with actual
OwnerLifecycleV2-issued operation tokens. It does not start NativeOwner, register
observers, drain product startup queues, use a renderer substitute, or invoke the
old matrix/launcher.

The assertions cover API28 field/selectable and API28/29 required-value refusal
before constructor/bind effects; explicit empty and absence; API29 four-setter
order; API30/36/37 set, null-clear, empty, receiver and drawable ownership/instance
identity. The finite loops prepare 152 interruptions at every applicable setter,
with ordinary/fatal throw identity, stale Mutation and stale nested bind reentry,
at entry and after native effects before return. They check no later setter,
no Mutation reacquisition, and scope/changing restoration. Twenty constructor/bind
calls cover stale/cleanup entry priority on API28/29/30/36/37. Separate tests cover
both lower-API guards and five V1 widget/container shapes.

These are reviewed assertions, not passing executable tests. Java syntax,
assertion behavior and host fixture behavior remain unvalidated until a separately
selected hosted run. The source-only inspection ran 36 data/source checks and
eleven in-memory corruption controls; all passed. Controls reject missing
postchecks, changed setter order, an outer API30 reference, removed presence
predicates and the original authority-order defect. They do not prove Java
semantics, emitted code or release safety.

## Exact remaining boundary

All three new nested helpers need fresh emitted-class/constant-pool/instruction
inspection and exact tool/source identities, followed by pinned official SDK37
compilation and D8 min-api28 evidence under separate root-selected bounded hosted
admission. No runtime dispatch is authorized here. Changed bytecode needs a new
exact source-pair reconciliation; old compiler/receiver/descriptor/BCI receipts
cannot authorize it.

Canonical pair.5 remains 22 SDK/23 adapter members with SDK `bc032885...`; held
editor pair.5 is 22/24 with older SDK `4c2e74bb...`. This derivative is neither
pair. A shared ID or lock-only refresh cannot select it. The historical 189 V2
dispositions/280-subject matrix and held v5 launcher remain incomplete; no
equivalent startup experiment was run or delegated, and cleanup remains
unverified. Existing custody, native, Unit A and broad hosted holds persist.

No lower-API full-renderer support, public V2, canonical promotion, OTA/release,
published package, native parity or GA acceptance is granted by this review.
VM integration at 5b6fc4f5 remains outside this lane.
