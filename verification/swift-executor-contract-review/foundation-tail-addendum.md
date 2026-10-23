# Superseding global foundation observation-tail review

This addendum supersedes the **sufficient foundation allowance** proposed in
`review.md`. That earlier three-option finding remains correct as a minimum for
the successful AccountedWasi final-header refund; it is not a sufficient global
bound. No earlier receipt or review bytes were changed. Root owns any source,
test or contract amendment and must obtain new revision-bound verification.

**Global bounded proposal: six Option<WasiUsage> shapes**, not three. Five
simultaneously active observed-control parameters plus one retained caller
observation are covered without last-use/compiler-elision assumptions or a
component header's spare allowance. On the independently measured host this is
`6*112=672` bytes, replacing `2*104=208`: **+464 bytes**, changing the upfront
foundation from **16,040 to 16,504**. No new ticket, heap allocation, refund,
admission, counter or cleanup behavior is needed.

The exhaustive control-family map is in `observation-chain-map.json`, bound to
the frozen committed control source. The maximum chains are:

1. `instruction_with_wasi -> charge_fuel_with_wasi -> check_with_wasi -> fail -> usage`.
2. `admit_cache_entry_with_wasi -> admit_with_wasi -> check_with_wasi -> fail -> usage`.
3. `admit_cache_entry_with_wasi -> admit_with_wasi -> preflight_bytes -> fail -> usage`.
4. `drop_reserved_with_wasi -> refund_with_wasi -> cleanup_fault_with_wasi -> fail -> usage`.
5. `drop_proof_with_wasi -> refund_with_wasi -> cleanup_fault_with_wasi -> fail -> usage`.

Each listed function has its **own** Option<WasiUsage> parameter. For example,
standalone `drop_proof_with_wasi` can encounter its first source/metadata refund
invariant without any AccountedWasi or cache header. The foundation itself must
therefore cover that five-parameter fault path; a rejected component-header
envelope cannot be its justification. One additional retained raw/optional
caller observation fits the sixth optional shape. More caller copies must be
named by the caller's still-live component/operation/construction envelope.

The component-specific distinctions remain:

| Window | Standalone optional observations | Accounting authority |
| --- | ---: | --- |
| Cache successful last header refund | 2 | foundation |
| Cache `record_cleanup -> usage` after that refund returned | 2 | foundation |
| AccountedWasi successful last header refund | 3: cleanup local plus two parameters | foundation |
| Cache rejected refund/fault chain | 5 | foundation now suffices; rejected cache header also retains its own envelope, without double-spending it |
| AccountedWasi rejected refund/fault chain | 6: cleanup local plus five parameters | foundation now suffices; rejected WASI header also retains its own envelope |
| Composed final header successful refund or finish -> usage | one retained final observation plus two parameters, at most 3 | foundation; no additional component envelope may be assumed after its refund |
| Composed final header failed refund -> fail -> usage | one retained final observation plus five parameters, at most 6 | foundation; original header charge is conservatively retained on rejection |

An external copied final WASI observation/outcome held while components drain
is disjoint from their own arguments. Its containing execution permanent header
normally still exists and covers that caller value until component cleanup
completes. At the last execution-header refund, the retained observation must
instead be the single caller shape explicitly assigned above; all other copied
observations and large owner/Result/Option/tail storage must already be dropped
or separately covered by an upfront named allowance. The proposed executor has
no implementation, so this final composed map remains an implementation blocker.

## Failure, usage and ticket classes

The existing **four failure / four usage / six ticket** conclusions are scoped
to named transfer phases. They are not a claim of spare payload bytes inside
`RuntimeControl`, `SwiftRunFailure` or `SwiftRunUsage`, or a compiler stack bound.
Independent Debug/Release measurements show outer Option/Result failure shapes
are 1,096 bytes, outer optional usage is 504, and optional ticket is 24, equal to
their respective named plain classes. Only whole same-sized outer shapes are
mapped to those classes; no embedded WASI field is reused as a standalone slot.

- Successful cache refund: caller outcome plus the observed refund Result and
  return/output transfers are within four failure-sized slots. The refund call
  and its Result end before later record_cleanup. The control-owned first fault
  is charged separately inside the live control header.
- WASI cleanup: accumulated Result, released Result and the two by-value
  Result::and operand/return-transfer positions occupy up to four failure-sized
  shapes. These are phase alternatives to the cache's output/refund positions,
  not simultaneous claims on the same four slots. Standard-library/compiler
  internal stack slots are outside this named Rust-object model.
- A standalone observed proof-drop path retains its first refund Result while
  the second refund runs; active failure plus wrapper/return transfer positions
  remain within four. The first cause stored in control is not a spare slot.
- `usage` return/local, first-fault usage transfer, record_cleanup local and
  after-cleanup assignment/return transfers use at most four usage-sized slots
  within their respective phases. Nested usages within a charged whole failure
  remain part of that failure, never an extra free standalone allowance.
- Header Option extraction, one owned ticket and the successive drop/refund
  transfer positions fit six ticket-sized slots. Ordinary phases and large
  possible-owner outputs have ended before final header refund.

This conclusion depends on completing components sequentially and dropping their
return storage before the next named phase. Additional caller-held failure/usage
copies, nested component outcomes, borrow/scalar wrappers or simultaneous phases
must be named in their own upfront envelope. The pending executor map must prove
these conditions with actual chosen types, field offsets and live counts before
acceptance. It cannot use a sum of byte totals or assume another live phase's
capacity is available.

Root should refine control, relevant tests and append-only contract/acceptance
addenda consistently to six optional observations. Frozen source and measured
shapes are retained in this review's archives/logs. Acceptance of that actual
delta requires its separate frozen source receipt; this addendum authorizes no
engine implementation, target run, devices or GA gate change.
