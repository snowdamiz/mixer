# Private host account and one-fixture entry source

This packet implements a private local host-account primitive and an enforcing
typed caller in `host_account.rs` and `entry.inc.rs`. It is source preparation,
not a completed grant. Both selected policy functions return a named pending
error. `run_one_fixture_v1` obtains the selected whole quote and atomically
reserves it before its consuming callback can open any fixture File, call the
loader, produce arguments, or call the real loaded-carrier leaf. There is no
production quote, root policy, fixture-binding constructor, environment budget,
public scalar permit, ordinary-proof adapter, CLI route or retry path.

The private account uses a `Cell<UsageV1>`; it cannot be shared across threads.
Checked work and storage additions and both limit comparisons precede one
state commit. Refusal changes no work, storage or peak amount. The reservation
is non-Clone and consumed by `FnOnce` dispatch. Work is never refunded. No
selected account can currently be constructed: root must first select and
independently review the fixed host policy, its P0 allocation and all complete
quote components. Test-only small synthetic limits are not production prices.

`PrepaidOwnedV1` keeps the entire real typed outcome, original loader files,
usage, I/O/validation failures, output files, claims and cancellation owner.
Only borrowed inspection is exposed; no mutable/owned extraction or transfer
exists. Ordinary Drop destroys owners without refunding storage. Explicit
`destroy_owned_v1` destroys the payload and wrapper in an inner frame and then
returns an opaque `DestroyedStorageV1` into P0. A later P0 call consumes that
token to release storage. Its actual borrowed account selects the release
target; another account cannot be supplied. The token and all destroy/release
arguments, return slots, moves and temporaries belong to the pre-existing P0
allocation. Moving retention into this token does not fund those places.
Destructor or dispatch unwind, an unused ticket, discarded completion token,
or an implicit owner Drop conservatively retain the storage charge. File Drop
is not a successful close, flush or durable-output receipt.

The actual typed route opens each of five reviewed paths at most once. Inputs
are read-only and outputs use `create_new`, preserving existing output files.
Every setup error returns the original I/O error and all earlier File owners.
The exact loader receives its independent original validator budget and
returns its authentic `SelectedValidatedProfileV1`; the wrapper passes that
type into the frozen seven-argument leaf. Loader refusal retains its actual
error and all File owners. The leaf's real finish/pre-scope alternatives are
kept inside the retained outcome. Product 1,000,000,000 work / 268,435,456 byte
limits are unchanged and independently enforced by the frozen product source.
No host credit is transferred into those counters.

`source-manifest.json` binds the exact 145-member compile-only tree: frozen
funding144 plus the released bootstrap leaf, the appended caller, and the new
private account include. **This is not the concurrently reviewed combined
source145** and contains none of its newer descriptor/composition changes.
The accepted work/common correction is an input custody binding, not a claim
that its fixed 451,814,442 store exists in this measurement tree. The leaf's
30 roles / 95,850 bytes and seven parameters / 1,344 bytes remain separately
bound to their frozen packet. Final composition must rebind every count,
layout, privacy/borrow/consume contract, fixed-store cut and source identity.

Current compiler measurements cover 19 newly authored functions and 396 MIR
places totaling 311,071 logical source-object bytes. Ninety diagnostic queries
measure 89 distinct non-unit types; the actual compiler reports the dispatch
closure's size as eight bytes. No place receives a guessed size. Generic
account places are instantiated only with the actual typed production
`OwnedFixtureOutcomeV1`; fake test owners do not replace it. This conservative
sum includes overlaps, parameters, returns, failures, moves and temporaries.
It is not a stack, RSS, allocator, CPU or complete operational storage bound.
`phase-inventory.json` assigns the new source places to P0..P5 and records
finite MIR block/call inventories. These counts are measurements, not logical
work prices or evidence authorizing OTA release.

Eleven standalone account tests pass in each of debug and optimized builds.
They cover pending policy/quote, six mandatory checked components, both
limits, addition/quote overflow, atomic refusal, exact-limit precharge, one
dispatch, no work refund, retained refusal/output/diagnostic owner drop order,
multiple live results, actual account identity, callback/destructor unwind,
unused tickets and implicit Drop. Three compile failures enforce consumed
ticket reuse, borrowed-result escape and cross-thread sharing. These tests use
only fake owners/callbacks and never load a genuine fixture. Earlier outputs
and an inventory-tool parser error are retained under `attempts/`; a later
closure-filter assertion failed before starting a compiler and is documented
in `attempts/tool-failure.json`. The current source tests and compiler/layout
measurements pass after those bounded repairs. Final producer self-audit also
corrected the parameter parser for the nested parentheses in `impl FnOnce()`:
two parameter places (24 bytes) were recovered from the existing compiler MIR
and already measured layouts, without another compiler run. The superseded
394-place claim is preserved under `attempts/02-parameter-parser-repair/`.
Compiler type-layout stdout is
preserved losslessly as gzip with original hashes in command receipts.

The complete quote remains unavailable. Required inputs include the exact
selected fixture/build/session/executable/process geometry and source/tool
binding; unchanged real-loader logical work and original validation work;
all P1 setup and dynamic backing; P2 argument/backing; P3 complete pre-store
and failure work; P4 final composed callee/leaf ownership and requested storage;
and P5 retained diagnostics, outputs and destruction. P0 policy construction,
checked-quote building, account bookkeeping, closure, caller/retirement/token
places, release and every late/error path require an independently provisioned
finite parent allocation and source-work quote before account construction.
No child grant can supply that authority. Six child component slots have no
default zero price; the currently selected quote returns `WholeQuotePending`.
The exact trusted outer-parent invocation/binding, complete P0/child prices,
whole-quote review and final composed source remain required before a grant
or genuine loaded-carrier entry may succeed.

Only owned scratch and directly owned compiler/test executables were removed.
No canonical/root/sibling files or Git state were changed. No process inventory,
native runtime, simulator, emulator, device, UI, capture, real loader/guest/VM/
cache/scope/writer runtime, network publication, customer operation, FieldLog
qualification or GA gate was run or accepted.
