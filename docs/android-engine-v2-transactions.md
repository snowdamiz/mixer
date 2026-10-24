# Ordinary Android engine candidate transactions

The existing ordinary Android exchange commits model state before the Java
renderer attaches its screen. A native attachment failure can therefore leave
the engine ahead of the displayed revision. The registry now has a private SPI
transaction path that retains the value-owned engine candidate until the native
coordinator explicitly commits or aborts it.

`prepareV2` performs the existing render/dispatch and bounded serialization on a
copy of the committed engine. Only a successful output copy retains a candidate
and returns a nonzero token. Buffer-capacity failure, rejected events, oversized
output and invalid arguments retain no candidate and consume no token. One
candidate is allowed per session, with the existing maximum of sixteen sessions.
Its output packet is returned to the caller and is not retained by the registry.

While a candidate is pending, both legacy exchange and another prepare return
busy. `commitV2` requires the same session, token and base epoch, then replaces
the committed engine once. `abortV2` discards the candidate without changing the
engine. Retrying the most recently aborted token is harmless even if a newer
candidate is pending; it cannot discard the newer candidate. Once another abort
occurs, earlier aborted tokens need not remain recognized. Destroy removes both
the committed engine and any candidate. Handles and tokens are monotonically
assigned, never reused, and scoped to one registry instance.

The existing lock serializes these decisions. The engine contract still requires
value semantics and synchronous, nonreentrant reduction without external effects.
`Sendable` alone does not establish those properties. The registry cannot undo
effects or shared-reference mutation performed by a contract-violating engine.

| Status | Meaning |
| --- | --- |
| 0 | Success; prepare returns packet and nonzero token |
| 1 | Invalid arguments |
| 2 | Closed or unknown session handle |
| 3 | Output capacity; written reports required bytes, token remains zero |
| 4 | Rejected event, engine error or hard output limit |
| 5 | A candidate is already pending |
| 6 | Invalid, foreign, consumed or stale candidate token |
| 7 | Monotonic counter exhausted |

Callers supply valid nonoverlapping buffers and writable output metadata.
Prepare zeros written/token on failure except the required size for status 3.
The private entry points require `@_spi(MixerNativeAppearanceV2)`; existing C/JNI
symbols, `MixerActivity`, generated apps and the signed presentation path are
unchanged. No ordinary V2 app opt-in is enabled by this slice.

The later native coordinator must prepare, attach with events gated, revalidate
the attached candidate, commit the matching engine token, then perform the
prepared native reference swap and reopen events. Failed preparation/attachment
aborts the token. A failed JNI output allocation must also abort it. If the
coordinator cannot determine whether commit happened, it must retire the session
and presentation rather than guess the authoritative revision. These JNI and
native-screen joins remain unimplemented here.

Fresh-source verification passes all sixteen existing/new engine tests per host
Debug, Release and Thread Sanitizer, including seven transaction tests. These
cover native-decision deferral using the real document session, stale events,
busy/foreign/repeated decisions, destroy, sixteen pending sessions, insufficient
output, mutation followed by rejection, oversized output, nil pointer/length
combinations, and twenty-four concurrent commit/abort races per mode. Existing
tests continue to pass. The official Swift 6.3.3 Android toolchain links the
arm64 API28 library. Counter exhaustion is guarded but not dynamically reached
by these tests. No emulator/native screen execution is claimed by this host and
cross-compilation receipt; the independent renderer lanes supply that evidence.

Receipts and the source archive are in
`verification/android-engine-v2-transactions/candidate-1/`. The earlier failed
test import is retained under `attempt-1/`; it omitted the required SPI import.
Physical validation remains deferred to final acceptance under the user's policy.
