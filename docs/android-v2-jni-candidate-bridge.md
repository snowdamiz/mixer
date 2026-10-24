# Private ordinary Android JNI candidate bridge

`NativeBridge.prepareV2(handle, operation, input)` returns a package-private final
`Candidate` after C preparation and all Java delivery allocations succeed.
Its private constructor clones the packet; `packet()` returns a new clone, and
`token()` returns the opaque nonzero UInt64 bit pattern in a Java `long`. Java's
sign bit is not a validity check. Only the engine can recognize the session token.
The immutable candidate grants no signed-presentation or release authority.

Preparation bounds input before copying it into caller-owned C memory. Successful
C preparation retains engine state; every later array allocation, packet-copy,
class/constructor lookup, object construction or constructor-clone failure aborts
the token. A pending Java exception is preserved. Cleanup uses no JNI calls until
only allowed local-reference deletions and exception checks remain. Successful
abort or CLOSED confirms disposal; other abort outcomes retire the C session.
Invalid successful C metadata also attempts abort and retires the session.

`commitV2(handle, token)` and `abortV2(handle, token)` return the C status directly
with no JNI allocation, lookup or exception creation after the engine decision.
All status values and stale/foreign/idempotent rules are those of
`mixer_android_v2.h`. Legacy create, exchange and destroy remain available.

This slice requires the generated-entry integration in the same merge: CLI
capture must include `mixer_android_v2.h` and its export allowlist, and generated
Swift entries must forward all three V2 C exports. Until then, the unconditional
JNI C references cannot link against those older generated entry points. This
document does not claim generated application build qualification.

The Activity/native coordinator remains separate: prepare, decode/validate,
attach with events gated, revalidate, commit the matching engine token, swap the
prepared presentation, and reopen events. Any ambiguous decision requires
retiring the presentation/session. This slice enables no ordinary V2 opt-in and
does not join native attachment, generated app behavior, or signed presentation.

The executable collector in `verification/android-v2-jni-candidate-bridge/verify.py`
snapshots exact sources and runs the unmodified production JNI against fresh
host Swift Debug/Release libraries in actual JVMs with `-Xcheck:jni`. A separately
retained derived C/Java harness injects allocation, JNI delivery, constructor-clone
and cleanup outcomes; its authority never enters the application. Each derivation
and artifact is hashed. The official Swift SDK bundled NDK r27d cross-links the
production JNI at arm64 API28, and all application Java sources compile with
release 17 and D8 min28. Receipts distinguish host execution, derived faults and
Android compilation. No Android runtime, emulator, physical device, final hardware,
immutable FieldLog publication or GA qualification is implied.
