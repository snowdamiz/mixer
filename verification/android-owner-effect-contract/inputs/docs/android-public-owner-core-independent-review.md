# Android owner core independent host review

The selected package-private `OwnerLifecycleV2` passes this independent host
review. No substantive candidate defect was found. This is a reviewer result;
root acceptance and delivery are separate. It establishes ownership decisions,
not execution of Android or native effects.

The reviewer froze its interpretation before reading candidate source. Its
[preparation](../verification/android-public-owner-core-independent-review/preparation.json)
binds root's 15 preaccess controls and seal
`afc099d49f365c143b3db12d880693d528ea48db67baa3b07f61913354515a09`.
The [selected contract](android-public-owner-contract.md) and root selection
were checked against their supplied hashes. Producer evidence was read and
hashed only; producer tests, runner and verifier were never imported or executed.

The producer manifest matched all **48 members / 183,472 bytes**. Its source
binding tree matched
`c5597d41313b506ef39a0dcd36ebde7fd8f50c78db436410681262c1c233833d`;
all 46 implementation/profile inputs matched, including all 42 unchanged
source-pair profile 1 members. The candidate source is exactly 12,473 bytes,
SHA-256 `4282e8284212fb042a139f597d9f34f061f6f27673e918a52f1f784e6fe9ebb6`,
at context revision `1f114d8f235e8042c275a2549fef7d4994272360`.

The independently authored package-peer harness compiles exactly the candidate
and its own source using the existing official Homebrew OpenJDK **25.0.4.1**:
`javac --release 17 -Xlint:all -Werror -proc:none`, with empty classpath and
sourcepath directories. All 14 resulting classes have Java 17 major version 61.
Manual facts and callbacks require no sleeps, Android stubs or native runtime.

| Attempt | Methods | Explicit scenarios | Assertions | Result |
| --- | ---: | ---: | ---: | --- |
| First | 32 | 70 | 264,250 | Passed unchanged; no initial compiler, harness, oracle or candidate failure. |
| Final | 33 | 71 | 264,289 | Passed after adding the identified input-invalidation coverage gap. |

Counts describe each complete attempt independently and must not be added.
The final attempt covers all R01–R15, observes 61,199 decision batches / 60,705
decisions, and sees a maximum batch of four against the declared bound of five.
It includes 20,000 deterministic refresh cycles and 134 injected wrong-thread
rejections: all 18 owner methods across six phases, four stale-delivery variants
across those phases, and both constructors. Immutable record accessors are
value reads; they do not read a live owner or obtain native authority.

The behavioral controls include missing readiness facts, fresh drain probes,
dirty bursts and invalidations during opening/refresh/input, eight opening
retirement causes, cross-owner/stale/duplicate completions, acquired-resource
failure cleanup, registration failure, independent cleanup diagnostics,
ineffective callback cancellation, input revocation/reentrancy, lifecycle and
focus/configuration changes, temporary unavailable geometry/insets, epoch
exhaustion, never-returning operations, fresh-owner independence, unknown
outcomes, and reference identity despite deliberately equal-valued objects.

Focused source review independently checks the bounded-state claim. The core
has **28 instance fields**: 20 fixed reference slots, six booleans and two longs.
It retains no collection or action history; only the latest facts, one resource,
one drain, one operation and one presentation are retained, alongside fixed
lifetime/cleanup tokens and four diagnostic slots. Referenced caller-owned
objects may themselves contain arbitrary graphs; this is a bound on core slots
and core-owned history, not a bound on the whole JVM heap. Per-call lists are
temporary and copied to immutable results. Reviewing every construction path
gives at most four decisions, including terminal seal/cancel/unregister/close.
Every owner entry invokes the trusted nonreentrant checker before branching or
observing owner state. Both completion branches preserve the selected rule that
only matching initial open may first adopt an acquired resource, including after
retirement. Refresh/input cannot replace it. A close result clears retained
ownership even when it reports failure; that does not prove actual reclamation.

Exact argv, tool versions/binaries, source snapshots/digests, stdout/stderr,
class hashes, coverage and cleanup receipts are retained in the
[review packet](../verification/android-public-owner-core-independent-review/receipt.json).
All 12 owned host children across the two attempts returned and were
reaped; both owned scratch directories were removed afterward. Each child was
bounded to 60 seconds plus a 15-second forced-reap bound, below 180 seconds.
No native, capture, device or unrelated process was started or queried.

Actual main-Looper identity, listener registration/unregistration, synchronous
native draw/input gate sealing, setter reentrancy, JNI and the commit/finish
boundary remain unproven. Emitted cleanup decisions and completion reports do
not prove cleanup attempts or resource reclamation. If an operation never
returns, deferred cleanup remains pending. The later Android effect runner,
adapter/public routing, native runtime matrix and final phones remain pending
under the current pause. API 28–35, unsupported accessibility/resources/fonts,
saved-state continuity, signed/store/operational qualification, immutable
published separate-repository FieldLog consumption and accountable GA review
also remain pending. Source-pair profile 1 and public V1 are unchanged. This
review authorizes no OTA release, production publication or GA promotion.
