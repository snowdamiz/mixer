> Historical producer proposal. Root and independent review rejected the two-copy
> last-use interpretation below as insufficiently conservative. The superseding
> root decision is six Option<WasiUsage> shapes (672 bytes here), replacing two
> raw WasiUsage shapes (208 bytes): upfront delta +464, foundation16504. Root owns
> the explicit addendum and source-bound prerequisite qualification. This file
> preserves the original concern/proposal; it does not define the accepted model.

# Measured observation-transfer gap (pending root decision)

This is an implementation accounting proposal, not a changed foundation or
contract. Final cache-tail qualification is paused. On aarch64-apple-darwin,
Rust 1.99.0, Debug: WasiUsage = 104/align8; Option<WasiUsage> = 112/align8.
SwiftRunFailure, Option<SwiftRunFailure>, Result<(),SwiftRunFailure> =1096/align8;
SwiftRunUsage=504/align8; ReservationTicket and Option<ReservationTicket>=24/align8.
The frozen standalone observation allowance 2*104=208 cannot cover the chosen
conservative two-transfer Option allowance 2*112=224. Do not use the extra 16
bytes from a different named allowance. This applies to the existing accounted
WASI final refund path as well as the new cache path.

Proposed bounded amendment: preserve the existing two-observation simultaneous
count, but bind its object shape to Option<WasiUsage> rather than WasiUsage.
The foundation upfront sum grows by 16 bytes on this target. No new ticket,
category, heap allocation, cleanup admission, or changed control behavior is
needed. Require independently reviewed layouts in Debug/Release and all root
source bindings before acceptance. Other targets must measure their own layout.

## Cache completion live-set map

The model describes named Rust values and last-use transfers, not compiler
stack slots, LLVM copies, allocator overhead, or RSS. Every by-value forwarding
edge is conservatively counted as two shapes (source and destination). A source
whose last use forwards the value is no longer an independently live observation
in subsequent nested calls. Returned SwiftRunUsage/SwiftRunFailure already
contain their nested Option<WasiUsage>; counting it again as a standalone Option
would count those bytes twice.

1. Caller drops the large cleanup Result/branch scope. `CacheCleanupTail` owns
   the same header ticket. Caller passes the empty Option<SwiftFunctionCache>
   and any remaining return storage into complete. These large shapes and all
   tail moves remain under the permanent header cleanup envelope.
2. `complete` destructures the tail, discarding its failure field, and drops
   actual supplied storage before refund. Only control/WASI borrows, header
   Option/ticket, caller output Option<SwiftRunFailure>, and unit storage remain.
   No standalone WasiUsage or Option<WasiUsage> has been retained.
3. `wasi.map(AccountedWasi::usage)` evaluates an actual borrowed context usage,
   then moves it into one Option<WasiUsage> argument. Count the 104-byte source
   payload and 112-byte Option destination as at most two 112-byte shapes.
   There is no local copied observation retained for the next call.
4. `drop_reserved_with_wasi((), ticket, observation)` drops unit storage, then
   directly returns `refund_with_wasi(ticket, observation)`. The observation
   source is last-used on this forwarding edge. Count source/destination two
   Options; no third independently live observation is used afterward.
5. Successful refund returns unit without calling fail/usage. On a refund fault,
   `refund_with_wasi` directly returns `cleanup_fault_with_wasi(..., observation)`;
   that helper forwards its last-used observation to `fail`; `fail` last-uses
   the observation in `self.usage(observation)`. Each nested edge reuses the same
   two-transfer standalone allowance; these are not simultaneous retained locals.
   `SwiftRunUsage` returned by usage and embedded in the new SwiftRunFailure is
   under the separately named usage/failure shapes, including its observation.
6. The discarded refund Result<(),SwiftRunFailure> ends before the final
   `record_cleanup(wasi.map(AccountedWasi::usage))` call. Therefore their returned
   failure and observation transfers do not overlap with that later call.
7. `record_cleanup` last-uses its Option observation in usage; its copied
   SwiftRunUsage is assigned to the control's already owned failure. Its copied
   Option<SwiftRunFailure> return is assigned to the caller-owned outcome slot.
   Completion returns unit. No large cache/Result/tail storage survives refund.

## Other frozen foundation shapes at completion

- Four SwiftRunFailure shapes cover caller output Option, refund Result failure,
  fail's returned/copied failure, and the return/output transfer. These phases
  overlap conservatively within four; the failure stored inside RuntimeControl
  belongs to its separately named control object. Option and Result failure
  shapes have exactly the same observed size/alignment as SwiftRunFailure.
- Four SwiftRunUsage shapes cover `usage` return/local, fail's at_failure transfer,
  record_cleanup's local, and its after_cleanup assignment transfer. Nested
  usages already inside a SwiftRunFailure/control are counted by that owner.
- Six ReservationTicket shapes cover header Option extraction and transfer
  across complete -> drop_reserved -> refund, with source/destination transfer
  shapes. Option and ticket have exactly the same measured size/alignment.
- Two proposed Option<WasiUsage> shapes cover the observation edges above. The
  old two plain WasiUsage shapes are insufficient by16 bytes, so this proposal
  expressly requires a reviewed upfront change.

## Existing AccountedWasi final-header refund

`AccountedWasi::cleanup` owns one local Option<WasiUsage>, one accumulated
Result<(),SwiftRunFailure>, and one `released` Result. Buffer storage is dropped
before each respective ticket refund. For the final header call, that local
observation's last use forwards it to `drop_reserved_with_wasi(self,ticket,wasi)`.
The AccountedWasi owner is actually dropped before its header refund. Subsequent
`result.and(released)` only transfers failure/Result values and does not use the
local observation again. Thus the same two-Option forwarding map applies; its
six Option<WasiUsage> permanent header envelope remains charged until actual
owner drop, while the post-drop forwarding/failure tail needs the amended
foundation observation shape. Earlier buffer-refund calls retain the local
observation for later iterations, but the still-live accounted header envelope
already reserves six Option<WasiUsage> copies for those active states.

The producer has not changed control.rs, accounted.rs, or the frozen v2 contract.
Root owns the decision and any additive prerequisite delta. Independent review
must challenge both the chosen last-use map and the amended target layouts.
