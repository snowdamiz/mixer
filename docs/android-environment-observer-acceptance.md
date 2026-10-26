# Android private environment observer acceptance

The private V2 observer now retires before terminal callbacks, rolls back partial
listener registration, retains the original removal targets and attempts every
owned cleanup slot independently. It defers removal while an add is reentered,
then disposes the settled acquisition. Repeated close cannot retry consumed
slots. Main-thread checks precede stale-callback checks, generation exhaustion
is terminal, and fatal errors remain fatal after best-effort cleanup. A failed
or dead-target removal is recorded as uncertain; a return does not prove
platform reclamation.

The fixed exported source profile is now `mixer.android-source-pair.2`. Only
`NativeEnvironmentV2.java` changed within the 42 mapped SDK/adapter sources.
The descriptor, wire formats, SDK sources and other 19 adapter identities remain
unchanged. Existing profile-1 locks are rejected: use the newer first-party CLI
and recreate a project explicitly. Neither the CLI nor the rendered Python
driver refreshes an old or edited lock to authorize it.

The producer passes 161 host fault cases. Independent review passes 287 cases
and 24,363 assertions with separately authored Android leaves, plus 22 fresh
CLI/driver/consumer/signature control families. Fresh generated sessions and a
distinct app-owned factory/reducer test pass. Eleven negative families exercise
both actual CLI and driver entrypoints; six further driver policy failures occur
before lock reads. Driver hash/tool/output traps were exercised. CLI ordering
has behavioral and source evidence, without an OS filesystem trace.

Independent compilation of the complete 14-source adapter against the Android
37 SDK produces 160 Java classes and D8 minimum-28 output identical to the
producer. Producer evidence also covers the ordinary app-owned Swift 6.3.3 and
JNI arm64 cross-build with NDK r27d; review audits those source, command, stream,
ELF and symbol identities without repeating that expensive cross-build. These
are compilation checks, not Android runtime or API 28–35 support evidence.

Root verifies 2,877 contract/producer/review members, 46 current proposal inputs,
31 current host inputs and 34 independent command results. Original failed
attempts remain preserved, including the producer host-toolchain failures and
three independent test-expectation corrections. Those corrections did not change
the producer implementation. All owned scratch and children were cleaned.

See the [root acceptance](../verification/android-environment-observer-root-review/implementation-acceptance.json),
[independent review](../verification/android-environment-observer-independent-review/review.md)
and [selected contract](android-owner-effect-contract.md). The private dedicated
V2 root still requires sole inset-listener ownership. Public V1 is unchanged.
The outer owner effect runner, public V2 routing, API 28–35/accessibility/resource
support, native runtime, phones, immutable published-package FieldLog and release
and GA gates remain pending. Computer use and native runtime testing remain
paused.
