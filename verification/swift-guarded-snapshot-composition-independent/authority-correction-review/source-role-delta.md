# Authority correction: exact role and work delta

Source seal: `a51d5791cad11e6fb3a587d11b7c225216c11b75ccd89768a691c477a7f51b4c`.
144-source tree: `575b55d3391729749039dc2badccc9107449cb2c9a021d8ef67282c39b2e1896`.
Only control.rs, cache.rs and initial_profile_v1.rs change from the prior candidate.

The source-level authority correction closes C1. Both formerly callable raw-parts
Selected boundaries now require a consuming `SnapshotScopeBorrowV1`. Its only
literal is inside consuming `SnapshotScopeV1::construct_v1`, after taking that
scope's actual adopted owner. Its private fields hold the actual scope cache and
control exclusive borrows, that scope's optional WASI shared borrow, and the
actual adopted owner. This is an owning capability carrying the parts themselves.
There is no detached permit, Clone/Copy implementation, alternate parts constructor
or output lifetime that can escape the scope. `into_parts(self)` moves exactly
those fields into one tuple with their original common lifetime.

The outer wrapper consumes and forwards the token. The inner wrapper consumes
it, obtains the tuple and calls the existing private closed constructor. The
sole Selected branch literal remains private to that inner module. Both exact
former raw-parts witnesses fail E0061 in Debug and optimized compilation. The
authentic carrier-to-scope-to-Run route compiles. Private mint, repeated consume,
scope escape, scope movement while borrowed and foreign-control replacement all
fail with their intended privacy/lifetime diagnostic. These are compiler facts;
no writer or VM executed.

## Occurrence recipe to reconcile before choosing any floor

The following are actual new/replaced source roles, not a sum and not guessed
arrays. Each listed token role has the same concrete token type. Each tuple role
has the concrete return type below. Fresh metadata const checks establish equal
size/alignment of token and tuple; they select no byte amount or storage floor.

`(&mut Option<SwiftFunctionCache>, &mut RuntimeControl, Option<&AccountedWasi>, AdoptedProof)`

| Qualified source role | New occurrence / reconciliation |
| --- | --- |
| `SnapshotScopeV1::construct_v1::owners.literal` | One token aggregate literal containing the four actual parts. Its three reference expressions replace the previous raw call-argument expressions; the adopted move becomes its fourth field. Do not retain both old and replacement field expression rows. |
| `SnapshotScopeV1::construct_v1::owners.binding` | One local token binding. Record its end at the consuming outer call. |
| `SnapshotScopeV1::construct_v1::outer-call.arg.owners` | One consuming token argument/move replaces four raw owner argument roles; claims/rows/output roles are unchanged. |
| `cache::construct_snapshot_in_scope_v1::arg.owners` | One actual token parameter replaces cache/control/WASI/adopted parameters. |
| `cache::construct_snapshot_in_scope_v1::inner-call.arg.owners` | One forwarding token argument/move replaces the four raw owner argument expressions. |
| `initial_profile_v1::construct_snapshot_owned_v1::arg.owners` | One actual token parameter replaces the four raw owner parameters. |
| `initial_profile_v1::construct_snapshot_owned_v1::parts-call.receiver` | One consuming token receiver expression at the new `into_parts` call. |
| `SnapshotScopeBorrowV1::into_parts::arg.self` | One token self parameter. |
| `SnapshotScopeBorrowV1::into_parts::pattern.{cache,control,wasi,adopted}` | Four actual field bindings, with their actual separate reference/Option/adopted types. These bind the same authentic owners, not new authorities. |
| `SnapshotScopeBorrowV1::into_parts::return-expression` | One tuple expression containing those four fields. Callee return storage and individual field move roles must use the chosen source-role convention explicitly. |
| `initial_profile_v1::construct_snapshot_owned_v1::parts-call.result` | One caller-held tuple call result; it is distinct from the callee return-expression role. |
| `initial_profile_v1::construct_snapshot_owned_v1::parts-pattern.{cache,control,wasi,adopted}` | Four caller pattern bindings, with their actual individual types. Map the old raw-parameter logical roles to these relocated bindings before adding new occurrence storage. |
| inner `construct_profile_core_v1` call arguments/result | Actual raw core arguments and owned `SnapshotOuterV1` result are unchanged. Preserve their existing rows; do not add a second full core/outer envelope. |
| scope `SnapshotRunV1` literal/return/caller | Unchanged. The token's borrows end before the scope moves into Run, as verified by the authentic positive and targeted move-negative controls. |

No function returns a token Result or Option, and the source contains no token
array. Do not invent those types as automatic allowances. The token does not
mint a control, ticket, cancellation backing or independently spendable ledger.
The prior scope/outer/finish types, guard, encoder, writer and old original ABI
are unchanged. The existing common and selected aggregate formulas are also
unchanged; this correction does not claim they now fund these roles.

## Unpriced work delta

The exact code adds one token aggregate initialization and local binding, routes
one token through each of the two formerly raw-parts call boundaries, and adds
one `into_parts` call. That helper has one consuming self parameter, four field
pattern bindings and one four-field tuple return expression. The inner caller
has the tuple call result and four pattern bindings. The previous three borrow
expressions and adopted move are relocated to the mint; existing core call,
outer result and Run return operations remain unchanged.

These are named source occurrences, not an ExecutionWork debit. Price reads,
moves, aggregate construction, helper entry/return and pattern operations using
the same source-action unit as the whole caller audit, replacing the old raw
forwarding/parameter rows rather than charging both paths. Owner routing runs
before the current phase planning debit, so its placement and predebit coverage
must be explicit. It is outside the encoder-only fixed initialization 14224 and
outside encoder callee/helper storage. No new encoder, native IO or stop-check
call is introduced by this correction. WorkAuditPending remains byte-identical
and prevents this exact candidate from admitting the writer.

Independent acceptance is limited to the authority correction. Exact common,
selected and conditional funding, the surviving finalizer diagnostics, full
caller work and the bounded-call stop amendment remain separate prerequisites.
