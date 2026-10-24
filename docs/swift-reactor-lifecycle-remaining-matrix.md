The private lifecycle verification candidate retains the accepted V3 production
engine bytes and expands the host synthetic lifecycle suite from 23 to 49 test
identities. All 49 passed in Swift-only and all-features Debug and Release:
196 exact identity executions, zero failed and zero ignored. The four final
executables, exact binary lists, source manifests, commands, tool versions and
stdout/stderr are retained under
`verification/swift-reactor-lifecycle-remaining-matrix/`.

The accepted 132-file baseline closure remains
`93adb6ac2d00acab30c02df8d96e044452edc14d704a6738a58874b0968b5f38`.
The isolated normal candidate closure is
`64a3d9c52ade75ec16de10191f14257fb75ff358c366666cf47809e2b9a7f0de`.
Only three test files differ: `lifecycle_tests.rs`, `cache_tests.rs` and
`memory_growth_operations_tests.rs`. The latter two provide setup for existing
unit-only checkpoint/refund hooks; formatting is normalized. Every other file
is byte-identical. `test-only.patch` records the complete delta. There is no
production engine change or new accounting credit.

The added cases exercise foreign original owners/tickets, refused preparation
with an actual unfinished frame bound, real frame/control/pin publication
barriers, committed memory with an old-ticket refund rejection, indirect traps,
cache/pin/nested resource limits, growth overlap, cooperative interruption,
cumulative later-call budgets, retained output/closed descriptors, invalid
results, allocation refusals and consuming cleanup. Independent expected traces
include instructions 7/15/23, host and WASI calls 1/2/3, and output x/xx/xxx.
The all-34 descriptor case actually executes each sealed descriptor with typed
zero arguments and checks its expected errno or GuestExit; separate granted
random/realtime/monotonic cases call actual OS services. These selected cases
do not exhaust each descriptor's range, partial-effect or grant matrix.

Six separate compiler-negative fixtures produced their required exact source
and diagnostic: external construction/request/pin access E0603, nonexistent
arbitrary invocation E0425, and whole-owner mutation during an actual phase or
retained completion E0506. The two borrow fixtures are injected only into a
separate compiler-negative source copy. Normal test sources contain no invented
Cargo features or new cfg-lint suppression. Final rustfmt checks passed for all
three changed test files and both borrow fixtures.

`coverage-ledger.json` is the per-row covered/remaining record. Every SL01–SL23
row remains **partial**; no original full row is newly claimed complete. SL12
guest table mutation remains unsupported, unimplemented and unrun; preserved
table reads do not establish mutation. SL24/full 53 MB reactor execution was
not selected. Fresh complete MIR/layout accounting, broader full-library,
Frozen/default/span/Node regressions and production Clippy remain for root
selection. Existing 1,602 executions/four checks and live 23-test/Clippy evidence
are bound through accepted receipts and are not recounted here.

Raw failed attempts remain in `commands/`, with matching historical source
snapshots and explanations in `failure-history.json`. They record a test import
path error, an allocation fixture that did not reach ordinal 1, an incorrect
256-byte growth chunk expectation (actual execution chunk is 4096), an incorrect
adapter-versus-runtime cancellation expectation, and an extern metadata filename
setup error. Each was corrected using the actual source contract; none received
pass credit. Historical failed executables were rebuilt before archive capture;
their exact sources and raw outputs remain, and all four final executables are
archived.

One owned build target was reused. Every recorded compiler/test command had a
180-second ceiling, with 158.139 aggregate recorded command seconds against the
30-minute cap. Before removing 134,966,066 logical bytes from that target, its
final binaries/metadata were archived and an empty live-holder check was saved.
No native instance, phone, emulator, network shell, signing/release, customer,
shared tracker or Git operation was performed by this lane. Root owns acceptance,
integration, commits and pushes. Host synthetic evidence grants no native,
published FieldLog or GA qualification.

Read-only packet verification:

```sh
python3 -B verification/swift-reactor-lifecycle-remaining-matrix/verify.py
```
