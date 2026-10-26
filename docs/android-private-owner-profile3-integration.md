# Android private owner profile3 CLI integration

The compiled `mixer.android-source-pair.3` policy now binds the exact frozen
candidate4 private owner sources. Root selected this bounded CLI rebinding in
[the exact selection receipt](../verification/android-private-owner-effect-integration-root-review/candidate-4-profile-selection.json)
(`fc0e083821790e12c1c12b709f2a8e7c44a40ff457e4183853ef6adbdd919106`).
This selection permits host consumer qualification; it does not accept the native
implementation or authorize canonical product delivery.

The profile uses the frozen [candidate4 proposal](../verification/android-private-owner-integration-implementation/candidate-4/profile-proposal.json)
(`fa20572d64d0cec8e2bbfd959df6a2993b4e231cca6f3f8009761bd0b2678d62`),
whose 22 adapter entries project to
`57606aa94648f3b43f1bd84cc5d7479be133e3ff3c948d4830b1645466f348f6`.
The 22 SDK entries still project to
`4c2e74bbdb1c060ffa2219ed378d11ed390e7a4454b95df4a2ee72074bb9b5a7`.
The wire contract and canonical 9,587-byte default descriptor remain the selected
identities. `NativeOwnerV2.java` and the exact moved `OwnerLifecycleV2.java` enter
the generated adapter through the existing policy-driven snapshot mapping;
`AndroidProject.swift` requires no change.

The earlier partial profile3 literal referred to rejected candidate3. The new
installation changes only the candidate4 identities for
`NativeCoordinatorV2.java`, `NativeOwnerV2.java` and `NativeRenderer.java`, plus
their adapter projection. It preserves profile ID3 and the SDK/default/wire
fields. The original profile2 snapshot, original2-to-candidate3 installer and its
installation receipt remain immutable. That historical installer was not rerun.

Profile2 projects receive explicit migration/recreation refusals. Updating a
generic local source lock cannot authorize changed owner/core sources. Focused
Swift controls now include all edit/remove/rename combinations for coordinator,
authored toggle, owner and core; they recompute the generic adapter lock before
checking source-pair refusal. The Python host suite adds explicit profile2 and
same-size/remove/rename owner/core controls with recomputed locks.

The [candidate4 qualification packet](../verification/android-private-owner-profile3-integration/candidate4-qualification/)
retains the bounded runner, exact input snapshot, pre/post source identities,
command arguments, executable hashes, tool versions, process-group ownership,
deadlines, output streams and cleanup receipts. The
[host qualification receipt](../verification/android-private-owner-profile3-integration/candidate4-qualification/receipt.json)
passes the selected scope against a 356-file isolated snapshot with projection
`c39822994dbea4b61a3082b7e6c237019ec2ce0c7f8b6e54daf23ffaf448738b`.

- Both actual CLI configurations build and pass 13 focused Swift methods each,
  including parameterized source inventory, profile context and tamper cases.
- The Python compatibility, staging and appearance suites pass 10, 9 and 11
  methods respectively in both ordinary and optimized Python modes.
- Actual Debug CLI creation and Release CLI export produce the exact 44-source
  pair and canonical descriptor. The copied application's four shared app tests,
  three host session tests and one distinct app-owned factory/reducer test pass.
- Eight refusal fixtures cover historical profile2, missing Android lock and
  same-size/removal/rename changes to each owner/core source. They pass 72 actual
  CLI/driver refusals across both configurations with recomputed generic adapter
  locks where applicable, plus direct admission traps. Tool and output sentinels
  stay absent. An old rendered profile2 policy refuses before reading a lock.

All five owned build/test scratch directories were removed after evidence
collection. Actual CLI and host consumer products were hashed before deletion.
The complete 309-input candidate closure and source snapshot match their original
identities after validation. All preexisting profile history remains unchanged.

The first sealing attempt rejected its assumption that the Release CLI would
retain its pre-test binary identity. The Release `swift test` command relinked
`mixer`; the actual export and refusal command receipts consistently identify the
resulting binary. A separate disposition preserves both hashes and binds every
executed CLI command to its observed product. The original qualification receipt
and failed seal remain retained. This evidence repair reruns no product tests.

The qualification checks actual isolated Debug/Release CLI products, the common
Swift admission gate, the actual rendered Python driver and fresh CLI-created
and copied-export host consumers. Copied app tests exercise the app-owned factory,
reducer and document revisions. Negative CLI platform names `android`, `host` and
`ios` fail in admission before tools or output; they do not perform native runs.
No simulator, emulator, physical phone, capture, UI automation or process
discovery is started. Mac host session tests are not Android runtime evidence.

The candidate4 producer's Java/SDK/D8 and Swift/JNI compilation observations may
be audited and reused only with their exact frozen inputs. This CLI slice claims
no new Android compilation or APK. Independent source/barrier/legacy matrix
review and root implementation acceptance remain pending. Public V2 routing,
native framework/JNI/IME/draw/lifecycle execution, physical-phone acceptance,
immutable published FieldLog consumption, signing, stores, operations and GA
gates remain open.
