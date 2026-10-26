# Independent Android candidate5 profile3 CLI review

The exact admitted candidate5 CLI integration passes this bounded independent
host review. No CLI source defect was found. The review covers source-pair
admission, actual creation/export and copied application semantics. Native owner
implementation acceptance belongs to the separate owner review and root.

The [receipt](../verification/android-private-owner-profile3-candidate5-independent-review/receipt.json),
[producer audit](../verification/android-private-owner-profile3-candidate5-independent-review/producer-audit.json),
[source review](../verification/android-private-owner-profile3-candidate5-independent-review/source-review.json)
and [sealed inventory](../verification/android-private-owner-profile3-candidate5-independent-review/manifest.json)
retain the exact inputs, commands, tool identities, stream outputs and products.
Git revision `d275c072b6c89b8e99213e4eb4dafdc4722f5f40` supplies context only;
source identities bind the uncommitted selected tree.

The audit verifies all 1,008 producer members and 7,073,964 bytes against manifest
`31e034832247144f6f042006f4725dbf0242408ec33d61b9d1cedaa688b90ec4`
and seal receipt
`8ffb4ec37ff4189a330dfb0c32b427d7399365fdbf3c94a5a64ea6b70cf92db0`.
It verifies the 356-source projection
`f57c7145ff5465b2ad40accf12bb4852f17d7de270963ec3b7b2cd73e2577502`
and 311 canonical candidate inputs against current sources. Root admission and
profile selection are checked explicitly before compiling. The candidate5
profile proposal is
`6bcf2c6b0b0936522e3a6f5297765b6e4f795203b55721aabe7a82c4ba216a8f`.

The compiled Swift profile and both fresh rendered Python policies equal that
proposal. The profile ID remains `mixer.android-source-pair.3`; its adapter
projection is
`c5df444d5be8f7d422dedde7786b0232f24db1b295288da3cc3fce31a27f5b59`.
The SDK projection remains
`4c2e74bbdb1c060ffa2219ed378d11ed390e7a4454b95df4a2ee72074bb9b5a7`.
All 44 projected files, the 9,587-byte canonical descriptor and generated lock
are checked in the created and exported applications. The owner identity is
`056aa51d07e765b59a3859ce76090477a24211c973b63336406ff4b0d4102269`;
the moved core remains
`4282e8284212fb042a139f597d9f34f061f6f27673e918a52f1f784e6fe9ebb6`.

Comparison with the previously reviewed candidate4 CLI inputs confirms that only
the compiled owner size/hash and adapter projection changed. The other four
selected CLI/driver/test files, profile ID, SDK, descriptor and wire contract are
unchanged. The Swift admission gate checks the profile before generic source
hashing or compiler/version probes; it completes topology, type and size checks
before bounded content reads. The Python driver validates its rendered policy
before reading the lock, then admits the profile and exact closed source pair
before generic hashing, tool inspection and output creation. Export validates
the input before making a destination. These are local development source
controls; this review does not authorize an OTA release.

The independent runner executes 69 host commands from a separate 156-file
source closure with projection
`eb5c8fe4f32825e7cba0b6178509cc96157c4bab07584e928d6e8e76c186c533`.
Fresh Debug and Release CLI builds pass with Apple Swift 6.4. The Debug CLI
creates an application; the Release CLI exports it. Java/C adapter files are
admission inputs in this review, with no native compilation or execution claim.

Three independent Swift host methods exercise the exported application's
modified factory and reducer: typed factory seed at revision 1; Unicode edits
with reducer transformation at revision 2; stale replay refusal with identical
committed bytes; and separate state for separate handles. The suite has 18
static `#expect` sites and two shared `#require` sites, rather than a claimed
dynamic assertion count. Positive Python probes run in normal and optimized
modes and check exact source admission plus two unsupported-policy pre-lock
refusals: profile2 and a Boolean schema.

Nine negative fixtures cover profile2, the missing Android lock record, a stale
candidate4 profile with the same profile ID, and same-size edit/removal/rename
for each of owner and moved core. Each of the six source tamper fixtures
recomputes the generic adapter digest. Each fixture executes Debug Android/iOS
build requests, Release host build/export requests, and direct Python driver
build requests in normal/optimized modes. All 54 commands return the expected
admission refusal; all nine Python in-process traps refuse before generic
hashing, tool inspection and output creation. Tools/output sentinels remain
absent, and every fixture's bytes—including its lock—remain unchanged after
the requests. This samples configuration/platform combinations; the producer
matrix independently supplies all three common platforms and export in both
configurations. The missing Android record is distinguished from removing the
entire lock file; the producer's focused Swift suite covers that separate case.

All 101 producer command results, raw literal arguments and output hashes
verify: 29 successful commands and 72 expected refusals. The source binding is
present on 100 commands; `tracked-input-list` runs before snapshot creation and
is disclosed as unbound. The 66 actual CLI consumer/refusal command executable
identities agree with their final pre-cleanup products. Producer outputs report
13 Swift methods per configuration, and 10/9/11 Python methods in each of normal
and optimized modes. The copied producer consumer reports four shared methods,
three session methods and one customized factory/reducer method.

Release `swift test` relinks the producer CLI. The initial version command used
`ed9083e21e9c9d47116b70bac6e32039f4d5af49ff62db6389fae1a2335a8ba0`
(3,158,696 bytes); actual export/refusal commands used
`b423da51a306a697c5fe85f5a48d396beef8004daddf49304251530f0540e371`
(3,282,040 bytes). Both are recorded correctly, and the candidate5 producer
packet has no seal failure. Its Debug CLI identity is
`a67dfb3741f9535d351c1b964e0b4de96bb99d7bffc429b2412fe3f736cbe130`
(4,510,032 bytes). The independent CLI products are separately built and bound
to their own executed identities. No equality across different build paths is
assumed.

Seven independent products were hashed before four owned scratch trees were
removed; the producer's 39 hashed products and five removed scratch trees also
verify. All independent children were reaped within per-command deadlines;
none required a signal. Commands retain literal argv, working directory,
source/input bindings, direct executable identities, output, timeouts and
PID/PGID. Resolved Swift frontend identities are recorded. This is not a
descendant launch/dependency trace or immutable sandbox attestation. The source
and prior sealed packets are rechecked before sealing; no old packet is edited.

Native runtime, emulator, simulator, physical-phone, screen capture, UI and
process-inventory work remains paused and was not attempted. No public V2,
published FieldLog package consumption, signing/store/operational or GA gate is
accepted. No dependency was added, and this lane does not commit or push.
