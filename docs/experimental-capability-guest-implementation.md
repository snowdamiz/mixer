# Experimental Rust guest capability composition

Status: bounded Rust-only implementation direction approved by root on 2026-10-23, after the design summary. Implementation is under `vm/src/experimental_capability_guest` and the nondefault Cargo feature below; [host evidence](../vm/verification/capability-guest/README.md) records actual results separately from this contract. Selection: `gpt-6.1-sol`, `xhigh`. Root owns integration/push and the later C/registry layer. No device commands are permitted while phones remain disconnected.

Baseline: reviewed mailbox `4e37b357ae029d9cdf5e5c6b4281d82f61b65f3a`. Payload/import contract: `3ba601332dab7c2aba98d7a50d7f0e893b1ea776`, [guest-capability-transport-v1.json](../contracts/guest-capability-transport-v1.json), file SHA-256 `052ebe9fbdc20a41307332086767e7903680bc83ba273c696edf9187be6b6439`. The broader [ABI proposal](guest-capability-abi-proposal.md) remains the product direction; this slice is smaller and supplies no new public profile/guest ABI/C/activation/identity/release admission.

## Explicit selection and proposed Rust API

Add nondefault Cargo feature `experimental-capability-guest`, depending on `experimental-capability-mailbox`. Keep `Profile`, `Limits`, `Module`/`Instance` field layouts, old headers/C/session entry points and all current ceilings unchanged. Require `Limits.profile == TableMemoryV3` only as the inherited numeric/table instruction grammar, not as permission to admit capability imports into profile3. The new constructor is the explicit experiment selector:

```rust
// Rust-only experiment; these types are unavailable without the feature.
pub struct GuestLimits { pub turn_milliseconds: u32 } // 1..=50, default50
pub struct CapabilityGuest { /* private Instance, startup/wake indices, owner */ }
pub struct CapabilityPort { /* private shared mailbox owner */ }
pub struct DispatchLease { /* private owner + opaque NativeLease; not Clone */ }

impl CapabilityGuest {
    pub fn new(wasm: &[u8], vm: crate::Limits,
        mailbox: experimental_capability::Limits, guest: GuestLimits,
        installed_startup_export: &str) -> Result<Self, crate::Error>;
    pub fn native_port(&self) -> CapabilityPort;
    pub fn cancellation(&self) -> crate::Cancellation;
    pub fn startup(&mut self) -> Result<Option<crate::Value>, crate::Error>;
    pub fn enable_effects(&mut self) -> Result<(), crate::Error>;
    pub fn invoke(&mut self, export: &str, args: &[crate::Value])
        -> Result<Option<crate::Value>, crate::Error>;
    pub fn wake_once(&mut self) -> Result<bool, crate::Error>;
    pub fn close(&mut self) -> Result<experimental_capability::CloseReport, crate::Error>;
    pub fn memory(&self) -> &[u8]; // read-only borrow, no exposed Instance/Module
    pub fn fuel_remaining(&self) -> u64;
    pub fn host_calls_used(&self) -> u64;
}
```

`CapabilityPort` is Clone and is the narrow trusted native half: bounded caller-buffer `take` returns no message/required capacity/call with `DispatchLease`/cancel identity; `post_trusted(&DispatchLease, &[u8])`, `ack_exit(&DispatchLease)`, `limit_deadline`, `expire`, `usage` and `close` preserve the reviewed mailbox rules. A ticket also provides `ack_exit()`, so an actual native exit can be acknowledged even after every guest/port is dropped. Errors retain opaque lease identity for retry. No port method accepts a guest-selected mailbox/session or calls guest code. `post_trusted` deliberately names its trust requirement: bytes remain opaque in Rust; the later strict native codec must bind result schema/operation/grants before posting or I/O. This slice runs no native I/O.

Introduce a private `ImportAdmission::{Legacy, ExperimentalCapabilityV1}` for full parse/type validation and private instance construction. Public `Module::decode`, `Instance::new`, CLI/inventory/C/session and experimental streaming routes always select Legacy, even with the Cargo feature enabled. Only the bytes-based wrapper constructor selects the experimental context and keeps its decoded Module/Instance private; there is no conversion, deref, module getter or public constructor accepting a predecoded privileged module. `Instance::new` must revalidate Legacy and reject such a module even if a private test obtains one. Merely recognizing import names during inventory never authorizes execution.

The experimental allowlist adds exactly `mixer.capability.v1` signatures: four enqueue functions `(i32,i32,i32)->i32`, cancel `(i64)->i32`, poll `(i64,i32,i32,i32)->i32`; the exact original two mixer imports remain. Unknown module/name/signature and every body/cross-reference still fail full validation. One defined nonshared memory0 is mandatory. Start sections stay unsupported. Require the native-selected startup export to be a defined no-argument function (existing single numeric/void result retained); require exactly named defined `mixer_guest_capability_ready_v1 ()->()` for wake. Reject missing, wrong-kind, imported or wrong-signature wake/startup entries before instantiation.

## Engine hooks and turn lifecycle

Keep existing public method signatures. Extract a private invocation context for Legacy or this wrapper's one mailbox/TurnId/turn deadline. It supplies no user function pointer, closure, native pointer or plugin lookup. The import engine returns `Result<Option<Value>, Error>` internally: direct Call and CallIndirect push the declared i32 status onto their caller stack; an exported-import entry returns it directly. Both legacy imports still return None, preserving their observable behavior/errors/fuel. Structural indirect signature matching and all existing stack/depth/host-call/fuel checks remain. Tests must cover all three call shapes, including exported capability imports; the designated startup and wake themselves remain defined functions.

Construction performs validation/initialization only; no startup executes implicitly. `startup()` executes just the selected entry once with effects disabled. Other turns and enable-before-success reject; successful startup permits one-way `enable_effects`, with idempotent repeated enable. Startup-disabled enqueues still own tokens and immutable unavailable completions; enabling never makes those calls drainable.

Every actual entry begins one owner-bound turn. On complete interpreter success, recheck cancellation/deadline and finish that exact turn successfully before returning. Only then may native take drain queued calls. Any interpreter trap, fuel/host-call/depth failure, cooperative cancellation/turn timeout or internal mailbox failure terminates the wrapper and closes all mailbox ownership. No later guest invocation/wake/enable can reopen it. Queued calls from that turn never dispatch. Prior native leases retain their separate acknowledgement obligation and can still ack after close through the native owner/ticket. A later trap cannot undo earlier native effects.

A panic/unwind guard closes on an unfinished turn without changing the original panic or panicking during cleanup; errors during best-effort close are suppressed in Drop. Rust unwinding is not advertised as general OOM containment. Poison/allocation/identifier-exhaustion are explicit interpreter traps, not invented guest transport codes; they also permanently stop guest admission. A poisoned lock can prevent normal mailbox cleanup/ack, retaining bounded state instead of claiming successful reclamation; no recovery/reopen or poison-clearing authority is introduced. This case needs an explicit negative test and remains a native registry follow-on concern.

Coalesced readiness is derived under the existing mailbox lock from its bounded authoritative slots: no active turn and some ready, unconsumed terminal. No additional readiness bit or expanding queue is introduced. `wake_once` checks that predicate, calls the prevalidated wake entry at most once and returns; unconsumed terminal work leaves the next explicit wake eligible. No reentrant invoke or internal spin loop. Every turn checks private `Instant` time and cancellation at instruction/import boundaries with existing fuel/host-call limits. The caller must serialize `&mut CapabilityGuest`. The cloneable existing `Cancellation` permits another thread to cancel a running turn; once observed, this terminates the wrapper permanently and is distinct from per-request guest cancel. Dropping `CapabilityGuest` best-effort closes the mailbox, cancels execution and refuses future native take, while previously retained normal tickets remain ackable. This is not an automatic executor: four-turn/8ms scheduler yielding, native rate limits and Swift continuation scheduling remain later work.

## Guest memory transactions and fuel

Interpret i32 offsets/lengths as unsigned bit patterns, then checked native ranges. Reject out-of-bounds/wrapping ranges, invalid lengths/capacities and overlap before any memory/request mutation. Enqueue args1..524288 and token8-byte range must not overlap; poll capacity0..524288 and length4-byte range must not overlap. Empty output range is genuinely empty, even if its address lies within the length-word range; capacity0 still requires offset<=memory length. Alignment is unrestricted; token/length words use explicit little-endian byte writes. Hold exclusive guest memory access only for this import; retain no slice/address through growth or native work.

Do not compose existing public `Mailbox::enqueue/poll` followed by fallible memory writes: enqueue would publish too early, and typed Failure poll consumes before wire encoding. Add feature-private guest transaction helpers under the mailbox lock. They use only internal bounded fuel accounting, never user callbacks:

| Transition | Before allocation/copy/commit | Commit, with no later fallible step |
| --- | --- | --- |
| Enqueue | Validate ranges, live exact turn, slot/reservation; charge `ceil((args_len+8)/64)` extra fuel; fallibly snapshot args | Install complete request/reservation and write token8, return0 |
| Poll pending | Validate both full output ranges and raw token; charge `ceil(4/64)` | Write length0, return1 |
| Poll small buffer | Determine exact payload length, including fixed terminal JSON; charge `ceil(4/64)` | Write required length only, retain result, return2 |
| Poll ready | Check complete destination, obtain immutable payload; charge `ceil((payload_len+4)/64)` | Copy whole payload, write length, consume/release delivery once, return0 |
| Cancel | Check this mailbox's live token/terminal; no guest-memory copy | First terminal wins; preserve native lease and queue bounded cancel control |

Each attempted import also uses one host-call and its ordinary dispatch fuel, including stale/invalid/pending retries. Rejections3/4/5/6/7 leave both guest outputs unchanged and issue no request/generation. Insufficient byte fuel traps before copy/consumption; allocation failure can follow a charged reservation but publishes nothing and traps. No refund/rollback is promised after a trap. Clock expiry may independently install its first terminal during a mailbox operation; it never permits partial guest writes. Compute sums/ceilings with checked arithmetic; no second staging payload buffer is needed.

Raw i64 token lookup is private to the wrapper's one mailbox owner, uses all64 bits, verifies nonzero high generation and low slot+1, and rejects consumed/retired/stale entries. There is no global lookup by bits or guest session ID. Equal raw bits can legitimately exist in two sessions; a call affects only its current owner, while a foreign native ticket always rejects. Slot reuse still waits for delivery consumption plus actual exit acknowledgement (or proof it never dispatched), retiring at UInt32.max.

## Fixed terminals and truthful ownership

An original offline development generator reads the frozen transport contract and capabilities/schema/hashes.json, verifies their exact fixed operation/hash table, and produces twelve static sorted-key ASCII JSON payloads: four operations times unavailable/cancelled/deadlineExceeded. No runtime format/string allocation, copied native exception text, arbitrary hash field, build.rs side effect or generic operation selector is involved. Regeneration/diff and independent decode parity are verifier commands. Exact capability hashes remain HTTP `fa1549c0a1e2e6b3bf4a83af1a6d37730bbefc8cddc3ffbe3c807d5e7af503f3` and storage `4a311222c978ddd0982e8dfbcf3d4864b856a80bcc1efb3b725adede7f8e22fd`. Fixed output has only abi/capability/operation/outcome/schemaHash; no request identity appears in JSON. Dynamic trusted completions and rejected-invalidArguments encoding remain the strict bridge/codec owner's responsibility.

The wrapper and native port share one private Arc owner; each dispatched native ticket retains that owner while held. Close/trap keeps the mailbox reachable through those owners for later acknowledgement, and dropping a ticket never asserts exit. Trusted native code must retain its owner/ticket until actual I/O cleanup; dropping every owner early does not prove retention. There is no counted registry or shared sixteen-session cap in this Rust-only slice; root's later native registry design must account closed/native-draining sessions through actual destructor completion. Per-mailbox 8-request/8MiB reservation/524288-byte payload bounds stay unchanged.

Existing decoded Module, execution frames/stacks/globals, error Strings, Cancellation Arc and new shared-owner Arc may allocate infallibly; initial memory/table and mailbox payload snapshots have their existing fallible boundaries. The standard mutex's first lock already has a measured64-byte infallible allocation and aborts on forced OOM. Do not claim end-to-end allocation-failure safety. Measure new fixed owner/ticket sizes and allocation peaks directly, separately from payload reservations, caller buffers, linear memory, allocator overhead/RSS and future bridge/OS copies. No resource ceiling is silently enlarged to fund this experiment.

## Required bounded implementation evidence

Use original handcrafted binary builders and mock trusted native ports, with actual interpreter execution in debug/release. Cover all six imports; each enqueue operation's fixed identity; direct/indirect/exported returns and indirect mismatch/null traps; all old API/CLI/C/profile/stream rejection paths even with combined features; malformed/uncalled imports; strict wake/startup/memory validation; disabled startup and enable ordering; successful-turn drain versus trap/fuel/cancel discard; coalesced wake and no same-turn I/O; zero/unaligned/end/negative/wrapping/overlap bounds and unchanged sentinel bytes on every rejection; pending/small/ready length semantics; exact/+1 byte fuel and host calls; quota/generation/turn/owner exhaustion; equal raw bits/foreign tickets; cancellation/expiry/duplicate/late post races; trap/close with ackable retained tickets; preserved panic unwind/poison failure; fixed payload hashes/bytes/required lengths and generator parity. Assert no allocation/consume/token generation on invalid memory/quota paths and retain known OOM abort transcripts instead of calling them graceful.

Receipts must pin source/contracts/generated payloads/tools/commands/logs and compare old ABI/layout/acceptance tests. Node may be a development oracle for original Wasm call/return/indirect semantics, never a production dependency. No C/native I/O/activation/identity/release/Swift async changes, full Swift/FieldLog execution, package dogfood, device/store/operational or GA claim follows. Official reference: [Wasm module validation](https://webassembly.github.io/spec/core/valid/modules.html) and [execution instructions](https://webassembly.github.io/spec/core/exec/instructions.html); all implementation/generator/fixture code remains independently authored.
