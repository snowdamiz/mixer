# Experimental native capability boundary

The nondefault `experimental-capability-native` feature adds15 C functions and
the separate `mixer_vm_capability.h`. It depends on the reviewed Rust guest
experiment. Legacy ABI1/profile1–3/header definitions remain unchanged. Default
and guest-only builds expose the same12 old C functions; native/all-feature
builds expose those plus15 new functions. This is an experimental native boundary,
not an activation/release profile, Swift bridge, JSON/grant validator or I/O engine.

The [final receipt](2026-10-23-final/receipt.json) pins90 implementation/contract
inputs with source manifest SHA
`76372fd254e646141e991b3289b14c8380f13ea68602b21d4aa746080fddc8cf`.
Inputs include root's shared registry and mixed-pool test, the private guest hooks,
root's pure ranges, every new C/Rust source, old contracts/headers and capability
semantic hashes. Source hashes matched before/after each command. SDK/native
implementation identity, Swift codec/bridge, CI and activation/release files are
excluded; no inference about them follows from this receipt. Implementation model
selection is `gpt-6.1-sol` with `xhigh`; independent review is recorded separately.

| Check | Debug | Release |
| --- | ---: | ---: |
| Default test functions |91 passed,8 explicitly ignored|91 passed,8 explicitly ignored|
| All-feature test functions |185 passed,9 explicitly ignored|185 passed,9 explicitly ignored|
| Explicit oracle functions |9 passed|9 passed|
| Explicit old session lifetime regression |1 passed|1 passed|
| Explicit mixed registry/destructor test |1 passed|1 passed|
| Explicit public native boundary functions |4 passed|4 passed|
| Explicit native allocation function |1 passed|1 passed|

Explicit targeted runs repeat functions already included in the all-feature count;
they are not additional distinct tests. Native module tests include17 functions:
four root range tests, four layout/preflight functions and nine ledger/quarantine
functions. Native public and allocation files add five, and root's mixed registry
test adds one, for23 functions beyond the previous162 all-feature total. The
range test performs346112 symmetric decisions. Default/all-target and
all-feature/all-target Clippy with warnings denied, cargo fmt and fixed terminal
regeneration parity pass. Node remains a development-only oracle.

The14 actual host C runs comprise four old clients for default, five for native,
and five for all features. The original new public C client passes27 status/alias
checks per native/all run and compiles assertions for every new size, alignment
and field offset. Rust has independent host tests and compile-time assertions
for every admitted cross target. Real C-facing functions execute handcrafted
Wasm: startup/effects ordering, native dispatch, opaque post, poll/read, duplicate
and stale exits, memory bounds, operation mismatch, unaligned input/output
structures, and rejection with unchanged aliased sentinel storage. The shared
pool test retains closed work and a blocked final destructor against the same
sixteen-slot ceiling as legacy sessions. The old allocator-gated lifetime
regression still passes.

The fixed eight-entry ledger owns actual Rust tickets while C holds numeric
tuples. Only Call creates an exit obligation; None/too-small/Cancel do not.
First successful exit ack decrements once; repeated ack consults the mailbox and
is successful kind2 only while identity remains retained. Acknowledged old
entries may be replaced only by a newer mailbox generation. Native methods use
ledger-before-mailbox order, and root's registry never acquires either lock.
Transient lease release synchronizes under the registry before reclamation;
the final destructor runs outside it in `Reclaiming`. Local unfinished take
transactions and actual unwind/poison/invariants latch monotonic quarantine.
Ordinary stale/malformed/busy errors do not quarantine. Cleanup close/cancel can
return0 for an unpoisoned quarantined owner, while quarantine stays sticky,
ack access returns4 and capacity remains pinned. That success is not reclamation.

Allocator observations agree between debug/release on this host:

| Interval | Requested allocations / bytes |
| --- | ---: |
| Validate-only a module declaring32 initial pages |60 calls,0 retained,3109 logical peak,368 largest|
| Create the same module |128 calls,2101738 retained/logical peak,2097152 largest|
| Refused1024-byte post allocation |1 failed call,0 retained/peak; status2|
| Retry that same post |1 call,1024 retained/peak; status0|
| Alias preflight refusal and close/last-exit ack interval |0 new allocations|

Validate-only shares the constructor's full module/import/body/startup/wake
checks, without allocating instance memory or a mailbox owner. Create reserves
shared capacity before parsing and performs bounded validation followed by the
existing constructor (a second decode); no privileged Module escapes. Post
allocation refusal preserves the request for retry/deadline without inventing
terminal state or exit. Measurements are GlobalAlloc requested Layout sizes,
not usable size, physical heap/RSS or allocator-internal realloc overlap. Source
and caller buffers are outside these intervals. Core/error Strings/Arcs and
standard mutex first-lock OOM abort boundaries remain; previous negative child
transcripts are retained in the all-feature suite. No end-to-end OOM guarantee.

Official iOS arm64 and Android arm64 builds pass Rust compile-time layout checks,
compile the actual C client and link it against the matching native archive.
The receipt pins objects, archives and executable hashes. macOS x86_64 C layout
compilation also passes. Only host clients ran: cross objects/executables were
never executed, installed or signed on a phone. Unsupported native pointer/arch
layouts reject numeric preflight. Phones remain disconnected.

The [supplemental archive provenance](2026-10-23-final/review-archive-provenance.json)
captures logged native-only debug/release builds and V3 archive copies for the
independent reviewer. Release is
`db04bf0baa4a844f12facbda682a557fef4e467e8a2f213c8341e00f60ac9f58`,
matching the primary receipt's native release. Debug is
`66519ab92e7779121a450914698f9fe1f00760bbcbcafdee3c29975d8302e640`.
The earlier V2 debug archive had a different hash after a later mixed-feature
rebuild with the same90 inputs. The failed equality check, original build log and
[explicit note](2026-10-23-final/archive-provenance-initial-check.txt) are preserved;
cause was not investigated and no bit-reproducibility claim is made. Historical
default/guest/all host output files in the shared build tree can be overwritten
by later feature builds; their captured hashes/client outputs remain evidence,
not a claim that every old binary is still at its former path. V3 copied archives
and cross-target artifacts have separately pinned paths/hashes.

The [first qualification attempt](2026-10-23-host/receipt.json) stopped at a
default-only Clippy diagnostic in root's registry match. Root changed only that
cfg-specific source form, preserving native behavior; final freeze includes the
correction. The failure log and its earlier source pin are retained.

Reproduce on the recorded host/toolchains with a fresh directory name:

```sh
python3 -B vm/verification/capability-native/verify.py --name host-replay
```

The driver prepends the configured rustup path and uses an isolated target tree.
Supplemental `pin-review-archives.py --name 2026-10-23-final` binds retained V3
copies to logged native-only builds; it is not a general deterministic-build
assertion. Full commands, versions, development elapsed times, environment
overrides and output hashes are in the receipt. No new dependency is introduced.

Dynamic arguments/completions remain trusted opaque bytes at this C layer;
strict Swift payload/operation/grant binding and actual HTTP/storage are later
work. The caller must ack actual native exit and coordinate registration versus
its activation-close latch; equal raw bits in two valid session contexts cannot
reveal caller intent. Poison/quarantine can permanently consume capacity. Swift
async/scheduling/lifecycle, device execution, full Swift/FieldLog owned-VM
admission, immutable consumer packages, release/store/operations and GA gates
remain open.
