# Independent authority-constructor work delta review

The proposed **19 added source actions per consuming construction** are
corroborated under the existing logical-action convention. No missing or doubled
category was found in this bounded delta. Scope bookkeeping16 becomes21;
forwarding5 becomes19; combined21 becomes40. This conclusion does not select
funding, accept a complete work/storage floor or measure runtime cost.

Producer9 seal
`625ca2e549dbf32545722b44d2fc8af5715f70cf31a623f6cd432590d96e626d`
and root release
`c9910093451dda292364135ab06987fca3dcb4af4ef3927fa763f67f34b3bea5`
match. All producer9, accepted authority225, prior authority review77, original
writer14 and corrected writer9 members were rehashed. Authority source144 tree
`575b55d3391729749039dc2badccc9107449cb2c9a021d8ef67282c39b2e1896`
is bound, and only control.rs, cache.rs and initial_profile_v1.rs differ from the
original composer manifest. The exact four function bodies were independently
extracted and matched byte-for-byte against the proposal. The prior compiler
authority acceptance is input evidence; no compiler or runtime was rerun here.

## Source-action reconciliation

The manual review reads the actual four corrected functions, their original
wrappers, the bound cost convention and the prior `source-role-delta.md`.
Named scalar/reference fetches, aggregate slots, explicit bindings and function
entry/return are charged. Bound local operands remain free; owned forwarding is
not an aggregate deep copy. Those rules also produced the old16 and5 rows.

| Source change or relocated occurrence | Added work |
| --- | ---: |
| Scope's token literal: four aggregate field stores | 4 |
| Explicit `owners` local binding | 1 |
| New `into_parts` entry/return | 2 |
| Helper's four explicit field-pattern bindings | 4 |
| Helper's four-field tuple output | 4 |
| Inner caller's four tuple-pattern bindings | 4 |
| Total | **19** |

The existing cache/control/WASI reference expressions retain their five actions
and are charged once at the token literal. They replace the old raw argument
expressions. The adopted owner is moved into the literal as its fourth field;
it is not copied or re-adopted. The two original forwarding entry/return pairs
remain4, and the private branch output slot remains1. The scope's adopted-take,
outer binding and Run literal are unchanged. These two old rows also remain
unchanged in the separately corrected writer ledger, so that correction and
this authority delta do not overlap.

The token's call arguments, parameters, consuming receiver and self operand are
owned or bound local forwarding under this convention. Adding extra raw-owner
argument costs at those occurrences would count the old path a second time.
The tuple return's four output stores and the caller's four explicit pattern
bindings are both charged; there is no additional named temporary tuple local
in the actual caller. Function return is already in entry/return2. Distinct
callee/caller storage roles still require storage-lifetime reconciliation; their
existence does not automatically add payload-copy work. The existing optional
WASI borrow is preserved; no Option/Result containing the token or token array
is created. No additional stop, encoder or native call occurs.

The token is minted once in a consuming scope call and consumed through the
outer wrapper and `into_parts` once. Each successful invocation needs the delta;
multiple different scopes need19 times their actual consuming-construction
count. It is not one global allowance for an arbitrary sequence of calls.

## Placement and remaining limits

All19 new actions occur before the unchanged original core constructor. The
core can return an early primary outcome before `branch.begin`, and its snapshot
planning debit occurs only inside that begin. Therefore the delta needs explicit
pre-admitted funding on **all** consuming-construction routes, including early
returns. Adding it only to begin's candidate shell2871 or a later planning debit
would leave those early routes unfunded. It belongs neither to encoder F14224
nor writer blocks/attempts. Formula-evaluation work, actual caller counts and
checked consuming arithmetic remain requirements for a future integrated recipe.

The original core, guard, writer, encoder, admission, original budgets and cleanup
retain their inherited attribution. Their costs were not re-reviewed here.
WorkAuditPending remains; storage occurrences, finalizer/F1 lifetime closure,
full work selection and actual writer testing remain pending. This delta review
is separate from the original495 writer correction review and does not rewrite
either frozen packet or claim authority acceptance beyond its existing receipt.

`review.py` adds40 source/custody/accounting controls, including six missing-category
and four extra-category rejection cases, original/corrected writer row agreement,
exact function binding and predebit call ordering. These tests corroborate the
manually inspected finite accounting model. They are not observed engine event
counts, CPU/latency measurements or proof of runtime costs. The producer's15
assertions remain attributed prior evidence. Its initial authoring SyntaxError
is preserved under its seal; compiling that text without executing it reproduced
the expected unmatched-parenthesis error at line55. No new review failure occurred.

Run
`python3 verification/swift-guarded-snapshot-writer-work-independent/authority-delta-review/review.py --verify`.
Generation writes only this review folder and verification compares deterministic
outputs. Commands, Python version, input bindings, checks and seal are retained.
No product/producer script, engine, VM, writer, Rust compiler, native/device/
simulator/emulator runtime, UI/capture, global process inventory, forbidden hosted
harness or stopped Android experiment was executed. No Git, commit, push,
operational work selection, production publication, OTA release, FieldLog,
store/customer qualification or GA verification occurred.
