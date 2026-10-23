# Independent final execution-cleanup accounting review

Decision: **blocked by missing disjoint named-object accounting**, at frozen control
`55e0e89c5da57347f02fd13dfb97296c19c3ace7d94fc11109dd224c9046b79f`
and executor `33f4ae0f00f20c24656a3456e5203a980e456acbb22a72214b74e82eb423f81e`.
This reviewer accepts no new allowance. Root owns any foundation correction,
source change, addendum and subsequent acceptance. This is only a private
compiling type/lifetime/layout prerequisite; there is no executor algorithm or
full-target instantiation/execution in this review.

`decision.json` binds source, every chosen inventory field, type, measured size,
alignment, offset and source role. `input-manifest.json` freezes 120 input files
at base `0f177adf10af78a8442e2dd4c66679fe54b20113`, with source-tree digest
`44081606beaae9380427732b139c0a295067e5811c842876f1b61f6b3ade9e2d`.
`derived-manifest.json` identifies the isolated probe tree. `commands.json` and
`logs/` record exact tool commands and outputs. The Debug and Release shape probes
both executed one test; the separate candidate const-formula probes also
executed one test per profile; all nine group layouts and 122 field rows match. Tool:
Rust 1.99.0, commit b940084d7, host aarch64-apple-darwin.

## Exact boundary and the missing values

`ExecutionCleanupTail::complete` calls `drop_cleanup_return_storage(self,storage)`.
Inside that helper, the original tail is destructured and `(storage,failure)`
actually drops. The helper returns `HeaderCompletionParts`. Its return expression
is destructured at the caller's statement ending on execution.rs:173. Thus the
large generic storage, tail failure, tail wrapper and whole returned parts have
ended before header refund. The original control, `header: Option<Ticket>`, one
`final_wasi: Option<WasiUsage>`, and the two output references survive.
The control is the original owner, not an embedded-parent borrow or replacement.

The two references on execution.rs:166-167 are real distinct eight-byte Rust
values. They survive successful header refund, record_cleanup and control
consumption. They have no explicit slot in the frozen foundation. Their pointed
to failure/usage storage is a different accounting question: those existing
outer optional shapes may occupy the foundation's actual diagnostic classes;
the reference values may not be relabeled as a failure class, placed in padding,
or hidden in a now-refunded execution header.

The remainder is not just those 16 bytes. `drop_reserved_with_wasi` forwards to
`refund_with_wasi`. The latter retains named category/combined/count checked
Options and creates a tuple match plus successful usize bindings. Shared and
mutable category helpers have authored receivers, enum parameters and returned
borrows. The underflow fault retains the refund parent while
`cleanup_fault_with_wasi -> fail -> usage -> micros` runs. This chain includes
invariant/code arguments, get_or_insert receiver/argument/result, actual Cursor
and Fault source/transfer roles, receiver borrows, Instant/Duration values,
u128 conversion input and Result<u64,TryFromIntError> operand/return shapes.
These are directly written source operations. Opaque library implementation
frames are not expanded.

`record_cleanup` is a later statement. Its own mutable receiver, direct
`&mut self.first_failure` expression, matched `&mut SwiftRunFailure`, clock
chain and copied returned Option failure need distinct accounting. The direct
expression here is `&mut Option<SwiftRunFailure>`; this source does not create an
`Option<&mut SwiftRunFailure>` wrapper.

`finish_owned_cleanup` consumes control only after record_cleanup returns. It
creates named `started`, `deadline`, `observation`, whole ticket array,
IntoIter and Flatten shapes, loop-next Option ticket and its matched ticket,
three checked Options, tuple match, three usize bindings, category helper roles,
construction-byte comparison Options, cleanup-invariant insertion roles, and
post-drop `now`/micros values. The complete array/iterator wrapper shapes are
measured, not approximated as a number of plain tickets. Their contained fields
are not also counted in plain-ticket classes in this proposed supplement.
The final `drop(self)` precedes final observation timing and return, as in the
frozen source; this review does not change that semantic order.

There is an additional self-referential accounting hazard in the current code:
`foundation_construction_bytes()` creates a seven-pair array, an IntoIter and
try_fold closure bindings at runtime, including during finish's Construction
comparison. These direct source objects measure 344 bytes as a complete
conservative group. Adding an eighth row would change that array/iterator's
shape. The new row cannot fund preflight of its own creation by implication.

## Source groups and safe phase partition

The following are explicit complete conservative parent inventories. They
include every source role in their child groups and retain parent values while
nested helpers run. Some source roles are sequential transfers/alternatives;
the numbers are conservative reservations, not a claim that every field is
physically live on one stack at once. There is no member switching to hide a
surviving parent frame. In particular the fault branch includes the refund
Options/tuple while the fault/usage chain runs.

| Group | Size / alignment | Scope |
| --- | ---: | --- |
| FinalOutputBorrows | 16 / 8 | Two surviving complete output references |
| ClockLeaf | 224 / 16 | Usage/micros direct operation and return roles |
| FaultLeaf | 264 / 8 | Cleanup fault and fail parameters/borrows/source transfers |
| CategoryLeaves | 40 / 8 | Both category helper operation shapes |
| RefundParent | 688 / 16 | Output refs, header take, drop/refund parent and complete nested fault/clock |
| RecordParent | 272 / 16 | Output refs, record parent and complete clock chain |
| FoundationFormulaRuntime | 344 / 8 | Current seven-row runtime formula only |
| FinishParent | 1216 / 16 | Complete current finish parent, wrappers, clock and runtime formula |
| FinishConstFormulaParent | 864 / 16 | Same finish parent if formula is explicitly constant evaluated |

Refund may use its full group until `let _ = ...;` ends. The if body and its
Result end before `record_cleanup` starts. Record may use its full group until
its return and the output assignment end. Only then may finish use its full
group. Output references persist across all three and are included in each.
A max of these **whole** groups therefore has a safe selected phase partition;
no per-field or last-use switching within a helper is needed. The previous cache
Control2/Control3 alternatives are not used by this proposal. No proof/adopted
slot, owner padding, remainder, or byte capacity inside another class is used.

## Existing foundation classes and transfer boundary

The frozen existing classes remain separate and unchanged in this proposal.
The counted output *objects* must be the sole surviving caller failure/usage
objects; any additional caller-held copies must already have been consumed in T
or have their own still-live envelope. These are requirements on the future
caller map, not behavior proved by this non-runnable prerequisite.

- Four failure-sized classes cover the output Option failure, a fail local or
  copy of the control-held cause, and sequential failure/Result return/output
  transfers. Each outer Option/Result shape is 1096 bytes. The control-owned
  first failure is contained in the charged control owner and is not a spare
  class. Uninitialized ABI return locations or compiler-generated spill slots
  are not added to this authored named-object model.
- Four usage-sized classes cover the output Option usage, usage local/return,
  record local/after_cleanup assignment, and final observation/Option return
  transfers in their sequential windows. Outer Option usage is 504 bytes.
  Embedded usage fields in a whole charged failure/control remain inside it.
- Six 24-byte ticket classes cover plain/optional header and explicit ticket
  extraction/argument/return transfers. In finish the array, IntoIter, Flatten
  and loop-next Option are whole separate supplement rows; their fields are
  not claimed again as plain tickets. Control-owned ticket fields remain in
  the control owner until their actual take.
- Six 112-byte Option<WasiUsage> classes suffice for the one retained
  `complete.final_wasi` plus parameters to drop_reserved, refund, cleanup_fault,
  fail and usage on a rejected refund. Success has three shapes. Later
  record_cleanup and initial finish usage each have three shapes. Post-drop
  micros creates no additional observation parameter. No copied optional/raw
  WASI payload beyond these is admitted after final header.
- The three control transfer classes cover the original control's successive
  wrapper/helper/local/consuming transfers. The final helper ends before refund;
  later by-value finish/drop transfers do not overlap the former large-owner
  transfer phases. These control classes are not repurposed for small borrows.

A strict compiler-stack or opaque standard-library-internal model would be a
different accounting system. The frozen contract expressly excludes it. This
review uses actual Rust type metadata for authored wrapper objects, while
excluding recursive accounting of opaque Flatten/try_fold/Option internals,
compiler temporaries and allocator/RSS effects.

## Minimal recommended root-owned correction

Use explicit const evaluation for the pure foundation size sum, as already
required for pure cache layout sums. This removes the runtime formula inventory
without changing its existing seven terms. Separately add a named disjoint
final-boundary allowance based on complete `RefundParent`, `RecordParent` and
`FinishConstFormulaParent` source/field groups. On this host the conservative
whole-group maximum is **864 bytes**, making a candidate foundation
`16,504 + 864 = 17,368` bytes. This is a concrete sufficient candidate for the
listed source-role inventory, not a claim of mathematically minimum bytes or
root acceptance. Different targets must compile all actual shapes and choose
their own maximum. The probes themselves grant no product reservation.

Root should freeze any chosen production spelling and new source before accepting
this correction. Do not merely add 16 bytes or the producer's starter 256/288-byte
supplement totals: neither accounts the complete control chain. Do not append an
ordinary runtime eighth-row formula while retaining this const-formula map.
An alternate helper design can change the inventory, but removing output refs
alone leaves refund/record/finish/clock values and iterator wrappers to account.

The candidate correction changes the upfront requested Construction bound. Any
budget-admission expectations and composed cache/header/construction sums that
include foundation must be remeasured and rebound to the new control source.
Existing C3 cache acceptance and unchanged historical C2 phase alternatives stay
historical exact-source receipts; neither can silently certify a changed
foundation or new executor caller allowance. A new append-only root addendum can
explain the invariant owner layouts/semantics and the explicit admission change.

Proposed executable checks for the root correction:

1. Compile exact production and cfg(test) size/alignment/offsets in Debug and
   Release; assert every new whole group fits the selected new allowance and
   that the size formula is explicitly constant evaluated. Keep each original
   stored owner layout and each old foundation class count unchanged.
2. Run actual final-helper success and foreign-header/underflow failure cases,
   preserving a real AccountedWasi observation and zero allocations. Verify
   drops precede refunds, successful valid cleanup leaves zero current/tickets,
   and rejection retains the entire unrefundable header charge.
3. Exercise existing first failure plus later cleanup invariant: preserve exact
   first cause/at_failure and update only independent cleanup/after_cleanup.
   Exercise no-header completion and finish's malformed construction, owner and
   underflow branches without manufacturing a false zero observation.
4. Rebind exact budget-boundary and Combined peak expectations to the new
   foundation, including construction failure before permanent header admission;
   rerun the cache/observed-control/frozen legacy matrices required by root.
   Retain original receipts rather than rewriting them.

These probes do not run any owner algorithm, allocator/service, interpreter,
full Swift target or device, and close no physical, signing, publication,
FieldLog, store, operational, performance or GA gate.

The patch-ready candidate is `foundation-proposal.rs`. It compiles in the
isolated tree without replacing the original foundation function; independent
Debug/Release tests assert the original 16504 and proposed 17368 values, and
the complete-group maximum 864. It is deliberately named
`proposed_foundation_construction_bytes` so root can adapt the original private
function in its own lane. Reproduce the metadata/candidate checks with
`build_probe.py`, `make_proposal.py`, `collect.py`, then `finalize.py`; these
operate only in this review directory. They do not accept a production delta.
