# Selected constructor authority correction

The original frozen composition exposes two selected constructors accepting raw
cache/control/WASI/adopted parts. Independent compiler witnesses successfully
called each route without the owning selected scope. This packet corrects that
source boundary in an isolated 144-file candidate.

`SnapshotScopeV1::construct_v1` alone constructs `SnapshotScopeBorrowV1` from its
actual owner slots. Private fields and the absence of a public constructor or
Clone/Copy implementation prevent sibling callers from forging or duplicating
it. Both the outer cache wrapper and inner selected constructor consume this
capability. Its consuming accessor returns the same exclusive cache/control
borrows, optional WASI borrow and adopted owner. No independent permit can be
combined with replacement parts. The borrows end before the original scope moves
into its run result.

Only three files change. The original ABI, original eight result variants,
encoder, writer body and fail-closed `WorkAuditPending` admission remain intact.
`source-delta.patch` contains every change; `source-seal.json` freezes source and
compiler support separately from the later completed command evidence.

Fourteen compiler commands pass on rustc 1.99.0, aarch64-apple-darwin:

- Production and unit positive metadata checks in Debug and optimized modes.
- Both exact original bypass witnesses fail with E0061 in each mode.
- Private-field fabrication fails with E0451, repeated consumption with E0382,
  and escaping the actual owner's borrows with three E0515 errors in each mode.
- Two compiler layout probes measure the capability and its real parts-return
  tuple at 1,240 bytes each, alignment 8. The measurement is appended only to
  owned compiler probe copies, absent from the corrected candidate itself.

The command receipts contain exact 144-source preimages, eleven immutable encoder
support bindings, compiler/version hashes, freshly derived build identity
environment, argv, output and cleanup. Every compiler child was reaped and its
owned group absent; disposable compiler sources/artifacts were removed. There
were no timeouts or unexpected failures. No engine, writer, native test, UI or
process inventory ran.

These checks establish a bounded compiler authority correction. They do not
establish a complete storage floor, logical-work debit or actual writer behavior.
The token literal/local and each forwarded parameter/move, consuming accessor
receiver, real tuple return, caller tuple/pattern and remaining core arguments
must replace the former raw-argument occurrences in the final accounting recipe.
The two measured type sizes alone are not additional storage charges. Independent
review and exact source occurrence/work attribution are recorded separately.
Common adapter funding, selected early admission, full encoder/caller closure,
conservative retained cleanup charges and genuine writer execution remain pending.
