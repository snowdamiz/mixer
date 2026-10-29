# Independent Android axis-refusal source review

Verdict: no actionable source-level implementation or test/API inconsistency found in the exact isolated candidate. This is a source/data review only. Swift compilation, all eight focused XCTest methods, existing runtime/transaction regressions and every native integration check are UNRUN. This review gives no runtime, source-pair, release, OTA or GA acceptance.

## Bound objects

- Candidate DocumentSession: 4,328 bytes / cf1954af12e316bcd7cf8ea4def41d2dc6b26921fffa60177bce477c7f0749b7.
- Candidate receipt: 5,980 bytes / c1f04809f7515dfebea9159d006eafbf5f998c16ef709b9996efffaac0e213f4.
- Candidate XCTest source: 11,870 bytes / 7d274de5f4de44b9acf2affc7579a8d1a0bd77cc00a5afd1883b86862411553d.
- Parent proposed adapter24: 8cd611a5b07fbf96adb270fa30042577789d4b87b252108697003809f00599b4.
- Candidate future adapter24 data projection: ae18d494f768a280600dbefcad0cd55fb9a4b9b993c6cd441f084a08fbf6e03e.
- Unchanged current SDK22: bc03288599ece5612cc4dce8b80fc404942584e0477ec9333bd39c0fa7d352d0.

All 55 candidate named input identities, all 24 candidate assembly rows, all 22 SDK map members and all five candidate pre-receipt output identities were independently rehashed. No mismatches were observed. Ordinal path projection reproduced both parent and candidate adapter digests and SDK22. Comparing complete parent/future row objects found only the DocumentSession replacement. Wire and descriptor objects compare equal to the parent proposal. This child does not alter or expand the parent's collapsed identity.

## Source behavior

Removing precisely candidate lines 63-64 reproduces the pinned canonical baseline byte for byte (4,128 bytes / 701b3d82add793a2b425bfc9673583afa8be4112406071242099da7da252bd0c). The diff declares the same two insertions and no deletions.

Candidate DocumentSession.swift:60 invokes the complete default UIValidator pass before the Android-specific traversal. Its line 64 checks dictionary presence, so every generically admitted explicit textField axis is refused without normalization. Malformed values retain invalidProperty; default vertical values retain unsupportedTextFieldAxis(.vertical), because validation exits before the new guard. The loop appends every child at line 69; the new guard applies to root and nested fields without changing list/baseline restrictions.

Initial profile admission at lines 24-27 precedes reconciliation. Dispatch checks the reducer's value copy at lines 41-45, reconciles a local copy at lines 46-47, encodes it at line 48 and only then assigns state/revision/reconciler at line 49. Thus the new refusal occurs before any candidate reconcile or state publication. These are source-order findings; value semantics and synchronous side-effect-free application closures remain required by the existing contract at lines 7-12.

SDK Authoring.swift:63-70 omits axis for both default and explicit horizontal. Protocol.swift:55-65 retains in-memory properties and :169-196 validates guarded decode and encode without normalization. Validation.swift:62-121 validates the complete tree and :158-170 retains the existing axis cases. Reconciliation.swift:114-150 retains the document/properties and current identity for an unchanged node kind; route at :78-94 checks revision first. NativePacketV1.swift:14-20 revalidates the portable default and :111-120 emits every sorted property. No SDK source bytes change in this candidate.

## Eight focused test API checks

Every listed method is present once, and the eight source names match the candidate manifest. Tests use the real public SDK/runtime declarations; no missing or inconsistent project API/type was found by inspection. XCTest/framework/compiler acceptance remains UNRUN.

| Candidate test lines | Obligation and checked project declarations |
| --- | --- |
| 81-109 | Default/explicit horizontal equality, packet bytes and accepted update. Authoring TextField initializer/document; UIDocument Equatable; UIValidator.encode; UIReconciler.apply/currentSnapshot; UIRenderSnapshot.encodeNativePacketV1; AndroidDocumentSession.render/dispatch/state/revision. |
| 111-126 | Guarded raw decode/encode/native packet preserve horizontal; Android initialization refuses. UIValidator.decode returns ValidatedUIDocument.document; UIDocument.decode; UIRenderSnapshot.identity(for:); UINodeIdentity Codable/Hashable. |
| 128-162 | Two refused reducer candidates preserve value state, revision and exact render bytes; original identity recovers; subsequent replay is staleRevision. State is a value-owned Equatable/Sendable struct; UINode.properties is mutable; RoutedUIAction.actionID/value and UIRoutingError.staleRevision exist. |
| 164-175 | Explicit horizontal survives SDK validation through vStack/section/hStack nesting and is refused by Android. NodeKind cases and UINode children initializer exist; generic structure permits this tree. |
| 177-185 | null/bool/number/unknown/empty axis retain invalidProperty. All UIValue cases and UIValidationError.invalidProperty(node:key:) exist. |
| 187-195 | A later malformed sibling retains the generic missing-text error before Android horizontal refusal. UIValidator traverses every child and requires text. |
| 197-205 | Typed and raw vertical keep portable-default refusal. TextFieldAxis.vertical and UIValidationError.unsupportedTextFieldAxis exist. |
| 207-215 | A later vertical sibling retains the generic vertical error before Android horizontal refusal; node/action identifiers are distinct and valid. |

The packet helper uses sanctioned UIDocument.decode for the embedded document and JSONDecoder only for [UINodeIdentity]. Event envelopes use the declared revision/identity/event/value initializer. The helpers' error comparisons are compatible with the project's Error/Equatable enum declarations. No subject was imported or typechecked to establish these observations.

## Executable obligations still open

Execute the eight focused methods in an explicitly authorized isolated assembly of the exact candidate and pinned SDK22/SessionRegistry. Also execute all existing RuntimeTests and TransactionTests against that assembly. The relevant source inventory is:

- RuntimeTests.candidateReductionAndRoutingAreAtomic; unsupportedAndroidSubsetFailsBeforePublishingPacket; registryRejectsUnknownOversizedAndSmallBuffersWithoutCommitting; escapedPacketLimitPreservesStateRevisionAndIdentityUntilAValidUpdate.
- TransactionTests.abortRetainsCommittedEngineAndCommitAdvancesExactlyOnce; ownerTokensNeverCrossSessionsOrSurviveDestroy; capacityAndEngineFailuresRetainNoCandidateAndNoReduction; invalidPrepareZerosOutputMetadataAndDoesNotRetainState; renderCandidateAndRegistryCapacityStayBounded; realDocumentRevisionAndIdentityWaitForNativeDecision; concurrentCommitAndAbortLinearizeOneDecision.

Those eleven existing methods preserve reducer/routing/output failure rollback, existing Android profile denials, buffer/status rules, token ownership, abort/commit-once behavior and real document publication timing. The eight new methods do not replace them. SDK TextFieldAxisTests and NativePacketV1Tests remain the existing regression suites for generic capability and encoding bounds; they were inspected only for source inventory here and remain UNRUN. Combined CLI/driver/Java admission, generated artifacts, native UI/phones and all qualification gates remain separate and pending.

## Authority and cleanup

Only axis-refusal-review/findings.md and axis-refusal-review/receipt.json were written. Candidate, canonical, frozen parent and global tracking files were untouched. No subprocess, compiler, Swift/JVM/Rust/product/Node oracle, Git/gh/network, subject-module import, process/group/signal/probe, native instance, UI automation, capture or phone operation occurred. No native cleanup was needed. All previous process/custody/runtime/publication holds remain.
