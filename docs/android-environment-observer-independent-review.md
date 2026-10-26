# Android environment observer: independent preaccess controls

This is an independent **preaccess plan**, frozen before reading the producer's
candidate, new host harness/leaves/runner, new profile implementation or packet.
It does not accept an implementation or claim executable, compiler or native
evidence. The selected implementation contract is
[`implementation-selection.json`](../verification/android-environment-observer-root-review/implementation-selection.json),
SHA-256 `dd7f43f91f24ea433fb01f3f27c4b823140a8d0a95df3a53c8a18362652fc319`.
The plan's machine-readable controls and admitted old-source identities are in
[`preaccess-plan.json`](../verification/android-environment-observer-independent-review/preaccess-plan.json).
Its seal binds this document, that plan and the preaccess read receipt.

Only live `AGENTS.md`, that selection, the frozen
[`android-owner-effect-contract.md`](android-owner-effect-contract.md), and
selected old-source files under
`verification/android-owner-effect-contract/inputs/` were read. The context
revision is the selection's `4e48ac1a3c1593d46c0dcbaf207053ff5e1b6d5d`;
it is not a new working-tree or candidate assertion. Source reads and hashing
were the only shell work. No implementation/test execution, compiler, native
runtime, capture, UI automation, process inventory or compiler/tool discovery
occurred. No frozen hosted catalog, authority, rejected-worker or broad harness
was read, imported or executed. No callback retry is selected.

## Admission and independence

Root must first supply an immutable candidate manifest and explicitly admit its
exact hashes. The reviewer must not follow a live producer path. A failed or
changed hash stops dependent work and returns to root; it cannot refresh the
expected identities. This plan remains immutable. Any necessary amendment is a
separate dated artifact recording why, when and which candidate bytes had been
seen; the original assertions remain visible.

After root admission, first author the independent leaves and harness from this
plan and the old source, without inspecting candidate source or producer tests.
Seal their complete file identities before compilation. Then inspect and compile
the exact admitted **actual** `NativeEnvironmentV2.java`, together with those
independent files. No translated observer, parallel lifecycle algorithm,
producer test import or patched candidate is admissible. The exact planned leaf
list is frozen in the JSON. A newly required Android leaf is a visible amendment,
not automatic source discovery. Java standard-library dependencies need no
Android leaf. Producer leaves may be reused only after an explicit independent
audit of every leaf's side effects, callback phase, fault placement and signatures;
the independently authored assertion suite and expected outcomes must survive.

The leaves implement a tiny test boundary, not Android. They record separate
events for `add.enter`, callback/reentry before acquisition, `add.acquire`,
callback/reentry after acquisition, `add.throw`/`add.return`, `remove.enter`,
platform removal, `remove.throw`/`remove.return`, and retained callback delivery.
Each event records slot, listener identity, target identity, main-thread status
and registration count. A before-acquisition fault acquires nothing; an
after-acquisition fault first records an owned registration. Faults and reentry
are one-shot, bounded actions. The leaf never silently retries or decides what
the observer should do. The harness independently checks the resulting platform
registry, call trace, renderer callback counts and capture behavior.

## Finite host controls and independent assertions

The slots are fixed in registration order: component, layout, attach, window
focus, insets, contrast, high contrast and animator settings. Each fake target
has a distinct identity; the content resolver and window observer can be replaced
after acquisition. Ordinary success acquires each slot once, permits a concrete
capture, invalidates an old capture when the tuple/generation changes, performs
the authoritative second read in `current`, and closes all eight slots once.
Foreign owners and changed window tokens reject captures. The clean control is
necessary alongside fault cases; an always-rejecting implementation cannot pass.

| Control family | Required observations |
| --- | --- |
| H01: all eight adds, before and after acquisition | Sixteen isolated faults. For slot `k`, no add after `k`; every acquired prefix slot and the uncertain failing slot receives its bounded cleanup disposition. A before-add throw still causes a removal attempt for `k`. Successful prefix registrations are absent after effective cleanup. The original failure remains identifiable; the observer cannot capture or reopen. |
| H02: close/detach in each add, before and after platform acquisition | Thirty-two isolated controls. Retirement is observable immediately. No later slot is added. Construction unwinds instead of publishing a usable observer. If an add reenters close **before** acquisition and then resumes to acquire, a premature removal cannot count as disposal of that later registration: defer the active slot's removal until its add settles, or otherwise prove its final registration is covered without a consumed-slot retry. Assert `add.acquire` precedes its effective final removal. Repeat when the active add subsequently throws. |
| H03: notifications during construction | Each nonterminal changing notification seals/invalidate existing renderer gates synchronously, while partial registration cannot publish a usable capture. Terminal notification stops later acquisition. Renderer callbacks inspect retirement and attempt capture inside the callback; no partial live publication is permitted. There is no later callback replay. |
| H04: retirement before external work | On the first detach, first close, generation exhaustion and terminal fault, attempt capture/current and reenter close from renderer invalidation or a removal hook. The terminal state is already visible. The first detach still invalidates prior presentation gates. Close cannot wait until cleanup returns to retire. |
| H05: callbacks after retirement and wrong thread | Deliver the saved identities for configuration, low-memory, changed and unchanged layout, attach, detach, focus, insets, contrast, high contrast and content observer after close, detach and constructor failure. No tuple read, generation increment, renderer callback, refresh or new registration occurs. Insets returns the received object unchanged. Repeat every callback and close/read/capture/current/invalidate from a non-main fake Looper: thread rejection occurs before stale/no-op guards, with no further side effect. |
| H06: generation bounds | Set only the actual observer's private generation via package-peer reflection. Test `MAX_VALUE-1`, `MAX_VALUE`, and a notification from the max state; never wrap/reopen. Exhaustion retires before renderer invalidation and cleanup callbacks, invalidates old captures and cannot publish another live capture. Reflection is a test setup, not a production API or second lifecycle model. |
| H07: every removal fault, combined faults and reentry | Eight isolated remove failures, all eight together, and each position while ordinary acquisition or invalidation already failed. Assert all eligible slots are attempted despite earlier throws. Reenter close/detach and deliver callbacks at every remove entry and after platform removal: no consumed slot is removed twice, remaining slots are attempted, and repeated close cannot retry failed, dead or uncertain slots. Include a removal that returns while retaining a queued callback/registration; late delivery stays inert, and a return is not called reclamation. |
| H08: fatal failure dominance and diagnostics | Inject `Error` at every add position before/after acquisition, renderer invalidation, and every removal position; also ordinary primary failure plus cleanup `Error`, multiple fatal failures, and the same Throwable reused as primary/cleanup to stress self-suppression. Every eligible cleanup is attempted. An original primary `Error` escapes as that Error; otherwise a cleanup/invalidation Error must escape as an Error, never as an ordinary rejected edit. With no Error, preserve the original ordinary primary. Preserve independent cleanup failure identities in bounded diagnostics where suppression is available; disabled/self-suppression must not truncate cleanup. Review allocation-failure paths separately without pretending host injection proves JVM OOM behavior. |
| H09: exact stored targets | Acquire on VTO A, replace root getter with VTO B, then close: removal targets A only and B is untouched. Make A dead: no removal call on A or B, and diagnostics say dead/uncertain rather than successful removal/reclamation. Replace the content-resolver getter too: animator removal still targets its acquired resolver. Assert exact Activity/root/manager/listener identities for all eight slots. |
| H10: dedicated insets owner | One private fresh root, no competing setter: install once, deliver the exact original insets object, clear that owned listener once, and retain/deliver its old callback after retirement. No claim that a preexisting/competing listener can be recovered or composed. The unchanged public V1 Activity/padding source is an independently checked profile invariant. |

Cleanup order need not be an arbitrarily imposed forward/reverse order. Record
the clean control's complete deterministic permutation and assert that isolated
fault cases preserve its eligible-slot projection, apart from an explicitly
deferred in-flight acquisition which must settle before its own final removal.
Reentrant traces must have no duplicate removal attempt for an already consumed
slot and must contain all eligible slots. This is an independently selected
ordering invariant, not an expected decision log copied from candidate code.

Diagnostics must keep distinct facts: attempted add, uncertain add, consumed
cleanup slot, removal attempted, removal returned, removal failed, target dead,
and outcome still uncertain. A test platform's empty registry establishes only
the modeled leaf outcome. An actual Android removal return never proves real
resource reclamation. Bounded diagnostics must not become an unbounded throwable
or callback retention mechanism. Host cases fail if a required control cannot
reach the actual observer; inaccessible behavior is reported unverified instead
of replaced with a separate implementation.

## Executable host strategy after admission

Use a fresh owned scratch directory, compile a closed explicit source list and
then run the package-peer assertion harness with a bounded timeout. Planned
compiler arguments are `javac --release 17 -Xlint:all -Werror -proc:none`, with
explicit empty classpath and sourcepath, explicit output, the admitted actual
observer, one independent harness and the frozen leaf list. Run with `java -ea`
and an explicit classes-only classpath. Strip implicit `CLASSPATH`,
`JAVA_TOOL_OPTIONS`, `_JAVA_OPTIONS`, `JDK_JAVA_OPTIONS` and `JDK_JAVAC_OPTIONS`.
Do not use source globs, ambient SDK stubs, annotation processors, class discovery
or another test catalog. Capture the tool executable identities/versions and
every argv, environment override, complete stdout/stderr, exit/timeout, source
and class identities. Reap only owned child processes and remove only owned
scratch in a `finally` path; record failed-run cleanup as well as successful
cleanup. No process inventory is required. No harness execution has occurred.

## Exact profile 2 and actual consumer controls

The new profile must be a frozen literal `mixer.android-source-pair.2`, schema 1,
with exactly the old 22 SDK and 20 adapter member names. Compare against the
sealed old Swift literal as data; do not treat an edited lock, mutable SDK,
rendered resource or recomputed projection as policy. All 22 SDK identities and
19 of 20 adapter identities must be byte-for-byte equal. Only
`app/src/dev/mixer/android/NativeEnvironmentV2.java` may differ, and that identity
must equal root's separately admitted candidate. Independently recompute the
sorted `path + NUL + sha256 + newline` projection from the fixed literal and
verify the adapter digest. The unchanged SDK projection is
`4c2e74bbdb1c060ffa2219ed378d11ed390e7a4454b95df4a2ee72074bb9b5a7`.
Descriptor identity remains 9,587 bytes /
`1aeab75c457c21e5c801ab8b446490971d510021c945d0841252360becd8ead3`.
The six wire fields remain exactly as the selected contract specifies. Root
must freeze the candidate 42-member map and source digest before qualification.
No automatically refreshed source identity, unknown-field acceptance, profile-1
reinterpretation or second production map authority is admissible.

Exercise the actual built Swift CLI and its actually rendered driver in separate
fresh owned projects. Use the ordinary CLI-created app-owned factory/reducer,
then a small ordinary app-owned value-state reducer variation. Verify the
generated entry actually constructs that app's `AndroidDocumentSession` and
dispatch reaches the app reducer with the expected document/state/revision.
Include the generated starter preset and a distinguishable independent value
change so a checklist engine, hard-coded fixture or always-empty document cannot
stand in. The default factory/reducer must still pass alongside rejection cases.
This is application source control, not device interaction or dogfood release.

Freeze the CLI binary, linked policy/resource identity, rendered driver bytes,
generated project inputs and locks. Run these consumer controls:

1. Fresh profile-2 creation/admission succeeds; snapshots equal the frozen 42
   identities and descriptor; both actual entrypoints accept those exact bytes.
2. Missing profile, full old profile-1 lock, profile-1 ID changed alone, missing
   fields, wrong scalar types and unknown fields reject. Preserve the old lock
   and historical receipts rather than modifying them into an approved project.
3. Profile-2 lock with same-size observer edit rejects; repeat after recomputing
   generic `adapterDigest`. Repeat with changed SDK member plus generic
   `sdkDigest`, and changed descriptor with recomputed generic digest. Also edit
   profile-lock projection fields to the changed-source values: the compiled
   fixed policy must still reject. Never rewrite the compiled profile itself
   to make a negative fixture pass.
4. Wrong or unrendered driver policy marker, map count/member-name drift,
   duplicate/unknown policy fields and unsupported ID fail closed. A deliberately
   modified driver is a rejected fixture, not an admitted release driver.
5. For early lock failures, use absent/unreadable source roots and tools that
   record invocation. For source admission failures, add explicit closure/name/
   type/size canaries and a tool-invocation sentinel. Assert the precise profile
   rejection, no generic-hash access outside admission, no tool discovery/probe,
   and no output/staging/build receipt creation. The driver may run through an
   independent bounded audit wrapper that records file opens/subprocess events
   while executing the original rendered bytes/entrypoint. Such a wrapper cannot
   replace policy or build functions. For the Swift CLI retain behavioral
   diagnostic/canary evidence plus source-order review; if an access fact is not
   directly observed, label that fact unverified rather than treating absence of
   output as a complete filesystem trace.

Source checks alone do not pass these controls. Test modifications must be
confined to explicitly negative copied fixtures. Do not import the broad frozen
test harness or copy its authority map. Existing producer receipts are evidence
to audit later, not independent assertion sources. Full build/sign/package paths
are unnecessary for negative admission controls.

## Native compilation boundary and pending gates

Only after host controls pass, audit direct compilation of the **complete actual
adapter**, not leaf classes, against the installed pinned official Android SDK
jar with Java 17 and D8 `--min-api 28`. Bind the exact adapter inventory and SDK,
JDK/D8, NDK and Swift Android SDK binaries/metadata, argv/streams and all class,
DEX and ELF outputs. Cross-compile the ordinary generated app-owned Swift/JNI
factory/reducer target in fresh owned output, with the actual admitted project.
Do not execute `native/android/build.py`, which can touch shared output and a
debug signing key. No signing, key creation or top-level native runtime path is
selected. Report unused/unsupported compiler checks as pending, never passed.

Host leaves establish modeled lifecycle behavior only. SDK compilation and D8
min 28 establish signature/bytecode bounds only; neither proves API 28–35
runtime support, API-36 high-contrast behavior, Looper behavior or platform
listener removal. Native runtime/capture/UI remains paused. Phone runs remain
pending without requesting reconnection. Public V2 routing, inset composition,
outer effect-runner fences, saved-state continuity, fonts/resources/accessibility,
runtime/device/performance, signing/store/customer/operational gates and
accountable GA review remain pending. FieldLog must eventually consume immutable
published packages from a separate repository. No OTA release authority follows
from this plan, a host pass or compiler success.

This reviewer owns only this document and
`verification/android-environment-observer-independent-review/**`. Root owns
integration metadata, delivery and acceptance. There are no commits, pushes,
root metadata edits or candidate acceptance in this preaccess phase.
