# Private Android owner roster amendment 1

This additive amendment resolves only R1 in
[the final correction review](android-private-owner-effect-contract-correction-review.md).
It narrows the domain of the universal V2 barrier wording in
[correction 1](android-private-owner-effect-integration-correction.md); it does not
edit or replace any sealed predecessor file. It is a source contract awaiting
independent review and root selection, not implementation or test acceptance.

The prior 189-entry inventory remains immutable historical evidence. The
[amended mandatory roster](../verification/android-private-owner-effect-roster-amendment/required-host-roster.json)
contains all **184 V2 semantic barriers explicitly**, with their exact existing
IDs, source/line/column/expression anchors and seven required future cases.
The [184-ID list](../verification/android-private-owner-effect-roster-amendment/v2-semantic-barrier-ids.txt)
provides a compact comparison. Only these five entries change classification:

| Exact historical ID | Expression | Effective class |
| --- | --- | --- |
| `NativeRenderer:L60:C234:1` | `parent.removeViewAt(` | V1 compile/baseline-only |
| `NativeRenderer:L61:C242:1` | `parent.addView(` | V1 compile/baseline-only |
| `NativeRenderer:L62:C149:1` | `view.setLayoutParams(` | V1 compile/baseline-only |
| `NativeRenderer:L62:C454:2` | `lp.setMarginEnd(` | V1 compile/baseline-only |
| `NativeRenderer:L62:C509:3` | `view.setLayoutParams(` | V1 compile/baseline-only |

These calls belong to legacy `children(...)`, reached by V1 `apply(...)`.
The V2 section starts at line 65 and uses its concrete native-view helpers.
Their original source bytes and all five anchors remain retained; the prior
inventory and per-record digests preserve their historical requirements as
evidence, rather than active V2 obligations.

In correction 1, “every selected barrier,” its universal terminal/dirty/fault
case matrix, actual V2 gate observations and operation/live-presentation guard
requirements now mean **every entry in the amended 184-entry V2 array**.
They do not apply to the five V1 entries. Future newly introduced calls in those
selected V2 regions remain mandatory additional V2 barriers. This amendment
introduces no discretionary omission from that matrix.

The five V1 entries require complete-source compilation and a separately labeled
positive unchanged-V1 baseline through actual `apply`/`children` code. They have
no V2 terminal/dirty reentry, operation-token, presentation-token, shared-fence or
current/pending-V2-gate requirement. No V1 behavior change or V2 bypass is selected.
Positive V1 host baseline evidence uses its declared controlled Android leaves;
it is distinct from V2 behavioral evidence and actual Android framework evidence.
Pinned-SDK compilation remains additional signature evidence. This amendment ran
none of those product checks.

Closure B retains the same 14 actual production subjects and 73 substitutes.
Every other prior roster field and every remaining V2 record is unchanged.
All C1 cancellation/consumption/exhaustion/cleanup, C2 typed terminal/cause/fatal
reporting, focus/lifecycle mapping, transaction versus live-callback authority,
commit/finish, exact-packet refresh, public V1 and profile boundaries remain
mandatory exactly as frozen. No public/private signature changes are introduced.

The [classification proof](../verification/android-private-owner-effect-roster-amendment/classification-proof.json)
compares every remaining V2 record in full, all five source anchors and all
non-inventory predecessor fields. The [receipt](../verification/android-private-owner-effect-roster-amendment/receipt.json)
binds the original proposal, original review, admitted plan, correction 1 and final
review seals. Its bounded checks verify custody and roster classification only;
they are not product tests or an independent correctness judgment.

All predecessor members, exact memberships and verifier bytes are preserved.
This packet is outside their sealed directories. There were no product/native
tests, source/profile/CI/root-metadata changes, commit/push, hosted harness access,
network/install, process discovery, signing/credentials/publication or UI/capture
actions. Implementation, host closures, cross-compilation, native/device and final
product acceptance remain pending under the existing restrictions.
