# R224 independent long-note boundary review

**PASS — exact R212 product slice against frozen R199 contract v2.** No product source blocker was found. No producer, canonical, or public source was changed. This accepts the reviewed host/data-policy slice; native and JNI execution remain with root.

Candidate patch SHA-256: `071c341ed4f13b7b0840fc4c378b323c6e2cc697282d4c0623e71477c2a60a81`.
Contract SHA-256: `cb8c3bcdfcb13f67735af5e3a2f8c9e8b45e94bb270c4526c60fd9cf20e1df65`.
All 13 actual public baseline hashes and afterimage hashes matched `pathmap.json`; regenerating the unified diff reproduced `candidate.patch` exactly. `identity.json` records every hash. Revision `d2172767c3d0d1984bc853e32a98e698f46dd603` is supplied provenance; no Git command was used.

## Independent execution

Three compiler/test invocations were used, all successful with owned command groups positively observed absent after reaping:

1. Swift test with `--jobs 2`: six test functions passed. It compiled the exact changed Swift sources with production MixerCore/MixerUI/MixerAndroid and the original FieldLog Workspace. It exercised scope refusals, malformed documents, escaped Unicode and decoded UTF-8 limits, invalid surrogates, duplicate escaped keys, raw byte overflow, NUL/required domain refusal, host profile mismatch, stale owner/revision/identity, invalid event kinds/values, mixed-batch atomic admission, foreign-policy snapshots, exact aggregate and 32-event ceilings, and all six existing Java-event fixtures through host/routing/domain.
2. `javac --release 17 -Xlint:all -Werror`, with launcher heap 384 MiB and ActiveProcessorCount=2: exact production UiPacket/AndroidUIProfile plus unchanged Json and independent attack source compiled.
3. Java with heap 384 MiB and ActiveProcessorCount=2: **94 checks passed**. These independently constructed packets and actual R212 fixtures exercised old profiles, horizontal/missing/forged axis, labels/IDs/accessibility/unknown properties, kind misuse, malformed values/Unicode/UTF-8, escaped duplicate keys, byte-exact event output, stale identity/revision, disabled events, and raw packet sizes exactly 1,048,576 and 1,048,577 bytes.

The original and returned payloads for ASCII, accent, emoji, decomposed Unicode, controls, and newlines were independently compared at exactly 100,000 UTF-8 bytes. Workspace's original hash remained `6f11d54b41081b20429be486f074f886ec6f53083753bf7a19c67a3c5d19e014`.

Two isolated mutant modules were compiled in the same Swift invocation. Removing the policy selection guard admitted a standard-policy 100,000-byte value; replacing UTF-8 byte count with Character count admitted 100,004 bytes of emoji. The same refusal oracles reject both original cases and detect both mutants. Mutants exist only in owned review scratch, with their hashes retained.

## Authority review

The Java profile is immutable on the surface, owner and renderer. V4 is explicitly selected; advertised capabilities cannot upgrade an old Swift profile. Snapshot policy equality is checked before host installation, and installed/current snapshot routing both precede source dispatch. Long value admission remains scoped to V4/longNoteV1, vertical textField.value and its bound textChange. The standard 16,384-byte value and 131,072-byte batch defaults remain intact.

The renderer's changed predicates extend the existing V3 branches to V4. The X/width guard in `sameFrameV2` remains; horizontal height checks, binding/ancestry equality, complete-candidate membership, exact owner/base/fence/operation identities and transition-cohort checks remain in their callers. No additional authority beyond the contracted V3 semantics was found by source review. This is not an executable native geometry claim.

## Nonblocking test-helper observation

R212 `LongNoteCodecTest.java:18-22` builds negative variants with `Json.encode(packet)`. Baseline `Json.java:41` has no List encoding branch, while a packet contains identities/children/actions arrays. Thus those helper-based negative cases can throw `unencodable value` before reaching `UiPacket.decode`; they alone do not prove the intended parser refusal. The source-level reproducer is `Json.encode(Json.parse(validPacketBytes))`. No extra invocation was spent reproducing this helper issue. R224's independently built raw packets avoid that helper, reach the production decoder, and pass the corresponding refusal checks. Root can correct the producer test helper without a product successor patch or another preparation campaign.

## Scope and cleanup

Exact commands, raw stdout/stderr, source/test/tool hashes and artifact hashes are retained here. Xcode metadata is 27.2 and the selected JDK release is 25.0.4.1; R212's supplied Swift 6.4.2/SDK27.2 version report is identified as inherited metadata, with current executable hashes recorded. No 26.6 claim is made.

No Git, remote, device, signing, child agent or held namespace operation occurred. No additional review round was launched. Cleanup removed only the fresh R224 userdata after all three owned groups were confirmed absent; see `cleanup.json`.

This review does not qualify the UIKit renderer, Android native measurement/editor behavior, C-ABI/JNI, durable consumer integration, published-package adoption, physical phones or GA. Root retains its planned actual V4 native flow.
