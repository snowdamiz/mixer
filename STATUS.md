# Current development status

## Completion policy, November 17, 2026

Implementation-plan completion now means working local end-to-end behavior under [Section 2](mixer-product-plan.md#2-completion-definition-and-scope) and L01–L08 in [the local checklist](gates/local.json). The eight checks cover setup/import/export, shared app/UI/capabilities, compiler/VM, signed OTA/recovery, the real local console/API/database/worker/build workflow, free administration, security/local reliability, and FieldLog/documentation.

Testing and early launch are free. Payment and purchase implementation, Stripe integration, paid entitlements, invoices, and financial activation are deferred. Verify the workflow without payment credentials or a billing service. This plan edit does not itself implement or verify that behavior. Keep existing billing code and evidence.

[Section 29](mixer-product-plan.md#29-completion-gates-and-later-qualification) maps every G01–G38 gate to local evidence and later qualification. Live deployment, provider operations, physical phones, registry publication, store approval, external apps/customers, paid pilots, and commercial metrics do not block plan completion. The launch checklist is tracked separately. The local checklist records the current evidence and remaining work. All recorded holds stay in force.

Local completion is still pending. Checkpoints retain their original scope.
Use the tracked results to assess L01–L08 and rerun any check that needs fresh
evidence from a clean checkout. Paths to disposable run files are historical
references. See [the worktree verification policy](mixer-product-plan.md#worktree-local-verification).

## November 21 SwiftPM import

The stock CLI accepts `swift package describe --type json` output and traces
findings through its local Swift target dependencies. The graph stays advisory.
In the macOS replay, SwiftPM built and ran a package with a local AppKit module,
an aliased target, and a copied Swift resource. The report kept the ambiguous
AppKit dependency, showed a separate dependency finding, and left the copied
resource unassigned. The full CLI run passed 137 Swift Testing cases and 32
XCTest cases, with one skip. Source141 admits the reviewed Swift files and
restores the previous 153-source archive. W15 remains in progress.
[Importer receipt](verification/receipts/import-swiftpm-description-v78.json) ·
[Stock CLI replay](verification/receipts/swiftpm-import-full-cli-v79.json) ·
[Source141 verification](verification/receipts/source141-swiftpm-migration-source-admission.json)

## November 21 FieldLog native date correction

The ordinary v74 export kept a partial date visible, disabled Save draft and
Commit entry, and preserved the workspace bytes. Correcting the date in the
same editor restored both controls. Save draft persisted the offset-normalized
instant. A cold launch restored the same title, timestamp, and draft. A single
Commit reused the draft ID, added one entrySaved event, and cleared the draft.
The next cold launch read the exact same committed workspace bytes. Both
owned ADB and emulator groups closed, and scratch was removed. L02 and L08
remain open. [Native date receipt](verification/receipts/fieldlog-android-date-correction-cold-commit-v76.json)

## November 20 independent FieldLog Android export

Maintained FieldLog source upgraded to public v74 (`44aecbeb6a82a`) and built
an unsigned arm64 APK from a fresh, relocated `Build/CI` export. The bundled
Android driver built after the preparation tree was removed. The source and
dependency locks matched before and after the build. APK inspection confirmed
the FieldLog launcher, API 36 minimum, API 37 target, and 16 KiB alignment.
A second independent build produced a development-signed APK. The exact APK
installed and cold-launched on a fresh API 36 arm64 emulator. Android reported
PublicActivity as resumed. The private ADB server and emulator closed, all
three ports were reusable, and the fresh scratch was removed. Earlier ADB
setup and port-reuse holds remain active. W15 and L08 remain open.
[Build receipt](verification/receipts/fieldlog-independent-export-v74.json) ·
[Installed launch receipt](verification/receipts/fieldlog-independent-export-android-launch-v74.json) ·
[Replay](docs/guides/fieldlog.md#build-the-v74-export-in-independent-android-ci)

The ordinary FieldLog iOS app also built from a relocated v80 export.
Stock Xcode built the unsigned arm64 Simulator app after the preparation
checkout and CLI were removed. All 187 exported files and four lockfiles
matched before and after the build. The bundle retained `dev.mixer.fieldlog`.
Independent review verified the exact inventory and guide. Installation
and launch remain open.
[iOS export guide](docs/guides/fieldlog-ios-export.md) ·
[iOS export receipt](verification/receipts/fieldlog-ios-independent-export-v80.json)

The maintained FieldLog `85e6fbe362` export built a generic arm64 iOS
Simulator app with stock Xcode after the preparation project, CLI, SDK,
and caches were removed. The relocated bundle linked the real capability
VM and both shared app sources. It carried the tracked guest placeholders.
All 79 successful-run command groups closed. An earlier `git init`
attempt retains its scratch hold after an unconfirmed group check.
The corrected guide pins Rust, checks both export inventories and the
VM symbol attribution, and distinguishes the generated iOS target from
FieldLog's native project. An offline build with an empty Cargo
directory reproduced the exact VM archive. Both guide paths resolve
their pinned inputs. Installed behavior remains unverified.
[Maintained export guide](docs/guides/fieldlog-ios-export.md#build-the-maintained-fieldlog-app-with-the-capability-vm) ·
[Relocated export receipt](verification/receipts/fieldlog-d2-combined-85e6fbe3-relocated-ios-export.json) ·
[Offline VM build](verification/receipts/l08-fieldlog-ios-vm-empty-cargo-home-6bc461f4.json)

## November 21 matching FieldLog development artifacts

The reviewed ordinary FieldLog tree `e39a5ea393` built for both platforms.
The Android development APK uses Mixer `857e4b4aa7` and contains the
reproducible Entry Commit payload. Static review verified all 41 APK
members, the ordinary launcher, the v3 certificate, all 19 aligned
arm64 libraries, and both guest signatures. Its development certificate
requires a clean install. The Apple bundle uses Mixer `6bc461f4fc` and
its own signed development payload. Static review verified all 19
FieldLog compiler inputs, the linked capability VM, and both guest
signatures. Installed Apple behavior remains pending.
[Matched artifact review](verification/receipts/fieldlog-e39a5ea3-matched-development-artifacts.json)

The exact Android APK ran on disposable API 36 arm64 emulators with
airplane mode enabled and no default network. The ordinary editor saved
a task and a draft, and signed Entry Commit persisted the draft once with
one linked outbox entry. A cold launch preserved the workspace bytes.
The Android system chooser delivered a 276-byte report with both saved
records. The separate local reader's digest matched both sender copies.
A focused task-only run verified the report bytes, Back to FieldLog,
and unchanged workspace bytes. Owned groups closed and scratch was
removed, including the emulator whose first group observation failed.
[Installed Android receipt](verification/receipts/fieldlog-e39a5ea3-857e4b4a-api36-offline-report-commit.json) ·
[Earlier attempts](verification/receipts/fieldlog-e39a5ea3-857e4b4a-offline-setup-attempts.json)

The current Pair25 guide reconstructs the FieldLog product and packaging
trees from public pins. The stock CLI prepared, exported, and validated
the Android app, then built the arm64 APK with the original preparation
path absent. All 174 source files retained their hashes. The separate
development signing replay built Java and JNI from a moved projection,
verified the reproducible Entry Commit payload, and checked a fresh APK
signature and both guest signatures. These newly built APKs passed
static readback.
[Pair25 recipe](tests/integration/fieldlog-pair25-android/README.md) ·
[Stock Android export](verification/receipts/fieldlog-e39a5ea3-pair25-relocated-android-export.json) ·
[Signed clean-source build](verification/receipts/fieldlog-e39a5ea3-pair25-signed-clean-source.json)

## November 21 hosted v76 verification

Identity Network and Intel Android passed at `32cd2c54b6`. Intel verified both
creates and all six consumers with terminal command custody. Phoenix admitted
all 555 sources, then stopped with one invalid test after a fixture directory
already existed. ExUnit recorded 1,026 passes and 29 skips before the final
source comparison. Swift host reproduced signal 11 in the CLI testing bundle.
The logs leave the crashing test unidentified. All 129 retained CLI command
receipts recorded terminal custody. Earlier holds remain active.
[Terminal CI receipt](verification/receipts/hosted-v76-terminal-ci-32cd2c54.json)

## November 20 hosted v73 verification

All three v73 hosted workflows passed. The Phoenix fixture kept its
attestation scratch outside the source tree and passed the final source
comparison. The macOS Intel job verified the 300-second Android policy
for both creates. All six generated Java consumers compiled, and the
command groups and owned scratch closed. The VM job ran the Guest UI v1
export-name mutation control in debug and release. [CI receipt](verification/receipts/hosted-v73-ci-6235f51c.json)

The v74 Intel run stopped during `debug-export` after rejecting a command
receipt directory. The published metadata lacks the rejected entry's mode
and owner. Custody for PID/PGID 68831 and its retained scratch is UNKNOWN.
Fresh arm64 controls reproduced a window where Foundation exposed the
directory at `0755` before applying `0700`. The local producer fix passed
the same control with `0700` at creation.
[Failure metadata and local controls](verification/receipts/hosted-v74-receipt-directory-atomicity.json)

The fresh v75 Intel job passed both create commands and all six generated Java
consumers. Both inner inspections used the 300-second runtime and 60-second
cleanup policy. All 79 outer command groups closed and the owned scratch was
removed. The Swift host job separately exited on signal 11 during CLI Swift
Testing. Its exact crashing test and overall descendant custody remain unknown.
The v74 and Swift hosted custody records remain in force.
[Intel receipt](verification/receipts/hosted-v75-intel-android-44869279038.json) ·
[Swift host diagnosis](verification/receipts/swift-cli-host-sig11-v75-44869279038.json)

The one-off Swift Testing diagnostic reproduced signal 11 in serial mode on
macOS 15.8.2 with Xcode 26.3 and Swift 6.2.4. The crash report matches the
test bundle UUID. The crashing thread reached Foundation's URL path decoder
from the malformed-NUL fixture in `ownedCommandControlSchedules()`.
Default scheduling did not run. The diagnostic's retained scratch and
unconfirmed descendants remain under its UNKNOWN custody record.
[Exact hosted diagnostic](verification/receipts/swift-cli-host-serial-crash-44876481949.json)

The corrected receipt test constructs encoded file URLs. The normal local
CLI suite passed on Xcode 27.2 with 132 Swift Testing passes and 32 XCTest
passes plus one skip. The five outer commands and all 200 recorded fixture
commands confirmed terminal custody, and the owned scratch was removed.
The installed CLI archive verifies the corrected test and restores the
predecessor bytes. Its 153-source digest and the hosted v77 selection
still match their pins. A supplemental Android runner test left an
unconfirmed child and retained its exact scratch under HOLD.
[Local CLI replay](verification/receipts/swift-cli-receipt-fixture-full-host-v77.json) ·
[Archive verification](verification/receipts/installed-cli-source141-owned-command-test-r1.json)

All nine Owned Engine jobs passed on `9d6adeee8b`. On hosted Xcode 26.3
and Swift 6.2.4, the corrected fixture passed under default scheduling
along with all 132 Swift Testing tests. The later signed startup checks,
generic iOS Simulator build, both Guest UI C clients, and all six Intel
Android consumers passed.
[Hosted verification](verification/receipts/owned-engine-ci-9d6adeee.json)

## November 21 FieldLog pending changes

The compact signed Pending Changes fixture rendered 26 real disk-backed
records across two pages. Six actions completed and returning from Tasks
preserved the page cursor. The observer counted four storage reads and
zero write attempts. Both owners retired, and cold reopen matched the
workspace bytes. V1 still refuses the exact historical navigation layout.
The offscreen macOS result leaves F10 and the two-target OTA count open.
[F10 replay](verification/receipts/fieldlog-f10-signed-pending-queue-v80.json)

The reviewed headless V3 replay delivered the six historical actions from
decoded events and scoped page bytes. All 26 records kept their navigation,
list, and section hierarchy, and returning from Tasks restored page two.
The repository reopened byte-for-byte unchanged after three reads and
zero writes. V1 refused the navigation frame and cleared the display.
[Headless route verification](verification/receipts/fieldlog-f10-historical-queue-v81-feature-ui-v3-review-fix.json)


An offline ARM64 API 36 emulator installed the standalone opt-in Pending
Changes APK. All six native taps reached their expected screens. The two
pages displayed all 26 ordered fixture rows. Tasks preserved page two,
and a fresh process returned to page one with the same bundled bytes.
The first APK lacked the descriptor at the stock renderer's asset path.
Adding the byte-identical descriptor there fixed startup. The passing
installation preserved every original APK member. The app observed the
actionable frame in memory. Signed Wasm activation and durable health on
Android remain pending. Both private ADB and emulator groups closed,
and the four attempts removed their scratch.
[Standalone Android replay](verification/receipts/fieldlog-f10-android-standalone-api36-c9ad5431.json)

The signed development APK and packet bytes matched their pins on the
offline Android emulator. The private V3 signed-envelope parser refused the
Android scope before the initial frame. That scope parser still selects
macOS for every UI schema 3. Independent review also found that the
draw listener can report a frame before Android renders it. Both findings
are open. The disposable emulator, private ADB and signing scratch closed.
[Signed Android scope refusal](verification/receipts/fieldlog-f10-signed-android-api36-scope-refusal-6b07f0da.json)

The reviewed signed Android successor checks the exact development scope
for UI schema 3. It sampled the committed hardware buffer at the content
interior and removed the default title that covered the native button.
Revision 2 stayed provisional for the observation window. A genuine tap
delivered the native envelope, drew revision 3 and displayed all 20 rows
in the signed guest's first page. Durable health recorded both milestones
with one scoped read and zero writes. Back retired the owner, preserved
the healthy candidate and left the fixture workspace byte-identical.
The first clean install stopped after the loading draw. The same signed
APK and packet passed on a fresh emulator. Its exact startup failure
cause remains unresolved. All owned build, signing and emulator scratch
closed. This advances F10's installed Android signed first page.
[Signed Android first-page replay](verification/receipts/fieldlog-f10-signed-android-api36-c83466ac.json)

On the exact same signed API 36 APK, changing only the manifest signature
and changing only the assignment signature each produced an Ed25519
refusal. Neither attempt committed a frame or advanced the accepted
sequence. Recovery and workspace bytes held. Restoring the exact packet
on the same install produced the provisional frame, a genuine native
tap, and durable health with all 20 first-page rows. Both refused owners
and the successful owner retired. All 172 commands, the disposable
emulator and private ADB reached terminal custody.
[Installed Android signature refusals](verification/receipts/fieldlog-f10-signed-android-api36-envelope-refusals-c83466ac.json)

The signed navigation candidate `4cdc06c2` reproduced the six-action
host route on the exact historical workspace. The APK reused 21 members
from the installed first-page witness and rebuilt DEX and JNI. Independent
review found two blockers. The Swift owner stopped on Previous from the
first visit to page 2. Java refused direct Tasks or Entries from page 1.
Those actions were enabled. The candidate is unsigned and held from
installation while both paths are corrected.
[Navigation review](verification/receipts/fieldlog-f10-signed-android-navigation-review-4cdc06c2.json)

The `7ef3f06d` correction passed those navigation choices in the host
controls. Independent review found that the real workspace actor still
refused the fourth legitimate read. It also found that the source
retained the previous Wasm pin. The unsigned packager bound the new pin
in its build copy. Both findings carried forward to the next source revision.
[Follow-up navigation review](verification/receipts/fieldlog-f10-signed-android-navigation-review-7ef3f06d.json)

The `6c5bc8ca` source binds the corrected Wasm and admits alternating
reads through the real workspace actor. Independent replay reproduced
the prior fourth-read refusal and verified all seven reads on the
successor. Three fresh API 36 installs of the same signed APK passed
the six-action route, direct Tasks and repeated pagination, and direct
Entries from page 1. The six-action route rendered 20, 6, 6, and 20
exact rows before Entries. All three committed health after the first
native tap, preserved the original 13,207 workspace bytes, and retired
the owner. All 408 device commands and owned services closed.
[Installed signed F10 navigation](verification/receipts/fieldlog-f10-signed-android-navigation-api36-6c5bc8ca.json)

On the same signed `6c5bc8ca` APK, single-bit changes to the manifest and
assignment signatures each failed Ed25519 verification. Neither attempt
committed a frame or advanced the accepted sequence. Restoring the
original packet on the same install passed all six native actions and
preserved the workspace bytes. All 206 commands closed and all three
ports were reusable. The notice audit found zero of the 12 required
entries in this private APK.
[Installed F10 signature refusals](verification/receipts/fieldlog-f10-signed-android-api36-envelope-refusals-6c5bc8ca.json)

The notice-only F10 successor adds 12 exact Pair25 entries. All 23
inherited APK members matched the historical install byte for byte.
The signed development successor kept the same guest packet and reached
Entries at revision 8 in six actions on API 36. The workspace bytes and
healthy candidate matched the prior replay. The signing keys, emulator,
private ADB, and scratch were removed.
[Noticed APK and installed replay](verification/receipts/fieldlog-f10-signed-android-notices-api36-6c5bc8ca.json)

The private F10 VM linked into a generic arm64 iOS Simulator XCTest
bundle. The default bundle linked V1 validation and omitted the F10
entry points. Exact patch replay and reversal matched both Git trees.
Signed iOS scope, V3 presentation, and installed navigation remain
pending.
[Apple VM link witness](verification/receipts/fieldlog-f10-ios-simulator-ecba9fa-vm.json)

The private signed iOS F10 owner at `3010d91c` passed the macOS
scope and event-order checks with the exact guest and synthetic workspace
pages. The host required revision 2 acknowledgement before input and
revision 3 acknowledgement before durable health. Navigation reached
revision 8 with zero writes. The private and default V1 generic arm64
Simulator test bundles linked. Root verified the reversible source patch
and recovered the exact historical workspace bytes. Installed UIKit
acknowledgement, native taps, and cold recovery remain pending.
[Signed Apple F10 source and build](verification/receipts/fieldlog-f10-ios-simulator-signed-consumer-ecba9fa.json)

The exact historical workspace and Wasm are now in a generic arm64
Simulator XCTest archive. The macOS control matched all 26 rows and
six actions through revision 8. It retained the healthy candidate
when reopening the store and made zero workspace writes. Root matched
both source patches, the archive, the linked selector, and its resources.
Native taps and UIKit display acknowledgement remain pending.
[iOS historical F10 witness](verification/receipts/fieldlog-f10-ios-native-tap-3010d91c.json)

The successor XCTest terminates the app after all six taps and Done,
then requires a new PID and launch ID with the same installation and
healthy candidate. The generic arm64 build passed. In an independent
macOS replay, two processes loaded the same recovery store. The cold
process received no new Wasm or assignment and recovered the original
sequence and candidate. All 13,207 workspace bytes matched. The
development trust expires at 08:17:49 UTC on November 22, 2026.
Native taps, UIKit display acknowledgement, and iOS relaunch remain pending.
[iOS F10 process relaunch witness](verification/receipts/fieldlog-f10-ios-native-process-relaunch-03378356.json)

The private macOS signed V3 candidate `6ba7034329` passed the first-page
Pending Changes smoke through the installed owner, VM, and storage mailbox.
One read hydrated the queue. The decoded action delivered the historical
navigation and list frame with the first 20 IDs and exact UTF-8 labels.
The attempt retired, zero writes were attempted, and cold reopen matched
the workspace bytes. Wrong and mixed identities were refused. The smoke
inherits the stale baseline capability fingerprint for installed admission.
Independent review found that caller-reported milestones could establish
health before observed presentation and that the bridge lacked a successful
hydration requirement. Native display, later pages, and the two-target
signed OTA count remain open. An earlier replay
scratch remains held because its process-group custody is unknown.
[Candidate smoke receipt](verification/receipts/fieldlog-f10-macos-signed-smoke.json)

The reviewed correction requires an observed actionable frame for durable
health and an exact posted, found queue response for hydration. The signed
macOS run kept failed, missing, wrong-request, and retired outcomes inert.
The good path hydrated one read, wrote nothing, and reopened the workspace
byte for byte. The pinned replay closed all 30 command groups. The 33-file
correction has a local composition at `dda816101e`. A fresh replay
re-signed for that exact source and VM archive. It confirmed provisional
health until presentation, all five inert response outcomes, and the V1
Commit, W09, and ordinary milestone controls. All 30 recorded groups closed.
The Source141 successor keeps 155 source inputs and the historical
fingerprint and archives intact. Both workflow projections admitted the
binding, and the normal and optimized sparse checks passed 16 tests each
on the local composition.
[Corrected V3 receipt](verification/receipts/fieldlog-f10-v3-observed-admission-macos.json) ·
[Exact composed replay](verification/receipts/fieldlog-f10-v3-root-dda81610.json) ·
[Source141 binding](verification/receipts/source141-private-f10-dda81610.json)

All nine hosted jobs passed on exact published `2acaac6760`. Source141
admitted the same 155 inputs in both preflights and postflight. The ordinary
build kept private F10 disabled and passed signed Commit and W09 tests.
Intel passed all six Java cross-compiles. The opt-in replay remains
separate local evidence.
[Published F10 CI receipt](verification/receipts/hosted-private-f10-ci-terminal-2acaac67.json)

All nine Owned Engine jobs passed on published `55b4d634d3`, including
Swift Host, the Swift aggregate, and Android generated Java. The push
triggered only Owned Engine checks.
[Terminal CI receipt](verification/receipts/hosted-restore-evidence-ci-terminal-55b4d634.json)

The next compiler and FieldLog evidence checkpoint `e99446de27` also passed
all nine Owned Engine jobs. That push triggered only Owned Engine checks.
[Terminal FieldLog evidence CI receipt](verification/receipts/hosted-fieldlog-evidence-ci-terminal-e99446de.json)

All nine Owned Engine jobs passed on published `9efad204c5`. Source141
matched all 155 inputs before and after the Swift Host run. Signed Commit
and W09 passed with private F10 disabled. Intel passed all six Java
cross-compiles. Phoenix and Identity did not trigger on this revision.
[Restore and Swift reproducibility CI receipt](verification/receipts/hosted-restore-swift-reproducibility-ci-terminal-9efad204.json)

All nine jobs passed on the published signed editor checkpoint
`1ef43cbb7b`. Source141 matched the same 157 inputs in both preflights
and postflight. Swift 6.2.4 passed ordinary V1, signed Commit, and W09
checks. CI kept the private editor and F10 disabled. Intel passed all
six Java cross-compiles. Phoenix and Identity did not trigger.
[Signed editor terminal CI receipt](verification/receipts/hosted-signed-editor-source141-ci-terminal-1ef43cbb.json)

The published closure and restore checkpoint `abfefec8e9` passed all
nine Owned Engine jobs. Source141 matched the 157-input digest in both
preflights and postflight. The ordinary signed V1, W09, and Commit
regressions passed. Intel passed six Java cross-compiles. The opt-in
allocator replay retains its separate local runtime receipt.
[Closure and restore terminal CI receipt](verification/receipts/hosted-closure-and-restore-ci-terminal-abfefec8.json)

The published FieldLog build checkpoint `5fd075d6df` passed all nine
Owned Engine jobs. Source141 matched the 157-input digest. Swift passed
ordinary signed V1, W09, and Commit, and Intel passed six Java
cross-compiles with all 100 reviewed command groups closed. Independent
review verified the ten archive digests. Phoenix and Identity did not
trigger. The local allocator and FieldLog runtime evidence retain their
separate scope.
[Matched-build terminal CI receipt](verification/receipts/hosted-fieldlog-allocator-ci-terminal-5fd075d6.json)

The published builder and export checkpoint `98ef14202e` passed eight
Owned Engine jobs. Both Intel sparse-checkout suites passed 16 tests,
but their reported times totaled 370.699 seconds against a six-minute
step budget. The six-consumer integration was skipped, and terminal
Intel process custody is unverified. The sparse test inputs and workflow
match the previous green commit. Independent review identified the
materialized-checkout test as the largest contributor to the slowdown.
Source141, signed Swift, VM, and Services checks passed.
[Builder and export terminal CI receipt](verification/receipts/hosted-fieldlog-builder-ci-terminal-98ef1420.json)

The subsequent checkpoint `c00f33e747` passed eight of nine jobs. Both
Intel sparse suites passed and the step succeeded. The later bootstrap
stopped after 20.206 seconds when the Swift Android SDK download returned
`curl` status 28. No consumer build began. All nine recorded bootstrap
commands reached terminal custody, and the receipt records scratch removal.
The other jobs passed, and independent review verified all eight uploaded
archive digests.
[Macro checkpoint terminal CI receipt](verification/receipts/owned-engine-c00f33e7-terminal-ci.json)

The Intel sparse step now allows nine minutes. Both sparse suites, the
six-consumer integration, and the 70-minute job cap retain their previous
settings. A reversible Source141 successor seals the prior workflow bytes.
Independent review verified both workflow sparse projections, both Python
modes, exact predecessor restoration, and tamper refusals. The composed
checkout also passed all 16 sparse controls per mode and admitted the same
157 source inputs. The exact `d7ab346ec8` push passed all nine hosted jobs.
The Intel SDK download succeeded, all six consumers cross-compiled, and
their DEX hashes matched. The job refused all 12 tamper cases before
staging and recorded terminal custody for 13 bootstrap and 79 integration
commands. The earlier timeout and download failure retain separate receipts.
[Timeout and Source141 verification](verification/receipts/android-sparse-checkout-timeout-c00f33e7.json)
[Exact hosted run](verification/receipts/owned-engine-d7ab346e-terminal-ci.json)

The subsequent reproducible Entry Commit checkpoint `857e4b4aa7` passed
all nine Owned Engine jobs. Intel compiled all six variants and produced
DEX identical to the prior run. All 100 Intel bootstrap, integration,
and nested command receipts recorded terminal custody. Independent
review verified all ten uploaded archive digests. Hosted selections
remained at 157 Source141 and 571 Services inputs.
[Terminal CI receipt](verification/receipts/owned-engine-857e4b4a-terminal-ci.json)

The six-action private V3 candidate `790d0b2253` delivered Open, Next,
Tasks, reopen, Previous, and Entries through the signed guest. Its two
pages displayed 26 real pending records from three scoped reads. The
workspace reopened byte-for-byte, with zero writes. Pagination kept the
previous page visible and input busy until the matching found response.
Entries stopped at the historical handoff. All 34 replay groups closed.
Review found that a paging read expiring during admission could leave input
busy after the mailbox acknowledged its cancellation. Automated
cybersecurity screening stopped the delegated correction. The candidate
remains open. Native display and installed OTA remain open.
[Six-action replay](verification/receipts/fieldlog-f10-v3-signed-six-actions-2acaac67.json)

The app-owned storage guide exercises the public installed storage adapter.
The signed host fixture committed one scoped write, refused an out-of-scope
write before repository entry, and read the saved bytes through a fresh
repository instance in the same process. The primary test and four focused
cases passed. The existing visible AppKit case compiled and was outside
the selection. The guide retains scratch when retirement is unconfirmed.
[Authoring guide](capabilities/app-owned-storage.md) ·
[Signed storage receipt](verification/receipts/w09-app-owned-storage.json)

## November 21 FieldLog signed entry Commit

The reviewed FieldLog Commit runtime now has a local v82 stock SDK
binding. The CLI archive validates 155 inputs and reconstructs the
previous 154-input roster and its predecessors. The combined stock CLI
built and reported the exact AppKit dependency cause from an independent
SwiftPM description. Both exact native sparse projections passed in each
Python mode. The ten signed macOS tests passed on the same reviewed runtime
and test bytes. Installed mobile verification remains open. An
earlier timed-out Intel attempt retains its exact scratch because
descendant custody is unverified.
[Source141 binding](verification/receipts/fieldlog-commit-v82-source141.json) ·
[Composed native admission](verification/receipts/fieldlog-commit-v82-composed-native-admission.json) ·
[Stock CLI composition](verification/receipts/fieldlog-commit-v82-stock-cli-composition.json) ·
[Signed host results](verification/receipts/fieldlog-v81-signed-runtime-composition.json)

On published `dbb9275d58`, Swift Host and Swift Capability Native failed
their generated identity and native preimage checks. The checked fingerprint
describes 17 inputs. The two changed SDK capability files and the added
Commit continuation yield a different fingerprint across 18 inputs.
The capability schema preimage is unchanged.
[Hosted failure and exact preimage comparison](verification/receipts/hosted-v82-followup-native-identity-drift-dbb9275d.json)

The reviewed refresh binds the 18 inputs across generated identities,
linked admission, test material, and Source141. The composed generator
and three native preimage controls passed, including optimized Python
for the controls. Source141 admitted 155 inputs in both Python modes,
and independent review restored both earlier archives. The author ran
22 linked macOS tests, including six signed FieldLog and W09 controls.
All 53 Pair25 input pins matched. An app rebuilt with the new linked
fingerprint needs updated installed identity and freshly signed release
and assignment material. Hosted verification of the refresh is pending.
[Fingerprint and archive receipt](verification/receipts/native-capability-fingerprint-dbb9275d58.json)

On hosted `6bc461f4fc`, Swift Host passed the generated capability step
and Swift Capability Native passed all three native preimage controls.
The latter then stopped while Swift 6.2.4 type-checked the signed guest
test fixture. The fixture correction emits byte-identical Wasm for
all nine modes and both additional scope controls on local Swift 6.3.3.
The exact Swift 6.2.4 capability job passed on `55f3ccf17c`. XCTest
reported 142 passes, five skips, and zero failures. Signed W09 storage and
retirement, one-use Commit, wrong-action and malformed-event denial,
and the invalid-frame storage controls all ran and passed. All nine jobs
passed, including Swift Host, the hosted VM, Services, and the six
generated Java cross-compiles.
[Fixture comparison](verification/receipts/hosted-swift-62-signed-fixture-byte-assembly.json) ·
[Terminal hosted verification](verification/receipts/hosted-swift-62-fixture-ci-terminal-55f3ccf1.json)

The exact fingerprint run finished with eight passing jobs. The Swift Host
and aggregate, VM, Services, and Intel six-consumer cross-compiles passed.
The sole failure was the Swift 6.2.4 fixture compilation in Swift Capability
Native. The newer fixture-only run is verifying that correction.
[Terminal fingerprint run](verification/receipts/hosted-v82-fingerprint-ci-terminal-6bc461f4.json)

The corrected signed guest displays Commit refused when the repository
declines a write. The macOS replay preserved workspace and outbox bytes and
joined the host owner after Done. The matching development APK passed
signature, alignment, and exact embedded payload checks. The first owned
ADB setup stopped before emulator launch and closed. The second stopped
before APK installation after the private ADB connection timed out.
Emulator PID and PGID 44098 had unconfirmed closure at startup.
A later user-authorized check found no matching processes and confirmed
the group had already exited. The startup scratch remains preserved.
[APK verification](verification/receipts/fieldlog-android-entry-commit-candidate-e1903e78.json) ·
[Original startup hold](verification/receipts/fieldlog-entry-commit-api36-startup-hold.json) ·
[Group absence receipt](verification/receipts/fieldlog-entry-commit-api36-pgid-44098-resolution.json)

A private ADB loopback test reproduced the five-second connect timeout while
the server still answered its version request. Its inert peer had accepted
TCP and received the ADB handshake request. The isolated probe cleaned up.
The held emulator's completed startup stage remains unknown.
[ADB loopback diagnosis](verification/receipts/fieldlog-entry-commit-api36-adb-loopback-diagnosis.json)

A fresh arm64 API 36 emulator reached boot and installed the exact
`85e6fbe362` development APK. The launch command used the activity's
Java package as the application ID and exited 1 before editor input.
Static APK readback identifies the correct component as
`dev.fieldlog.generatedr90/dev.fieldlog.generatedr90.androidhost.PublicActivity`.
The private ADB server and all 25 boot, install, and preflight commands
closed. The emulator child exited 0, and group 75289 remained unconfirmed
at teardown. A later user-authorized observation found the PID and group
absent. Both kernel checks returned `ESRCH`. No termination signal was sent.
The historical scratch and exact three ports were left untouched.
[Fresh launch and custody receipt](verification/receipts/fieldlog-entry-editor-fresh-api36-launch-hold.json) ·
[Group absence receipt](verification/receipts/fieldlog-entry-editor-api36-pgid-75289-resolution.json)

The reviewed `e39a5ea393` FieldLog APK installed on a clean arm64 API 36
emulator. The installed launcher matched the manifest's application ID and
fully qualified activity. The ordinary editor showed the unsaved title, and
force-stop and cold launch preserved the original workspace bytes. After
closing the keyboard, Save added exactly one task and one linked
`taskSaved` record. The queue showed the task first and viewing it left
disk unchanged. Cold launch preserved the task and outbox.

From Entries, Save draft persisted one draft without an outbox append.
Opening the signed sequence-1 dialog and choosing Done preserved that draft
byte for byte. Reopening and choosing Commit showed **Committed once**,
replaced the draft with the matching entry, and added exactly one
`entrySaved` record. Done dismissed the dialog. A third cold launch
preserved the exact committed bytes and the earlier task. Input used
ADB-generated key events. Unicode through the system keyboard and internal
guest-owner retirement telemetry remain outside this run. Both service groups
and all 113 commands reached terminal custody, and the three ports rebound
before the disposable AVD was removed.
[Installed editor and signed Commit receipt](verification/receipts/fieldlog-e39a5ea3-api36-ordinary-signed-entry-commit.json)

A separate clean API 36 install of the same APK completed checklist row
20, moved it to rank 21, and moved it back to rank 20 through the ordinary
UI. The view moved to page 2 and back to page 1. Row 20 kept its completed
state, and the last row's **Move down** button was disabled. The workspace
advanced three revisions and appended one `taskSaved` and two
`taskOrderChanged` records. Cold reopen and queue viewing preserved the
exact workspace bytes. The 22 tasks were synthetic fixture data.
[Installed checklist result](verification/receipts/fieldlog-e39a5ea3-api36-checklist-page-boundary.json)

On another clean install, an Android test IME sent a composing candidate
and replaced it with a two-line note containing a decomposed accent and an
emoji. The IME refused the Title field and a repeated commit request.
Save draft preserved the exact note bytes through a cold launch. The
signed Entry Commit displayed **Committed once**, saved the draft under
the same record ID, and appended one `entrySaved` record. The final cold
launch preserved the workspace bytes. The original keyboard was restored,
the test IME was uninstalled, and both disposable emulator campaigns
recorded terminal process groups and reusable ports before removing their
scratch.
[Installed Unicode note result](verification/receipts/fieldlog-e39a5ea3-api36-unicode-note-signed-commit.json)

The same APK selected a synthetic PNG through Android DocumentsUI. Photo
selection saved the previously unsaved title and one attachment in a single
draft revision. A cold launch restored the complete draft. Signed Entry
Commit kept the draft ID and attachment reference and appended one
`entrySaved` record. A second cold launch preserved the workspace bytes and
the JPEG's SHA-256. The 96 × 96 stored JPEG decoded successfully. The test
recorded 84 terminal command groups, three listener rebinds, and removal of
the disposable emulator scratch.
[Installed photo and signed Commit receipt](verification/receipts/fieldlog-e39a5ea3-api36-photo-signed-entry-commit.json)

## November 20 local release delivery outage and recovery

A committed Phoenix release reached local Workerd through the private historical
export and the PostgreSQL pointer fence. Workerd served the exact offer and
both allowlisted artifacts while PostgreSQL was stopped. Renewal was refused.
The lease expired with HTTP 204 for offers and 404 for both artifacts. After
verified TLS recovery, a late permit left the pointer unchanged. An ambiguous
acknowledgement was reconciled to exactly one pointer advance. A signed halt
refused stale authority and a stale pointer ETag. L05 remains in progress.
[Cross-runtime replay](verification/receipts/l05-delivery-cross-runtime-20261120.json)
· [First outage proof](verification/receipts/l05-delivery-cross-runtime-first-outage-20261120.json)

Separate PostgreSQL protocol controls reproduced COMMIT acknowledgement loss
and generic rollback after the CAS. The corrected fence reported indeterminate
in both cases and preserved certain conflict and pre-CAS unavailable.
[COMMIT acknowledgement controls](verification/receipts/l05-delivery-fence-commit-ack-20261120.json)

## November 21 stock attestation privacy

The stock loopback API attached a synthetic V2 envelope, returned the original
result on exact replay, and refused a read-only bearer and a cross-tenant
request. PostgreSQL showed one matching row. The BEAM, Bandit, and PostgreSQL
captures contained their positive controls and zero matches for 48 synthetic
markers. The observed handler inventories had no registered exporter. Both
owned groups closed and scratch was removed. L07 remains open.
[Attestation privacy receipt](verification/receipts/l07-native-attestation-stock-log-6b9b826c.json)

## November 21 private source-map retention

The opt-in local operator retains the bytes bound to a signed publication.
It applies the earlier retention or owner authorization cutoff to transfer
and publication, rejects inherited output access, and leaves public OTA
responses byte-identical. The v81-composed macOS replay passed 21 focused
controls and the signed PostgreSQL fixture. The captured logs contained
zero synthetic payload markers. The disposable database closed and its
port rebound. Hosted v82 binds 571 source inputs, including the opt-in
migration. The full collector passed 317 tests in each Python mode under
the original 360-second alarm. L07 remains open.
[Operator guide](hosted/scripts/private-source-map-retention.md) ·
[Composed verification](verification/receipts/l07-private-source-map-v81-composition.json) ·
[v82 source admission](verification/receipts/hosted-v82-private-source-map-retention-source-admission.json)

Published v82 Phoenix passed 1,029 cases and skipped 32. The Linux
source-map fixture reached the signed owner export and received
`output_unavailable`. The corrected browser trace ran to its normal
capture limit. PostgreSQL stopped and owned scratch was removed. The
source-map export refusal is under investigation.
[Hosted failure evidence](verification/receipts/hosted-v82-phoenix-private-source-map-failure.json)

Phoenix on follow-up `dbb9275d58` reached the same assertion. The suite
again recorded 1,029 passes, one failure, and 32 skips. The signed owner
export returned `output_unavailable`. The protocol, session storage, and
migration checks passed. The foundation receipt confirms PostgreSQL stopped
and owned scratch was removed.
[Follow-up failure evidence](verification/receipts/hosted-v82-followup-phoenix-dbb9275d.json)

Hosted v82 Identity Network stopped during the first Git blob collection,
before creating any containers or running either network method. The
exact request and a complete local readback matched all 571 pinned blobs.
The framed response grew from 8,382,516 bytes on v81 to 8,501,053 bytes
on v82, exceeding the existing 8 MiB per-command limit. The finalizer
verified cleanup. The corrected collector reproduced every framed byte in
two bounded reads. The exact composed Services run passed all 321
collector tests in each Python mode. On the published follow-up
`dbb9275d58`, both bounded reads completed and both isolated network
methods passed without skips. The before and after manifests matched.
The finalizer confirmed absence of all three owned containers and removal
of owned scratch.
[Exact overflow evidence](verification/receipts/hosted-v82-identity-source-batch-overflow.json) ·
[Batching verification](verification/receipts/hosted-v82-batched-services-collector.json) ·
[Hosted follow-up](verification/receipts/hosted-v82-followup-identity-dbb9275d.json)

Published v82 Owned Engine passed all nine jobs. Both Swift Host source
checks matched the 154-input archive, and Intel compiled all six Java
consumers with terminal receipts. Services passed all 317 collector
tests in each Python mode and the Go checks. Phoenix passed the 12
private-login and 10 ordinary catalog cases before the source-map suite
failure. The initial v82 Identity run stopped before either method.
[Exact hosted results](verification/receipts/hosted-v82-terminal-e1202816.json)

On follow-up `dbb9275d58`, Owned Engine finished with six successful jobs
and three failures. The two Swift preflight failures came from the native
fingerprint drift, and the Swift aggregate failed. Intel passed all six
consumer builds, with byte-identical DEX. Services passed 321 collector
tests per mode and all Go checks. Hosted signed FieldLog regressions did
not run in the failed Swift jobs.
[Owned Engine follow-up](verification/receipts/hosted-v82-followup-owned-engine-dbb9275d.json)

## November 21 attestation readiness

The ordinary application-registration and native-attestation fixtures now use
separate evidence directories. The original order reproduces the v76
`:eexist` failure, and both corrected tests pass together. Browser startup and
writer admission also verify the two exact owner row policies and require
effective SELECT and INSERT independently. Revoking either grant closed both
admission paths before a write. Restoring the grants let the stock signer
attach and replay with one row. [Readiness receipt](verification/receipts/l05-native-attestation-owner-admission-v77.json)

Hosted v77 source admission passed across all five sparse projections in
normal and optimized Python. The full local Phoenix replay reached the
concurrent build-create check, where one request hit a PostgreSQL lock timeout
and returned 503. The focused rerun passed the concurrency and browser
admission checks and reached the final unchanged-source comparison. The
separate attachment database suite was skipped by this runner.
[Sparse replay](verification/receipts/hosted-v77-owner-privilege-source-admission.json) ·
[Local Phoenix replay](verification/receipts/hosted-v77-local-phoenix-composition.json)

Hosted Phoenix passed 1,027 tests with 32 skipped, including the concurrent
build replay and the attestation browser catalog fixture. The final source
comparison passed and PostgreSQL stopped. Hosted Identity Network passed all
316 collector checks and both production-path methods, with successful owned
resource finalization.
[Phoenix job](https://github.com/snowdamiz/mixer/actions/runs/44876481915/job/136762184228) ·
[Identity Network job](https://github.com/snowdamiz/mixer/actions/runs/44876482058/job/136762184762)

## November 20 local development attestation attachment

The stock Go signer signed a retained iOS Simulator build completion, then
submitted the exact V2 envelope twice to ordinary loopback Phoenix. The
API returned attached and duplicate, and PostgreSQL kept one byte-exact
attachment to the settled worker operation. The API starts a separate
restricted TLS pool for the optional writer. The composed host replay
passed 159 focused tests and the Workerd outage replay. The signer used
synthetic retained products and identities.
[Composition receipt](verification/receipts/l05-w11-w12-composed-v74-5a3c6dd0.json)

The November 21 managed replay completed one generic iOS Simulator-target
Xcode build, with no Simulator boot. The restricted worker settled the original
job and authenticated reads matched all three retained products. The
attestation wrapper did not start because the runner passed integer port
arguments to the launcher. The runner exited 74 and preserved both scratch
roots and the Phoenix and PostgreSQL processes under custody hold. A focused
control reproduced the launch failure and passed after both arguments were
converted to decimal text.
[Build and launch hold](verification/receipts/l05-managed-ios-attestation-wrapper-launch-hold-20261121.json)

A fresh managed replay settled one build and used the stock Go signer to
attach the V2 development envelope to that exact worker operation. Phoenix
returned 201 and 200 on exact replay. PostgreSQL kept one byte-identical
envelope, with an unchanged journal. All 36 outer command groups closed,
all five ports were reusable, and both fresh scratch roots were removed.
The earlier custody hold remains active. L05 and W12 remain open.
[Managed stock attachment receipt](verification/receipts/l05-managed-ios-stock-attestation-20261121.json)

## November 20 signed release queue

The opt-in Phoenix queue commits a signed publication, the release head, and
one Oban job in the same PostgreSQL transaction. Exact retries added no jobs.
The updater served the committed release while the processor was stopped. A
denied enqueue and a deferred commit failure preserved the prior release.

The restricted processor wrote three byte-exact projections. The fixture
recovered an abandoned job that already had a projection and a discarded job
that had exhausted its attempts. The administrator retried the discarded job
without changing its ID. The maintained runner passed all 27 selected tests
and the packaged-release checks. The final independent review passed the
processor grant correction. The earlier transient browser-head 503 remains
unexplained. [Hosted replay](verification/receipts/l05-w11-release-jobs-final-admission-0f191753.json)

Hosted v67 admitted 483 source paths in five sparse projections and restored
v66 and v65 byte-for-byte with their original modes. Dual-platform environment
promotion and delivery through a control-plane database outage remain open.
[Source binding](verification/receipts/hosted-source-binding-v67-0f191753.json)

Hosted v68 adds the release processor to the three standalone startup
compile rosters. All 35 startup controls passed locally. The collector
fixtures now restore each adjacent predecessor. All 316 tests passed in
both Python modes in real Identity and Verify services sparse checkouts.
The 483-path v68 selection restores exact v67 and v66 bytes and modes.
[Startup controls](verification/receipts/hosted-v67-startup-roster-29aeb806.json) · [Source binding](verification/receipts/hosted-source-binding-v68-29aeb806.json) · [Collector replay](verification/receipts/hosted-v68-collector-ci-repair-89e9be3f.json)

All three GitHub workflows passed on the exact v68 repair. [Hosted CI](verification/receipts/hosted-v68-main-ci-ed6ea631.json)

## November 20 local environment promotion

Hosted v69 adds exact target enrollment and commits both platform
publications, one promotion binding, and both queue jobs in one database
transaction. A deferred failure leaves the destination heads and queue
unchanged. The 495-path source selection restores the previous 483-path
selection with its original bytes and modes. [Authority replay](verification/receipts/w11-stage-promotion-authority-e5b3a977.json) · [v69 source admission](verification/receipts/w11-stage-core-v69-composed.json)

Hosted v70 connects the generated stock Swift command to the ordinary
loopback Phoenix endpoint. The runtime loader resolves all four enrolled
targets. The stock CLI promoted and replayed both exact signed assignments
against the PostgreSQL fixture. All 26 selected hosted checks and five
Swift contract checks passed. The installed app and database-outage
delivery proofs remain open. [Stock replay](verification/receipts/w11-stock-stage-promotion-configured-302b3ac1.json) · [v70 source admission](verification/receipts/w11-stock-v70-source-admission.json)

The authenticated console now labels an environment promotion separately
from a rollout expansion. The live PostgreSQL replay committed and displayed
the staging iOS head at sequence 3 and Android at sequence 12. The existing
summary and detail views retain their response behavior. The console reads
each exact target independently, so it reports the promotion group as
unavailable. Independent review passed the parser, focused console tests,
and production build. [Console promotion replay](verification/receipts/console-staged-release-head-v77.json)

The opt-in group view reads both committed destination receipts and their
current heads in one PostgreSQL statement. The live console retained
Android's original sequence 12 and displayed its advanced head at 13.
Independent review passed the request and client controls. The exact
composed root replay passed all seven Bandit/PostgreSQL tests, preserved
449 source inputs, stopped PostgreSQL, and removed scratch. Hosted v78
Phoenix and Identity Network passed.
[Group replay](verification/receipts/console-exact-stage-promotion-group.json) ·
[Root verification](verification/receipts/console-promotion-group-root-v79.json)

The v78 Services job admitted all 555 sources. Its normal collector test
then reached the six-minute process alarm during a predecessor control.
The optimized collector and Go race suite did not start. The separate
Identity job passed all 316 tests in 244.383 seconds. Descendant custody
for the interrupted Services worker remains unverified.
[Services timeout](verification/receipts/hosted-v78-services-collector-alarm-814c7218.json) Replaying the exact v78 Go module on arm64 macOS passed module verification, vet, and the full race suite.

The v79 Services collector reuses imports only for the same resolved sparse
checkout and matching import inputs. An independent regression reproduced
the wrong-checkout reuse on the parent and verified the correction. All 317
checks passed locally in 167.0 seconds in normal mode and
269.5 seconds with optimization. Both runs admitted the
same 558 hosted paths under the original six-minute collector limit, left
the sparse source unchanged, and removed owned scratch.
[Services replay](verification/receipts/hosted-v79-services-collector-final.json)

All three hosted v79 workflows passed at `34a165c878`. Phoenix ran 1,027
tests with 32 skips and verified the unchanged 435-file archive. Identity
Network passed both configured production-path methods. Services ran all 317
checks in each Python mode in about 205 seconds, then passed Go module
verification, vet, and race tests. Owned Engine passed all nine jobs, including
both creates and six Intel Android Java consumers.
[Hosted v79 receipt](verification/receipts/hosted-v79-terminal-34a165c8.json)

Hosted v80 pins the four reviewed console files and the author receipt for
saved promotion links. The author reopened the same iOS sequence 3 and
Android sequence 12 records after both release heads advanced. Root passed
313 console tests and the production build. All five workflow sparse
checkouts passed focused controls with and without Python optimization.
Exact source and workflow preimages recover v79 and v78. The installed CLI
still validates 154 inputs, and the ordinary migration inventory remains at 27.
The full collector exposed two historical corruption fixtures that skipped v79
while restoring v78. After correcting that hop, all 317 tests passed locally
in 146.8 seconds in normal Python and 152.1 seconds with optimization.
Both exact sparse runs admitted 559 source inputs, preserved their checkouts,
and closed their owned scratch.
[Corrected Services replay](verification/receipts/hosted-v80-services-collector-final.json)
[Source admission](verification/receipts/hosted-v80-console-promotion-history-source-admission.json) ·
[Console composition](verification/receipts/console-promotion-history-v80-composition.json) ·
[Phoenix fixture replay](verification/receipts/console-promotion-v80-composed-phoenix.json)

All three hosted v80 workflows passed at `5f4277e12e`. Phoenix passed 1,027
tests with 32 skips and compared all 435 archived inputs. Identity Network
passed both methods and verified removal of the three owned containers.
Services passed 317 tests in each Python mode and passed Go module, vet, and
race checks. Owned Engine passed all nine jobs, including both creates and
all six Intel Android consumers.
[Hosted v80 receipt](verification/receipts/hosted-v80-terminal-5f4277e1.json)

The published evidence follow-up at `9c21d3edb4` passed all nine Owned
Engine jobs. Intel compiled all six Java consumers and recorded terminal
custody for the two creates and their recorded commands. Hosted activation
skipped the signed Swift trap case because the input modules were absent.
The corrected local guide supplied the modules and passed all three signed
tests with Xcode 27.2. It refuses a changed index and stops on an existing
output path before it can reuse a prior archive.
[Owned Engine receipt](verification/receipts/owned-engine-v80-evidence-9c21d3ed.json) ·
[Swift recipe verification](verification/receipts/w15-signed-swift-public-recipe.json)

The reviewed local promotion-link continuation resumes the canonical saved
record after ordinary sign-in. The rendered fixture returned iOS receipt 3
and Android receipt 12 with heads at 4 and 13. A background organization-list
request returned HTTP 503 while the exact promotion request returned 200.
The cause of the 503 remains open. The composed console passed all 319 tests
and its production build. Hosted v81 admits 561 exact sources and restores
the v80 and v79 source and workflow bytes. The full collector passed all
317 tests in each Python mode in 173.1 seconds against the unchanged
360-second alarm. Both owned checkouts and scratch were removed.
[Browser receipt](verification/receipts/console-promotion-sign-in-resume-v80.json) ·
[Composition receipt](verification/receipts/console-promotion-sign-in-composition-v81.json) ·
[Source admission](verification/receipts/hosted-v81-console-promotion-sign-in-resume-source-admission.json) ·
[Collector replay](verification/receipts/hosted-v81-services-collector-final.json)

Published v81 passed Identity Network and the Services job. The hosted
activation job passed the W09 signed storage test. Swift Host and Intel
Android stopped at the predecessor Source141 test binding, before the
two Android creates and six Java consumers. Phoenix stopped while
registering the browser trace because its targets predated the sign-in
intent. The corrected macOS fixture observed both current targets and
passed all 12 selected tests with the CI Node drivers. The combined v82
and W09 Source141 binding passed both exact native sparse projections,
including all 45 bootstrap and 16 sparse controls per Python mode. The
154 CLI inputs and the restored Source141 and Source127 archives matched
their pinned identities. The cause of the earlier organization-list
503 remains open.
[Terminal CI receipt](verification/receipts/hosted-v81-terminal-abb32b83.json) ·
[Trace repair](verification/receipts/hosted-v81-phoenix-trace-arity.json) ·
[Combined admission](verification/receipts/hosted-v82-combined-source-and-native-admission.json)

The v80 restore fixture observed PostgreSQL reject the injected queue
operation at COMMIT with SQLSTATE `PZ080`. The failed request preserved
the scoped ledger. Retrying the same request succeeded. After a restore
into a distinct cluster, a fresh authorized browser session could read
either platform's original promotion receipt, and another tenant received
404 for both selectors. The replay driver was retired after two corrected
attempts stopped at application startup. The authority test covers restored
reads. The two subsequent attempts retain scratch because Bandit port
reuse was unverified.
[Historical evidence](verification/receipts/l05-l07-v80-stage-promotion-restore.json) ·
[Replay retirement](verification/receipts/l05-l07-v80-stage-promotion-restore-replay-retirement.json)

At `2acaac676`, a fresh restored PostgreSQL 17.11 cluster accepted a
normal signed two-platform promotion through Phoenix. Staging advanced from
3 to 4 on iOS and from 12 to 13 on Android. Post-exit SQL readback found
two artifact-bound publications, one paired promotion record, and one new
durable queue job per platform. The exact retry returned the same HTTP 200
bytes without adding rows or jobs. Both earlier selectors kept their
original receipts. The SQL comparison covers the selected ledger values.
Independent review matched the executed fixture hashes and confirmed the
normal signed endpoint, restored role, and append and retry assertions.
The runtime receipt covers synthetic signing and loopback services with
queue consumers idle. The author verified terminal closure and rebound all
eight recorded listener ports before removing scratch. L05 and L07 remain
running.
[Runtime receipt](verification/receipts/l05-l07-restored-stage-promotion-2acaac67.json) ·
[Executed test overlay](verification/receipts/l05-l07-restored-stage-promotion-2acaac67-overlay.patch) ·
[Historical command record](verification/receipts/l05-l07-restored-stage-promotion-2acaac67-commands.md)

The first restored release-worker replay stopped at source Phoenix startup.
PostgreSQL opened on a private Unix socket, and `LifecycleRepo` rejected the
fixture's `socket_dir` option before connecting. A separate executable
control confirmed that the pool admits the existing hostname, port, and
password options. All owned groups closed and three listeners could rebind.
The next fixture uses SCRAM authentication on IPv4 loopback. Restore, queue
drain, and signed delivery remain open for this replay.
[Startup failure and option control](verification/receipts/l05-l07-restored-release-worker-55b4d634.json) ·
[Historical test afterimages](verification/receipts/l05-l07-restored-release-worker-55b4d634-afterimages.patch)

The SCRAM follow-up restored the database into a distinct cluster and
accepted a signed promotion to iOS sequence 4 and Android sequence 13.
The initial ACL comparison stopped on seven owner-only table ACLs that
PostgreSQL restored as defaults. The effective privileges matched, so
the replay continued on the same cluster with the restored grants.

The restricted Oban release processor completed all eight jobs on their
first attempt and created one projection per publication. After the
processor stopped and Phoenix restarted, both staging targets returned
HTTP 200 for their signed offers and artifacts. The signed assignments,
manifests, and payloads matched the committed records. Exact retry and
readback left the compared rows and jobs unchanged. The author confirmed
all owned groups closed, rebound ten listeners, and removed scratch.
Independent review passed the restore, worker, and delivery result. The
captured runner is historical. Inert controls found that a timeout can leave
a child unreaped and that interruption during PostgreSQL launch can leave
the child unregistered. Operational verification uses the stock service
commands in the restore guide. L05 and L07 remain running.
[Restore and delivery receipt](verification/receipts/l05-l07-restored-release-worker-scram-55b4d634.json) ·
[Historical SCRAM test patch](verification/receipts/l05-l07-restored-release-worker-scram-55b4d634-delta.patch) ·
[Historical ACL continuation](verification/receipts/l05-l07-restored-release-worker-scram-55b4d634-acl-continuation.patch) ·
[Restore operator checks](docs/operations/restore-local-hosted.md#check-release-worker-and-delivery)

The stock CLI rolled back both staging targets after a separate fresh
SCRAM-authenticated PostgreSQL restore at `9efad204c5`. iOS advanced
from 4 to 5 and Android from 13 to 14. Both assignments pointed back to
their original artifacts. Exact signed retries returned byte-identical
CLI receipts and added no rows or jobs. The restricted release worker
completed one rollback job and one projection per target. After the API
restarted, ordinary delivery verified both signed assignments, manifests,
and payloads. The original promotion receipts stayed readable. Delivery
reads preserved the measured state. The local fixture used synthetic
identity and no billing dependency.

Independent review matched the exact overlay and the ordinary CLI
dispatch. The author recorded 35 supervised groups closed, 10 ports
rebound, and scratch removed. The runner remains historical because a
logging failure after launch could prevent its custody check. Client
activation, L05, and L07 remain open.
[Rollback receipt](verification/receipts/d6-l05-l07-restored-stock-rollback-9efad204.json) · [Executed fixture overlay](verification/receipts/d6-l05-l07-restored-stock-rollback-9efad204-overlay.patch)

The separate Swift updater run at `5fd075d6df` activated signed sequences 1
and 2 from Phoenix and rejected exact replays with unchanged recovery files.
The first restored rollback returned HTTP 422 before baseline validation.
After validation was added, the rollback returned HTTP 503 because the
ordinary writer lacked the fixture's `INSERT(action)` column grant.
[Initial run](verification/receipts/d6-l04-l05-swift-restored-phoenix-5fd075d6.json) ·
[Validated run](verification/receipts/d6-l04-l05-swift-restored-phoenix-5fd075d6-corrected.json)

With the documented grant present before the dump, the distinct SCRAM
restore retained forced row-level security and the grant. The stock CLI
committed sequence 3, its exact retry preserved the SQL snapshot, and the
restricted worker created one matching projection. The restarted API's
first offer returned HTTP 503. Later read-only SQL under the delivery role
returned the exact signed assignment and baseline artifact. The HTTP
cause, sequence-3 Swift activation, and fresh-process offline recovery
remain open. The run recorded 56 closed groups, ten listener rebinds, and
scratch removal. Static verification matched the source manifest and all
ten overlay files.
[Grant and delivery observations](verification/receipts/d6-l04-l05-swift-restored-phoenix-5fd075d6-action-grant.json) ·
[Historical fixture overlay](verification/receipts/d6-l04-l05-swift-restored-phoenix-5fd075d6.patch)

A fresh instrumented follow-up reproduced the first HTTP 503 after the
restored API restarted. The delivery pool had no available connection and
queueing was disabled. PostgreSQL never received the query. The same pool
reported a ready connection about 1.2 ms after startup returned. The
subsequent read-only diagnostic matched the exact sequence-3 assignment and
payload under the restricted delivery role. The campaign sent no HTTP retry.
The Swift workspace retained sequence 2, leaving sequence-3 activation and
fresh-process offline recovery open. All 74 recorded groups closed and 14
listeners could rebind.
[Readiness diagnostic](verification/receipts/d6-l04-l05-swift-restored-phoenix-5fd075d6-delivery-readiness.json) ·
[Test-only observation patch](verification/receipts/d6-l04-l05-swift-restored-phoenix-5fd075d6-delivery-readiness.patch)

The initial delivery admission candidate `2ade050cce` passed a full
macOS headless Swift restore replay. The first ordinary post-restart
offer returned HTTP 200 without a warm-up or retry. The Swift owner
accepted rollback sequence 3 and refused its exact replay. After the API
stopped, a fresh offline process reopened the same artifact, retained
all three signed candidate receipts and payloads, and recorded fresh
health. The fixture recorded 71 terminal command groups and nine
listener rebinds before scratch removal.

Independent review reproduced a separate existing health-halt restart
test failure. The admission child spec persisted after a successful
startup. The stalled-checkout test also left its callback waiting after
repo shutdown. The candidate remains pending correction and integration.
[Candidate restored Swift replay](verification/receipts/d6-l04-l05-swift-restored-phoenix-2ade050c.json)

The correction makes delivery admission temporary and the stalled test
releases its connection callback and waits for a normal exit. Independent
review passed the health-halt restart and browser publication selectors.
The startup query's timeout option is 5,000 ms. The pool can affect the
elapsed startup time. Ordinary requests still use fail-fast checkout.

A full replay using the corrected production files passed signed sequences
1, 2, and 3 with zero replay writes. Stock rollback and the restricted
worker each produced one durable result. The first ordinary offer after
restart returned HTTP 200, and a fresh offline Swift process recovered the
same sequence-3 candidate after the API closed. The run recorded 73 closed
command groups and nine listener rebinds.
[Startup regression receipt](verification/receipts/d6-delivery-startup-correction-2ade050c.json) ·
[Corrected Swift restore receipt](verification/receipts/d6-l04-l05-swift-restored-phoenix-corrected-6e9ed4e6.json)

Hosted v83 binds the corrected startup to 572 source inputs. Independent
review admitted the three real workflow sparse checkouts in normal and
optimized Python and restored the prior hosted selection and Source141
and Source127 byte-for-byte, including file modes. Root passed 323 normal
collector tests. The optimized suite passed 320 before its existing
360-second alarm, and the remaining three passed in a focused run.
A fresh optimized run then passed all 323 tests in one process within
the original alarm. Source141 still selects 157 inputs, and all 16 Android
sparse controls passed in both modes.
[Source binding](verification/receipts/d6-hosted-source-v83-binding.json) ·
[Root admission](verification/receipts/d6-hosted-source-v83-root-admission.json) ·
[Optimized replay](verification/receipts/d6-hosted-source-v83-optimized-rerun.json)

The exact hosted v83 push passed Owned Engine and Identity Network.
Services passed all 323 collector tests in each Python mode. Phoenix
passed the delivery startup and health-halt restart regressions. The
signed source-map export returned the same Linux refusal as v82. A
separate post-COMMIT read test returned `:not_found` before reaching
its configured delay. Both failures remain recorded.
[Hosted terminal receipt](verification/receipts/hosted-v83-terminal-866c3e80.json)

The v84 test fixture creates a private directory under canonical OS
scratch for the signed owner export. Focused macOS checks verified the
exact export bytes and cleanup after success and assertion failure.
The reviewed source packet binds the one changed test and restores v83
and v82. All three sparse workflows admitted 572 inputs, while
Source141 and Pair25 preserved their existing input sets. The exact
v84 Linux Phoenix run passed all 1,030 executed tests, including the
signed owner export. It skipped 32 tests and confirmed database
shutdown and owned scratch removal.
[Hosted owner export](verification/receipts/hosted-v84-phoenix-owner-export-3c9f6ece.json)
[Fixture verification](verification/receipts/l07-source-map-fixture-os-scratch-857e4b4a.json) ·
[v84 source binding](verification/receipts/l07-hosted-source-v84-866c3e80.json) ·
[Root admission](verification/receipts/l07-hosted-source-v84-root-admission.json)

The exact v84 push passed all 11 jobs across Phoenix, Identity Network,
and Owned Engine. Both isolated identity methods passed. Intel
cross-compiled six generated Java consumers with matching DEX bytes.
Its receipts record terminal custody for 13 bootstrap and 79
integration commands and removal of both owned scratch roots.
[Hosted v84 terminal receipt](verification/receipts/hosted-v84-terminal-3c9f6ece.json)

The v83 post-COMMIT assertion failed because its token expired 8 ms
before the first evidence query. PostgreSQL acknowledged ROLLBACK.
The corrected test requires a typed COMMIT acknowledgment before the
token expires and checks the response after crossing the expiry.
The v85 candidate-only run used disposable SCRAM PostgreSQL. The same
runtime backend committed the fresh read, the short-lived read before
expiry, and another fresh read after expiry. ExUnit passed the selected
case. Source admission matched 572 inputs in both Python modes.
[Original timing diagnosis](verification/receipts/l07-r1026-postcommit-expiry.json) ·
[Reversible v85 binding](verification/receipts/l07-r1026-v85-composition.json) ·
[Candidate-only replay](verification/receipts/l07-r1026-v85-root-replay.json)

The exact hosted v85 push passed all 11 jobs. Linux Phoenix recorded
1,030 passes and 32 skips. The corrected R1026 test observed PostgreSQL
acknowledge COMMIT before token expiry and rejected the response after
expiry. The signed owner export passed again. Identity passed both
isolated network methods. Intel cross-compiled all six Java consumers.
[Hosted v85 terminal receipt](verification/receipts/hosted-v85-terminal-1e2de013.json)

Phoenix is pinned to 1.8.17, the upstream fix for GHSA-pvfx-rx4x-phrr
and GHSA-5vmc-qgf8-rw36. The private Hex audit reported zero findings
after the update. The ordinary Mixer endpoint uses Plug HTTP routes.
Source inspection found no Channel or Presence entry point. The
PG16 and PG17 relation manifests bind the new dependency lock.
Test and production compilation and loopback GET and HEAD passed.
Hosted v86 admits the exact updated inputs and preserves v85, Source141
and Source127 restoration.
[Dependency and source verification](verification/receipts/hosted-phoenix-1.8.17.json)

The exact updated hosted subtree also passed the focused R1026
assertion on PostgreSQL 17.11 with SCRAM. The same restricted backend
acknowledged the live reads before and after expiry, and the late
response was refused. All ten recorded commands closed. PostgreSQL
exited cleanly, its loopback port rebound, and scratch was removed.
[Database replay](verification/receipts/hosted-phoenix-1.8.17-scram-r1026.json)

The combined v86 source selection also binds the completed Pair25
browser runner. All three non-cone workflow checkouts admitted the 572
inputs in normal and optimized Python. Focused refusal checks and
Source141 and Source127 restoration passed. The full local collector
runs reached their time limits. Hosted Phoenix and Identity passed on v86.
The Engine run passed eight jobs, including six Intel Java and D8
consumers. The Swift cache fixture passed before its artifact upload
timed out. All 11 jobs passed on v87. The Intel receipts for both
revisions record terminal custody and scratch removal.
[Terminal hosted evidence](verification/receipts/hosted-v86-v87-terminal-551576a0-92ae77bc.json)
[Combined source binding](verification/receipts/hosted-phoenix-v86-pair25-integration.json)

## November 21 FieldLog Android exit readback

The relocated Pair25 development APK opened the same FieldLog workspace
after a separate data restore. The original app saved one entry and a
draft with a DocumentsUI JPEG. The exported build opened the draft on its
first offline launch, showed the saved entry, and listed the same two
pending changes. The workspace and JPEG matched the backup byte for byte
after the queue read. Both private process groups closed, the three
ports were reusable, and scratch was removed. This run used separate
development certificates and a fresh install in one disposable API 36
emulator.
[Installed exit receipt](verification/receipts/fieldlog-e39a5ea3-relocated-android-workspace-readback.json)

## November 21 FieldLog Android draft save with retained focus

Both the relocated Pair25 development APK and the current camera and
queue APK opened the same synthetic draft and seven JPEGs offline.
After typing in Note and hiding the keyboard with Back, Save draft
triggered `unsupportedNativeOperation` in the native renderer. The
surface retired and the repository stayed at revision 8 with identical
workspace bytes. The earlier export restore and camera and queue
results still cover their recorded actions. The first boot attempt
stopped at the emulator userdata space check. All four attempts closed
their owned groups, released the private ports, and removed scratch.
[Installed save refusal](verification/receipts/fieldlog-android-focused-draft-save-20261121.json)

The reviewed correction keeps the signed Entry Commit button present
and disabled while the ordinary editor saves. On the corrected API 36
APK, Note retained focus after Back and both Save draft and Commit
entry reached disk once. The draft and committed entry reused the
same ID and seven JPEGs. The commit appended one outbox event.
Separate cold launches confirmed exact saved and committed bytes.
The first run committed successfully but stopped at the entry-row
locator. Both runs closed their groups and removed scratch.
[Correction and installed verification](verification/receipts/fieldlog-android-focused-entry-save-installed-114e9820.json)

## November 21 FieldLog release-origin restart

The stock loopback Go service delivered the exact Pair24 sequence-1
offer and artifact. Its port refused connections after shutdown. A fresh
process reopened the same store and served identical bytes, then delivered
the signed sequence-2 correction. Each publication added one audit event
and outbox row. Exact retries did not write. Both origin groups closed,
the port was reusable, and scratch was removed. [Host replay](verification/receipts/l08-android-release-outage-host-d89c742e9d.json)

The installed API 36 app then activated the same sequence 1. With the
Go origin stopped and its port refusing TCP, a fresh app process
reopened the healthy cached release. The ordinary editor saved a note
and a second cold launch read back the same bytes. The restarted origin
served the known baseline and then sequence 2. The same install activated
the correction and retained the note, outbox, and JPEG. All 174 commands
closed. Both Go groups, private ADB, and the emulator retired. The reverse
mapping was removed, the ports rebound, and the scratch was removed.
[Installed outage receipt](verification/receipts/l08-android-installed-release-origin-outage-d89c742e.json)

A separate installed replay mapped the app's release port to local
Workerd and ran stock Go on a different port. Workerd served the
signed baseline after Go stopped. When the lease expired, Workerd
returned no offer and refused the expired artifact. The app kept its
healthy candidate. During the Workerd cut, Go remained healthy while
the app cold-reopened sequence 1 and saved an ordinary note edit.
Workerd reopened on the same port and delivered sequence 2. The app
retained the draft, JPEG, and outbox. All owned host and device
groups closed, the listed ports were reusable, and scratch was removed.
[Installed Workerd replay](verification/receipts/l08-android-installed-workerd-outage-d3b23e0d.json) · [Host controls](verification/receipts/l08-android-workerd-control-plane-boundary-d3b23e0d.json)

## November 21 installed Android update refusals

The Pair24 Android API 36 replay exercised 15 stages on one development
install. FieldLog kept sequence 1 healthy after offers for a different
app, environment, or runtime and after the size, truncation, malformed
envelope, replay, and altered digest cases. The accepted sequence
advanced to 9 and 11 for two payload refusals while sequence 1 stayed
healthy. A valid sequence 12 activated later and reopened offline.
Every stage preserved the saved draft, workspace, outbox, and JPEG.
The checker matched the installed journal and all 24 loopback exchanges.
All 474 command groups closed, the four fixture ports were reusable,
and scratch was removed. The corresponding iOS scenarios remain open.
[Installed matrix](verification/receipts/fieldlog-android-227-228-installed-95b9b959.json) ·
[Fixture inputs](verification/receipts/fieldlog-android-227-228-inputs-95b9b959.json) ·
[Fixture delta](verification/receipts/fieldlog-android-227-228-fixture-95b9b959.patch)

## November 21 Apple project pagination

The Apple project list shows 20 matching projects per page. It resets
to the first page on a search edit and clamps the page if the result
set shrinks. The generic arm64 iOS build passed. An independent macOS
control checked a 24-project fixture, title and site search, page ranges,
UUID navigation, and preservation of restoration state and the outbox.
Installed UI and accessibility checks remain open. The separate Android
project picker is under correction after its native renderer review.
[Apple patch](verification/receipts/fieldlog-apple-project-pagination-00406fe7.patch) ·
[Build receipt](verification/receipts/fieldlog-apple-project-pagination-00406fe7.json) ·
[Host projection check](verification/receipts/fieldlog-apple-project-pagination-host-review-00406fe7.json)

## November 21 installed Android project picker

The corrected ordinary FieldLog APK opened the North Ridge project
with Search still focused on an API 36 arm64 emulator. It paginated
23 saved projects, returned an empty search result, and distinguished
two Valve Route projects by site. Only the selected project's task,
draft, and entry labels appeared in the checked screens. Selection
advanced the workspace revision from 52 to 53 and preserved all 47
outbox records. The same APK reopened North Ridge in a fresh process.
All 118 commands closed, and the emulator, private ADB, and scratch
were removed. Prior setup and hierarchy-label failures are preserved
in the receipt. Apple installed pagination remains pending.
[Installed replay](verification/receipts/fieldlog-android-project-picker-installed-ad6c8dba.json) · [Reviewed Android patch](verification/receipts/fieldlog-android-project-picker-ad6c8dba.patch)

The API 36 emulator's Camera2 activity resolved the standard image
capture intent. Its software back camera reached native image review
after the shutter tap. The emulator and private ADB closed. FieldLog's
capture candidate then reached native image review twice from the ordinary
editor and Cancel preserved the workspace and all seven photos. Camera2
failed to open FieldLog’s output descriptor on Done, and the eighth
photo was never written. Both disposable emulators and their private ADB
servers closed, and all ports rebound. The capture candidate needs an
output correction and a fresh installed save. [Provider check](verification/receipts/fieldlog-android-api36-camera-provider-probe.json) · [Installed failure](verification/receipts/fieldlog-android-camera2-capture-refusal-29135a2f.json)

The corrected development APK supplied a background Handler to the API
36 camera output descriptor. On a fresh API 36 install, shutter and
Cancel preserved all seven existing photos and workspace bytes. Shutter
and Done persisted one 1,392 × 1,856 JPEG in the same draft, advanced
its workspace revision once, and preserved the existing photos and
outbox. Both acquisition controls disabled at eight photos. A fresh
process reopened the exact draft and JPEG. All 156 recorded commands
closed, all three ports rebound, and the disposable emulator and
scratch were removed. The emulator used the software rear camera.
[Installed replay](verification/receipts/fieldlog-android-camera-installed-api36-26bbde4a.json) · [Exact patch](verification/receipts/fieldlog-android-camera-corrected-26bbde4a.patch) · [Build receipt](verification/receipts/fieldlog-android-camera-output-api36-successor.json)

## November 21 Apple entry photo capture

The reviewed correction resizes camera and library photos off the UI
actor before JPEG encoding. The owner requires the selected draft's
queued save to succeed. The repository checks the exact selection before
publication. A known pre-publication failure removes the JPEG created
by that attempt. A failure after snapshot rename preserves the JPEG and
requires reopening the repository. Nine focused host tests, five legacy
storage tests, and the generic arm64 iPhoneOS build passed. The source
composes with the installed Android camera patch. The Android queue
continues to call the existing revision-checked transaction.
UIKit capture, permission prompts, and combined Android runtime checks
remain pending.
[Source composition](verification/receipts/fieldlog-ios-entry-camera-composition-e10048f8.json) · [Exact patch](verification/receipts/fieldlog-ios-entry-camera-corrected-e10048f8.patch) · [Build and test receipt](verification/receipts/fieldlog-ios-camera-corrected-15fa8e9b.json)

## November 21 FieldLog site-map model

The shared model saves an optional project pin and keeps a foreground
position in the map session. Both FieldLog model copies match. The
independent host replay verified save, clear, cold reopen, and stale
write refusals. Legacy workspaces opened with the same bytes. A separate
rebuild reproduced the bundled Natural Earth linework byte for byte.
Native map UI and foreground permission tests remain pending. The Apple
integration must wait for the committed selected project before allowing
a pin write. The review observed a source race between the navigation
state and the queued restoration write.
[Shared patch](verification/receipts/fieldlog-site-map-shared-26bbde4a.patch) · [Producer receipt](verification/receipts/fieldlog-site-map-shared-26bbde4a.json) · [Independent review](verification/receipts/fieldlog-site-map-shared-review-23150c6a.json)

The standalone Android map rendered offline on API 36. The manual
pin save touched only the selected project and workspace revision.
The system permission prompt handled denial and grant. Emulated GPS
drew a separate blue marker, and backgrounding cleared the position
status. The workspace stayed byte-identical through the location
checks. A cold reopen retained the pin, and clearing it changed only
the pin and revision. Back to project left an empty dashboard with
both a manually saved pin and a preseeded one. Restart restored the
dashboard. All five runs closed their private groups and removed
scratch. [Installed Android map](verification/receipts/fieldlog-android-site-map-api36-f2184a4c.json)

The corrected combined Pair25 APK keeps the dashboard live behind
the Site Map. Warm Back returned to the same process before and after
saving a pin, with the keyboard dismissed and after backgrounding.
The accessibility-filtered hierarchy isolated the map controls.
The granted GPS fix reported direction and accuracy and left disk
bytes unchanged. Cold reopen kept the saved pin, and clearing it
advanced the revision once. Camera cancellation and queue readback
worked after dismissal. Both owned attempts removed scratch.
[Installed map and exact source delta](verification/receipts/fieldlog-android-site-map-pair25-87c95c5a-installed.json)

A second owned API 36 run on that APK granted only approximate
location and displayed the operating system's reported accuracy.
Backgrounding cleared the preview. Disabling location produced an
unavailable message, and revoking the coarse grant ended the app
process. The fresh process prompted again and kept the saved pin.
Workspace bytes and the repository file list were identical. The
sampled app log contained neither exact synthetic input coordinate.
[Installed permission lifecycle](verification/receipts/fieldlog-android-site-map-permissions-87c95c5a.json)

On the same Pair25 APK, Android's 1.3 font scale visibly enlarged
the ordinary draft editor text. A focused Save draft kept the draft
ID and changed only the note, its timestamp and workspace revision.
Cold reopen retained the note, all seven JPEGs and the one pending
queue record. Restoring 1.0 returned the original Note bounds. The
owned emulator and ADB closed, and scratch was removed.
[Installed larger-text editor](verification/receipts/fieldlog-android-large-text-entry-87c95c5a.json)

A separate replay on the same APK cancelled at 65,536 bytes, resumed
and reconciled the lost acknowledgment. SQLite held one new event
and the exact JPEG. One local outbox record retired after the retry.
The emulator, private ADB and loopback fixture closed, and scratch
was removed. The reviewed Apple camera and map patches also compose
with the Android packaging delta in either order. Both repository
copies match on the paired source tree. Installed evidence remains
bound to each tested build. [Queue and paired source receipt](verification/receipts/fieldlog-paired-site-map-7b2b98f0.json)

The reviewed iOS Site Map queues project restoration in navigation
order and checks the active map session during pin publication.
The review reproduced a late save from the earlier implementation.
With the corrected lease, Back before rename preserved the old
workspace bytes. Rename before Back preserved the pin through the
queued restoration and a cold reopen. Location stays in the map
session, and the position summary describes its relationship to the
saved pin. All 20 macOS host tests passed. The final unsigned
arm64 iPhoneOS build linked the pin publication path and verified
the bundled geometry and both permission strings. Installed UI,
accessibility, and Core Location checks remain open.
[Exact Apple map patch](verification/receipts/fieldlog-ios-site-map-rename-33398784.patch) ·
[Host replay](verification/receipts/fieldlog-ios-site-map-rename-33398784.json) ·
[iPhoneOS build](verification/receipts/fieldlog-ios-site-map-rename-7fdc4ab9-iphoneos.json)

The existing iOS Settings tab now applies saved appearance, regional
dates and a larger-text floor. Offline help and a five-field support
summary are part of the reviewed source. The loader preserves oversized
records until Reset. Two independent macOS runs passed all 22 tests,
and an unsigned generic arm64 iPhoneOS build linked the exact corrected
source. Installed behavior remains pending.
[Settings patch](verification/receipts/fieldlog-ios-settings-bounded-7b2b98f0.patch) ·
[iPhoneOS build](verification/receipts/fieldlog-ios-settings-bounded-iphoneos-build.json)

The ordinary Android dashboard now opens Settings & Help. On API 36,
Apply relaunched the Activity with Dark and Larger active and displayed
the saved-entry date in French. Cold launch retained all three values,
and Reset relaunched to the original light dashboard. The two pending
records, workspace and seven JPEGs kept their exact bytes. Diagnostics
showed only the five app and OS fields. The first two installed attempts
exposed screenshot-path and Activity-observer errors in the witness.
Both closed cleanly. The corrected replay passed with 211 terminal
commands, three reusable ports and scratch removed.
[Android Settings patch](verification/receipts/fieldlog-android-settings-elapsed-7b2b98f0.patch) ·
[API 36 Settings receipt](verification/receipts/fieldlog-android-settings-pair25-api36-ac305262.json)

The same development APK binds all twelve notices and both ELF digests
in its sealed build inputs. Independent ZIP readback matched all 51
members. APK v3 signing, 16 KiB alignment for all 19 ARM64 libraries,
and both guest signatures verified. The signing and build scratch was
removed. L02 and L07 remain running.
[Android APK build receipt](verification/receipts/fieldlog-android-settings-pair25-build-ac305262.json)

The retained Pair25 APK passed F20 ordinary pagination on API 36. The
native journey checked 23 saved drafts across pages of 20 and 3 and 43
committed entries across pages of 20, 20, and 3. Forward and reverse
navigation, opening a draft without editing, and cold reopen preserved
the recorded workspace bytes, file identity, revision, and all 46
outbox records. The first attempt stopped at the emulator console
preflight. The passing run used the exact AVD properties on a dedicated
ADB server. All 151 native driver commands and 52 outer commands closed.
[Installed F20 pagination](verification/receipts/fieldlog-f20-android-pagination-api36-ac305262.json)

The same offline Pair25 APK passed ordinary F09 across the 20-task
page boundary. A native Move up tap moved “Verify café drain” from
position 21 to 20. The workspace advanced from revision 1 to 2, kept
all 27 previous outbox entries and appended one `taskOrderChanged`
event. A new process reopened both pages with the exact committed
bytes. Independent review matched all seven page visits and twelve
checkpoints. The first attempt stopped at a driver assertion that
counted the Checklist heading as a row. Both attempts removed their
owned emulator, package, and scratch.
[Installed F09 checklist boundary](verification/receipts/fieldlog-f09-android-checklist-api36-ac305262.json)

Ordinary offline F08 completed one task and reordered its two-task
checklist. Revisions advanced from 3 to 4 and 5, with one event per
action. A new process reopened the same completed task, order, five
unsent queue rows, and exact workspace bytes. Independent review
reconstructed both post-write digests from the fixture and events.
All 153 outer and native commands closed.
[Installed F08 checklist and queue](verification/receipts/fieldlog-f08-android-checklist-api36-ac305262.json)

F12 passed on the retained offline Pair25 APK. The native date field
converted the offset leap-day input to `2024-02-29T18:15:12.125Z`.
The partial date stayed visible, and the two disabled write controls
left the exact seed intact. Save advanced the revision once with the
outbox unchanged. A new process reopened the saved UTC instant, and
one Commit advanced the revision again and appended one linked
`entrySaved`. The unrelated draft and prior outbox bytes were preserved.
Independent review accepted this ordinary emulator journey. All 210
root and native commands closed and owned scratch was removed.
[Installed F12 field-note date](verification/receipts/fieldlog-f12-android-date-api36-ac305262.json)

A fresh F12 replay verified the intermediate Tasks screen through the
native Checklist heading and the seeded task's Reopen action. Returning
to Entries kept the partial date and validation text with the same
workspace bytes and file identity. The full draft-save, cold reopen and
single Commit continued to pass. All 196 outer and native commands
closed and owned scratch was removed.
[Installed F12 Tasks navigation](verification/receipts/fieldlog-f12-android-tasks-return-api36-ac305262.json)

Ordinary offline F11 reopened a saved note on API 36. Native input
appended ASCII to the existing Unicode and multiline note. Save left
the outbox unchanged, and a new process restored the edited bytes.
One Commit appended one entry and one matching event. The disabled
repeat tap preserved the exact file, and a second cold launch reopened
the byte-identical sibling draft. The exact historical and Pair25 host
selectors passed Unicode event input and stale-action refusals.
Independent review accepted the installed slice, and all 158 native
and outer commands closed.
[Installed F11 restored note](verification/receipts/fieldlog-f11-android-restored-note-api36-ac305262.json)

The introducing revision, historical pin, and current Pair25 source
all passed both F13 selectors on macOS. Repository readback preserved
the exact 100,000-byte note and verified one linked entrySaved in the
historical control.
[F13 exact host replay](verification/receipts/fieldlog-f13-android-host-pair25-ac305262.json)

The ordinary API 36 ARM64 replay entered the exact 100,000-byte Note
through a test IME selected before FieldLog launched. The native editor
matched all bytes before Save and after a cold reopen. Save and Commit
advanced revisions 1 to 2 to 3, with one linked entrySaved at Commit.
A second new process reopened the committed entry with the same
workspace bytes. Independent review accepted attempt 11 for ordinary
local F13. The earlier IME-switch attempts left the Note empty
even for a short input, and hardware typing still worked. All 11
disposable attempts restored original IME settings, removed their
packages and scratch, and closed 1,496 setup and ADB commands.
[Installed F13 long note](verification/receipts/fieldlog-f13-android-long-note-api36-ac305262.json)

An ordinary Android F15 check sent a 100,001-byte synthetic Note through
the same focused editor. Two text queries bracketed it, and the native
field stayed empty with the workspace byte-identical. The same process
then accepted exactly 100,000 bytes. Save and Commit advanced revisions
1 to 2 to 3 and produced one linked entrySaved. Both cold reads matched
the intervening workspace snapshots. This verifies the Note input limit
on API 36 ARM64 and passed independent review. The separate projection
rollback checks remain host evidence.
[Installed F15 Note boundary](verification/receipts/fieldlog-f15-android-note-limit-api36-ac305262.json)

A same-draft API 36 control reproduced the IME switch from a working
Note connection. After switching away from the fixture IME and back,
both text queries returned null with Note still focused. Returning from
Home to the same Activity also left the fixture without an eligible
editor in a separate run with no IME switch. Tapping Note still failed
the query, and the exact workspace matched the seed. Four runs closed
all 479 commands and restored the original IME settings. The served
connection identities remain unobserved.
[Installed editor lifecycle controls](verification/receipts/l02-android-note-ime-rebind-api36-ac305262.json)

A separately signed diagnostic build traced the same two failures.
During the switch, Mixer closed the active Note connection while a
replacement was being created. Android sent extraction, surrounding
text and commit callbacks through the revoked connection. The replacement
had no handler observation. In the separate Home control the original
connection closed on window-focus loss. Android requested a new adapter
after return and Mixer refused it in IDLE. The exact foreground guard
remains unobserved. The same draft bytes survived both controls, and
all 161 commands closed.
[Installed connection lifecycle trace](verification/receipts/l02-android-note-ime-lifecycle-trace-api36-3362bf6c.json)

The readiness diagnostic identified `ownerInputSealed` on a fresh
Home return. The exact Activity and process survived, and the retained
field had regained window focus with its predecessor closed. An
explicit Note tap and hardware text still failed to produce input
at the sampled points. Persisted workspace bytes matched the seed.
All 132 commands reached terminal custody. The first refusing predicate
is known. That trace did not capture the subsequent owner publication.
[Installed Home readiness trace](verification/receipts/l02-android-note-home-owner-sealed-api36-c6ee43e1.json)

A second same-Activity Home trace observed the focus callback and
a successful synchronous focus read. Android requested a connection
while the owner drain was queued. The exact committed refresh then
published input authority, but Android made no further connection
request through the Note tap and hardware probe. The workspace stayed
unchanged and all 135 commands closed.
[Installed Home publication order](verification/receipts/l02-android-note-home-publication-order-api36-c6ee43e1.json)

A private one-shot restart recovered the Note on the same API 36 Home
journey. The exact owner refresh published input authority. Before the
Note tap, one restart opened a fresh adapter on the same Editable.
The fixture IME read the field, committed the exact synthetic value,
and read it back through the new adapter. The same runner failed on
the diagnostic baseline. Both arms kept their Activity, process, and
workspace. All 130 baseline and 137 candidate commands reached terminal
custody. Public SDK adoption and the separate IME switch remain open.
[Installed Home restart A/B](verification/receipts/l02-android-note-home-restart-api36-c6ee43e1.json)

Independent review of the diagnostic found missing ownership for a
reused drain, reuse of an earlier native close, and a platform exception
outside owner cleanup. The product-only candidate ties the close and
drain to the same stop and resume episode and routes restart failures
through the owner. Its 22 host cases passed. A separate API 36 run on
the DEX-only signed build read, edited, and read back the exact Note
after Home. It kept the same Activity, process and workspace bytes.
All 130 commands closed. This candidate has no queue trace, and public
source adoption remains pending.
[Installed product-only Home correction](verification/receipts/l02-android-note-home-product-api36-ccb5221c.json)

A separate host review reproduced loss of recovery after two equivalent
sealed requests and verified the coalescing correction. The same signed
product APK then had mixed API 36 results. The first run returned
wrongEditor after Home. The second read, edited, and read back the Note
exactly. Both kept their Activity, process and workspace and removed
scratch after terminal custody. Native callback order remains unobserved.
[Coalesced Home replay](verification/receipts/l02-android-note-home-coalesced-api36-39966a15.json)

Both instrumented Home runs observed the same successful order on
offline API 36 ARM64. Window focus loss closed the exact old connection
before Activity stop. On return, a sealed Note create marked the
pending drain. That drain published input authority, and one restart
opened a fresh connection on the same field. The fixture IME read,
edited, and read back the exact value. Both runs kept their Activity,
PID, and workspace bytes and verified cleanup. The earlier wrongEditor
result did not recur, so the failing order and public adoption remain
open.
[Instrumented Home callback order](verification/receipts/l02-android-note-home-order-api36-48df9b48.json)

Two Java host schedules reproduced loss of automatic recovery. Taking
window visibility away before focus closed the old connection before
the owner could record it. A create before the resume drain bound
cleared the pending recovery. Both schedules committed a new
presentation with zero restarts. An explicit later create on the same
field and Editable handled the exact edit once. Neither schedule was
observed in the two instrumented Home runs.
A separate unforced API 36 control returned to the same Activity
without a Note tap or IME switch. One restart recovered exact input,
and the workspace stayed unchanged. All 127 commands closed.
[Alternate Home callback orders](verification/receipts/l02-android-note-home-alternate-orders-host-48df9b48.json)

A one-shot decor visibility callback after pause closed the exact
predecessor before window-focus loss on API 36 ARM64. The same
Activity and field regained visibility and focus. The first create
was refused while input was sealed, the owner committed a presentation,
and no restart or later create followed. The untouched fixture IME
returned wrongEditor and the workspace stayed unchanged. All 122
commands closed. The run reproduced the failure under the selected
order. The intermittent unforced failure still has no causal trace.
[Selected visibility-first Android run](verification/receipts/l02-android-note-home-visibility-first-api36-94775102.json)

The private successor passed the same selected API 36 callback
order. The first create was refused while sealed, then committed
publication led to one restart and one fresh connection on the same
Editable. The untouched Note accepted and read back the exact text.
Activity, PID and workspace bytes stayed stable, and all 132 commands
closed. SDK adoption and the create-before-drain host case remain open.
[Visibility-first successor replay](verification/receipts/l02-android-note-visibility-first-successor-api36-6dda69d9.json)

Independent review passed the three-file Note recovery patch. Its clean
development APK passed two API 36 Home returns without a Note tap.
Both preserved Activity, process and workspace bytes and accepted the
exact IME edit. All 125 and 131 commands closed. No forced callback or
diagnostic hooks were present.
[Clean Note Home replay](verification/receipts/l02-android-note-product-clean-home-api36-613fb3c1.json)

The Pair26 review branch binds the same three Java sources and updates
the hosted source inventory to v89. The clean Android bootstrap passed
45 tests in each Python mode, and the focused Swift run passed 27.
Both installed source verifiers passed in both modes. The local
historical cutover unittest timed out. CI found a collector fixture
still using the v89 path for a v88 preimage. The corrected control
passed in both Python modes on the services sparse projection.
CI for the correction is pending.
[Pair26 and hosted source receipt](verification/receipts/android-source-pair26-hosted-v89-adoption-926f6d94.json)

The IME-switch experiment withheld an overlapping connection and posted
a public restart after the exact predecessor closed. Android briefly
received a new SDK adapter, then closed it after another overlapping
create. Both post-switch queries failed and the Note stayed empty. All
157 installed commands reached terminal custody. The SDK still needs a
handoff that survives repeated speculative creation.
[Installed restart experiment](verification/receipts/l02-android-note-ime-restart-experiment-api36-c6ee43e1.json)

The staged-adapter experiment passed the same-focus IME switch on API
36 ARM64. The baseline still forwarded both reads and the IME edit to
a revoked predecessor. The successor kept the same field and Editable,
armed the exact round after the predecessor closed, and carried the
selected adapter through reflow. That adapter handled the queries and
one exact commit. The Activity, process, and workspace were preserved
within each arm. All 113 baseline and 122 candidate commands closed.
The overlay remains private pending source review and SDK integration.
[Installed staged IME rebind A/B](verification/receipts/l02-android-note-ime-staged-rebind-api36-c6ee43e1.json)

Independent host review found that a selection change after the old
adapter closes can leave the served staged adapter refusing input. It
also reproduced a false zero from a valid first caps query. The
installed switch remains scoped evidence. The production correction
must preserve stale-metadata refusal, recover the active field, and
admit a valid caps query through the same authority check.

On API 36 ARM64 the fixture IME queried caps at its first Note bind
after switching away and back. The previous staged APK returned zero.
The product successor returned the expected 0x1000, then both variants
read, edited, and read back the same Note without changing workspace
bytes. Both runs removed the disposable packages and closed all 169
and 140 commands, respectively. Independent host review found a separate
argument-validation issue before staged activation. SDK adoption is open.
[Installed first caps query A/B](verification/receipts/l02-android-note-ime-caps-api36-39966a15.json)

The historical F04 reducer selector and the exact Pair25 Apple owner
host replay passed the tested save boundary. A held save refused new
edits, Cancel, and a second Save. A recoverable read denial preserved
the input and the same editor retried successfully. An interruption
before rename preserved workspace bytes and input, but the repository
refused retry until reopened. The fresh editor then required re-entering
both fields. Independent replay confirmed the remaining retry defect.
This is macOS owner and repository evidence.
[F04 task save and recovery](verification/receipts/fieldlog-f04-ordinary-pair25-ccb5221c.json)

With the original lock held, the next F04 candidate let the same
editor retry after the pre-rename error. Cold readback found exactly
one task, one revision increment, and one outbox event. Independent
review also found that a retry can publish if the original workspace
lock is displaced after the first error. The source remains private
until retry admission and publication recheck ownership.
[F04 same-editor retry host replay](verification/receipts/fieldlog-f04-same-editor-retry-pair25.json)

The follow-up checked lock identity at retry admission and just before
rename. It blocked both earlier displacement cases, and the same
editor still saved the retained task once with the original lock.
Independent macOS review found a remaining race between the last
check and rename. The stale repository committed one task and outbox
event while a second descriptor held the replacement lock. FieldLog
needs to serialize publication with supported ownership changes before
downstream adoption. The exact candidate compiled and linked as an
unsigned generic arm64 iPhoneOS Debug app.
[F04 lock lifecycle and review](verification/receipts/fieldlog-f04-lock-follow-up-pair25.json)

An experimental directory descriptor lock prevented a second patched
repository from opening after replacement of the inner lock file.
The original retry persisted one revision, task, and event. Replacing
the whole directory bypassed the experiment, and path-based cleanup
left a temporary file inside the moved test directory. The fixture
removed all disposable files. The result supports one-directory
mutual exclusion on macOS, with production adoption still open.
[F04 directory lock control](verification/receipts/fieldlog-f04-pair25-directory-lock-macos.json)

A private follow-up held a per-workspace lease outside the replaceable
directory and bound writes and cleanup to the open directory. The macOS
replay refused a competing patched owner across both displacement cases
and let a separate workspace commit. Replacement bytes stayed intact,
with no temporary files left. The same-editor retry and all six
uncertainty cases passed. Late external displacement can still leave a
commit on the original inode before fencing. Mixed-version displacement
and native runtime behavior remain outside this evidence. The same
candidate compiled into both Android storage configurations and linked
as an unsigned generic iPhoneOS app. Independent review returned no
result. Adoption remains open.
[F04 stable workspace lease](verification/receipts/fieldlog-f04-stable-workspace-lease-pair25.json)

All four F14–F16 selectors passed on the historical and Pair25
sources. F14 wrote one entry and one event after a valid edit-and-commit
batch and preserved editor, frame, and disk state on refusal. F15
rejected both over-contract projections before a durable write. F16
injected close cancellation after save admission. The save reached disk
and a new app instance in the same process acquired the real repository
lock. Independent review repeated the four Pair25 selectors. The
surface was synthetic, and the F16 test did not force write overlap.
[Editor transaction host replay](verification/receipts/fieldlog-f14-f16-pair25-host-bb6a1999.json)

The ordinary Android F16 background run tapped Save draft, waited
250 ms, and sent Home. The STOPPED Activity kept the same PID, and
the first post-input snapshot showed one saved revision, an unchanged
peer draft and no new entries or outbox events. A new PID displayed
the exact saved draft and reopened identical workspace bytes. The
immediate-input runs sampled no saved revision. One confirmed that
Home stopped the Activity despite a parser whitespace mismatch.
Independent review accepted the paced installed scope. The installed
checks leave save/close overlap unobserved.
[Installed F16 background and cold readback](verification/receipts/fieldlog-f16-android-save-home-api36-ac305262.json)

A separate macOS XCTest held an admitted real repository write before
rename. Close reached the save drain and was cancelled. A fresh process
saw the original snapshot and a busy lock. After release, rename and
directory sync completed before close returned. A different process
acquired the real lock and read one new revision while the original
host stayed alive. The synthetic Android surface leaves JNI and device
overlap unverified. The passing scratch closed. A separate preparation
observer error left unknown custody, with the exact path preserved in
the receipt.
[F16 admitted write and cancelled close](verification/receipts/fieldlog-f16-close-write-overlap-pair25.json)

The independent F16 reviewer found that the original lock probes could
inherit the parent's lock descriptor. A stdio-only control reproduced
the busy and reopen results. Root applied the close-on-exec spawn flag
and explicit reporting descriptors to the fixture and reran all three
XCTest cases. The held write and cancelled close reached the same
order, a distinct PID acquired the released lock, all 27 groups closed,
and fresh scratch was removed.
[F16 stdio-only lock probes](verification/receipts/fieldlog-f16-close-write-overlap-stdio-pair25.json)

All five F17–F19 selectors passed on the historical and Pair25 sources.
The macOS host replays covered photo refusal, preserved draft edits,
cold storage readback, write-fault rollback, and report descriptor
ownership. The exact installed APK previously preserved seven seeded
JPEGs and completed the report chooser handoff.
[Photo and report host replay](verification/receipts/fieldlog-f17-f19-pair25-host-5f922bd6.json)

The ordinary offline API 36 ARM64 replay used the system DocumentsUI
picker. Android Back preserved both unsaved edits and the exact
workspace with zero photos. A second picker visit attached the
synthetic image as one 96×96 JPEG to the same edited draft, with no
outbox change. A new process reopened the identical draft and JPEG.
One Commit appended a linked entrySaved at revision 3 and preserved
the JPEG. Independent review accepted the installed scope. All 204
commands and both services closed, and the scoped
package, fixture files and disposable scratch were removed.
[Installed F17/F18 picker and attachment](verification/receipts/fieldlog-f17-f18-android-picker-api36-ac305262.json)

The installed F19 report replay delivered one 325-byte saved-project
report to a permissionless recipient through the Android chooser.
The recipient held the distinct provider cache descriptor with no reads
while the driver atomically replaced the synthetic repository export.
The same descriptor read the original report and closed. FieldLog
returned to the same project and process with the workspace, outbox and
two JPEGs unchanged. The first run verified the swap and stopped at an
all-caps button lookup. The test recipient's inset and button correction
passed on a fresh run. All 146 commands closed and scratch was removed.
[Installed F19 report descriptor](verification/receipts/fieldlog-f19-android-report-descriptor-api36-ac305262.json)

A fresh offline API 36 install of the same APK ran the bundled signed
Entry Commit. It moved the draft under the original ID, appended one
entrySaved record and retained seven JPEGs. After cold reopen, Android's
report chooser returned to the same project. Settings explained the live
handoff and disabled Apply and Reset. A new app process cleared the hold
and enabled Reset. The workspace and JPEGs stayed byte-identical after
commit. All 190 commands and both services closed, all three ports
rebound, and scratch was removed.
[Installed signed Commit and report handoff](verification/receipts/fieldlog-android-signed-commit-report-settings-ac305262.json)

The exact ordinary Pair25 APK completed a fresh offline signed Commit
with its normal recovery journal. Ready and Committed once shared the
same runtime fingerprint, candidate, launch, and durable first-screen
milestone. Commit wrote one entrySaved event and preserved the original
draft ID and seven JPEGs. Done cleared the attempt with effects_closed
in the same app process. The next process read the same healthy recovery
bytes and workspace. All 215 commands closed. The graphics sample did
not identify the exact buffer behind first-screen health.
[Ordinary Pair25 activation and retirement](verification/receipts/l07-fieldlog-ordinary-pair25-commit-trace-ac305262.json)

The historical GuestFrame called the display witness after dispatchDraw
and two animation callbacks. FieldLog tree `807c198c` requires a hardware
frame commit and exact PixelCopy readback from the current dialog. The
independent review reproduced the early witness in the baseline and
matched the corrected DEX across separate builds.
[Display source readback](verification/receipts/l07-fieldlog-ordinary-pair25-display-source-9c2d665c.json) ·
[Corrected source and producer review](verification/receipts/fieldlog-ordinary-frame-commit-admission-807c198c.json)

The corrected signed APK recorded both health milestones before the
native Commit tap on an offline ARM64 API 36 emulator. The active
launch, sequence, and runtime matched. Commit appended one entrySaved
record and preserved the original draft ID and seven JPEGs. Done
retired that owner in the same process. The offline cold process read
the exact retained journal and workspace bytes. The rebuilt JNI hash
differs from the predecessor and was sealed with the corrected DEX
and all 12 notices. Both disposable emulator sessions closed and their
ports were reusable.
[Corrected installed Entry Commit](verification/receipts/l07-fieldlog-ordinary-frame-commit-api36-807c198c.json)

A separate offline run of the current APK selected an independent
reader in Android’s report chooser. The reader received all 280 bytes
and matched the saved export by SHA-256. Back returned to the same
FieldLog process and project with the workspace, seven JPEGs and both
pending records intact. All 131 commands closed, both owned services
ended, all three ports rebound and scratch was removed.
[Cross-app report receipt](verification/receipts/fieldlog-android-pair25-separate-report-ac305262.json)

All nine Owned Engine jobs passed on the Settings evidence revision
`1e1cda5284` and the signed Commit evidence revision `f6cc4ae0c2`.
[Settings checkpoint](https://github.com/snowdamiz/mixer/actions/runs/44971812161) ·
[Signed Commit checkpoint](https://github.com/snowdamiz/mixer/actions/runs/44972270468)

The same APK created an ordinary task offline with the assignee field
still focused. Save recorded exactly one taskSaved event. The selected
project, original queue, draft, and all seven JPEGs survived. A fresh
app process rendered the new task from the exact saved workspace.
[Installed task creation baseline](verification/receipts/fieldlog-android-saved-task-predecessor-ac305262.json)

The ordinary saved-task editor passed on an owned API 36 arm64 emulator
with the signed Pair25 tree `e14b6189`. Cancel preserved the separate
new-task draft. Cancel and a whitespace-only title save preserved the
workspace bytes. A changed save kept the task ID, added one
`taskSaved` event, and reopened offline with the original draft and
all seven JPEGs. The pinned V4 replay also passed Edit, Cancel, and
Save with pending text changes in the same batch. The emulator and
private ADB server closed, and their ports were reusable.
[Installed saved-task editor](verification/receipts/fieldlog-android-saved-task-edit-api36-e14b6189.json) ·
[Focused renderer replay](verification/receipts/fieldlog-android-saved-task-renderer-568793c0.json)

A follow-up used that same development APK through saved-task editing,
the native Site Map, Camera2 and the pending queue. The pin save added
one revision and the warm map return kept the same process. The eighth
JPEG persisted with the other seven, the saved draft and all three
pending records. Both photo controls stayed disabled after cold launch.
All 402 commands and both device services closed, and scratch was removed.
[Installed task, map, camera and queue replay](verification/receipts/fieldlog-android-saved-task-cross-flow-e14b6189.json)

On the owned offline API 36 emulator, a genuine notification-shade tap
opened the exact saved task, including its assignee. The warm tap
preserved an unsaved editor title. After process death, a fresh process
opened the same task. Three stale routes showed unavailable. These cases
preserved every byte of the workspace and its 47 outbox records. A
separate explicit Activity launch left a blank screen while the existing
workspace owner was alive. A fresh replay with the normal launcher
action reproduced it. Launcher reuse needs a fix. The installed
private-alias refusal step was not reached.
[Installed Android assignment shade replay](verification/receipts/fieldlog-android-assignment-shade-api36-c4c133d6.json)

The `singleTop` manifest successor passed a fresh API 36 replay. After a
cold shade tap, returning from Home through the launcher kept the same
Android Activity record, task, and process and restored the dashboard.
The public Activity ignored an unrelated assignment action, and Android
denied a direct launch of the private alias. All five shade cases still
passed, including the warm unsaved title and three stale tuples. The
workspace and its 47 outbox records stayed byte-identical. The build
relinked the manifest and preserved all 37 other APK members.
[Installed assignment launcher correction](verification/receipts/fieldlog-android-assignment-single-top-api36-f82f7397.json)

A follow-up reached the real Camera2 shutter over the assignment-rooted
Activity. Home and the launcher then opened a second, blank FieldLog
Activity in the same task. The original Activity and workspace bytes
remained.

The corrected Camera2 APK finishes this duplicate before it starts
a workspace. The root-owned API 36 run returned through the launcher
to the original capture twice. Back preserved every workspace byte.
Accepting one image saved the new draft and its restoration pointer
in one revision, preserving both existing drafts and all 47 outbox
records. The 1,392 × 1,856 JPEG and workspace matched after cold
reopen in a fresh process. All owned device and signing scratch closed.
[Camera2 launcher return receipt](verification/receipts/fieldlog-android-assignment-camera-launcher-api36-22c00318.json)

The iOS assignment correction `73e9f093` held a cold intent through
a real workspace-open failure and routed it once after retry. A report
that finished behind an assignment waited for dismissal and presented
once. Independent host controls reproduced both original failures and
verified the fixes. Unsigned generic arm64 iPhoneOS Debug and Release
linked. Installed presentation remains pending.
[iOS assignment recovery review](verification/receipts/fieldlog-ios-assignment-recovery-73e9f093.json)

FieldLog's local SQLite issuer now exchanges native callback codes for
account sessions and uses the same authority in task and entry sync.
A lost exchange response originally occupied the last session slot for
eight hours. The corrected service reclaims unconfirmed sessions after
60 seconds. Confirmation starts a stable eight-hour lease. A fresh
root replay passed the capacity, restart, revocation, scope, and legacy
workspace and photo controls. The ordinary iOS and Android account
adapters still need installed verification. Recovery and deletion remain open.
[Account session confirmation](verification/receipts/fieldlog-local-account-session-confirmation-b6debbc4.json)

The ordinary iOS account owner now verifies confirmation before storing
the bearer or opening the workspace. Two root host replays matched the
exact composed FieldLog tree and passed live confirmation, withheld
callbacks, retry, sign-out, isolation, and draft, photo, and outbox byte
checks. The author's 40 host tests and unsigned generic iPhoneOS build
also passed. Native browser delivery and Keychain runtime remain open.
[iOS confirmed account owner](verification/receipts/fieldlog-ios-account-confirmed-owner-ebb53f9e.json)

The ordinary Android development account route passed on API 36 arm64.
The emulator browser submitted the synthetic sign-in, Android delivered
the callback, and session confirmation opened the bound workspace. A
new process restored the same credential through Android Keystore.
Sign-out revoked the SQLite session, cleared the credential, and returned
to ordinary FieldLog with byte-identical account and ordinary workspace
files. The original mount failure and pre-fix cold JNI crash are retained
in the receipt. Offline Android restore, account recovery, deletion,
and native iOS acceptance remain open.
[Android account verification](verification/receipts/fieldlog-android-account-api36-066e5038.json)

Two fresh API 36 runs used the same signed Android account APK. Removing
the device route to the session service preserved the unexpired Keystore
credential and admitted the same workspace in a new process. Restoring
the route allowed sign-out and revocation. A separate run used a
70-second issued session. After the confirmed deadline, an offline cold
launch cleared the credential and displayed **Local session expired**
without mounting the account workspace. Both runs preserved the ordinary
and account workspace files and made no offline service request.
[Offline restore and expiry](verification/receipts/fieldlog-android-account-offline-expiry-api36-066e5038.json)

While an Android account workspace stayed open, a valid offline expiry
retired the workspace and cleared the credential but displayed ordinary
Welcome. The corrected API 36 build kept the expiry reason and displayed
**Local session expired** in the same process. Both workspace files stayed
byte-identical, and ordinary online cold restore and sign-out still passed.
[Active Android account expiry](verification/receipts/fieldlog-android-account-active-expiry-api36-000c3321.json)

The same signed Android build recovered after two kinds of response
loss through the actual browser callback. Losing the exchange reply
returned to sign-in with one provisional server session and without an
account workspace mount or saved credential. A fresh sign-in confirmed
a new session. The transport retried a single lost confirmation reply
automatically. Holding the fault through that retry exposed **Retry**,
which reused the same bearer and opened the exact workspace when the
service replied. Sign-out revoked the confirmed session, and both
workspace files retained their original bytes.
[Android account reply loss](verification/receipts/fieldlog-android-account-lost-replies-api36-000c3321.json)

The FieldLog local recovery backend passed a fresh fixed-port replay.
A one-use operator code and explicit browser approval allow the client
to replace a lost sign-in proof. Recovery revokes prior sessions and
requires confirmation of the new session. The replay verified response
loss, a rolled-back transaction, another account's continued access,
and byte-for-byte equality of stored task, entry, and photo rows. Native
recovery and account deletion remain open.
[Local account recovery](verification/receipts/fieldlog-local-account-recovery.json)

The shared Swift recovery owner and iOS Debug route passed a separate
host replay against the recovered backend. A lost exchange reply kept the
replacement code staged, and a fresh owner signed in with it through the
ordinary flow. The account, scope, workspace, draft, photo, and outbox
matched. The implementation lane's unsigned generic iPhoneOS build passed.
Native browser delivery and Keychain acceptance remain open.
[Shared Swift and iOS recovery](verification/receipts/fieldlog-ios-account-recovery-host.json)

The Android recovery candidate passed the acknowledgement and reply-loss
paths on API 36. It kept the workspace closed across restart until
acknowledgement, then used a staged replacement in a fresh process after
a separate exchange reply was lost. Both workspaces and the seeded service
task stayed unchanged. An earlier cold sign-in stopped before confirmation.
Independent review found that Cancel can erase the staged replacement and
a different scope can rotate credentials before Android refuses the mount.
The reveal and foreground mount guards also need correction. Keep the
candidate unadopted and local account recovery open.
[Android recovery device observations](verification/receipts/fieldlog-android-account-recovery-api36-0f2bbcfd.json)

The Android lifecycle successor requires a fresh reveal after Home or cold
launch before enabling acknowledgement. The installed Cancel scenario
preserved the replacement after server commit and reopened the same
workspace through ordinary sign-in. This pass used a shortened fixture
expiry after a default-expiry confirmation left the app unavailable.
Independent review reproduced a separate cold startup wait failure
while paused. Adoption remains held for startup and service scope.
[Recovery lifecycle device observations](verification/receipts/fieldlog-android-account-recovery-lifecycle-adc3238e.json)

The exact shared owner reproduced the account timing failure when the
client clock lagged the service by one second. At the default lifetimes,
the owner showed unavailable after a successful exchange or after a
successful confirmation, depending on when the lag began. The shorter
fixture admitted the account. All three runs preserved the workspace
files and the peer service data.
[Controlled session clock replay](verification/receipts/fieldlog-account-wall-clock-lag-cfaa8410.json)

The clock correction waits once when a fresh receipt appears up to two
seconds over its lifetime limit. It then checks the same receipt under
the original limit and checks cancellation and owner generation.
The macOS replay admitted one-second lag at exchange, confirmation, and
both stages while preserving the returned expiry. Larger lag, expired
receipts and stale owners were refused. The generic iPhoneOS app linked.
On API 36, one run verified recovery acknowledgement with the default
lifetimes. The next browser form did not appear. A fresh run verified
Cancel after the service committed, cold sign-in with the preserved
replacement code, and sign-out. Both app candidates remain unadopted.
[Clock correction evidence](verification/receipts/fieldlog-account-clock-correction-bd0b37cf.json)

The corrected Android Activity counts foreground time while cold account
startup waits for the previous workspace owner. The old Activity exhausted
the budget during a synthetic 90-second pause. The new Activity restored
once after focus returned, and all six host controls passed. A signed API 36
build also passed the recovery and Cancel regression with shortened fixture
expiry. The service-scope and default-expiry issues still hold adoption.
[Cold startup foreground checks](verification/receipts/fieldlog-android-account-startup-foreground-82d9809d.json)

The FieldLog deletion backend requires a confirmed account, its exact scope,
and explicit intent. It removes the scoped service data and stores an
idempotent receipt in the same transaction. Two root replays passed
rollback, lost reply after commit, restart, and unchanged rows for a
second account. The exact completed request recovered its receipt after
reprovisioning without changing the new account. The replay used a
disposable SQLite database and loopback requests.
[Local account deletion](verification/receipts/fieldlog-account-deletion.json)

The private Android deletion candidate passed the lost-response path on
API 36. Cancelling confirmation kept the workspace and sent no deletion.
After explicit confirmation, SQLite committed one receipt. The app kept
its workspace and credential when the response was dropped. A new
process waited for **Retry deletion**, then removed the scoped workspace
and credential after the matching receipt. The ordinary workspace and
peer service records stayed unchanged. Independent host review found
two startup failures involving a saved sign-out marker and a browser
callback during a slot-read error. App adoption remains held.
[Installed Android deletion](verification/receipts/fieldlog-android-local-deletion-api36-bffb082b.json)

The earlier APK reproduced the stale sign-out marker loop in two new
processes after a lost deletion reply. The first successor ignored the
browser Sign in button. Restoring the command let the corrected APK
sign in and wait for explicit deletion retry on API 36. The retry
returned the original SQLite receipt, cleared the marker, and removed
only the test account workspace and credential. The same APK retained
one genuine cold browser callback across a temporary credential-read
failure and confirmed one session when the user retried. The API 36
ordering control then delivered a stale test redirect before the genuine
browser return. The earlier app reopened the browser prompt without an
exchange. The final app confirmed one session after Retry, without
browser redelivery. The final APK also recovered the original deletion
receipt and kept the ordinary workspace and peer data intact. Host review
reproduced an earlier Java handoff failure before Swift receives the
return. Startup can lose the callback at ten seconds or retain only a
later stale return. Full Android account adoption remains held.
[Android startup and deletion replay](verification/receipts/fieldlog-android-deletion-startup-api36-386d0577.json)

The Java handoff successor passed a delayed browser return on API 36.
The local service approved one test sign-in. The driver scheduled that
return and then a stale return through Android while the display slept
for 11 seconds. The previous APK opened the browser prompt without an
exchange. Waking the corrected APK confirmed exactly one session in the
waiting process. Sign-out preserved the ordinary workspace. A separate
run recovered the original deletion receipt and cleared its stale
marker. Independent host review and another API 36 run reproduced a
pre-existing warm callback loss on a temporary credential-read failure.
Retry reopened the browser prompt with zero exchanges. Full account
adoption remains held.
[Delayed browser handoff](verification/receipts/fieldlog-android-java-callback-api36-11a509d1.json)

The warm-return correction passed the installed API 36 replay. One
browser return reached the same app process during a credential-read
failure. Restoring the original sealed slot and tapping Retry produced
one exchange and one confirmed session without browser redelivery.
Sign-out preserved the ordinary workspace. A separate run on the exact
APK recovered the original deletion receipt, removed only the scoped
test account, and cleared the stale marker. The shared Swift owner
retains the Apple Boolean API. Independent host review reproduced
Cancel being dropped while a callback command was busy. A subsequent
Retry exchanged the retained return in both ordinary recovery and
deletion reauthorization. Installed reachability of that command order
is unverified. Full account adoption and Apple adapter parity remain
open.
[Installed warm callback](verification/receipts/fieldlog-android-warm-callback-api36-b9bff058.json)

The Cancel successor passed exact host controls for ordinary recovery
and deletion reauthorization. Cancel before attempt consumption caused
zero subsequent exchanges on Retry. The host review confirmed preserved
replacement codes and deletion intent. On API 36 the exact APK cleared
the pending credential through the ordinary Cancel button. It then
admitted one new browser sign-in and passed the separate warm Retry
regression. The busy callback command order remains host evidence.
A separate API 36 run tapped Cancel while the credential slot was
unreadable. After restoring the slot and force-stopping, a new process
reopened the saved browser attempt with zero exchanges. Cold
cancellation and account adoption remain open.
[Android browser Cancel](verification/receipts/fieldlog-android-browser-cancel-api36-09851a72.json)

The durable Cancel candidate `5d8c624b` passed the same installed
ordinary sign-in control. After Cancel with an unreadable credential
slot, a new process returned to Welcome and retired the matching saved
attempt. A separate new sign-in confirmed one session, and sign-out
preserved the ordinary workspace. Independent host review reproduced
two blockers in recovery and deletion reauthorization. A failed
cancellation-record write can leave the old attempt usable despite a
writable credential slot, and a temporary record-read failure can drop a
newer valid callback on Retry. A separate API 36 run confirmed the
first finding through ordinary sign-in. The old attempt reopened in a
fresh process when only the cancellation-record write failed. No
callback or exchange was submitted. Adoption remains held.
[Installed cold Cancel and review disposition](verification/receipts/fieldlog-android-durable-cancel-api36-5d8c624b.json)

The signed `6ff80e48` successor passed both installed storage fault
comparisons and repeated the ordinary cold Cancel check. A writable
credential slot retired the exact attempt when the Cancel-record
write failed. Retry consumed a newer return once after the record
became readable, with no browser redelivery. Independent host review
reproduced one further order. When restore failed with an empty queue,
the first valid callback arriving afterward was dropped, and Retry
made zero exchanges. A signed API 36 ordinary sign-in reproduced
that order with one real browser return and zero exchanges. Its
first setup attempt stopped before return delivery, and the repeat
foregrounded the exact Debug Activity before opening the browser.
Adoption remains held on that order.
[Installed Cancel record I/O checks](verification/receipts/fieldlog-android-cancel-record-io-api36-6ff80e48.json)

The signed `f4ad72f7` candidate retained the first callback after
blocked restore. A genuine return delivered after the Retry screen
appeared confirmed one session on Retry without browser redelivery.
The earlier-arrival control also passed. Two separate cold Cancel runs
retired the attempt with an unreadable credential slot or an unwritable
cancellation record, then accepted one fresh sign-in. All four owned
emulator runs closed. Independent host review reproduced a separate
Cancel → callback → Retry schedule that drops the first Retry before
the callback task runs. The second Retry worked. The first Retry made
no exchange, credential write, or deletion-journal change. Installed UI reachability remains open,
and full account adoption remains held.
[Installed early and late browser return checks](verification/receipts/fieldlog-android-blocked-restore-return-api36-f4ad72f7.json)

The first Retry correction passed independent host review on both
routes. After Cancel and a stale return, the first Retry restored the
expected browser with one marker read and zero exchanges or credential
writes. The exact signed successor also passed the installed ordinary
late-return and cold Cancel checks. The three-command order remains
host evidence. Full account adoption remains open.
[First Retry and installed regressions](verification/receipts/fieldlog-android-first-retry-api36-891c38dc.json)

The iOS deletion owner now loads the saved reauthorization intent when
the browser callback arrives before startup restore. The real loopback
host replay passed both orders. Local data stayed intact until renewed
confirmation, and each fixture retained one deletion receipt. The exact
corrected tree linked for generic arm64 iPhoneOS. Native browser and
Keychain checks remain pending.
[iOS deletion owner checks](verification/receipts/fieldlog-ios-account-deletion-callback-5cdfa986.json)

The shared iOS owner now retains an unacknowledged replacement across
recovery cancellation and supersession. The loopback replay cancelled
held exchange and confirmation replies, then recovered the replacement
in fresh processes and signed out after ordinary sign-in. Both deletion
callback orders and scoped cleanup still passed. The exact source
linked for generic arm64 iPhoneOS.
[iOS pending replacement replay](verification/receipts/fieldlog-ios-pending-replacement-1ba375bb.json)

The generic iOS Simulator witness builds the same ordinary FieldLog
tree with a named XCTest. It opens the saved project, edits a draft
through the Photo Library picker, saves a manual Site Map pin, and
changes Appearance. A read-only Debug checkpoint compares the exact
workspace, JPEG, and preferences across a cold launch. Independent
static readback matched the pinned sources, test selector, and bundle
signatures. Installed execution remains pending.
[Build and test receipt](verification/receipts/fieldlog-ios-ordinary-73e9f093-witness.json) ·
[Rebuild and run guide](tests/integration/fieldlog-ios-assignment/ordinary-witness/README.md)

The maintained FieldLog Swift task client now supports an injected
bounded exchange. The Apple initializer passed the two-replica macOS
replay, including the stale edit, explicit merge, and exact retry after
a lost acknowledgement. SQLite recorded two events. Pinned Android
Swift compiled the client with an injected transaction. The Android I/O
and installed conflict cases remain open.
[Exact Swift task patch](verification/receipts/fieldlog-ios-task-conflict-injected-f2865989.patch) ·
[Source and host verification](verification/receipts/fieldlog-ios-task-conflict-injected-f2865989.json)

The exact FieldLog tree `41eaf5b4` linked as an unsigned arm64 iPhoneOS
app against Pair25. Static readback followed ordinary Project Detail
into the Apple URLSession task-sync transport and confirmed Settings
and the camera and location usage descriptions. The iPhoneOS bundle
omits the Simulator loopback ATS exception. Installed behavior and
loopback reachability remain unverified.
[Generic iPhoneOS build](verification/receipts/fieldlog-ios-task-conflict-injected-iphoneos-build.json)

## November 21 current FieldLog Android queue

The Pair25 queue port ran the ordinary On device screen on macOS with
loopback HTTP and SQLite. Cancel and owner close both resumed a photo
at 65,536 bytes. Both recovered a lost acknowledgment with one remote
event, a byte-identical JPEG, and the unrelated local records intact.
The queue stayed offline without a matching project session. The
successful run closed its owned groups and removed scratch. Two earlier
sampler attempts have separate custody holds. The host replay reproduced
the stock resolver and manifest refusals.
[Host replay](verification/receipts/fieldlog-android-queue-pair25-host.json) · [Scoped holds](verification/receipts/fieldlog-android-queue-pair25-custody-holds.json)

The stock Android builder recognizes the NDK's system `libz.so`.
The corrected collector resolves the real Swift Android runtime
closure and omits `libz.so` from the staged libraries. The NDK API 28
stub exports the five zlib symbols the closure imports. An unavailable
non-system library still fails. The exact source admissions pass in the
Swift, Intel, Phoenix, Identity, and Services sparse checkouts in both
Python modes. The historical Source141 and Source127 restores and
Pair25 inputs retain their prior bytes and modes.
[ELF check](verification/receipts/android-stock-libz-elf-8e8d75c3.json) · [Archive checks](verification/receipts/android-stock-libz-source141-06e7202a.json) · [Combined admission](verification/receipts/android-stock-libz-combined-admission-8e8d75c3.json)

Hosted Engine passed all nine jobs on `7799110750`. Its 157-input
Source141 receipt matched the zlib source digest, all six Java and D8
consumers produced byte-identical DEX, and both scratch roots were
removed. The earlier `f1bf257b2d` Engine run ended with eight passing
jobs and a generated-Java job failure. The final integration step
has no terminal log or artifact, so its cause and custody are
unverified. Phoenix and Identity passed at that revision.
[Passing Engine run](https://github.com/snowdamiz/mixer/actions/runs/44958276169) ·
[Earlier Java job](https://github.com/snowdamiz/mixer/actions/runs/44957321744/job/137008196141)

The signed camera and queue APK passed two separate clean API 36 installs.
A missing session, wrong workspace session, and selected sibling project
made zero HTTP requests. Cancel preserved the first 65,536 server-staged
bytes. Resume committed one remote event and one byte-identical JPEG.
The lost acknowledgment kept the local event queued. The next attempt
read the complete offset and retired only that outbox item without sending
another chunk. One workspace revision changed. Cold reopens preserved
both local photos and the sibling record.
The same APK bytes passed Camera2 Cancel, Done, the eight-photo limit,
and cold reopen. Both emulators and their private ADB servers closed.
The queue reverse mapping was removed and all owned ports rebound.
[Installed checks](verification/receipts/fieldlog-android-camera-queue-installed-api36-cb54a33d.json) · [Exact patch](verification/receipts/fieldlog-android-queue-from-camera-cb54a33d.patch) · [Build receipt](verification/receipts/fieldlog-android-camera-queue-pair25-local.json)

## November 21 Apple signed draft validation host replay

On macOS, the Apple selected-draft owner and stock VM checked a
photo-linked draft titled with three spaces. Signed sequence 1 showed
“Ready to save entry”. Sequence 2 showed “Entry title is required”,
and a cache-only reopen retained sequence 2. All checks preserved the
workspace, outbox, and JPEG, with zero attempted repository writes.
The host reopened the runtime and repository in one process and
acknowledged display through the attachment API. The iPhoneOS arm64
XCTest product built. Installed Simulator execution remains pending.
[Host and generic build receipt](verification/receipts/fieldlog-ios-222-stock-vm-host-d89c742e.json)

The same test then built for generic arm64 iOS Simulator. The archived
app, XCTest runner, and plug-in matched their executable hashes. The
run configuration selects only the title correction test, and both
releases were signed for the Simulator runtime identity. Install and
execution remain pending. [Simulator build](verification/receipts/fieldlog-ios-222-simulator-build-d89c742e.json)

The signed Apple row-reorder case passed on the macOS owned VM.
The sequence-2 Move up appended one task-order event. Signed rollback
and an offline cold reopen kept the moved order, the same draft and
JPEG, and the exact post-move workspace. An earlier replay committed
the move and hit the 50 ms wake deadline before showing the next frame.
The same signed inputs and deadline passed in the later run. The
generic Simulator archive passed the three signature checks and the
XCTest selector readback. Simulator execution remains pending.
[Row-reorder witness](verification/receipts/l08-fieldlog-ios-signed-row-reorder-1032909c.json)

The earlier pinned row fixture passed its installed iOS Simulator
XCTest after Accessibility trust was restored. One Move up committed
one task-order event. Signed rollback and offline reopen preserved
the reordered workspace and its selected draft.
Independent attachment readback matched the exact bytes across
the reviewed, rollback and offline phase comparisons.
[Installed row replay](verification/receipts/l08-ios-fresh-simulator-signed-row-584cd194.json)

The iOS refusal fixture passed a fresh macOS replay through the installed
owner and loopback delivery. Wrong scope, wrong runtime, invalid body
and replay cases preserved the verified staged baseline, draft, JPEG,
outbox, and workspace. The valid sequence-12 successor reached a
headless first frame. Independent readback matched all three Simulator
bundle signatures, seven embedded fixture files, and the XCTest selector.
Both host listeners closed. The generic build ran past its nine-minute
bound and removed its scratch. Installed health and offline cold reuse
remain pending.
[iOS refusal witness](verification/receipts/fieldlog-ios-227-228-generic-6a46e529.json)

Two fresh iOS Simulator runs fetched the signed baseline and rendered
**Open** at sequence 1. Both stopped before the refusal phases at
the baseline observation. The diagnostic read the healthy journal,
the original JPEG and the saved task and draft. The journal named
the healthy candidate in its staged slot, which the Debug witness
requires to be empty.
Both fresh devices and listeners closed. Each of the 13 monitored
external devices matched its baseline.
[Installed refusal diagnosis](verification/receipts/fieldlog-ios-227-228-native-healthy-staged-diagnostic-6a46e529.json)

The corrected Debug witness passed on a fresh iOS 27.0 ARM64
Simulator. Fifteen checkpoints preserved the same workspace,
draft, JPEG and outbox. Invalid releases left sequence 1 healthy.
The valid sequence-12 successor became healthy and reopened
offline in a new process. Direct disk readback matched both
the final workspace digest and fixture JPEG. All 98 runtime
commands closed, both loopback listeners retired, and the fresh
device was removed with the 13 monitored external devices unchanged.
[Installed iOS refusal replay](verification/receipts/fieldlog-ios-227-228-native-refusals-6a46e529.json)

## November 21 Android saved-draft validation

One fresh FieldLog Pair24 development install on Android API 36 saved
a three-space title and a DocumentsUI JPEG through the ordinary editor.
Signed sequence 1 showed “Ready to save entry”. Sequence 2 showed
“Entry title is required” after the same Check saved draft action.
The workspace, draft ID, revision, outbox and JPEG stayed unchanged
through both checks and an offline cold launch. The signed journal
retained sequence 2 on the same installation. The installed APK hash
matched before and after. All 197 command groups closed, the four
private ports could be rebound, and the disposable emulator scratch
was removed. This covers Android §22.2.2. The iOS scenario remains open.
[Installed replay](verification/receipts/fieldlog-android-222-installed-551576a0.json) ·
[Build inputs](verification/receipts/fieldlog-android-222-inputs-551576a0.json) ·
[Fixture delta](verification/receipts/fieldlog-android-222-fixture-551576a0.patch)

## November 21 reusable iOS build worker recovery

One loopback Phoenix API, restricted Oban processor, and SCRAM PostgreSQL
fixture started a real unsigned Starter Xcode build. The listener was
replaced while that build was active. The independent supervisor retained
custody, and the replacement settled the original job under a fresh guard.
The same configuration, listener port, supervisor, and ledger admitted
and settled a second build. Both builds had one start and one capacity
release. The owner downloaded all three artifacts for each build and
re-read the first build after the second. Its artifact hashes matched.
All 52 command groups closed, all five ports were reusable, and live
scratch was removed. Both builds targeted the generic iOS Simulator
SDK. No Simulator device booted.
[Live receipt](verification/receipts/l07-ios-worker-reusable-live-551576a0.json) ·
[Exact fixture overlay](verification/receipts/l07-ios-worker-reusable-live-fixture-551576a0.patch)

The independent inert check passed 54 tests with one fixture-dependent
skip in each Python mode. The v87 binding restored v86 through v82 and
preserved the 157 Source141 inputs and 53 Pair25 inputs. All three
hosted v87 workflows passed. The two real Xcode recovery builds ran
separately on macOS.
[Worker correction](verification/receipts/l07-ios-worker-reusable-supervisor-compat-1e2de013.json) ·
[Source binding](verification/receipts/hosted-source-v87-composition.json)

## November 21 public Swift feature replay

On v86, the owned Guest UI V1 runtime matched four native TaskCompletion
frames and refused six malformed inputs per arm while preserving the
prior frame. Floating-point, associated-type, and property-wrapper
controls matched. Both shared-memory admission routes refused the
fixture without publishing a session. The two Rust suites passed all
32 focused tests, and all 34 command groups closed. This is macOS host
evidence. The installed iOS TaskCompletion comparison remains open.
[Replay receipt](verification/receipts/l03-swift-profile-v86-551576a0.json)

## November 21 FieldLog Rust notices

The amended Pair25 recipe binds all five notices and the exact VM
receipt before Java and JNI production, then checks them again before
sealing and signing. A clean development APK build from FieldLog
`00406fe7` passed static readback. Independent checks matched all 42
members, verified 16 KiB ZIP and ELF alignment for all 19 arm64
libraries, and verified both signed guest envelopes. The final driver
search order resolves libunwind to the Swift SDK's NDK r27d archive.
No linker archive-member trace was emitted. The independent source review
records four historical receipt hashes that differ from the staged bytes.
The same APK also passed an offline API 36 install. FieldLog saved a
photo through DocumentsUI and restored the draft after a cold launch.
The bundled sequence 1 Entry Commit showed “Committed once”, reused
the draft ID and JPEG reference, and appended one `entrySaved` record.
A second cold launch preserved the exact workspace and JPEG bytes.
All 180 command groups closed, the three private ports were reusable,
and the disposable scratch was removed.
[Installed APK replay](verification/receipts/fieldlog-pair25-rust-notice-apk-api36-runtime-00406fe7.json)
[Source integration](verification/receipts/fieldlog-pair25-rust-notice-source-integration-v87.json) ·
[Development APK build](verification/receipts/fieldlog-pair25-rust-notice-apk-00406fe7.json) ·
[Independent APK readback](verification/receipts/fieldlog-pair25-rust-notice-apk-readback-00406fe7.json)

The combined camera, queue and Site Map APK retains those notices.
Independent ELF and signed ZIP readback found additional linked curl,
SDK and JNI copies of BoringSSL, Swift Crypto and XKCP. Their component
notices are missing. Linkage of the resolved Swift ASN.1 package was
unobserved. System zlib remains outside the APK. The next notice
bundle must bind the pinned inputs and both ELFs.
[Exact combined APK notice review](verification/receipts/l07-fieldlog-pair25-network-crypto-notice-review-87c95c5a.json)

The maintained paired recipe now requires all twelve notice files and binds
the SDK FoundationNetworking and FieldLog JNI ELF digests. Independent
review passed 26 modern inert checks, 18 historical checks, and seven
additional controls. The explicit historical recipe retains the exact
photo-only five-notice build. Source141 admits the new inventory in both
actual sparse checkouts and both Python modes. Both predecessors restored
with matching bytes and file modes. Real APK and installed verification
remain pending. The SDK BoringSSL build commit remains unproven.
[Recipe and Source141 evidence](verification/receipts/fieldlog-pair25-l07-notice-source141-adoption-491d708b.json)

The official ARM64 FoundationNetworking ELF identifies 221 BoringSSL
paths and 113 curl paths in its DWARF strings. All matched the pinned
upstream source trees. Three sampled function declaration locations and
both packaged notice texts also matched. The BoringSSL tag differs from
its parent only in a build tool. The SDK SBOM contains no package source
checksum, so the exact SDK build input remains unproven.
[SDK networking provenance](verification/receipts/l07-swift-android-networking-dwarf-provenance.json)

The near-release Swift Android builder defaults to BoringSSL
fips-20220613 and records its Git-derived version in the SDK SBOM.
The installed SBOM names that tag, whose annotated reference peels
to the notice commit. A fresh independent control showed that a dirty
tagged checkout still emits the bare label. The release invocation,
working-tree state, and a manifest binding exact inputs to the ELF
remain unverified. The earlier receipt's upstreamGitTree fields are
commit IDs. The successor records the corresponding tree IDs.
[Recipe and SBOM attribution](verification/receipts/l07-swift-android-boringssl-sbom-recipe-5f922bd6.json)

The fresh signed FieldLog `891c38dc` APK binds its JNI to five
selected objects from the Swift Android SDK's bundled r27d
`libunwind.a`. The linker trace, sealed JNI input, and exact packaged
JNI digest are recorded. Independent readback matched both NDK
notices across the SDK copies, the embedded seal, v3 signature, and
16 KiB alignment. A separate earlier relink had different JNI bytes
from its prior installed comparison. Historical APK archive selection
and the SDK BoringSSL build revision remain open.
[Traced JNI link and signed package](verification/receipts/fieldlog-android-first-retry-api36-891c38dc.json)

All nine Owned Engine jobs passed at `2fbba61cb1`. Swift admitted the
157 installed inputs in both Python modes and restored both historical
archives. Intel passed bootstrap, sparse checkout controls and all six
Java/D8 consumers. The hosted test that requires a built APK skipped.
The local installed evidence above covers the FieldLog APK itself.
[Hosted Source141 and notice admission](https://github.com/snowdamiz/mixer/actions/runs/44970018258)

On `5f922bd6`, the six-consumer Android Java cross-compile passed
and its owned scratch closed. GitHub failed to create the top-level
metadata artifact after five requests. On `3362bf6c`, the Swift host
download failed before the integration. The metadata upload reported
a finalization timeout, and the exact ZIP was readable through GitHub.
Its five bootstrap commands reached terminal custody and the owned
scratch was removed. The one retry passed all six Java consumers and
the metadata upload. All nine jobs passed for that attempt.
[Hosted Java retry](https://github.com/snowdamiz/mixer/actions/runs/45026922011/attempts/2)
The next public revision, `c6ee43e1`, passed all nine jobs on its first attempt.
[Hosted Engine run](https://github.com/snowdamiz/mixer/actions/runs/45029091735)
[Hosted Java bootstrap and artifact receipt](verification/receipts/hosted-java-bootstrap-and-artifact-3362bf6c.json)

All nine Owned Engine jobs passed on `554515a3`. The two hosted
Java artifacts matched GitHub's archive digests. The 157 source inputs
matched the tracked Source141 map, and all six archived DEX files
matched byte for byte. The two producer receipts record all 92 command
groups terminal and scratch removed.
[Hosted Engine and Java readback](verification/receipts/hosted-engine-terminal-554515a3.json)

The next Owned Engine run passed all nine jobs on `ccb5221c`,
including the six-consumer Java job.
[Hosted Engine result](https://github.com/snowdamiz/mixer/actions/runs/45032006705)

All nine Owned Engine jobs passed on the Rust notice binding.
Both Python modes admitted the same Source141 and Pair25 inputs, and
all six Intel Java and D8 builds returned identical DEX bytes.
[Hosted notice binding receipt](verification/receipts/hosted-pair25-rust-notice-95b9b959-terminal.json)

Engine passed all nine jobs on `fe713fa71a` and `d89c742e9d`. The
raw hashes and byte counts of all ten GitHub archives matched for
each run. The six Intel Java consumers reproduced their DEX bytes,
and the 13 bootstrap and 79 integration process groups reached
terminal custody in each run. [Hosted evidence](verification/receipts/hosted-engine-fe713fa-d89c742e-terminal.json)

The Swift host job on `b7ead55c26` failed two five-second waits for
scripted store requests to start. Both neighboring Swift host jobs
passed with the same CLI, SDK, and workflow bytes. The failed run's
archive records terminal custody for 140 owned commands and 60 store
children. [Hosted failure](verification/receipts/hosted-engine-b7ead55c-swift-store-start-timeouts.json)

An injected start delay reproduced both messages before either test sent
its old request. The fixture now starts an owned thread and captures the
held URLProtocol response, preserving the five-second limits and request
ordering. All 44 focused tests passed independently on macOS Swift 6.4.2,
with 59 real CLI children confirmed closed. The original hosted trigger
remains unknown. Hosted validation of the correction is pending.
[Author replay](verification/receipts/store-reconciliation-host-fixture-7d257e0d.json) · [Independent replay](verification/receipts/store-reconciliation-host-fixture-independent-7d257e0d.json)

Hosted Swift at `c18b3060f8` stopped before running the test correction.
Source141 still pinned the predecessor StoreReconciliationTests.swift
bytes in its inherited CLI inputs. Both hosted admission checks refused
the new bytes. The same 45-pattern sparse checkout reproduced this locally
in normal and optimized Python. The predecessor admitted all 157 inputs
in both modes. The same mismatch stopped Intel at its 45-test bootstrap
step, before its six consumers ran.
[Admission failure](verification/receipts/hosted-engine-c18b3060-swift-store-source-admission.json)

The reversible archive now admits both corrected Swift tests and their
new helper. Both actual non-cone selections admit the same 157 Java
inputs in each Python mode. Historical restore matches all 890 Source141
and 845 Source127 files by bytes and mode. The independent replay passed
the 45 bootstrap and 16 sparse controls in both modes. Hosted Swift
6.2.4 then passed both corrected tests and all 137 CLI tests. All nine
hosted jobs passed, including all six Intel consumers. The two
APK-dependent Swift tests skipped for missing fixtures.
[Hosted receipt](verification/receipts/hosted-engine-8e8d75c3-store-reconciliation-terminal.json)
[Archive checks](verification/receipts/source141-store-reconciliation-admission-c18b3060.json) · [Independent replay](verification/receipts/source141-store-reconciliation-admission-c18b3060-root.json)

## November 20 generated release REST client

The stock Swift CLI uses generated REST operations for upload, validate,
publish, promote, rollback, and halt. The maintained Phoenix and PostgreSQL
fixtures exercised all six operations. They passed 16 tests with the
separate opt-in TLS uploader case skipped. The Swift contract tests passed
all four cases, including exact signed request bytes and full-width
integers. [Phoenix replay](verification/receipts/l05-v3-generated-cli-phoenix-301b0daf.json)

The Verify workflow checks the generated Swift and all six Phoenix routes.
The archive admits both CLI projections and restores the exact v68
predecessor. [Release REST contract](contracts/release-rest-v3.md) · [Source admission](verification/receipts/release-rest-v3-ci-source-admission-v68.json)

## November 20 Swift language support matrix

The generated Swift support matrix maps 18 scoped claims to executable
controls. Eight rows remain unqualified. Native Swift and the owned guest
produced the same four FieldLog frames and refused six malformed events
without changing state. The owned validator and session constructor refused
shared memory before admitting a guest session.

The macOS FeatureStore probe joined the replacement, replaced, cancelled,
and stopped tasks before checking delivery. Only the replacement reached
the reducer. Swift guest task cancellation and installed iOS TaskCompletion
qualification remain open. [Swift language support](compiler/swift-language-support.md) · [Scoped host and VM replay](verification/receipts/l03-swift-language-support-b963585e.json) · [Completion control](verification/receipts/l03-swift-language-support-w07-correction.json)

For seven finite inputs on arm64 macOS, Swift `Float` and `Double` arithmetic
and comparisons matched native result bits through the installed Guest UI v1
VM. The guest rejected a short input without changing its result and retired
with a stale-handle refusal. The two recorded builds emitted different Wasm
hashes and the same observed instructions and ordered frames. [Producer replay](verification/receipts/swift-floating-point-preview-6f4fdee12e.json) · [Integration replay](verification/receipts/l03-swift-floating-point-integration-b463c00d.json)

Native Swift and installed Guest UI v1 produced byte-identical results
for four runtime inputs to the shared associated-type function on arm64
macOS. The concrete specializations extract `Int16` and `UInt16` readings.
Both paths preserved the last result after a truncated event. The guest
closed and refused its stale handle. Existential dispatch remains open.
[Associated-type replay](verification/receipts/l03-swift-associated-types-v73.json)

Native Swift and installed Guest UI V1 produced the same stored values and
projected update counts for one value-type property wrapper. Both paths
refused the out-of-range event, preserved the previous frame, and accepted
the next valid reading. The guest closed and returned status 3 on stale
startup. An independent arm64 macOS run matched the frames using rebuilt
host and Wasm bytes with different hashes. The cause of that variation
remains unverified.
[Property-wrapper replay](verification/receipts/l03-swift-property-wrapper-v77.json)

A synthetic fixed-slot Swift result builder produced matching native and
installed guest frames for zero through three children on arm64 macOS.
Both paths refused four children and retained the previous frame. Closing
and reopening the guest reclaimed the slot with a fresh generation.
The separate dynamic-loop builder passed natively and failed guest linking
on the array allocator imports. Independent replay confirmed both scopes.
[Fixed-slot replay](verification/receipts/l03-swift-fixed-slot-result-builder.json) ·
[Dynamic-loop boundary](verification/receipts/l03-swift-result-builder-v78.json)

Native Swift and the installed Guest UI V1 VM on arm64 macOS emitted the
same frames for one associated-value enum and typed throw and catch. A
refusal carrying 1,100 preserved the previous frame for 1,000. The next
valid event published 57 and the caught value. The guest rejected stale
handles after closing and reused the slot with a fresh generation.
Independent review matched the source pins, frame bytes, and support matrix.
Signed activation and mobile execution remain open.
[Typed-error replay](verification/receipts/l03-swift-enum-typed-throws.json)

The first composed replay reproduced the frames, fuel, and linked VM
archive. Its 534-byte Wasm had a different digest. A controlled rebuild
isolated the difference to the 16-byte Swift module hash carried in the
Wasm data section. With a fixed Swift object output argument, two fresh
replays emitted byte-identical Wasm and preserved the matching frames,
fuel, and close behavior. The default replay passed 32 VM tests and the
fixed-slot builder passed its replay. All observed command groups closed
and scratch was removed. Independent review matched the tested source,
receipt pins, and compile arguments for the current and earlier modes.
[First composed replay](verification/receipts/l03-swift-enum-typed-throws-composed-2c3cf5e0.json) ·
[Reproducibility receipt](verification/receipts/l03-swift-enum-typed-throws-reproducibility-160fb742.json)

The native Swift escaping-closure probe read its capture across repeated
turns. Exact frames showed deinitialization on replacement and explicit
release, and late invocation kept the release frame unchanged. The exact
reviewed source emitted an Embedded Swift object in each capture mode.
The import-free Wasm linker reported undefined `posix_memalign` and
`free`. No guest session ran. The original and exact-source receipts
record 28 and 14 terminal command groups, respectively, with scratch
removed. L03 remains open.
[Exact closure replay](verification/receipts/l03-swift-escaping-closure-final-object-0ed34547.json)

An opt-in link with the pinned Swift 6.3.3 WASI `libc.a` supplied
`posix_memalign` and `free` from `dlmalloc.o`. Both closure fixtures
retained zero imports and memory fixed at one page. The shipped Guest UI V1
VM matched their native frames, including a refused invocation and two
replacement and release cycles. The object variant observed four
deinitializations across those cycles. The highest accepted turn used
1,071 of 1,000,000 fuel. Retirement refused stale handles and a fresh
session opened with a clean frame. Independent review checked the
archive, fixture, and VM pins. Runtime readback comes from the experiment
receipt. Default linking still refuses both symbols. That closure experiment
left heap exhaustion and block reuse unmeasured.
[Stock SDK allocator experiment](verification/receipts/l03-swift-sdk-allocator-abadfffa10.json)

The closure replay's `--stock-wasi-allocator` option reproduces
the no-library refusal before linking with the pinned archive. Two fresh
runs per fixture reproduced the object and Wasm hashes and matched native
and owned VM frames. The default replay and all 32 VM tests passed.
Independent review checked the selector, archive admission, link order,
and receipt. The support matrix now records the two scoped guest fixtures.
[Maintained allocator replay](verification/receipts/l03-swift-stock-wasi-allocator-replay.json)

The dynamic result-builder replay also uses the pinned WASI allocator
when explicitly selected. Two corrected runs produced identical
12,559-byte Wasm. The unsigned one-page guest matched native frames,
preserved the prior frame on a four-child refusal, and reclaimed its
session slot. The highest accepted turn used 2,783 fuel. The initial
frame comparison reached retirement, where the harness expected a
closure-only receipt. The corrected harness requires both closure and
slot reclamation. Default, fixed-slot, and closure regression modes
passed. The ordinary dynamic builder still reports both unresolved
allocator symbols without the archive.
[Dynamic builder replay](verification/receipts/l03-swift-result-builder-stock-wasi-allocator.json) ·
[Initial harness failure](verification/receipts/l03-swift-result-builder-stock-wasi-allocator-initial.json) ·
[Regression results](verification/receipts/l03-swift-result-builder-stock-wasi-allocator-regressions.json)

A separate allocator control passed in two installed Guest UI V1
sessions. Nine 4,096-byte allocations aligned to 64 bytes succeeded.
The tenth returned WASI `ENOMEM`. Freeing a middle block let a same-size
retry reuse its address, with the survivor and replacement canaries
intact. Drain freed all live blocks. Every turn stayed at one page and
zero host calls, with 6,785 fuel at most. The stale handles were refused,
and a fresh generation started with identical bytes. Independent
review confirmed the pinned source and reconstructed the recorded
observations. The author recorded 22 closed command groups and scratch
removal. The initial SDK header and host compilation failures occurred
before runtime. The captured runner remains historical.
[Allocation recovery receipt](verification/receipts/l03-guest-allocator-release-followup-abadfffa10.json) · [Initial setup failures](verification/receipts/l03-guest-allocator-release-abadfffa10.json)

The maintained allocator control requires the exact VM archive and
allocation outcomes. Its fresh run reproduced both sessions and observed
all 25 command groups close. The receipt is published without replacing
prior evidence. Independent review compiled the host assertions and
passed all 11 inert controls. The observed Wasm and runtime output
digests match the historical pass.
[Strict allocator receipt](verification/receipts/l03-guest-allocator-release-strict-abadfffa10.json)

A fresh independent run used the checked-in replay command with a pinned
sparse checkout. It reproduced both sessions and the exact VM archive,
guest Wasm, and runtime stdout digests. All 25 command groups closed.
The disposable checkout and scratch were removed.
[Maintained allocator replay readback](verification/receipts/l03-guest-allocator-release-maintained-root-abadfffa10.json)

The paired allocator diagnostic reproduced the fixed-page control and
grew a separate Guest UI V1 guest from one page to two. Allocation 10
preserved all nine existing canaries. Attempt 26 returned `ENOMEM`
with 25 live blocks. The guest reused the freed address and drained
all blocks. Both sessions had zero host calls and refused retired handles.
Independent review confirmed the strict runner requires these outcomes
and verifies its helpers before loading them. The author recorded 36
closed command groups for the corrected replay. A fresh root replay
matched both Wasm digests, the exact VM archive, and the growth stdout.
All 36 command groups closed again and scratch was removed.
[Initial growth run](verification/receipts/l03-guest-allocator-growth-d14ca99c.json) ·
[Strict paired replay](verification/receipts/l03-guest-allocator-growth-strict-41a05264.json) ·
[Independent replay](verification/receipts/l03-guest-allocator-growth-maintained-root.json)

Swift 6.3.3 verified the actor-isolated checklist counter on macOS with
an explicit native SDK and target. A synchronous call from outside the
actor failed at compile time. The Embedded Wasm target refused the tested
`@MainActor` async entry and could not load `_Concurrency` when imported
explicitly. Both guest compilations stopped before object emission.
Independent review matched the receipts, scope, and existing selectors.
[Actor boundary replay](verification/receipts/l03-swift-actor-isolation-5aafc1a7.json)

Swift 6.3.3 expanded the same synthetic checklist macro in native and
Embedded Swift. The 1,268-byte guest ran through the strict Guest UI V1
session with zero imports and one fixed page. All six frames matched,
both refusals preserved the prior frame, and retirement reclaimed the
slot. The missing-plugin control diagnosed the original call site
before object emission. Independent review verified the replay custody
fix, and a fresh root replay confirmed closure for all 20 command groups
and removed owned scratch. Rebuilt Wasm bytes differ across these runs.
[Macro replay](verification/receipts/w07-l03-checklist-macro-maintained-root-98ef1420.json) ·
[Runner correction](verification/receipts/w07-l03-checklist-macro-custody-41a05264.json)

Swift 6.3.3 selected two checklist formatter conformances through a
protocol existential on macOS. Embedded Swift refused the same fixture at
its source location before emitting an object. A static variant replays
the same events in Guest UI V1, matches all nine native frames, and
refuses the retired handle after close. The canonical runner passed
seven focused controls, three publication regressions, and the owned VM
replay. All 26 nested command groups closed.
[Checklist formatter fixture](compiler/experiments/checklist-existential/README.md) ·
[Canonical replay](verification/receipts/w07-l03-checklist-existential-canonical.json)

The current FieldLog Android APK ran five checklist scrolls at each of
20 and 1,000 tasks on an isolated 60 Hz API 36 arm64 emulator. Each
trial started the ordinary activity cold, verified its expected first
page, revealed new rows by swiping, and preserved the workspace bytes.
For 1,000 tasks, the median of five graphics frame p95 observations
was 17.54 ms, with a 17.49–55.73 ms range. Activity Manager cold launch
time was 229 ms at the median, and median process RSS was 190.95 MiB.
Timing varied within both datasets. This evidence covers
`FrameCompleted − IntendedVsync` for the first 20-row page. The
packaged signed guest contains 7,606 Wasm bytes and 2,055 bytes of
manifest and assignment metadata. All owned groups closed.
[Native measurement](verification/receipts/fieldlog-api36-checklist-measurement-e39a5ea3.json) ·
[Setup and partial attempts](verification/receipts/fieldlog-api36-checklist-measurement-attempts.json)

The Entry Commit guest's 16 varying bytes came from Swift's
`.swift_modhash` segment. Changing the absolute object output path changed
that segment, and relinking the same object preserved the Wasm bytes. The
fixture now writes the exact Entry Commit object through stdout. Two fresh
output directories reproduced the same 7,606-byte module in the composed
checkout. The producer's owned VM runs reached **Committed once** and closed
their sessions. Independent review verified the other five fixture variants
and the package boundary. The ordinary APK recipe still pins the earlier SDK
checkout. A package using this module needs the updated checkout and freshly
signed release material.
[Entry Commit reproducibility and VM receipt](verification/receipts/l03-l08-fieldlog-entry-commit-reproducibility-d7ab346e.json)

A compact Swift event trapped at function 3, byte 514 in the owned VM.
The matching line table resolved that position to `SwiftEventGuest.swift:32:9`
and LLVM agreed. Stripped and mismatched inputs preserved the raw trap
coordinates and withheld the source location. Independent replay confirmed
all four owner closures. This covers one macOS host diagnostic.
[Swift trap replay](verification/receipts/w15-l03-v79-swift-event-diagnostic.json)

The signed installed host emitted the same trap after its second routed
event. Both variants reported function 3 and Wasm byte 514. The matching
variant reported the Swift line, and the separately signed stripped variant
returned no source location. Both retired, disabled input, and reopened
to native fallback. Independent offscreen macOS verification passed three
selected tests. Swift Wasm hashes varied across scratch paths.
[Signed diagnostic replay](verification/receipts/w15-l03-signed-installed-swift-event-diagnostic.json)

The maintained WebAssembly Core replay reproduced ten exact returns, three
traps, and six invalid-module refusals on arm64 macOS. The Rust CLI and the
installed V3 session C ABI agreed on the selected upstream cases. Guest UI v1
coverage consists of admission refusals. The replay used a private Git export,
and all 79 command groups closed. [Replay commands](vm/verification/standards-replay/README.md) · [Integration receipt](verification/receipts/l03-standards-replay-integration-9f4acf56.json)

The maintained stateful replay ran five consecutive upstream memory
assertions in one installed V3 C session on arm64 macOS. Mixer and WABT
agreed on memory growth, initial zero bytes, the store and its readback,
and a fresh instance with zero prior pages. The full upstream block
traps on the first zero-page access in both runners. Mixer then reports
a terminal session, while WABT continues. Independent replay passed the
selected sequence, the 19 existing assertions and six runner controls.
[Stateful memory replay](verification/receipts/l03-stateful-memory-e414fa1a.json)

The maintained replay also runs an unchanged upstream overlapping
`memory.copy` block. The installed V3 C session and WABT read address
12 as 7 before the copy, 2 afterward and 7 in a fresh instance.
WABT passed all 35 commands. The existing 19 assertions and seven
wrapper tests passed. All 91 replay commands closed and owned scratch
was removed. Guest UI V1 refused admission of the same module.
[Overlapping copy replay](verification/receipts/l03-memory-copy-installed-v3-f6cc4ae0.json)

The replay now also uses stock WABT to execute the 19 independent
return and trap assertions in fresh instances. Six calls from the
pinned `elem.wast` covered initialized slots, an overwritten slot and
a null slot across three unchanged upstream modules. WABT, the Mixer
CLI and the installed V3 C ABI agreed on all 19 outcomes. Both stateful
memory groups, all six invalid cases and eight runner controls passed.
Independent replay verified the module and reference manifest hashes.
The installed Guest UI V1 check still covers admission refusals.
[Core element and reference replay](verification/receipts/l03-wabt-table-elements-60b8656a.json)

The installed V3 C session and stock WABT also ran two overlapping
`memory.fill` operations through one unchanged upstream export. Five
readbacks checked every byte of the resulting page. The overwritten
four-byte range read zero before the fill and in a fresh session.
WABT passed all 10 checks, and both omission controls failed at the
expected ranges. Independent replay confirmed the same behavior,
125 terminal command groups and all eight wrapper controls. The
default fuel limit and VM product source stayed unchanged.
[Stateful memory fill replay](verification/receipts/l03-stateful-memory-fill-f98f3297.json)

The pinned upstream branch-table module uses a value type outside the
Mixer V3 profile. WABT ran all ten selected assertions on that original
module. An excerpt preserves the exact scalar function and assertion
text. All ten passed through WABT, the Mixer CLI, and the installed V3 C
session. Four indexed targets returned 213 through 210. The first
default index and unsigned high indices returned 214. Independent
replay matched the Wasm and VM archive hashes and observed 154 terminal
commands. All eight runner controls passed.
[Scalar branch-table replay](verification/receipts/l03-w08-br-table-3488ef30.json)

The installed V3 C session and WABT also passed the pinned growth
block with a declared ten-page maximum. Growth reached ten pages, and
two further requests returned `-1`. A fresh instance started at zero
pages. All 156 commands closed and eight runner controls passed.
Independent replay matched the exact source, Wasm, and outcomes.
[Declared memory maximum replay](verification/receipts/l03-w08-memory-maximum-603d33d9.json)

The upstream indirect-call module uses three tables, outside the V3
single-table profile. Stock WABT passed the selected original assertions.
A line-preserved single-table excerpt returned `-1` and trapped with
`indirect_call_type_mismatch` and `table_out_of_bounds` in fresh WABT,
Mixer CLI, and installed V3 C instances. The independent replay closed
all 173 subprocess groups, and all eight runner controls passed.
[Indirect-call replay](verification/receipts/l03-w08-call-indirect-9d96980f.json)

The installed V3 C session read integer globals initialized to -12 and
-15, ran the two upstream setters, then read 6 and 7 in the same instance.
A fresh instance read -12 again. WABT passed the same scoped assertions in
the original fixture and line-preserved excerpt. The independent replay
closed all 185 commands and passed all eight wrapper tests.
[Scalar-global replay](verification/receipts/l03-w08-scalar-global-f00921a63.json)

Seven original upstream `f32.nearest` cases matched exact result bits in
stock WABT, the Mixer CLI, and the installed V3 C session. The cases
cover both signs of zero and halfway values that round to the even
integer. The independent arm64 macOS run closed all 211 replay commands
and passed eight wrapper tests.
[Float rounding replay](verification/receipts/l03-f32-nearest-145b8648.json)

Eight upstream signed and unsigned `i64` to `f32` conversions matched
all 32 result bits in WABT, the Mixer CLI, and the installed public V3
C ABI. The original module was admitted unchanged. Independent replay
passed all 43 selected cases and eight wrapper tests. The earlier
35 outcomes, CLI, installed archive, and four public headers matched
the baseline. L03 and W08 remain open.
[Integer-to-float conversion replay](verification/receipts/l03-w08-i64-f32-d6f8b57f.json)

The original upstream i64 bit-count module passed six assertions for
zero and high-bit inputs in stock WABT, the Mixer CLI, and the installed
V3 C ABI. The independent review matched all 43 prior outcomes and all
five stateful sections. This extends local W08 replay coverage.
[Bit-count replay and review](verification/receipts/l03-w08-i64-bit-count-independent-review-5f922bd6.json)

The maintained W08 replay now covers both directions of overlapping
memory copy. The unchanged upstream module copies seven bytes from
address 10 to 12. WABT passed all 35 manifest steps, and the installed
public V3 C ABI matched all 30 byte assertions. In both runners address
12 read 7 before the copy, 0 after it, and 7 in a fresh instance. An
independent replay matched all prior outcomes and passed all eight
wrapper controls. The candidate used all 256 command slots. This is
arm64 macOS V3 session evidence.
[Higher-address copy replay](verification/receipts/l03-w08-memory-copy-higher-address-554515a3.json)

The four upstream binary64 min and max assertions passed in WABT, the
Mixer CLI and the installed V3 C session. Both operand orders preserved
exact input bits. Minimum returned negative zero and maximum returned
positive zero. The independently repeated host replay matched all prior
outcomes and passed all eight wrapper controls. The test wrapper used
270 command slots, up from 256. The VM runtime limits were unchanged.
[Binary64 signed-zero replay](verification/receipts/l03-w08-f64-signed-zero-ccb5221c.json)

Seven pinned binary64-to-i64 truncation assertions matched exact
result bits in stock WABT, the Mixer CLI, and the installed V3 C ABI.
The cases cover fractional inputs, the signed limits, and unsigned
results with the high bit set. The independent review matched all 53
prior assertion outcomes. The integrated run completed 284 commands,
passed all eight wrapper tests, and removed scratch.
[Binary64-to-i64 replay](verification/receipts/l03-standards-f64-i64-truncation.json)

Ten original WebAssembly i64 assertions now check the shift count
boundary and sign propagation. WABT, the CLI, and the installed
C session ABI matched the exact 64-bit results. All 60 preceding
cases and six stateful sequences matched. All 304 commands closed.
[i64 shift replay](verification/receipts/l03-w08-i64-shifts-926f6d94.json)

The seeded TableMemoryV3 check retains one instance for 40 copies on
each of 24 seeds. Mixer and Node matched all 960 observations of the
complete initialized region in Debug and Release. The separate
reset-between-calls control failed on seed 1's second call. The
maintained parser still counts all 2,996 independent cases in each
mode, and the stateful counts are reported separately.
[Seeded stateful reference replay](verification/receipts/l03-stateful-node-copy-3292cdfa.json)

The hosted VM job passed. Swift host and Intel bootstrap refused the
WAST inventory edit because Source141 still pinned the old bytes. The
corrected archive binds the new inventory and keeps the 157 selected
source inputs. Both workflow projections passed admission in normal
and optimized Python. The Source141 and Source127 restores matched
their 890 and 845 files by bytes and modes.
[Hosted result](https://github.com/snowdamiz/mixer/actions/runs/44965471303) ·
[Archive verification](verification/receipts/source141-stateful-wast-notice-admission-839fed77.json)

The repaired revision `491d708b7d` passed all nine Owned Engine jobs.
Swift preflight, optimized preflight, and postflight admitted all 157
files. Intel passed bootstrap and the six Java/D8 consumers with
byte-identical DEX, terminal custody, and both scratch trees removed.
[Hosted repair verification](https://github.com/snowdamiz/mixer/actions/runs/44968626012)

The installed Guest UI v1 validator refused all 616 single-bit mutations
of three required export names in each host build profile. Each refusal
used zero guest fuel and host calls and retained zero caller-thread
allocation bytes. All 16 session slots opened and closed afterward.
This control covers one pinned seed. Continuous fuzz qualification
remains open. [Mutation replay](verification/receipts/l03-guest-ui-v1-export-mutation-7a9b6516.json)

The arm64 macOS Guest UI V1 C test admitted an original one-page guest and
executed three host-written events. Two `br_table` entries and the default
selected distinct frames through little-endian `i32.load16_u` reads. The
default read used the last two bytes of the page. Each event used 24 of 64
fuel and made zero host calls. The host matched all three frame documents,
closed each session, and confirmed all 16 mixed registry slots were reusable.
The test covers the native ABI. Signed activation and presentation remain
outside this receipt. [Guest UI V1 execution](verification/receipts/l03-guest-ui-v1-execution-v77.json)

A separately signed guest used the same branch selectors through installed
Guest UI V1 and offscreen macOS presentation. Host events 0, 1, and 9
produced the expected decoded revision-2 documents. A same-length payload
mismatch returned an integrity error and the cold owner showed native
fallback with input disabled. Four focused tests passed independently, and
all four owners retired and released their reservations. Device coverage
remains open. [Signed presentation replay](verification/receipts/l03-guest-ui-v1-signed-branch-v78.json)

The compiler qualification recorder now preserves the cleanup error and
observed log sizes when custody is unknown. All 14 compiler support
tests passed in normal and optimized Python. The earlier hold for PID
99218 remains active. [Recorder verification](verification/receipts/l03-qualification-recorder-custody-f13d6dab.json)

The original FieldLog EntryEditor refused a blank-title Commit with its
100,000-byte draft intact and zero new entries on macOS. The full Swift
WASI development replay matched that refusal. Compact Embedded Swift
stopped at the Foundation import, and the installed owned VM rejected the
full WASI module at its size check before any session started. Installed
editor parity remains open. [EntryEditor boundary](verification/receipts/fieldlog-entry-editor-blank-commit-v74.json)

The v74 host replay compiled the same FieldLog save decision into native Swift
and a signed Embedded Swift Guest UI V1. A blank restored draft launched no
save effect. Malformed date text kept **Check entry** available, and correcting
the date restored eligibility through the same action and selection lease.
Switching drafts revoked the old lease. The reopened workspace and attachment
bytes matched, and all three owners retired. The installed guest's durable
Commit and mobile execution remain open.
[Shared decision](verification/receipts/fieldlog-entry-save-decision-v74.json) ·
[Date recovery](verification/receipts/fieldlog-entry-save-invalid-date-v74.json)

The hosted v74 Android job stopped at debug export when its observer
rejected an inner receipt directory. The job retained the exact scratch
and recorded unresolved custody. [Hosted hold](verification/receipts/hosted-v74-android-debug-export-custody-hold-44863139576.json)

## November 19 local verification

The combined FieldLog iOS and Android storage patches passed 30 host checks across the compatible rollback and successor writers. An independent replay passed all 30 checks and 10 additional controls. The four writers refused newly introduced draft and entry ID overlaps, preserved edits to existing pairs, and recovered a complete snapshot after a write fault. [Composed storage receipt](verification/receipts/fieldlog-l08-cross-platform-draft-overlap-20261119.json)

The exact reviewed FieldLog writer preserved the saved follow-up flag during a signed rollback and ordinary draft save on macOS. The re-upgrade and fresh offline process recovered the same record, outbox, and JPEG. The archival control lost the flag. Both ordinary app recipes built on iOS and Android, and inspection showed that their target inputs omit the selected-draft adapter. Binding and installed mobile replay remain open. [Signed host replay](verification/receipts/fieldlog-l08-reviewed-signed-host-20261119.json) [Ordinary app builds](verification/receipts/fieldlog-l08-native-build-qualification-552559d2.json)

The signed FieldLog host kept the follow-up flag through an ordinary draft save while the rollback guest was active. The save advanced revision 3 to 4 and preserved record identity, JPEG bytes, the outbox prefix, and the restored draft. A fresh process reopened revision 4 with the re-upgraded guest from the installed cache. Mobile verification remains open. [Signed rollback receipt](verification/receipts/fieldlog-l08-signed-rollback-ordinary-save-20261119.json)

The newer signed Commit composition on `dbb9275d58` also passed the
optional-field rollback save on macOS. The older guest stayed healthy
while the ordinary editor saved from its stale draft copy. Revision 4
retained follow-up, the unrelated draft, JPEG, and outbox. A fresh process
resumed the rollback guest from disk and re-upgraded without writing again.
The replay uses a headless presentation witness and the current native
writer. Installed mobile and service delivery remain open.
[Current rollback save](verification/receipts/fieldlog-signed-rollback-ordinary-save-dbb9275d.json)

The local release origin gave one Android installation its own signed offer for each of two recorded runtime fingerprints. Both offers and artifacts survived restart byte for byte. The origin and Swift verifier refused cross-runtime delivery, and an unknown runtime received no offer. The original APKs were unavailable, so the replay used their pinned descriptors. Native binary replacement remains open. [Android runtime cohort receipt](verification/receipts/fieldlog-android-runtime-cohort-offers-501eca8a.json)

A same-signer Android FieldLog pair now has two distinct linked engine revisions and runtime identities. Both APKs passed signature, alignment, and package-version readback. The repeated host replay selected each signed offer and refused cross-runtime delivery across restart. Android in-place replacement and workspace continuity remain open. [Engine cohort pair](verification/receipts/fieldlog-android-engine-cohort-pair-20261119.json)

The FieldLog selected-draft adapter now links through the native targets. The Android development APK was packaged and matched the signed packet’s embedded identity and JNI bytes. The generic arm64 iOS build linked the adapter and bundled the signed material. The first iOS Simulator test build ran out of disk space. The next build passed. Independent extraction verified the arm64 Simulator app, XCTest runner signatures and test configuration. The host binding refused a revoked selection and kept the follow-up flag through an ordinary save and offline reopen. Installed rollback remains open on both targets. [Android package](verification/receipts/fieldlog-android-selected-draft-apk-20261119.json) [iOS build](verification/receipts/fieldlog-ios-selected-draft-bound-app-20261119.json)

The authenticated free iOS Starter build reached `native_succeeded` with one restricted Oban execution, one Xcode run, one capacity reservation and release, and unchanged billing rows. An independent read of the retained SQLite and artifact packet matched the closed operation, PostgreSQL terminal rows and all three artifact sizes and hashes. The fixture misread PostgreSQL’s `t` and `f` values and dropped the source database before the customer downloads or `pg_dump`. A complete backup, restore and authenticated artifact delivery remain open. [Closed Starter build](verification/receipts/l05-l07-native-starter-closed-20261119.json)

The rebuilt two-engine packet passed all 122 checksum checks. The owned API 36 run transferred the first APK, matched its digest on the emulator and installed version 24101 through Package Manager. The first UI hierarchy read timed out, leaving the emulator group and private ADB held. The release origin closed. Workspace continuity, version 24102 installation and runtime cursor verification remain open. [Staged install and UI custody](verification/receipts/fieldlog-android-engine-cohort-ui-custody-20261119.json)

A fresh same-signer FieldLog engine pair rebuilt both linked engine revisions from pinned public source. The arm64 APKs use package `dev.fieldlog.generatedr90`, versions 24101 and 24102, with distinct runtime fingerprints and signed sequence 7 and 1 offers. Four host VM, 35 origin HTTP, and 20 Swift verifier checks passed. Root verified all 45 sealed files again. On the first owned API 36 Google APIs install, Package Manager installed 24101, the installed APK hash matched, and Activity Manager launched it. The host text recognizer timed out on the first returned screenshot. The origin and UID log reader closed. The recognizer, private ADB and emulator remain held. A fresh Google APIs instance on a different private ADB server reached ADB and timed out waiting for Android boot completion. Its origin, private server and emulator closed and its scratch was removed. No replacement or workspace-continuity result follows from these two attempts.

On a fresh API 36 AOSP arm64 emulator at port 5574, the same 24101 APK staged and installed by hash, and Activity Manager launched it. Direct review of the Android screenshots observed the System UI unresponsive dialog over the app. One Wait action dismissed it. The native activity frame and checklist button appeared, while five subsequent screenshots showed an empty ordinary content surface. UID log readback showed activity creation, first draw, skipped frames, and a SurfaceSyncGroup timeout. The test did not create a task or install 24102. The reverse mapping, private ADB, origin, log reader and emulator all closed. The AVD was reclaimed. The pinned Activity gives up after its bounded window-focus readiness check. Launching after the system launcher has settled is the next discriminating check.

On a fresh API 36 AOSP emulator at port 5578, root verified four steady launcher-focus reads before launch. FieldLog rendered the ordinary view, saved task PumpCohort19 through the native form, and reached revision 2. Switching this disposable AVD to gesture navigation exposed the signed checklist button above the system controls. The old APK displayed signed sequence 7 and Open. The guest’s selected-task wire value contains the revision and completion bit. It carries no title. The replay incorrectly expected the title in the guest frame and could not advance automatically. A direct Done action closed effects, and the durable readback verified both health milestones and matched the signed artifact and payload. The workspace SHA-256 a876507ea6366ba8c9fcbc68b67cd19086f2113b70ba8118641530ae59c648b3 matched before and after closing, with installation 8d47b680-03a2-4d4a-9594-b27eb54f7a02. No replacement was installed. The observation bound expired before the original controller collected emulator and ADB teardown. The origin and UID reader closed. The corrected replay checks the visible status and binds the title through the exact native workspace readback.

The rebuilt selected-draft Android APK and its four signed assignments passed packet verification. One owned API 36 emulator booted, then the streamed APK install timed out before the launcher was observed. The install command, emulator and private ADB remain held with unknown custody. The independent release origin closed. Installed rollback remains open. [Android install hold](verification/receipts/fieldlog-android-selected-draft-install-hold-20261119.json)

A second authenticated free iOS Starter build reached `native_succeeded`, and the retained PostgreSQL dump, SQLite snapshot and three artifacts matched its terminal journal. A new cluster restored those records. After a fresh sign-in, Phoenix returned the build status, logs and all three artifact downloads. Independent readback matched sizes and hashes. The source session expired before completion. Plain `pg_restore` changed the rendered grouping of two authorization checks, so this fixture reapplied the pinned definitions before Phoenix admitted the restored catalog. The closed worker replay started no compiler. [Starter restore and downloads](verification/receipts/l05-l07-starter-restore-downloads-20261119.json)

A free owner built the registered iOS Starter through Phoenix, PostgreSQL, restricted Oban, and the native worker. One Xcode run completed and released its capacity reservation. A fresh authenticated session downloaded all three artifacts and checked their digests. Membership, permission, usage, quota, support, export, and organization exit checks passed with billing inactive. Exit was refused while the build was queued and succeeded after settlement, preserving the terminal records and artifacts and cutting off the former owner. A second tenant retained its access and data. One support read returned HTTP 503 and passed on retry. The combined run used the ordinary authenticated APIs. The browser administration run remains separate. [Free-owner build and exit](verification/receipts/l06-real-starter-7aeef847.json)

Chrome signed in two free owners and submitted one iOS Starter build through the ordinary console. Restricted Oban dispatched one Xcode run. A fixture sandbox blocked SwiftPM package resolution and Xcode exited 74. The final services closed. A separate zero-POST browser-driver attempt remains held. [Rendered Starter dispatch and custody](verification/receipts/l06-browser-starter-dispatch-20261119.json)

The selected-build page now offers the unsigned iOS build, debug symbols, and resource inventory from the current build detail. The console validates the destination against the exact selected build before rendering a download. All 300 console tests passed. Chrome sent the loopback session cookie and saved three synthetic attachments with matching sizes and hashes. Hosted selection v43 verified 407 owning inputs in normal and optimized Python and preserved the pinned Rust fixtures. Six workflow sparse projections and 51 focused collector tests in each Python mode passed locally. The full hosted collector and the rendered journey with an actual successful build remain pending. [Console attachment replay](verification/receipts/console-build-artifact-links-browser-20261119.json)

The Phoenix foundation client compiler reproduced TypeScript TS2769 on the console artifact parser. The parser now uses URLSearchParams.forEach, which passes the workflow’s standalone TypeScript 5.9.3 compile with ES2022 and DOM libraries. It still validates the exact selected build query before constructing a download link. Hosted selection v44 binds the single source change and the installed archive verifies its workflow update in normal and optimized Python. All 300 console tests passed with serial Node execution, and the production console built. The three focused collector classes passed 43 tests in each Python mode. Hosted workflow completion and the rendered Starter journey remain open. [Original Phoenix job](https://github.com/snowdamiz/mixer/actions/runs/44573984514/job/135736362140)

The subsequent rendered Starter attempt received a secure session cookie for tenant B, then received four HTTP 503 responses from the session endpoint across eight visible retries. The browser sent zero organization requests and zero build POSTs. All 55 recorded command groups closed, the fixture database was removed, and all eight ports were reusable. The cause of the session refusal and rendered Starter completion remain open.

At `72d135441ea5b50dbcf87902252e0c05e1e3b179`, a fresh ordinary Phoenix fixture on PostgreSQL 17 admitted the zero-organization account with the stock browser and build-create catalog roles. The same post-callback cookie returned authenticated HTTP 200 directly in 288 ms and through the local-workspace-builds TLS proxy in 580 ms. The proxy response matched its Phoenix request, and RuntimeOwner stayed storage-ready at generation 1. A fresh Chrome login displayed **No organizations yet** after authenticated session reads and an empty organization list. No build requests or jobs were created. All owned groups closed, all seven ports rebound, and fixture scratch was removed. The earlier browser 503 did not recur. The creation control and rendered Starter build remain unverified by this run.

The local rendered Starter fixture verified PostgreSQL startup after setting LC_ALL=C and passed the stock cancellation admission check. Phoenix stopped the test before Chrome or the worker started because the fixture omitted the six workspace-writer policies required by builds_v1. No build request was sent. The next fixture uses SelfServiceSchema.processor_policy_statements/0. In the separate L07 worker run, the locked dependency acquisition passed, PostgreSQL and Phoenix started, and the sole authenticated Starter request returned HTTP 201. The relay timed out before the observer could prove compiler closure or native_ready. Phoenix, restricted Oban and PostgreSQL closed. The worker remains held. Settlement, restart and artifact delivery remain unverified by that run.

The next Chrome fixture installed all six stock workspace-writer policies and admitted Phoenix and the restricted Oban processor. Chrome signed in and created the empty free organization through HTTP 201. The driver then timed out at the project form. A fresh replay timed out during navigation before sending any API request. No build POST, native worker or Xcode ran. Owned processes and ports closed. A separate L07 transport preflight passed authenticated query, ensure_started and query through the same local relay as the normal adapter. It withheld exactly one inert terminal response while an independent request still succeeded. Receiver timeout and later terminal readback behaved as expected. The fixture covered preflight_failed, and the real native_ready response remains open. Immediate worker port rebinding refused EADDRINUSE. The next real restart requires a fresh upstream port behind the stable relay or a verified database barrier.

A separate PostgreSQL 17.11 control reproduced the CHECK expression rewrite after a dump and restore between two independent clusters. Reapplying the original definition in one transaction restored the exact catalog expression and preserved existing rows. All three invalid insertions were refused. This test used a synthetic table. [CHECK round-trip control](verification/receipts/l07-postgres-check-roundtrip-20261119.json) Plain restore of the retained Starter backup reproduced the two catalog mismatches. A separate transaction restored all 80 CHECK expressions to their pinned form and preserved the readback from ten relations. Running it twice preserved the repaired constraint identities. An unexpected second expression rolled back the transaction, including the first replacement. Phoenix readback comes from the earlier restored fixture. [Retained Starter CHECK repair](verification/receipts/l07-starter-raw-check-repair-20261119.json)

A clean-checkout replay on PostgreSQL 17.11 restored the two pinned expiry CHECK expressions from the checked-in authorization migration and catalog manifest. The repair preserved four seeded rows, refused all six invalid updates, and kept both constraint identities on a second run. An unexpected second constraint rolled back the first replacement. All 30 command groups and both clusters closed, both ports were reusable, and the disposable directory was removed. The current run checked PostgreSQL directly. The earlier Starter restore covers authenticated service readback. [Local hosted restore and replay](docs/operations/restore-local-hosted.md)

The tracked public update replay now restores a halted release into a freshly initialized PostgreSQL cluster. Run the commands in the public update guide with `--postgres --restore-after-halt`. At source pin `72d135441ea5b50dbcf87902252e0c05e1e3b179`, Swift 6.4.2, Go 1.26.4, and PostgreSQL 17.11, normal and optimized Python confirmed distinct cluster identifiers, exact sequence-5 audit and outbox rows, the original halt response on retry, and denial of a foreign tenant. Restored promotion to sequence 6 served the same signed assignment, manifest, and payload for both eligible cohorts. The excluded cohort still received HTTP 204. Promotion preserved all earlier audit, outbox, and idempotency rows, and the source database snapshot stayed unchanged. Both clusters and all origin instances closed and their scratch was removed. The PostgreSQL replay without restore and the file-store replay also passed. Hosted build-journal recovery and the remaining L07 checks are separate. [Public update replay](tests/integration/public-update/README.md)

The concurrent native attestation test passed on macOS arm64 with Go 1.27.1. Separate signer processes with different ephemeral development keys each fetched the same test build and all three artifacts through the loopback fixture. The shared state directory retained one envelope. The winner’s pinned public key verified it. The losing key was rejected before sending an HTTP request. The package suite passed once normally and ten times under the Go race detector. The test covers duplicate publication after both signers observe empty state. Concurrent custody of a key against an untrusted worker under the same OS account remains open. [Local native build attestation](services/cmd/mixer-native-attest/README.md)

Two disposable Phoenix fixtures exhausted both browser lifecycle connections. All ten authenticated build requests received HTTP 503 before BEGIN. RuntimeOwner stayed ready, and the existing session, same-key replay, build read, and exact-once creation recovered without a listener restart. Both fixtures closed. The forced saturation check leaves mixed checkout outcomes under natural contention open. [Bounded checkout recovery](verification/receipts/l07-bounded-checkout-recovery-c2bae0e5.json)

The Starter preparation stopped before its single build request when shared disk space fell and Xcode peak use was unknown. A focused Elixir replay verified both pinned relation manifests with Oban in the separate Phoenix checkout at `hosted/deps`. Alternate-only dependency placement and modified pinned bytes still failed. The full Phoenix/native capture and backup remain open. [Starter preflight](verification/receipts/l05-l07-starter-prepost-relation-path-20261119.json)

A macOS FieldLog layout probe received the accessibility text size, but its semantic fonts stayed the same size. Explicit 53-point fonts grew the Arabic and English content beyond the test viewport. The initial signed run stopped at a manifest route error. All six corrected loopback routes passed, and signed activation and native reachability remain open. [Localization scale probe](verification/receipts/fieldlog-localization-scale-c2bae0e57.json)

The corrected macOS replay served both signed FieldLog checklist versions through loopback and activated Arabic at sequence 2 under the same installation and runtime. Native accessibility readback confirmed right-to-left alignment and 16 points of additional wrapping at the narrower viewport. The saved workspace bytes stayed identical through the language change. Two native button presses delivered guest events. The harness applied the corresponding completion and reopen through the real repository, preserving the task ID and title and appending two outbox records. The modeled iOS text size grew from 17 to 53 points, while the macOS title and button dimensions stayed the same. Installed iOS and Android localization and large-text reachability remain open. [Signed localization replay](verification/receipts/fieldlog-localization-signed-macos-20261119.json)


The reproducible Arabic Android checklist guests passed in the host VM with FieldLog's ordinary task storage. The reviewed guest required confirmation. Completion and reopen each advanced the workspace revision and outbox once, and both states survived repository restart. Review reproduced deletion of unresolved compiler scratch on wrapper exits 0 and 1. The corrected replay retained scratch on each injected build failure and recorded a hold when the file was writable. The corrected host run reproduced both Wasm payloads, closed all five command groups, and removed build scratch. Signed installation, the Android layout comparison, and native offline readback remain open. [Host replay and cleanup receipt](verification/receipts/fieldlog-android-localized-replay-cleanup-20261120.json)


One owned Android 36 emulator ran both signed Arabic checklist releases on the same APK, runtime and installation. All six captures showed the full title and digits 07 at 1× LTR, 1× RTL and 2× RTL. The title glyph height grew from 47 to 71 pixels. At 2× RTL, confirmation left the workspace unchanged. Completion and offline reopen each appended one outbox row for the same task. Two cold launches without an origin recovered the completed and reopened states. Some accessibility reads were unavailable, so the regular reviewed layout used raster evidence. The origin and private ADB server closed. The emulator exited, but its process group was not confirmed absent and the exact scratch remains held. [Installed Arabic checklist receipt](verification/receipts/fieldlog-android-localized-native-20261120.json)

Independent review confirmed the installed task and offline readbacks. The host launcher mirrored between LTR and RTL, while the Arabic guest text stayed right-aligned. The first run left the reviewed 1× accessibility action and final guest retirement unverified. Host controls accept a successful newline-only ADB reverse list and wait for confirmed process-group absence after the direct child exits. [Host teardown receipt](verification/receipts/fieldlog-android-localized-teardown-host-20261120.json)

A fresh Android 36 emulator accepted one install and both signed Arabic releases. At 1× text size the review control was enabled and clickable. The confirmation screen preserved the saved task before the write. Completion and reopen each added one outbox row, and both values survived separate cold launches without an origin, default route, or ADB reverse mapping. **Done** returned to the ordinary checklist. The journal kept the same healthy sequence 2, cleared the attempt, and recorded `effects_closed`. The installed APK and final workspace matched their expected bytes. All four command groups closed, all four ports were reusable, and both fresh attempts' scratch was removed. The original emulator hold remains in force. [Native retirement receipt](verification/receipts/fieldlog-android-localized-retirement-20261120.json)

The iOS Arabic checklist XCTest typechecked with the iPhoneSimulator 27.2 SDK. The prepared guest pair passed 11 signing and refusal controls. Independent review found that the descriptor still used the rotation build's link and fallback digests, and that the inherited probe and readback need localization-specific assertions. The signed scratch was removed. Generic bundle and Simulator verification remain pending. [iOS protocol control](verification/receipts/fieldlog-ios-localized-preimage-protocol-20261120.json)

The corrected fixture binds its link and fallback inventories to the localized sources. Fresh signing, all 11 verifier controls, six developer-origin publication controls, and the localized loopback smoke passed. The macOS installed-owner probe loaded both Arabic releases on the same installation and retired both owners. Revoked and wrong-runtime offers left workspace and recovery bytes unchanged. The corrected generic arm64 iOS Simulator app, XCTest runner, and test bundle passed strict ad hoc signature and Mach-O platform checks. The generated plan permits the exact localized selector and embeds all six expected signed files. That build verified the bundle and dispatch plan before device execution. [Signed host receipt](verification/receipts/fieldlog-ios-localized-signed-host-20261120.json) · [Generic build receipt](verification/receipts/fieldlog-ios-localized-generic-20261120.json) · [Replay guide](tests/integration/fieldlog-localized/ios/README.md)

One fresh iOS 27.0 arm64 Simulator installed the signed Arabic checklist and accepted sequence 2 without reinstalling. The guest showed the full title and digits `07` in LTR, RTL, and the largest accessibility size. The RTL guest title grew from 22.33 to 69.00 points in each release. The enclosing navigation title ellipsized at that size. Review left the workspace unchanged. One confirmation advanced revision 2 to 3 and appended one `taskSaved` for the same task. A cold launch without the data listener reopened the completed sequence-2 checklist, and Done returned to the same task. The first attempt missed the bidirectionally isolated accessibility label before any offer request. The corrected XCTest used the stable task identifier. Both disposable devices were removed and all 13 observed external Simulator states matched at all checkpoints. [Installed iOS localization receipt](verification/receipts/fieldlog-ios-localized-native-20261122.json)

The signed Apple V1 host now gives tall checklist documents a vertical viewport and centers documents that fit. The AppKit regression clicked the Arabic `task.toggle` action after 49 points of native scroll at 16 points high and 33 points at 32 points high. At 96 points, the first clickable row stayed at 16 with zero scroll travel. Both tested text-size settings produced the same results. Positive native display observation awaits a host window that AppKit reports as unoccluded. Installed iOS Simulator and Android qualification remain open. [Signed AppKit reachability](verification/receipts/fieldlog-signed-apple-overflow-6d612a.json)

The engine workflow passed all nine jobs on the retained Swift probe correction at `6e136eddd4`. The Android generated-Java job passed its bootstrap and sparse checks, then completed the actual six-consumer integration and uploaded its evidence. The authenticated native Starter capture remains open. [Hosted CI receipt](verification/receipts/starter-worker-swift-probe-hosted-ci-20261119.json)

Two hosted Swift fixtures refused the runner after its default Rust advanced to 1.100.0. The analyzer envelope and shared cache fixture now install and resolve their exact arm64 Rust 1.99.1 in a temporary rustup home. The official compiler matched the pinned binary hash and verbose identity. Installed source checks passed in normal and optimized Python, and reverting either launcher reproduced its exact source refusal. The full historical workloads await hosted execution. [Compiler selection receipt](verification/receipts/hosted-swift-fixtures-rust-pin-20261119.json)

An inert replay against the unchanged native worker verified the revised observer. It waited for `absent/0` to become `running/1`, then matched the preflight failure to its authenticated closure diagnostic. Missing or mismatched terminal evidence blocked reuse, and an uncertain restart refused a contender and shutdown. An independent replay matched those results. The actual Starter build and backup remain open. [Worker observer replay](verification/receipts/l05-l07-native-observer-inert-20261119.json)

The clean-provenance Starter replay kept all 284 source entries unchanged and symlink-free before the request. The sole authenticated request returned HTTP 201, and restricted Oban committed one coordinator start. The observer stopped on a worker ledger row in `absent` state before confirming dispatch. Worker custody remains unknown and the exact resources are held. Compiler launch, capacity release, artifact reads, and a matching backup remain unverified. [Clean-provenance attempt and custody hold](verification/receipts/l05-l07-observer-worker-custody-20261119.json)

The corrected CLI passed worker admission during one ordinary authenticated Starter request. Restricted Oban recorded one start and released capacity after terminal failure. The fixture had placed Phoenix's build cache under the compiler provenance root, so source hashing refused a symlink before Xcode. [Starter settlement receipt](verification/receipts/l05-l07-retained-worker-settlement-20261119.json)

Both Android storage writer variants passed host saves and linked arm64 Swift and JNI products. Independent review verified that an older selected-draft adapter cannot access a replacement after committed deletion. A raw transaction can still introduce an overlapping draft and entry ID. [Storage and identity checks](verification/receipts/fieldlog-l08-storage-identity-and-android-20261119.json)

The private F01 host profile configured interactive keyboard dismissal from the historical FieldLog change. Installed older profiles and Android refused the new operation. Signed selection and the iOS keyboard gesture remain open. [F01 host comparison](verification/receipts/fieldlog-f01-scroll-host-profile-20261119.json)

The retained iOS build now runs the worker's Swift version probe as `/usr/bin/swift --version`. The compiled CLI produced an absolute-path terminal receipt, and the worker settled the deliberate pre-compiler veto and accepted shutdown. Ordinary CLI commands still resolve Swift through PATH. The archive admits the corrected source and refuses the relative-probe predecessor. [Compiled preflight and archive verification](verification/receipts/l05-l07-worker-swift-probe-20261119.json)

The D2 source audit matched the iOS 27 and Android 16 conflict runs to the same FieldLog task contract and SQLite backend. Both native runs retained the local title and peer assignee at version 3 with two committed events. The apps used separate workspaces, platform adapters, and SDK revisions. A fresh host replay reached version 4 after a lost acknowledgement and another offline edit. [Source sharing and paired workflow](verification/receipts/fieldlog-d2-task-conflict-source-sharing-20261119.json)

The measured export targets list 14 distinct app-owned Swift inputs. Three
are byte-identical across the two targets, including two directly shared
logic inputs. The shared UI input is listed by both targets, and its
Android runtime use remains unverified. The iOS and Android exports use
different FieldLog trees and SDK revisions. The whole-app sharing target
remains unassessed.
[Source-sharing report](docs/fieldlog-d2-source-sharing.md) ·
[Measurement receipt](verification/receipts/fieldlog-d2-app-source-sharing-v82.json)

The reviewed signed Commit FieldLog tree `380e764598` built as an unsigned
arm64 iPhoneOS app against Mixer `dbb9275d58`. Xcode compiled 15 app-owned
Swift inputs. The maintained Android recipe refused that SDK revision before
project creation. Six files match between the iOS compiler inputs and the
Android signed build manifest. A real Android compile is still needed for a
matched measurement and the whole-app sharing assessment.
[Matched-target attempt](verification/receipts/fieldlog-d2-matched-targets-dbb9275d.json)

The Pair25 recipe then built a signed development APK from FieldLog tree
`e09018a23e3a` and preserved the observed Apple build closure. Actual Android
compilation used 14 app-owned Swift files. Six files across the two targets
were byte-identical, comprising 937 of 5,354 distinct source lines.
Independent review matched all 41 APK members, its APK v3 signature,
both embedded Ed25519 signatures, and the two source rosters. The APK
carries the old native capability fingerprint. The corrected Android
rebuild must check the linked fingerprint and both sealed identity fields
against its SDK pin. The older Apple build remains tied to its original
Mixer revision. Installed behavior remains open.
[Pair25 build evidence](verification/receipts/fieldlog-d2-pair25-android-build-dbb9275d.json)

The corrected `6bc461f4fc` Android build resealed the actual JNI, DEX,
manifest, and installed resources. All 41 package members and both native
identity fields matched readback. Its development guest uses a storage-only
grant with two request slots and a 2 MiB reservation. Independent review
verified the linked JNI fingerprint, VM source provenance, APK and
embedded signatures, alignment, and compiler roster. The different
development certificate requires a clean isolated Android API 36 or later
installation. The device hold remains active.
[Corrected Android reseal](verification/receipts/fieldlog-d2-pair25-android-reseal-6bc461f4.json)

The matching arm64 iOS Simulator bundle now builds from the same Mixer
pin `6bc461f4fc`. The 15 Apple app-owned Swift inputs match the historical
roster, and six are byte-identical across both current compiler rosters.
The bundle carries a development-signed Commit guest and the corrected
linked capability fingerprint. Independent static review verified both
development signatures, the linked identity, executable, and resource
loader. The executable has a linker ad hoc signature. The app bundle has
no OS resource seal or provisioning profile. Simulator installation and
the signed Commit flow remain open under the existing hold.
[Matching Apple build](verification/receipts/fieldlog-d2-pair25-apple-simulator-build-6bc461f4.json)

FieldLog tree `eb08569c13b5` uses the shared `TaskEditorPresentation` in
the ordinary Android checklist. The reviewed correction exposes three
editor operations through a FieldLog-specific SPI across the production
SwiftPM package split. Baseline and candidate macOS replays verified
unsaved discard, stale-action refusal, and exactly one task and linked
outbox record after Save and cold reopen. The candidate also linked arm64
`libAppAndroid.so` for API 28 with Swift 6.3.3 after an Xcode 27.2 frontend
crash.
[Shared task presentation receipt](verification/receipts/fieldlog-d2-shared-task-presentation-eb08569c.json)

The checked-in replay reproduced all three package-access refusals on the
initial tree and matched the baseline and corrected host behavior. All 11
command groups closed and scratch was removed. The 11 inert runner
controls passed. They cover unresolved custody, receipt publication
failure, and propagation of a requested Android compile failure.
[Maintained host replay receipt](verification/receipts/fieldlog-d2-shared-task-presentation-maintained-replay.json)

The reviewed shared-editor tree `eb08569c13b5` produced a development
APK against Mixer `6bc461f4fc`. The packaging overlay changed eight
recipe files. Android compiled 14 app-owned Swift inputs into the
ordinary launcher package. The author's static checks verified the
linked `5d467c65…` identity, APK v3 signature, both Entry Commit
signatures, and 16 KiB alignment across all 19 arm64 libraries. The
separate Entry Commit fixture remains bundled. Independent review matched
all 78 retained file hashes and verified both development signatures.
The packaged JNI calls the shared title-field implementation from the
ordinary form. Installed behavior remains open.
[Shared-editor APK receipt](verification/receipts/fieldlog-d2-pair25-shared-editor-eb08569c.json)

The first matched iPhoneOS build stopped before FieldLog compilation. Its
scratch guard counted a sparse Xcode cache at 37 GiB apparent size. The
scratch occupied 149 MiB on disk when the run closed and was removed.
The follow-up uses allocated disk blocks for the same 4 GiB limit.
[Initial Apple build receipt](verification/receipts/fieldlog-d2-shared-task-presentation-eb08569c-iphoneos-guard-failure.json)

The corrected generic arm64 iPhoneOS build linked ordinary FieldLog with
OS signing disabled. It peaked at 462 MiB allocated. Static readback
verified the separate development-signed Entry Commit resources added
after linking. Both target builds used Mixer `6bc461f4fc` and FieldLog
product tree `eb08569c13b5`. The Android tree adds eight recipe files.
All 15 Apple and 14 Android compiler inputs match their source blobs.
Six are byte-identical across the two targets, accounting for **954 of
5,367 distinct physical lines (17.8%)**. One shared file is UI and five
are logic. The 90% source-sharing target remains unmet on the measured
inputs. Installed behavior remains open.
[Corrected Apple build](verification/receipts/fieldlog-d2-shared-task-presentation-eb08569c-iphoneos-corrected.json) ·
[Matched compiler inputs](verification/receipts/fieldlog-d2-matched-compiler-inputs-eb08569c.json)

FieldLog candidate `e49ac6bb82` uses the same repository source in both
ordinary packages. Android retains its revision-checked merged-draft
photo transaction. Apple retains its `addPhoto` route. Baseline and
candidate matched at all 11 disk checkpoints in both package paths,
including cold reopen, durable task and draft writes, refused precommit,
and recovery after a rename error. The Android arm64 Swift library and
unsigned generic iPhoneOS app linked. Independent review confirmed the
four-file patch and reconstructed both disk traces from the afterimages.
The historical receipt supports 59 distinct terminal groups. The
earlier total of 60 included a separate artifact-retention check.
Installed behavior and the whole-app sharing target remain open.
[Repository source](verification/receipts/fieldlog-d2-workspace-repository-e49ac6bb-patch.patch) · [Verification receipt](verification/receipts/fieldlog-d2-workspace-repository-e49ac6bb.json) ·
[Disk afterimages](verification/receipts/fieldlog-d2-workspace-repository-e49ac6bb-afterimages.json)

The maintained repository replay verified each command's terminal
receipt and readable log digest. All 20 cleanup controls passed. A fresh
host run matched the historical disk afterimages byte for byte, completed
the standalone export link, closed all 19 command groups, and removed
scratch. Its native build scope was the host. The original arm64 Android
and iPhoneOS build evidence stays in the separate product receipt.
[Maintained host replay](verification/receipts/fieldlog-d2-workspace-repository-e49ac6bb-maintained-host.json) ·
[Log integrity controls](verification/receipts/fieldlog-d2-workspace-repository-e49ac6bb-replay-log-integrity.json)

FieldLog tree `85e6fbe362` shares the checklist row projection across
ordinary SwiftUI `ProjectDetail` and Android `PublicFactory`. Both
consume the same 21-line source. Android computes move eligibility
before slicing the page. The host replay moved a row across positions
20 and 21 in both directions and exercised completion and cold reopen
in both package paths. Invalid and stale actions made no writes.
The Android arm64 library and unsigned iPhoneOS app linked the shared
code. The Apple replay exercised model handlers, and compilation
covered the SwiftUI call site. Independent review verified exact source,
routing, and scope. The author observed 22 terminal groups and removed
scratch. Rendered UI, accessibility interaction, and installed runtime
remain open.
[Checklist patch](verification/receipts/fieldlog-d2-checklist-row-85e6fbe3-patch.patch) · [Verification receipt](verification/receipts/fieldlog-d2-checklist-row-85e6fbe3.json)

The combined FieldLog tree `85e6fbe362` built as an unsigned generic
arm64 iPhoneOS app and a signed arm64 Android development APK on the
same Mixer pin, `6bc461f4fc`. Both artifacts passed independent static
review, including their separate development-signed Entry Commit material.
The actual compiler rosters share 8 of 23 distinct app-owned Swift
inputs and 1,338 of 5,084 physical lines (26.3%). The 49 Android-only
photo lines are included in that physical count. The 90% goal and
installed behavior remain open.
[Apple build](verification/receipts/fieldlog-d2-combined-85e6fbe3-iphoneos.json) ·
[Android package](verification/receipts/fieldlog-d2-pair25-combined-85e6fbe3.json) ·
[Source comparison](verification/receipts/fieldlog-d2-combined-85e6fbe3-compiler-inputs.json)

FieldLog `64841ade77` shares directional checklist ordering in the
ordinary app. Apple resolves moves inside its queued transaction.
Android checks the admitted revision and moves focus to the task's
destination page after commit. Both host routes and arm64 builds passed.
Independent review reproduced cold disk readback and stale and
invalid refusals. The matching ordinary build rosters gained 13 shared
lines and lost six unshared lines. Shared physical source rose from
1,513 of 4,806 to 1,526 of 4,813 lines. These source counts include
conditional code. Native UI and signed runtime remain unverified for
this patch.
[Move source](verification/receipts/fieldlog-d2-checklist-move-source.patch) ·
[Host and build receipt](verification/receipts/fieldlog-d2-checklist-move.json) ·
[Compiler inputs](verification/receipts/fieldlog-d2-checklist-move-compiler-inputs.json)

FieldLog `e39a5ea393` shares project checklist, draft, entry, and queue
content through both ordinary owners. Paired host routes passed, and
both ordinary arm64 targets linked. The exact rosters gain 100 shared
physical lines and remove 12 unshared lines. A negative control that
reversed the shared queue failed both routes. Independent review also
checked 20-row slices of a 50,000-item queue. The normalized Apple
cold-reopen digest remains producer evidence because its snapshot is
absent from the handoff. The fresh campaign recorded closure for 25
commands. Seven earlier command holds remain preserved.
[Product patch](verification/receipts/fieldlog-d2-ordinary-screens-e39a5ea3.patch) ·
[Reviewed producer receipt](verification/receipts/fieldlog-d2-ordinary-screens-e39a5ea3.json) ·
[Initial holds](verification/receipts/fieldlog-d2-ordinary-screens-e39a5ea3-initial-holds.json)

FieldLog candidate `00406fe735` shares the ordered photo roster and
picker capacity in the ordinary Apple and Android entry editors. Both
arm64 targets linked the projection. The matched production compiler
inputs grow from 1,380 to 1,392 shared physical Swift lines.

The source-bound Android macOS replay passed 22 baseline and 23
candidate tests in separate workspaces. Both preserved the Unicode
draft, date, category, and eight ordered photo references on reopen.
The picker was enabled at seven and disabled at eight, and refused
inputs preserved disk bytes. This replay resolves the source
attribution gap in the earlier Android logs. The platform picker,
installed candidate UI, and signed guest execution remain unverified
for this tree.
[Product patch](verification/receipts/fieldlog-d2-entry-editor-photos-e39a5ea3.patch) ·
[Apple host and native build receipt](verification/receipts/fieldlog-d2-entry-editor-photos-e39a5ea3.json) ·
[Source-bound Android host receipt](verification/receipts/fieldlog-d2-entry-editor-photos-android-host-00406fe7.json)

On a fresh offline arm64 API 36 emulator, the reviewed `00406fe735`
development APK opened an existing draft with seven synthetic photos.
Android DocumentsUI delivered the eighth photo. The next frame disabled
photo selection, and tapping it left the exact workspace unchanged.
The cold app reopened with the same ordered references and all eight
JPEGs. The photo write advanced revision 9 to 10 without adding an outbox
entry. All 111 recorded commands, private ADB and the emulator closed,
and all three listener ports were reusable.
[Installed photo capacity replay](verification/receipts/fieldlog-d2-entry-editor-photos-api36-00406fe7.json)

The store CLI now uses the platform-specific iOS bundle ID or Android package for status and fixture submission. The shared application ID still applies when the platform entry is absent. The original 13 loopback cases and 18 independent checks passed. The updated native archive accepts the corrected four-file source and refuses each obsolete file. [Store fixture and source verification](verification/receipts/l05-store-platform-identifiers-20261119.json)

A free owner created one build through Phoenix, restricted Oban, and the loopback worker. The worker's inert exit-23 fixture settled the build and released capacity. Organization exit was refused before settlement and succeeded afterwards. The former owner lost access while tenant B retained its export and created another project. [Settled build and organization exit](verification/receipts/l06-settled-exit-65c89e08.json)

The older FieldLog writer dropped the optional follow-up value after a draft save and after an unrelated task save. The read-only rollback preserved the exact workspace, and the record identity, outbox prefix, and JPEG survived the saves. The host result exposes a compatibility gap in whole-workspace writes. [Legacy writer reproduction](verification/receipts/fieldlog-l08-scenario4-legacy-save-58951594.json)

The matched D3 macOS workload reproduced all four FieldLog frames and the original-source trap. Each path completed 36 timed turns across 12 fresh processes. Prepared-input to frame medians were 0.50 µs for native Swift and 317.27 µs for the owned VM. The rebuilt guest was 5,359 bytes raw and 2,691 bytes gzip. The receipt records the different timing boundaries, host contention, and peak process memory. Mobile parity remains open. [Host benchmark and raw samples](verification/receipts/l03-d3-task-completion-host-benchmark-7b61fe1c.json)

The versioned Starter restart passed its inert control. The real pinned replay accepted one build and closed its Swift preflight before Xcode. The CLI refused a Phoenix-generated symlink inside the runner's provenance directory. The wrapper waited for artifacts and timed out without collecting fixture service closure. The held run is preserved. The next version separates the provenance directory and handles positively closed preflight failures. [Restart preflight receipt](verification/receipts/l07-versioned-starter-preflight-provenance-20261119.json)

The corrected pinned Starter replay passed one real local build. Phoenix accepted one authenticated POST and restricted Oban recorded one Xcode run and one capacity release. The relay withheld one artifact reply after closure. The worker restarted with the same SQLite file and terminal row and the same artifact store. Fresh owner sessions downloaded all three exact artifacts, and the unrelated tenant received 404 for the build and each download. Billing was unchanged. All 47 owned command groups closed, all seven ports were reusable, and the runtime scratch was removed. [Verified restart receipt](verification/receipts/l07-versioned-starter-worker-restart-20261119.json)

The restart replay now runs from the checked-in Starter tools. It verifies the historical worker, CLI, and both overlay files inside an owned archive. The maintained runner passed source admission, the inert restart, and the ordinary Phoenix and restricted Oban fixture with two tenants and zero build requests. The checked-in launcher also completed a real Xcode build and verified the worker restart, tenant-scoped downloads, and cleanup. [Maintained replay receipt](verification/receipts/l07-maintained-starter-restart-20261119.json) [Replay instructions](tests/integration/free-project-starter/README.md#l07-closed-worker-restart)

### Restart of a closed Starter worker

On `9315129781d6d32215a452b0bd2722cf6123ffd1`, one authenticated free iOS Starter request returned HTTP 201. The local relay withheld the first artifact response after the worker verified that Xcode and the CLI had closed. A replacement worker opened the same SQLite ledger and artifact store on a fresh port. Restricted Oban settled the original build at revision 2 with `native_succeeded`. The worker ledger recorded one start and one Xcode invocation, and PostgreSQL recorded one capacity release. All three authenticated downloads matched the stored sizes and SHA-256 hashes. A separate tenant received HTTP 404 for the build and each download.

The fixture used PostgreSQL 17.11, Elixir 1.20.4, and Xcode 27.2 on macOS arm64. It checked the persisted request key, deterministic build ID, and stable authenticated reads with one POST. Billing rows matched before and after the build. The fixture ran without a payment service. All owned groups exited, all seven ports were reusable, and the disposable database and scratch were removed. L07 remains open for recovery when the compiler exits without verified closure and for combined load and delivery recovery.

### Mixed authenticated build contention

At `1e81569c47`, a real authenticated build request began its PostgreSQL transaction while a fixture held the other lifecycle connection. Four concurrent requests received HTTP 503 before BEGIN. The admitted request returned HTTP 201 after the barrier opened. The same Phoenix listener and session stayed ready at generation 1. The refused key then created exactly one build, each accepted key replayed with HTTP 200, and the unrelated tenant received HTTP 404. Exactly two builds and two jobs remained. Both direct verification and the checked-in test collector passed. The run covered admission and recovery in the build API. Native worker recovery and combined release delivery remain open. [Mixed checkout receipt](verification/receipts/l07-mixed-checkout-recovery-20261120.json)

The combined checkout replay at `ea4954ff38` kept the signed release offer and artifact byte-identical before, during, and after a build request was refused before BEGIN. The same Phoenix listener and session accepted that exact key after check-in and replayed it without creating another build or job. Cross-membership reads and writes returned 404. Both databases and the release origin closed, all five TCP ports rebound, and scratch was removed. This replay covers ordinary build admission and signed loopback HTTP delivery under the same controlled contention. [Combined replay receipt](verification/receipts/l07-combined-outage-control-20261120.json)

The local incident drill emitted a `build_checkout_unavailable` test alert on the observed HTTP 503. The runner acknowledged it before the fixture released the checkout. The exact key returned 201 and then 200. Two accepted builds left two Oban jobs, and the signed release bytes and audit history matched their baselines. All 23 command groups closed and all five ports were reusable. This covers the local build outage alert and recovery exercise. [Rehearsal receipt](verification/receipts/l07-local-build-alert-rehearsal-20261120.json) · [Runbook](docs/operations/rehearse-local-build-outage.md)

A separate ordinary Pair25 replay terminated its owned worker while the inert runner still held the operation. During the outage, restricted Oban retried the original job, PostgreSQL held capacity, and the owner could read the build without artifacts. The reopened worker reused its port and ledger, recovered the same operation with one start, and accepted one cancellation. The terminal closure released capacity once. This replay used a real local API and inert runner backend. The first attempt retains its scoped shutdown hold. The real compiler recovery replay remains pending. [Ordinary worker outage receipt](verification/receipts/l07-pair25-ordinary-worker-crash-20261120.json)

The real compiler follow-up submitted one build and observed Android Swift compilation before terminating the owned worker. The owner could still read the original running build while Oban retried and PostgreSQL held capacity. After 29.039 seconds the worker reopened on the same port and the runner accepted a fresh guard for the same operation. The next build read failed the fixture’s running-state assertion, and the response state was discarded. No cancellation request was sent. All ten host command groups closed. The exact container, stage and fixture scratch remain held because terminal settlement and Docker custody were unverified. A separate earlier dependency attempt stopped before startup. Using a private locked Hex cache resolved that preflight. [Live worker outage observation](verification/receipts/l07-pair25-live-worker-crash-hold-20261120.json)

The corrected Pair25 replay records the first owner response after the worker reopens. Both controls used ordinary Phoenix, PostgreSQL, and restricted Oban with an inert runner backend. In the active case, the owner read the running build and cancelled it once. In the completion case, the first read returned `native_succeeded` at revision 2. The owner read the terminal logs and downloaded all three matching fixture artifacts. Each run preserved the original Oban job and worker operation, observed one start and one capacity release, closed all nine command groups, and rebound all five ports. The subsequent dedicated Linux VM run verified live compiler recovery. [Hosted recovery controls](verification/receipts/l07-pair25-recovery-hosted-controls-20261120.json)

A fresh Pair25 replay observed an Android-target Swift frontend in its owned Linux container before terminating the native worker. While the worker was down for 29.337 seconds, Oban retried the original job, PostgreSQL held capacity, and the owner could read the running build without artifacts. The worker reopened on the same port with the same ledger and recovered the original runner operation. The first owner read after reopen showed the running build. That same attempt reached revision 2 native success, with one runner start, one capacity release, two logs, and three digest-matched downloads. No cancellation POST was needed. Billing matched its baseline. All ten fixture command groups closed, all five fixture ports were reusable, and the dedicated VM and its scratch were removed. The historical holds remain in force. [Live recovery](verification/receipts/l07-pair25-live-worker-recovery-20261120.json)

A combined Pair25 replay held both Phoenix lifecycle checkouts while its worker was down. The original build key returned HTTP 503 before BEGIN. After both checkouts returned and the worker reopened on the same port and ledger, the same session and key returned HTTP 200 for the original build. The signed v3 offer, artifact and publication audit stayed unchanged on the separate PostgreSQL origin. Restricted Oban settled one start and released capacity once. The owner read the logs and all three synthetic artifacts. All owned groups closed and ports were reusable. The runner used an inert backend and the combined real-compiler replay remains pending. [Combined outage receipt](verification/receipts/l07-pair25-combined-outage-inert-20261120.json)

The completion-only follow-up observed the real Android Swift frontend in a fresh dedicated Linux VM before terminating the worker. During the outage, the original build key returned 503 before BEGIN and the signed v3 offer and artifact kept their original hashes. After both checkouts returned, the original key and session returned 200 on the same API listener. The reopened worker recovered the same job and operation, settled native success once and released capacity once. The owner read two terminal logs and all three digest-matched artifacts. No cancellation was sent. The signed delivery bytes and audit remained stable, and owned fixture services, the container and the VM closed. L07 still needs the live iOS worker-loss case and the W16 workflow decision. [Live combined outage receipt](verification/receipts/l07-pair25-combined-outage-live-20261120.json)

The bounded-load follow-up exercised a real Pair25 compiler on a dedicated local Linux VM. Both signed reads returned byte-identical responses while four authenticated retries waited for their pre-BEGIN 503 responses. The same session and key returned 200 after worker restart. Oban settled the original native build once and released capacity once. The owner read both logs and all three digest-matched artifacts. Tenant refusals, billing, and the release audit matched their expected values. The container, daemon, VM, and fixture groups closed. L07 and W16 remain open for installed iOS privacy and the remaining security review. [Live bounded-load receipt](verification/receipts/l07-pair25-bounded-load-live-20261120.json)

The opt-in independent macOS build owner recovered one iOS attempt through the ordinary Phoenix, PostgreSQL, and Oban fixture. The replacement worker reopened the same ledger after the original port became reusable. Capacity stayed held after nested acknowledgement while the CLI remained live. Once the original parent reaped the CLI, the owner cancellation settled and released capacity once. The owner received the terminal log, and the cancelled build exposed no artifacts. The CLI payload was inert. Hosted v55 binds the candidate and restores all 423 v54 source files. [Inert custody replay](verification/receipts/l07-ios-active-custody-replay-0151489c.json) · [Hosted v55 binding](verification/receipts/hosted-source-binding-v55-20261120.json)

A separate run interrupted the worker during an unsigned generic iOS Starter build. The independent parent retained custody of the CLI through Swift preflight and one Xcode invocation. Oban retried the same job during the outage, and the replacement worker reopened the original ledger and port. The original attempt settled as `native_succeeded` with one start and one capacity release. The owner read two log events and three digest-matched downloads. Anonymous downloads returned 401. All owned processes closed, five ports were reusable, and the fixture and staging scratch were removed. Hosted v56 admits the two-command receipt check and restores all 424 v55 source files. No Simulator or device ran. [Live recovery receipt](verification/receipts/l07-ios-active-native-recovery-20261120.json) · [Hosted v56 binding](verification/receipts/hosted-source-binding-v56-20261120.json)

The maintained staging command rebuilt the pinned CLI and exported the same Starter source and lock in fresh scratch. Preflight admitted the new CLI digest and verified the pinned source and tools. All 21 preparation commands closed, both scratch directories were removed, and preflight made zero build POSTs. [Replay guide](tests/integration/l07-ios-active-custody/README.md) · [Fresh staging receipt](verification/receipts/l07-ios-starter-stage-preflight-20261120.json)

Three local development signer runs lost the acknowledgment after publishing one envelope. A repeat `sign` refused before reading the private key or sending a request. The original public key verified the exact committed envelope, and the fixture port became reusable after each run. [Signer recovery receipt](verification/receipts/l07-signer-post-publication-aae21e08.json) · [Replay guide](tests/integration/l07-native-attestation/README.md)

The ordinary Phoenix backend disables HTTP/2 because Bandit 1.14.1 can log request data in its HTTP/2 warnings. A normal loopback health GET returned HTTP/1.1 200 before and after the change. HTTP/2 returned 200 before the change and was refused afterward. Both listeners closed and their ports were reusable. [Backend transport receipt](verification/receipts/l07-hosted-http1-privacy-20261120.json)

The maintained two-tenant privacy replay passed access controls and stock log checks with native retention disabled and enabled. A privileged in-process subscriber still received sensitive metadata from Bandit, Phoenix, and Ecto. The replay kept that finding visible in strict mode. App telemetry, external egress, and attachment and source-map retention remain open. [Privacy replay](verification/receipts/l07-hosted-privacy-replay-20261120.json) · [Original adverse observation](verification/receipts/l07-hosted-privacy-original-adverse-20261120.json)

The exact Phoenix 1.8.17 tree repeated both privacy profiles under
SCRAM PostgreSQL. Tenant access and refusal checks passed, and stock
Logger and PostgreSQL logs showed their controls without private
markers. The deliberately attached privileged subscriber observed
markers in 74 ordinary-profile events and 78 retained-profile events.
Strict mode exited 2. The fixture's TLS signer needed relative paths
under deep scratch. Both profiles closed their command groups, removed
their databases and scratch, and released all eight listener ports.
[Current privacy replay](verification/receipts/l07-hosted-privacy-v86-551576a0-test.json)

A repeat against the same v86 sources used the locked Phoenix package
from the local Hex cache. Both stock profiles matched the earlier
result. The retained profile initially refused its scratch path
under the world-writable temporary directory and passed from a
trusted ancestor chain. Strict mode still exited 2 for private
metadata reaching the privileged subscriber.
[Exact-source corroboration](verification/receipts/l07-hosted-privacy-v86-551576a0-cache-replay.json)

The hosted runtime, configuration, lock, and replay fixture match those
tested bytes at `d89c742e9d`. The stock startup inventory contains
Phoenix Logger and Mixer transaction receipt callbacks. An attached
subscriber still sees private framework metadata. The local operations
guide specifies how to keep raw events inside the process. Installed iOS
privacy remains open. [Source and scope review](verification/receipts/l07-hosted-privacy-boundary-d89c742e.json) ·
[Operational boundary](docs/operations/security-boundaries.md#local-hosted-telemetry)

On the same stock hosted configuration at `926f6d94`, 11 runtime tests passed. An offline startup of the real dependencies registered zero exporters and zero Bandit request-start subscribers. Ten inert environment settings left the effective configuration unchanged. Stock Logger recorded its positive control with no synthetic private markers. A privileged test callback received the synthetic metadata and detached. [Offline telemetry startup receipt](verification/receipts/l07-stock-telemetry-startup-review-926f6d94.json)

The installed Android Site Map received a foreground synthetic fix with
networking available. The app UID's packet and byte counters stayed
unchanged between two TCP controls from the same UID. Both controls
reached the owned loopback listener and advanced all four counters.
The map reported direction and accuracy, retired the fix on close, and
left the workspace byte-identical. The app-process log had no enrolled
location markers. The first control timed out before launch. The passing
run kept the ordinary dashboard active during both controls. The owned
emulator, ADB and listener closed, and both runs removed their scratch.
This covers the tested app UID and process log. L07 remains running.
[Installed Site Map privacy](verification/receipts/l07-fieldlog-android-site-map-live-network-f08f99a4.json)

The installed Pair25 Settings APK displayed only the five support
diagnostics fields in the captured screen. Applying Dark, reopening
from a cold process and resetting preserved the exact workspace and
all 47 pending records. Reset restored the original Settings hierarchy.
Both app-process logs had zero enrolled workspace-marker hits. Android's
app UID counters stayed unchanged during Settings. The same UID's TCP
controls advanced every counter before and after. All 152 commands
reached terminal custody and owned scratch was removed.
[Installed Settings privacy](verification/receipts/l07-fieldlog-android-settings-live-network-ac305262.json)

A fresh Android API 36 account sign-in exercised the browser callback and
confirmed session. The app UID log contained both positive window markers,
and the sampled Android activity records included the callback Activity.
None of six synthetic account markers appeared in either sample. One
earlier run stopped after exchange and before confirmation. The receipt
preserves that unresolved failure and both capture-control failures.
[Installed account sign-in privacy](verification/receipts/l07-fieldlog-android-account-sign-in-privacy-api36-066e5038.json)

An independent L07 audit at `e985e4650e` kept the gate running. The current
Pair25 notices and stock hosted sink tests support their tested scopes.
The remaining local evidence includes an integrated signer interruption
on the managed build attachment path, live two-tenant cache reuse, review
of the current VM-to-activation composition, and installed iOS verifier,
privacy and outage checks. The deliberate privileged telemetry result
remains recorded separately.

The live loopback worker admitted the same pinned source for two tenants
using one disposable ledger. Both operations reached `native_ready`
with one start and distinct project, home, temporary and artifact paths.
All 16 cross-tenant requests were refused while both were ready. Each owner
read its own outputs after listener restart. The CLI supplied fixture bytes.
The exercised worker has no shared build-result cache. Both operations
stopped, the owned groups closed, and scratch was removed.
[Two-tenant worker replay](verification/receipts/l07-local-worker-two-tenant-995eede.json)

The live attachment recovery fixture settled one real unsigned iOS
Starter build. After one signature, Phoenix selected HTTP 201 and
the fixture shut down the connection before writing the response.
A fresh PostgreSQL read found the exact envelope before a single retry
returned HTTP 200. One attachment row, the settled records and the
worker ledger stayed unchanged. All 30 outer groups closed, five ports
were reusable, and disposable keys and scratch were removed.
The independent review verified the fault boundary and reproduced
v87's source refusal. v88 preserves all eight tested fixture files
and binds 573 source inputs. The three hosted sparse projections,
the Source141 archive check and all 43 fixture tests passed locally
in normal and optimized Python. L07 remains running.
[Live attachment recovery](verification/receipts/l07-live-lost-attach-ack-4d28a7c7.json) ·
[Reversible hosted source binding](verification/receipts/l07-hosted-source-v88-composition-c9ad543.json)

All three hosted runs on the v88 push passed. Phoenix reported 1,030
passes and 32 skips. Identity passed both network methods. All nine Engine
jobs passed, including the seeded Node replay in Debug and Release and all
six Java consumers. All six DEX files matched byte for byte. The two
uploaded receipts record 92 terminal groups and both scratch trees
removed. Hosted v88 and reconstructed v87 digests matched their inputs.
[Hosted v88 terminal record](verification/receipts/l07-hosted-v88-engine-terminal-6b07f0da.json)

All nine Owned Engine jobs on `6c73017a` passed. The ten archived
artifacts matched GitHub's digests. All six Java consumers produced
identical DEX, and the Source141 inputs matched all 157 Git blobs.
The two Java receipts account for 92 closed commands and removed scratch.
The Swift custody archive accounts for 140 closed CLI commands.
[Hosted Engine terminal record](verification/receipts/hosted-engine-terminal-6c73017a.json)

The unchanged FieldLog updater ran in two macOS processes under an Android-scoped development identity. The owned observer saw four bodyless loopback GETs and found no workspace or JPEG markers, cookies, or bearer credentials. A complete signed offer activated sequence 1. After an artifact HTTP 503, a new process recovered the same candidate and preserved the workspace and JPEG. The sandbox denied a second loopback destination, and both owned ports closed. [Updater privacy receipt](verification/receipts/l07-fieldlog-updater-loopback-b144c2c-20261120.json)

One installed Android fixture completed a signed sequence-1 update and reopened the same healthy candidate in a new process after an artifact HTTP 503. The private origin saw four bodyless GETs and no credential headers. The verifier found none of the 21 synthetic workspace markers in those requests or 483 entries from the two app-process logs. Airplane mode and unreachable default routes limited the fixture to its owned reverse mapping. The workspace stayed byte-identical, all four ports were reusable, and raw logs and device data were removed. OS diagnostics and privileged BEAM metadata remain open. [Installed Android updater privacy](verification/receipts/l07-fieldlog-android-updater-native-20261120.json)

### Restore of the Starter database and artifact store

The empty fixture restored to a separate PostgreSQL 17.11 cluster. The roles and journal matched, and two fresh sessions authenticated under the restricted API role. All 38 command groups closed, eight ports were reusable, and the replay removed its scratch.

The first full replay stopped at `starter-export` with `lock.toolchain-drift`. The corrected replay applies a pinned four-file Swift lock patch only to the historical CLI build. It submitted one iOS Starter build, closed one compiler invocation, and backed up the settled journal, SQLite ledger, and retained files. [Restore controls and initial failure](verification/receipts/l07-starter-restore-controls-20261120.json)

A separate PostgreSQL cluster restored the same journal and served matching build and log content and all three advertised artifacts with fresh owner sessions. The unrelated tenant received the expected HTTP 404 body for each read. Both sessions received `Cache-Control: no-store`. The reads left the restored journal, SQLite operation, and artifact bytes unchanged. The target launched no worker or compiler. All 73 command groups closed, all 11 ports were reusable, and scratch was removed. Recovery after unverified compiler closure remains open under L07. [Settled Starter restore receipt](verification/receipts/l07-starter-settled-restore-20261120.json)

A separate PostgreSQL cluster restored one committed Phoenix beta release and its private staging and audit rows. Authenticated owner downloads, audit bytes, and signed updater responses matched the source. The unrelated tenant received HTTP 404. The same upload, validation, and publication keys replayed without changing the frozen rows. A raw restore first refused upload replay because PostgreSQL flattened the pinned request-key CHECK. The disposable target passed after restoring the exact catalog expression. Both clusters and all six listener ports closed. [Phoenix release restore](verification/receipts/l07-phoenix-release-restore-71e6ffa5.json)

### Android FieldLog saved-draft rollback

On an owned Android 36 arm64 emulator, the same FieldLog installation accepted four signed assignments. The optional guest saved the follow-up flag. The rollback guest reopened the same JPEG-linked draft, and the ordinary editor saved a new note with airplane mode on, no default route, and the release origin mapping removed. A cold reopen read the edit from disk and used the cached rollback guest. The re-upgraded guest recovered the true flag, edited note, and same JPEG bytes. An unsaved draft could not open a new signed session. [Android readback receipt](verification/receipts/fieldlog-android-saved-draft-offline-readback-20261120.json)

The closed run stopped before saving the second draft after an invalid driver swipe. A later attempt displayed the rollback guest and failed the durable recovery check after reopening the panel to correct a screenshot label. That emulator and its private ADB server remain held. Those attempts remain historical evidence. The maintained rebuild recipe includes per-phase custody checks and Rust LLVM tools. Its seven inert controls passed in normal and optimized Python. [Clean rebuild receipt](verification/receipts/fieldlog-android-saved-draft-terminal-d82b7878.json) · [Rebuild recipe](tests/integration/fieldlog-saved-draft/android/README.md)

A fresh Android API 36 replay passed all 11 checkpoints for §22.2.4 on the same installation. The ordinary editor saved the revised note offline. A cold reopen used the cached rollback release, and the re-upgraded guest recovered the flag and JPEG. An unsaved draft was refused. The second saved draft showed no photo and an unset flag. Reselecting the first draft restored its own photo, flag, and note. The workspace readbacks confirmed both draft identities and an unchanged outbox. The APK hash matched before and after the replay. All owned groups closed and all four ports were reusable. The first fresh attempt stopped when a tap during scrolling committed the test entry. The passing replay waited for the list to settle. Installed iOS coverage for this scenario remains pending. [Android isolation receipt](verification/receipts/fieldlog-android-saved-draft-isolation-20261120.json)

The iOS saved-draft fixture can check copied native snapshots against the pinned executable, signed sequence and exact saved draft. Its readback controls passed. Separate macOS processes using the pinned FieldLog repository preserved the authored flag, edited note, outbox, and linked JPEG across rollback and re-upgrade. The bound XCTest assertions and native capture coverage remain pending. [iOS readback recipe](tests/integration/fieldlog-saved-draft/ios/README.md) · [Host receipt](verification/receipts/fieldlog-ios-saved-draft-readback-20261120.json)

### Android FieldLog engine replacement

Section 22.2.13 passed on one owned AOSP arm64 API 36 emulator. FieldLog saved an open task through the ordinary form. Android installed version 24102 over 24101 with `pm install -r` and the same development signer. The old engine displayed signed sequence 7, and the replacement displayed sequence 1. Both showed **Open** and reached durable `first_screen` and `feature_started` before **Done** closed effects.

The APKs linked Mixer engines `15a2c0a98593d6e2bafaa1f5c00eb045c9815944` and `9fd7e7f6ebd9cadfd96d71a6c71225e6b11e33b9` with FieldLog `552559d2d3278abb9b1aa7dcf0288102c09a202b` and the pinned Android host overlay. The installed APKs matched SHA-256 `dfe81f4e03f4dd60e2db6116a340872c518c776357a826c428712c9374a5d15a` and `1e01140e6daa3ea0e54e581c7004991bb9c7b93ae3cea0d02587ceed15509711`. The two runtimes kept separate recovery cursors under installation `908880d5-6fab-43db-8cad-a11abee08cdc`. The old journal and the 888-byte revision-2 workspace each matched byte for byte after replacement. The workspace SHA-256 was `fa28b39831416d4ca070c945ae996e6356808d8ee6ae98f22aa436a1514657e7`.

The first replacement attempt reopened a workspace with one task but stopped while looking for its title below the visible checklist controls. The corrected replay checked the rendered task count and compared the full saved workspace before opening the guest. It used Python 3.14.8, ADB 37.0.1 and Android Emulator 37.2.12 with image build 13818094. All 578 recorded command groups closed. The reverse mapping, private ADB, origin, log reader and emulator closed, all four ports were reusable, and the disposable AVD was removed. L04 and L08 remain running.

A clean host reconstruction recovered both engine APKs after the earlier
packet files became unavailable. The same fresh development certificate
signed both builds. The stock loopback service passed 35 HTTP checks and
the Swift verifier passed 20. Publishing the new runtime left the old
wire responses intact, and both runtimes received byte-identical offers
and artifacts after service restart. Both service groups closed, their
port was reusable, and disposable keys and origin scratch were removed.
The rebuilt packet's evidence covers host signing and delivery.
[Rebuilt cohort replay](verification/receipts/fieldlog-android-engine-cohort-signed-e985e465.json)

### iOS FieldLog engine replacement

FieldLog 24101 and 24102 linked two distinct engines and the same
upgrade XCTest selector. Both arm64 iOS Simulator bundles use
`dev.mixer.fieldlog` and share development trust. The stock loopback
origin served signed sequence 7 to the old runtime and sequence 1 to
the new runtime. An independent host run passed all 35 HTTP and 20
Swift verifier checks, refused cross-runtime delivery, and matched the
offer and artifact bytes after restart. All 154 handoff hashes matched,
both service groups closed, and their port was reusable. Installed
in-place replacement and workspace and journal continuity remain pending.
[iOS engine cohort builds and host replay](verification/receipts/fieldlog-ios-engine-cohort-generic-73717993.json)

### Rendered free Starter build

At `72d135441ea5b50dbcf87902252e0c05e1e3b179`, Chrome signed in, created the free organization and project, registered the app, and selected the pinned Starter. The first fixture returned HTTP 400 because its proxy dropped `Idempotency-Key`. The corrected fixture forwarded the header, accepted one POST, and rendered the matching build ID. The stock admission API configured one fleet slot and one iOS slot. Restricted Oban dispatched one Xcode run, and the build reached `native_succeeded`.

PostgreSQL and the worker agreed on the size and SHA-256 of all three artifacts. Billing rows stayed unchanged, and the fixture used no payment credentials. Chrome then displayed **Check session** while the runner waited for **Refresh build**. The fixture closed before session recovery, rendered terminal logs, downloads, export, or exit. The database and scratch were removed, all owned groups closed, and all six ports were reusable. L05 and L06 remain running.

A loopback Chrome control forced HTTP 401 on a saved build at `72d135441e`. The test clicked **Check session**, signed in again, and reselected the same build. Chrome showed the terminal log and saved three synthetic attachments with matching SHA-256 hashes. The control issued zero build POSTs and ran no compiler. The console and hosted source trees match `9315129781`. The full browser journey with real artifact downloads, export, and exit remains open.

A fresh ordinary console run at `201ead70ff68bfe18de24c0642f518701459e0a4` submitted one real iOS Starter build. Phoenix returned HTTP 201 and persisted the browser's idempotency key. Restricted Oban ran Xcode once, and PostgreSQL released capacity once. After session expiry, **Check session** and a fresh sign-in let Chrome reselect the exact build and display its terminal compiler log. All three authenticated browser downloads matched the native worker's SHA-256 hashes. Workspace export and organization exit returned HTTP 200. The separate tenant received HTTP 404 for the build. Billing rows stayed identical and the fixture ran without a payment service.

The tenant's session and organization list returned HTTP 200 after the owner exited, but its project list returned HTTP 503. A separate zero-build control returned HTTP 200 for session, organizations, projects, and applications before and after exit. The same tenant directories matched. The integrated 503 remains unexplained. The disposable databases were removed, owned process groups closed, and their ports were reusable. L05 and L06 remain running.

On public Mixer `528efdd558dd`, Chrome submitted one free Starter build after the corrected navigation check. The build reached native success at revision 2. All three retained files matched the worker's sizes and hashes, and billing rows stayed unchanged. After renewed sign-in, the session endpoint returned HTTP 200 and the first organization read returned HTTP 503 outside the trace. The run stopped before browser downloads, export, and exit. All owned groups closed and all eight ports were reusable. [Starter replay receipt](verification/receipts/l06-rendered-starter-renewal-528efdd.json)

Separate store checks on the same source passed 34 compiled submission controls over loopback and 25 scripted status tests. The submission controls covered both platforms, including recovery after a lost acknowledgement and refusal by the ordinary CLI. The status tests covered App Store Connect, TestFlight, and Google Play. [Store fixture receipt](verification/receipts/l05-local-store-fixtures-528efdd.json)

Two traced Chrome controls returned HTTP 200 for the first organization read after both cold sign-in and renewed sign-in. Each first request was observed without a retry. The complete trace showed successful lifecycle and directory transactions with the owner in `storage_ready`. The controls submitted no builds. The original post-build HTTP 503 remains unexplained. [Renewal trace receipt](verification/receipts/l06-renewal-directory-trace-fef67b64.json)

On v79, a real managed unsigned Xcode build reached `native_succeeded`.
A fresh OAuth login then returned HTTP 200 on the first ordinary session,
organization, project, application, and exact build reads. Each request used
one attempt. RuntimeOwner stayed `storage_ready`, and no SQL exception was
observed. All 64 recorded commands closed and all five ports were reusable.
The historical 503 did not recur. This loopback control used browser cookies
without driving a frontend or forcing the old cookie to expire.
[Post-build renewal receipt](verification/receipts/l05-v79-post-build-browser-renewal.json)

The v80 follow-up let the old synthetic session expire after a real managed
build. Its first organization request returned 401. A single new OAuth
exchange issued a distinct cookie, and all five first reads returned 200.
No SQL exception occurred and the persisted build records were unchanged.
This HTTP-only replay did not reproduce the historical rendered-browser 503.
[Expired-session replay](verification/receipts/l05-v80-post-build-browser-expiry.json)

Native build completion now verifies each retained artifact with reads of at most 64 KiB. A 16 MiB storage control returned the same bytes and passed eight refusal checks on both revisions. Hosted source v45 admits the exact verifier, and its 59 focused Elixir tests passed. Authenticated HTTP streaming and the Android worker remain open. [Bounded verification receipt](verification/receipts/hosted-bounded-retained-verification-v45.json)

On public Mixer `a5398fad7c`, the ordinary console completed one free iOS Starter build, signed in again, and showed the retained compiler log. All three authenticated downloads matched the native worker's sizes and SHA-256 hashes. Workspace export and exit returned HTTP 200. The unrelated tenant's first session, organization, project, and application reads after exit all returned HTTP 200 with unchanged scoped data. PostgreSQL confirmed the owner tombstone, retained journal, and released capacity. Billing stayed unchanged through the build. Exit updated only the owner's lifecycle mirror, and the fixture used no payment service or credentials. The supplemental expired owner build read returned HTTP 503. The browser run stopped before checking a renewed former-owner session. L05 and L06 remain running. [Rendered Starter receipt](verification/receipts/l06-starter-console-ca-a5398fa-20261119.json)

The ordinary Pair24 Android Starter resolved both locked Swift dependencies using the two verified local Git mirrors. SwiftPM exited successfully, both checkouts matched the pinned revisions, and the SDK and platform lockfiles retained all 656 original bytes. This run evaluated dependency manifests. Managed Android compilation and artifact delivery remain open. [Offline Android resolve receipt](verification/receipts/l05-w12-pair24-offline-swiftpm-120s-20261119.json)

A separate settled-journal control used the ordinary Phoenix endpoint at the same hosted source pin. The first expired former-owner build request returned 401. The first renewed former-owner request returned 404. The journal stayed intact, and the earlier HTTP 503 did not recur. [Former-owner read receipt](verification/receipts/l06-starter-owner-exit-discriminator-a5398fa-20261119.json)

A follow-up at `59cab78cd8` completed one registered iOS Starter build through the ordinary API and verified all three authenticated artifact downloads. After export and exit, the first expired-cookie build request returned 401 and the first request after renewed sign-in returned 404. PostgreSQL retained the original build history and released reservation. Tenant B retained its access and received 404 for A’s build. The completed run closed all six ports. A separate zero-build setup remains under custody hold. [Real-build former-owner receipt](verification/receipts/l06-starter-real-build-owner-exit-59cab78-20261119.json)

**L06 passed for local free testing and administration.** The maintained `--owner-exit` replay started from a checkout without `verification/local`, ran one registered native build, released capacity once and verified both first former-owner reads. It preserved the build and all three downloaded artifact digests and kept the unrelated tenant's workspace available. All seven ports were reusable. Review found a false success in the fixture-only verdict. The correction now returns exit 1 for the injected failure in both Python modes. The full replay had already passed. [Maintained replay receipt](verification/receipts/l06-maintained-starter-owner-exit-20261119.json) [Local gate decision](verification/receipts/l06-local-acceptance-20261119.json)

### Retained Android Starter artifacts

The corrected standalone CLI built and reopened an unsigned Pair24 Android Starter APK, detached debug symbols, and a canonical inventory. The actual APK measured 27,795,726 bytes and declared arm64, minimum API 28, and target API 37. The report matched the CLI executable mapped into the running process. A separate development signer ran after compiler closure, verified the v3 signature and 16 KiB alignment, and preserved all 26 APK payload entries. Managed Android builds and authorized downloads remain open. [Retained Android and development signing receipt](verification/receipts/l05-android-retained-starter-build-signing-20261119.json)

The local Phoenix route served all three Android artifact roles from a synthetic completed journal and replayed all three existing iOS artifact downloads. The 27,795,726-byte Android fixture verified the exact body, hash, and APK download headers. An unsigned Android APK has a 32 MiB cap. Other roles retain 16 MiB. The console labels the artifact **Unsigned APK**. Managed Android build and download from the same worker operation remain open. [Platform policy](verification/receipts/android-retained-policy-fc92687.json) [Authenticated read-path and source admission](verification/receipts/l05-android-retained-delivery-v46-20261119.json)

The Phoenix CI replay exposed a missing two-argument reader used by the iOS compatibility controls. Restoring that entry point passed all 45 focused hosted tests. The authenticated route still passes the selected platform. [Compatibility and v47 source receipt](verification/receipts/l05-retained-reader-compatibility-v47-20261119.json)

The next Phoenix CI run passed 935 tests and skipped two before its source-integrity check failed. The retained artifact control reproduced seven writes under the hosted checkout. The corrected control used system scratch and left the hosted inventory unchanged. [Fixture scratch receipt](verification/receipts/l05-retained-ci-scratch-v48-20261119.json)

An operator-registered Pair24 Android Starter passed the ordinary local build and download path. One authenticated POST created the build, restricted Oban dispatched one Swift app compile, and PostgreSQL recorded native success at revision 2 with one reservation released. All three downloads matched the worker and an unrelated authenticated user received 404. A separate development signer verified the exact downloaded APK with 16 KiB alignment and all 26 payload entries intact. L05 remains open for the rest of the platform workflow. [Ordinary managed Android receipt](verification/receipts/l05-ordinary-managed-android-pair24-v49-20261119.json)

The authenticated build log route and console now report **Android build driver finished** from the closed driver receipt. The projection carries an exit code and output byte counts. The replays preserved the existing iOS log shape and refused wrong-scope requests. [Android build log receipt](verification/receipts/l05-retained-android-build-logs-v50-20261119.json)

A live Swift frontend targeting Android ran outside its managed driver's process group. The worker had no confirmed shutdown, and the attempt remains under a custody hold. The ordinary cancellation replay remains pending until the worker can account for an in-flight compiler. [Compiler custody receipt](verification/receipts/l05-android-compiler-process-group-20261119.json)

A focused test with the pinned SwiftPM waited for the observed Android frontend after a normal sibling compiler failure. With SIGINT, SwiftPM exited and its pipe reached EOF while that frontend remained live. The test hook later reaped it. All observed groups closed. Managed cancellation still needs compiler closure before it releases capacity. [SwiftPM closure receipt](verification/receipts/l05-android-swiftpm-phase-closure-20261119.json)

A no-signal SwiftPM compiler-override test built a tiny AArch64 Android library. The test reaped seven wrapped `swiftc` commands and the SwiftPM launcher. The wrapper missed manifest execution and nested compiler and linker actions, leaving terminal custody for those phases unverified. The exact scratch remains held. Managed live cancellation remains open. [Tool boundary receipt](verification/receipts/l05-android-swiftpm-compiler-boundary-20261119.json)

An isolated local Linux container compiled a SwiftPM Android arm64 library at API 28. A separate run observed the Android frontend during compilation and cancelled its own container. The runtime reported exit 137 and PID 0, and the cancelled run produced no library. The native arm64 Swift image used its bundled linker and a verified NDK sysroot. The emulated amd64 attempt stopped at manifest evaluation. All owned trial resources closed and were removed. [Linux compiler custody receipt](verification/receipts/managed-android-local-linux-swiftpm-custody-20261120-ppzw6p4o.json)

A private offline Linux worker packaged an unsigned Pair25 public V4 Starter APK at 27,804,143 bytes. The receipt and independent readback agree on the APK digest, launcher, API 36 minimum, API 37 target, DEX, 18 AArch64 libraries, and four runtime notices. All 18 libraries have 16 KiB ELF load alignment. The APK stores them compressed. The trial verified packaging and removed its owned container resources. Managed Linux dispatch and authenticated artifact delivery remain open. [Linux Pair25 packaging receipt](verification/receipts/managed-android-local-linux-pair25-20261120.json)

The maintained offline replay retained all three Pair25 products from one Linux arm64 build. The unsigned APK was 27,804,143 bytes, the debug-symbol ZIP was 537,200 bytes, and the resource inventory was 10,317 bytes. Host readback matched all 26 APK entries and both debug members against the inventory and verified every artifact's size and digest. Docker reported terminal closure and removed the five owned containers, toolchain volume, and three acquired image references. This supplies real artifact inputs for the managed Linux delivery test. [Retained products receipt](verification/receipts/managed-android-linux-retained-products-20261120.json)

A separate Docker Desktop smoke recovered the exact prepared container across a runner reopen after disabling compression with the one-file log limit. The earlier start failed on that combination. The corrected start returned running and Docker confirmed the same container ID. The smoke stopped before shutdown because its guest readiness log was empty. Both attempts remain held, with no terminal or artifact publication conclusion. [Prepared recovery receipt](verification/receipts/l05-linux-docker-prepared-recovery-20261120.json)

A fresh managed Pair25 run on Linux arm64 completed through the authenticated native worker and private Docker runner. Docker Desktop first reported the writable output bind under its VM share path. After checking that both inspect views resolved to the exact operation directory, the restarted runner resumed the same prepared container. The worker recorded one start and returned the unsigned APK, debug symbols, and resource inventory with matching stored digests. The normalized APK content matched the standalone Linux build. Both worker and runner processes closed, the worker port rebound, and the owned container, volumes, and image references were removed. Phoenix and Oban dispatch, customer HTTP delivery, and managed cancellation remain open for this Linux workflow. [Managed Pair25 worker receipt](verification/receipts/l05-managed-linux-pair25-worker-20261120.json)

A second managed Pair25 run observed the same two Android Swift frontends before and after a controlled restart of the native worker. The reopened worker queried the original operation and accepted one authenticated stop. The runner proved the exact container and its processes were gone. The persisted tombstone blocked artifact reads and another start. Both worker listeners and the runner closed, the two TCP ports rebound, and the owned toolchain volume, image references, and scratch were removed. This replay exercised the authenticated worker protocol directly. [Managed Linux cancellation and restart receipt](verification/receipts/l05-managed-linux-pair25-cancel-restart-20261120.json)

The maintained Noble recipe reproduced the approved Pair25 source and Linux lock. The ordinary authenticated Phoenix API accepted one build. After paused admission, restricted Oban dispatched that same operation to the native worker and the Docker runner. PostgreSQL released capacity once. The owner downloaded the APK, debug symbols, and resource inventory with matching digests and read both terminal log events. The driver reported 2,413,517 stdout bytes and zero stderr bytes. Each artifact and log request returned 404 for the other tenant and 401 for an anonymous caller. The exact build container and its raw output were gone, the local services closed, and all five service ports were reusable. The operator stage was reserved for the separate cancellation replay. [Ordinary Linux Pair25 build receipt](verification/receipts/l05-managed-linux-pair25-ordinary-http-20261120.json)

After the managed worker and runner closed, a separate development signer signed the retained Pair25 APK from the direct worker replay. Build Tools 37 verified its v3 signature and 16 KiB alignment. All 26 ordered ZIP payload entries and the original unsigned APK matched byte for byte. The ephemeral key and signed output were removed. [Separate development signing receipt](verification/receipts/l05-managed-linux-pair25-development-signing-20261120.json)

A read-only audit of the same retained Linux APK matched all 26 entries to the resource inventory and all 18 ELF dependency lists to the readback. The 16 bundled runtime libraries matched the pinned toolchain archives byte for byte. All four notices matched the selected source bytes. Both detached symbol files matched their packaged ELF build IDs and passed DWARF verification. The separate policy check passed on 696 exact committed manifests. [Managed APK provenance receipt](verification/receipts/l07-managed-linux-pair25-apk-provenance-20261120.json)

The ordinary Pair25 owner cancel request returned HTTP 202 after the launcher observed an Android Swift frontend in the exact build container. Restricted Oban settled that same build as `cancelled` at revision 3 and PostgreSQL released its reservation once. Both ledgers recorded one start and the worker kept its stop tombstone. Docker removed the container and its raw output before settlement. The three artifact URLs returned HTTP 404 to both signed-in tenants and HTTP 401 to anonymous callers. All nine owned command groups closed, all five ports were reusable, and the dedicated stage, volume, and acquired image references were removed. [Ordinary Linux Pair25 cancellation receipt](verification/receipts/l05-managed-linux-pair25-ordinary-cancel-20261120.json)

A no-signal cancellation probe wrote the worker’s durable tombstone while the Android compiler was active. A marker-write failure and a short wait both kept capacity occupied. After the fixture reaped SwiftPM and fenced the next phase, it settled cancellation without publishing artifacts. The production driver still needs evidence for that transition and for other process paths, including hard deadlines. [Cooperative drain receipt](verification/receipts/managed-android-cancel-drain-20261119.json)

The ordinary local API can now select an operator-pinned Android Starter. The locked Pair24 replay persisted one source input, queued one build and one Oban job, and returned the same selections on replay. The processor was disabled. Dispatch of the selected input and live cancellation remain open. [Android Starter selection receipt](verification/receipts/l05-android-starter-selection-v51-20261119.json)

The same locked Pair24 export completed the ordinary selected-input build. One new POST returned HTTP 201, and its same-key replay returned HTTP 200. Restricted Oban dispatched once, PostgreSQL settled at revision 2 and released the reservation, and the selected build returned the Android driver event and three matching authenticated downloads. An unrelated principal received HTTP 404. The observed out-of-group Swift frontend was absent after worker closure. Live cancellation remains open. [Selected Android native delivery](verification/receipts/l05-selected-android-pair24-native-delivery-20261119.json)


The managed Linux Pair25 selector uses an opt-in catalog and an operator-pinned manifest. Two ordinary selection requests returned the same input and persisted one row. An unrelated tenant and an unknown Starter received HTTP 404. A build request with a changed digest returned HTTP 409 without enqueue. Restricted Oban dispatched one build from the selected response in each of two runs. One completed with two log events and three matching fixture artifacts. One settled after the owner's HTTP 202 cancellation and exposed no artifacts. Both runs used the inert backend and released capacity once. The two billing mirror rows matched before build and after readback. The subsequent live replay verified Docker compilation from the selected input. [Selector controls](verification/receipts/l05-managed-linux-pair25-starter-selection-20261120.json) · [Selected dispatch](verification/receipts/l05-managed-linux-pair25-selected-dispatch-20261120.json) · [Billing controls](verification/receipts/l05-pair25-free-build-billing-control-20261120.json)


A fresh local arm64 Linux VM dispatched the real managed Pair25 build from the ordinary authenticated Starter selection. Two selections returned the same input. One accepted build POST returned 201, the worker and runner recorded one start, and restricted Oban settled the original attempt and released capacity. The owner read two log events and downloaded the unsigned APK, symbols, and inventory with matching byte counts and SHA-256 hashes. The unrelated tenant received 404 and anonymous callers received 401. Billing remained unchanged. The exact container and its writable output were removed, all five fixture ports were reusable, and the service scratch was removed. This replay used the HTTP API. The separate Chrome run covered browser selection and queueing. [Live selected build](verification/receipts/l05-managed-linux-pair25-live-selected-20261120.json)

Hosted source v54 admits the managed Linux Starter selector and its optional migration. The focused checks passed in normal and optimized Python. The archived v53 selection restored all 422 predecessor files byte for byte. [Source admission receipt](verification/receipts/hosted-source-binding-v54-20261120.json)

The compiled console control selected the managed Android Starter, reloaded the single admitted Android input, and submitted its exact scope, source, Linux lock, recipe, and idempotency key. It rendered the matching queued build. Typechecking and all 304 console tests passed on Node 22.23.3 with scripted API responses. [Console selection receipt](verification/receipts/l05-managed-linux-pair25-console-control-20261120.json)

An owned Chrome profile drove the compiled console against stock Phoenix and PostgreSQL. The Starter selection returned 200. One browser POST returned 201, and the console read back that exact queued build at revision 0. PostgreSQL matched the browser's idempotency key, one verified Android input, one build, and one available Oban job. Billing rows stayed unchanged, and no dispatch intent or capacity reservation was created. Chrome and all fixture services closed. The catalog used synthetic operator pins. A subsequent replay completed the same journey with real compilation. [Rendered queue receipt](verification/receipts/l05-managed-linux-pair25-rendered-queue-20261120.json)

The Pair25 browser completion fixture now pauses restricted Oban before opening the bridge. A fresh Chrome profile selected the approved Android Starter and one browser POST returned 201. Chrome and PostgreSQL agreed on the queued build ID, and the processor drained the original job at attempt zero. The same build reached native success at revision 2 in a dedicated Linux VM, with one worker and runner start and one capacity release. Fresh owner API reads returned two log events and three digest-matched downloads. The unrelated tenant received 404 and anonymous callers received 401. Billing matched before queueing, after queueing, and after readback. Eleven command groups and Chrome closed, all six fixture ports and the Chrome debug port were reusable, and the exact VM and scratch were removed. Browser observation ended at queue confirmation. [Real browser-submitted build](verification/receipts/l05-pair25-browser-real-build-20261120.json)

The v85 console reopened the exact Android build submitted earlier by
Chrome. It displayed **Succeeded** at revision 2, rendered both terminal
log events, and downloaded the unsigned APK, debug symbols, and resource
inventory. Their SHA-256 values matched the worker, the authenticated API,
and the bridge. The owner reads returned 200, the other tenant received
404, and anonymous callers received 401. The run used one browser POST,
one worker and runner start, and one capacity release. Billing matched
at all three checkpoints. Eleven fixture groups and both disposable
Chrome instances closed, all nine ports could rebind, and the owned
Docker daemon, Linux VM, and scratch were removed.
[Rendered terminal replay](verification/receipts/l05-pair25-browser-rendered-terminal-1e2de013.json)

**L05 passed for the documented local platform workflow.** Independent
review verified the rendered iOS and Android build evidence, restricted
live cancellation, separate development signing, stock CLI transitions,
SCRAM restore and signed rollback delivery, and store protocol fixtures.
[Local acceptance](verification/receipts/l05-local-platform-acceptance-20261121.json)

An isolated Phoenix and PostgreSQL replay committed signed v3 sequences 7 and 8 for one provisioned target. The browser head and public updater agreed on both. The updater refused staged artifacts, and committed bytes remained available after Phoenix restarted. The independent review led to a startup check that refuses an extra HTTPS listener and workflow triggers for the release UI fixture. Hosted v57 binds the corrected source. [Signed release replay](verification/receipts/local-signed-release-v56-composition-20261120.json) · [Listener checks](verification/receipts/l05-release-delivery-effective-listener-20261120.json) · [Hosted v57 binding](verification/receipts/hosted-source-binding-v57-20261120.json)

Normal Phoenix startup now accepts one opt-in release target and its public trust roots. A dedicated reader using PostgreSQL TLS served a committed offer and artifact. The ordinary browser publisher and stock CLI validate and publish routes used the same release head and restricted writer login in a separate shared-database replay. All 40 selected tests passed, including browser admission with the CLI migration absent and present, listener refusal, and idempotency conflicts in both directions. [Startup provisioning](docs/operations/local-signed-release-delivery.md) · [Startup receipt](verification/receipts/l05-local-release-runtime-v57-20261120.json) · [CLI authority receipt](verification/receipts/local-v3-cli-publication-review-fixes-20261120.json)

Normal Phoenix startup can enable the opt-in CLI writer with the restricted release login and verified PostgreSQL TLS. Signed promotion and rollback passed 37 focused tests with the stock CLI. The upgrade preserves existing publications, requires the action-column grant for transitions, rejects exact retries after assignment-key revocation, and requires explicit validation before rolling back to a browser-published artifact. The composed runtime and transition suite passed 86 focused tests. The ordinary one-boot publication and installed release journey remain open. [Writer startup](verification/receipts/l05-local-release-writer-runtime-6047348a.json) · [Stock CLI transitions](verification/receipts/l05-signed-promotion-rollback-public-6047348.json) · [Composed verification](verification/receipts/l05-release-writer-transitions-composed-20261120.json)

The stock CLI uploaded, validated, and published a development-signed release in the maintained authenticated fixture. The browser head and updater agreed on sequence 8 and its artifact digest, and delivery survived a Phoenix restart. The separate ordinary-boot trial reached two boundaries. The resolver refused the synthetic loopback issuer, and startup had no artifact storage configuration. The passing fixture supplied a restricted uploader. [Stock CLI join receipt](verification/receipts/l05-local-release-join-6047348a.json)

The opt-in uploader used a dedicated verified TLS connection to commit one signed artifact and its audit record. An exact retry added no rows, and the release writer validated the committed digest. On the composed candidate, 80 focused Mix tests and 35 standalone startup checks passed. Independent review reproduced a browser admission failure after provisioning the uploader grants. The correction passed 14 PostgreSQL tests, with usable browser cookies before provisioning, with upload enabled, and after disabling upload while retaining the exact grants. All 13 malformed grant and role variants were refused. [Browser ACL correction](verification/receipts/hosted-browser-artifact-upload-acl-20261120.json) [Uploader TLS receipt](verification/receipts/l05-local-artifact-upload-config-20261120.json) · [Composed startup checks](verification/receipts/l05-local-artifact-upload-startup-composed-20261120.json)

A fresh local Linux VM ran the ordinary release API with the configured identity verifier. The namespace-local issuer handled one TLS JWKS fetch. The configured bearer validated the staged artifact, and publication and exact retry left one sequence-7 ledger row. The updater served the exact signed offer and artifact. Phoenix, PostgreSQL, and the issuer closed, and the owned VM and scratch were removed. The run staged the artifact before startup. The stock CLI upload against the same boot remains pending. [Configured identity replay](verification/receipts/l05-configured-release-linux-authenticated-20261120.json)

The unchanged macOS CLI uploaded, validated, and published the same development-signed candidate twice through one configured Phoenix startup in a fresh local Linux guest. The release started from an empty store. It committed one artifact, one upload audit event, one upload receipt, one validation, and one sequence-7 publication. The updater served the exact signed offer and artifact. The SSH forward closed, both host ports became reusable, and the guest and scratch were removed. Installed activation remains pending. [Stock CLI configured replay](verification/receipts/l05-configured-stock-cli-publication-20261120.json)

Hosted v59 binds the composed release and privacy source. The standalone startup check now supplies disabled release leaves and passes all 15 controls. The composed source formats and compiles with warnings treated as errors, and 41 selected provisioning, protocol, and listener checks passed. [Hosted v59 binding](verification/receipts/hosted-source-binding-v59-20261120.json) · [Startup CI repair](verification/receipts/l05-isolated-release-startup-ci-repair-20261120.json)

Full v59 CI exposed stale migration checks and a shared evidence directory in the release fixture. The repaired Phoenix replay passed 56 selected tests on PostgreSQL 17 with the former shared directory occupied. The identity and Verify services runs also exposed stale predecessor selection in the collector fixtures. The repair restored each intervening source version, and all 316 collector tests passed under the identity sparse checkout and both Verify services Python modes. Hosted v60 binds the four corrected ExUnit files and restores all 461 v59 inputs exactly. On main `70f48537c3`, Phoenix CI passed 965 tests with two skipped, and identity CI passed. [Phoenix CI repair](verification/receipts/hosted-v59-ci-phoenix-repair-20261120.json) · [Collector CI repair](verification/receipts/hosted-v59-ci-collector-repair-20261120.json) · [Hosted v60 binding](verification/receipts/hosted-source-binding-v60-20261120.json)

The v52 artifact-read fixture now requires a successful metadata row while the token is live, then checks that expiry prevents its callback. All 15 focused PostgreSQL tests and both negative boundary controls passed in independent review. The normal and optimized source checks passed, followed by the public Phoenix and isolated identity-network workflows. [Verification receipt](verification/receipts/phoenix-artifact-read-expiry-v52-20261119.json)

Hosted v61 binds the composed release writer and transition source and admits 462 files with 24 ordinary migrations and four opt-in migrations. Each hosted sparse checkout restored all 461 v60 files and their modes. All 316 collector tests passed through unittest discovery in the Verify services sparse checkout after the direct runner reached its six-minute alarm. [Hosted v61 verification](verification/receipts/hosted-source-binding-v61-20261120.json)

The v61 identity and engine workflows passed. Phoenix CI reported three failed release tests. Two local PostgreSQL runs passed the promotion retry after the fixture verified writer reconnection. An isolated Ubuntu replay reproduced the browser fixture's failed database drop and duplicate database. The fixture now closes sessions on its own database during teardown, and both publication cases passed with the CI settings. The earlier browser bootstrap 503 did not recur and remains unexplained. [Browser fixture cleanup](verification/receipts/l05-v61-browser-fixture-session-cleanup-20261120.json) [Phoenix CI](https://github.com/snowdamiz/mixer/actions/runs/44777997623) · [Reconnect control](verification/receipts/l05-v61-release-commit-reconnect-20261120.json)

Hosted v62 binds the configured artifact uploader, browser release fixture repairs, and the stock CLI replay to 470 source paths. The full local suite passed 974 tests with four skips after compiling the CI console drivers. Both browser release cases, promotion retry, and uploader ACL admission passed. All 462 predecessor paths restored exactly. Installed Source141 passed in both Python modes. [Hosted v62 binding](verification/receipts/hosted-source-binding-v62-20261120.json) · [Full local runtime](verification/receipts/hosted-v62-local-runtime-20261120.json) On main, the Phoenix workflow passed the same 974 tests with four skips. The archived report confirmed the disposable PostgreSQL instance stopped and scratch was removed. [Public Phoenix receipt](verification/receipts/hosted-v62-main-phoenix-ci-20261120.json) The identity-network and Owned engine workflows also completed successfully on the exact v62 main revision. [Main workflow results](verification/receipts/hosted-v62-main-workflows-20261120.json)

The maintained recipe rebuilt and signed the Android calculation packet from pinned sources. All 26 handoff hashes passed. The first macOS witness accepted signed sequence 1 and recorded an effects deadline before the first frame. A fresh witness passed baseline, correction, rollback, and cold offline reopen with the same packet and workspace. The packet is staged for Phoenix publication and installed activation. [Android packet preflight](verification/receipts/l05-android-phoenix-packet-preflight-20261120.json)

One configured Phoenix boot received six stock CLI calls for the signed FieldLog Android packet. Two publications and one rollback committed across the three exact retries. The app installed once and fetched the original signed offer and artifact bytes at each sequence. It displayed 0%, 100%, 0%, then 33%, 100%, 0%, and then 0%, 100%, 0% after rollback. A new process reopened the cached rollback offline with a fresh healthy launch. The workspace hash stayed identical. The emulator, private ADB, forwarders, PostgreSQL and Linux guest closed. [Native Phoenix delivery](verification/receipts/l05-l04-fieldlog-android-phoenix-live-20261120.json)

Hosted v63 binds the Android replay to the 471-path source selection. All 470 v62 and 462 v61 inputs restored byte- and mode-exact. The Phoenix, identity-network, Verify services, and installed Source141 projections passed local source admission in both Python modes. [Hosted v63 binding](verification/receipts/hosted-source-binding-v63-20261120.json) GitHub's Phoenix job passed 974 tests with four skips and closed its PostgreSQL fixture. The configured-identity replay was one of the skips. The installed Android result comes from the separate local run. [Public Phoenix receipt](verification/receipts/hosted-v63-main-phoenix-ci-20261120.json) The identity-network and Owned engine workflows also passed on the same main revision. [Main workflow results](verification/receipts/hosted-v63-main-workflows-20261120.json)

The production console rendered the empty release head, two signed releases at sequences 7 and 8, and rollback at sequence 9 with the original manifest digest. Phoenix issued the browser's sessions through a synthetic identity fixture. The second tenant received HTTP 404 and saw no release fields. The first navigation after Phoenix restarted reported an unavailable session. A fresh navigation showed sequence 9. The cause of the first failure remains open. [Rendered console receipt](verification/receipts/l05-console-release-head-71e6ffa.json)

The production console now requests committed release details. The live browser showed the manifest source commit, payload size, signing key IDs, ledger action, and exact signed capabilities for publications 7 and 8 and rollback 9. The same tenant received 404 for the wrong channel, and a second tenant received 404 for the original target. Neither denial rendered release data. The test dropped its database, closed the owned preview, and confirmed reuse of all six ports. The full local hosted suite passed 975 tests with four skips. Hosted v66 admits 475 source inputs and 27 ordinary migrations, with byte-exact restoration of both preceding versions. [Source binding](verification/receipts/hosted-source-binding-v66-f2045e9b.json) [Live details replay](verification/receipts/console-release-head-details-acid-20261120.json)

A follow-up sent the same persisted session directly to the replacement Phoenix listener. One read returned HTTP 503, and two overlapping browser session reads returned 200 and 503. The bridge also returned a separate HTTP 502 while it still pointed at the retired listener. The internal cause of the Phoenix 503 remains open. [Session restart comparison](verification/receipts/l05-l07-console-session-restart-63097fdd.json)

A controlled page-load replay reproduced HTTP 503 from lifecycle checkout contention. Session and release-head reads now retry a proven pre-checkout refusal for up to 300 ms per lifecycle read. A real PostgreSQL fixture recovered both reads after check-in and kept the owner ready after sustained refusal. Independent review verified that the owner checkpoint itself obeys the retry cutoff. The two Phoenix CI assertions now include the existing halt migrations. The complete sparse-hosted suite passed 975 local tests with four opt-in skips. Hosted v65 admits the same 474 paths and restores all v64 inputs exactly. [Source binding](verification/receipts/hosted-source-binding-v65-83eb5167.json) · [Browser retry and CI evidence](verification/receipts/l05-l07-browser-read-checkout-cutoff-v65-20261120.json)

Hosted v64 adds signed rollout halt and a scoped halt audit view to local Phoenix. The stock CLI committed a zero-rollout assignment, updates returned HTTP 204 across a Phoenix restart, and a higher signed promotion restored offers. Exact retries returned the original result and left one audit event with the committed health sample. The existing artifact audit bytes and cursor matched across both API boots. The binding admitted 474 source paths and 26 ordinary migrations. Its v63 predecessor restored byte- and mode-exact. Installed iOS halt remains pending. [Signed halt](verification/receipts/local-release-halt-health-71e6ffa.json) · [Halt audit](verification/receipts/local-rollout-halt-audit-d4caebb.json) · [Source binding](verification/receipts/hosted-source-binding-v64-20261120.json)

One owned Android API 36 emulator exercised the signed halt using two fresh users. The active installation rendered sequence 2 and retired. The other received 1,024 bytes of the 15,531-byte artifact response and accepted no candidate. The stock CLI halted sequence 3, its exact retry left one audit event, and both installations received empty HTTP 204 responses. The pending bytes stayed unchanged. After the relay and reverse mapping closed, the active installation reopened sequence 2 in a new process with the same workspace. Both IP route lookups were unreachable. The emulator, private ADB, and fixture closed, and all six ports rebound. [Installed Android halt](verification/receipts/fieldlog-android-rollout-halt-native-20261120.json)

An installed Android API 36 update stayed on sequence 1 through a 1,024-byte interruption and a cold offline reopen. The saved prefix matched byte for byte. A subsequent response with one changed prefix byte was refused and discarded. The same signed sequence 2 activated after a matching complete response, rendered the corrected calculation, and cleared the spool. All six workspace reads matched. Both origins, the emulator, and private ADB closed, and all five ports were reusable. Installed iOS resume remains pending. [Android resume receipt](verification/receipts/fieldlog-android-signed-resume-native-20261120.json)

### TaskCompletion parity and source diagnostic

The maintained Swift FeatureProbe passed on public Mixer `d89c742e9d`
after the VM admission refactor. Native Swift and Guest UI V1 matched
all four TaskCompletion frames and preserved them on malformed events.
Float, associated-type, and wrapper probes matched in both paths.
Both VM entry points refused shared memory without publishing a handle.
All 32 focused VM tests passed. The replay recorded closure of all
34 inner command groups and removed its scratch. Installed iOS parity
and performance remain open. [Host replay](verification/receipts/l03-swift-feature-probe-d89c742e.json)

The strict UTF-8 title probe executed with Embedded Swift 6.3.3 and
the pinned stock WASI allocator in Guest UI V1. Four exact title
frames matched native Swift, and all twelve invalid events preserved
the previous frame. The separate Foundation import was refused.
[Producer replay](verification/receipts/l03-swift-string-title-7d257e0d.json) · [Independent replay](verification/receipts/l03-swift-string-title-independent-7d257e0d.json)

The exact FieldLog model uses `String.localizedStandardContains` to search
titles and sites. Both target source copies matched. Swift 6.3.3 on
arm64 macOS verified six queries, including case and accent matches,
Arabic, blank input, and no match. Result order and stable IDs survived
workspace decoding, and the searches left workspace bytes intact.
Embedded Swift refused Foundation before emitting an object. The
Foundation-free control emitted a Wasm object.
[Project-search receipt](verification/receipts/l03-fieldlog-project-search-8e8d75c3.json)

The Swift 6.3.3 cancellation replay observed a cancelled task and
caught `CancellationError` from `Task.checkCancellation()`. Two
uncancelled controls stayed clear. The pinned Embedded Wasm compiler
refused the task APIs before object emission, and the scalar control
emitted a Wasm object. The default replay matched all four prior
TaskCompletion frames and passed all 32 VM tests. Both replay
scratch directories were removed.
[Cancellation receipt](verification/receipts/l03-swift-task-cancellation-6b4e756c.json)

At Mixer `7b61fe1cd9ae79d3153a29b5aff91c0146b0bd99`, the signed TaskCompletion trial passed on an owned AOSP arm64 API 36 emulator. A single staged Package Manager install matched development APK SHA-256 `f95407b596fe7d883a06a2c132b0ca0705b4f1189124d626c50c9e5a41368787`. The app drew **Open**, **Review required**, **Completed**, and **Open** from the same Swift source as the host differential. The JNI route refused the stale revision-1 input at revision 2. The fourth tap trapped at `TaskCompletion.swift:94:9`, function 8, Wasm offset 1883. The app kept the same PID and published no revision 5. **Close guest** confirmed retirement.

The rebuild used Wasm SHA-256 `59623248e6afe4fd66e4dbb0adf8ae6cd353528ad6f4769b52269a3020e2811b` and verified the same four frames and diagnostic on macOS before the Android run. The first Android attempt reused a debug-only `run-as` check and closed before guest launch. The passing run used direct screenshots and PID-scoped logcat readback. It used Android Emulator 37.2.12, ADB 37.0.1, and system image build 13818094. All 344 recorded groups closed, the private ADB and emulator exited, the disposable AVD was removed, and all three ports were reusable. D3 remains open for iOS and the local target performance comparison. [Installed Android replay](verification/receipts/l03-d3-task-completion-android-7b61fe1c.json)

Five matched native Swift and owned-VM TaskCompletion pairs ran on a fresh API 36 arm64 emulator. Every process reproduced the four frame digests. Both paths refused two invalid events with unchanged frames. The guest trap mapped to TaskCompletion.swift:94:9. Median sums for three prepared-event-to-frame intervals were 3.459 µs native and 970.667 µs guest. Median whole-process peak RSS was 20,008,960 and 21,151,744 bytes. The emulator and private ADB group closed, and all three ports were reusable. Android app latency and the iOS local comparison remain pending. [Matched Android receipt](verification/receipts/l03-d3-taskcompletion-android-matched-20261120.json)

The same TaskCompletion harness built optimized and debug arm64 iOS Simulator executables against the owned VM with Xcode 27.2 and Rust 1.99.0. Both retained executables passed strict signature verification. The Mach-O platform, linked VM symbols, and SDK dependencies matched the Simulator target. The handoff includes the exact 5,263-byte guest from the signed-size replay. All 23 command groups closed and build scratch was removed. The retained optimized executable was selected for a fresh Simulator replay. [iOS build receipt](verification/receipts/l03-d3-taskcompletion-ios-simulator-link-20261120.json)

The optimized arm64 executable ran through `simctl spawn` on a fresh
iOS 27.0 Simulator. Native Swift and the owned VM matched all four
frame digests and preserved the current frame for both refused
events. The guest mapped the trap to `TaskCompletion.swift:94:9` and
closed. Five alternating timing pairs completed under high host
load. The timing receipt describes three accepted turns per process.
Installed FieldLog UI, signed activation, and iOS peak RSS remain open.
All 105 commands closed. The fresh device was removed with all 13
monitored external devices unchanged.
[Standalone iOS replay](verification/receipts/l03-d3-taskcompletion-ios-simulator-parity-926f6d94.json)

A separate generic iOS Simulator XCTest packet has three replay
selectors for parity and refusals, the native measurement, and the
guest measurement. Independent static readback verified all 30 hashes
and both bundle signatures. Its 5,224-byte diagnostic guest matched
the four historical frame digests and trapped at TaskCompletion.swift:94:9
on macOS. The earlier signature covers its own 5,263-byte payload.
Simulator execution, signed activation, and the installed FieldLog
frontend and renderer remain pending.
[XCTest packet receipt](verification/receipts/l03-d3-taskcompletion-ios-xctest-packet-24b8efb9.json)

### Reproducible Android engine pair

The [engine-pair recipe](tests/integration/fieldlog-android-engine-pair/README.md) passed all seven phases from a fresh checkout of `201ead70ff68bfe18de24c0642f518701459e0a4` on Xcode 26.6 and macOS SDK 26.5. The build matched both pinned VM trees and all four Android and host archives. Swift's incremental LLVM module hash caused the original Wasm pin mismatch. Disabling that incremental step produced byte-identical guests across fresh builds and both guests passed on both host engines.

The recipe built versions 24101 and 24102 with one development certificate, distinct linked runtimes, and 16 KiB APK alignment. The signed replay passed 35 HTTP and 20 Swift verifier checks and preserved durable state across the origin restart. Both service groups closed, the port was reusable, and the private keys and build scratch were removed. This proof covers newly built host artifacts. The earlier Android engine replacement used a separately built pair.

### Android renderer source Pair25

Pair25 incorporates the Android editor callback fix for a pressed-state update from a retired renderer. The reviewed source profile passed 25 focused Swift checks, strict Java and D8 compilation, and installed-source admission in normal and optimized Python. The follow-up matched all three getter records to the emitted bytecode and preserved the predecessor archive. Existing Pair24 projects can use their matching CLI or explicitly upgrade. The registered Pair24 Starter retains its existing source and worker pins. [Pair25 receipt](verification/receipts/renderer-press-pair25-composition-18e9d8be.json)

The [public Pair25 workflow](https://github.com/snowdamiz/mixer/actions/runs/44671130901) passed. A separate local run built both pinned CLIs, verified build and export refusal for the original Pair24 project, and upgraded a fresh copy with the original and platform lock intact. The relocated public V4 export built an unsigned arm64 APK from its bundled driver after the source projects and both CLIs were removed. AAPT2 confirmed API 36 minimum, target API 37 and the expected launcher. ZIP integrity, 16 KiB alignment and runtime notices passed. The first readback used the legacy API floor. The corrected check verified the same APK. All 26 command groups closed and owned build scratch was removed. [Independent export receipt](verification/receipts/l01-l08-pair25-independent-export-20261119.json)

### Android selected-draft action failure

The rebuilt FieldLog APK with SHA-256 `dd3472914451d292d3e7b837bcb4c5469563ea9205b05324e79817b7a7e1588b` passed static and host verification from the reviewed app tree `3e456ac47f590b5749f465dad193d6551b9c1804`. On an owned AOSP arm64 API 36 emulator, the ordinary editor imported a JPEG through Android DocumentsUI and saved draft `L08ValveA`. Signed sequence 1 initially displayed **Saved draft loaded** and **JPEG linked**. **Check saved draft** later displayed **Saved draft unavailable** and **No photo shown**.

Signed sequence 2 opened the same selected draft and displayed **Follow-up unset** and **JPEG linked**. Two presses of **Mark follow-up required** left the optional value absent. The seed, sequence-1, and sequence-2 workspace snapshots matched byte for byte at revision 3, including the selected draft and photo reference. The workspace SHA-256 was `102c606cf05cc1018f95b0769ed7c6375a62164fceb500b0ba4fe1778951e24c`. Both signed guests reached native health and retired before teardown. The reverse mapping, emulator, private ADB, and origin closed, the disposable instance was removed, and all four ports were reusable. The run stopped before sequence 3, offline editing, or re-upgrade. L08 remains running.

The Android diagnostic APK traced one tap per signed draft action. Both taps reached the guest and issued a storage request. The sequence-1 read reached its 30-second deadline. The sequence-2 write returned cancelled after about 30 seconds, and the follow-on read reached its own deadline. Both rendered **Saved draft unavailable**. The follow-up flag stayed unset, and the workspace bytes matched at revision 3. The emulator, private ADB, and origin closed. Storage lease entry remains unobserved, and rollback is still open. [Draft action trace](verification/receipts/fieldlog-android-draft-action-deadline-20261119.json)

Moving the selected-draft storage lease off MainActor fixed both traced actions in one Android installation. Sequence 1 read the draft, sequence 2 committed the follow-up flag at revision 4, and sequence 3 reused the earlier payload while preserving the exact workspace. The ordinary editor then crashed on a long press of the note after the rollback dialog closed. The stack ends at `NativeField.drawableStateChanged` with `unknown retired editor callback`. Offline save, cold reopen, re-upgrade, and selection isolation remain open. [Android verification receipt](verification/receipts/fieldlog-android-draft-storage-owner-20261119.json)

The subsequent Android APK preserved the tested JNI and changed the Java renderer and DEX. The ordinary editor selected the note on the former crashing long press, then saved offline at revision 5. A cold process restored the note and cached sequence 3. Sequence 4 read the flag and JPEG, and a second draft showed the field unset with no photo. Reselecting the first draft showed its edited note and retained flag after one guest-open retry. The final runner then failed because navigation left the previous saved restore point intact. Rechecking the captured workspace reproduced the old assertion and passed with the corrected last-saved check. A fresh full replay remains pending. [Renderer and rollback receipt](verification/receipts/fieldlog-android-draft-renderer-offline-20261119.json)

The fresh Android diagnostic run verified one baseline check, the optional flag write at revision 4, signed rollback with identical workspace bytes, and an ordinary offline note save at revision 5. After cold start, the editor restored the note and JPEG, and the cached sequence-3 guest completed another check. The operator annotated the restored screen under a different label than the runner required. That stopped the run before durable cold readback or re-upgrade and left the exact emulator and private ADB under custody hold. The origin and log observer closed. L08 remains open. [Fresh Android replay receipt](verification/receipts/fieldlog-android-draft-first-frame-replay-20261119.json)

### Recovered Android startup-quarantine packet

The recovered fixture re-signed the verified Android engine-pair APK with fresh development trust material. Version 24102 kept its linked engine, app code, manifest, and permissions. The packaged trust roots and matching installed identity changed. The product verifier accepted all three assignments. Sequences 2 and 3 referenced the same startup-failure artifact. The pinned Mixer VM archive `0beb9fbab5f2d1f718482391a43ecb57a3e76f6e3e0d31a0676b87b7a1852116` started the healthy guest and reported `unreachable` on the failure guest with zero host calls. Both host VM sessions closed. The re-signed APK SHA-256 was `48807d0f23952004e65f63874b90cdc54cf1c4c8f2249b9891e1314bc579504b`. These checks cover host admission and startup behavior.

The installed AOSP arm64 API 36 replay passed the Android startup-quarantine scenario. FieldLog saved an open task through the ordinary editor. The public CLI published all three assignments to the owned release service. The app reported `deterministic_trap` for sequences 2 and 3, kept the sequence-1 healthy candidate, and quarantined artifact `6778642bea9cc16961f641bd77081275a197364366e3ceac438b9a8cdea7d071` after the second failure. The accepted sequence advanced to 3.

After the origin stopped and the reverse mapping was removed, two new app processes reopened without a default network. Both displayed **Using saved checklist release** at sequence 3 and rendered the original healthy guest. The installation ID, failure count, and workspace bytes matched. The workspace SHA-256 was `cbdc01e5ed6769858ec5a010f276998175030a855a3c08322d6b2dc1c8019a13`. The observation record preserves the actual offline heading and the comparison alias used by the first runner. Both guests retired. All 506 command groups closed, the owned AVD was removed, and all four ports were reusable.

The first origin attempt stopped before any device action because the readiness probe used an unsupported Python HTTP context manager. Its origin exited on SIGINT and its process group was absent. The launcher recorded the nonzero exit and retained that setup record. The corrected run used a new origin. D5, L04, and L08 remain running for the remaining targets and cases.

## November 18 local verification

The identity-network, Phoenix, and owned-engine workflows passed all 11 jobs on Mixer main at `65c89e08af`. Both workflows affected by the historical lock assertion passed. [GitHub Actions run record](verification/receipts/hosted-v42-main-ci-65c89e08af.json)

The native build worker records a fixed reason in its private SQLite ledger when a build's closure is uncertain. It distinguishes a failure before it receives a process handle from a failure recording the launch after it receives one. Both cases retain the capacity hold. The identity-network collector also reads the preserved lock for its historical format test. L07 still needs a closed native build backup and restore. [Verification receipt](verification/receipts/l07-hosted-worker-uncertainty-v42-20261118.json)

Hosted v41 passed 932 tests with two skips on the local Phoenix and PostgreSQL fixture. The role edit and overlapping member read both returned HTTP 200 after upgrade. Conflicting authority writes still waited, and rollback restored the catalog exactly. The terminal log and concurrent build replay checks passed with the workflow's full fixture set. L06 and L07 remain open. [Verification receipt](verification/receipts/hosted-v41-local-qualification-20261118.json)

A scoped L07 restore matched one synthetic PostgreSQL build row to its SQLite worker operation and three restored artifact descriptors. The worker refused a corrupted payload. Both clusters and worker listeners closed. The earlier successful native runs removed their original stores. Full Phoenix reconciliation still requires the settled PostgreSQL row and job, matching SQLite journal, and manifest plus payloads from one closed native build. A fresh capture admitted one authenticated build and recorded one worker start. Worker shutdown returned uncertain before an aligned snapshot could be taken. The exact process and inputs are held. [Native capture hold](verification/receipts/l07-real-build-freeze-3ec017157a.json) [Build-journal restore](verification/receipts/l07-hosted-build-journal-restore-8844d474.json)

The dedicated Android Debug calculation APK passed integrity checks. The host witness completed 0% → 33% → 0% → 0% in one developer run. The separate root replay reached 0% and 33%, then missed the existing guest deadline in sequence 3 after effects intent. The origin and its three host probes closed. Two bounded follow-up macOS runs completed rollback at the existing 50 ms wall deadline. The prior failure did not recur, and its execution time versus waiting time remains unmeasured. Installed Android rollback and offline reopen remain open. [Deadline discriminator](verification/receipts/fieldlog-android-calculation-sequence3-host-340061c8.json) [Debug packet](verification/receipts/fieldlog-android-calculation-debug-e9b2cbdf.json) [Independent deadline observation](verification/receipts/fieldlog-android-calculation-root-host-deadline-41a05264.json)

The calculation packet was rebuilt with a fresh runtime and signer. It installed once on Android API 36 and opened the exact workspace showing **1 of 3 tasks completed**. Signed sequence 1 accepted its offer and recorded possible effects. Android reported an input timeout waiting for window focus loss, and the recovery store still had no healthy frame. The origin closed. The emulator and private ADB are held because guest retirement was unverified. Correction, rollback, and offline reopen remain open. [Native calculation receipt](verification/receipts/fieldlog-android-calculation-focus-anr-20261119.json)

An Android API 36 diagnostic with the traced APK rendered **0%, 100%, 0%** from one tap on sequence 1. The focus callback returned, VM effects were enabled, and the exchange accepted the native draw. After Done, durable state recorded both health milestones and the exact 3,530-byte workspace. All 199 command groups closed and all four ports were reusable. A separate full replay showed the same percentages, then the readback rejected its combined health and pending-state check while the dialog remained open. The second emulator and private ADB remain held. A fresh discriminator verified that both health milestones were durable while the matching attempt was still active. The strict verifier expects the attempt to be absent after retirement. A tap sent without the newly required checkpoint screenshot was refused before input and left the discriminator's emulator and private ADB held. The origins closed. A host control verified that the corrected checkpoint can refuse that tap and still accept a properly witnessed tap. Correction, rollback, and cold offline reopen remain open. [Traced calculation receipt](verification/receipts/fieldlog-android-calculation-first-open-20261119.json)

The calculation replay now has separate live and retired readback checks. The live check requires both health milestones on the matching active attempt. The retired check requires closed effects and a cleared attempt, then compares the committed health and candidate with the live readback. Sixteen controls passed in normal and optimized Python, using the genuine closed sequence-1 snapshot and a derived active control. The following Android replay completed the installed calculation. [Readback controls](verification/receipts/fieldlog-android-calculation-phase-readback-20261119.json)

One fresh Android API 36 arm64 emulator installed the traced calculation APK once. Signed sequence 1 rendered 0%, 100%, 0%. The stock update action moved to sequence 2 and rendered 33%, 100%, 0%, then signed rollback at sequence 3 restored 0%, 100%, 0%. A new app process reopened saved sequence 3 with airplane mode on, no default route or ADB reverse mapping, and the origin closed. All four launches reached both health milestones. Done retired the rollback before and after the cold reopen. The APK, runtime, installation, revision-9 workspace, and 11 outbox IDs stayed the same. All four owned groups closed and all four ports were reusable. The fresh AVD and scratch were removed. Installed iOS calculation remains pending. [Android calculation receipt](verification/receipts/fieldlog-android-calculation-correction-20261120.json) The independently reviewed source-built APK reproduced the same calculation, signed rollback, and offline cold reopen on one fresh Android API 36 emulator. The workspace bytes matched through retirement. [Source-built native replay](verification/receipts/fieldlog-android-calculation-source-native-20261120.json) The maintained source recipe built a fresh signed handoff in one invocation. The host replay passed all four phases with identical workspace bytes. BoringSSL build paths changed the JNI digest, and fresh signing changed the runtime fingerprint. The fresh APK is pending device verification. [Clean rebuild receipt](verification/receipts/fieldlog-android-calculation-rebuild-host-20261120.json)

The FieldLog macOS host replay attempted to add the native HTTPS capability to a healthy storage-only runtime. The developer service refused the old-fingerprint artifact with HTTP 422, and the old host kept its signed sequence-2 offer and workspace. The new fingerprint received sequence 3 and admitted the HTTPS adapter. The old host rendered the same saved-task results in a fresh offline process. Installed mobile readback and the store-build classification for this HTTPS change remain open. [Native capability OTA receipt](verification/receipts/fieldlog-native-capability-ota-71e6ffa.json)

One Android API 36 emulator installed the storage-only APK and fetched an incompatible signed sequence-3 artifact. The app used its healthy sequence-2 release and reopened that candidate in a cold offline process. The same-signer in-place upgrade added the HTTPS configuration and grant under a separate runtime fingerprint. It activated its own sequence 3 and preserved the installation ID, workspace bytes, and prior runtime recovery file. Both origins, private ADB, and the emulator closed. [Android build and host replay](verification/receipts/fieldlog-android-native-capability-ota-20261120.json) · [Installed Android upgrade](verification/receipts/fieldlog-android-native-capability-in-place-20261120.json)

The stock release inspector refused both original APK identities before classification because their native ABI digest differs from the linked SDK. The stock v3 verifier accepted both offers on their respective runtimes and refused the successor offer on the original runtime. [Original stock inspection](verification/receipts/fieldlog-android-https-stock-inspector-ad295143.json)

The current-ABI Android pair links both APKs to one fresh VM archive. The APKs share a development signer and byte-identical compiled manifests. The distinct signed guests rendered 0%, 100%, and 0% on the storage-only macOS host witness and 33%, 100%, and 0% on the HTTPS witness. The old runtime retained its recovery and workspace bytes. The stock inspector admitted both native identities and signed offers, then stopped because its confirmation-flow schema cannot decode the calculation observations. These read-only APKs remain blocked at behavior-evidence decoding. [Current-ABI build and inspection receipt](verification/receipts/fieldlog-android-https-current-abi-b144c2c2.json)

The same current-ABI pair ran on one owned Android API 36 emulator. The old APK rendered 0%, 100%, and 0%. It fetched the incompatible higher offer, kept its sequence-2 candidate, and reopened that candidate in a cold offline process. An in-place development install using the same signer and version code activated sequence 3 and rendered 33%, 100%, and 0%. The workspace, installation, and prior runtime recovery bytes stayed unchanged. Both origins, the emulator, and private ADB closed. [Installed current-ABI replay](verification/receipts/fieldlog-android-https-current-abi-native-20261120.json)

For a separate ordinary selected-task APK pair, stock Mixer classified the same-native confirmation edit as `ota-compatible` and the HTTPS successor as `store-build-required`. Both reports kept publication disabled. An independent macOS replay of the exact offers observed one persisted completion after each action, unchanged workspace bytes before confirmation, and old-runtime refusal followed by a cold launch of the retained sequence-2 candidate. [Stock producer receipt](verification/receipts/fieldlog-https-stock-producer-37e351f5.json)

The same APKs and offers exercised direct completion, review and confirmation, incompatible-offer fallback, cold offline reopen, and in-place native replacement on an owned Android API 36 emulator. The workspace, installation preferences, and old recovery journal matched across replacement. Teardown returned EPERM while checking emulator PGID 17018. Keep the exact emulator and campaign under custody hold, and keep installed acceptance pending. [Android observations and custody hold](verification/receipts/fieldlog-android-https-selected-task-native-37e351f5.json)

The pinned public FieldLog checkout and tracked overlays reproduce the exact source of the Android calculation replay. The pre-trace and traced Git trees match, along with 25 and 29 per-file SHA-256 pins. The delivered native packager still requires the previous APK. [Source receipt](verification/receipts/fieldlog-android-calculation-source-review-20261120.json)

A signed release restored into a separately initialized PostgreSQL cluster with a different system identifier. Restricted runtime reads reproduced the signed artifact, assignment, and audit bytes. Idempotent publication and tenant isolation held. Sequence 2 added three linked audit events. Both clusters closed. The receipt transcribes results after the first cleanup removed the raw logs. Hosted build-journal reconciliation and cluster-wide role and configuration recovery remain open. [Cross-cluster restore](verification/receipts/release-postgres-cross-cluster-restore-20261118.json)

A controlled member session read reproduced the free owner's HTTP 503 at the default pool size. PostgreSQL reported a timeout on the shared identity-profile row. The candidate uses shared read locks, completed the same role change once and still blocked concurrent authority writes. The create-authority SQL generated byte for byte identically. Independent review confirmed the authority fences and found that the catalog's exact SQL match requires an existing-installation migration and coordinated rollback. That migration and browser qualification remain pending. [Role-edit diagnostic](verification/receipts/l06-member-session-read-lock-41a05264.json)

The Android startup-failure test packet passed host verification. The signed CLI delivered all three assignments, and the VM started the healthy payload and classified the failing startup with zero host calls. The two failure assignments bind the same artifact. Independent APK readback confirmed 34 non-signature members and only the two expected trust-asset changes. On macOS the pinned coordinator quarantined the shared failing artifact after sequences 2 and 3 failed before effects intent. Both failures recovered the sequence-1 candidate. After the listener closed, two fresh host processes reopened that candidate and the exact workspace without re-entering the failed guest. Installed Android rendering and lifecycle checks remain open. [Durable host recovery](verification/receipts/fieldlog-android-startup-durable-host-4766a73d.json) [Host preflight](verification/receipts/fieldlog-android-startup-host-preflight-83efa96c.json) [Packet audit](verification/receipts/fieldlog-android-startup-packet-review-41a05264.json)

The installed Android D3 attempt booted the owned API 36 emulator. The ADB install exceeded its bound before the app rendered a frame. The install command, private ADB, emulator, and exact run directory remain held. The signed macOS parity and source-diagnostic preflight passed. [Installed attempt](verification/receipts/l03-d3-android-install-custody-41a05264.json) [Build and host preflight](verification/receipts/l03-d3-android-root-replay-ff7f67a3.json)

Both reviewed D0 and D1 sign-in overlays built as complete generic arm64 iOS apps. The standalone link map contained zero Mixer objects. Adoption built the real project detail against public SDK pin `56ff14c9`. Both unsigned apps have the same bundle identity and compiled Keychain configuration. Simulator installation and signed Keychain continuity remain open. [Full iOS build receipt](verification/receipts/fieldlog-d0-d1-generic-ios-dfddb38f.json)

The full iOS calculation run stopped at installation with CoreSimulator Mach error -308. Root removed the disposable device after confirming Shutdown. The external comparison found one unrelated Minds Simulator changed from Booted to Shutdown. Mixer paused iOS Simulator verification for recovery coordination. [Install and cleanup receipt](verification/receipts/fieldlog-ios-full-calculation-install-recovery-41a05264.json)

The user authorized resumption on a fresh disposable Simulator. Public Accessibility checks initially refused before any device operation. After trust returned, the installed signed row XCTest passed on a fresh iOS 27.0 ARM64 device. All three run-owned devices were removed, and the 13 monitored external devices matched their baseline at every checkpoint. [Fresh-device preflight](verification/receipts/fieldlog-ios-fresh-device-accessibility-preflight-613fb3c1.json) [Fresh installed replay](verification/receipts/l08-ios-fresh-simulator-signed-row-584cd194.json)

In the rebuilt shared-origin replay, both Android APKs installed and matched their pins. Activity Manager reported a launch timeout before the first FieldLog screen. The crash buffer contained repeated Android Bluetooth service failures. iOS ended its rendezvous wait, and the owned emulator, Simulator, private ADB and origin closed. Neither app reached a signed release phase. [Joint native attempt](verification/receipts/fieldlog-rebuilt-shared-native-launch-41a05264.json)

The replacement Android install passed report export to a separate reader, signed sequences 1–5, and offline recovery. It preserved the 2,112-byte partial file across restart, completed the same saved task, and imported a photo that survived a cold reopen at revision 9. The APK matched after the final reopen. The owned emulator, ADB, and origin closed. [Android native replay](verification/receipts/fieldlog-android-restage-signed-native-41a05264.json)

The Android API 36 cohort replay verified the signed 50% rollout. Bucket 4999 received the exact sequence-6 offer and bucket 5000 received an empty HTTP 204. One fresh install landed in bucket 3805, received HTTP 200, and committed sequence 6. A separate clean install landed in bucket 8709, received HTTP 204, and kept sequence 5. In both runs the APK and workspace bytes matched after offline reopen, and all owned processes closed. The paired native run remains open. [Android cohort receipt](verification/receipts/fieldlog-android-cohort-native-41a05264.json)

One Android API 36 development install admitted the initial signing keys, declined offers using revoked artifact and assignment keys, and reopened healthy sequence 1 while disconnected during the publisher's key transition. Reconnecting accepted the replacement keys at sequence 2 and recorded both native health milestones. The installation, APK and workspace bytes matched throughout. Host verification separately refused the initial keys at expiry. The paired delivery run remains open. [Installed rotation receipt](verification/receipts/fieldlog-android-key-rotation-native-41a05264.json) [Host controls](verification/receipts/fieldlog-android-rotation-host-bceb3705.json)

The iOS key-rotation packet passed a generic arm64 Simulator build-for-testing, ad hoc signature checks, and host checks for revoked keys and intact recovery state. All 99 files matched their checksums after the packet was copied. [iOS preparation receipt](verification/receipts/fieldlog-ios-key-rotation-preparation-fef67b64.json)

One fresh iOS 27.0 arm64 Simulator passed the installed development-key rotation journey. The app rejected releases signed with either revoked key, reopened healthy sequence 1 offline in a new process, and accepted the replacement keys at sequence 2 in that process. The maintained readback matched the exact workspace bytes at all five checkpoints and reconciled the healthy and previous-healthy records with the signed payloads. The runner removed the disposable device and matched all 13 external Simulator states at five checkpoints. The initial setup failed on a missing origin validator before device creation. Native clock expiry and paired native delivery remain open. [Installed iOS rotation receipt](verification/receipts/fieldlog-ios-development-key-rotation-native-fef67b64.json)

A separate clean-source recipe builds both rotation guests from public inputs and signs them for the installed runtime. Eleven macOS verifier cases passed, including expiry and independent artifact and assignment revocation. The installed actor kept the saved workspace and recovery bytes on refusal and reopened the same task under both valid assignments. The replay now checks exact signed response digests, prepared plan filters, and the selector in the dispatched XCTest result. The maintained Debug arm64 Simulator app, runner, and test bundle built with fresh development roots. The strict ad hoc signature, Mach-O platform, compiled Swift method and async bridge, and exact prepared selector checks passed. All eight loopback response hashes matched. [Generic build receipt](verification/receipts/fieldlog-ios-key-rotation-generic-4bf1078d.json) [Host receipt](verification/receipts/fieldlog-ios-key-rotation-host-885d11ae.json) · [Adoption controls](verification/receipts/fieldlog-ios-key-rotation-adoption-controls.json) · [Recreation recipe](capability-activation/verification/fieldlog-ios/rotation/README.md)

The replacement Android APK passed the exact historical 240-byte title through signed sequences 1 to 3 on API 36. Review left the workspace unchanged. Confirm appended one outbox event. Rollback and offline cold reopen preserved the completed workspace and all 240 title bytes. The runtime kept its 50 ms guest-turn budget. The earlier intermittent off-CPU delays remain unexplained. [Installed long-title receipt](verification/receipts/fieldlog-android-historical-title240-native-41a05264.json)

Two five-pair macOS replays at `4bf1078d46` matched all four historical TaskCompletion frames and the source diagnostic. Each run timed 15 turns per path from prepared event to materialized frame. The second run measured median three-turn sums of 7.375 µs in native Swift and 862.000 µs in the owned VM, with process peak RSS medians of 6,651,904 and 7,356,416 bytes. Both rebuilt unsigned Wasm modules were 5,266 bytes and had different hashes. The receipt pins both harness blobs and records both samples. Signed update size and installed mobile measurements remain pending. [Matched host replay](verification/receipts/l03-d3-taskcompletion-matched-macos-4bf1078d.json) The pinned overlay instructions were exercised in a third five-pair host replay, which reproduced all frame digests and the diagnostic. [Replay guide](compiler/experiments/fieldlog-guest-benchmark/README.md) · [Third replay receipt](verification/receipts/l03-d3-taskcompletion-pinned-replay-00aa86d3.json) A separate signed macOS host delivery measured 8,930 bytes across the exact offer and artifact HTTP response bodies for one update. The raw Wasm and signed envelopes totaled 6,969 bytes. The downloaded payload matched the four TaskCompletion frames after protocol verification. [Signed delivery measurement](verification/receipts/l03-d3-taskcompletion-signed-size-a55f5a55.json)

On current Mixer `8fa09d66e7`, five interleaved macOS pairs matched all
four TaskCompletion frames. Both paths preserved the last frame after
two invalid inputs, located the trap in `TaskCompletion.swift:94`, and
closed every guest owner. Native Swift's median for three prepared
turns was 7.166 µs (6.583–7.292 µs), and the owned VM's was 764.917 µs
(756.333–876.874 µs). In a separate component run, the synchronous C ABI
invoke interval accounted for 99% of the measured guest time. The raw
unsigned Wasm was 5,266 bytes. The receipt records whole-process peak
RSS and all samples. Installed tap-to-visible timing and iOS samples
remain open.
[Current D3 host replay](verification/receipts/l03-d3-taskcompletion-current-host-8fa09d66.json)

Two installed Android draft-validation releases each carried
5,450 bytes of Wasm. The replay reconstructed and hash-matched the
exact Go and Workerd offer and artifact response bodies. The two
bodies totaled 9,488–9,495 bytes, depending on release and origin.
Separately gzipping the bodies offline produced totals of
4,911–4,923 bytes. The corpus-wide compressed size measurement
remains open. [Release byte measurement](verification/receipts/l03-fieldlog-draft-validation-release-wire-a1d3cefb.json)

The development origin for the installed Android row reorder served
10,874 response-body bytes for the baseline, 15,438 for the reviewed
update, and 10,874 for rollback. Each count includes the signed offer
and the signed artifact with its base64 Wasm. Two reads per response
matched the original signed packet. The receipt records separate
offline gzip sizes and excludes headers and transport overhead.
[Signed row response sizes](verification/receipts/l03-android-signed-row-release-wire-d92cb15a.json)

The two installed Android Arabic checklist releases used 10,563 and
10,939 response-body bytes for their signed offers and artifacts.
Independent reconstruction with the stock Go wire types matched all
four recorded body hashes. Separate offline gzip totals were 5,340
and 5,509 bytes. Headers, retransmission, and APK installation are
outside these counts. The full change corpus remains open.
[Signed localization response sizes](verification/receipts/l03-android-localized-release-wire-bb6a1999.json)

On API 36, three fresh FieldLog fixture identities each accepted one
native Move up tap and appended one reorder event. The first raw crop
matching settled reordered rows reached the host 790–932 ms after the
ADB tap request, with a median of 831 ms. Pre-tap screenshot reads took
322–340 ms. The result includes capture and transport, and device
click-to-presentation latency remains unmeasured. Independent review
recomputed each bound. All 220 commands closed and the emulator and
origin were retired.
[Android row observation](verification/receipts/l03-android-installed-row-observation-fa45f636.json)

A repeat on the same signed APK measured the row action inside the
Android device. The first matching crop finished 321–373 ms after the
tap command began, with a median of 369 ms. All three moves advanced
revision 9 to 10, each added one event, and Done retired the owner.
Device-local capture and file writes are included. The ADB image reads
occurred after capture and the presentation instant was unobserved.
All 261 commands closed and all four ports were reusable.
[Device-clock row observation](verification/receipts/l03-android-device-row-observation-45135184.json)

The current TaskCompletion shell fixture passed on the API 36 ARM64
emulator. Five alternate native and owned-VM pairs matched all four
frames. Both paths refused two malformed inputs without replacing
their last frame. The guest reported `TaskCompletion.swift:94:9` and
retired. The native fault terminated by signal 5. The median three-turn
times were 3.8 µs native and 1.35 ms through the VM. Median process peaks
were 19.0 MiB and 19.7 MiB. The elected 5,266-byte payload also passed
the four frame and trap checks on macOS and has a distinct digest from
the earlier macOS run. The emulator used 4 KiB pages. The 18 ELFs passed
the separate 16 KiB alignment check. All 72 commands closed.
[Current Android TaskCompletion](verification/receipts/l03-d3-taskcompletion-current-android-fa45f636.json)

At public pin `7b61fe1cd9`, native Swift and the owned VM produced byte-identical FieldLog task frames from the same unchanged source. Both refused stale and noncanonical events without changing the frame. The deliberate precondition failed at `TaskCompletion.swift:94`. the VM identified column 9 and closed the session. Mobile parity and matched performance evidence remain open. [Task differential receipt](verification/receipts/l03-d3-task-review-event-trap-7b61fe1c.json)

A compact 1,973-byte FeatureV3 guest passed the signed macOS cold-start coordinator in fresh and retained launches. The store persisted effects intent before offering the frame. Health committed after acknowledgement for the exact launch and frame and the 10-second observation. Stale tickets left the newer launch unchanged, both owners retired, and all 11 signed Guest UI V1 tests passed. This private test used a controlled display attachment. Native rendering and the full F05 editor remain open. [Signed coordinator receipt](verification/receipts/fieldlog-f05-installed-feature-v3-host-1d3e6560.json) [Cleanup](verification/receipts/fieldlog-f05-installed-feature-v3-cleanup-1d3e6560.json)

The private F05 APK linked and installed on an owned offline API 36
arm64 emulator. Default opt-out rendered. The first opt-in attempts
failed before window readiness. The corrected window admitted Edit.
Subsequent runs corrected the installed ABI digest and all three
canonical material records, then reached the Swift verifier's
macOS-only scope check. It refused the Android development packet
before a guest frame. All five emulator and private ADB pairs closed,
their ports were reusable, and scratch and disposable keys were removed.
Native F05 Cancel, Save, cold readback, and F06 remain open.
[Android F05 startup attempts](verification/receipts/fieldlog-f05-android-api36-startup-7fa6b6ea.json)

The relinked private F05 owner accepted the exact Android development
scope. The host verifier still refused substitutions in each scope field.
On API 36, Cancel kept the workspace bytes and retired the owner. A new
process recovered the signed candidate. With one native character per
committed frame, Save wrote `Inspect pump P-17` and one matching
taskSaved event. The owner reopened the repository before retirement and
confirmed the saved record. A separate burst input lost the visible
editor after three accepted envelopes and remains open. All three
emulator pairs closed, their ports were reusable, and scratch was removed.
[Android F05 signed editor replay](verification/receipts/fieldlog-f05-android-paced-editor-api36-7fa6b6ea.json)

Two fresh burst replays kept the seed bytes and closed the active owner
before Save. The diagnostic APK kept the JNI and guest bytes and logged
the revision 3 failure at NativeRenderer.preflightEditorsV2. The
independent host control reproduced that refusal when the widget advanced
beyond the guest's echo. Burst input remains open. Both emulator and
ADB groups closed, their ports were reusable, and scratch was removed.
[Android F05 burst diagnosis](verification/receipts/fieldlog-f05-android-burst-preflight-api36-7fa6b6ea.json)

The private F05 adapter now preserves late input before the Editable
changes and replays it after the matching frame is hardware-witnessed.
The corrected API 36 APK passed the original burst, with exact title,
one taskSaved event, and joined owner retirement. Cancel preserved the
seed and a new process recovered the same signed candidate. The stock
renderer, JNI and Wasm bytes match their baselines. The host control
covered plain IME commits. The installed run covered hardware keys.
[Android F05 buffered burst replay](verification/receipts/fieldlog-f05-android-buffered-burst-api36-9d96980f.json)

The provisional F06 APK initially closed before displaying a guest frame.
The relinked private adapter selects the existing packet encoder for
vertical fields. An offline API 36 run then passed Cancel with identical
workspace bytes, cold recovery of the same candidate, and paced Save
with one task and one linked outbox event. All three disposable emulator
pairs closed and their ports were reusable. The 102,348-byte rebuilt guest
matches the historical oracle. Its Wasm digest differs from the archived
guest, so the historical-byte replay remains open.
[Android rebuilt F06 replay](verification/receipts/fieldlog-f06-android-rebuilt-editor-api36-7fa6b6ea.json)

The historical F06 producer's object output path reproduced the original
Wasm and both archived Saving variants. The exact 102,348-byte editor
passed the locked macOS oracle. The freshly sealed API 36 APK then
passed opt-out, Cancel, cold candidate recovery, and paced Save offline.
The retained journal matched both the signed manifest and the historical
Wasm digest. Cancel kept the seed bytes, and Save appended one task and
one matching outbox event. Both emulator attempts closed. The first
driver compared the two digest fields and stopped before Cancel.
[Exact historical Android F06 replay](verification/receipts/fieldlog-f06-android-exact-editor-api36-7fa6b6ea.json)

Both archived F06 Saving controls passed on signed API 36 ARM64 fixture
APKs. Native Add reached revision and input sequence 2. The absent variant
and the revision-3 presentation refusal each recorded one terminal event
and zero workspace write attempts. The first Back dismissed the keyboard.
The second retired the Android owner, and a cold process read the original
workspace bytes. Both disposable test environments closed.
[Installed F06 Saving refusals](verification/receipts/fieldlog-f06-android-saving-refusals-api36-c8a27e36.json)

The byte-exact positive F06 editor reproduced an unpaced title-input
failure on the same signed APK that passed paced Save. Cancel preserved
the seed. After restart the editor accepted text events through revision 3
and disappeared before Add. The journal retired the attempt and the
workspace stayed byte-identical. The input handoff correction remains open.
[Exact F06 unpaced input failure](verification/receipts/fieldlog-f06-android-title-burst-baseline-7fa6b6ea.json)

The private F06 title buffer passed the same burst with the historical
Wasm and JNI on API 36. The 17 text echoes reached committed revision 18.
Add saved the exact title and appended one matching task event. Cancel
preserved the seed, both owners retired, and a separate process read the
saved workspace bytes offline. Host checks cover plain IME commits.
Native composition remains open.
[Buffered F06 native replay](verification/receipts/fieldlog-f06-android-buffered-title-api36-7fa6b6ea.json)

A disposable Android IME sent two consecutive plain commits to the same
F06 APK on API 36. The IME received a multiline field with the None
action and the No Enter Action flag. Both title echoes committed. Add
saved one task and its outbox entry, and a cold process read the same
workspace bytes. The fixture restored the original keyboard and uninstalled
both APKs. Composition remains outside this replay.
[Installed F06 plain IME replay](verification/receipts/fieldlog-f06-android-plain-ime-api36-7fa6b6ea.json)

The stock Android LatinIME keyboard left the signed F06 title blank on
API 36. Tapping **P** reached the private editor, which refused the
composition and its enclosing batch before delivering an editor action.
Cancel retired the owner and preserved the workspace byte for byte.
[Stock F06 keyboard baseline](verification/receipts/fieldlog-f06-android-stock-ime-api36-7fa6b6ea.json)

The composing candidate accepted **P** from LatinIME on two fresh API 36
runs. The title echo committed at revision 2, and **Add** saved one task
and one outbox event. Both journals closed the effects attempt. The
first run lacked the installed-owner retirement marker, and the second
reported retirement unconfirmed after Activity replacement. Neither run
reached cold readback. Both disposable environments closed.
[Stock F06 composing candidate](verification/receipts/fieldlog-f06-android-latinime-save-retirement-d92cb15a.json)

The private F06 close path checks for the historical title
`Inspect pump P-17`. On the same signed APK, stock LatinIME entered that
full title with 17 committed edits. Add saved one task and one outbox
event. Activity replacement retired the Save owner, and a new offline
process read the exact saved workspace. Cancel preserved the original
workspace. The test restored the keyboard setting and removed the app
and disposable emulator. The broader composing matrix remains open.
[Full stock LatinIME replay](verification/receipts/fieldlog-f06-android-latinime-full-title-api36-d92cb15a.json)

A free owner completed current membership edits, usage and quota checks, support, export, and organization deletion in Chrome against Phoenix and PostgreSQL. One organization stayed isolated from the other. Two earlier role edits returned 503 during the member page load. Exit with settled build history remains open. [Free-owner administration](verification/receipts/l06-owner-admin-browser-e3c1f6c65c.json)

An owned API 36 emulator completed the ordinary FieldLog task conflict. After a 409 response, the user kept the local title **Inspect valve today** and the peer assignee **Morgan**. Both replicas reached version 3, each kept four prior outbox rows, and the final offline cold reopen preserved the Android workspace byte for byte. The earlier iOS replay reached the same task outcome with a separate workspace. [Android conflict receipt](verification/receipts/fieldlog-android-ordinary-task-conflict-41a05264.json)

The measured F05 guest weighs 54,739,192 bytes and requests 586 initial memory pages. ICU data accounts for 33,976,096 bytes and code for 16,569,305. Removing ICU data alone would leave the guest over the installed 4 MiB limit. The next Swift/WASI probe targets the guest runtime dependency surface. No signed limit was raised. [Size measurement](verification/receipts/fieldlog-f05-size-attribution-3607a916.json)

The public GuestUI cutoff now builds on Swift/WASI. The debug and release probes admitted startup without a cutoff and refused an unsupported cutoff before revision or effects admission. All four focused deferred-startup tests and both archive modes passed. The delivery uses the reviewed source without the local diagnostic overlay. [Cutoff verification](verification/receipts/fieldlog-guest-ui-wasi-cutoff-41a05264.json) The hosted engine workflow passed on the source commit. [Hosted CI](https://github.com/snowdamiz/mixer/actions/runs/44444528939)

A reduced byte-array JSON probe removed the Foundation archive and linked to 5,534,857 bytes and 20 initial pages. It passed 527 scalar parity cases, but the owned VM refused the oversized artifact at the unchanged 4 MiB cap. The exact F05 editor remains open. [Scalar JSON probe](verification/receipts/fieldlog-f05-scalar-87a40238.json)

An empty Swift/WASI reactor linked at 5,508,619 bytes with the pinned full-runtime toolchain. The Embedded scalar probe linked at 119,642 bytes and three initial pages and passed 22 Node WASI checks. Strict Mixer VM admission refused its random source import. The historical editor also failed Embedded type checking at its Foundation import. Independent macOS wire parity passed on the scalar patch. Android Pair 24 still pins the older source bytes. The patch remains a private experiment. [Runtime floor](verification/receipts/fieldlog-f05-embedded-1ada67c8.json) [Scalar review](verification/receipts/fieldlog-f05-scalar-independent-review-d263c67b.json)

A reduced F05 JSON probe linked to 12,651,963 bytes and 40 initial memory pages with FoundationEssentials. That cleared the memory ceiling and exceeded the 4 MiB payload ceiling. FoundationEssentials also lacked the lock used by the V1 cutoff path. The exact editor remains open. [FoundationEssentials probe](verification/receipts/fieldlog-f05-foundation-essentials-ec0b6949.json)

The F05 design keeps the existing signed recovery authority and selects one closed V3 runtime owner. The exact guest exceeds the 4 MiB installed ceiling. Work proceeds on a compact signed-host control and a separate guest-size measurement. [Design decision](verification/receipts/fieldlog-f05-signed-design-decision-41a05264.json)

The F05 host probe compiled the historical FieldLog reducer and presentation to Swift/WASI and ran them on the owned development256 VM. Current edit, stale-action rejection and cancel checks passed. Retirement reported zero current usage in all fourteen ledger counters and zero live tickets or cleanup invariant failures. The probe used a candidate WASI build fix. Installed signed selection and device runs remain open. [F05 host receipt](verification/receipts/fieldlog-f05-public-swift-5961ea0c.json)

A compact unsigned Embedded Swift editor now runs in the owned VM on
`2acaac6760`. It compiles the title reduction extracted from the two
historical editors and matches their observed state across 12 turns
each. The 86,887-byte guest has zero imports and two initial memory
pages. One longer equivalence case still exhausts the fixed fuel
budget. Independent review confirmed the source identity, projected trace,
and scope of the unsigned host proof.
[Compact editor evidence](verification/receipts/fieldlog-f05-f06-embedded-editor-2acaac67.json)

The follow-up replay saved `Inspect pump P-17` through each historical
FieldLog editor and through the unsigned guest. The host committed the
exact title from VM memory before completing Save in the guest. Each leg
made one owner call. A fresh repository instance in the same process read
the complete seed plus one revision, one task, and its linked `taskSaved`
outbox entry. Independent review matched the source and verified the
assertions, including the existing Edit and Cancel trace. Signed installation,
platform rendering, and broader parity remain open.
[Save replay](verification/receipts/fieldlog-f05-embedded-editor-save-2acaac67.json)

The signed editor candidate `eae2a13aef` passed an author-run headless macOS
replay for both FieldLog pins, including title edits, Cancel, and one durable
Save per pin. Review requested two lifecycle corrections. The presenter
needs exclusive ownership by one runtime. When a Saving frame is rejected,
the owner must complete its presentation claim before retirement. One V1
input-readiness assertion failed on the first combined run and passed on
repeat. The cause remains unresolved.

Swift Host and Android generated Java sparse preflights passed the published
155-input Source141 binding in ordinary and optimized Python. Both projections
rejected the unbound candidate at `GuestUIEditorV2.swift`. A successor must
bind the corrected source and preserve predecessor restoration. All 16
preflight command groups closed and scratch was removed.
The capability generator and all 53 Pair25 SDK and adapter file pins
matched on both revisions. Those checks covered the selected inputs and
did not compile an Android consumer.
[Source141 preflight](verification/receipts/fieldlog-signed-editor-source141-preflight-eae2a13a.json)

Independent review passed the corrected signed compact editor at
`5d07663547`. The macOS development profile uses the installed MUI1 owner
and admits text events up to the 4 KiB encoded limit. The presenter has
one owner through joined close. Rejected Saving frames complete their
claims with zero repository writes. F05 and F06 passed Edit, Cancel,
and durable Save, and the F06 uncertain commit did not replay. The
author recorded 30 combined, 27 flag-off, and three editor-only passes
with 81 command groups closed. The earlier V1 readiness failure remains
recorded. Installed mobile behavior remains open.
[Corrected author replay](verification/receipts/fieldlog-installed-compact-editor-correction-5d076635.json)

The exact composed runtime at `276d84b419` passed 61 headless macOS XCTest
executions across combined, flag-off, editor-only, and W09 selections.
Edit, Cancel, and Save matched both historical editors. The two rejected
Saving cases wrote nothing, and the post-rename case preserved one durable
write without replay. The first build stopped at the harness's file-size
limit. The successful combined run's collector missed its XCTest executable
hash. The receipt preserves the test output counts and exact VM, guest, and
source hashes. Root verified all 11 runtime Git objects in the final
composition.
[Composed signed replay](verification/receipts/fieldlog-composed-signed-editor-replay-276d84b4.json)

The reviewed Source141 successor admits all 157 inputs in both workflow
sparse projections and both Python modes. It restores the 155-input
predecessor and the 890-file Source141 and 845-file Source127 trees with
matching bytes and modes. The composed archive check passed in both modes.
[Source141 successor](verification/receipts/fieldlog-signed-editor-source141-successor.json)

Automated cybersecurity screening rejected the delegated Unicode input
verification near the 4 KiB encoded limit. That run produced no result.

The L07 terminal restart attempt used a CLI that predates the current closure acknowledgement. The worker declined shutdown, leaving compiler custody unknown. Three separate no-compiler controls passed. [Worker custody receipt](verification/receipts/l07-worker-terminal-restart-hold-41a05264.json)

A restricted Oban build reached one durable worker start. The test stopped its owned worker before compiler spawn. Restart on the same journal observed uncertainty with no second start. The owner replayed the original build, tenant B received 404, and the coordinator retained capacity after lease expiry. Post-spawn closure and artifact readback remain open. [Worker recovery receipt](verification/receipts/l07-worker-recovery-07a536f3.json)

The starter follow-up makes a verified nonzero CLI exit before Xcode a terminal failed build. Both installed-worker test modes passed 13 checks, and the hosted dispatch and lifecycle suites passed 27. Independent review verified terminal SQL settlement with an inert exit-23 CLI, including capacity release. The collector now restores the v39 predecessor before older source controls. The composed v40 selection, 12 focused collector controls and the installed archive passed in both Python modes. The hosted Phoenix and identity runs passed on the delivery commit. Actual native compilation and the hosted engine run remain open. [Composed v40 checks](verification/receipts/l05-v40-composed-validation-41a05264.json) [Pre-compiler failure receipt](verification/receipts/l05-starter-preflight-failure-66bba3c2.json)

The standalone and adopted FieldLog variants now have an opt-in local sign-in candidate. Both passed live loopback admission and Swift storage checks for scope, owner isolation, revocation and offline reopening. Both built for arm64 iOS, with no Mixer objects in the baseline. The host tests used an in-memory credential store. Independent review reproduced a revoked offline grant after a matching manual denial. The follow-up cleared only the matching grant on actual 401 and 404 responses in both host clients. Independent replay confirmed the manual-denial correction and found a delayed cold-restore denial that clears a newer credential. The follow-up compares the saved grant before acting on the restore. Both pinned hosts passed all 15 controls and both generic iOS builds passed. Independent review confirmed that this protects a different replacement grant. Independent macOS tests confirmed that the admission-ID follow-up protects identical re-sign-in from stale restore responses on both pins. A later review found that a delayed successful manual request could still re-create a grant after sign-out or replace a newer sign-in. Matching request ownership closed both cases on the two pinned clients. The delivered loopback check passed 114 cases and independent replay passed 36 additional cases, including identical and rotated credentials. Both pins passed iOS SDK typechecking. The adoption typecheck substituted the project detail screen. Full builds, installed Keychain, and the paired Simulator checks remain open. [Request ownership verification](verification/receipts/fieldlog-d0-request-ownership-0fbda7b4.json) [Independent check](verification/receipts/fieldlog-d0-request-ownership-independent-29139f7b.json) [Admission review](verification/receipts/fieldlog-d0-cold-restore-p2-independent-9b7b4836.json) [Cold-restore correction](verification/receipts/fieldlog-d0-d1-cold-restore-41a05264.json) [Revocation correction receipt](verification/receipts/fieldlog-d0-d1-local-sign-in-denial-7a6523d2.json) [Local sign-in receipt](verification/receipts/fieldlog-d0-d1-local-sign-in-5e584fba.json)

The exact pre-adoption FieldLog revision `9a69cb9` built for arm64 iOS Simulator. Its link map contained zero Mixer products. On macOS, the baseline and adopted repositories read the same workspace and JPEG byte for byte. The adopted app repository committed the offline draft under its original UUID and appended one outbox operation. Local sign-in and the paired Simulator journey remain open. [Standalone baseline receipt](verification/receipts/fieldlog-d0-standalone-9a69cb9.json)

The independent D0 and D1 review verified the public SDK iOS evidence for project creation, entry save, offline draft reopen and photo readback. The paired Simulator journey still needs installed sign-in and readback of the same workspace after adoption. [Baseline review](verification/receipts/fieldlog-d0-d1-local-review-5961ea0c.json)

A local signer stopped during the symbols download before writing an attestation. A fresh signer wrote one envelope that a separate verifier accepted. Both loopback ports and the owned group closed. In-flight worker recovery remains open. [Signer interruption receipt](verification/receipts/l07-signer-interruption-review-5961ea0c.json)

An Android-only host check served all five rebuilt signed releases and resumed the exact interrupted bytes after restart. The native attempt installed the same APKs and Activity Manager returned success. Android kept a System UI unresponsive dialog over FieldLog, ending the run before signed delivery. The owned emulator and ADB closed. A second run timed out during streamed installation. Local staging and one system Wait advanced the third run to task entry, where automated input lost characters. A replay of an earlier exact workspace stopped at preflight when both pinned APK paths were missing. [Signed Android attempt](verification/receipts/fieldlog-android-signed-system-ui-41a05264.json)

The replacement FieldLog and report-reader APKs passed signature and alignment verification and have a new development runtime identity. A fresh host delivered all five signed sequences, resumed the interrupted bytes, and rejected the wrong runtime. The first owned API 36 run installed both APKs and cold-opened that exact saved workspace. The Sharesheet stayed collapsed before signed delivery. [Replacement Android delivery](verification/receipts/fieldlog-android-restage-host-43f653e9.json)

The rebuilt Android app passed a fresh offline run on API 36. It saved a task, reopened it in a new process, and exported a 168-byte report that a separate app read byte for byte. Returning preserved the same workspace at revision 2 with both outbox rows. The emulator and private ADB closed. [Offline report receipt](verification/receipts/fieldlog-rebuilt-android-offline-report-41a05264.json)

Two direct VM replays of the rebuilt 240-byte title review exceeded the 50 ms guest deadline. They took 90.5 and 137.9 ms elapsed, used at most 0.274 ms of guest-thread CPU, and made no capability calls. Successful original and rebuilt turns consumed identical fuel. The measurements indicate an off-CPU stall. Scheduler and kernel state remain unobserved. [Host timing receipt](verification/receipts/fieldlog-signed-title-turn-timeout-diagnosis-745406d2.json)

The replacement development APK passed the archive integrity check and retained all four exact runtime notices. All five notice tests passed in both Python modes with that APK selected. [Replacement APK notices](verification/receipts/fieldlog-android-restage-runtime-notices-41a05264.json)

The exact rebuilt FieldLog APK contained all four selected Swift, NDK and ICU notices. The complete archive and both Python test modes passed five checks each. [Runtime notice receipt](verification/receipts/fieldlog-rebuilt-runtime-notices-41a05264.json)

The reviewed `85e6fbe362` Pair25 development APK also passed the
complete archive check and all five runtime notice tests in each
Python mode. The packaged Swift, two NDK, and ICU notices matched
the expected bytes. The ICU library matched the installed toolchain
and the pinned digest. Independent ICU publisher provenance remains
open. [Combined APK notice readback](verification/receipts/fieldlog-d2-combined-85e6fbe3-android-runtime-notices.json)

An instrumented iOS 27 run rendered the signed calculation baseline on the saved task and committed health. The first hydration wake took 5.031 ms elapsed and 1.697 ms thread CPU. The readback kept revision 9 and 11 outbox rows. The Simulator was removed. The external inventory matched after resuming. The earlier effects deadline remains unexplained. [iOS timing receipt](verification/receipts/fieldlog-ios-calculation-baseline-diagnostic-41a05264.json)

The shared localhost origin served sequences 1–5 to the original iOS packet and the rebuilt Android packet. All 43 host controls passed, and both interrupted 2,048-byte prefixes matched across restart. Native verification and the separate Android 240-byte title deadline remain open. [Shared-origin host replay](verification/receipts/fieldlog-rebuilt-shared-origin-host-41a05264.json)

The interrupted Android conflict Save attempt has no terminal receipt. Its last recorded stage was transport admission. The AVD, private ADB, and recorded process resources are held. [Custody record](verification/receipts/fieldlog-android-conflict-save-interruption-41a05264.json)

The free starter successor passed hosted source admission for v40 in both Python modes. Its installed worker bundle passed 11 tests per mode. Phoenix and PostgreSQL verified exact legacy replay and required a verified local package closure for new registrations. Restricted Oban dispatched one admitted start attempt. The worker returned uncertain and did not acknowledge shutdown. Compiler launch and artifact delivery remain unverified on the successor. Independent review reproduced a worker defect. A nonzero CLI exit before Xcode can persist an uncertain result despite a valid closure acknowledgement and observed process-group exit. The fix is in progress. The cause of the held dispatch remains unknown. [Starter successor receipt](verification/receipts/l05-starter-package-closure-successor-777e22f9.json)

A private local-package starter candidate reached native_succeeded after one compiler start. A free owner downloaded all three artifacts, which matched durable worker sizes and SHA-256 digests. Five invalid package inputs were refused before compilation. Billing remained disabled. Kernel egress isolation and independent source review remain open. [Free starter candidate](verification/receipts/l05-starter-package-closure-f923af86.json)

The Android combined app and report reader have new verified development APKs. The rebuilt JNI has a new runtime identity and matching signed packet. The signed macOS replay finished the 62-byte task title and hit the 50 ms VM turn limit during review of the 240-byte title. The rebuilt app still needs the joint native replay. [Rebuild and host test receipt](verification/receipts/fieldlog-combined-rebuilt-apks-41a05264.json)

The corrected iOS calculation test opened Filter inspection and the intended saved task. The app retained the exact workspace and accepted the signed 10,540-byte baseline at sequence 1. Activation recorded effects_deadline before a healthy calculation frame. The owned Simulator and release origin closed. [iOS activation observation](verification/receipts/fieldlog-ios-calculation-effects-deadline-41a05264.json)

The Android task-conflict host replay preserved all four prior outbox rows and converged on the local title and peer assignee. Four API 36 attempts stopped during offline setup, an unresponsive System UI dialog, or streamed installation. Separate push-and-install verified the same APK on disk. In that run Wi-Fi was off and LTE remained the default route. The four owned emulators and private ADB groups closed. [Android attempts](verification/receipts/fieldlog-android-task-conflict-preflight-41a05264.json)

All nine engine jobs passed at `1cbb6f9a26`. A later run on Cargo 1.100.0 moved the VM test executable and exposed a stale test-only library lookup. The privacy test now compiles the library in its own target and passes Cargo’s final output to the original 13 compiler probes. The exact test passed on Cargo 1.99.0 and 1.100.0, and all 46 optimized cache controls passed. All nine engine jobs passed on the correction commit. [Hosted CI](https://github.com/snowdamiz/mixer/actions/runs/44430570539) · [VM CI receipt](verification/receipts/vm-external-privacy-cargo-layout-e990792f53.json)

The first iOS calculation test installed the intended app and preserved the exact 3,530-byte saved workspace. FieldLog opened Upcoming inspection, while XCTest expected Filter inspection. The test stopped before guest launch. The release origin closed and the owned Simulator was removed. A new test selects the intended project through the ordinary screen. [Simulator receipt](verification/receipts/fieldlog-ios-calculation-project-route-41a05264.json)

A free project owner submitted the selected iOS starter. Real Phoenix and restricted Oban dispatched the same source, recipe and lock recorded in PostgreSQL to the worker. SwiftPM identified a remote Swift Crypto dependency in the local-only recipe. A test guard refused launch, and the worker recorded zero compiler starts. Owner cancellation released capacity, SQLite reopened the stopped record, and billing rows stayed unchanged. Local package admission and compilation remain open. [Worker dispatch receipt](verification/receipts/free-starter-dispatch-to-worker-41a05264.json)

A fresh localhost run served both signed FieldLog packets in one journey. Both downloads stopped at 2,048 bytes, matched the 2,112-byte saved partials from the earlier native runs, and replayed the same bytes after the service restarted. Both service generations closed and all three ports were reusable. The combined native replay needs a rebuilt Android app APK and report-reader APK. [Shared-origin host receipt](verification/receipts/fieldlog-clock-shared-origin-host-41a05264.json)

The Swift CI repair updates the capability fingerprint for the installed hydration source and splits a fixture expression that Swift CI could not compile. The capability host suite passed 52 tests. The bridge passed 58 tests each in debug, release, and Thread Sanitizer after one debug wake deadline. Both sparse-checkout modes passed 16 checks on the combined Android and Swift changes. Hosted Swift CI is pending. [Swift CI repair](verification/receipts/swift-capability-ci-repair-41a05264.json)

A hosted Android job exceeded its two-minute bootstrap limit after both test suites printed OK. The same checks now have four minutes. All 90 bootstrap checks and 32 sparse-checkout checks passed on the local CI projection. Normal and optimized Python admitted the same 150 inputs after the workflow change. Hosted qualification is pending. [CI repair evidence](verification/receipts/android-bootstrap-ci-budget-41a05264.json)

On iOS 27, ordinary FieldLog completed all 16 signed-checklist checkpoints through sequence 5. One wake timed out after the task edit had committed (50.130 ms elapsed, 0.488 ms thread CPU). FieldLog showed the saved Completed status and reopened it once without duplicating the edit. During the service outage, a cold launch preserved the saved task and the same 2,112-byte partial download. Reconnect replayed 2,048 bytes of the prefix, completed the download, and preserved the task. Final rollback passed. Both mobile apps still need their joint native run against one origin. [Simulator evidence](verification/receipts/fieldlog-ios-signed-checklist-complete-41a05264.json)

The optimized macOS VM passed all 44 capability guest, mailbox and public FFI tests. The replay closed a timed-out guest turn, discarded work from a trapping turn, and released pending native delivery only after its lease conditions were met. Simulator and emulator timing remain outside this host test. [VM test receipt](verification/receipts/vm-capability-turn-controls-41a05264.json)

The iOS Simulator links the optimized Rust VM. A fresh release build reproduced the linked archive byte for byte. On macOS the same signed guest’s first turn took 7.7 µs median across 15 fresh processes. A controlled 60 ms pause reproduced the rollback fault at the same instruction. Measuring wall and thread CPU time on the Simulator remains necessary to attribute its delay. [Build and timing receipt](verification/receipts/fieldlog-ios-startup-optimization-5581cdbb.json)

The ordinary iOS app completed the signed baseline and reviewed confirmation flow on one saved task. On rollback, the 50 ms VM startup turn expired before a frame or effects intent, with 4.58 seconds left on the signed startup deadline. The committed revision-5 workspace matched the confirmed edit byte for byte. Cold reopen and reconnect remain pending for this journey. [Simulator receipt](verification/receipts/fieldlog-ios-rollback-startup-runtime-41a05264.json)

Concurrent browser requests to register the first application now acquire PostgreSQL identity locks in the same order. The full Phoenix suite passed 931 tests in 389.3 seconds on macOS. Two Linux network-namespace tests were skipped. [Qualification receipt](verification/receipts/phoenix-foundation-qualified-41a05264.json)

The Apple SDK now lets an editor accept consecutive callbacks from the same text binding after it installs each exact value. Public FieldLog saved and reopened **Night shift** in the macOS replay, and both native field identifiers remained accessible. The SDK suite passed 228 tests and the FieldLog host suite passed 44. [Regression and consumer patch](tests/integration/fieldlog-apple-section-accessibility/README.md#consecutive-edits-in-the-same-text-field) · [Verification](verification/receipts/fieldlog-current-sdk-typing-41a05264.json)

On the corrected iOS 27 build, the ordinary task editor showed **Night shift** before Add and saved it exactly, with one task-save event. The signed baseline was fetched and accepted at sequence 1, then recorded a deadline before first-screen health. The release service and owned Simulator closed. [Candidate runtime](verification/receipts/fieldlog-ios-assignee-candidate-runtime-41a05264.json)

For a project with one of three tasks complete, the signed FieldLog calculation changed from **0%** to **33%** on the macOS host. Signed rollback restored the earlier result, and the offline workspace stayed byte-identical. One root replay missed the baseline first frame. The next run passed with the same deadlines. Both mobile runs remain open. [Calculation replay](tests/integration/fieldlog-task-calculation/README.md) · [Host receipt](verification/receipts/fieldlog-task-calculation-source-41a05264.json)

Both iOS 27 conflict tests passed. After an offline edit and a conflicting peer save, the ordinary editor reopened the merged task with the local title and peer assignee. SQLite held exactly two task events, and all seven prior outbox rows survived. [Native evidence](verification/receipts/fieldlog-ios-ordinary-task-conflict-41a05264.json) · [Replay from source](tests/integration/fieldlog-task-sync/README.md#ordinary-ios-task-editor)

On iOS 27, the ordinary checklist test typed **Night shift** and the saved task contained **Night shif**. It fetched the signed baseline and stopped at the exact assignee check before exercising the update. The Simulator and release service closed cleanly. [Saved task and XCTest result](verification/receipts/fieldlog-ios-checklist-assignee-readback-41a05264.json)

The iOS 27 conflict replay reached the saved task on the project screen. The restored Field note sheet covered the task menu. XCTest found the underlying button but could not tap it. That attempt ended before an edit. The owned Simulator was removed. [Native conflict test](verification/receipts/fieldlog-ios-conflict-menu-41a05264.json)

In the combined Android development APK, FieldLog returned from sharing a 168-byte populated report with an offline recipient. The signed phase stopped at the reverse-mapping check before opening the guest. The emulator exited with code 0, but cleanup could not confirm group 16950 had gone. Its instance and ports are held. [Combined replay and custody](verification/receipts/fieldlog-android-combined-report-and-custody-41a05264.json).

On a fresh API 36 emulator the combined app shared the exact 168-byte report, returned to the saved workspace, and opened signed sequence 1. The checklist displayed **Open** and an enabled **Complete task**, but omitted the saved task title. The replay stopped before a guest tap or photo import. The disposable AVD was removed and all five ports were reusable. [Combined runtime receipt](verification/receipts/fieldlog-combined-checklist-title-api36-41a05264.json)

A free project owner selected a verified iOS starter from the build console. After reload, Chrome showed the same input and source digest, and PostgreSQL held one input. The worker verified the selected source without starting a build. Dispatch and compilation from this owner session remain open. [Selection receipt](verification/receipts/free-project-starter-selection-v38-41a05264.json) · [Local replay](tests/integration/free-project-starter/README.md)

Both FieldLog recipes replayed from pinned public sources. The iOS 27 Simulator passed four tests across an in-place upgrade and cold reopen. On macOS, the Android consumer resumed the queued JPEG after cancel and owner close and reconciled a lost acknowledgment without sending more chunks. The unsigned arm64 APK cross-build passed. [Installed upgrade](verification/receipts/fieldlog-ios-installed-upgrade-public-replay-41a05264.json) · [Android queue](verification/receipts/fieldlog-android-queue-public-replay-41a05264.json)

At 180 dpi on API 36 the system status bar covered the signed task-reorder fixture’s baseline button. Two taps left the app at Ready. The default-density run stopped before a baseline tap, and its emulator and private ADB remain held. Neither attempt verified reorder. [Native observation](verification/receipts/fieldlog-android-signed-row-insets-41a05264.json)

The inset-aware Android fixture passed the signed row move on API 36.
Sequence 1 displayed the original order. One **Move up** tap on sequence
2 moved **File report** ahead of **Valve “北”**, advanced revision 9 to
10, and appended one `taskOrderChanged` event. Signed rollback and an
offline launch in a new process preserved the reordered workspace and
open draft byte for byte. **Done** retired both sequence 3 launches. The
private APK carries four historical notices. Installed iOS remains open.
[Signed Android row move](verification/receipts/fieldlog-android-signed-row-api36-d92cb15a.json)

The resealed Android row fixture with all 12 Pair25 notices passed the
same API 36 journey. One native move advanced revision 9 to 10 and
appended exactly one event. Signed rollback and a fresh offline process
kept the exact reordered workspace and open draft. All 43 APK payloads
matched the sealed staging inventory, including 19 ARM64 libraries.
Independent unsigned review passed 27 refusal controls. The fixture had
zero attachments. Exact SDK BoringSSL build and linked unwind archive
provenance remain open. All 146 installed commands closed, the emulator
was removed, and the four owned ports were reusable.
[Signed row with 12 notices](verification/receipts/fieldlog-android-signed-row-twelve-notices-api36-d92cb15a.json)

Independent replay verified the signed row releases with stock
mixer-update verify-v3 and matched the three candidates to the four
installed launches. The row fixture recorded first-screen health
through its draw callback. The retained packet has no exact compositor
frame for those launches, and the raw recovery journals were removed.
Ordinary Entry Commit has separate hardware frame evidence. L04, L07
and L08 remain open.
[Signed row activation trace](verification/receipts/l07-android-row-activation-positive-trace-12616bb2.json)

A fresh development seal bound the hardware-frame and PixelCopy
witness to the row fixture. The stock verifier passed all three
signed assignments. The API 36 run recorded both durable milestones
for four launches. Independent review matched display witness pairs
to baseline, pre-move, and offline. The pair initially attributed
to warm rollback occurred before that launch. Its journal, hierarchy,
and retirement passed readback. One Move up tap advanced revision 9 to
10 and appended one event. Rollback and a new offline process preserved
the reordered workspace. All 160 commands closed. Installed iOS remains
open.
[Installed row hardware-frame witness](verification/receipts/l07-android-row-hardware-frame-api36-6dda69d9.json)

A second run with the same APK saved the raw epoch logs, live journals,
hierarchies and workspace snapshots. Readback matched one successful
display witness pair inside each launch window, including warm rollback.
Independent review matched all 20 captures and replayed the journals.
The parser needed to accept logcat's leading spaces. The raw workspace
shows one new reorder event and exact continuity through rollback and
offline reopen. All 172 commands closed. The trace and journal still
lack a common attachment ID.
[Row witness launch windows](verification/receipts/l07-android-row-witness-launch-windows-613fb3c1.json)

On Android API 36, the ordinary FieldLog app cold-restored an uncommitted photo draft, saved it, and resumed the JPEG transfer at 65,536 bytes after cancellation. When the backend withheld the final receipt, retry reconciled the original event without sending another chunk. SQLite held one event and one matching 281,378-byte JPEG. The two unrelated outbox events survived cold reopen. [Runtime and readback](verification/receipts/fieldlog-android-ordinary-queue-runtime-41a05264.json)

Ordinary FieldLog passed an installed upgrade from 0.1.0 (1) to 0.1.1 (2) on iOS 27 Simulator. The same photo draft, JPEG and two pending events survived replacement. Saving in the new build preserved the draft ID as the entry ID and appended one event. Cold reopen preserved the exact saved bytes. Four XTests passed. [Installed iOS upgrade](verification/receipts/fieldlog-ios-installed-upgrade-runtime-41a05264.json)

The Apple renderer puts a titled section’s accessibility identifier on its native heading. FieldLog’s macOS form exposed one section heading and separate title and assignee controls. Headerless sections retained their existing hierarchy. On iOS 27 Simulator, XCTest selected both fields by their IDs, entered the title and assignee, and saved the task. [Simulator result](verification/receipts/apple-fieldlog-task-accessibility-ios27-41a05264.json) [Host evidence](verification/receipts/apple-integrated-section-accessibility-root-cjmN9HqN.json) · [FieldLog test](tests/integration/fieldlog-apple-section-accessibility/README.md)

The ordinary iOS checklist opened from the visible task title. The signed baseline completed the task, and the update reopened that same task and showed **Review required** without changing the workspace. After **Confirm completion**, the sheet stayed open but its guest controls disappeared. A second run stopped one action earlier. Its installed recovery record reported `effects_deadline`, retained healthy sequence 2, and the task remained open at revision 4 with four outbox events. [iOS native receipt](verification/receipts/fieldlog-ios-ordinary-signed-confirmation-41a05264.json)

On iOS 27, tapping the saved task left the ordinary project screen visible until the signed-release check timed out. In the upgrade test, Files exposed the FieldLog folder but XCTest could not tap it. Both Simulators were retired. The shared origin passed its host interruption and restart checks for both packets. Android cold reopening before photo commit remains unverified after emulator cleanup returned an unresolved group. [iOS observations](verification/receipts/fieldlog-ios-checklist-and-upgrade-observations-41a05264.json) · [Shared origin](verification/receipts/fieldlog-shared-origin-host-41a05264.json) · [Android custody](verification/receipts/fieldlog-android-uncommitted-cold-draft-hold-41a05264.json)

The corrected combined Android app showed the saved task title through signed sequences 1–5, offline reopen and download completion. The same install imported a photo, saved the draft as an entry at revision 9 and cold-reopened the exact workspace and JPEG with eight outbox entries. The independent recipient read the same 168-byte report. On iOS the versioned upgrade stopped at the Files picker before replacement. [Android runtime](verification/receipts/fieldlog-android-combined-signed-task-photo-41a05264.json) · [iOS upgrade attempt](verification/receipts/fieldlog-ios-installed-upgrade-files-picker-41a05264.json)

FieldLog opened the saved task from Android’s notification shade while offline, both in the existing process and from a cold start. Back restored the unsaved task title in the warm case. Missing and foreign targets were refused, and the workspace and its two outbox rows stayed byte-identical. The fixture used a local notification adapter. [API 36 assignment replay](verification/receipts/fieldlog-android-assignment-notification-runtime-41a05264.json).

The iOS assignment-routing candidate resolved a saved task by workspace, project and task IDs in macOS tests. Returning to the editor preserved its unsaved title. Debug and Release built for generic iOS. On iOS 27 Simulator, the owner created a task assigned to Rae, opened it from the SpringBoard local notification, verified its title and open status, and returned to the checklist. The workspace retained exactly two outbox events. [Simulator XCTest](verification/receipts/fieldlog-ios-assignment-runtime-41a05264.json) [Host and build receipt](verification/receipts/fieldlog-ios-assignment-notification-41a05264.json)

On macOS, FieldLog reopened a pending task conflict and let the user keep their own title and the other editor’s assignee. Repeating Save or Resolve preserved the earlier outbox records. The host delivered the peer’s saved values directly. Authenticated delivery and mobile interaction remain open. [Saved-task conflict replay](verification/receipts/fieldlog-task-conflict-host-41a05264.json)

Two offline FieldLog replicas subsequently synchronized competing saved task edits with the localhost backend. Retrying after a lost acknowledgement preserved the newer edit and seven unrelated outbox events. The generated Android entry point separately resumed a queued JPEG at 65,536 confirmed bytes in a macOS host replay. Android queue networking and both mobile conflict screens remain open. [Conflict replay](verification/receipts/fieldlog-offline-task-sync-41a05264.json) · [Android queue evidence](verification/receipts/fieldlog-android-queue-send-host-41a05264.json)

The public CLI halted a local signed rollout after an operator supplied an adverse health sample. The file store and PostgreSQL stopped new offers to all three tested cohorts. Restoring the sequence-5 database backup after the source advanced to sequence 6 reproduced the halt receipt and audit. A fresh signed promotion from the restored database delivered the same assignment, manifest and payload. [Operator guide](docs/local-update-release.md) · [Local restoration evidence](verification/receipts/public-cli-halt-restore-41a05264.json).

A real VM trap supplied the adverse signal for a second CLI replay on macOS. The sequence-3 halt survived restart, and both installation stores remained byte-identical across the halt. Offline, the healthy installation reopened and the 8-byte partial download remained ineligible. The host supplied the UI milestones. [Installed recovery replay](verification/receipts/public-cli-installed-halt-41a05264.json)

In the ordinary console, **View build logs** displayed the compiler phases, exit codes and output sizes for the selected failed iOS attempt. Switching builds cleared those events. The browser used seeded terminal records and an authenticated Phoenix session. Chrome group closure remains unconfirmed. [Browser receipt](verification/receipts/l05-console-terminal-build-log-view-41a05264.json) · [Source admission](verification/receipts/l05-console-build-logs-v36-41a05264.json).

On macOS, FieldLog kept a saved entry queued after its local backend committed the event and JPEG but the acknowledgement was cut short. Reopening and retrying left one remote event and one byte-identical 341,976-byte JPEG. The fixture used a provisioned account token. Mobile UI and signed guest capability integration remain open. [Offline entry sync](verification/receipts/fieldlog-local-entry-sync-41a05264.json). The [replay guide](tests/integration/fieldlog-entry-sync/README.md) uses the maintained FieldLog commit and both downstream patches. A clean host replay passed all 13 repository tests and the interrupted transfer. [Replay receipt](verification/receipts/fieldlog-entry-sync-public-replay-41a05264.json).

The macOS transfer replay resumed a saved JPEG from 65,536 acknowledged bytes after cancellation and reconciled a lost final receipt. SQLite contained one event, one matching photo, and zero staged uploads. In a separate SwiftUI host replay, retrying from FieldLog’s **On device** queue preserved six unrelated events. Both iOS configurations built for a generic device. In a subsequent macOS SwiftUI run, the queue displayed 32,768 confirmed bytes, cancelled the selected send, and resumed it at 65,536 bytes. Both interruption cases preserved seven unrelated rows. That private composition used the earlier resumable backend. Native Simulator execution remains open. [UI progress and cancel](verification/receipts/fieldlog-ios-queue-photo-resume-41a05264.json). A fresh run of the checked-in replay also verified that resending identical chunk bytes returns the persisted receipt. [Public replay](verification/receipts/fieldlog-photo-resume-public-replay-41a05264.json) · [Resumable transfer](verification/receipts/fieldlog-photo-resume-host-41a05264.json) · [Queue replay](verification/receipts/fieldlog-ios-entry-sync-queue-41a05264.json).

The SwiftUI queue also passed both cancellation timings against the committed resumable backend. A late duplicate returned the original chunk receipt without changing SQLite. Each run finalized one exact JPEG and preserved seven unrelated outbox rows. [Reproduce the queue journey](tests/integration/fieldlog-ios-queue/README.md) · [Host receipt](verification/receipts/fieldlog-ios-current-resume-41a05264.json)

On iOS 27.0 Simulator, the **On device** queue showed 32,768 confirmed JPEG bytes, paused on Cancel, and resumed against 65,536 bytes already staged on the server. The receipt removed exactly one queue event. App-container readback and SQLite confirmed one exact 341,976-byte JPEG and seven unrelated events preserved. Both disposable Simulators were removed. [Simulator and disk evidence](verification/receipts/fieldlog-ios-queue-native-41a05264.json)

On macOS, one press on the signed Move up button moved File report from third to second. FieldLog advanced revision 8 to 9 and appended one task-order event. Rollback and offline cold reopen preserved that order and the open draft. The tested guest uses stacked rows. Both mobile executions remain open. [Task reorder evidence](verification/receipts/fieldlog-signed-row-reorder-host-41a05264.json).

A fresh Android API 36 emulator installed the source-built reorder APK once. In gesture navigation, one signed Move up tap moved File report ahead of Valve, advanced revision 9 to 10, and appended one task-order event. Signed rollback and a new offline process preserved the moved workspace and the open draft. The launch button overlapped the system navigation bar in the initial three-button mode. The initial tap reached the Android launcher and made no update request. The emulator, private ADB, and origin closed, all four ports rebound, and the AVD was removed. [Installed Android reorder](verification/receipts/fieldlog-task-reorder-android-native-71e6ffa5.json)

The corrected Activity moved the launch button up by the 72 px three-button inset. A fresh API 36 emulator accepted one install, one signed Move up action, and both launcher taps above the navigation bar. Signed rollback and cold offline reopen preserved the reordered workspace and saved draft. The new origin, private ADB, and emulator closed, and all four ports could be rebound. iOS remains pending. [Three-button Android replay](verification/receipts/fieldlog-task-reorder-nav-inset-native-20261120.json)

A signed FieldLog update on the macOS host changed the Arabic checklist labels. The title and status aligned on the right in RTL and on the left in LTR. The title style change increased its measured height from 16 to 26 points. Changing the macOS accessibility size alone produced no measured growth in either the guest or the native controls. On Android API 36 the signed baseline rendered the complete Arabic title, including 07, at 2× system font scale in RTL. One run displayed a failure while disk already recorded both health milestones for the active launch. A fresh API 36 run verified both healthy releases, fallback after an unsupported asset map, and the updated Arabic title, status and action at 2× RTL. The 1× direction comparison and durable localized tap remain open. The third attempt left its UI dump, private ADB and emulator under a custody hold. [Runtime and cleanup](verification/receipts/fieldlog-android-localized-late-health-41a05264.json). [Android runtime evidence](verification/receipts/fieldlog-android-localized-runtime-41a05264.json). [Localized guest evidence](verification/receipts/fieldlog-localized-guest-host-41a05264.json).

A signed C guest replayed the historical FieldLog task editor on the macOS VM. Save persisted Unicode input and one outbox event. Cancel preserved the workspace. Compiling that editor from Swift and mounting it through the installed mobile owner remain open. [Historical editor replay](verification/receipts/fieldlog-f05-signed-editor-host-41a05264.json).

The exported Android starter packages the Swift SDK, two NDK notices and the Apple ICU 76.1 license for the bundled Foundation ICU library. Full-APK checks verified all four files and rejected a missing, altered or extra notice. Independent publisher attestation for the ICU binary remains open. The SDK also exports the public guest draw and tap callback. [APK and source checks](verification/receipts/android-starter-icu-source150-41a05264.json) · [SDK integration](verification/receipts/android-sdk-public-witness-and-runtime-notices-41a05264.json).

The local v3 origin served distinct signed FieldLog releases to the old and new iOS runtime fingerprints for one installation ID. After restart, each still received its original offer. The host verifier used retained descriptors and a fresh cursor to model the upgrade. [Runtime cohort offers](verification/receipts/fieldlog-runtime-cohort-offers-41a05264.json).

With the local v3 origin running on API 36, the digest-verified public APK opened its launcher and displayed only “Open signed checklist.” The ordinary task form never appeared. The UID log captured no messages. The run removed the reverse mapping and emulator and closed both listeners. [Public checklist startup](verification/receipts/fieldlog-android-public-checklist-startup-41a05264.json).

The ordinary Android FieldLog launcher recovered when the missing appearance descriptor was packaged. One API 36 installation then saved a task, ran signed sequences 1–5, reopened the same rollback candidate cold with the local service stopped, and resumed the interrupted download. After Done, the ordinary screen showed zero completed tasks and six pending changes. The last workspace read before Done showed one completed task at revision 7 with seven outbox entries. The final UI check failed and infrastructure cleanup passed. [Android checklist replay](verification/receipts/fieldlog-public-checklist-appearance-runtime-41a05264.json).

The corrected ordinary Android FieldLog app completed all five signed release steps on API 36. It retained the saved task and the interrupted download across a cold start with both listeners stopped. After reconnect and rollback, Done returned to the ordinary screen with one completed task and seven pending changes. Reading revision 7 before and after Done yielded identical workspace bytes. [Signed checklist return](verification/receipts/fieldlog-ordinary-android-signed-checklist-return-41a05264.json). Independent review matched both corrected APKs to their separate device runs. The earlier failing checklist receipt has an inconsistent Activity source hash. Its rebuilt DEX matches the failing APK. [Android return review](verification/receipts/fieldlog-android-return-independent-review-41a05264.json).

On API 36 the offline run reached FieldLog’s launcher and showed only the signed-checklist button. A separate Pair23 run showed an Android system dialog, and the next cold boot timed out. The offline queue and report checks remain open. The Android 0.1.0 and 0.1.1 upgrade APKs passed host package and signer checks. On API 36 an in-place upgrade from build 1 to build 2 preserved the saved task, photo draft, workspace file and JPEG bytes. The upgraded app committed that draft, appended one entrySaved event and reopened it after a cold launch. [Installed upgrade](verification/receipts/fieldlog-android-installed-upgrade-runtime-41a05264.json). [Offline attempts](verification/receipts/fieldlog-android-offline-queue-report-41a05264.json) · [Upgrade preparation](verification/receipts/fieldlog-android-in-place-upgrade-prep-41a05264.json).

On a fresh API 36 emulator, FieldLog saved a task in airplane mode. After force-stop, the new process displayed both pending changes and Android opened the share sheet for the byte-verified project report. On return, five FieldLog hierarchies contained no visible labels. The final workspace comparison remains pending. [Offline report and return failure](verification/receipts/fieldlog-ordinary-android-offline-report-41a05264.json). A separate recipient then read the same 165 bytes through Android’s granted content URI with no active network. The workspace stayed byte-identical through delivery. On Back, the current FieldLog process reported an incomplete frame install and showed a blank screen. [Recipient transfer](verification/receipts/fieldlog-offline-populated-report-transfer-41a05264.json).

The corrected FieldLog Activity waits for its chooser result, resume, and window focus before delivering the close event. On API 36, the recipient read the exact 165-byte report and Back restored the ordinary task screen. The workspace matched byte for byte before sharing and after return. [Fixed report return](verification/receipts/fieldlog-android-offline-report-return-41a05264.json).

The release inspector’s first dual-target result reused an Android observation for iOS. A corrected host replay compiled the iOS guest, observed the confirmation under the Apple contract, and rejected swapped observations. An Android camera permission change required a store build. [Inspection review and correction](verification/receipts/l04-source-derived-inspector-review-41a05264.json). The integrated CLI passed 15 inspection controls and 53 public update observations. Installed verification covered all 150 source files. [Integrated release inspector](verification/receipts/l04-release-inspector-source150-41a05264.json). The [recipe](cli/release-tools/README.md) builds the qualification from supplied app, source and host-probe inputs. The reviewed implementation passed 17 inspector controls, including the historical tool inventory. [Recipe review](verification/receipts/fieldlog-release-inspection-recipe-review-41a05264.json). A clean build of the recipe commit reproduced all 17 controls and both retained sequence-2 offers after origin restart. [Pinned replay](verification/receipts/fieldlog-release-inspection-clean-pin-41a05264.json).

The local CLI can publish, promote and roll back signed v3 updates. After the origin committed a publish and the relay returned a 503, retry recovered the original receipt without adding an audit event. [Operator commands](docs/local-update-release.md) · [Loopback replay](verification/receipts/public-update-cli-20261118.json). A PostgreSQL replay verified the offered bytes, the 5%, 25% and 100% rollout transitions, and the sequence-4 rollback. Retrying after an origin restart returned the original receipts and left the eight rows in each audit, outbox and idempotency table unchanged. [PostgreSQL operator replay](verification/receipts/l05-public-update-postgres-41a05264.json).

The v3 release audit records the previous and new assignment sequence, artifact digest and rollout percentage. The PostgreSQL replay verified five channel changes through rollback, with no duplicate event on retry. Both storage backends now serve a verifiable chain in the original shape to strict v1/v2 readers and the stored chain to v3 readers. PostgreSQL pages event IDs in numeric order. Deep-page performance remains unmeasured. [Legacy reader and restore tests](verification/receipts/release-audit-legacy-reader-compatibility-41a05264.json). [Release audit](verification/receipts/release-v3-channel-audit-20261118.json).

The FieldLog history replay covers 20 behaviors from six commits. Seventeen behaviors are candidates for OTA. Fifteen of those have passing host controls, including the standalone F02 row-move replay. Zero have verified signed delivery on both targets. The development apps now build with signed checklists reachable from their usual entry points. Android still needs the trial build flag for its native display callback. [Corpus](compiler/experiments/fieldlog-change-corpus/README.md) · [App builds](verification/receipts/fieldlog-supported-entrypoint-build-41a05264.json).

An authorized client can retrieve terminal build events after worker shutdown. In the local store fixture, iOS and Android each recovered one accepted submission after a lost acknowledgement. The hosted manifest covers 391 source inputs and the native manifest covers 143. [L05 integration](verification/receipts/l05-build-logs-store-integration-41a05264.json).

On API 36 the ordinary FieldLog app saved all 132 characters from one IME commit after composition, followed immediately by blur and Save. A cold relaunch preserved the note, its linked JPEG and one matching outbox event. A second run passed at 180 dpi on the original display dimensions. An earlier run at that density lost the form after photo selection. [Android input and persistence](verification/receipts/fieldlog-android-ime-compose-paste-cold-41a05264.json).

The opt-in workspace-builds profile is now integrated with hosted v35. The combined console build and 278 tests passed. An earlier live browser run let one free owner create a project, submit a build and cancel it while queued. This run seeded the application and source input. The full owner registration, worker, support and exit journey remains open. [Browser workflow](verification/receipts/l06-free-owner-queued-build-41a05264.json) · [Integration](verification/receipts/l06-combined-workspace-builds-v35-41a05264.json).

In the application-registration candidate, a free owner registered the first application in an empty project through the console and saw it after reload. An identical request returned the same receipt, and a viewer was denied. Source-input selection and source admission remain open. [Browser and database evidence](verification/receipts/free-project-first-application-41a05264.json)

The integrated console offers registration after loading an empty application list. PostgreSQL accepted one owner registration under competing requests and preserved workspace data through migration rollback and reapply. The 291 console tests passed. Hosted v37 admitted all 398 sources and 20 migrations. Both broad collector runs timed out after 289 passing cases. Selecting the first source input remains open. [Integration receipt](verification/receipts/free-project-application-registration-v37-41a05264.json)

On macOS the installed signed FieldLog guest rejected a whitespace-only draft title after update, then preserved the draft, optional follow-up flag, JPEG and outbox across rollback. Mobile form delivery remains open. [Draft validation and schema rollback](verification/receipts/fieldlog-draft-validation-optional-rollback-41a05264.json).

The downstream FieldLog patch adds **Check saved draft** to the ordinary iOS entry editor. The workspace-model action and installed signed host both read the selected draft through the same repository actor. The macOS replay preserved the JPEG and outbox through validation, the optional-field edit, signed rollback and cold reopen. The iPhoneOS typecheck passed. Signed mobile attachment and taps remain open. [Host receipt](verification/receipts/fieldlog-check-saved-draft-host-41a05264.json) · [Patch and replay](tests/integration/fieldlog-saved-draft/README.md).

On API 36 a first signed FieldLog release survived force-stop after staging and before its first guest launch. After shutdown of both service listeners, the new process rendered the saved completed task on its first frame. Workspace and outbox bytes matched throughout. This run used the development Activity on the corrected core. [Cold first release](verification/receipts/fieldlog-android-first-release-staged-offline-41a05264.json).

The hosted API now recovers the same browser session after a refused pool checkout before BEGIN. An ambiguous database transaction still closes access. The 15 PostgreSQL tests passed. Source admission passed for all 389 hosted inputs and the 141 native inputs in both Python modes. [Session recovery](verification/receipts/l07-recovery-v33-41a05264.json).

On the combined build tree, a free authenticated client downloaded the app, symbols and inventory after worker shutdown. A separate signer verified the attestation. In a second build, cancellation returned 202 while Xcode was running and released capacity once the worker confirmed termination. The local store CLI candidate reconciled a lost acknowledgement on both platforms with one durable submission each. [Native build](verification/receipts/l05-combined-native-build-41a05264.json) · [Store fixtures](verification/receipts/l05-local-submission-reconciliation-41a05264.json).

Chrome verified free workspace administration with the preliminary session recovery fix. The workspace profile refused build submission and cancellation. L06 remains open for a free owner to manage the workspace and use its build services. [Browser evidence](verification/receipts/l06-combined-console-browser-793196991d.json).

L04 review requires signed delivery through the supported FieldLog entry points and a CLI check that distinguishes an eligible task edit from a change requiring a native binary. The mobile fixture runs and host checks remain scoped evidence. [Independent decision](verification/receipts/l04-independent-review-9fd7e7f6eb-41a05264.json).

On API 36, FieldLog’s development fixture installed once, read the saved task before each signed guest’s first frame, and preserved its workspace through Activity recreation, rollback and process-cold offline reopen. Reconnecting resumed the 258-byte partial download. The final confirmed change persisted revision 5 and eight outbox records. The disposable AVD was removed and all owned groups closed. [Android runtime](verification/receipts/fieldlog-android-hydrated-signed-runtime-41a05264.json).

Five paired macOS runs matched native and guest results across three persisted tasks. Each implementation processed 60 actions, including 45 commits. Two earlier guest runs stopped before parity, once after input and once at the hydration deadline. Mobile performance and reliability remain open. [Matched workload](verification/receipts/fieldlog-matched-persisted-host-41a05264.json).

The installed guest runtime now supports reading saved state before its first frame, after durable effect authorization. The reviewed implementation passed host checks for grant denial, startup deadline, quota forwarding and prior ABI behavior. The earlier iOS runtime receipt used the original overlay. [Implementation and review](verification/receipts/fieldlog-public-first-frame-hydration-41a05264.json).

Local commit `793196991d` integrates free workspace administration, support, organization exit and native build cancellation. All 278 console tests and 88 PostgreSQL-backed build tests passed on the combined source. The authenticated exit fixture retained a settled build and found zero payment credentials. The combined browser journey and cancellation during a live compile still need runtime verification. [Integration receipt](verification/receipts/l06-combined-admin-support-cancel-41a05264.json).

The ordinary iOS in-place upgrade test stopped during system photo import before its first XCTest. The disposable Simulator and import process remain under hold. Installation of the replacement build is pending. [Upgrade attempt](verification/receipts/fieldlog-installed-upgrade-import-hold-41a05264.json).

**L01 passed for the documented local setup, adoption and export workflow.** The review verified independent exports and native starter runs on both platforms, the import report, and public SDK use by the separate FieldLog app. L02–L08 remain open. [L01 decision](verification/receipts/l01-independent-final-review-41a05264.json).

Both VM validators now accept the valid unreachable-code branch table identified by the WebAssembly standards suite. The root replay passed 71 focused tests. [VM review](verification/receipts/l03-standards-review-41a05264-DK7nuyvA.json).

With the local release service and forwarder stopped, a fresh macOS process reopened FieldLog’s signed rollback at workspace revision 4 with seven outbox records. The workspace bytes and pending 258-byte download survived. After the service restarted against its original store, a third process resumed the reviewed release and committed revision 5 with eight records. [Release outage replay](verification/receipts/fieldlog-release-service-outage-41a05264.json).

The independently reviewed v3 halt stopped new offers across a service restart. The macOS installed host reopened a committed release offline after key expiry and accepted the replacement key on reconnect. The reviewer’s additional Go run stopped before producing a result and left a process group under hold. [Halt and rotation review](verification/receipts/release-v3-rotation-halt-review-41a05264.json).

The relocated iOS starter built with the documented Pair24 pin and SDK dependency lock. On iOS 26.5 Simulator its title and initial progress appeared on launch and after termination and relaunch. Installed executable and debug library hashes matched the export. [Pinned iOS runtime](verification/receipts/l01-public-pin-ios-runtime-41a05264.json).

On iOS 27.0 Simulator the installed FieldLog guest rendered the saved task on its first frame after a signed update, rollback, and relaunch without a delivery URL. Disk readback matched revision 6 and seven outbox records. Correcting the missing final newline in the fixture’s storage grant preserved the executable code and both Wasm payloads. [Hydrated iOS runtime](verification/receipts/fieldlog-ios-hydrated-signed-runtime-41a05264.json).

During a local outage drill, the restarted Oban processor drained eight queued jobs once. A separate five-request burst exhausted the browser lifecycle pool and left authenticated requests unavailable even after the connections became idle. Restarting Phoenix restored the existing session. A subsequent candidate recovered the same session after connection check-in on the original listener. Two isolated database runs verified idempotent retry and tenant isolation. [Candidate recovery](verification/receipts/l07-ordinary-session-recovery-41a05264.json). [Service outage drill](verification/receipts/l07-integrated-outage-41a05264.json).

The public upgrade guide replay preserved FieldLog’s workspace, photo, outbox and dependency lock through recovery, upgrade, export and an independent Android build. The macOS bridge now reports the Swift source location for a trap in both optimized guest builds. A fresh root replay passed 53 tests. [Upgrade and exit](verification/receipts/l08-public-upgrade-02002272.json) · [Swift diagnostics](verification/receipts/l03-swift-diagnostics-review-41a05264.json).

The first iOS build with automatic task hydration failed its installed capability material check before the baseline guest started. The loopback service closed and the owned Simulator was removed with all external identities and boot states preserved. [Hydration attempt](verification/receipts/fieldlog-ios-first-frame-material-runtime-41a05264.json).

The corrected Pair24 default Android starter launched from its relocated export on API 36. Adding and toggling an entry moved progress from zero to one completed. FieldLog separately persisted all 132 note characters after paced input and a cold launch. A single burst on the trace build retained 119 characters and logged 26 stale Android input events. [Starter runtime](verification/receipts/l01-default-starter-pair24-runtime-41a05264.json) · [Note input comparison](verification/receipts/fieldlog-android-note-burst-and-paced-41a05264.json).

The separate macOS development signer binds the three authenticated build downloads to the exact tenant, build and journal revision. Verification succeeded after the ephemeral key was removed. A separate replay verified recovery on the signed loopback port and refusal of extended ACLs on key and state files. [Build attestation](verification/receipts/l05-native-development-attestation-41a05264.json) · [Custody and restart](verification/receipts/l05-native-attestation-acl-restart-41a05264.json).

Local iOS v2 development attestations bind the exact settled worker operation. The restricted PostgreSQL fixture rejected an old envelope after replacement with byte-identical products, preserved replay and rollback, and required an explicit writer grant. Historical v1 verification and the existing browser build detail remain compatible. The ordinary runtime still needs wiring for the attachment call. [Operation binding and privilege checks](verification/receipts/w12-l05-native-attestation-operation-v2-716a3f3a.json) · [Composed v72 verification](verification/receipts/w12-l05-hosted-v72-composition-1f7eda6884.json).

On Android API 36, the signed fixture kept the same process through two Activity recreations. A separate installed fixture fetched baseline, review and rollback from the local v3 service. After an interrupted download and force-stop, it reopened the rollback with the service forwarding rule removed, then resumed and ran the reviewed release. The guest task remains in memory. [Activity recreation](verification/receipts/fieldlog-android-recreate-runtime-41a05264.json) · [Local service delivery](verification/receipts/fieldlog-android-network-runtime-41a05264.json).

The local v3 release origin suppressed a previously published offer after its assignment key was revoked. The replacement key restored delivery at sequence 2, and the independently signed artifact retained its original bytes. [Release origin](verification/receipts/l07-v3-publisher-incident-41a05264.json). The default Android starter crashed in Activity startup on API 36 before rendering its first frame. Both disposable emulators and private ADB servers closed. [Android starter](verification/receipts/l01-export-android-startup-41a05264.json).

Free organization creation passed against the full 16-migration PostgreSQL schema. The local Phoenix replay exercised 38 HTTP responses, and SQL counted zero payment credentials. The integrated checkout passed hosted and native source admission in both Python modes. [Free onboarding](verification/receipts/l06-hosted-free-onboarding-integrated-41a05264.json).

The relocated iOS starter rendered its title and zero-entry progress on first launch and relaunch on iOS 26.5. A separate Android input trace stopped at the Title field before reaching Note. Emulator group custody is unresolved. [iOS starter](verification/receipts/l01-export-ios-runtime-41a05264.json) · [Android input hold](verification/receipts/fieldlog-android-input-title-hold-41a05264.json).

The public setup guide includes both downstream FieldLog patches. A fresh checkout reproduced the exact Pair23 build tree and Android photo test tree. Android received 52 of 132 note characters before keyboard dismissal. After one retry of the missing suffix, the cold-reopened entry contained 90. [Public fixture replay](verification/receipts/fieldlog-pair23-public-fixtures-41a05264.json) · [Android input](verification/receipts/fieldlog-android-long-note-runtime-41a05264.json)

The CLI changes are on main at `79233ba123` and the corrected Android renderer and Pair23 source profile are on main at `735ecec14e`. The default starter lock fix is on main at `f048e40c52`, the signed host replay at `9dadcee1d7`, and the restricted worker, ordinary artifact downloads and console navigation fix at `af8bc9dc24`.

The exported starter passed all four host tests after removal of its source project and SDK checkout. Export now stages in a private directory, verifies the copied lock, preserves empty resource directories, and publishes without overwriting another export. The final local replay passed five focused Swift tests and all 100 discovered Python tests, including five public export regressions. The relocated iOS starter built for arm64 Simulator. FieldLog’s older Pair21 SDK was rejected. A separate FieldLog checkout pinned to public Pair23 then produced a signed Android APK from a relocated export with the original SDK and adapter unavailable. The downstream patch seeds the admitted dependency lock. The default starter lock correction passed a real Pair22 Android build locally. [Pair23 FieldLog build](verification/receipts/fieldlog-public-pair23-export-41a05264.json) · [Default lock](verification/receipts/l01-android-starter-lock-pair22-79233ba.json) [Independent starter](verification/receipts/l01-public-cli-independent-export-41a05264.json) · [Publication and copy checks](verification/receipts/l01-public-cli-export-atomic-41a05264.json)

The public GeneratedReport app on an API 36 arm64 emulator saved a task, restored its exact title and responsible person after a cold launch, showed the unsent queue entry, and opened the native share sheet for the report. Completing the reopened task blanked the UI and the completion did not persist. The emulator exited with PGID 3401 still present. Its instance is held. [Public build](verification/receipts/fieldlog-public-android-41a05264.json) · [Runtime and cleanup](verification/receipts/fieldlog-android-public-runtime-41a05264.json)

On iOS 27.0 Simulator, FieldLog picked a seeded photo, saved the entry, terminated, relaunched, and displayed the same photo in the saved entry. The persisted 1600 × 1067 JPEG matched all four seed colors within one RGB channel level. All 14 external device identities and states matched after cleanup. One already-booted external device reported 987,136 additional bytes before shutdown of the owned device. The cause is unverified. With a draft-scoped field identity fix in the separate FieldLog checkout, Android selected the seeded PNG in DocumentsUI, committed the entry and cold-reopened it. The linked 1920 × 1280 JPEG matched all four seed swatches within one RGB channel level. [Android persistence](verification/receipts/fieldlog-android-photo-persistence-41a05264.json) [Android attempts](verification/receipts/fieldlog-android-photo-first-runtime-41a05264.json) · [iOS runtime](verification/receipts/fieldlog-ios-photo-persistence-41a05264.json)

A separate Android diagnostic isolated the checklist failure to the unfocused responsible-person field while rendering the saving state. Its proposed frame shifted one pixel. With the corrected renderer, Complete survived force-stop and relaunch, and the unsent queue grew from two changes to three. Both runs released their emulator and ADB groups, ports and test instances. [Corrected Android runtime](verification/receipts/fieldlog-complete-fixed-runtime-41a05264.json) [Android diagnostic](verification/receipts/fieldlog-complete-diagnostic-runtime-41a05264.json)

Two Swift-compiled guests (2,757 and 2,790 bytes) matched native task completion and review-before-completion behavior on the owned macOS VM. The tightened replay checked every export, the one-page memory limit, and each newly appended outbox record. The original signed-pair inputs passed all 14 descriptor controls. Mobile activation remains open. [Reviewed replay](verification/receipts/fieldlog-compact-abi2-review-replay-41a05264.json) [Guest proof](verification/receipts/fieldlog-compact-abi2-41a05264.json)

A project-create receipt now preserves a newer workspace selection. A directory load that finishes while creation is in flight still allows the new project to be selected. All 277 console tests passed. [L06 console receipt](verification/receipts/workspace-create-navigation-20261118.json)

The host update tool now exposes release-v3 verification. The updates suite passed 69 Swift tests and 32 CLI cases. On macOS, the signed baseline completed a task in one press, the second signed release required confirmation, and a newer signed rollback restored the first behavior under the same installed identity. The app reopened offline with the accepted assignment after an interrupted download. The guest task was in memory. The Android fixture initially timed out before native first-screen health. With the draw callback fixed, baseline completed in one tap and the reviewed release required confirmation. One rollback lost the guest controls on Complete. Two fresh API 36 replays completed rollback, retained the 257-byte partial download at sequence 4, and recovered the same rollback candidate after force-stop. One replay used the same APK as the failure. The cause remains open. [Android offline replays](verification/receipts/fieldlog-android-signed-offline-runtime-41a05264.json) [Android rollback](verification/receipts/fieldlog-android-signed-rollback-runtime-41a05264.json) [Android signed trial](verification/receipts/fieldlog-android-signed-first-runtime-41a05264.json) · On iOS Simulator the baseline reached first-screen health and saved the task at revision 2. The first transition reported incomplete work while retiring the prior owner. After fixing the retirement wait, one iOS Simulator test passed baseline → review → signed rollback → offline reopen with the same installed app. The disk verifier matched the final launch and candidate, workspace revision 6, and seven outbox records. [Signed iOS runtime](verification/receipts/fieldlog-ios-signed-runtime-41a05264.json) The owned device was deleted and all 14 external device identities and states matched. [iOS activation attempt](verification/receipts/fieldlog-ios-signed-first-runtime-41a05264.json) [Installed host replay](verification/receipts/fieldlog-signed-installed-v3-41a05264.json) [L04 verifier receipt](verification/receipts/fieldlog-l04-release-v3-host-cli.json)

The opt-in operation-admission companion migration passed PostgreSQL catalog admission. In the restricted Oban workflow the authenticated POST returned 201. The real start job received SQLSTATE 42501 when the processor tried to record its intent. Migration 500 subsequently allowed the lease-fenced start to record intent and release capacity on stop. That intent-only run recorded zero compiler starts. A subsequent authenticated request started one real unsigned iOS Simulator build and the worker verified the app, symbols and resource inventory. The first ordinary client still saw a running build. After the delivery change, the authenticated client saw `native_succeeded` and downloaded all three outputs after worker shutdown. Their sizes and hashes matched. Replaying the request and jobs left one completion and zero held reservations. A joint rerun used the corrected worker, reproduced all three downloads after shutdown, and confirmed that a stale lease could not publish or release capacity. [Joint integration](verification/receipts/l05-native-joint-review-41a05264.json) [Delivery](verification/receipts/l05-native-delivery-41a05264.json) · [Worker corrections](verification/receipts/l05-native-worker-review-fixes-41a05264.json) [Native build](verification/receipts/l05-native-success-41a05264.json) [Fenced intent](verification/receipts/l05-fenced-operation-intent-41a05264.json) · [Catalog](verification/receipts/l05-hosted-operation-acl-integration.json) · [Dispatch](verification/receipts/l05-restricted-durable-intent-scheduler-41a05264.json)

On the macOS host, five fresh processes per compact guest delivered all 120 timed inputs. The median input-to-next-document time was 10.23 ms for immediate completion and 9.92 ms for confirmation. [Host workload and limits](verification/receipts/fieldlog-guest-benchmark-41a05264.json)

An isolated full-migration database exposed a billing trigger that prevented free organization creation. The candidate migration enabled two free tenants to create organizations, change membership, enforce quotas, export data and tombstone a project through 30 HTTP responses with no payment credentials. [Free administration](verification/receipts/l06-free-admin-41a05264.json)

A fresh local database restored the signed v3 release, assignment and audit responses byte-for-byte. Replaying publication returned its original response and left the audit count unchanged. The source and restored databases shared one isolated PostgreSQL cluster. [L07 restore receipt](verification/receipts/release-postgres-backup-restore-20261118.json)

## Current checkpoint. Public-root SDK support and local end-to-end completion

Main `31f012f13f` defines completion through L01–L08. The public SDK root and nested package now select the unchanged Apple declarations only on macOS hosts. The public root passed234 macOS tests and226 Linux tests with unchanged engine/test bodies. The reviewed net-nine-path cohort includes the compiled Pair22 SDK26 projection and two corrected ordinary digest expectations; installed source admission passes normally and under actual `-O`. SDK96 is `a8c7834694d79818ba5b0cc6e8c6f93f25d0286bd6bfc049221e5ffadc1ab3c7`, Source141 remains `a13d2f79…`, and SDK26 remains `0d030f8b…`. [Public root](verification/receipts/public-root-sdk-boundary-r5560.json) · [Linux](verification/receipts/public-root-sdk-linux-r5600.json) · [Review](verification/receipts/public-root-sdk-review-r5604.json). All9 engine jobs and artifact retention passed at delivered head `d7343fd7f8`. [Exact-head CI](verification/receipts/public-root-sdk-green-ci-r5760.json).

The fresh CLI ordinary suite has30 XCTest passes and125 Swift Testing declarations passing, with404 configured invocations and zero issues. Store-child descriptor closure is unexposed. One real FieldLog Android create/build passed against the new SDK26 inputs; its full SDK96 snapshot was27da, before the public-root-only change, and is not relabeled as the new full SDK. The scoped Android launch is recorded below. [CLI](verification/receipts/sdk-ordinary-contract-root-r5450.json) · [Android build](verification/receipts/sdk-new-profile-android-build-r5500.json).

The Linux container was retired exactly. Fifteen external Mesh containers disappeared concurrently; their owner confirmed intentional cleanup. The protected Papercut container remained exact. The original Linux receipt retains the observed baseline difference.

FieldLog now also passed its unchanged offline UI workflow against the current public-root SDK on iOS27.0 Simulator:1 test,0 failures/skips, with five retained screenshots. The exact owned Simulator was observed Shutdown and deleted; all13 external device identities/states remained exact. This covers edit/save, draft recovery after relaunch, the native share sheet and the unsent local queue; Android, photo attachments, guest parity and signed OTA remain pending. [Build](verification/receipts/fieldlog-public-root-ios-build-r5680.json) · [Actual UI run](verification/receipts/fieldlog-public-root-ios-runtime-r5710.json). [Independent review](verification/receipts/fieldlog-public-root-ios-review-r5720.json) and [Root development acceptance](verification/receipts/fieldlog-public-root-ios-acceptance-r5774.json) confirm this scoped component.

Both repaired five-export FieldLog guests ran in the shipping VM on macOS. Each saved and reloaded one task through the real workspace model and repository. Both runs and the cancellation control closed cleanly. Independent review found that valid whitespace can trap a save and that a lost acknowledgement can strand a committed task. The sheet also needs to retain cleanup ownership. R5862 passed eight real VM cases for those corrections, including replay after a lost acknowledgement and retry after repository rejection. The iOS app compiled. R5876 confirmed the corrections and found that closing the sheet could still let a queued save reach the repository. R5886 blocked the same-turn Save and close write while preserving already admitted commits. The corrected iOS app built and rendered the baseline guest prompt. The native test observed a truncated title and stopped before Save or the changed guest. R5902 confirmed that the title shortened at focus transfer. A stale callback reproduced the same prefix in a macOS control. R5912 recorded 42 live stale-revision refusals in SwiftUI. The full Responsible value was rejected twice, while the title reached its full value after focus. The test stopped before Save. R5924 corrected the private mounted text binding, passed the real guest control and rebuilt the unchanged iOS XCTest. R5934 passed all title readbacks and observed zero stale rejections. Responsible remained partial at AX readback, so the test stopped before Save. The private trace recorded roughly 1.2 seconds per completed text dispatch. R5938 reproduced second-scale dispatch on the host and measured at least 99.57% in VM event and settlement. A separate owned stack sample located a deadline-clock hotspot. R5958 measured a median 62.48 million clock reads per edit across 140 instrumented host turns. Frame agreement accounts for a median 10.93 million. R5978 removed the agreement clock reads in a private candidate and measured 20.8% less matched-prefix dispatch CPU per interpreted instruction across five host process pairs. First frames, all 616 edits, safety controls and consuming ledgers matched. R5998 independently verified both source hunks and the 20.79% scoped macOS host result. R6008 applied the two exact hunks to the local working tree and verified the inverse. The active hosted source check still selects Source359. R6008 prepared both exact arm64 Simulator runners and reverified the unchanged test and guest payloads. R6020 ran the pair on one owned Simulator. Both arms captured partial title accessibility values before Save, then showed the exact padded title later. The median of 24 matched dispatch intervals was 1.681 s for the reference and 0.981 s for the candidate. The owned device was deleted and the 14 external devices matched. R6028 built the exact typing settlement check. R6036 proved host relay readiness but XCTest parsed a nil URL host before app launch. The owned device was deleted and all 14 external devices matched. R6048 proved actual relay reachability. The baseline saved and reopened, and the changed variant settled both exact inputs. R6050 corrected the selector. R6054 passed the owned iOS XCTest for both variants, including exact input, Save, dismissal, zero ledger, and identical records after relaunch. The result uses bundled guests in separate workspaces. R6060 found the bundled guests exceed the signed runtime's 4 MiB limit and use a different ABI. The current iOS fixture also lacks signed-store activation. R6066 and R6068 were interrupted. Resume the compact guest and signed host work as fresh attempts using the retained R6060 rejection evidence. [Simulator pair build](verification/receipts/fieldlog-vm-frame-ios-pair-r6008.json). [Reviewed VM adoption](verification/receipts/fieldlog-vm-frame-agreement-adoption-r6008.json). [Host comparison](verification/receipts/fieldlog-vm-frame-agreement-live-ledger-r5978.json). [Clock profile](verification/receipts/fieldlog-vm-clock-accounting-r5958.json). [Native binding trial](verification/receipts/fieldlog-ios-guest-binding-root-r5934.json). [Native input trace](verification/receipts/fieldlog-ios-guest-input-trace-root-r5912.json). Signed OTA remains pending. [Native trial](verification/receipts/fieldlog-ios-guest-typing-root-r5898.json). [iOS prerequisite](verification/receipts/fieldlog-ios-guest-archive-handoff-r5880.json). [Guest save evidence](verification/receipts/fieldlog-guest-save-private-evidence-r5862.json). The corrected Android controller established the private transport and launched the actual FieldLog app on API 36. The test verified text entry, then observed an empty app frame after tapping Save draft. Draft persistence and cold reopen remain unverified. Both process groups closed and the disposable AVD was removed. A fresh run reproduced five blank frames after Save draft while the activity stayed resumed. The workspace stayed byte-identical at revision 1 with zero drafts. The follow-up confirmed the crash database path was private and retired the AVD and both groups. R5890 reproduced the draft save in the Swift host and isolated a viable renderer-rejection path in a control. The R5906 diagnostic run reached the Saving snapshot, then the Swift event send threw before any repository entry was observed. The workspace stayed unchanged. The Java trace filled at touch down. R5926 prepared an arming marker and bounded Java and Swift error traces. R5942 captured the actual Saving-frame rejection in the Java retained-editor preflight. The workspace stayed unchanged and the owned emulator closed. R5952 reproduced two possible mismatch predicates on the host. R5966 sent one armed Save tap to the enabled button on an owned emulator. Five frames were blank, both traces stayed at readiness, and the workspace was byte-identical at revision 1 with no draft. Emulator, ADB and private storage closed. R5974 found readiness-only paths in the Activity controls. A delivered DOWN with a live writer still logged when the SDK gate was closed. R5986 built the Java-only diagnostic and bounded observer. R5994 recorded startup Activity recreation, then the replacement Activity received Save through a current SDK gate without a trace writer. It enqueued the Save before the renderer rejected it. Workspace bytes stayed unchanged, and the owned AVD and ADB closed. The rejecting predicate and Save durability remain unverified. The R5996 lane delivered the R6004 Android APK that preserves fixed diagnostic codes across recreation. R6016 observed a current SDK gate then HANDOFF_CURRENT_FRAME at the nonvertical handoff check, followed by CONFIGURATION in the retained fallback. The workspace stayed byte-identical. Both owned Android resources closed. R6018 prepared a Java-only diagnostic for the first refusing current-frame guard. R6030 stopped before binding the AVD transport and reported unknown inner custody. Save did not run. R6032 passed ten host controls for pre-bind reporting and direct cleanup. Its earlier inert helper groups remain held. R6046 observed emulator exit 1 before transport binding, with no captured stderr. Both direct groups closed and detached-helper custody remains unverified. R6052's provider failed after writing a recoverable diagnostic patch. R6062 replayed five host controls and ran one startup-only attempt. The emulator still exited 1 before bind, and the new namespace and ports are held. R6064 verified that the 6 GiB cold AVD fixture needs 8,912,057,140 available bytes with the local reserve. After disk cleanup, the worktree volume exceeded that threshold. A fresh preflight on the selected AVD volume and one owned startup-only trial remain pending. [R6064 preflight](verification/receipts/fieldlog-android-cold-data-space-r6064.json). [Rejection APK](verification/receipts/fieldlog-android-save-rejection-apk-r6004.json). [Live renderer reason](verification/receipts/fieldlog-android-save-current-frame-root-r6016.json). [Unsigned diagnostic](verification/receipts/fieldlog-android-save-input-apk-r5986.json). [Owned Android trace](verification/receipts/fieldlog-android-save-activity-root-r5994.json). [Input diagnostic](verification/receipts/fieldlog-android-save-input-diagnostic-r5974.json). [R5966 Android receipt](verification/receipts/fieldlog-android-save-predicate-root-r5966.json). [Armed Save trace](verification/receipts/fieldlog-android-save-retained-editor-root-r5942.json). [Android save trace](verification/receipts/fieldlog-android-save-trace-root-r5906.json). [First Android trial](verification/receipts/fieldlog-android-ordinary-root-r5872.json) · [Post-save observation](verification/receipts/fieldlog-android-save-observation-r5888.json). [Guest execution](verification/receipts/fieldlog-guest-five-export-repair-r5790.json) · [Android preparation](verification/receipts/fieldlog-android-workflow-prep-r5780.json).

The shipping CLI inventoried five Swift files in the actual FieldLog iOS app and reported six advisory migration findings. [Import run](verification/receipts/fieldlog-advisory-import-root-r5864.json).

The private worker handled a real request and produced an unsigned Simulator app, matching symbols, and a resource inventory. Replay reused the result. Independent review confirmed the three artifacts and found that preflight and postflight checks cannot bind the bytes read during compilation. R5870's real build used the worker's admitted copy after the caller's lock changed. It produced the same three artifact kinds. Replay reused the result, and reopening the worker confirmed the stopped tombstone. Review confirmed the private result and requires authenticated startup and preservation of ordinary iOS CLI behavior. R5896 passed the startup checks, ordinary iOS CLI argument control, and managed socket controls with zero compiler starts. The artifact request timed out and remains held with compiler custody unverified. R5914 confirmed the scoped startup and no-build evidence and identified open registration binding, response authentication, cancellation, and completion issues. R5922 joined the real Elixir adapter and Python listener. After one lost stop acknowledgment, a query recovered the same tombstone, and same-registration reopen recorded one stopped row and zero starts. R5928 confirmed the paired proof and identified a fail-closed but unrecoverable first-registration interruption. A private R5936 caller-side startup check recovered same-pin pending bytes after simulated filesystem failures and refused mismatched or unbound state. Live process-interruption recovery remains unverified. R5932 proved capacity hold after a lost acknowledgment and exactly-once release through a subsequent authenticated query. R5948 reviewed that scoped result. R5956 passed the composed prepared-worker SQL checks with 13 authenticated exchanges, five releases, one hold, and zero compiler starts. The current lease released once after the old lease expired. The optional extra psql pass was skipped after the driver misread the final summary. The successful SQL output and independently reopened SQLite rows agree. [R5956 scoped receipt](verification/receipts/native-worker-composed-coordinator-root-r5956.json). R5970 composed seven files against Source359 and passed an authenticated Python worker startup and query with zero compiler starts. Source360 remains proposed. R5980 reproduced three worker issues involving prelaunch expiry, terminal custody after validation failure, and missing retained evidence. R5988 passed all 14 registered-worker cases in normal and optimized Python. The private corrections preserve zero-start expiry, confirmed terminal custody and retained-evidence admission. R6004 reproduced two remaining worker defects. Partial admission cleanup can appear as clean absence, and lost readiness evidence can block definitive cancellation after confirmed terminal custody. R6010 passed private cleanup and cancellation controls, including one SQL capacity release after a lost stop acknowledgment, with zero compiler starts. R6026 reproduced a failed evidence write that can keep capacity held after proven compiler closure. R6034 corrected both stop orderings and passed the independent normal and optimized worker controls. R6042 proved one authenticated local build reached three-artifact native_ready with capacity held, then cancelled with one release. The private fixture installed its operation schema after the request. R6058 fixed the preboot catalog check with a private companion migration and proved the real restricted Oban scheduler could release a zero-start reservation. R6072 was interrupted. Source360 remains inactive. Resume with a fresh private run that verifies one real compiler start through the ordinary restricted processor. [Worker review](verification/receipts/native-worker-known-custody-review-r6004.json). [Worker corrections](verification/receipts/native-worker-known-custody-retention-r5988.json). [Independent review](verification/receipts/native-worker-managed-cohort-review-r5980.json). [Worker composition](verification/receipts/native-worker-managed-source-composition-r5970.json). R5930 admitted and executed the actual FieldLog Task Editor guest, saved and reopened one task, and closed the VM cleanly. The native artifacts from R5870 are for a different app. R5940 built and executed a fresh guest from the locked recipe. The native build stopped at Xcode manifest setup before compilation. R5950 compiled the private arm64 Simulator app with the exact fresh Wasm from R5940 and matching dSYMs. R5964 captured and reopened the app, symbols, and resource inventory through the existing owners, and matched the embedded and standalone guest. The original public CLI native-build.json is missing, so compatibility, SBOM and provenance remain open. R5972 proved the ordinary CLI refuses the app-owned Xcode project. The private retaining adapter refused its incorrect recipe digest before Xcode. The source digest now matches the owning implementation. R5982 built the exact FieldLog recipe via the public command and private adapter. The owner reopened the original v2 report, pinned all five identities and matched the app, symbols, inventory and embedded guest. The separate report command refused the 136,595,681-byte archive at its 64 MiB parent reader. R5992 streamed the exact existing archive through the private owner-bound change and reopened the original same-build report with an unsigned SPDX SBOM and SLSA provenance. The original build and 64 MiB ordinary reader limit were preserved. R6002 verified the retained byte and binding evidence. It found a publication defect when the final archive name no longer refers to the verified descriptor or the directory flush fails. R6012 corrected final-name identity and cleanup in a private patch. Both regressions reproduced the original defects, then 32 owner tests and two private integration controls passed. R6022 passed the exact change at its tested scope. R6044 applied the exact archive correction and Source141 successor locally. Both Python modes admitted the installed authority, Source359 still verified, and the artifact check passed in a separate index. [Archive correction](verification/receipts/native-report-final-name-ownership-r6012.json). Compatibility and aggregate eligibility remain open. [Archive review](verification/receipts/native-report-parent-archive-review-r6002.json). [Reopened report](verification/receipts/native-report-parent-archive-retention-r5992.json). [Original v2 report receipt](verification/receipts/fieldlog-corrected-public-build-r5982.json). [Public build boundary](verification/receipts/fieldlog-public-native-build-boundary-r5972.json). [R5964 retained artifacts](verification/receipts/fieldlog-same-recipe-retained-artifacts-r5964.json). Complete guest coverage and the remaining lifecycle outputs are pending. [Worker materialization](verification/receipts/native-worker-materialized-request-r5870.json). Free self-service passed the consent checks, then stopped at login because the new permission rows conflicted with the browser catalog guard. R5868's private catalog correction passed login, organization and project creation, authorization, quotas, export, and tombstone deletion over live loopback HTTP with payment disabled. Review found gaps in catalog drift detection, existing membership edits, and the migration inventory. R5892 passed both private PostgreSQL tests covering those corrections, including ordinary migration up and down, and the proposed Source352 passed its source-only checks. R5910 confirmed the catalog and membership corrections. Two exact migration assertions and active collector cutover are included in the combined R5916 work. R5894 proved cookie login and the database rejection when either role attempts the other operation. R5904 passed live loopback creation of the first organization and project with the browser session locked during the write transaction. R5916 passed seven private PostgreSQL tests and the Source355 collector controls. R5918 built both console modes and passed focused workspace UI controls. R5944 confirmed the backend migration and collector changes and found that the combined backend and console bytes need a new source pin and a reconciled artifact policy. R5954 pinned all 359 combined paths. R5962 applied the reviewed packet locally after exact rollback and retention checks in an isolated index. The active source check passed in normal and optimized Python. [Source359 apply receipt](verification/receipts/free-workspace-source359-root-r5962.json). R5946 passed private browser onboarding. A real browser signed in, created one free organization and project, and reread both after reopening with zero extra writes. The owned browser and both services closed. R5960 timed out at the first browser navigation before Sign in or Create build. The database retained 25 builds and 25 jobs, and all five server ports became reusable. Chrome group 87408 and its exact private namespace remain held. R5976 passed the inert navigation and cleanup controls. The live fixture first refused an old BEAM source path. R5984 rebuilt the 32 modules in the new fixture and ran one real default-profile Create build click. It received 201 and a matching authenticated queued detail; SQL confirmed the one queued build and job. A bridge write and final queued DOM assertion still failed. The new browser and both services closed. R5990 passed one fresh live run. The corrected observer matched the queued card ID to one HTTP 201, the authenticated iOS detail and the PostgreSQL build and job. All recorded browser and service owners closed. This accepts the default browser create and queue slice. No worker dispatched. The earlier R5984 failure remains preserved. [Queued browser result](verification/receipts/free-workspace-default-build-create-root-r5990.json). [Navigation controls](verification/receipts/free-workspace-default-browser-navigation-r5976.json). [Browser and SQL receipt](verification/receipts/free-workspace-default-build-create-root-r5984.json). [R5960 default browser receipt](verification/receipts/free-workspace-default-browser-root-r5960.json). [Local browser onboarding receipt](verification/receipts/free-workspace-browser-onboarding-root-r5946.json). L05 and L06 remain open. [Self-service HTTP](verification/receipts/free-self-service-http-private-evidence-r5868.json). [Worker run](verification/receipts/native-worker-pinned-request-r5856.json) · [Earlier self-service failure](verification/receipts/free-self-service-admin-r5800.json).

R5350 remains held: consuming closure was observed but the success assertion failed and HTTP success is unestablished. Emulator-5584, group18659 and its exact retained namespace remain untouched. [Native result and hold](verification/receipts/signed-jni-genuine-root-r5350.json). All other specific holds remain active.

Historical delivered `39f6771` had nine engine jobs and artifact retention passing. Later `e8b5e5` failed its Swift download in Android CI; the one manual hash profile exceeded the hosted job time limit without exposing counters. These are scoped unresolved diagnostics, separate from dependency-ready local implementation. [CI failure](verification/receipts/e8b5-android-first-failure-r5424.json) · [Manual profile](verification/receipts/manual-profile-cancel-diagnosis-r5460.json).

## Current checkpoint. Prepared Android lock and final source guard adopted

Root adopted the reviewed nine-file lock-preparation and APK-cleanup slice. The actual platform lock is resolved before source freezing and bound by its own bytes; its origin hash remains distinct from the SDK lock. Final source-admission failures reject and remove the owned APK where deletion succeeds, preserving the original failure. Current Source141 is `8acdb9dc49f6b564e58ca4f1c3ac6704836ba86d59455e569436108d3374029e`; Source347 and the canonical SDK96 remain unchanged. Full installed admission passed normally and under actual `-O`. [Source adoption](verification/receipts/android-lock-source-root-adoption-r5278.json).

The exact selected CLI graph passed all 404 ordinary invocations. One Android create/build produced an unsigned APK with the legitimate platform lock and final source guard intact. Root completed the AAPT37 metadata readback; the earlier failed environment and finalizer receipts remain preserved. Store-child descriptor closure remains unexposed. This is development source/build acceptance; signing, Android runtime and release qualification remain pending. [Qualification](verification/receipts/lock-qualification-root-r5276.json).

The signed JNI successor fixes the bounded-poll report defect and passed its 15-row fake proof plus focused source/APK review. Genuine Android JNI/HTTP and signing remain unrun. The original Linux SDK build failed on CoreGraphics; the four-guard successor reached the intentional SwiftUI-only adapter rejection before any tests. Its owned container was removed and the unrelated Docker baseline preserved. A package-level supported-target correction is being prepared. [JNI review](verification/receipts/jni-poll-bound-fix-review-r5240.json) · [Linux failure](verification/receipts/linux-sdk-apple-target-failure-root-r5292.json).

The remote91f CI timeouts remain unresolved: Android inspection180s and the cache lane60s. Matched local measurements rejected general adoption of the unchanged bulk-zero proposal because Debug regressed despite an optimized improvement. The matched-host hash diagnostic is being rebound to the current exact resource; no manual profile has run. All18 product packages, all38 GA gate records, physical-phone restrictions and historical holds remain unchanged; GA stays0/38. [Measurement decision](verification/receipts/arena-fair-measurement-r5244.json).

## Current checkpoint. Android build-input defect and measured CI timeouts

The bootstrap contract repair is delivered at `91f7b10448896cd5c7b8b55fddbdcc30ec424cd4`. Current CI bootstrap controls pass. Seven of nine engine jobs succeeded; Android integration and the shared cache fixture failed. Artifact retention passed. Android inspection completed the Swift toolchain and Android SDK hashes, reading 4,904,356,389 and 3,677,205,885 bytes respectively, before its unchanged 180-second deadline. The CPU/IO cause remains unproven. The cache fixture exceeded its unchanged 60-second limit after a last checkpoint of 960/1003 cases; no assertion failure was exposed. Fresh isolated profiling targets the actual owning operations. [Delivery](verification/receipts/bootstrap-contract-delivery-root-r5034.json) · [Android counters](verification/receipts/91f7-android-progress-failure-r5064.json) · [Cache failure](verification/receipts/91f7-cache-fixture-first-failure-r5066.json).

The private signed Android JNI harness passed its Java boundary compile, then both Swift builds failed on an omitted observation overlay and an unavailable imported C array member. Fake tests, JNI linking, APK packaging and genuine execution did not run. A separate FieldLog Android build compiled and linked 31 Swift sources but correctly rejected its output after SwiftPM added an unbound platform lockfile. Its final APK was deleted. The SDK and platform locks have identical dependency pins but different origin hashes; copying the SDK lock is invalid. The first lock-preparation task stopped after an unisolated help command triggered manifest compilation with a mismatched SDK. No product fix was delivered by that task. Independent private successors now address the actual interop and resolver-input boundaries. [JNI failure](verification/receipts/signed-android-jni-harness-r5050.json) · [FieldLog build rejection](verification/receipts/fieldlog-current-android-build-r5054.json) · [Lock discriminator and failed preparation](verification/receipts/android-resolved-input-contract-r5080.json).

The genuine signed guest HTTP development path now passes: one normal-trust GET returned 200 and 577 bytes through the actual Wasm guest, with one native call take, exit join and acknowledgement. Consuming shutdown drained the mailbox and left zero active HTTP leases, retained exits and payload bytes; store and reservation closed. This uses private read-only instrumentation and a TESTONLY iOS descriptor on a macOS host, not an iOS runtime receipt. The initial canonical-material failure and prior inert-test failures remain preserved. Full W06/W09, JNI, platform and immutable-package qualification remain pending. [Genuine guest acceptance](verification/receipts/genuine-guest-http-root-acceptance-r4880.json).

The shipping source export preserved all 107 source, SDK and lock files. A fresh standalone host build produced 24 arm64 objects, and Root completed the independent review readback. Full FieldLog at app commit 552559d2d3278abb9b1aa7dcf0288102c09a202b now builds for arm64 and x86_64 iOS Simulator using the exact current 96-file SDK; only private dependency location and generated lock changed. Build/source review passed. Root launched one isolated iOS 27 Simulator workspace and visually verified its initial screen; the disposable device was shut down/deleted and the external device baseline remained unchanged. The initial-screen smoke is preserved separately. [Native smoke](verification/receipts/fieldlog-native-smoke-root-r4890.json). [Export acceptance](verification/receipts/export-build-root-acceptance-r4844.json) · [FieldLog build](verification/receipts/fieldlog-current-sdk-build-r4864.json).

The existing FieldLog offline workflow now passes on an owned iOS 27.0 Simulator: one actual UI test, zero failures or skips. It creates a project, edits and reorders tasks through public SDK fields, restores the exact multiline draft after relaunch, saves it, opens the native share sheet without choosing a destination, and verifies six local pending changes. Root viewed all five screenshots. The disposable Simulator was shut down and deleted; all twelve external device identities and states remained unchanged. Independent evidence review and Root development acceptance passed. Immutable-package consumption in independent CI, physical devices and full W15/W17 acceptance remain pending. [Workflow evidence](verification/receipts/fieldlog-offline-workflow-root-r4926.json) · [Root acceptance](verification/receipts/fieldlog-offline-workflow-root-acceptance-r4954.json).

Android Rust and Swift compiler prerequisites remain accepted within their recorded scope, including the Swift compiler preparation-bound deviation. The selected blocking JNI ownership design has a private implementation, but its first host and Android builds failed before fake tests or a shared-library link. Actual Android JNI, normal-trust TLS and consuming closure remain unrun. The original failures and all holds are preserved. [Android prerequisites](verification/receipts/android-native-prerequisites-root-r5036.json) · [Unaccepted harness](verification/receipts/signed-android-jni-harness-r5050.json).

Billing development startup/shutdown remains accepted after 42 assertions, fourteen migrations, the eight-mask privilege matrix, actual Repo/ProcessorAdmission/Oban supervision, zero jobs and clean shutdown. Financial activation, deployment and full W14 acceptance remain pending. [Billing acceptance](verification/receipts/billing-startup-root-acceptance-r4654.json).

Production141 now binds the diagnostic resource at e966c43efd05ae04e9ed3b14f1f4dbb525646558442807bcca3b09a0b6d34e86; original source127 inverse and SDK96 remain exact. SDK96, original source127 inverse and historical authorities remain preserved. All eighteen packages remain in scope. Physical phones stay disconnected; broader UI input/appearance, complete platform, immutable-package, customer and operational gates remain pending. All holds remain active. GA stays 0/38.

## Continuation checkpoint, November 16, 2026 — console development accepted; SDK ordinary qualification passed

The owned-Chrome console slice now has Root acceptance and an independent review of all three actual screenshots, source identities, HTTP/DOM results, matching creator-role database records, and positive service/browser cleanup. One build submission returned 201 and its exact queued build ID appeared in both DOM and PostgreSQL. The backend test passed once. This uses a synthetic development provider; production-provider delivery, compiler draining, broader browser coverage and GA remain pending. Historical callback and cleanup failures remain preserved. [Acceptance](verification/receipts/console-development-acceptance-root-r4382.json) · [Independent review](verification/receipts/console-visual-db-evidence-review-r4380.json).

The source141/Pair22 workflow cohort passes 14 controls in both normal and actual optimized Python, with independent source/evidence review. A fresh standard CLI build and one unfiltered ordinary batch now pass all 404 invocations. The successor changes only the stale Pair21 expectation and test name, and uses writable fixture copies. The original failure remains preserved. SDK adoption still awaits the coordinated test and authority bindings and their independent review. Root staged this evidence checkpoint during the worker's index observation. That explains its preserved index-byte mismatch; all source and dependency bytes remained exact. [Final guard review](verification/receipts/sdk-workflow-final-pin-review-r4372.json) · [Ordinary qualification](verification/receipts/source141-pair22-ordinary-r4384.json).

The genuine public SDK native title result remains scoped and frozen: six keyboard events, revisions 1/2, stale rejection, zero consuming ledger balances and positive OS closure. Native pixels remain unverified. Billing's minimal dedicated ingress startup now passes. The first worker case passed eleven HTTP assertions, then its binding query failed through human-directory organization RLS. Nine worker cases remain unrun. A narrow authorization-boundary correction is in progress. The latest delivered CI head passes Android, VM, services, and the cache fixture. Its Swift aggregate fails because both prerequisites report abandoned, with no Swift compiler or test failure exposed. The older Android inspection deadline remains preserved; it justifies no production optimization or budget change. All historical holds remain active. [Native](verification/receipts/public-sdk-native-successor-root-r4306.json) · [Billing](verification/receipts/billing-minimal-ingress-runtime-r4386.json) · [CI diagnosis](verification/receipts/8f06-swift-first-failure-r4388.json).

All eighteen packages remain in scope. GA remains 0/38; physical-phone, immutable-package, platform, customer and operational gates are unchanged.

## Continuation checkpoint, November 16, 2026 — final SDK guards pass; integration holds preserved

The corrected source141/Pair22 packet passes all 13 final controls in normal and actual optimized Python, including direct rejection of an extra authority member after its seal is recomputed. A zero-write dry apply validates all 57 paths against current canonical preimages. The earlier reviewer stopped on a directory setup error before testing; Root supplied the exact 928-file fixture and completed both final waves. Independent source/evidence review remains pending, and canonical SDK/profile adoption is still false. [Final qualification](verification/receipts/sdk-source141-root-qualification-r4324.json).

The genuine public SDK native title acceptance remains valid and frozen: six events, revisions 1/2, stale rejection, fourteen zero currents, zero tickets/invariant, host exit 0 and positive OS closure. The callback-only diagnostic observed 303 before STOP, but owned Chrome cleanup became UNKNOWN before PostgreSQL shutdown. Its entire live namespace and associated processes are held; no console acceptance or further held access is authorized. Root's initial post-run read preceded the hold check and is recorded as a deviation. A prospective cleanup-error diagnostic is being prepared without executing another browser. [Native acceptance](verification/receipts/public-sdk-native-successor-root-r4306.json), [new console hold](verification/receipts/console-callback-root-hold-r4322.json).

The first-party billing implementation compiles but remains unaccepted. Its first PostgreSQL attempt is held. A separate start/SELECT1/fast-stop control passed, and a fresh worker attempt then exposed actual PostgreSQL 42601 from the migration's multiple statements. All ten worker cases remained unrun; that fresh PostgreSQL/runtime cleanup closed positively. Independent source review also found two effective-privilege defects. A minimal DDL/privilege correction is active. [Held prerequisite](verification/receipts/billing-worker-hold-root-r4312.json), [fresh liveness](verification/receipts/postgres-fresh-liveness-root-r4314.json), [actual migration failure](verification/receipts/billing-worker-runtime-successor-r4318.json), [source findings](verification/receipts/billing-worker-source-review-r4316.json).

At pushed head `d153cad219e354130495ba8d6f373b75ce6e917a`, Phoenix, identity-network and retention CI pass. Eight engine jobs pass; generated Java integration is the sole engine failure and its first actual failure is being diagnosed. All 18 packages retain their full scope, every historical and new hold remains active, and GA remains 0/38. The global native-resumption index/policy update is deferred until the coordinated source141 policy boundary is resolved; exact new attempt receipts are retained separately.

## Continuation checkpoint, November 16, 2026 — genuine public SDK native title control passed

The exact qualified SPI SDK and optional backend now pass the genuine original-feature native title trial. Six PID-targeted keyboard events produced the original title result, revisions 1/2 and stale-action refusal. Five callbacks processed and eleven retired explicitly; none remained queued or inflight. Actual consuming cleanup recorded fourteen zero currents, zero tickets and invariant zero. The host exited 0 without forced signals; all 194 source and 96 SDK inputs, executable and module remained exact. The neutral constructor container is initialization only, not guest evidence. Native pixels, canonical source/profile admission, immutable published packages, portable execution, physical final acceptance and GA remain pending. [Actual native control](verification/receipts/public-sdk-native-successor-root-r4306.json), [changed-fix review](verification/receipts/native-startup-bootstrap-review-r4296.json).

The formatter correction is pushed as `d153cad219e354130495ba8d6f373b75ce6e917a`. Phoenix, isolated identity-network and artifact-retention CI checks pass; engine checks remain in progress at this observation. The closed console callback503 is a separate development failure; its exact internal refusal is still unexposed. A single compiled fixed-tag discriminator is being prepared for the next owned browser trial. SDK source141/Pair22 admission and the first-party billing worker remain private active work. All historical holds remain intact and GA stays 0/38.

## Continuation checkpoint, November 16, 2026 — whole formatter correction and closed console trial

The remaining JSON HTTP regression is now officially formatted with the same Elixir AST. The whole default formatter passes across 266 inputs; normal and actual optimized source controls each pass 21 cases. Installed current-source admission and CLI127 ownership pass. Six exact test/current-source bindings are updated; the auth product remains unchanged. The original CI formatter artifact remains unread, so the local result does not identify that historical artifact's failing file. [Applied correction](verification/receipts/auth-whole-format-root-r4292.json).

The owned Chrome trial captured and visually verified the signed-out console. One login returned 200, but the actual callback returned 503; no build was submitted. PostgreSQL, Phoenix, Vite and Chrome all closed positively, all six owned ports were reusable, and source/dependency inputs stayed exact. Authenticated pixels and paired submitted-build database proof remain pending. [Actual trial](verification/receipts/console-owned-chrome-root-r4288.json).

The first genuine public-SDK host attempt failed on duplicate revision-1 reconciliation, while consuming cleanup proved fourteen zero currents, zero tickets and invariant zero. A constructor-only successor passes the old-fail/new-pass SDK proof and builds; independent changed-fix review and a fresh native control remain pending. SDK consumer source review passed; coordinated successor source/profile admission is private work. [Closed native failure](verification/receipts/public-sdk-native-root-r4280.json), [startup successor](verification/receipts/native-startup-bootstrap-completion-r4290.json), [consumer review](verification/receipts/sdk-consumer-final-review-r4270.json).

Billing still lacks a shipping reconciliation worker. Its first implementation task stopped during source discovery with UNKNOWN command custody and no code or runtime. The exact hold is preserved; a fresh isolated implementation uses the selected first-party worker contract. No financial activation or provider qualification follows. All 18 packages retain their scope and all 38 GA requirements remain open.

## Continuation checkpoint, November 16, 2026 — formatted auth source and qualified SDK components

The first Phoenix check after auth v28 delivery stopped on official formatter output, before runtime. The rollback regression is now officially formatted with identical Elixir AST, and its six current-source bindings are corrected. All 21 relevant source/sparse controls passed in normal and actual optimized Python. Installed source admission, CLI127 ownership and the official formatting check pass. The earlier missing-AGENTS fixture failure remains preserved. [CI diagnosis](verification/receipts/auth-v28-hosted-first-failure-r4240.json), [applied correction](verification/receipts/auth-v28-format-root-r4262.json).

The final private SDK session and retirement fence pass 234 tests in each package graph, including all 18 policy cases. The optional native backend links to the accepted VM archive without execution; ordinary tests have no VM linkage. A genuine feature host using this exact SPI opt-in SDK also builds. Canonical SDK/source-profile adoption, host adapter review and actual public-SDK native control remain pending. [Component qualification](verification/receipts/public-sdk-final-component-root-r4264.json), [host build](verification/receipts/public-sdk-genuine-host-build-r4260.json).

The real browser completed login and authenticated workspace/catalog reads. Two snapshot calls timed out; its target then closed before build submission. The one backend test failed on the missing submission record. PostgreSQL, Phoenix and Vite closed positively, all five owned ports were reusable, and inputs remained exact. No pixel or paired submitted-build database pass is claimed. A separate owned headless Chrome blank-page capture passed; it is tooling evidence for the next browser trial. [Closed browser attempt](verification/receipts/console-current-session-root-r4242.json), [capture capability](verification/receipts/owned-browser-snapshot-premise-r4252.json).

All historical failures and holds remain preserved; all 38 GA requirements remain open.

## Continuation checkpoint, November 16, 2026 — auth v28 adopted

The pending-login session correction is installed with its two ordinary regressions. The final full ordinary run passed 911 of 913 methods; the other two are existing Linux-only network tests skipped on macOS. Both Python modes completed 310 unique source controls in segmented runs. Independent review passed. The workflow update also required rebinding CLI127's owning metadata; that repair passed 20 controls per mode and preserved all 829 historical replay files and the production127 digest. Installed v28 and CLI127 checks now pass in both modes. [Root adoption](verification/receipts/session-source-v28-root-adoption-r4214.json), [actual full run](verification/receipts/active-session-diagnostic-full-r4204.json), [segmented review](verification/receipts/v28-segmented-final-review-r4208.json), [co-owner repair](verification/receipts/cli127-v28-workflow-rebind-r4226.json).

The full engine CI run at delivered head `c9941f03` completed successfully. Browser submission with paired database and visual evidence is the next integration. SDK session source remains private: its retirement fence passed source review, but final compiler/test/link qualification is still pending. All earlier failures and custody holds remain preserved; all 38 GA requirements remain open.

## Continuation checkpoint, November 16, 2026 — genuine native title and durable billing ingress

Both SDK designs are grounded and compared. The selected design keeps the session facade portable and moves native ABI ownership into an optional backend product. Its implementation is private and uses the existing standard Swift Crypto pins; canonical SDK adoption, final source admission, portable verification and the genuine public-SDK host run remain pending. [Architecture selection](verification/receipts/sdk-session-architecture-selection-r4186.json).

The next full regression stopped with unresolved PostgreSQL custody after a nonzero runtime. Its actual test counts and failure are unexposed inside the protected run. Auth adoption remains blocked; static launcher diagnosis and SDK implementation proceed separately. [Scoped hold](verification/receipts/active-session-relative-full-hold-r4188.json).

The next full run preserved 489 passes but stopped at a new test-only assumption: the shared provider counter was five, rather than zero. Its canonical unauthenticated session checks completed. The correction removes that absolute-zero assumption while preserving all before/after, retry and replay count checks; a fresh full run and final packet rebind are active. The old full failures remain preserved and no auth source adoption follows. [Failed full run](verification/receipts/active-session-final-full-r4166.json), [test-only correction](verification/receipts/provider-relative-rollback-r4180.json).

The genuine original FieldLog guest passed its owned native title control. Six PID-targeted keyboard events reached the focused original title field, the guest display advanced from revision 1 to 2, and the host exited zero after consuming fourteen zero currents, zero tickets and no invariant failure. All fourteen admitted callbacks were processed or explicitly retired. Pixels, public SDK adoption, immutable published packages, whole-app save and GA remain pending. [Actual native result](verification/receipts/genuine-native-title-queue-root-r4138.json), [closed-evidence reconciliation](verification/receipts/genuine-native-title-closed-review-r4160.json).

Shipping billing ingress passed eleven synthetic development HTTP cases against PostgreSQL and normal Oban. First acceptance and duplicate preserve one durable inbox/job pair; enqueue failure rolls back, and identical-body retry succeeds. Provider delivery, worker effects, financial activation and G23 remain unqualified. [Ingress](verification/receipts/billing-production-ingress-r4120.json), [independent review](verification/receipts/billing-production-ingress-root-review-r4130.json).

The pending-session fix passes all three focused HTTP regressions and nineteen negative plus three positive decoder controls. The fresh full ordinary batch registered 913 methods: 489 passed, one callback-rollback session expectation failed, and 423 remained unrun. The targeted rollback control now passes with canonical unauthenticated HTTP 200, original CSRF, no cookie/redirect and protected-resource 401; all rollback/retry/replay assertions remain intact. A fresh full suite and final v28 packet qualification are running; neither is accepted or applied yet. The earlier R4136 nested-custody hold remains preserved. [Focused HTTP](verification/receipts/active-session-candidate-run-r4128.json), [full regression](verification/receipts/active-session-full-successor-r4144.json), [private source packet](verification/receipts/active-session-source-admission-r4140.json).

All nine engine jobs and artifact retention passed at delivered CLI127 head `397cada95`; this is metadata-level CI evidence. The full product plan and all 38 GA requirements remain open. [CI](verification/receipts/CLI127-green-CI-r4092.json).

## Continuation checkpoint, November 16, 2026 — delivered fixture repair and first auth exception

The public-focus renderer control passed: the uniquely identified original title field owned the field editor, and six keyboard events produced two exact task.title.change callbacks. This is renderer-only evidence with zero VM constructions; the genuine guest host control remains pending. The proposed auth caller change was rejected because it lies outside the observed session route. The next auth test targets ActiveRead discovery directly, and a separate lane exercises the shipping billing ingress with a real durable inbox/job fixture. [Renderer result](verification/receipts/owned-title-focus-root-r4114.json), [rejected caller hypothesis](verification/receipts/browser-session-pending-comparison-r4100.json).

The public-placeholder control identified one enabled, editable title field after fresh Accessibility access was restored. Eight PID-targeted click/key events produced five Cancel actions and zero title changes; the window and controller closed cleanly. A bounded standard-focus escalation now tests focus ownership on that exact field. The auth lane has nine focused contract checks: narrow load rejects the same valid pending attempt that discovery admits; the actual caller comparison remains in progress. [Native control](verification/receipts/owned-placeholder-title-root-r4098.json), [storage contract](verification/receipts/browser-store-decode-fix-r4088.json).

Both reviewed CLI127 test repairs are delivered at `397cada95`. Swift host, VM, generated Android and the downstream Linux guard now pass. The first attempt's two macOS control jobs were not acquired by a hosted runner; their capacity-cancellation annotations remain preserved. One rerun request was accepted on the unchanged commit; all nine engine jobs now pass, and artifact retention passed. [Final CI result](verification/receipts/CLI127-green-CI-r4092.json). [Delivery](verification/receipts/CLI127-fixture-delivery-r4074.json), [hosted evidence](verification/receipts/CLI127-hosted-capacity-r4080.json).

A fresh isolated auth trial reproduced session 200, login 200, then immediate session 503. The first observed exception is `badmatch` in `MixerHosted.BrowserAuth.Store.decode!/2`; the underlying cause is not yet proven. PostgreSQL and Phoenix closed, owned ports are reusable, and all 5,314 copied source/compiled/dependency files remain exact. No provider traversal, browser submission or visual pass occurred. [Actual trial](verification/receipts/console-auth-first-exception-root-r4084.json).

The owned AppKit semantic-tree observer closed cleanly with no title candidate and no input posted. The hosting view exposes no children through this protocol, and two decoration proxies do not conform; this does not prove absence of the title identifier. A different public-placeholder discriminator is in preparation. Native title acceptance, screen pixels and all 38 GA gates remain pending. All historical holds remain preserved. [Native observation](verification/receipts/owned-semantic-title-root-r4082.json).

## Continuation checkpoint, November 16, 2026 — fresh-checkout source127 fixture repaired

At delivered head `955523711`, the VM job passes. Swift host controls fail before ordinary CLI execution because two rejection tests use an absent scratch parent; Linux Swift then stops at its prerequisite guard. The reviewed repair creates and validates the fixture-owned directory. All 20 controls pass in normal and actual optimized modes from initially absent parents, both rejection assertions are reached, and installed admission passes. Production127 remains unchanged. [Root adoption](verification/receipts/source127-scratch-root-adoption-r4068.json).

The separate ordinary-test repair passes all 394 cases without the private historical CLI variable. Both corrections are ready for delivery; fresh hosted results remain pending. The original-renderer probe closes normally but cannot identify the semantic title field through NSView traversal, so it sends no input. The next probe examines the owned accessibility tree. The console's first underlying auth failure remains unproven. Native title, screen pixels and all 38 GA gates remain pending; all historical holds remain preserved.

## Continuation checkpoint, November 16, 2026 — public same-build report admitted as CLI127

At delivered head955523711, the VM job passes; Swift host adoption controls fail before the ordinary CLI step, and Linux Swift stops at its prerequisite guard. The newly found ordinary baseline dependency is a separate issue now repaired locally. The console browser attempt returned authorization_unavailable before submission; all three owned service groups closed and no visual pass is claimed.

The ordinary CLI registration test now uses only the current CLI; the private old-binary comparison remains historical evidence. The isolated full394-case suite passed with that private variable absent, and the coordinated six-path metadata repair passed independent review,20source controls per mode and installed normal/optimized admission. [Ordinary isolation repair](verification/receipts/public-report-ordinary-root-adoption-r4058.json).

CLI127 is applied with the explicit public report command, its ordinary tests, exact caller/workflow bindings and fifteen new authority fixtures. Independent review passed; 292 controls passed in normal and actual optimized modes. Installed admission and idempotent readback pass. The full inverse restores corrected CLI126 exactly, and the prior authorities remain unchanged. [Root adoption](verification/receipts/public-report-root-adoption-r4030.json).

The actual report binds 760 retained materials, 766 SBOM file entries and three genuine native subjects. The ordinary suite passed 394 cases, and both fresh reopens passed. The original build CLI/compiler identity remains distinct from the later observing command. These unsigned results retain verified_subset completeness and refuse aggregate eligibility. Formal schema validation remains pending: the official CUE summary still fails parsing before artifact validation. No whole-app or GA acceptance follows.

The reviewed VM Clippy correction is applied after a fresh ordinary pass across all 59 harnesses: 578 tests passed, zero failed and 30 existing ignored tests remained. All 1,675 consuming rows have fourteen zero currents and zero tickets; 113 expected negative invariant rows are separate. The earlier R3978 chain remains held. At the preceding delivered head, eight Engine jobs passed; the sole VM failure was exactly the twenty Clippy diagnostics now corrected. Fresh hosted validation of these changes remains pending.

Native startup and cooperative cancellation are qualified within their recorded scope. Two bounded keyboard/title attempts closed with zero ledger balances but did not produce a guest title result. A plain AppKit field did receive the PID-targeted title events, so production focus/routing remains unresolved. Screen capture and native title acceptance remain pending. All 38 GA gates remain unverified, and no historical hold is released.

## Continuation checkpoint, November 16, 2026 — real checkout admission and public report evidence

The current CLI126 production selection is unchanged. A coordinated nine-file metadata and caller correction removes two derived Python bytecode declarations, rejects cache paths before source reads, and includes the owning workflow in Android's real sparse checkout. Installed admission passes in normal and actual optimized modes. Qualification covers 277 unique controls per mode from preserved source controls and final isolated apply controls; it is not a single clean 277-test batch. The exact prior metadata inverse and historical authorities remain preserved. [Root correction](verification/receipts/source126-metadata-root-adoption-r3988.json).

The private public report command now executes successfully against the genuine retained build: 760 materials, 766 SBOM file entries and three native subjects. Its ordinary suite passed 394 cases, both fresh reopens passed, and Root completed the independent review's three embedded app checksums and custody gap. Typed CLI127 admission and canonical command adoption remain pending. The output is unsigned `verified_subset`, and all aggregate eligibility checks refuse. [Completed scoped review](verification/receipts/public-report-root-completion-r3996.json), [actual execution](verification/receipts/public-report-registration-fix-r3974.json).

The ARC-corrected AppKit host completed the genuine ten-node startup and expected cooperative cancellation, with fourteen zero currents, zero tickets, no cleanup invariant and positive OS closure. Native title interaction, the AX window contract and pixels remain pending. The VM Clippy correction is now applied after source review and a fresh 59-harness ordinary batch: 578 passed, zero failures and 30 existing ignored tests. The nested privacy build and all 13 probes completed. All 1,675 consuming rows have fourteen zero currents and zero tickets; 113 expected negative invariants remain separate. The earlier R3978 chain remains held, and its historical panic cause is unproven. [Adoption and bindings](verification/receipts/private-swift-clippy-root-adoption-r4020.json). [Native cancellation](verification/receipts/native-cancel-ARC-r3956.json), [VM hold](verification/receipts/private-swift-clippy-ledger-hold-r3992.json).

At delivered head `ab387791a`, eight of nine Engine jobs pass, including generated Android integration, Swift host and Linux Swift. The VM job remains failed at the private Swift step; its exact current predicate is being checked before the reviewed Clippy correction is delivered. The preceding `74131ec2` admission and sparse-checkout failures remain preserved. [Delivered CI result](verification/receipts/real-checkout-CI-result-r4020.json). All 38 GA gates remain unverified, and no hold is released.

## Continuation checkpoint, November 16, 2026 — CLI126 and Android draft persistence

CLI126 is applied with all six reviewed report-component files, the ordinary test update, current caller bindings and the Android sparse-checkout correction in one guarded packet. Final normal and optimized source qualification passed 275 controls each, including all 15 sparse cases; independent review passed. The exact 121 inverse and immutable 121/119/118/Pair21 history are preserved. Installed source admission passes in both modes. The composed CLI ordinary batch passed 388 cases. Same-build snapshot, SBOM and unsigned observing provenance are component-qualified; public automatic snapshot/SBOM/provenance wiring remains pending. Completeness remains `verified_subset`, and aggregate promotion refuses. [Root adoption](verification/receipts/native-report-root-adoption-r3926.json), [final source review](verification/receipts/native-report-source126-final-review-r3922.json), [ordinary composition](verification/receipts/native-report-components-ordinary-r3900.json).

The fresh API36 arm64 emulator run passed saved-draft title/note editing, both edited fields after relaunch, commit acknowledgement, and committed-title persistence after another relaunch. Root inspected the captured Android screenshots and XML. All driver and client groups closed positively; the disposable AVD and private ADB IPC were removed. Committed-note readback and committed-entry editing are not exposed by this pinned app. R3904's earlier expired-window partial result remains preserved. R3930 independent source/evidence review passed all 22 checks; physical phones, immutable-package dogfood and GA remain pending. [Observed UI and cleanup](verification/receipts/fieldlog-draft-root-observation-r3924.json).

The VM ordinary suite now passes 698 tests across all 59 harnesses, with 30 existing ignored tests. Root verified the 479-file composition and 204 raw hashes. Only the historical private stderr-allocation experiment was removed from ordinary collection and retained byte-exactly for replay: the same binary counts five allocations under capture and two with direct stderr. Production code, AF21, SL13 and every other assertion remain unchanged. The 1,675 observed consuming rows have fourteen zero currents and zero tickets; 113 expected negative invariant flags remain separately recorded. Linux CI on this correction remains pending. [Root review and adoption](verification/receipts/VM-private-diagnostic-root-adoption-r3928.json).

The latest pushed Engine run at `3c0609ad` failed in that private VM experiment and a stale seven-pattern Android test fixture; the actual Android job selected eight patterns. Both corrections are now applied locally. Five Engine jobs succeeded and two dependent jobs were cancelled. Fresh hosted qualification awaits the next coherent push. Cache materializer/compiler qualification remains pending. The fourth closed AppKit probe still returned AXApplication aliases for AXWindows members; its cause remains unproven. All specific native/process/ledger holds remain active. GA is still **0/38**.

## Earlier checkpoint, November 16, 2026 — R3880

The cache successor is applied locally with immutable R8 history preserved. Its normal and optimized real suites each passed all 36 successor methods: 33 original bodies and three explicit UNKNOWN replacements. Normal then failed only at an extra launcher completion-marker write; that invocation failure remains preserved. The optimized invocation exited0. Both modes' acquired command groups reached positive terminal custody. Installed cache and CLI121 source admission pass; Root corrected the candidate's CLI121 seal-tree scalar using the unchanged validator's digest formula. The 1 GiB policy is unchanged. Full materializer/compiler and fresh hosted qualification remain pending. [Cache integration](verification/receipts/cache-root-adoption-r3876.json).

The private public-build resource inventory passed Root's completion of the bounded review: all1223 raw files, all three product objects, all three app payloads and the parent binding agree. The390-case private ordinary batch is preserved, and Root's fourth independent process reopened the genuine store successfully. The eight fixture-dependent qualification cases remain separate from the two-path product map. Canonical product adoption and a future typed CLI selection remain pending. The retained input snapshot has752 material rows and524 objects. Its independent byte audit passed; a real Foundation URL probe exposed an output-normalization gap, corrected and tested in the same-build SBOM lane. The resulting SBOM has758 Files with SHA1 and SHA256 and remains a verified subset. Its independent review and same-build provenance work continue. [Inventory completion](verification/receipts/public-resource-root-evidence-r3862.json), [snapshot](verification/receipts/build-input-snapshot-r3838.json), [same-build SBOM](verification/receipts/same-public-build-sbom-r3868.json).

The fresh FieldLog native attempt canceled on AXIdentifier error-25212 before any title action. It consumed to fourteen zero currents, zero tickets and invariant0; its host then exited with signal11. Direct reap, descriptor closure and positive group absence are confirmed without forced signals, so this attempt adds no hold. Three bounded AppKit probes acquired no guest Runtime and closed positively. Swift's native ApplicationServices API reproduced the Python helper's unexpected AXApplication roles for AXWindows members; adding application-bundle metadata did not resolve that result. Native and pixel acceptance remain pending. R3830's older OS hold remains active. A separate source-review wrapper left an unrecorded identity held at its exact logging namespace; that scope is recorded in AGENTS.md. All38 GA gates remain unverified. [Native observation](verification/receipts/native-owned-AX-diagnostic-r3880.json), [review hold](verification/receipts/build-input-snapshot-review-r3858.json).

## Earlier checkpoint, November 16, 2026

The last fully qualified main commit is `087feddc148b1785129c4958e13e2709dad99e9f`, where all nine Engine jobs and artifact retention passed. The latest pushed commit is `5299e9828990a372084051d87ea0c42a174747b2`. Its Engine run completed with seven successful jobs and two failures. Android create reached the 180-second toolchain-inspection deadline during distribution hashing, with terminal command custody. The cache descendant control recorded UNKNOWN for hosted PGID2106; its exact failing OS operation remains unexposed. That command and the downloaded archive stay held. The proposed cache successor passed a fresh descendant control and source review, but full original controls exited74 with inner custody unexposed. Root withdrew all11 cache integration changes. A bounded source-only admission investigation continues before another actual control run. [Earlier green CI](verification/receipts/terminal-phase-upload-hosted-proof-r3558.json), [current Android failure](verification/receipts/android-current-failure-r3750.json), [current cache hold](verification/receipts/current-cache-hosted-hold-r3730.json).

The actual console browser journey passed: Sign in → Visible → Project A → Builds/fieldlog → admitted input-a → Create. The exact returned ID appeared as Queued, and the fixture verified its durable build/job pair, immutable inputs and revision 0 outside the first 25 seeded rows. The fresh canonical backend and console builds were reused without source changes. All owned tabs and services closed; all four ports are reusable. This is DOM evidence with a synthetic offline provider and an explicit navigation bridge. The original HTTPS login envelope stayed unchanged. Pixel capture failed, and the initial refused context and proxy diagnostic remain recorded. Independent evidence review passed; root accepted this scoped DOM development slice. [Review and root acceptance](verification/receipts/console-browser-root-acceptance-r3664.json). [Actual browser and database evidence](verification/receipts/console-browser-root-r3626.json). Earlier preparation and runtime failures are preserved.

The private public-CLI output path retained a genuine unsigned Simulator app and matching dSYM. Manifest admission was corrected to reject symlink reads. The corrected unfiltered ordinary suite now passed 18 XCTest cases plus 364 Swift Testing cases across 123 declarations, with no failures or skips. All 59 CLI children closed. Exact compiled dependencies and product bytes stayed unchanged; three missing fixtures were supplied at their original compiled paths. Root rehashed the recorded artifacts and raw output. This closes the ordinary-suite prerequisite. Root selected and applied source121 after the authority-membership correction passed independent review. Installed admission passed in normal and optimized Python. The real failed-compiler output branch also passed: one CLI/Xcode build reached the deliberate Swift type error, retained only a failure report and closed both nested commands. [Failure-branch root evidence](verification/receipts/native-output-compiler-failure-root-acceptance-r3744.json). CLI119 and Pair21 history, and canonical backend v27/source338, remain unchanged. [Source121 root adoption](verification/receipts/native-source121-root-adoption-r3788.json). [Retention and manifest review](verification/receipts/public-native-manifest-root-acceptance-r3552.json), [full ordinary evidence](verification/receipts/native-output-ordinary-root-acceptance-r3654.json).

Root applied the reviewed 25-file VM correction to canonical source for development. The 479-file base matches the compiled and reviewed candidate. A later cleanup removed spaces from30 blank lines in one test file; rustfmt output proved the test body unchanged. [Whitespace proof](verification/receipts/VM-test-whitespace-equivalence-r3816.json). All 59 retained test executables ran: 699 passed, zero failed, and 30 existing tests stayed ignored. The genuine Swift UI module validated all 86,451 bodies and produced the original ten-node tree with title revisions 1, 2, 2, 3. Its consuming close returned fourteen zero currents, zero tickets, and no invariant failure. Ordinary negative tests retain 113 invariant flags, which do not establish a blanket clean-ledger result. The earlier R3732 failure was a missing `rustc` on PATH before owner acquisition; the retained replay corrected only that environment. Independent composition review passed. This closes the VM development dependency and permits a fresh AppKit build against the exact qualified library. SDK, native, release and GA acceptance remain pending. The fresh AppKit build passed, but the root native controller failed to import its AX client under Python isolated mode after acquiring PID37558. That process and its resources remain held with ledger and OS closure unproven. The corrected absolute import passed a new isolated-mode, fake-only check before any acquisition. [Native hold](verification/receipts/swift-ui-root-native-hold-r3800.json), [import counterproof](verification/receipts/native-isolated-import-r3802.json), [cache control hold](verification/receipts/cache-original-control-hold-r3810.json). [Root adoption](verification/receipts/VM-development-root-adoption-r3774.json). Historical R3478, R3544 and R3642 holds remain active; these fresh results release none of their resources. [Native hold](verification/receipts/swift-ui-root-native-hold-r3500.json), [profile regression hold](verification/receipts/swift-ui-profile-regression-root-hold-r3550.json), [later regression hold](verification/receipts/swift-ui-stock-full-root-hold-r3700.json).

The genuine unsigned provenance remains a verified subset. Tests, reopen and 474 semantic checks passed. The published versioned CUE itself fails parsing before artifact validation; three targeted semantic negatives passed, but formal schema validation remains pending. The reviewed compatibility report remains blocked by differing source bindings and missing whole-app proof. [Formal validation limit](verification/receipts/native-provenance-versioned-schema-r3588.json), [compatibility evidence](verification/receipts/compatibility-private-root-acceptance-r3514.json).

The binding scope remains all 18 packages in `mixer-product-plan.md`. GA is 0/38 verified. Activation, publication, physical-phone validation, source121 selection and all unreleased holds remain unchanged.

## Continuation: November 15, 2026 — genuine guest execution and direct calls

The exact compiled original FieldLog feature now initializes under official Node/WASI, returns its complete 10-node tree, changes the title, acknowledges an unchanged title, and accepts another title change. The four document revisions were 1, 2, 2 and 3. This is actual guest execution on Node, with no Mixer Runtime or native presentation receipt. [Genuine guest oracle](verification/receipts/genuine-ui-node-oracle-r3234.json).

The private Mixer profile now validates all 86,451 bodies and returns the genuine original 10-node tree within the unchanged work budget. Indexed cache lookup uses 22,037,065 of 64,000,000 cache-work units for startup. A fresh run accepts the title and an identical-byte acknowledgement, with revisions 1, 2 and 2; the next title exhausts the cumulative work budget before revision 3. Both runs consume to 14 zero currents, zero tickets and no invariant. Independent storage review found a P1: smaller admitted modules allocate fewer than 256 slots while wide lookup requires exactly 256. The next experiment addresses that layout mismatch and separates bounded UI-turn execution from retained session resources. No native library is accepted. The subsequent R3394 attempt stopped in an accounting fixture before any genuine payload, leaving ledger closure unknown; its six resource paths remain held. Fresh work uses a separate namespace and only permitted static handoff metadata. The entire older R3252 namespace also remains held with unknown ledger closure. [Startup and cache evidence](verification/receipts/swift-ui-cache-work-r3312.json), [actual title sequence](verification/receipts/swift-ui-genuine-turn-r3376.json), [storage finding](verification/receipts/swift-ui-storage-review-r3374.json).

The reviewed direct-call test is admitted. Its 24 modules passed 48 Node oracles and 96 Mixer executions, each with complete zero-ledger reports; 30 malformed environments were rejected separately. All 58 targets compiled. The original tableless-fixture failure remains preserved. At `2376526f3`, its debug and release parents passed in the complete VM log; per-case CI counts remain source-implied. The CI evidence producer exceeded its review deadline; root independently checked the retained body hash, source and pass lines and preserves that campaign failure. Generated Java separately failed before consumer execution at package trust; its exact rejected predicate remains unexposed. [Root CI evidence](verification/receipts/direct-calls-ci-root-evidence-r3300.json), [package refusal](verification/receipts/generated-java-237-first-failure-r3282.json). [Review and runs](verification/receipts/vm-direct-calls-review-r3220.json), [root admission](verification/receipts/vm-direct-calls-root-admission-r3240.json).

The structured-control test is admitted after changed-fix review. All 30 programs passed both discovery modes, with 60 Node comparisons and 60 complete consuming cleanups. Four controlled mutants prove the old outer-branch cases falsely passed and the fixed cases reject wrong fallthrough; the other 26 binaries and all 30 goldens remain unchanged. The fresh final build compiled all 59 advertised targets. Pinned default rustfmt, backend source selection and CLI119/Pair21 admission pass on the adopted bytes. The original four-target campaign and review finding remain preserved. [Final evidence](verification/receipts/vm-structured-branch-fix-r3396.json), [changed-fix review](verification/receipts/structured-branch-changed-review-r3412.json), [root admission](verification/receipts/vm-structured-root-admission-r3426.json).

The bounded package-trust diagnostic passed independent review and is applied with its exact caller predecessor composition. Installed-workflow admission passes in normal Python and actual `-O`; the 119-file CLI, Pair21 and 338-file backend selections remain unchanged. The trust gate is preserved. A refusal can now expose at most 2,048 UTF-8 bytes of the already returned signature report within the existing single-JSON output cap. The historical rejected predicate remains unexposed; fresh hosted execution is pending. [Independent review](verification/receipts/swift-package-trust-review-r3310.json), [root application](verification/receipts/package-trust-root-application-r3356.json).

Engine CI at `5862a5079` completed successfully in all nine jobs, including generated Java. This is job-level evidence; detailed hosted counts, artifact bindings and inner custody were not inspected. The historical trust-refusal predicate remains unexposed. [CI outcome](verification/receipts/package-diagnostic-ci-result-r3436.json).

The private native provenance producer now emits a genuine 29,434-byte statement for the retained native and symbol archives. Both focused tests, 19 refusal assertions, fresh-process reopen and 474 semantic checks pass. Root rehashed the copied inputs and retained object and matched the executed producer to its prior source review. Coverage remains unsigned `verified_subset`; formal CUE validation, complete build closure, CLI120 and aggregate release eligibility remain pending. [Actual evidence](verification/receipts/native-provenance-execution-r3422.json), [private root acceptance](verification/receipts/native-provenance-private-root-acceptance-r3458.json).

At `00dcaa0bc`, all four workflows passed. Complete VM logs show the lifetime and supplemental indirect-call parents passing in both debug and release. Hosted/isolated logs expose 296 source controls and 12/8/15 constructor executions; serial counts, named runtime traces, compiled manifests and hosted custody remain unexposed or partial. The prior local 910-test regression and real compiler-error join remain separate evidence. [VM proof](verification/receipts/v27-vm-parent-ci-proof-r3216.json), [hosted/isolated proof](verification/receipts/v27-hosted-isolated-proof-r3226.json).

The corrected SBOM unit passed review and retains required SHA1 and SHA256 for all 98 files. It is a verified subset with explicit provenance, license and dependency gaps; aggregate promotion and canonical CLI120 wiring remain refused. No production activation or GA gate is claimed. [Private unit acceptance](verification/receipts/genuine-sbom-private-root-acceptance-r3228.json).

## Continuation: November 15, 2026 — canonical development dispatch v27

The explicit development adapter, worker and ordinary tests are admitted under **v27/source338**. The implementation passed 910 hosted tests with zero failures and two existing Linux-only skips on this Mac before the test-only formatter update below. Source controls passed 296 tests in normal Python and actual `-O`; the final composed packet passed 120 guard refusals per mode and canonical source checks in both modes. The default dispatcher and worker startup remain unchanged. [Guarded admission](verification/receipts/development-v27-root-admission-r3090.json), [full regression](verification/receipts/development-complete-fixtures-full-r3032.json).

The test-only formatter successor is admitted. All 24 assertion nodes and literal bytes are preserved; all production sources remain byte-exact. The final source packet passed 296 controls normally and under actual `-O`, 111 guarded refusals per mode, both canonical source checks and the actual formatter check. [Final admission](verification/receipts/development-v27-format-root-admission-r3160.json), [changed-packet review](verification/receipts/development-v27-format-review-r3150.json).

A fresh canonical-v27 run passed authenticated POST201, restricted Oban processing, one real Swift compiler error, terminal GET/replay200, capacity release and lease clearance. Restart preserved the diagnostic, binding and `starts=1`. One compiler invocation took 7.55 seconds and progressed through 18 bounded drains. All owned resources retired. This proves the compiler-error path, not successful artifact production. [Actual canonical join](verification/receipts/canonical-v27-compiler-join-r3092.json).

The private production artifact has 141 sources, 230 modules and 23 priv files. All 35 constructor controls passed: 20 against actual release modules and 15 with explicit fake composition leaves. No operational production startup or deployment ran. [Artifact qualification](verification/receipts/development-production-r3070.json).

The VM workflow now supplies the explicit Node executable required by the lifetime test. Its earlier hosted failure occurred before Node or VM execution and remains preserved. A reviewed supplemental indirect-call test is admitted with 24 modules and 96 consuming ledger closures; constructor failures were not exercised and reset evidence covers fresh runtimes. At `00dcaa0bc`, all four workflows passed. The actual VM log confirms both lifetime and supplemental indirect-call parents in combined-feature debug and release. Per-case cleanup counts remain source-implied; hosted inner custody is partial. [Scoped CI proof](verification/receipts/v27-vm-parent-ci-proof-r3216.json). [First cause](verification/receipts/globals-lifetime-ci-failure-r3040.json), [indirect-call review](verification/receipts/indirect-calls-review-r3052.json).

All five genuine FieldLog feature files compiled to Wasm, but versioned guest UI admission remains blocked. The 65,980,818-byte module exceeds stock V2 limits; debug stripping still leaves 64,581,241 bytes. Its WASI imports, memory minimum and navigation/list/section document also require a coordinated contract. No UI runtime or title event ran. The selected architecture adds a persistent Swift UI owner and a versioned document codec; implementation is underway. The private owner builds and passes 19 unchanged GuestUI tests plus the original 10-node host-model title oracle, but the genuine module is refused before Runtime acquisition. Its maximum is 783 parameters and 1,575 combined parameter/local slots; the UI-only parameter adjustment then hit the local-slot ceiling. A complete resource-envelope audit is running. Independent review also found action-provenance, error-ownership and no-op-turn defects in this private prototype; their correction is separate from the policy audit. [Policy failure](verification/receipts/swift-ui-profile-envelope-r3186.json), [source findings](verification/receipts/swift-ui-owner-review-r3188.json). Accessibility is enabled; native presentation remains unexecuted. [Preserved admission failure](verification/receipts/swift-feature-ui-implementation-r3118.json). [Current constraints](verification/receipts/development-progress-r3134.json). [Guest UI evidence](verification/receipts/fieldlog-guest-ui-adapter-r3050.json), [measured constraints and budget exception](verification/receipts/guest-ui-admission-ground-r3084.json).

The private genuine SBOM producer now includes required SHA1 and SHA256 checksums for all 98 files. The correction passed its focused tests and independent review. It remains a verified subset with explicit provenance, license and dependency-closure gaps; aggregate promotion and CLI120 adoption remain refused. [Private unit acceptance](verification/receipts/genuine-sbom-private-root-acceptance-r3228.json).

Immutable CLI119, Pair21 and historical metadata remain preserved. CLI120 selection, production activation, publication and all **38 GA gates** remain unqualified. Every historical hold stays active.

## Continuation: November 15, 2026 — real compiler-error integration and globals

The fresh private development join passed authenticated HTTP creation, the restricted Oban processor, an actual Swift compiler error, terminal readback and duplicate replay. Capacity was released and the lease cleared; worker restart retained the diagnostic and `starts=1`. One compiler invocation progressed through 36 bounded drains. Independent review found no issues in this scoped evidence. The development adapter and worker remain private; canonical dispatch and successful seven-artifact completion are still pending. [Actual join](verification/receipts/real-compiler-Oban-join-r2834.json), [review](verification/receipts/real-compiler-Oban-review-r2844.json).

The broader private adapter test found that a malformed configured port exits with `:badarg`. Five focused tests and 80 worker checks passed, but the full suite did not run. The private guard correction passed eight focused tests. Its full run reached 909 passes but failed because the candidate copy omitted two canonical audit golden files. A fresh complete-input run and source review are pending. [Guard and preserved full-run failure](verification/receipts/development-config-fix-r3002.json). [Preserved boundary failure](verification/receipts/development-dispatch-full-r2972.json).

The reviewed globals corpus is admitted: 28 single-entry parities and 24 unsupported-ABI refusals passed in each discovery mode, with 56 consuming cleanups and all 55 advertised targets compiled. A second reviewed test passed same-process lifetime overlap and fresh-instance resets across 12 consuming runtimes, including two traps. Guest instruction interleaving and post-inner reads of outer globals remain untested. Hosted execution of this second test remains pending. [Lifetime/reset evidence](verification/receipts/vm-globals-isolation-r2944.json), [independent review](verification/receipts/vm-globals-isolation-review-r2982.json). [Runtime](verification/receipts/vm-globals-final-run-r2852.json), [review](verification/receipts/vm-globals-review-r2858.json). The complete hosted log at `7c1392dff` confirms that the original globals parent passed in debug and release. Per-case CI counts remain source-implied. [Exact hosted proof](verification/receipts/vm-globals-ci-proof-r2998.json).

Three producer units remain private. Native app and dSYM capture passed its real build and retention checks. The reviewed correction now rejects seven unsupported embedded native formats while preserving supported thin64 images and ordinary resources. Diagnostic-profile guest production passed validation of 79,108 function bodies, actual evaluation, retention and corruption checks. Its two outer test invocations plus nested evaluator count as three. A resource-inventory producer also passed tests against three genuine retained native files. Independent review passed. Two file roles remain unclassified. [Resource-inventory evidence](verification/receipts/resource-inventory-product-r2990.json). Whole-app eligibility, public CLI wiring and the complete seven-artifact set remain pending. [Native changed-fix review](verification/receipts/native-format-review-r2920.json), [guest review](verification/receipts/guest-product-review-r2868.json).

The hosted FieldLog APK passed a fresh Android smoke test: install and launch, save a new entry, force-stop, relaunch, and observe the same title with one saved entry. The owned emulator was API36/arm64 with 4 KiB pages. Both emulator and private ADB server terminated with positive custody evidence; owned AVD and IPC were removed. Existing-entry editing, note persistence, 16 KiB runtime behavior and immutable-package qualification remain pending. An earlier pre-acquisition port refusal was incorrectly classified HOLD; its namespace remains preserved without implying endpoint ownership. [Actual native evidence and cleanup](verification/receipts/fieldlog-android-persistence-r2936.json), [preserved earlier record](verification/receipts/fieldlog-direct-image-r2862.json).

Canonical v26/source335, immutable CLI119, Pair21 and activation remain unchanged. No historical hold is released. GA remains **0/38**.

## Continuation: November 13, 2026 — v26 hosted CI verified

At `ecde901ad53819ad77f1514d2482ce478e541028`, the repaired Phoenix job passed the full hosted suite: **902 passed, 0 failed, 2 existing skips**. All 35 constructor checks passed: 12 trust, 8 secrets, and 15 composition controls with explicit fake leaves. The secret driver reported zero compiler diagnostics and zero fixture startup calls. All 140 product-source bindings match canonical files. The prior missing-driver-dependency failure remains preserved. [Verified hosted log and artifact](verification/receipts/v26-phoenix-ci-proof-r2822.json).

The earlier v26 isolated run proves 290 collector checks and both network methods, with all 335 source rows exact before and after. Its container-cleanup report records three exact IDs removed; inner custody and the local audit of the earlier prepare-container absence remain partial. The current isolated workflow also reports success; its detailed artifact is not requalified here. [Scoped isolated evidence and reader limitations](verification/receipts/v26-isolated-ci-proof-r2816.json).

The constructor-driver correction leaves v26/source335, CLI119, Pair21 and historical metadata unchanged. Restricted processing remains a development slice with modeled compiler failure. Real compiler integration, production activation and all 38 GA gates remain unqualified; every historical hold stays active.

## Previous checkpoint: canonical v26 processor admission

The restricted processor development slice is applied under canonical v26: 335 selected sources, a complete typed inverse to v25's 331 rows, and 33 exact writes. The API keeps its restricted role; the processor uses its own constrained login and a separate lock-only definer. Exact privilege, policy, STRICT and notifier admission checks remain enforced. The existing 19 security controls and four actual Oban drains cover terminal revision 2/fence 2, released capacity, a cleared lease and authenticated readback/replay without extra effects. Compiler failure was modeled. Production configuration and deployment remain pending. [Root admission](verification/receipts/processor-v26-admission-r2802.json), [security and worker evidence](verification/receipts/processor-fixture-final-r2618.json), and [independent fix review](verification/receipts/processor-changed-fix-review-r2626.json).

The exact final hosted suite passed 902 tests with zero failures or invalid tests and two existing Linux skips. Ordinary fixtures now acknowledge a usable read connection, start the membership-expiry scenario while its initial membership is live, and wait for actual expiry within the unchanged product deadline. Positive test acknowledgements have a bounded one-second default; negative waits and product deadlines are unchanged. The lock observer retries the captured nil wait fields within its original bound and still requires exact Lock/advisory evidence. Controlled failures and the earlier full-suite failures remain preserved. [Snapshot counterexample](verification/receipts/authorization-snapshot-expiry-r2790.json), [snapshot correction](verification/receipts/authorization-snapshot-expiry-r2792.json), and [final regression](verification/receipts/ordinary-barrier-fix-r2796.json).

Final collector validation passed 290 tests normally and 290 with actual optimized Python, with 148 refusal controls per mode. Targeted historical reconstruction passed in both modes; it restores all three changed fixture predecessors and rejects corrupted bytes without changing historical manifests or assertions. Both canonical source CLIs confirm v26. The production artifact retains the previously qualified 140 sources, 229 modules, 21 dependencies and 22 priv files; 20 release controls and 15 composition controls used the same archive. Those composition controls use the specified fake leaves. [Source qualification](verification/receipts/v26-source-escalation-r2800.json) and [artifact controls](verification/receipts/processor-composition-helper-r2650.json).

The actual compiler join remains held and unaccepted. All historical custody holds stay active; this slice releases none. Fresh PostgreSQL campaigns were stopped, directly reaped and positively observed absent, with their ports reusable. Native phones remain disconnected. No production activation, signing, store, device or GA acceptance follows. All 38 GA states remain unchanged, with none verified.

## Previous checkpoint: before canonical v26 admission

Canonical authority remains v25 with 331 selected inputs. The private v26 tooling packet passed 290 collector tests in normal and actual optimized Python, both source CLIs, 140 refusal controls per mode, application, inverse and idempotence checks. Root completed the interrupted independent review: fresh module execution, exact-content compilation caching and the four authority assertion updates are sound. No v26 source promotion or activation occurred. [Qualification](verification/receipts/v26-budget-final-r2750.json) and [completed source review](verification/receipts/v26-source-review-r2770.json).

An actual controlled Ecto/PostgreSQL test proved that Repo startup can return while its connection is still inside after_connect. With that gate closed, queue-disabled transaction checkout failed before the callback; a positive SELECT 1 acknowledgement then allowed the same transaction. This proves the primitive, not historical attribution. The optional BEGIN fixture was also formatted with unchanged AST and binary literals. The fresh unfiltered serial suite finished with 901 passed, one failed, zero invalid and two existing skips. The remaining unchanged authorization snapshot test returned authorization_unavailable before its 1100ms sleep completed; the cause remains unproven. The readiness acknowledgement and the admin-only teardown change are private. The v26 source packet still binds the earlier 21-path version, so the final fixture bytes require a new exact binding before application. [Controlled discriminator](verification/receipts/direct-repo-gate-r2772.json), [format proof](verification/receipts/read-format-successor-r2760.json), and [fresh regression](verification/receipts/readiness-full-r2782.json).

The new actual compiler campaign remains unaccepted and held after its restart-readback assertion interrupted PostgreSQL finalization. The separate Repo-gate campaign also has unresolved custody after a failed fast-stop. Two formatter preparations recorded UNKNOWN before an inner identity or compiler/database launch; their namespaces remain preserved. A fresh source proof reproduced the missing launcher global before constructor invocation and verified the corrected context with a real Mix version command. These proofs release no hold. [Compiler hold](verification/receipts/development-compiler-finalization-hold-r2752.json), [Repo hold](verification/receipts/repo-gate-custody-hold-r2766.json), and [launcher proof](verification/receipts/launch-global-proof-r2780.json).

The delivered float-width and reinterpretation corpus has actual combined-feature debug and release parent passes at 8ca67f8. Its 54-target debug compilation and per-case results remain separate local evidence; CI per-case totals are source-implied. Browser submission retains the previously recorded scoped public UI and SQL-pair pass with the synthetic local provider. Neither slice qualifies the whole Engine, W08 or GA. [Hosted VM proof](verification/receipts/vm-float-width-ci-proof-r2758.json).

All 38 GA states remain unchanged, with none verified. Physical phones remain disconnected. Every historical custody hold stays active; no production publication, signing, store, customer or operational acceptance is implied.

## Previous checkpoint: before current readiness and custody evidence

The reviewed float-width and reinterpretation corpus is applied. Its fresh debug build compiled all 54 targets, including the example. Exact and blanket discovery produced 64 Node parity pairs, 128 scalar outputs, 64 consuming cleanups and 32 environment refusals. The first build failure remains preserved. Root formatting, target discovery and source admission pass. Hosted execution of this new corpus remains pending. [Root checks](verification/receipts/vm-float-width-root-r2732.json) and [independent execution](verification/receipts/vm-float-width-review-r2714.json).

The public console submission flow passed against canonical v25. Actual Sign in, admitted input selection and one POST 201 led to the exact returned Queued build, outside the first 25 catalogue rows. SQL proved one matching journal and Oban job with the selected input hashes. Queued has DOM evidence. The later screenshot shows the project-reset state after the session became unauthenticated. All owned services and browsers retired with positive custody and reusable ports. The earlier automation timeout and rejected HTTP fixture URL remain separate failures. This uses a synthetic local identity provider. [Browser and SQL evidence](verification/receipts/console-browser-public-create-r2684.json).

The restricted processor remains private. Its 19 security controls and four real Oban drains passed. The formatted production archive passed 20 release controls and 15 composition controls using the specified fake leaves. Fixture and helper review passed. An instrumented full regression passed 902 tests with two existing skips, without reproducing the earlier unacknowledged BEGIN. Its historical cause remains unproven. [Security review](verification/receipts/processor-changed-fix-review-r2626.json), [fixture review](verification/receipts/processor-fixture-helper-review-r2674.json), [release controls](verification/receipts/processor-composition-helper-r2650.json) and [full regression](verification/receipts/processor-BEGIN-discriminator-r2676.json).

The optional BEGIN diagnostic correction passed source review and handler controls. Its attempted ordinary full run lost Mix's priv directory symlink during build copying, so that run is unqualified. R2728 owns a fresh build and a migration-path preflight. The v26 source packet is also unaccepted: both final collector modes reached the 120-second alarm after 247 completed methods. R2726 profiles that work before any limit change. Product promotion, source selection and activation remain pending. [Diagnostic correction](verification/receipts/BEGIN-diagnostic-optional-fix-r2702.json), [changed-fix review](verification/receipts/BEGIN-optional-fix-review-r2716.json) and [partial source packet](verification/receipts/restricted-processor-source-v26-r2694.json).

The real compiler join remains held after nested custody became UNKNOWN with an unexposed PID and PGID. Its deadline correction passed independent source controls, but no terminal compiler integration follows. A fresh owned Darwin experiment observed EPERM for a proven unreaped zombie and ESRCH after exact reap. That experiment releases no historical hold. The prospective CLI change passed independent source review. Kernel evidence covers its POSIX adapter, while full controller sequencing remains synthetic. CLI119 and Pair21 remain unchanged. [Compiler hold](verification/receipts/development-compiler-custody-hold-r2654.json), [deadline review](verification/receipts/development-deadline-review-r2658.json) and [owned Darwin control](verification/receipts/darwin-zombie-observation-r2698.json).

Engine run 43490106127 reports all nine jobs successful at 75e77360e576e7d084e771ef63e5448e0b52677d. The arithmetic parent has actual debug and release passes; its per-case CI totals remain source-implied. This does not qualify the whole Engine or W08. All 38 GA gate states remain unchanged, with none verified. Physical phones remain disconnected and every specific custody hold stays active. [Engine metadata](verification/receipts/arithmetic-head-ci-metadata-r2718.json) and [arithmetic execution](verification/receipts/vm-arithmetic-ci-proof-r2640.json).

## Previous checkpoint: before float-width delivery and browser submission evidence

The returned-memory diagnostic correction is applied. Bootstrap now includes bounded inner_hold and hold-persistence errors in its existing single JSON stdout line; stderr, UNKNOWN/exit74 policy and custody deadlines are unchanged. Its exact caller successor restores the complete prior R2426 bytes and earlier renderer/Play119/immutable118 contracts. All 161 existing controls pass normally and with actual optimized Python, including 41 unchanged bootstrap tests; independent review found no blocking defect. Canonical installed caller and source admission pass in both modes, and the actual canonical memory sentinel retains both errors. Six policy entries change only blob/size, with all other policy bytes and the 1 GiB budget preserved. Fresh hosted execution of the new diagnostic remains pending. [Root application](verification/receipts/inner-hold-diagnostic-root-r2588.json) and [independent review](verification/receipts/inner-hold-diagnostic-review-r2580.json).

Delivered comparison coverage now has actual combined-feature debug and release parent passes for both integer and floating comparisons at `34c2f6c63`. The complete 3,916,456-byte log matches Content-Length and SHA256. Per-case markers are absent: 64 integer parities, 672 floating i32 results, 112 cleanups and 48 environment denials remain source-implied in CI; the local per-case receipts remain separate. The first filtered-log read failure is preserved. [Complete CI proof](verification/receipts/vm-comparisons-ci-complete-r2574.json).

The restricted processor's frozen candidate passed the named real PostgreSQL/Oban join: restricted admission, four drains, failed revision2/fence2, capacity released, lease cleared, GET200 and replay200 with no extra effects. It remains private and unaccepted. Independent review found two P2 gaps: STRICT-function drift is omitted from admission, and the separate notifier backend bypasses Repo admission. Extra drift/quota/cross-organization/rollback controls were not executed. R2586 stopped before controls on incorrect locker-role projections; R2594 corrected those projections but its raw UUID logger failed. R2606 repaired and exercised that logger, then passed 16 of 19 live groups: baseline/STRICT/NULL locking, privilege and policy drift, and forbidden writes. Three fixture prerequisites still prevented fleet counting and notifier connections. R2618 passed all nineteen controls and the unchanged positive join with four actual Oban drains after those fixture corrections. Notifier initial/reconnect admission, transactional delivery, fleet counting and successor rollback now have actual evidence. All fifteen product afterimages remain private while R2626 performs the changed-fix review. [Final runtime evidence](verification/receipts/processor-fixture-final-r2618.json). [Actual partial controls](verification/receipts/processor-logger-escalation-r2606.json). [Positive join](verification/receipts/restricted-processor-admission-r2576.json) and [findings](verification/receipts/restricted-processor-source-review-r2578.json).

Source authority remains v25/331 with digest `f8b6be3e87cb50f8c5bb5dc02616e0bfbd63a6e99c54d8446774db1c9699fa62`; CLI119, Pair21 and immutable118 remain exact. Full v25 hosted tests remain 900 passed, zero failures, two existing skips. Engine metadata at `34c2f6c63` reports all nine jobs successful. The earlier `681ca7a4a` release-export PID/PGID18165 is still UNKNOWN and held; no later success releases it or recovers its exception/errno. No held resource was inspected, signalled or retried.

GA remains 0/38. Production processor/notifier/reconnect qualification, real compiler/provider integration, deployed queue liveness, immutable packages and the specified final acceptance matrix remain pending. Physical phones remain disconnected and all historical holds remain active.

The diagnostic/caller successor is published at `9f31f5444`; fresh Engine metadata records all nine jobs successful. Actual host evidence confirms installed admission before and after the prospective compiler step, plus 8 XCTest and 208 Swift Testing SDK passes, 69 Updates, 123 CLI and 68 CLI-build Python checks. Returned verification JSON, private-control counts, optimized host runs and inner custody remain unexposed. The read-only proof exceeded its 240-second delivery bound. [Scoped host acceptance](verification/receipts/diagnostic-hosted-root-r2622.json). The earlier held export remains UNKNOWN. [Delivery](verification/receipts/inner-hold-diagnostic-delivery-r2590.json).

Integer arithmetic now has an independent source review and both discovery modes: 32 modules per mode across twelve i32/i64 wrapping and bitwise operations, 64 consuming cleanups and 18 pre-payload environment refusals. The initial collector failure remains preserved. Final default-rustfmt source is now qualified and installed in the worktree: all 53 targets compile, both fresh discovery modes pass, all 64 runtimes consume cleanly, and all 32 module byte strings match the reviewed source. Only whitespace and 33 trailing commas changed. Canonical staging and publication follow the final guard. [Formatted proof](verification/receipts/vm-arithmetic-format-final-r2614.json). [Independent review and blanket run](verification/receipts/vm-arithmetic-review-blanket-r2602.json).

The next compiler boundary is selected: an explicitly configured development Dispatch adapter, separately authorized exact-spec source registration, and a real public-compiler diagnostic through the durable Oban completion path. R2610 is implementing that slice; source grounding exceeded its time bound and is recorded as such. This does not qualify hostile customer execution, a production provider or successful build artifacts. [Grounding](verification/receipts/real-compiler-boundary-r2598.json).

## Previous checkpoint: before reviewed inner-hold diagnostic application

## Continuation: November 13, 2026

Two independently reviewed consuming comparison corpora are applied. Integer coverage exercises all 22 i32/i64 comparison opcodes through 32 distinct modules per run: 64 Node parities, 64 consuming cleanups and 18 environment denials across exact and blanket discovery. Floating comparison coverage exercises f32/f64 equality and ordering, signed zeros, infinities and unordered NaNs: 24 distinct modules per run, 672 exact i32 results, 48 cleanups and 30 environment denials. Every recorded runtime finishes with fourteen zero currents, zero tickets and no cleanup invariant. Each slice had one independent debug build compiling all 51 targets; the composed 52-target inventory is admitted but was not rebuilt at root. Full-suite/release/hosted execution of these two additions remains pending. [Root acceptance](verification/receipts/vm-comparisons-root-r2540.json), [integer review](verification/receipts/vm-integer-comparisons-review-r2536.json), and [floating review](verification/receipts/vm-float-comparisons-review-r2538.json).

Final formatted v25 is delivered at `681ca7a4a`: 331 selected paths and digest `f8b6be3e87cb50f8c5bb5dc02616e0bfbd63a6e99c54d8446774db1c9699fa62`. Actual Phoenix CI proves 900 passed, zero failed, two existing skips; the named customer-create/replay/final-expiry case and 12 trust, 8 secret and 15 composition checks pass. All four product identities match the hosted receipt and archived source bytes. Hosted before/after snapshots are not exposed in that artifact. [Delivery](verification/receipts/customer-authz-v25-delivery-r2518.json) and [hosted proof](verification/receipts/v25-phoenix-ci-proof-r2534.json).

Actual isolated-network CI at the same head proves 283 collector controls under the 120-second bound and K03 plus combined IS04/IS05 with no skips or exclusions. All 331 pre/post source rows and compiled BEAM bindings match. The four changed modules are not in the loaded snapshot, so their execution is not inferred from isolated evidence. Three exact containers are absent; hosted inner process custody remains partially unexposed. [Isolated proof](verification/receipts/v25-isolated-ci-proof-r2526.json).

Delivered v24 host evidence is also retained separately: Debug and Release producers and all six Java consumers pass, each recording 21 sources, 232 classes and 5,610 member references. Swift host execution passes 8 XCTest plus 208 Swift Testing SDK tests, 69 Updates tests and 123 CLI tests, with normal source/caller controls; bootstrap and optimized runs are unexposed. No broader native/package qualification follows. [Android consumers](verification/receipts/generated-java-green-proof-r2512.json) and [Swift host](verification/receipts/swift-green-proof-r2514.json).

The restricted processor design is selected, preserving Ecto.Multi with a lock-only SQL helper and explicit denial of capacity updates. R2550 actually passed the minimal PostgreSQL permission probe and one strict compile, but the full join never ran: probe teardown batched DROP DATABASE in a transaction, and the second compile failed on an unused ACL checker. The final one-line call and two constructor-fixture corrections remain uncompiled/unrun (initial constructors 29/31). The probe's pair table was not the canonical composite-key schema. A fresh R2562 campaign is compiling final source and executing the full migrated-schema worker join; none of the private processor code is admitted. [Partial evidence](verification/receipts/restricted-processor-implementation-r2550.json).

Engine job metadata at delivered head `34c2f6c63` now reports all nine jobs successful. Actual comparison-parent debug/release proof is being collected separately; job success alone does not expose per-case rows or establish whole-Engine acceptance. The preceding `681ca7a4a` generated-Java job reported UNKNOWN custody for release-export PID/PGID 18165. That hold is recorded in AGENTS.md; no artifact was downloaded and no held resource was inspected or released. Its exception/errno remain unexposed. A memory-only discriminator reproduced the bootstrap's omission of the runner-populated inner_hold error. R2566 is qualifying the bounded diagnostic and exact caller-admission correction. The later green run does not release the earlier hold. [Hold and synthetic proof](verification/receipts/generated-java-release-export-hold-r2560.json).

No production activation or GA acceptance follows. Restricted production processing, real compiler/provider integration, deployed queue liveness, immutable-package qualification and all specified final GA checks remain pending. Physical phones remain disconnected and every historical custody hold remains active; GA stays 0/38.

## Previous checkpoint: before comparison coverage and final v25 CI proof

## Continuation: November 13, 2026

The formatted authorization correction is applied as source v25: 331 selected paths, four product replacements and 327 unchanged rows, with a complete typed v24 inverse. Build creation initializes Read Committed before taking the early exclusive authorization lock; Session remains byte-exact. All five root acceptance conditions passed. Canonical source and installed caller admission pass normally and with optimized Python. [Root review](verification/receipts/customer-authz-v25-root-review-r2510.json) and [adoption](verification/receipts/customer-authz-v25-root-adoption-r2516.json).

The exact formatted sources pass the original HTTP module's two cases and return 201 under Read Committed, Repeatable Read and Serializable connection defaults. Concurrent replay, physical transaction evidence, failed-INSERT rollback/retry, post-INSERT expiry, missing scope and revocation assertions pass. A fresh production release passes 35 controls: 20 use release modules and 15 use the specified composition leaves. The earlier unformatted full suite passed 900 tests with two existing Linux skips; formatter AST and binary-literal equality carries that evidence forward. Fresh final v25 full CI remains pending. [Formatted runtime](verification/receipts/customer-authz-formatted-runtime-r2496.json) and [release](verification/receipts/customer-authz-formatted-production-r2498.json).

V25 collector admission passes 283 tests in normal Python and 283 in actual optimized Python, plus 32 guarded-apply refusals per mode. Historical validator bytes, CLI119, Pair21, immutable118 and the 1 GiB artifact budget remain exact. Two preparation failures and their corrections remain preserved in the producer packet; two root review-script failures are also preserved. No historical custody hold was released.

Observed hosted evidence at delivered v24 head `0e8c97d3d` is green: Phoenix ran 900 passing tests with two skips and 35 constructor/composition checks. Isolated-network execution passed K03 and combined IS04/IS05 without skips; all 276 collector tests completed in 53.266 seconds under the 120-second allowance. Exact source331 bindings and three-container absence are recorded; inner process custody remains partially unexposed. [Hosted proof](verification/receipts/v24-green-ci-proof-r2486.json).

Float arithmetic now has actual combined-feature debug and release parent passes at the same delivered head. Its 320 scalar comparisons, 40 cleanups and 30 environment denials remain source-implied in CI; local per-case evidence remains separate. This does not qualify the entire Engine or W08. [CI proof](verification/receipts/vm-float-arithmetic-ci-proof-r2508.json).

The private customer-create-to-worker join remains accepted for development: four real Oban drains, terminal failed readback and duplicate replay passed under explicit privileged fixture authority with a modeled compiler failure. Restricted production processing, real compiler integration, provider provenance, production activation and the specified GA matrix remain pending. Physical phones remain disconnected; GA stays 0/38.

## Previous checkpoint: before formatted v25 admission

## Continuation: November 13, 2026

The independently reviewed float-arithmetic corpus passes 320 Node scalar comparisons across two runs of 20 original modules. Results include 196 exact-bit, 72 canonical-NaN, and 52 permitted arithmetic-NaN comparisons. All 40 consuming runtimes finish with fourteen zero currents and zero tickets; 30 malformed environments are rejected before payload. One debug build compiled all 50 manifest targets, but the full suite was not executed. [Root acceptance](verification/receipts/vm-float-arithmetic-root-r2464.json) and [independent review](verification/receipts/vm-float-arithmetic-review-r2452.json).

Complete delivered scalar-memory CI output now proves actual combined-feature debug and release parent passes at `ae5c399a8`. Its 48 comparisons, 48 cleanups, and 30 denials remain source-implied in CI; local per-case evidence remains separate. The complete log is 3,903,203 bytes. [CI proof](verification/receipts/vm-memory-access-ci-proof-r2434.json).

The diagnostic caller repair is applied. Canonical installed admission passes normally and with optimized Python, preserving the exact Pair21, Play119 and historical118 inverse. The complete merged collector suite passes 276 tests in each mode with no skips. The separate caller matrix passes 161 existing tests and 10 negative controls per mode. Fresh hosted confirmation of the caller repair and 120-second aggregate collector allowance remains pending. [Root review](verification/receipts/diagnostic-caller-root-r2442.json) and [composed controls](verification/receipts/composed-ci-repair-r2462.json).

The collector suite now has a bounded 120-second aggregate allowance within the unchanged 15-minute CI job. The failing hosted run completed 240 methods before its former 50-second alarm; no Docker operation began. All 276 test bodies and assertions are unchanged. The original baseline and both candidate Python modes pass locally. The active-method profile identifies repeated cold sparse-source imports, but hosted sufficiency of 120 seconds remains unverified. [First cause and local evidence](verification/receipts/v24-isolated-ci-failure-r2394.json) and [root selection](verification/receipts/collector-alarm-root-r2422.json).

Scalar-memory coverage and the completed private worker join are delivered in `ae5c399a8`. Artifact retention passed for that commit; its Engine run was still in progress at observation. [Delivery and exact source](verification/receipts/vm-memory-access-delivery-r2412.json).

Commit `a82cc695d` delivers the v24 corrections. Complete Console CI output proves 277 unique passes, zero failures, and zero skips. Artifact retention passed. Phoenix and isolated-network CI failed and have separate first-cause investigations; Engine CI finished with six successful jobs and three failed jobs. Generated-Java debug-create hit its 180-second bundled-inspector deadline with terminal custody; the slow phase is unproven. Swift host admission rejected a stale diagnostic-bootstrap caller pin; its aggregate inherited that refusal. Canonical caller/predecessor admission now passes in both Python modes; hosted Swift execution remains pending. [Delivery](verification/receipts/ci-discovery-expiry-delivery-r2390.json) and [actual Console proof](verification/receipts/console-discovery-ci-r2406.json).

The new scalar-memory corpus passed 48 independent Node comparisons across 24 original modules, including 38 values and 10 bounds traps. All 48 consuming runtimes ended with fourteen zero currents and zero tickets. Thirty malformed environments were refused before execution. Independent source and evidence review passed. This is local macOS debug evidence; combined-feature CI remains pending. [Root acceptance](verification/receipts/vm-memory-access-root-r2410.json) and [review](verification/receipts/vm-memory-access-review-r2398.json).

Canonical browser v24 contains the reviewed console discovery, source-ordering, and expiry-fixture corrections. Ordinary console discovery passes 277 tests. The expiry fixture passes the full hosted suite with 900 passes, zero failures, and two existing Linux skips. All 276 source controls pass in each Python mode, and both canonical source checks pass. The 331-source digest is `31f1bb54cacceda486cae725d4d10091aa024a900ba3998b3a47c96ba8222027`. [Root adoption](verification/receipts/customer-expiry-source-root-adoption-r2380.json) and [expiry runtime proof](verification/receipts/customer-create-expiry-fix-review-r2342.json).

Generated-Java diagnostics preserve the existing single JSON stdout line and empty stderr. The result includes bounded failure metadata captured from returned memory before validation and flushed before final receipt persistence. All 41 unchanged bootstrap tests pass normally and with optimized Python. CI preserves eight metadata files first and uploads 48 durable consumer outputs only on success. [Reviewed correction](verification/receipts/generated-java-diagnostic-final-r2374.json) and [root application](verification/receipts/generated-java-diagnostic-root-r2382.json).

At `0cd921110`, all nine Engine jobs and artifact retention passed. The fresh Java/D8 job proves two Swift producers, six Java/D8 consumers, 12 refusal controls, 92 terminal outer commands, and six terminal inner CLI receipts. The earlier exit-74 job remains UNKNOWN and held. Actual float-rounding parents passed in combined-feature debug and release; per-case CI totals remain source-implied. [Consumer evidence](verification/receipts/generated-java-six-consumer-ci-r2372.json), [rounding evidence](verification/receipts/vm-rounding-ci-proof-r2368.json), and [unchanged old hold](verification/receipts/generated-java-hosted-hold-r2350.json).

The full private customer-create-to-worker join passed. Four real Oban drains reached failed revision 2 and fence 2, released capacity, and cleared the lease. Live GET 200 and duplicate POST 200 returned the same build with no additional jobs or domain events. Root verified 285 current source bindings, 51 raw evidence files, and all 14 terminal command records. Compiler failure remains modeled, and processor authority is an explicit superuser-session/schema-owner fixture. A restricted production processor, actual compiler, and ordinary-CI packaging remain pending. [Runtime evidence](verification/receipts/customer-create-worker-final-replay-r2384.json) and [root acceptance](verification/receipts/customer-create-worker-root-r2392.json).

At delivered customer-create commit `5e6dd01a5`, Console CI ran 219 tests and artifact retention passed. Isolated-network runtime preparation failed on source-map ordering. The full Phoenix suite passed 899 tests and failed one missing INSERT-witness assertion, with two existing skips; the early-expiry discriminator and a test-only successor are separate. Eight engine jobs passed; the generated-Java consumer job ended exit 74 with unproven hosted custody and no retained artifact. That exact hosted chain remains held. [Hosted failure](verification/receipts/hosted-v22-ci-failure-r2322.json) and [new scoped hold](verification/receipts/generated-java-hosted-hold-r2350.json).

Mixer commit `21f4894db` delivers the reviewed browser v21 composition and consuming integer-division corpus; browser source commit `d5ae01a63` is its parent. All five workflows at that head completed successfully. Complete logs prove 219 console tests, typecheck/build, 20 constructor checks, 15 composition checks with fake leaves, and integer differential parent passes in combined-feature debug and release. Full hosted-suite and JSON HTTP counts are not exposed by those logs. [Delivered CI evidence](verification/receipts/v21-main-ci-proof-r2104.json).

The preceding delivered browser v21 selected 290 inputs, digest `13cbf07d04bcbceaaaebb6278166bc18630e4d63f0fcf9857bca3e7319203463`. The separate fresh local serial suite passed 881 tests, zero failures and two existing Linux-network-namespace skips. Production release closure passed for 130 sources, 216 modules and 21 dependencies, with 35 constructor/composition controls and 288 package rejections. Composition uses specified fake leaves; deleted pre-strip inputs are bound through retained hash-pinned evidence. Configured database Application startup has its separate scoped proof. Operator activation, external-provider provenance and deployment remain unqualified. [Full suite](verification/receipts/hosted-v21-full-r2070.json), [release closure](verification/receipts/hosted-release-closure-r2086.json) and [configured startup](verification/receipts/configured-project-r1874.json).

The delivered sign-in and retained-status behavior is accepted: real Sign in → Queued → Refresh → Failed, 11 joint HTTP tests, 219 frontend tests and a separate session-reset adversarial case. The raw browser-driver text-expectation failure remains preserved. The publication clock correction retains the original deadline and expiry/rollback safeguards; historical R2004 causation remains unproven. [Browser acceptance](verification/receipts/console-signin-runtime-acceptance-r1996.json), [status review](verification/receipts/console-coherence-final-review-r2028.json) and [clock correction](verification/receipts/build-read-correction-r2060.json).

Mixer commit `72c48190d` delivers the collector entrypoint correction. Fresh hosted job 131773840120 actually ran and passed all 258 source controls, including all twelve cases in the two formerly undiscovered classes; its complete 70,639-byte log is retained and length/hash verified. The exact block move also passed all 258 tests locally under actual optimized Python. Test bodies, the 50-second alarm, v21 source authority, CLI119 and Pair21 remain unchanged. All four workflows at that head completed successfully. The separate artifact audit below records actual Linux execution and its remaining custody limits. [Actual hosted discovery](verification/receipts/collector-entrypoint-ci-r2118.json), [discovery correction](verification/receipts/collector-entrypoint-fix-r2106.json) and [root application](verification/receipts/collector-entrypoint-root-r2110.json).

The cache descriptor guard delivered at `8f15463b3` now has selected actual CI evidence: 36 original controls pass in each Python mode, and all 103 compiler-fixture commands have positive reap, group absence, both EOFs and descriptor/selector closure. Its 57 zero exits and 46 expected compiler rejections match their contracts; UNKNOWN/HOLD count is zero. Immediate EPERM → UNKNOWN remains unchanged. Individual original-control custody is not exposed by their summaries; full compiler qualification and every historical hold remain pending. [Bounded selected-artifact proof](verification/receipts/cache-fd-selected-proof-r2094.json).

FieldLog main `552559d2d` now has its first accepted hosted public-recipe Android build/export: run 43377874896, job 131728522099. All 90 source files, CLI119/Pair21/SDK bindings and provenance match. The unsigned APK is 28,713,599 bytes, SHA-256 `dd013f35f6adf068c9cdae7d30f4ca14102c12fd506f82d87d9219838211f5a9`; the source ZIP is 1,513,092 bytes, SHA-256 `8b387259427b17ef4d1a32187296ad02e945799ec88a230ee638981db78a8c32`. Static manifest/DEX checks and all 18 AArch64 libraries pass, including 16 KiB ELF alignment. This APK has no new runtime result. The older API36 chooser/recipient 179-byte equality remains separate development evidence. [Hosted artifact acceptance](verification/receipts/fieldlog-hosted-artifact-r2098.json) and [older native review](verification/receipts/public-report-result-review-r1924.json).

Mixer commit `168648626` delivers the reviewed integer-bit corpus: 32 original consuming cases across i32/i64 leading/trailing-zero counts, population counts, shifts and rotations. Its exact-parent and blanket-ignored runs passed 64 independent Node comparisons and 64 consuming cleanups, each with fourteen zero currents and zero tickets; 18 invalid environments were rejected before payload execution. Independent source/evidence review passed. This is local macOS debug evidence; both Engine and retention CI pass. The complete 3,886,671-byte VM log proves actual combined-feature debug and release parent passes; per-case CI totals remain source-implied. [Delivery](verification/receipts/vm-integer-bits-delivery-r2130.json) and [complete CI proof](verification/receipts/vm-integer-bits-ci-r2132.json). [Producer](verification/receipts/vm-integer-bits-r2116.json), [independent review](verification/receipts/vm-integer-bits-review-r2122.json) and [root acceptance](verification/receipts/vm-integer-bits-root-r2124.json).

Selected retained v21 network artifacts prove K03 and the combined IS04/IS05 method actually executed on Linux: two passed, zero failed/skipped/excluded. Exact test/PG container absence and fixture cleanup are recorded. Inner PID/PGID/ESRCH traces and eight consolidated-module bindings remain unexposed, so full custody acceptance is partial. This does not qualify an external provider or deployment. [Runtime evidence and limits](verification/receipts/v21-isolated-runtime-proof-r2120.json).

Mixer main `658fd3034` delivers the independently reviewed integer-width corpus: 32 original consuming modules covering i32 wrap, signed/unsigned i64 widening and all five sign-extension operations. Exact-parent and blanket-ignored execution passed 64 Node comparisons, 64 consuming cleanups and 18 pre-payload environment rejections. All 46 manifest targets were admitted; the new integration target and its implicit library/binary artifacts were compiled. The complete 3,890,825-byte VM log now proves actual combined-feature debug and release parent passes. Per-case CI counts remain source-implied; local observed evidence stays separate. [Complete delivered CI proof](verification/receipts/vm-integer-width-ci-r2174.json). [Delivery](verification/receipts/vm-integer-width-delivery-r2161.json). [Producer](verification/receipts/vm-integer-width-r2150.json), [independent review](verification/receipts/vm-integer-width-review-r2152.json) and [root acceptance](verification/receipts/vm-integer-width-root-r2160.json).

The independently reviewed float-selection corpus adds 32 original f32/f64 min, max and copysign modules. Both discovery modes passed: 48 exact-bit comparisons and 16 comparisons against the specified NaN result classes, with 64 consuming cleanups at fourteen zero currents and zero tickets. Thirty malformed environments were refused before payload execution. All 47 manifest targets were admitted; one fresh debug build compiled the library, CLI binary and new test. Published in Mixer `33ae3ab60`; complete delivered CI logs prove combined-feature debug and release parent passes. CI per-case totals remain source-implied; local evidence stays separate. [Actual CI proof](verification/receipts/vm-float-selection-ci-r2234.json). [Delivery](verification/receipts/vm-float-selection-delivery-r2198.json). [Producer](verification/receipts/vm-float-selection-r2178.json), [independent review](verification/receipts/vm-float-selection-review-r2186.json) and [root acceptance](verification/receipts/vm-float-selection-root-r2196.json).

The independently reviewed float-rounding corpus adds 32 original modules covering f32/f64 ceil, floor, truncation and nearest ties to even. One fresh debug build and both exact and blanket ignored discovery passed 352 scalar comparisons: 288 exact-bit results and 64 allowed-NaN results. All 64 runtimes consumed cleanup with fourteen zero currents and zero tickets; 30 malformed environments were refused. The producer's earlier type-error build remains preserved, and the corrected bytes were compiled and executed by the independent reviewer. Other manifest targets were source-admitted only. CI/release and W08/GA qualification remain pending. [Independent execution](verification/receipts/vm-float-rounding-review-r2320.json) and [root acceptance](verification/receipts/vm-float-rounding-root-r2334.json).

Customer build submission is now delivered and now admitted by canonical browser v23: sign in, choose an admitted input, submit, and view the exact queued build independently of the first catalog page. The final backend composition passed 900 tests with zero failures and two existing Linux skips; the admitted-input HTTP module passed 6/6. The console's 277 tests, typecheck and build passed on the exact composed bytes. [Composition](verification/receipts/customer-console-composition-r2274.json) and [console review](verification/receipts/console-submit-state-review-r2258.json).

The actual local browser flow passed against Phoenix and PostgreSQL. A public Sign in used the original HTTPS authorization URL with a controlled provider bridge and real callback/cookie. Selecting input-a produced one POST 201, one new queued journal and one job; the returned build remained visible despite falling outside the first 25 catalog rows. Cleanup confirmed browser/backend process termination and port reuse. External identity-provider and TLS qualification remain separate. The preceding timed-out root attempt and its command-registry collision are preserved as failures. [Browser and SQL evidence](verification/receipts/console-create-browser-root-r2294.json).

The preceding v22 authority selected 331 inputs, digest `aed55457231b1e9a2191c071f2b718bd7f271addf892e209602f38873587089c`, with a complete typed inverse restoring all 290 v21 rows. All 57 guarded writes match their reviewed afterimages, and 598 preserved bindings remain exact. Producer source controls passed 268/268 in each Python mode; canonical source checks now pass in normal and actual optimized Python. CLI119, Pair21, immutable118 and the 1 GiB artifact budget are unchanged. Staging checks, coherent delivery and fresh hosted CI are next. [Source review](verification/receipts/customer-create-source-review-r2292.json) and [root adoption](verification/receipts/customer-create-root-adoption-r2300.json).

The optional create repository now participates in strict browser configuration and connection accounting. Its independent review passed; its earlier full suite passed 894 tests, zero failures and two existing skips. The final composition also passed a fresh strict production compile/release and 35 controls: 137 sources, 225 modules, 21 dependencies and 21 exact priv files. Twenty constructors used stripped release modules; fifteen composition controls used isolated leaves. Fixture exports and test support were absent. This artifact evidence does not qualify activation, deployment or external-provider provenance. [Final release proof](verification/receipts/customer-console-production-r2296.json). Activation, deployment, external-provider provenance and every GA gate remain unqualified. [Configuration review](verification/receipts/customer-create-runtime-review-r2272.json).

All W01–W18, G01–G38 and D0–D8 requirements remain binding; zero GA gates are verified. No historical hold is released. Report/photo budgets remain exhausted, phones stay disconnected, and frontend-dependent iOS Simulator tests remain pending. [Current checkpoint](verification/receipts/continuation-checkpoint-r2262.json).

## Previous checkpoint

Private provider work remains unadopted. R1576 passed 12 pure constructor cases; R1578 independently passed one adversarial test covering 71 rejection cases. R1586 passed the actual KeyOwner lease and generation-fencing test. These results do not qualify ProviderOwner lifecycle or configured production startup. [Constructor](verification/receipts/production-browser-admission-r1576.json), [independent review](verification/receipts/provider-trust-review-r1578.json), and [KeyOwner result](verification/receipts/provider-trust-official-context-r1586.json).

R1590 requested changes after reproducing P2: 16 old workers survived permit release and overlapped 16 replacements against capacity 16. Its review batch also failed a cleanup assertion. R1592 remains incomplete. R1594 passed two selected ProviderOwner-death and reaper controls, but remains REQUEST_CHANGES: the broader cross-KeyOwner replacement race is source reasoning without runtime verification, and the changed fix has no independent acceptance. Root reports an R1596 review-provider refusal with no verdict; no completed R1596 receipt was available when this checkpoint froze. Constructor and provider afterimages remain private, and canonical v15/272 plus CLI118 remain unchanged. Production startup still refuses; activation and all 38 GA gates remain pending. [P2 review](verification/receipts/provider-owner-lifecycle-review-r1590.json), [incomplete fix](verification/receipts/provider-worker-crash-fix-r1592.json), and [selected controls and remaining gate](verification/receipts/provider-permit-owner-r1594.json).

Main is 64bd540a044766c4d4e2b30485dcf9e9546afd2d, source272/v15. Root applied the guarded32-path packet and fast-forwarded the exact tested commit from c87d5011. The private unfiltered hosted batch passed854 tests with2 skipped; all856 names were unique. All24 hosted inputs and272 selected source identities match. Format, warnings-as-errors compilation, release admission, protocol45, storage24 and migration1 passed; release warnings remain recorded. At15:56:28UTC, actual main had four successful workflow runs and all12 jobs passed, with0 failed or pending. The Swift job materialized and passed. This is run/job status evidence; the private854/2 counts remain separately sourced. [Terminal main CI](verification/receipts/ordinary-browser-main-terminal-r1572.json). The preceding c87 main run finished12/12 green. [Adoption](verification/receipts/ordinary-browser-adoption-r1566.json), [full hosted result](verification/receipts/ordinary-browser-full-result-r1556.json), and [preceding main result](verification/receipts/typed-queue-and-package-results-r1548.json).

The ordinary Application/Endpoint graph and initial owner-only queue seam are now delivered. Focused11/11 and the full suite passed: original9 Application cases, real-owner early release and deadline refusal. The bounded synchronous history classifies the original failed BEGIN as db_connection_error; records stayed identical after release and the observed251ms interval, with the same unavailable generation and HTTP503/no cookie. No strict millisecond ordering or longer-horizon retry claim is made. Product guards, original5s deadline, request queue:false, scopes, grants and migrations remain unchanged. Production configured startup still refuses pending real resolver, provider trust and secret custody. [Typed evidence](verification/receipts/typed-queue-and-package-results-r1548.json) and [independent review](verification/receipts/ordinary-browser-review-r1534.json).

Current-source admission passed219 normal controls,219 actual optimized controls and the public v15/272 CLI. The32-path inverse/apply proof passed; protected CLI118, provider4, TypeScript12, production migrations and historical v14 authority remain exact. [Source qualification](verification/receipts/ordinary-browser-current-source-r1540.json) and [formatted inputs](verification/receipts/ordinary-browser-formatted-source-r1542.json).

The separate private Android package-closure run passed debug/release producer and create boundaries plus all six generated-Java host consumers. The selected checkout adds55 exact package inputs; inspection remains180s and historical118 authority is unchanged. This is host cross-compilation evidence: no API28 runtime, signed APK, immutable package or physical-device acceptance. The original timeout cause remains unproven, and diagnostic source has not been adopted. [Actual package result](verification/receipts/typed-queue-and-package-results-r1548.json).

Console208 business cases, strict TypeScript, production Vite and genuine compiled cookie HTTP joins remain scoped passes. Synthetic visual row ordering and handler query-key evidence passed, but the retained image still showed Choose a build; a later browser attempt timed out. Installed visual acceptance remains incomplete. [Visual limits](verification/receipts/console-fixture-ordering-r1510.json) and [browser attempt](verification/receipts/console-settled-browser-r1516.json).

VM200M/private256M failures remain red. Final384M is unexecuted: the latest capacity sample failed the unchanged swap rule, and its single authorized continuation missed the inherited Cargo cutoff without resetting the deadline. Rust remains27, with no new runtime owner or hold. About451MB of obsolete owned compiler outputs were removed; source packets, raw evidence and retained replay binaries hash-match, and the filesystem later reported17GiB free. All historical holds remain protected; phones remain disconnected. Production activation, native/immutable packages, operations and all38 GA gates remain pending. [Expired execution window](verification/receipts/final-private-window-r1560.json) and [cleanup](verification/receipts/owned-obsolete-build-cleanup-r1564.json).

## Development execution update: November 9, 2026

The user authorized removing verification bottlenecks. [Product-plan section 24.5](mixer-product-plan.md#245-development-tests-must-advance-application-behavior) governs fresh development: standard tools, compact raw evidence, concrete isolation, one independent slice review, and executable application progress instead of recursive controller preparation. Pinned public-SDK checkout integration may advance while immutable-package and final launch qualification remain pending. All explicit historical holds remain active. The next development behavior is FieldLog open/edit/save/close/reopen with preserved state on each platform; root coordinates native resources and source delivery. [Policy evidence](verification/development-unblock-2026-11-09/receipt.json).

Current working-state observations follow; earlier checkpoint sections remain historical. This policy change does not promote any GA gate.

## Current continuation: November 10, 2026

Computer use, UI automation and screen capture are resumed by the user’s November 10 instruction. [AGENTS.md](AGENTS.md) and [product-plan section 24.5](mixer-product-plan.md#245-development-tests-must-advance-application-behavior) record the current authorization. Existing Accessibility, owned-device cleanup, physical-phone and specific resource holds continue to apply. [Authorization receipt](verification/plan-continuation-2026-11-07/computer-use-capture-resumed-2026-11-10/receipt.json).

Main `f22221e0` contains the resumed computer-use policy and passes all seven hosted CI jobs. The public Android app also passes direct native composition, selected replacement and deletion while retaining its View/Editable and preserving the six-task/ten-outbox repository; [R196](verification/plan-continuation-2026-11-07/public-editor-composition-native-r196/REPORT.md) records scope and exact cleanup.

The app's light-window status-bar correction passes an actual same-signer update and capture. A staged SDK viewport correction also removes the observed scrolling bleed over navigation/status bars; [R236](verification/plan-continuation-2026-11-07/native-scroll-viewport-runtime-r236/REPORT.md) records actual before/after captures, unchanged six-task/ten-outbox data and emulator cleanup, and R234 independently passes the source correction. Canonical adoption remains pending.

The independently reviewed shared Entries feature now passes actual API37 OS-IME input, durable 100,000-UTF-8-byte draft Save, fresh-process restoration, a byte-exact 100,000-byte emoji edit and one Commit. The original six tasks and ten outbox records remain intact; final state is six tasks, eleven outbox records, one entry and zero drafts. [R252](verification/plan-continuation-2026-11-07/fieldlog-entry-ime-native-r252/REPORT.md) records this complete flow after the reviewed whole-screen FieldRemoval correction. [R268](verification/plan-continuation-2026-11-07/fieldlog-ime-boundary-native-r268/REPORT.md) also passes real 100,001-byte refusal without truncation, valid Unicode recovery and byte-exact repository preservation. Original IME settings were restored and the owned emulator is off. The reviewed V4 SDK/CLI source pair is installed locally as Pair19. Final source116 `ee43817e…` passes all six generated consumers and twelve refusals, actual public-V4 create/49-command Android build, full SDK tests (208 Swift Testing plus eight XCTest), and complete owner regressions (189 bindings/1,323 callback cases/15 helpers plus 231 owner cases). The corrected build receipt identifies V4 accurately. The source is delivered at `1a56d6d0`. Its fresh CI passes VM, services, native archive and owner-host jobs; two stale Pair18 test snapshots are corrected in the R316 follow-up. The cache control independently records EPERM/UNKNOWN for hosted group 1143, which remains held. Native/app development continues independently. UIKit, native date editing, immutable packages, physical phones and GA remain pending; historical failures and resource holds remain preserved.

The separate iOS app now has a reviewed shared-EntryEditor migration. R296 passes 13 XCTest and 62 Swift Testing tests plus a fresh unsigned iOS build, closing the reproduced photo-import/autosave race. Native PhotosUI and dismissal behavior remain pending; this source/build result does not qualify SDK UIKit rendering or immutable packages.

The actual public Pair18 FieldLog Android package now accepts real on-screen keyboard input, Save and fresh-process checklist readback with six tasks and ten outbox records. All five prior tasks and nine prior outbox rows remain intact. The last runtime assertion expected a bare title while native UI correctly displayed its numbered/status label; [captured UI admission](verification/plan-continuation-2026-11-07/fieldlog-public-ime-native-readback-r192/result.json) verifies the exact decorated row and retains the original failure. No additional Save was needed. The owned emulator exited and disappeared; the external device baseline is unchanged. Android consumes public `d2172767` through the reproducible sparse-checkout recipe, while iOS/host remain at `b898d3c3`. Main `cff82c2d` fixes the stale helper anchor and its hosted renderer job passes. The separate Swift Python output-limit cleanup failure remains held; its negative test now separates synthetic overflow detection from custody priority, with focused and binding checks passing in both Python modes and all seven jobs passing in the fresh f9d and f222 hosted runs. Full IME composition, physical phones, immutable packages and GA remain pending.

The actual shared FieldLog TaskEditor now executes through the opt-in owned-VM command route: all 80,514 bodies validate, and the full 439-byte output matches the native result. One save/completion, exact Unicode/newlines and consuming zero-reservation cleanup pass. R115 independently reviewed the runtime; root integration passes 29 command/validator/WASI tests and Clippy. Default profiles and fixed-reactor limits remain unchanged. The broader R118 run is incomplete with its exact process/build resources held; fresh app work remains independent. [Integrated evidence](verification/plan-continuation-2026-11-07/owned-taskeditor-focused-integration-r124/receipt.json). Full W07/W08 and GA remain pending.

FieldLog's public-SDK iOS save/relaunch and broader offline workflow pass on the owned iOS 26.5 Simulator, including multiline draft restoration, task completion/reorder and native report-share presentation/dismissal. The owned device is Shutdown and both protected Simulators remain unchanged. Headless device tests do not accept host keyboard/focus/window parity, VoiceOver, physical phones or immutable published packages. [Actual iOS workflow](verification/plan-continuation-2026-11-07/fieldlog-ios-offline-workflow-r2/receipt.json).

Android FieldLog now passes the complete pinned-checkout public Swift host prototype flow on API37 arm64: distinct Activity handoff, old-context teardown after new-context open, exactly-once reply routing, true multiline Unicode input/save, repository reopen, fresh Activity, native-only refresh, and final owner/core/coordinator/renderer cleanup ledgers. The final run took 31.63 seconds, all eight observer removals returned, and retired remeasurement/repeated close preserved the final state. The owned emulator exited 0; a fresh ADB inventory is empty and the external baseline is unchanged. The app-specific handmade shell remains a separate earlier result. [Actual native result](verification/plan-continuation-2026-11-07/fieldlog-distinct-activity-runtime-r41/receipt.json). Headless development proof does not qualify full IME composition, the final Android floor/phone matrix or immutable published packages.

The Pair12 external-frame owner source is installed for coherent delivery: source114 `5814b0dab60dfe3fdbce2791644499fc0362072a99bf9034c7f28ea266577608`, unchanged SDK24, adapter26 and Java20. All 92 CLI Swift Testing functions pass. The focused external-source/real-renderer Gate tests pass, full owner-host A passes 231 cases/1,253 assertions, and full B passes 14,692 checks with all 189 callback bindings, 1,323 cases and 15 helper obligations. All six actual Debug/Release original/relocated/exported Java/D8 consumers pass on this exact source with terminal command custody and scratch removal. [Delivery evidence](verification/plan-continuation-2026-11-07/pair12-development-delivery-r40/receipt.json).

The stalled native regression was a fixture task-reuse error: its first Activity returned and became ready, but `NEW_TASK` reused that task while the test waited for a second instance. A phase-only probe localized the wait; adding only `FLAG_ACTIVITY_MULTIPLE_TASK` made the original handoff and final-ledger assertions pass. All product libraries and other classes stayed exact. The two earlier timeouts and the disproved first-start premise remain retained. Production app host packaging/generator integration remains the next product boundary; the prototype glue does not establish published-package acceptance.

Delivery `b7b459d95` now passes [all seven ordinary CI jobs on attempt one](https://github.com/snowdamiz/mixer/actions/runs/42715894123), including the new public-surface cleanup/focus regressions, hosted Swift/iOS and generated Android consumers. The prior `fd373fc8f` all-green run remains preserved. [Observed current CI](verification/plan-continuation-2026-11-07/public-surface-combined-native-r49/main-ci-final.json).

The public Android SDK surface passes the actual API37 FieldLog regression from an external application package. A real InputConnection followup exposed a legitimate retained multiline editor moving from Y=115 to Y=144 after model reflow. Pair14 permits this vertical movement only for V3 multiline input, retaining X/width, binding, target, ancestry and owner checks. The unchanged native regression now passes composition/finish, selection replacement, exact save/repository reopen, fresh Activity, native refresh and all final cleanup ledgers in 33.85 seconds. Independent review passes 17 cases/102 assertions, including rollback and required refusals. [Native evidence](verification/plan-continuation-2026-11-07/fieldlog-v3-reflow-native-r61/receipt.json). [Review](verification/plan-continuation-2026-11-07/v3-editor-vertical-reflow-fix-r58/v3-editor-reflow-review-r60/REPORT.md).

Pair14 is installed with 115 owning inputs, unchanged SDK24, adapter27 and Java21. All six actual Debug/Release original/relocated/exported Java/D8 consumers pass with 227 classes each; all 92 CLI methods pass in one complete run. Python controls pass 114 in normal mode and 114 under actual `-O`; the public host regressions and full 189-binding concrete-renderer matrix pass. The earlier harness setup failures remain preserved. [Installed validation and delivery scope](verification/plan-continuation-2026-11-07/v3-reflow-installed-validation-r64/REPORT.md). Production public-V3 generation/packaging remains a separate active slice. Three generated Swift host/C-entry methods and the actual unsigned Android production build pass. The real generated Activity starts through JNI/MainActor and renders native UI, but normal typing exposes a single-slot event queue rejection. A first-false probe confirms eventPending=true after two earlier successful requests; a FIFO alone would stale the original revision. The same-origin batch correction passes 58 root Swift tests and an independent 62-test/three-Java-control review. A second real failure was an acknowledged draft clear rejected by editor binding; target, ancestry and frame were valid. The owner-controlled clear correction now passes actual API37 native typing/model echo, Add with visible draft reset, and Toggle in 38.33 seconds. Strict SDK37/JDK25 compilation passes, all 18 native libraries are unchanged, and owned emulator cleanup is confirmed. [Actual generated-app result](verification/plan-continuation-2026-11-07/generated-add-correction-native-r84/receipt.json). Pair15 is now installed with 116 owning inputs. All 94 CLI tests, full SDK Debug/Release tests, six final Java/D8 consumers and a fresh full-CLI public-V3 Android APK build pass. The complete callback matrix passes 14,692 checks. The final source is `3cd790bcd01dcf406ad2935d810b2fbbe7ab126c1e90efa032c3a92a62cc1e07`. [Final validation](verification/plan-continuation-2026-11-07/public-batch-final-validation-r89/summary.json). Delivered as `6d2648e43`; [all seven ordinary CI jobs pass](https://github.com/snowdamiz/mixer/actions/runs/42774292888) on attempt one. The real FieldLog consumer now passes the actual macOS C-entry Unicode/multiline burst/save/close/fresh-repository-reopen test with old-owner refusal and context isolation. The local public-host ABI correction now builds the real FieldLog APK. API37 starts the native form. On the unchanged APK, fast whole-string title/person input passes after focus and editor bounds settle. The Save refusal was reproduced on the focused horizontal Responsible editor when the model disables it. The two-file V3 correction now passes the actual API37 generated-public-host flow: fast settled-focus input, focused Responsible before Save, visible Saved state with exact disabled text fields, durable repository state, and fresh-process/Activity reopen. The run took 45.20 seconds; all 18 native libraries were unchanged. The emulator exited 0, its serial is absent and the external baseline is unchanged. Pair16 is installed as source116 `20d70a1778ffdfc7427f8e87bf0849ddfa956794dec4e9096ddf53a985b03b6f`; all 94 CLI tests, six actual Java/D8 consumers and seven permanent public-host suites pass. Delivered as `94745c66`; [all seven fresh ordinary CI jobs pass](https://github.com/snowdamiz/mixer/actions/runs/42789803741) on attempt one. This is a headless pinned-checkout development result; full keyboard/IME, private terminal ledgers, phones and published-package qualification remain pending. [Actual FieldLog result](verification/plan-continuation-2026-11-07/fieldlog-focused-disable-native-r102/result.json). [Actual diagnostic](verification/plan-continuation-2026-11-07/generated-event-first-false-probe-r71/receipt.json). Pair14 delivery `483813016` now passes [all seven ordinary CI jobs](https://github.com/snowdamiz/mixer/actions/runs/42724081429) on its first attempt. This headless proof leaves OS IME service, keyboard/window parity, phones, API floor, immutable packages and GA pending.

The cache control correctly preserves UNKNOWN after EPERM; current hosted PGID1222 and the prior source303 group/scratch remain specifically held. Their OS cause is unproven and they do not block independent app/source work. All historical holds remain active, physical-device testing remains unauthorized, and GA remains **0/38 verified**. [Current native/CI development evidence](verification/plan-continuation-2026-11-07/pair12-development-delivery-r40/receipt.json).

## Earlier continuation observations

The profile 10 callback and reference-count repairs have passed both public manifests, selected CLI compatibility and Python controls. A fresh Sol review is active. The CF install-boundary review passed 259 tests in each Python mode and accepts one prospective API37 diagnostic; fresh root admission remains pending. Three Sol agents now own profile review, CLI process supervision and independent FieldLog iOS build recovery. Grok 4.7 checks the FieldLog assertions without visual or runtime actions. Root owns CF preflight and integration. [The parallel work snapshot](verification/plan-continuation-2026-11-07/resumption-2026-11-08/plan-update.html) records five lanes and the remaining launch scope.

Work resumed on November 8 under the user’s Sol 6.1 / Grok 4.7 restriction. [The resumption record](verification/plan-continuation-2026-11-07/resumption-2026-11-08/resume.json) distinguishes the accepted hosted slices from unfinished work: profile 10 has two reproduced review findings, the full store suite needs contained execution, and the CF attempt stopped at controller validation of successful install output before executor assertions. Fresh isolated corrections are active. The delayed device comparison preserves both protected Booted simulators and one new unrelated Shutdown device. The root observation wrapper’s persistence failure is a separate unresolved hold; no retry or scratch inspection is authorized.

The CI corrections remain delivered at `93001260`. [Ordinary CI 42447022532](https://github.com/snowdamiz/mixer/actions/runs/42447022532), attempt 1, finished with six jobs passed and cache failed. [Hosted CLI acceptance](verification/plan-continuation-2026-11-07/store-cli-caller-hosted-acceptance.json) covers 74 tests with the real binary; [envelope acceptance](verification/plan-continuation-2026-11-07/envelope-r2-hosted-acceptance.json) covers the exact 40-command fixture. [Cache R8 is independently accepted and installed](verification/plan-continuation-2026-11-07/cache-r8-acceptance.json): 70 retained tests and four independent methods covering 54 cases pass in each Python mode. The exact workflow and unchanged source103 passed installed verification. The correction is delivered at `7bf0854e`; [fresh ordinary CI 42456334193](https://github.com/snowdamiz/mixer/actions/runs/42456334193), attempt 1, has passed all seven jobs. [Exact hosted cache acceptance](verification/plan-continuation-2026-11-07/cache-r8-hosted-acceptance.json) covers 18 audit groups, 135 Python controls, both descriptor preflights and all 103 fixture commands under the recorded Rust 1.99.1 / Python 3.15.2 profile. R4 UNKNOWN scratch and all earlier failures and holds remain intact.

[API28 runtime and visual acceptance](verification/plan-continuation-2026-11-07/api28-settled-acceptance.json) covers the exact 34-assertion arm64 attempt and both opaque checklist frames, with terminal cleanup and the external device baseline preserved. [The API37 MainActor baseline](verification/plan-continuation-2026-11-07/mainactor-baseline-acceptance.json) is accepted as diagnostic evidence only: JNI returned, detached Swift progressed and a UI heartbeat ran, but MainActor start was not observed in the finite snapshot. The CF source review reproduced application-result spoofing of framework success. [The isolated parser correction](verification/plan-continuation-2026-11-07/mainactor-cf-terminal-fix-r2/REPORT.md) passes 86 controls normally and under `-O`; independent review accepts it after 12 additional test groups per mode. Its seven native source files remain unchanged. A fresh witness library and APK have been built for the changed JNI ABI. Both build-driver parsing failures remain preserved; subsequent read-only artifact audits passed. The exact package and bound controller are independently accepted for one finite CF diagnostic. The single API37 CF attempt stopped before executor assertions. ADB returned exit 0 with `Performing Push Install` and `Success`; the controller rejected the combined progress output. The receipt records terminal cleanup and no new native custody hold. [The resumed controller correction](verification/plan-continuation-2026-11-07/resumption-2026-11-08/resume.json) remains under validation.

[Public Android host R3](verification/plan-continuation-2026-11-07/public-android-host-r3-acceptance.json) remains accepted for macOS MainActor behavior; both exact package manifests pass 185 tests each. [Vertical retirement R5](verification/plan-continuation-2026-11-07/vertical-retirement-final-r5/report.md) passes the unchanged 193/86/182 suites, 2,732 cohort checks, final full B with 1,323 cases / 189 bindings / 15 helpers, strict SDK37 compilation and D8 min28. Product bytes remain identical to R4. [Independent review accepts the exact host candidate](verification/plan-continuation-2026-11-07/vertical-r5-host-acceptance.json), including 376 new checks across all four two-field order/active-field save and reopen combinations. The isolated [source-pair .10 candidate](verification/plan-continuation-2026-11-07/public-android-profile10-r1/REPORT.md) now has an explicit public V3 profile, 106 source inputs and 19 Java products. Its package and Java checks passed. [Integration review](verification/plan-continuation-2026-11-07/public-android-profile10-review-r1/REPORT.md) reproduced profile changes during callbacks and a stale reference-count assertion. A fresh Sol campaign owns those corrections. Synthetic retained authority and uncertain cleanup remain unqualified; canonical adoption, executor/JNI, published FieldLog and GA remain pending.

[The separate FieldLog iOS build lane](verification/plan-continuation-2026-11-07/fieldlog-ios-flow-selection/selection.json) stopped after two clone failures on the same unavailable Git blob. It produced no app, test runner or xctestrun. Its interrupted work remains preserved. It does not alter the original keyboard experiment, shared Simulator preferences or protected devices; no new iOS runtime attempt is selected.

W13 has an isolated [read-only TestFlight status candidate](verification/plan-continuation-2026-11-07/store-testing-status-r1/REPORT.md). It built the actual CLI and exercised 39 supervised CLI processes, including 24 concurrent writers; selected Swift tests passed 39/40 before an unrerun fixture-only correction. [Independent review found no confirmed product defect](verification/plan-continuation-2026-11-07/store-testing-status-review-r1/REPORT.md), but four original tests lack bounded child-process handling. The isolated [test-runner correction](verification/plan-continuation-2026-11-07/store-cli-custody-campaign-r2/REPORT.md) passed all 44 store tests, including the corrected fixture and original four subprocess cases, with 59 real CLI child custody receipts. Full87 remains unrun because other tests exercise the product process runner; the [fresh containment probe](verification/plan-continuation-2026-11-07/store-full-suite-containment-r4/REPORT.md) disproved shared-group containment. Full87 remains unrun. Its three inner groups and two bootstrap groups remain held. [A separate Sol source repair](verification/plan-continuation-2026-11-07/process-runner-boundary-selection-r1/selection.json) now owns explicit command supervision before any new runner runtime test. No canonical integration or live provider calls occurred; source integration and fresh consumers remain required.

The reviewed real-CLI caller fix is delivered at `0f30624d`. [Fresh ordinary CI 42442717964](https://github.com/snowdamiz/mixer/actions/runs/42442717964), attempt 1, has failed before reaching the CLI tests: the Swift envelope preflight rejects the changed job binding, and the cache optimized descendant control reports EPERM with unknown custody. [Exact failure artifacts and root observation](verification/plan-continuation-2026-11-07/store-cli-caller-delivery/ci-discovery/failure-observation.json) are retained. Local qualification remains 74 tests, including 31 store tests and 48 concurrent real CLI children; no new hosted CLI pass is claimed. Separate bounded corrections preserve the sealed envelope history, all cache limits and the hosted custody failure. Android runtime work has advanced: [API28 narrow runtime acceptance](verification/plan-continuation-2026-11-07/pair9-api28-runtime-acceptance.json) covers 34 assertions, genuine JNI/Swift execution and terminal cleanup. Its two transition-like screenshots leave stable visual presentation inconclusive. [Independent API32/33 acceptance](verification/plan-continuation-2026-11-07/pair9-api32-33-runtime-acceptance.json) covers 12 and 75 checks, respectively, with both diagnostic-window screenshots reviewed. API33 observed main-thread motion callbacks, silence after removal and exact effective/raw restoration. All three owned instances were cleaned up and the protected Simulator baseline stayed unchanged. These are exact development slices; no full API-floor or GA promotion follows.

Accepted evidence and execution instructions are delivered in checkpoint `62ce9b76`. [Ordinary CI 42436018168](https://github.com/snowdamiz/mixer/actions/runs/42436018168), attempt 1, has passed all seven jobs. [Terminal job metadata](verification/plan-continuation-2026-11-07/runtime-checkpoint-delivery/ci-discovery/final-jobs.json) is retained; prior artifact qualifications keep their original source/run bindings. The Android product remains the accepted pair9 R2 bytes. The independently accepted store CLI/source103 closure is now delivered in `3e2f0907`. Its [ordinary CI 42440636337](https://github.com/snowdamiz/mixer/actions/runs/42440636337) failed the Swift job because four real-CLI tests require the absent `MIXER_STORE_TEST_CLI` environment binding. [Exact logs and observation](verification/plan-continuation-2026-11-07/store-status-delivery/ci-discovery/swift-failure-observation.json) are retained; the [three-caller correction is now integrated](verification/plan-continuation-2026-11-07/store-cli-caller-acceptance.json) after 74 full CLI tests passed, including 31 store tests and 48 real CLI children. That caller correction was subsequently delivered at `0f30624d`; its newer CI observation appears above. [Final job metadata](verification/plan-continuation-2026-11-07/store-status-delivery/ci-discovery/final-jobs.json) records six successes and this one failure. The actual generated-Java job passed; no retry or overall CI pass is claimed.

Source pair `.9` R2 is delivered as `96f03ab6`. [Fresh ordinary CI 42430741909](https://github.com/snowdamiz/mixer/actions/runs/42430741909), attempt 1, has passed all seven jobs. [Independent host acceptance](verification/plan-continuation-2026-11-07/pair9-host-ci-acceptance.json) covers A231 cases, B14,692 checks with all 1,323 cases and 189 bindings, Observer190 and platform134/699. [Hosted Java/D8 acceptance](verification/plan-continuation-2026-11-07/pair9-generated-hosted-acceptance.json) independently covers all six consumers, 216 classes and 4,976 member references each, the official bootstrap and all 24 tamper invocations. [Independent product review](verification/plan-continuation-2026-11-07/android-motion-thread-review-r2/REVIEW.md) accepts main-thread motion delivery, publication of coalesced notices and the corrected drain-order oracle. [Parent integration](verification/plan-continuation-2026-11-07/android-motion-r2-integration/verification.json) preserves the reviewed 15-file implementation and exact 101-input closure. [Independent artifact qualification](verification/plan-continuation-2026-11-07/generated-java-pair9-r2-actual-review/result.json) accepts six original/relocated/exported Java17/D8 consumers from Debug/Release CLI producers: 79 commands, 216 classes and 4,976 member references each, with all 24 CLI/copied-driver tamper invocations refused and terminal cleanup. The integrated inputs [equal those executed bytes](verification/plan-continuation-2026-11-07/android-motion-r2-integration/artifact-binding.json). Fresh host evidence covers B14,692 checks / 1,323 cases / 189 sites / 15 helper boundaries, Observer190 and platform134 cases / 699 assertions; CI rebinding passes 28 bootstrap and 12 sparse controls in both isolated Python modes. One root verification-helper lookup error is retained separately from successful integration verification. Native and API-floor runtime qualification are not inferred.

The preceding reviewed CI fixes and API28 harness are delivered at `25ac442c`. [Ordinary CI 42429965271](https://github.com/snowdamiz/mixer/actions/runs/42429965271), attempt 1, has passed all seven jobs. The signature correction requires positive Apple notarization in every admitted report format. The cache correction verifies actual interruption and scratch preservation without claiming a wall-clock latency guarantee. [Fresh cache qualification](verification/plan-continuation-2026-11-07/cache-deadline-ci-acceptance.json) accepts the exact Rust1.99.1 fixture and new deadline-control adoption: 103 commands, 768 method executions, 124 captures and 135 Python controls. [Hosted pair8 Java acceptance](verification/plan-continuation-2026-11-07/generated-java-hosted-acceptance.json) covers the official bootstrap and six consumers, 92 command records and 24 tamper invocations; it does not qualify pair9 or runtime behavior. The earlier `e7254f370` run's signature-parser refusal and cache timing failure remain [preserved](verification/plan-continuation-2026-11-07/ci-e725-observation.json). Its consumer compilers and cache fixture did not execute.

The cache correction's final local optimized suite remains 35/36 because unchanged descendant cleanup returned `EPERM`; its normal suite passed 36/36. [PGID23663 and retained scratch remain on custody hold](verification/plan-continuation-2026-11-07/cache-deadline-custody-hold/receipt.json), independent of the later hosted pass. Both corrected deadline controls and all 11 contracts passed in both local modes. Historical exact Rust1.99.1 [cache](verification/plan-continuation-2026-11-07/cache-actual-acceptance.json) and [envelope](verification/plan-continuation-2026-11-07/envelope-actual-acceptance.json) acceptance from `df7b67ace` remains limited to those host profiles; previous failures and attempt limits are preserved.

Pair `.8` retains its earlier [11-assertion API37 arm64 smoke acceptance](verification/plan-continuation-2026-11-07/android-toggle-oracle-integrated/parent-acceptance.json). A subsequent real settings callback failed by entering the UI-only Observer on a Binder thread; raw setting absence was restored, but effective restoration and silence after removal remain unverified. Pair `.9` fixes that delivery path in source and host tests. The selected runtime preparation stopped before any emulator or APK build because the old controller lacked required custody, output-bound and failure-restoration handling. Zero native attempts were consumed. The controller repair then hit unexpected host-process `EPERM`: [groups 40708, 40709 and 40711 remain held](verification/plan-continuation-2026-11-07/android-controller-custody-holds/receipt.json). Its final source refinements are unrerun. The [custody premise campaign](verification/plan-continuation-2026-11-07/native-custody-premise/packet.json) selected reaping before signalling and before group-absence checks, with EPERM still stopping on unknown custody. [Independent controller review](verification/plan-continuation-2026-11-07/native-custody-review/review.json) admitted one attempt. That [API37 arm64 run](verification/plan-continuation-2026-11-07/native-custody-premise/runtime-attempt/receipt.json) passed 104 checks, including the original 11 smoke assertions, main-thread motion callbacks, owner refresh, exact packet preservation, effective/raw restoration and observed silence after listener removal. All 50 owned command records reached terminal custody; scratch and private keys were removed. [Independent review and root acceptance](verification/plan-continuation-2026-11-07/pair9-api37-native-acceptance.json) qualify only this API37 arm64 development smoke. The review corrects one bookkeeping count to 103 unchanged prior inputs out of 105; it preserves the original receipt. The deleted test APK was not independently rehashed, and custody depends on retained command records. Earlier failures and all holds remain unchanged. [Pair8 generated-consumer acceptance](verification/plan-continuation-2026-11-07/generated-java-pair8-acceptance.json) and its [static API-floor review](verification/plan-continuation-2026-11-07/generated-java-pair8-api-floor-review/REVIEW.md) do not establish API28/32/33 runtime behavior.

The [API28 packaging correction and harness](verification/plan-continuation-2026-11-07/android-api28-integrated/acceptance.json) are independently accepted and delivered. Product DEX, 215 classfiles and 18 native libraries remain exact pair8 bytes; the signed test APK has no overlapping definitions. The official API28 image is [installed](verification/plan-continuation-2026-11-07/android-api28-image-install/receipt.json), with its package/source-properties revision discrepancy recorded. A separate [pair9 R2 package](verification/plan-continuation-2026-11-07/pair9-api28-packaging/result.json) now reuses all 216 accepted classes, exact DEX and 18 libraries; one packaging attempt, six tamper controls and 23 command custody records passed. [Independent review and root acceptance](verification/plan-continuation-2026-11-07/pair9-api28-package-acceptance.json) cover this exact package only. ART/JNI runtime remains unrun. The first controller passed 34 host controls in each mode, but [independent review](verification/plan-continuation-2026-11-07/pair9-api28-controller-review/review.json) found an ADB replacement-daemon path and lost screenshots after late failure; R2 passes 50 host controls in each mode, but [review R2](verification/plan-continuation-2026-11-07/pair9-api28-controller-review-r2/review.json) finds that emulator-issued clients can still start a detached server after controller exit. The [R3 correction](verification/plan-continuation-2026-11-07/pair9-api28-controller-fix-r3/identity-receipt.json) passes 53 controls in both modes and a real inherited-client refusal probe. [R3 independent review](verification/plan-continuation-2026-11-07/pair9-api28-controller-review-r3/review.json) accepted 62 controls per mode. The [one actual API28 attempt](verification/plan-continuation-2026-11-07/api28-root-observation/result.json) booted the emulator, then stopped before APK install because ro.boot.qemu.avd_name was empty. All 22 commands reached terminal custody; owned emulator, keys and scratch were removed. [R4 independent review](verification/plan-continuation-2026-11-07/api28-runtime-identity-review-r4/review.json) accepted the direct public console query after 78 controls per mode. The [fresh R4 attempt](verification/plan-continuation-2026-11-07/api28-r4-root-observation/result.json) passed boot, exact console identity and APK installation, then stopped before instrumentation because API28 logcat rejects --uid. All 25 commands reached terminal custody; scratch, keys and the emulator were removed. The supported-logcat successor now passes 86 host controls in each mode; a separately selected root normal run closes the producer path-error gap while preserving that failed command. [R5 independent review](verification/plan-continuation-2026-11-07/api28-logcat-review-r5/review.json) reproduced a false-success path when final cleanup crosses the log-output cap. A successor will reject that terminal limit after draining; ART/JNI assertions remain unrun. Historical PAIR8 harness labels require binding the runtime result to the accepted pair9 APK hash. Both below-36 V2 refusals remain intact.

The [official API32 and API33 ARM64 images](verification/plan-continuation-2026-11-07/android-api32-33-image-install/receipt.json) are installed for the separate motion-boundary gate. Existing tools/images remain unchanged and installer custody is terminal. Their exact package/source-property versions and file hashes are retained. The [dedicated signed instrumentation package](verification/plan-continuation-2026-11-07/api32-33-motion-package/REPORT.md) passed strict Java/D8 compilation, signature/alignment and six tamper controls against unchanged pair9 product DEX and native libraries. [Independent artifact review](verification/plan-continuation-2026-11-07/api32-33-package-acceptance.json) accepts the package and finds the pre-mutation diagnostic gap nonblocking. [Independent controller review](verification/plan-continuation-2026-11-07/api32-33-motion-controller-review/REVIEW.md) rejects missing emulator-lifetime checks and the ADB console authentication/output filter. The public-query successor passes 82 host controls per mode. [Fresh review](verification/plan-continuation-2026-11-07/api32-33-console-review-r2/REVIEW.md) confirms the console repairs but requires typed root admission and a nonblank baseline-evidence reference; that narrow correction and the shared final-output-limit check are active. No API32/33 emulator or runtime test has run.

On iOS26.5, [Settings passes and original reference-first Tab fails](verification/plan-continuation-2026-11-07/apple-settings-runtime-r2/REPORT.txt) `actualNativeFocusTraversal`; the other 19 predicates pass. The keyboard experiment stopped before XCTest on Accessibility denial `-25211`; one attempt remains. Its Simulator cleanup mistakenly shut down two protected devices. [User-authorized recovery restored both to Booted](verification/plan-continuation-2026-11-07/simulator-state-recovery/result.json), preserving identities/data paths but not prior in-memory sessions. The incident remains a cleanup failure. [Independent safe-controller review](verification/plan-continuation-2026-11-07/apple-safe-keyboard-review/REPORT.txt) required fixes for exception latching, uncertain window identity, missing held groups and nested-process custody. [R2](verification/plan-continuation-2026-11-07/apple-safe-keyboard-fix-r2/REPORT.txt) passes its 72 controls, but [independent review](verification/plan-continuation-2026-11-07/apple-safe-keyboard-review-r2/REPORT.txt) reproduces further cleanup after external-device drift and acceptance of malformed terminal data. [R3](verification/plan-continuation-2026-11-07/apple-safe-keyboard-fix-r3/REPORT.txt) passes 94 controls normally and under optimized Python, preserving all 83 earlier test bodies. [R3 independent review](verification/plan-continuation-2026-11-07/apple-safe-keyboard-review-r3/REPORT.txt) reran all 94 controls successfully in both modes, but its four new wrapper fixtures failed before exercising the candidate. No candidate defect was reproduced. [R4 completed those 19 wrapper scenarios in each mode and accepted the unchanged controller](verification/plan-continuation-2026-11-07/apple-safe-keyboard-review-r4/result.json). The [root attempt](verification/plan-continuation-2026-11-07/apple-safe-keyboard-root-runtime/result.json) passed fresh trust checks, created one disposable simulator, then stopped before XCTest on AXWindows error -25204. All 13 command records have terminal custody; device/window cleanup remains incomplete. A separate [root read-only reconciliation](verification/plan-continuation-2026-11-07/apple-window-recovery/inspection-1/result.json) verified the protected-device baseline unchanged and showed three windows with empty AXIdentifier values, including the owned window and windows for both protected devices. [Independent successor review](verification/plan-continuation-2026-11-07/apple-window-identity-review/REPORT.txt) passed 129 controls per mode. The [actual adoption](verification/plan-continuation-2026-11-07/apple-window-identity-campaign/adoption-attempt-1/result.json) established window identity and fresh trust, but found hardware keyboard disconnected and skipped XCTest. Its exact owned-window close began asynchronous shutdown; cleanup stopped on Shutting Down. [Separate root recovery](verification/plan-continuation-2026-11-07/apple-adoption-recovery/attempt-1/result.json) positively observed Shutdown, deleted only that disposable device, and verified the external baseline unchanged with both protected devices Booted. The original cleanup failure remains recorded. The keyboard-readiness/transition campaign passes 150 host controls per mode, but cannot establish shared keyboard-toggle isolation. The [completed isolation investigation](verification/plan-continuation-2026-11-07/apple-device-set-isolation-premise/REPORT.txt) found that private device sets and per-process keyboard arguments still write shared Simulator preferences. It proposes a separately verified login/home/session boundary. The user confirmed there is no separate test login. [The root decision](verification/plan-continuation-2026-11-07/apple-isolation-root-decision.json) leaves this specific keyboard experiment pending while Android/CI work continues; no account creation or shared-keyboard change is selected. The original XCTest attempt remains available. No global frontend quit is permitted. macOS27.0.1 calls the permission pane Device Control and Data Access. Retained TCC logs identify Acid (`com.t3tools.t3code`) as responsible for both helpers. After the user toggled only Acid off and back on, [fresh osascript and Python checks still report false](verification/plan-continuation-2026-11-07/apple-accessibility-after-toggle/receipt.json). [Dynamic code validation](verification/plan-continuation-2026-11-07/apple-tcc-identity/findings.json) confirms running Acid matches the installed app. A [fresh check under that instance](verification/plan-continuation-2026-11-07/apple-accessibility-current-acid/receipt.json) still reports both helpers denied. After the user removed and re-added the exact Acid.app entry, [fresh Python and osascript trust checks both returned true](verification/plan-continuation-2026-11-07/apple-accessibility-after-readd/receipt.json). The permission prerequisite and window-identity review are resolved; the remaining experiment requires verified keyboard connection and safe asynchronous shutdown handling. One root request for the standard OS notice crashed the helper with exit -11 and terminal custody, after an earlier wrapper-only argument error; neither started a simulator or consumed the remaining attempt. The user screenshot shows Acid enabled in the correct pane. Original Tab remains pending; the fresh setup consumed no XCTest attempt, and the one remaining original XCTest attempt is preserved.

W13's isolated implementation of the [read-only existing App Store Connect build-status command](verification/plan-continuation-2026-11-07/store-next-integration/REPORT.md) passes eight original host test groups. [Independent review](verification/plan-continuation-2026-11-07/store-status-review/REPORT.md) reproduced one credential-persistence defect: a prior observation recognized as a newly supplied token was hidden only in the current response, then re-emitted by a later credential-free invocation. R2 passes 13 host groups, but [independent review](verification/plan-continuation-2026-11-07/store-status-review-r2/REPORT.md) rejects its permanent admission closure after 16 distinct credential fingerprints. R3 passed 18 of 19 groups before a concurrent-writer failure; its second attempt failed test compilation, and the final annotation fix is unverified. Its direct fingerprint-file design cannot detect deletion of individual entries. [The retained R3 report](verification/plan-continuation-2026-11-07/store-status-fix-r3/REPORT.md) remains unqualified. [The completed campaign](verification/plan-continuation-2026-11-07/store-credential-index-campaign/REPORT.md) reproduced deleted-fingerprint re-emission and an ENOENT race in concurrent lock-file creation. Its referenced-tree index and exclusive lock creation pass 23 serialized test groups, including 120 distinct credentials and five 24-writer rounds. [Independent review](verification/plan-continuation-2026-11-07/store-credential-index-review/REPORT.md) passes 28 groups but reproduces one additional failing group: a format-valid one-byte mutation in the unchecked pending journal changes recognition and permits credential re-emission. The [versioned journal correction](verification/plan-continuation-2026-11-07/store-journal-integrity-fix/REPORT.md) passes 31 host groups. [Independent review](verification/plan-continuation-2026-11-07/store-journal-integrity-review/REPORT.md) accepts it after 33 groups, 462 byte-mutation refusals and 20 refusals before provider dispatch. Root integrated the exact four-path candidate after the pinned API28 attempt finished. Source103 is eda43c6bb96bfeb15ab31731858c7388a7ba52329c8ba8e48ed52505bfe86158; 45 runner, 28 bootstrap and 12 sparse controls pass in each mode. All six actual generated consumers passed with 79 command receipts, 216 classes and 4,976 member references per closure; all 24 tamper invocations refused and cleanup completed. [Independent actual-artifact review](verification/plan-continuation-2026-11-07/store-journal-integrated-acceptance.json) accepts all six consumers and exact source103. The exact integration was committed and pushed as `3e2f0907`. Its fresh ordinary Swift CI job failed on the missing real-CLI test executable binding; the accepted three-caller correction is integrated for coherent delivery. It covers ordinary CI, scripts/verify.sh and README. Its first local build failed under a producer-added outer sandbox. A root campaign using the established executor built the real CLI and passed the store-status suite, but its full suite failed because the copied test input set omitted optional Android fixtures. Both failures and terminal custody are retained. [The complete-input campaign and independent review](verification/plan-continuation-2026-11-07/store-cli-full-fixture-campaign-r2/review.json) pass all 74 tests; all eight definitions affected by the 81 missing-fixture issues now pass unchanged. All ten command groups closed and fresh scratch was removed. The caller correction is delivered at `0f30624d`; its fresh CI stopped at the earlier envelope and cache gates, before these CLI tests. The previous pre-checksum prospective digest remains unadmitted. No live account, upload, signing, provider, TestFlight/Play or D6 acceptance is claimed. Frozen hosted lanes remain untouched; complete store distribution and immutable published-package FieldLog consumption remain required.

The [store reviewer information template](docs/store-reviewer-information-template.md) now covers the actual interpreter, signed update boundary, native fallback, specific examples and reproduction steps. Its official policy references were checked on November 7; completed notes and real store decisions remain separate release evidence.

The user explicitly resolved the conflicting instructions with “Keep native testing resumed.” [The clarification receipt](verification/plan-continuation-2026-11-07/native-resumption-confirmed.json) and [AGENTS.md](AGENTS.md) authorize fresh bounded native/UI/capture attempts under one-instance and exact cleanup rules. Phones remain disconnected. All specifically held historical processes, PGID23663, the v5 startup and frozen hosted lanes remain untouched. GA remains **8 running, 30 planned, 0 verified**. The full W01–W18, G01–G38 and D0–D8 scope remains binding.

Earlier November 7 observations and transitions remain in the [preserved checkpoint text](verification/plan-continuation-2026-11-07/pair9-r2-delivery/current-continuation-before-refresh.md) and their linked receipts.

## Previous checkpoint before the November 7 CI inspection

Mixer `a3967100` delivered the exact 202-path `mixer.android-source-pair.7` slice. [The command record](verification/github-delivery-android-pair7/root-closed-command-series.json) closes all 38 new target commands with exit zero and zero signals. The original delivery controller separately exited 1 after push because one root-delegated review namespace became nonempty after preflight. [Independent post-push review](verification/github-delivery-android-pair7/review/post-push-preservation/seal.json) and [explicit data recovery](verification/github-delivery-android-pair7/post-push-recovery-decision.json) verified the 202 changed objects, sole parent, non-force remote result and empty index while retaining that controller failure. Both protected files and all 2,435 prior collapsed identities remain preserved. This establishes no recursive untracked-content proof. The historical target-command series totals 147 commands, with 146 exit-zero results and one older closed staging failure. The new outer controller failure is separate.

[Engine CI 40968793326](https://github.com/snowdamiz/mixer/actions/runs/40968793326), attempt 1 at `a3967100`, completes with five successful jobs and a failed `android-owner-host` job, `123779983605`. [The canonical failure summary](verification/android-broader-pair7-integration/ci-failure/failure-summary.json) binds the retained artifact and javac diagnostics. Closure A failed before any host test main because the controlled renderer substitute omitted `completeFailedV2` and `editorDisposalBusyV2`. Production already declares both methods. Closure B and later environment steps were skipped. Pair.7 host acceptance remains pending.

The [source-only correction](verification/android-broader-pair7-integration/host-fixture-fix/adapter-leaves/final-source-selection.json) selects ten canonical test files. Its three receipts cover nine new behavioral cases, a live explicit roster with A87 and B96 sources, actual `NativeEditorConnectionV2` in B, and five independent controlled Android types with required signatures. The runner freezes the exact roster bytes. [Root independent source review](verification/android-broader-pair7-integration/host-fixture-fix/root-review/review.json) accepts the correction for fresh ordinary CI. No compiler or host assertion has run for this correction. Coherent delivery and new ordinary CI remain pending. The separate generated Java CI proposal and review are in progress. That proposal is not installed or included in this delivery claim.

The delivered pair.7 tuple remains SDK22 `bc03288599ece5612cc4dce8b80fc404942584e0477ec9333bd39c0fa7d352d0` and adapter24 `ae18d494f768a280600dbefcad0cd55fb9a4b9b993c6cd441f084a08fbf6e03e`, covering 46 named members and 661,583 bytes. The original nine installed source bindings, axis `DocumentSession`, wire tuple and 9,587-byte default descriptor remain unchanged. The prior `3da0d01b` six-job canonical pair.6 host acceptance stays historical. The [first Rust 1.99.1 actual-data audit](verification/rust-1991-first-actual-result/refusal-receipt.json) retains its refusal of the observed 1.98.1 artifact. Rust 1.99.1 remains unqualified, with no retry, reprofile, install or fallback selected.

Generated Android Debug/Release, relocated and exported actual consumers, all 18 product Java files and actual generated Java still need fresh compilation evidence. Both below-36 guards retain the API28-35 full V2 refusal. Prior API28 collection proof is not inherited. These source and host records establish no Android UI or runtime acceptance.

Public FieldLog `00c8fe04` host run `40820029857` remains historical with 39 accepted tests. Immutable published SDK consumption, full native owners, D0-D8, physical devices, signing, store, customer and GA acceptance remain pending. Gates remain **8 running, 30 planned, 0 verified**. Native/UI/capture and local compiler/custody holds remain, phones are disconnected, all seven held local groups and FieldLog run `40802230894` / PGID `2424` / PID `2621` stay untouched, and the v5 startup is not retried. [This tracking checkpoint](verification/pair7-host-fix-tracking-checkpoint/observed-checkpoint.json) records the exact retained evidence and pending work.

## Previous delivered checkpoint at 3da0d01b

Mixer `3da0d01b` delivered the exact 227-path canonical `.6` slice. [Independent delivery review](verification/github-delivery-axis-canonical-followup/review/actual/seal.json) accepts all 38 new closed commands with exit zero and zero signals. The 71 historical commands retain the original closed staging failure. The combined record is 109 commands, with 108 exit-zero results and one historical failure. Both protected outside changes remain. The 2,425 original collapsed entry identities and modes remain preserved through 2,413 common paths and 12 prior-scope-to-nested transitions. The stored lists differ; this establishes no recursive untracked-content proof.

[Engine CI 40960463690](https://github.com/snowdamiz/mixer/actions/runs/40960463690), attempt 1 at `3da0d01b`, passes all six jobs and 68 steps with zero failures or skips. [Canonical host acceptance](verification/android-axis-canonical-host-acceptance/receipt.json) covers eight axis XCTest cases, 16 existing engine Swift Testing tests across three suites, 11 CLI compatibility declarations with 70 effective cases, and 13 Python source-pair methods. The earlier isolated 19-test result at `2c751cbb` remains historical. Stage 4 host checks retain 39 cases per mode and exclude `DocumentSession`.

The [first Rust 1.99.1 actual-data audit](verification/rust-1991-first-actual-result/refusal-receipt.json) correctly exits 1 because the retained artifact reports Rust 1.98.1. Its one invocation records 16,758 checks, with 16,757 passes and one exact-identity mismatch, and zero inner or outer denials. Independent review accepts that refusal. The new 1.99.1 profile was not exercised and remains unqualified. This partial audit establishes neither a compiler/workload failure nor new complete 1.98.1 envelope acceptance. The 33 prospective synthetic controls and installed workflow retain their historical attribution. No retry, reprofile, install or fallback is selected.

Root has [installed nine reviewed source files](verification/android-broader-pair7-integration/application-receipt.json) for fresh bare `mixer.android-source-pair.7`. It preserves 22 SDK members and selects 24 adapter members, covering 46 named members and 661,583 bytes. The axis `DocumentSession`, wire tuple and 9,587-byte default descriptor remain unchanged. [Independent review](verification/android-broader-pair7-source-review/seal.json) passes 300 source/data checks. Product tests, compiler invocations and native runs for this installed slice are zero; `.7` delivery and CI remain pending. Both old `.6` tuples, the historical broader id, mixed or drifted sources, recomputed locks and the old exact-profile driver remain refused.

Generated Android Debug/Release and actual relocated/exported consumer compilation remain pending at the integrated sources. The `.7` slice also needs fresh emitted closure for all 18 product Java files and actual generated Java. API28-35 full V2 remains refused by both below-36 guards; prior API28 collection proof is not inherited. These host and source receipts establish no Android UI/runtime acceptance.

Public FieldLog `00c8fe04` [host run 40820029857](https://github.com/snowdamiz/fieldlog/actions/runs/40820029857) remains historical with 39 accepted tests. Immutable published SDK consumption, native/full-owner integration, D0-D8 and release/GA acceptance remain pending. Gates remain **8 running, 30 planned, 0 verified**. Native/UI/capture and local compiler/custody holds remain, phones are disconnected, all seven held local groups and FieldLog run 40802230894 / PGID 2424 / PID 2621 stay untouched, and the v5 startup is not retried. [The tracking checkpoint](verification/pair7-tracking-checkpoint/observed-checkpoint.json) records the exact evidence and pending work.

## Previous delivered checkpoint at 2c751cbb

Mixer `2c751cbb` delivered the strict JSON binding correction in an exact 123-path slice. [The recovery receipt](verification/github-delivery-axis-binding-stage-recovery/stage-recovery-delivery-receipt.json) preserves the failed original staging attempt. [The recorded command audit](verification/axis-canonical-tracking-refresh/v2/command-closure-audit.json) accounts for 71 commands, with 70 exit-zero results and that one historical exit-one result. Every recorded command has exact reap, owned-group absence, separate stdout/stderr EOF and zero signals.

The [isolated axis run 40943215863](https://github.com/snowdamiz/mixer/actions/runs/40943215863) passes all eight XCTest and eleven Swift Testing methods at the delivered source. The actual host is macOS 15.7.9 ARM64, image `20260907.0337.1`, Xcode 26.3 and Swift 6.2.4. [Independent actual-data review](verification/android-axis-refusal-binding-host-actual-review/independent-review/seal.json) accepts 4,809 checks against the exact retained artifact. This establishes the isolated 27-file host behavior. Its single dispatch is consumed, with no remaining allowance.

The [six-file canonical source integration](verification/android-axis-canonical-source-integration/application-receipt.json) is now applied locally. Bare `mixer.android-source-pair.6` keeps the same 22 SDK members and selects the reviewed 23-member adapter projection, covering 45 named members and 569,431 bytes. The wire and default descriptor remain unchanged, and broader same-name tuple refusals remain. Delivery, canonical CI and generated Debug/Release, relocated and exported consumer evidence are pending at this integrated source.

The latest [Engine CI 40942282975](https://github.com/snowdamiz/mixer/actions/runs/40942282975) at `2c751cbb` completes with five successful jobs and one failed Swift job. [The failure review](verification/engine-ci-2c751cbb-swift-failure/REVIEW.md) records a compiler-selection refusal at `Accepted standalone analyzer fixture envelope`: the observed Apple ARM64 Rust 1.99.1 identity was outside the selected policy. All 22 adoption controls and eight postflights pass. Only five identity commands run and close; no fixture compilation or scratch starts. Later Swift SDK, CLI, raw-transport, TSan and generated-consumer steps are skipped. The earlier six-job pass at `2cea1013` remains historical.

Root [prospectively selects that exact observed Rust 1.99.1 identity](verification/envelope-rust-1991-default-ci-adoption/root-selection.json) for qualification through the next ordinary push. The derivative passes all 33 guarded synthetic controls. Focused independent review approves 1,649 source/data assertions across 139 inputs, without rerunning those controls. Root installs the exact prospective workflow. The controls use fake children. Their final recorded run takes 4.111 seconds; the earlier sealed 3.925-second result differs only in duration. Compiler qualification still requires the unchanged complete 40-command envelope and independent actual-evidence review. This selection grants no local compiler invocation or manual workflow dispatch.

Public FieldLog `00c8fe04` [host run 40820029857](https://github.com/snowdamiz/fieldlog/actions/runs/40820029857) remains accepted with 39 tests. Immutable published SDK consumption, native/full-owner integration, D0–D8 and release/GA acceptance remain pending. Gates remain **8 running, 30 planned, 0 verified**. Native/UI/capture and local compiler/custody holds remain, phones are disconnected, and held processes and the v5 startup stay untouched.

## Previous delivered checkpoint at 2cea1013

Mixer `2cea1013` [Engine CI 40907857341](https://github.com/snowdamiz/mixer/actions/runs/40907857341) passes all six jobs after the exact 174-path correction delivery. [The observed outcome](verification/android-axis-refusal-expression-host-failure-2026-10-29/observation.json) accounts for all 52 local Git/gh commands, with exact kernel reap, owned-group absence and separate stdout/stderr EOF. There were 173 changed paths and one unchanged selected file; delivery left the index empty and preserved unrelated changes.

The [first isolated axis run](https://github.com/snowdamiz/mixer/actions/runs/40909865814) reached its binding step and failed before Apple probes or Swift. The verifier compared JSON object insertion order; the producer sorted keys without changing values. [Fresh Astra diagnosis](verification/android-axis-refusal-expression-host-failure-2026-10-29/astra-review/REVIEW.md) traces the exact 1,624-byte input through all five logged environment appearances and audits 76 equality calls. Postflight reached its source-after write, which failed because the output directory did not exist. Assessment also failed, and the uploader warned that there were no files. No artifact or test success is inferred. The one manual allowance is consumed with no replay; all eight XCTest and eleven Swift Testing methods remain unrun.

The [strict JSON comparator correction](verification/android-axis-refusal-host-admission-binding-correction/README.md) is installed after [189 passing data controls and one composed preflight](verification/android-axis-binding-controls-actual/receipt.json), with independent source and actual-data review. Its fresh source-bound host run awaits delivery. Canonical source pair.5 remains SDK22/adapter23; the prepared axis-only .6 integration remains unapplied. The prior Android package run 40895131023 retains its accepted seven commands, 13 groups and 2,227 assertions at its own revision; it has no remaining allowance.

Public FieldLog host evidence remains 39 tests at 00c8fe04. Immutable published SDK consumption, native/full-owner integration, D0–D8 and release/GA acceptance remain pending. Gates remain **8 running, 30 planned, 0 verified**. Native/UI/capture and local compiler/custody holds remain, phones are disconnected, and held processes and the v5 startup stay untouched.

## Previous delivered checkpoint at c89b4d16

Mixer `c89b4d16` [Engine CI 40883834822](https://github.com/snowdamiz/mixer/actions/runs/40883834822) passes all six jobs after the exact 256-path delivery. [The observed outcome](verification/android-host-followup-outcome-2026-10-29/observation.json) accounts for all 50 local Git/gh commands with kernel reap, owned-group absence and separate stdout/stderr EOF. The original CI-binding phase remains 8/11 incomplete because the axis workflow was invalid. Independent package binding and one durable submission succeeded; its allowance is exhausted.

The [focused Android run](https://github.com/snowdamiz/mixer/actions/runs/40895131023) passes all seven commands, 13 groups and 2,227 reported assertions, covering 152 source-correlated interruption invocations. [Actual evidence review](verification/android-view-api-package-runtime-actual-review/ACTUAL-REVIEW.md) verifies the 742-file archive, all 74 package-observed runtime files, 337 host classes, 214 SDK classes and one 414,640-byte DEX. [Independent binary review](verification/android-view-api-package-runtime-binary-review/REVIEW.md) reproduces all three reports against the exact SDK37 jar. All 214 SDK classes occur in the 383-class DEX; the 169 additional classes have D8 synthetic SourceFile markers. The empty synthetic-owner-name heuristic does not imply zero generated classes. The original official JDK profile is unchanged, and package provenance remains unproven.

GitHub [rejected the original axis workflow](https://github.com/snowdamiz/mixer/actions/runs/40883832500) before any job because `runner.temp` was used in job-level environment configuration. [The exact correction is installed](verification/android-axis-expression-selection-2026-10-29/source-installation.json), with 18 actual source/data controls, independent Sol review and fresh Astra review. The prior 47 parser controls retain their original attribution. Delivery, GitHub validation and the first eight XCTest plus eleven Swift Testing methods remain pending; no axis manual submission occurred. Canonical source pair.5 remains SDK22/adapter23.

The first artifact link expired before download; its HTTP 403 and zero-byte result are preserved. A separately selected recovery retained the exact archive with consumer EOF and reader release. Source scratch and nonce reservations remain retained. No independent transport/kernel trace or provider disposal is inferred.

Prior canonical bitmap evidence remains attributed to `5b6fc4f5`, including 699 all-feature tests per Debug/Release mode. Public FieldLog `00c8fe04` host run 40820029857 remains accepted with 39 tests and zero source compiler warning diagnostics. Immutable published SDK consumption, native/full-owner/source-pair integration, D0–D8 and release/GA acceptance remain pending. Gates remain **8 running, 30 planned, 0 verified**. Native/UI/capture, local compiler/custody and older holds remain; phones are disconnected and the held v5 startup is not retried. FieldLog run 40802230894 / PGID 2424 / PID 2621 stays untouched.

## Previous delivered checkpoint at 47b62878

Mixer `47b62878` [Engine CI 40863262879](https://github.com/snowdamiz/mixer/actions/runs/40863262879) passes all six jobs after the exact 74-path JDK observation delivery. All 46 local Git/gh commands record kernel reap, owned-group absence and separate stdout/stderr EOF. [The new outcome](verification/android-jdk-data-outcome-2026-10-29/observation.json) preserves the single dispatch visibility race and confirms one successful diagnostic run; neither manual allowance has any remaining attempt.

The [actual JDK data audit](verification/android-view-api-focused-actual-review/jdk-data-actual-review/actual-review-receipt.json) verifies all 13 artifact files and 74 complete source-bound file observations: 72 whole-file hashes match the official release, while `ct.sym` and `jrt-fs.jar` differ. Both inert exports match their installed package checksum records for `temurin-17-jdk` version `17.0.21.0.0+9-0`. The artifact environment reports image `20261026.354.1`, while the job setup log names `20261025.353.1`; that discrepancy remains explicit. These data do not identify the older focused run’s bytes or establish package provenance.

The [completed inner archive comparison](verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/actual-data-execution/result-summary.json) preserves all 13,653 non-directory `ct.sym` entry names and payloads. Exactly 204 empty directory names change from double to single trailing slashes. All 61 `jrt-fs.jar` entry names and payloads match; compression and metadata also differ. The narrow parser correction passes 104 guarded controls, and [independent actual review](verification/android-jdk-comparison-challenge/ACTUAL-RESULT-REVIEW.md) passes 329 data assertions. Four comparison invocations and three archive acquisitions are closed with zero remaining allowance; all prior failures remain. A [separate exact package-observed profile and one fresh focused run are selected](verification/android-package-jdk-host-selection-2026-10-29/root-review.json), with 282 guarded controls and 234 independent source/data checks passed. The original official profile remains unchanged. Its new workflow is installed; delivery and exact dispatch binding remain pending. The original seven Java commands, thirteen groups, 152 interruptions and class/DEX checks remain unrun.

The [axis refusal host package](verification/android-axis-refusal-host-preparation/proposal.md) contains 27 frozen files and has independent source review. The corrected host admission passes 47 data controls and actual filesystem fixtures; an unexpected quoted success is refused. [Its exact workflow is installed](verification/android-axis-host-selection-2026-10-29/root-review.json), with one first host run pending coherent delivery and revision binding. Eight XCTest and eleven Swift Testing methods remain unrun; canonical source pair.5 remains SDK22/adapter23.

Prior [canonical bitmap evidence](verification/bitmap-canonical-ci-2026-10-29/REVIEW.md) remains attributed to `5b6fc4f5`, including 699 all-feature tests per Debug/Release mode. FieldLog `00c8fe04` [host 40820029857](https://github.com/snowdamiz/fieldlog/actions/runs/40820029857) remains accepted with 39 tests and zero source compiler warning diagnostics; native, immutable published-package and D0–D8 acceptance remain pending.

Gates remain **8 running, 30 planned, 0 verified**. Native/UI/capture, phones, local compiler/custody, Unit A and broad hosted holds remain. The held v5 startup is not retried. FieldLog run 40802230894 / PGID 2424 / PID 2621 remains held without probes or disposal assumptions. Raw CI/archive/helper data stays local.

## Previous delivered checkpoint at df0d15f9

Mixer `df0d15f9` [Engine CI 40853352784](https://github.com/snowdamiz/mixer/actions/runs/40853352784) passes all six jobs after the exact 227-path isolated Android source/admission delivery. All 46 local Git/gh commands record exact kernel reap, owned-group absence and separate stdout/stderr EOF; unrelated work remains preserved. The single focused manual run refused JDK preflight before any Java child, as detailed below.

At canonical bitmap revision `5b6fc4f5`, [root CI review](verification/bitmap-canonical-ci-2026-10-29/REVIEW.md) verifies 306 successful VM summary rows. All-feature Debug and Release each pass 690 regular tests plus all nine explicitly executed Node checks, 699 per mode. Every new bitmap test passes in four configurations. Defaults, private-reactor, allocation isolation and strict library Clippy also pass at their recorded scopes. Ordinary CI uses Rust 1.99.1; prior exact-candidate formatting, strict all-target Clippy and manual Debug/Release remain attributed to their original runs. Other jobs received terminal metadata inspection.

The [canonical 136-member closure](verification/bitmap-canonical-integration-2026-10-29/installation.json) contains two changed runtime files and 13 changed test files; 121 others, public ABI, dependencies and defaults remain unchanged. Original admission already rejected more than 64 active pins. The historical 512-resident/128-pin source experiment is separate and not requalified.

The [Android view API derivative](verification/android-view-api-boundary-root-source-review/REVIEW.md) remains accepted for source and focused test design: two changed files, 14 unchanged product files, 36 source/data checks and 11 corruption controls. API29/30 calls are isolated; original authority order and both below-36 guards remain. Canonical source pair.5 remains 22 SDK / 23 adapter inputs; this derivative has no canonical or lower-API full V2 authority.

The [227-path slice is delivered](verification/android-view-api-focused-outcome-2026-10-29/README.md) as `df0d15f90f2bc5e702127bdf6ab79f3d8e3d0cce`; standard CI run 40853352784 passed all six jobs. The single focused run 40854344723 refused initial JDK preflight because `lib/ct.sym` differed from its fixed official-archive pin. Zero owned Java children started. All seven commands, thirteen groups, 152 interruptions, class emission and DEX checks remain unrun. The actual mismatching file identity and cause are unknown, and the allowance is consumed without retry. [One separate filesystem-only JDK/package observation is selected](verification/android-jdk-data-observation-selection-2026-10-29/root-review.json), pending exact delivery and phase admission. All 42 actual guarded Python pure-function checks pass. It reads the fixed 74-member manifest and bounded package metadata, retaining only the two selected archive files as data; it runs zero Java or other child commands. Its new allowance is distinct from the consumed focused run.

A separate [Android axis refusal candidate](verification/android-view-api-source-pair-reconciliation/axis-refusal-candidate/README.md) now rejects explicit text-field axis properties before reconciliation or state publication, while preserving generic validation priority and typed horizontal omission. Independent source review found no blocker. Eight new host tests and eleven existing runtime/transaction tests remain unrun; no canonical change or new source-pair selection is made.

FieldLog `00c8fe04` [host 40820029857](https://github.com/snowdamiz/fieldlog/actions/runs/40820029857) remains accepted with 39 passing tests and zero source compiler warning diagnostics. Native, immutable published-package and D0–D8/GA qualification remain pending.

Gates remain **8 running, 30 planned, 0 verified**. Native/UI/capture, phones, local compiler/custody, Unit A and broad hosted holds remain. The held v5 startup is not retried. FieldLog 40802230894, PGID 2424 and PID 2621 remain held without probes or disposal assumptions. Raw CI/archive/helper data stays local.

## Previous delivered checkpoint at 32ef6faf

Mixer `32ef6faf` [Engine CI 40828151608](https://github.com/snowdamiz/mixer/actions/runs/40828151608) passes all six jobs. The exact 53-path delivery preserves unrelated work; all 58 Git/gh admissions have recorded direct reap, owned-group absence and separate stdout/stderr EOF. These ordinary CI observations are terminal metadata; earlier full fixture/envelope audits retain their original attribution.

The first [Release completion 40828181211](https://github.com/snowdamiz/mixer/actions/runs/40828181211) independently passes 699 tests across 37 groups, with zero failed or ignored tests and all nine Node oracles. [Actual review](verification/swift-pin-bitmap-release-actual-review/sanitized-result.json) verifies 937 evidence checks plus 19 parser refusal controls. Every test identity and group membership matches the prior successful Debug output. All three managed commands, source/tool postflights and scratch cleanup pass. Prior formatting, strict Clippy and Debug results remain attributed to run 40824584975, whose failed original parser admission is preserved. No such command was repeated.

Root has [installed the exact tested candidate](verification/bitmap-canonical-integration-2026-10-29/installation.json): two runtime files and 13 test files, with all 136 source members matching the accepted closure and all 121 other members unchanged. [Focused semantic review](verification/swift-pin-bitmap-canonical-semantic-review/REVIEW.md) confirms that original admission already rejected more than 64 active pins. Public ABI, dependencies, all 17 defaults and production limits remain unchanged. The historical 512-resident/128-pin experiment used a separate generated source variant and is not requalified here. Canonical delivery and its ordinary CI remain pending.

FieldLog `00c8fe04` [host 40820029857](https://github.com/snowdamiz/fieldlog/actions/runs/40820029857) remains independently accepted with 39 passing tests and zero source compiler warning diagnostics. Native, immutable published-package and D0-D8/GA qualification remain pending.

Gates remain **8 running, 30 planned, 0 verified**. Native/UI/capture, phones, local compiler/custody, Unit A and broad hosted holds remain. FieldLog 40802230894, PGID 2424 and inner PID 2621 remain held without probes or disposal assumptions. Raw CI, archives and helper evidence stay local.

## Previous delivered checkpoint at 1eec8e0f

Mixer `1eec8e0f` [Engine CI 40824567237](https://github.com/snowdamiz/mixer/actions/runs/40824567237) passes all six jobs. Terminal metadata confirms this exact-head result; earlier full fixture and envelope artifact audits retain their original run attribution. The 64-path delivery preserves unrelated work, and all 65 Git/gh command admissions have recorded direct reap, owned-group absence and separate stdout/stderr EOF.

The [VM attempt 40824584975](https://github.com/snowdamiz/mixer/actions/runs/40824584975) passes compiler/Node identity, formatting and strict all-target Clippy. Debug exits zero with 37 groups totaling 699 passes, zero failed or ignored tests and all nine Node oracles. The harness nevertheless fails because its terminal parser misses 11 doctest names containing spaces and six results separated by trace output. [Independent review](verification/swift-pin-bitmap-match-actual-review/sanitized-result.json) reconstructs all 699 successes with 301 artifact checks; the failed admission remains recorded. Release never starts. All five started children/groups close, every source/tool postflight passes and scratch is removed. Formatting changes no bytes; the complete candidate closure remains unchanged.

Root has reviewed the strict parser correction (81 controls), the Release-only admission (40 controls) and 97 independent parser/admission controls. [One bounded first Release completion is selected](verification/bitmap-release-completion-host-selection-2026-10-29/root-review.json): compiler and Node identity, then the original Release vector, with 660 active seconds plus 60 cleanup seconds. The installed source/binding check passes. Successful Debug, formatting and Clippy retain their prior attribution. Actual Release and canonical VM integration remain pending; production limits are unchanged.

FieldLog `00c8fe04` [host 40820029857](https://github.com/snowdamiz/fieldlog/actions/runs/40820029857) remains independently accepted with all 39 tests passing and zero source compiler warning diagnostics. [Review](verification/fieldlog-projector-warning-host-review/root-summary.json) preserves unrelated SwiftPM/action warnings and the native, immutable published-package and D0-D8/GA boundaries.

Gates remain **8 running, 30 planned, 0 verified**. Native/UI/capture, phones, local compiler/custody, Unit A and broad hosted holds remain. FieldLog 40802230894, PGID 2424 and inner PID 2621 remain held without probes or disposal assumptions. Raw CI, archives and helper evidence stay local.

## Previous delivered checkpoint at 88c32d7f

Mixer `88c32d7f` [Engine CI 40822174506](https://github.com/snowdamiz/mixer/actions/runs/40822174506) passes all six jobs. The partitioned envelope is now accepted in ordinary CI: [independent artifact review](verification/envelope-ordinary-actual-review/sanitized-result.json) verifies 1,479 assertions, all 40 commands, 78 producer methods across 18 groups, 14 independent methods, 32 layouts and 21,714 comparisons on the unchanged Rust 1.98.1 ARM64 policy. All 92 retained payloads, eight source postflights, 40 direct/group/pipe closures and scratch cleanup pass. Other jobs received terminal metadata/log inspection; their older full artifact audits retain their original attribution. Timing does not establish a causal speedup.

The sole [VM lint/regression attempt 40822264739](https://github.com/snowdamiz/mixer/actions/runs/40822264739) passes all 43 guarded controls, compiler identity, Node identity and formatting, then fails Clippy with one `blocks_in_conditions` error in the constructor test. Debug and Release correctly remain unrun. [Independent failure review](verification/swift-pin-bitmap-lint-actual-review/sanitized-result.json) verifies 209 checks, all 15 formatting before/after pairs, four recorded child/group closures, complete source/tool postflights and scratch removal. The old allowance is consumed.

Root reviewed the exact correction: assign the unchanged constructor block to `construction_result`, then match it. The other 14 overlays retain the actual formatter bytes. All 654 source checks and 43 rebound host controls pass. [One new-source host attempt is selected](verification/match-binding-host-selection-2026-10-29/root-review.json) with the same six commands, limits, compiler/Node rules, strict Clippy warnings and 699 expected tests per Debug/Release including all nine Node oracles. Actual new execution remains pending; canonical VM source and production limits remain unchanged.

FieldLog `00c8fe04` [host 40820029857](https://github.com/snowdamiz/fieldlog/actions/runs/40820029857) remains independently accepted with all 39 tests passing and zero source compiler warning diagnostics. The three late-save joins and projection-failure behavior are covered; unrelated SwiftPM/action warnings stay recorded. [Review](verification/fieldlog-projector-warning-host-review/root-summary.json) preserves all transport/source/custody limits and the native, immutable published-package and D0-D8/GA boundaries.

Gates remain **8 running, 30 planned, 0 verified**. Native/UI/capture, phones, local compiler/custody, Unit A and broad hosted holds remain. FieldLog 40802230894, PGID 2424 and inner PID 2621 remain held without probes or disposal assumptions. Raw CI, archives and helper evidence stay local.

## Previous delivered checkpoint at 6d57e05e

Mixer `6d57e05e` [Engine CI 40814685299](https://github.com/snowdamiz/mixer/actions/runs/40814685299) passes all six jobs. The clock-corrected ordinary fixture passes all 61 controls and 103 commands, verifies its exact 137-member dependency closure and installed job before/after execution, and retains every original method, vector and capture inventory. It uses the existing Rust 1.98.1 ARM64 compiler. All 103 recorded direct children/groups close and scratch is removed; explicit pipe-EOF flags remain unavailable. The earlier four-control failure and skipped fixture at `836fc67b` remain preserved.

The sole [formatting/lint diagnostic 40814738980](https://github.com/snowdamiz/mixer/actions/runs/40814738980) collects both arms successfully, but **both Clippy commands fail** under unchanged `-D warnings`: 50 baseline and 46 candidate error observations. The multiset has 45 shared, five baseline-only and one candidate-only observation; parallel compilation and these partial diagnostic sets do not establish causation. Standard Rust 1.99 formatting artifacts are retained for the exact four-file candidate. All five recorded children/groups and both-arm source postflights pass; scratch is removed. [Actual review](verification/clock-format-actual-results/sanitized-result.json) passes 34,222 guarded data assertions across the fixture and formatting results. The one manual allowance is consumed. A narrow source correction now addresses the observed lint findings while preserving allocation assertions; no canonical VM installation is accepted.

The earlier corrected [bitmap lifecycle run 40810326741](https://github.com/snowdamiz/mixer/actions/runs/40810326741) passes all six Cargo commands. Debug and Release each report 690 passed and nine explicit Node-oracle ignores. The [partitioned envelope run 40810340963](https://github.com/snowdamiz/mixer/actions/runs/40810340963) passes all 40 commands, 78 producer plus 14 independent methods, 32 layouts and 21,714 comparisons, with all recorded child/group/pipe closures and scratch cleanup. Ordinary envelope adoption is independently reviewed and installed for the next coherent push, using this exact source and the unchanged compiler policy. Neither timing sample proves a causal speedup; production defaults remain unchanged.

FieldLog `00c8fe04` [host run 40820029857](https://github.com/snowdamiz/fieldlog/actions/runs/40820029857) passes all 39 distinct tests with zero source compiler warning diagnostics. [Independent review](verification/fieldlog-projector-warning-host-review/root-summary.json) rederives the exact one-file test correction, five source phases, three typed declaration/consumption comparisons, 11 metadata audits, eight full SDK blob audits and recorded closure of 39 outer groups, 59 registered groups and 195 inner children. All 53 local delivery commands have separate stdout/stderr EOF; no signals were sent. The preceding [39-test editor run](https://github.com/snowdamiz/fieldlog/actions/runs/40818275229) independently passed with its original warning retained. Three late-save tests now join completion, and the new owner-level projection-failure test preserves text and revokes input/effects. Other SwiftPM/action warnings remain recorded. Native/device, mutable remote filesystem, arbitrary descendants, immutable published-package and D0-D8/GA qualification remain unproven.

Root has installed and selected [the next coherent host slice](verification/envelope-lint-host-selection-2026-10-29/root-review.json). Ordinary CI adopts the exact partitioned envelope with unchanged compiler rules. A separate one-attempt VM workflow will run the corrected formatter/Clippy candidate, then full Debug and Release suites with all nine Node oracles enabled (699 expected tests per mode). Its 43 guarded controls pass; the six managed commands have 1,800 active seconds plus 60 cleanup seconds. Failure-evidence corrections reject contradictory test summaries and retain safe formatter evidence before roster refusal. Actual new CI remains pending; canonical VM source and production limits remain unchanged.

Gates remain **8 running, 30 planned, 0 verified**. Native/UI/capture, phones, local compiler/custody, Unit A and broad hosted holds remain. FieldLog run 40802230894, PGID 2424 and inner PID 2621 remain held without probes or disposal assumptions. Raw CI, formatted files and helper evidence stay local.

## Previous delivered checkpoint at 836fc67b

Mixer `836fc67b` [Engine CI 40810235312](https://github.com/snowdamiz/mixer/actions/runs/40810235312) passes five jobs and fails the fixture controls. The 16 adoption and nine materializer controls pass; four of 36 runner controls fail because their synthetic clock is paired with a deadline created from the real host clock. The complete 103-command fixture is skipped. The one-line test-helper correction is independently reviewed and installed for the next ordinary CI run; the production runner, compiler policy and fixture deadlines remain unchanged. The previous complete ordinary fixture pass at `c7648ab4` remains valid evidence for that run.

The corrected [bitmap lifecycle run 40810326741](https://github.com/snowdamiz/mixer/actions/runs/40810326741) passes all six Cargo commands on Rust 1.99.0 Linux. Debug and Release each report 690 passed and nine explicit Node-oracle ignores, including successful corrected SL13/SL14 fixtures. All six 136-member source postflights match; seven recorded children/groups close and three owned roots are removed. Explicit pipe-EOF flags and installer-descendant custody remain unavailable. A corrected five-child formatting/Clippy diagnostic is selected for one fresh host attempt. Actual formatting, Clippy and canonical VM integration remain pending; production defaults are unchanged.

The [partitioned envelope run 40810340963](https://github.com/snowdamiz/mixer/actions/runs/40810340963) passes all 40 commands on the existing Rust 1.98.1 ARM64 compiler: 78 producer methods across 18 groups, 14 independent methods, 32 layouts and 21,714 comparisons. All recorded children/groups and both pipes close, all eight source postflights pass and scratch is removed. The 120-second per-group limit is unchanged; neither this run nor the earlier unpartitioned pass establishes a causal speedup. [Independent actual-results review](verification/corrected-host-diagnostics-actual-results/sanitized-result.json) verifies 3,714 assertions across these two diagnostics and the fixture failure. Both selected manual allowances are consumed.

FieldLog is public at `46d59fbe`. [Host run 40813169278](https://github.com/snowdamiz/fieldlog/actions/runs/40813169278) passes compilation and all 38 observed host tests after the runner-only declaration correction. The [delivery audit](verification/clock-format-host-selection-2026-10-29/fieldlog-host-result.json) verifies exact SDK consumption, five source phases, three public-to-owned-mirror declaration comparisons, 11 metadata audits and eight blob-body audits. All 39 outer commands, 59 registered groups and 195 inner children have recorded terminal custody; no signals were sent. Independent artifact review is in progress. The older run 40802230894 remains held without probes or disposal assumptions. Native and immutable published-package qualification remain pending.

Gates remain **8 running, 30 planned, 0 verified**. Native/UI/capture, phones, local compiler/custody, Unit A and broad hosted holds remain. Raw CI and helper evidence stay local. No native, published-package dogfood or GA acceptance is implied.

## Previous delivered checkpoint at c7648ab4

Mixer `c7648ab4` [Engine CI 40806044568](https://github.com/snowdamiz/mixer/actions/runs/40806044568) passes all six jobs and 65 steps. The shared-input fixture is adopted in ordinary CI: 61 focused controls, all 103 fixture commands and complete original inventories pass on the existing Rust1.98.1 ARM64 compiler. The unchanged envelope runner also passes its original 23 commands and 78 producer plus 14 independent methods; producer execution takes 96.206916 seconds under the same 120-second bound. The prior timeout remains preserved, with no causal timing claim. [Actual review](verification/reviewed-host-slice-actual-results/sanitized-result.json) records 11,607 independent data assertions across these results and the bitmap failure.

The sole [bitmap run 40806119805](https://github.com/snowdamiz/mixer/actions/runs/40806119805) passes the seven new owner tests and cache/frame regressions, then fails the all-feature Debug suite at two lifecycle fixtures (465 pass, two fail). Their expected constructor and pin-selection costs still describe the previous implementation. The source-derived test correction is reviewed and selected for one fresh regression; the optimized all-feature suite remains unrun, and no canonical VM installation is selected. All six recorded children closed and three owned roots were removed. The failed Cargo command has no observed final source postflight; that limitation is preserved.

FieldLog is public at `087f502b`. [Run 40808838978](https://github.com/snowdamiz/fieldlog/actions/runs/40808838978) now resolves the dependency and completes one audited SDK checkout, then fails at app declaration validation because SwiftPM reports its configured file mirror and default traits. Build and all 38 tests remain unrun. All 19 outer commands, 26 registered groups and 132 inner children have verified terminal records; output remains within the selected caps. A narrow source correction will bind the original public declaration to the exact owned mirror. The older run40802230894 remains held without probes or disposal assumptions.

Root has selected [two fresh bounded diagnostics](verification/next-host-diagnostics-selection-2026-10-29/selection.json): the source-derived lifecycle accounting correction with 35 guarded admission controls, and the unchanged envelope partition candidate with corrected workflow context placement and 31 guarded review/context controls. Each has a separate one-attempt allowance; corrected Rust execution and partition execution remain pending. Canonical VM source and production limits remain unchanged.

Gates remain **8 running, 30 planned, 0 verified**. Native/UI/capture, phone, local compiler/custody, UnitA and broad hosted holds remain. Raw CI and helper evidence stay local.

## Previous bounded host results

The VM original two-corpus run is independently accepted for scoped Linux host feasibility: both eleven-field observations match, full wall time is 599.150431397 seconds, all final logical/live/ticket currents are zero, six command groups closed and scratch was removed. [Actual review](verification/github-delivery-dense512-completion/ci-review/receipt.json) records 2,757 independent assertions and the precise admission/output limitations. Its 1,200-second/4B-fuel profile remains experimental. The separately reviewed bitmap-pin source candidate preserves canonical limits and is selected for bounded hosted regression; no production default or signed authority changes are accepted.

The corrected fixture [run 40801256712](https://github.com/snowdamiz/mixer/actions/runs/40801256712) at `00e08721` passes explicit exact Rust1.98.1 provisioning, 79 focused controls and all 103 original fixture commands. Both complete 1,003-vector closures, all required Debug/optimized methods, API negatives, captures, output hashes and postflight/owned-fixture cleanup pass. [Independent result](verification/github-delivery-fixture-context-v4/sanitized-result.json) passes 9,411 assertions. Rustup descendant reap and provider disposal remain unverified; no causal speedup claim is made. Separate ordinary Engine [40801222690](https://github.com/snowdamiz/mixer/actions/runs/40801222690) fails only its Swift envelope step: producer-execute reaches the unchanged 120-second timeout after 76 terminal successes of 78 expected methods, with no retained assertion/panic diagnostic. Recorded child/group cleanup and postflight pass; five other jobs pass. The frozen failed run remains preserved while a source-only partition/setup correction is prepared.

FieldLog public `6276e6ae` [run 40802230894](https://github.com/snowdamiz/fieldlog/actions/runs/40802230894) passes the selected immutable-manifest read and ordered optional-metadata denial pair, then advances to precheckout work. Its sixth metadata audit exceeds the unchanged aggregate16MiB output limit; no actual checkout clone or any of the 38 tests starts. [Small result](verification/host-diagnostic-checkpoint-2026-10-29/fieldlog-output-held.json) records 11 of 12 outer groups closed, 16 registered groups reported absent, and 72 terminal reaps for 73 inner children. **That remote run remains held:** host-resolve group absence/EOF and the final inner-child reap are unverified, with ambiguous-permission evidence. Remote PGID2424 and child2621 will not be probed, signalled or retried; runner disposal is not assumed. A fresh source-only audit/output and cleanup correction is under preparation, with no further host attempt selected. Earlier unknown adapter identities and eight unreceipted local reads remain historical limitations.

Gates remain **8 running, 30 planned, 0 verified**. Native/UI/capture, disconnected phones, local compiler/custody, UnitA and broad hosted holds remain. Raw CI stays local. [Checkpoint](verification/host-diagnostic-checkpoint-2026-10-29/checkpoint.json) binds these results; no native, published-package dogfood or GA promotion is selected.

## Closed public host campaigns

Mixer `295f3f18` passes all six ordinary Engine jobs. The explicit 128-frame /
128-pin comparison also completed its diagnostic workflow: both variants passed
compilation, nine/ten finite controls, their original harness and the unchanged
256 MiB envelope. Both reached 67 frames/pins, then exhausted the 768M cache-work
budget in Corpus 1 at about 790M instructions. Neither completed the original
11-field corpus observation or started Corpus 2. All eleven command groups
closed, scratch was removed and final owner ledgers/tickets were zero. The two
full attempts are spent; no retry or production/default promotion is selected.

FieldLog is public at `de09821b`. The reviewed four-file transport candidate
passed 106 pure controls and was delivered with one host dispatch. Git 2.55
fetched the exact pinned SDK's filtered metadata in a small owned store
(1 commit, 27,424 trees, zero blobs; 6,573,259 bytes), then its explicit 73-blob
request failed with “bad revision” and missing necessary objects. The run did
not reach SwiftPM resolution, compilation or any of the 38 authored tests.
All nine remote outer groups, 21 inner children and 49 local delivery commands
closed. This establishes the observed hydration failure, not a server-policy
refusal. The immutable SDK pin and all prior failed evidence remain preserved.

[Small sealed summaries](verification/public-host-campaigns-2026-10-28/checkpoint.json) bind both actual results;
raw CI remains local. Fresh bounded source experiments now address the Git
hydration command and VM cache work/capacity. A separate review covers a fixture
setup optimization; the existing fixture CI currently passes. No further run is
selected by this checkpoint. Gates remain **8 running, 30 planned, 0 verified**;
native/UI/capture, physical-phone, local compiler/custody and Unit A holds remain.

## Historical frame and pin selection

Current baseline `5efcb6a2` CI is independently reviewed: all six Engine jobs
succeeded; ordinary Phoenix formatting/compilation and 701 methods pass, with
two expected network skips (703 total), including all four new TLS controls.
The isolated network lane passes 141 collector controls and both exact methods
without skips, with 137 commands, 131 metadata members, final source bindings
and all three exact container cleanups verified. Phoenix's 43 command hashes,
PostgreSQL stop and scratch removal are verified. Only the
[sanitized summary](verification/github-delivery-frame-pin-128/public-summary-candidate.json)
is delivered; raw CI remains local. FieldLog `146f2a27` still has no observed
host tests after its 180-second dependency fetch timeout; all ten remote groups
closed. The new transport candidate passed 54 pure methods, but independent
review found the `--[no-]` help-token parsing blocker; its narrow correction is
pending and no new host run is selected by this delivery.

Root selects `paired-128-v1` for one remote comparison after independent Astra
source review: 152 producer structural/arithmetic checks, 39 pure runner methods,
117 independent binding/workflow checks, 11,716 bitmap cases, 293 runner cases,
three mutation witnesses and 39 replayed methods pass. The exact reviewed workflow
is installed unchanged. Both Rust 1.99.0 optimized builds, nine/ten finite tests,
compiled geometry, zero cleanup and original harness controls must pass before
either full attempt. The cap is two full attempts, eleven commands and 2,700
seconds. Both arms use 128 frames/pins, 256 residents, the unchanged 256 MiB
combined envelope, 1B fuel, 8B execution credits, 768M cache credits and 600,000ms
cumulative Runtime/WASI duration; dense uses two u64 bitmap words. Compilation
and all new actual runtime behavior remain pending. No retry, resume, production
default promotion or GA acceptance is selected.

The previous comparison `40768719255` is closed: both arms failed at FrameLimit
65/64 in Corpus 1, with no full original observation or Corpus 2. All eleven
commands closed and final owner ledgers reached zero. Its matched-prefix dense
elapsed reduction is one diagnostic sample, not a production winner. The failed
baseline remains preserved. [Selection](verification/github-delivery-frame-pin-128/selection.json)
binds both reviewed packets, source closures, finite admission and one-dispatch
authority. Gates remain 8 running, 30 planned, 0 verified; all native/UI/capture,
physical-phone, local custody and Unit A holds remain.

The October 28 planning update adopts empirical resource-budget calibration and
aggressive bounded blocker experiments, with fresh Astra 6 Extra High escalation
after repeated failed or preparation-only cycles. Native shared FieldLog flows
remain an independent integration priority. [ADR 0002](docs/adrs/0002-empirical-budgets-and-blocker-experiments.md)
defines the first cache-capacity/work-allowance comparison. This update changes
execution policy only: no VM run, runtime limit, implementation acceptance or
GA status changes. Native/UI/capture, physical-phone and local custody/UnitA
restrictions retain their actual state. Validation is recorded in
[the plan receipt](verification/blocker-experimentation-plan-2026-10-28/receipt.json).

Current fixture format correction: Phoenix `40775131269` stopped before compilation and all four new controls at one long TCP assertion. The exact emitted whitespace diff is applied and separately bound by immutable amendment v2: 178 sources / `8d0139c8c64e02f29f42a96384661f60dd7b724fa5fb4d5f54f6e7c1b7b78cd3`. All 141 pure collector controls pass with children/sockets denied; the initial wiring-control failure is retained. Historical 177/023df04 and v1 178/ab8f8d packets and the accepted semantic review remain unchanged. The TLS fixture bytes, four control assertions, original production method bodies and argv are preserved. Fresh formatted-source compile, four ordinary Phoenix controls and both network methods remain pending. [Selection and limits](verification/github-delivery-fixture-format/selection.json) binds the exact diff, helper/source/archive/prepared/compiled comparisons and reviewed prior CI. No local formatter/Elixir/compiler/Docker/PostgreSQL/native/UI/capture or held-group probe ran. Gates remain 8 running, 30 planned, 0 verified.

Independent artifact review of `86a96a4b` network run `40775131359` verifies both original methods pass with zero failures/skips/exclusions against historical v1 178/ab8f8d. All 135 command streams are complete; 123 metadata members, seven helpers, 1,233 prepared files, 955 compiled modules including 113 JOSE Erlang modules, both semantic receipts, ten migrations and final input equality are verified. Key directories are empty and all three exact containers were removed and observed absent. Phoenix `40775131269` proves only the formatting failure; its four new controls were unrun. Large raw CI evidence stays local. The earlier architecture run `40768719255` closed both attempts at FrameLimit 65/64 in Corpus 1 with no complete observation or Corpus 2. Its Frame128/pin128 source candidate has 152 producer and 39 independent pure checks and is entering independent review; compiler/full runs remain zero. Public FieldLog `146f2a27` run `40771309900` failed dependency-pin fetch at 180.084 seconds before host phases, with zero observed tests, unavailable failure count and ten remote groups cleaned. An executable filtered transport candidate is being implemented and has not been delivered or run. No new architecture/FieldLog acceptance or GA verification is implied.

Historical timestamp-only checkpoint: the minimal positive prepared-archive timestamp correction is independently accepted for fresh isolated CI after 129 producer and six independent pure controls; all 126 original test bodies, 1,232 payload entries and 177 product files remain unchanged. Mix 1.20.4 treats a missing target as time zero, so epoch-zero inputs omitted 97 of JOSE's 113 Erlang modules. The prior exact `8888d8e2` network run `40766689512` passed the 895-byte Rebar capture but failed both product methods with `:jose_jwk` unavailable; all three container cleanups passed. Corrected compilation and both product methods remain pending. Source-pair5 now has actual host evidence: 132 Swift Testing SDK tests plus eight XCTest tests, 69 update tests, 31 CLI tests and 30 Python CLI tests passed, including ten source-pair methods. Negative cases use actual rendered children; the positive tool-order sentinel is in process and proves no Android child build. The generated consumer passed four host tests and an iOS simulator-target cross-build with no simulator boot. Engine run `40766689541` still failed the 60-second `context_schema_scalar_reserved_and_lengths` cache-fixture test; five other jobs passed and cleanup completed. Phoenix run `40766689598` passed 697 tests with two skips plus 45 protocol, 24 storage and one migration checks. Architecture run `40768719255` at `dfd0e319` was in progress at the saved 21:05 UTC observation after pure controls and compiler installation; actual full results remain unknown, with two maximum attempts and no retry. FieldLog public `4d17c926` run `40765792113` timed out its `swift-test` command at 480 seconds after pinned SDK resolution, with no observed build completion or test start; failure count is unavailable, all 16 remote groups closed and one SIGTERM was used. Post-test SDK and lock checks were unreached. Its same-pin phase-split diagnostic is under preparation and has not been selected or pushed. The large raw CI review stays local; [published summaries and timestamp selection](verification/github-delivery-positive-timestamp/selection.json) bind its metadata and hashes. Native/UI/capture, disconnected-phone and all local custody/UnitA holds remain; gates stay 8 running, 30 planned, 0 verified.

Checkpoint `56ff14c` passes exact binary exports, locked dependency preparation, archive/restore, PostgreSQL isolation and offline compilation in the isolated network lane. It then rejects one fresh 895-byte Rebar `source.dag` after command 89; zero product methods ran, all 107 commands closed and all three owned containers were removed. The exact generated-output classification and opaque 64KiB retention correction passes 126 producer plus six independent pure methods and is selected only for fresh isolated CI. Both second-campaign full attempts are closed: 64M cache work exhausts at 64,000,001 after 41.737 seconds; 128M reaches the original instruction-fuel limit at 100,000,001 after 44.335 seconds. Neither finishes Corpus 1; Corpus 2 remains unrun. All final resources are zero, eleven commands closed and scratch was removed. No replay or default promotion is selected; the prepared Astra algorithm/resource-policy/implementation comparison remains under independent review, with zero runs and no installed workflow. The Swift host job passes 132 SDK tests including all nine axis cases and 69 update tests, then fails its 31 CLI tests with 32 issues from stale compiled source-pair4; later VM/generated-consumer steps were skipped. Reviewed source-pair5 refreshes only two SDK rows and passes eight in-process controls; full CLI/Python validation remains pending. This distribution ID does not authorize the held Android candidate v5. The user authorized public FieldLog publication: repository visibility is verified and one 26-test host run is dispatched at `4062256`, with results pending. The 12-file/38-test adoption draft is source-reviewed but unapplied and unexecuted. All native, custody, UnitA and GA holds remain; gates stay 8 running, 30 planned and 0 verified. Bindings and limits are in [the checkpoint receipt](verification/github-delivery-source-pair-and-rebar/checkpoint.json).

Checkpoint `fb7c7f2` verified the isolated preparation mount policy, exclusive Rebar transfer and complete bootstrap. Its next failure is binary export: Unicode standard output changed the pinned Hex bytes, confirmed by an exact transformed size/hash match. Preparation cleanup is verified; dependency compilation and both product network methods remain unrun. The byte-transparent export and bounded rejected-public-byte retention correction passes 111 canonical and 12 independent pure checks and is selected for fresh CI. The second cache campaign compiled its primary profile but stopped at a stale finite test expecting 30 seconds instead of the selected 60; three controls passed, one failed, and zero full attempts ran. All five command groups closed and scratch was removed. A literal test-expectation correction passes 19 pure checks, preserving runtime budgets, the original two-call oracle and the command-custody guard. A six-file public multiline text-field addition has source review and nine prepared tests; Apple admission is explicit and unsupported consumers reject vertical fields. Runtime, shared-theme and private FieldLog adoption remain pending. FieldLog’s private workflow remains blocked before its 26 host tests by GitHub account billing/spending, and its earlier local compiler cleanup is still unverified. Shared GitHub API quota delays manual dispatch and further inspection until the reported 19:37:21 UTC reset. All native/custody/UnitA holds and all GA boundaries remain unchanged.

Checkpoint `cc350d3` passes all six Engine jobs and ordinary Phoenix with 697 tests and two explicit skips. The cache runner passes 32 controls and 103 current fixture commands; this does not diagnose the earlier unknown cleanup error. The isolated image now passes tool/OpenSSL/CA prerequisites, then Rebar fails with EACCES; exact preparation cleanup is verified and product network methods remain unrun. A bounded executable tooling mount carved from the existing workspace allowance passes 103 canonical and 16 independent pure controls and is selected for fresh remote CI. All four full cache experiments ran: none completed Corpus 1, and Corpus 2 remained unrun. The 256-entry profile sharply reduced repeated decoding and reached the 30-second deadline with cache credits remaining; 128 entries stopped earlier on cache work. The first campaign is closed without feasibility or speedup acceptance. The next selected comparison keeps 256 entries and 100M instruction fuel, raises cumulative Runtime/WASI deadlines to 60 seconds, and permits one work-budget increase only after actual CacheWork exhaustion and verified cleanup. FieldLog’s shared task editor and nine new tests are pushed to its private separate repository. GitHub blocked its first workflow before runner assignment because of an account payment or spending restriction; none of the 26 host tests ran. The corrected cache experiment runner passes 17 pure controls and preserves unresolved command custody on exceptional exits. Its previous local dependency-fetch timeout remains unverified for cleanup and further local compiler work stays held. All native, custody and UnitA holds remain; no GA gate is verified.

Checkpoint `0b99469d` passed ordinary Phoenix: 697 tests and two expected isolated-network skips, exact source/readset bindings, scoped cleanup and no copied historical receipts. Checkout took 3.42 seconds in that run. Five Engine jobs passed; cache runner controls lost the primary cleanup error, so a reviewed diagnostic-retention change is selected without claiming the cause fixed. The isolated network transfer passed, then the old image failed its OpenSSL prerequisite; a reviewed immutable image amendment passes 84 pure controls plus 14 independent rejection cases and is selected for fresh CI. New policy commit `b6410e9` is preserved. Two Astra lanes prepared and independently checked four bounded cache-capacity/work comparisons on the unchanged full Swift workload; the dispatch-only campaign is selected for execution, with zero full attempts so far. FieldLog public document/event ownership is being integrated into its native task form; its first bounded host attempt timed out fetching the public dependency before tests, with cleanup unverified and further local compiler work held. Corrected storage-stage specification work is accepted but deferred behind executable integration. Capacity, admission, GA and all native, local-custody and UnitA holds remain unchanged.

Checkpoint `41af4a3` passed all six Engine jobs/64 steps. Phoenix passed 696 of 697 tests with two existing skips: all five HTTP/2 methods/seven cleanup-complete wire cases passed, while KOL09 exposed a dead-supervisor callback and premature replacement before old TLS cleanup. Eight of nine lifecycle methods passed (seven existing plus two new in-flight cases); the exact failure and successful terminal cleanup are retained. The reviewed and formatted two-file correction awaits fresh CI. Local custody remains held. The separate offline physical-region verifier passed all 16 synthetic methods with independent terminal review and owned cleanup; actual compiler geometry capture remains pending.

Checkpoint `c51f67c5` passed full remote CI: all six Engine jobs and 64 steps, plus all 13 Phoenix steps. Phoenix compiled 95 files without warnings and passed 690 tests with two existing skips; PostgreSQL and scratch cleanup passed. The deterministic cancellation suite passed all 17 cases in Debug and Release. The Bandit/JOSE patch and reviewed relation-lock bindings are accepted for host development; HTTP/2 wire, lifecycle, physical-verifier and GA qualification remain pending.

The latest local custody controls failed seven of 18 cases after permission refusal on owned-group observation. Those failures and seven unknown group states remain preserved; no retry or group probe is selected. The 31-file scratch copy is archived and its exact original tree removed. The independently reviewed ordinary-CI collector, production fixture exclusion and nine in-flight lifecycle tests are selected for the next remote checkpoint; their runtime results remain pending.

Checkpoint `d87ce0a1` is pushed with 867 selected paths. Engine CI passed five jobs and failed a timer-based cancellation assertion; its replacement uses a deterministic guest-growth checkpoint with strict cancellation and cleanup checks. Phoenix stopped before tests because its relation manifests still pinned the old lock. Both narrow corrections are source-reviewed, the Rust formatter check passed, and fresh full remote CI is selected. The prior accepted host evidence remains intact.

Checkpoint `a4f1d13f` is pushed with 197 selected paths. The test-only KeyOwnerTest supervision correction now has remote host acceptance: Phoenix passes all thirteen steps, 95-file zero-warning compilation, formatting and 690 tests, with two existing skips; all six previously failing teardown cases and K07g pass. PostgreSQL 16.15 and scratch cleanup complete, and the remote source hash matches the correction. Engine passes all six jobs and 64 steps on attempt one without skips. The closed Swift accounting join and dispatch/lifetime source contract are included. Unfinished local TLS harness and model implementation remain excluded; their separate failures and pending gates are preserved.

Bandit 1.14.0 and JOSE 1.11.13 are applied with an officially generated and independently reviewed lock; all nineteen other complete lock entries are unchanged. The isolated five-command resolution passed and cleaned up its groups and scratch. Full remote CI on these pins passed. Two actual HTTP/2 body batching/deadline checks and all operational/GA qualification remain pending.

Before the remote acceptance above, the isolated fixture harness stopped on two setup errors after source compilation; those failures and its unexecuted successor remain preserved. Remote CI subsequently validated the test-only supervision correction. The separate in-flight harness passed eighteen fault controls and two process-cleanup checks. Its expected-failure evidence exposed repeated permission errors without precise call sites and an incomplete normal-exit guard. Real lifecycle execution remains pending a narrow custody correction; the fake-control scratch was archived and removed. The Swift dispatch/lifetime model passed all 24 host tests with zero compiler warnings and independently reviewed cleanup. This accepts the isolated synthetic model, with a source-only physical/capacity evidence plan selected next. The earlier process-control failure remains recorded separately without a diagnosed cause. Actual capacity, numerical prices, root funding, product integration and all GA gates remain pending.

Checkpoint `fd92138a` is pushed with 1,559 selected paths: the supervised identity-owner cleanup fix, seven ordinary lifecycle tests, and independently checked diagnostic layout observations. Phoenix compilation and formatting pass, but six existing KeyOwnerTest teardown callbacks fail; 684 tests pass, including all seven new lifecycle cases, and two existing tests are skipped. PostgreSQL and scratch cleanup complete. An explicit fixture-ownership correction is in preparation. Engine CI passes all six jobs and 64 steps on attempt one, with no skipped steps. Active in-flight lifecycle and accounting work were excluded from this checkpoint.

Checkpoint `837e7084` is pushed with 644 selected paths: the dispatcher test isolation correction, accepted seven-method default-authority host qualification, and independently reviewed finite Swift accounting inventory. Engine passes all six jobs and 64 steps on attempt one; Phoenix passes all thirteen steps, with 683 ordinary tests passing and two existing tests skipped. The exact remote dispatcher test hash matches the corrected source; remote PostgreSQL and scratch cleanup complete. The sole canonical source change is the dispatcher test setup; active layout preparation and preaccess review were excluded. Supervised provider lifecycle, session/browser integration, numerical work/storage prices, root funding, native qualification and every GA gate remain pending.

The ordinary identity-owner correction now has independently reviewed host acceptance for seven socket-free lifecycle cases: normal supervisor shutdown clears its Admission pointer, and close requires the current table and its creator. The original defect reproduces; all seven corrected tests, zero-warning compilation and three formatting checks pass. Both VMs and scratch are cleaned up. The earlier formatting failure is preserved. Active TLS drain, worker-supervisor faults with active flights and application/provider integration remain pending. The Swift layout lane now accepts 28 named size/alignment observations and the actual closure at 48 bytes with alignment 8, limited to the exact isolated source, compiler, target and configuration. One compiler query was followed by separately reviewed retrospective parsing of its saved diagnostics; both producer and independent parsers agree on all values and 346 source spans. The original warning-policy rejection is preserved, and all three baseline warnings remain visible. No second compiler run, numerical work/storage price, aggregate peak, backing or root funding is accepted. The finite accounting join now has independent acceptance: all 645 roles are retained, with 97 named-layout links, two exact dispatch-closure links and 546 unbound roles. All twelve work and twelve storage obligations remain open; the next source contract concerns dispatch, returned-child and destruction lifetimes without selecting a numeric grant.

The console can now return to the first organizations or projects page after paging forward, including after a later-page failure. Root source review and 57 outer host tests pass, with four nested Solid binding cases and the project typecheck also passing. The eleven-file implementation preserves scoped selection, session freshness and cancellation; it is pushed in checkpoint `b231f3d` with 492 selected paths and four frozen contract/review packets. Console CI is cancelled at its five-minute limit during checkout; setup, tests and build were skipped. The checkout-only sparse repair is pushed as `114a2632` with 165 selected paths. Console CI passes all nine steps on attempt one, with a six-second checkout and unchanged runtime pins, tests and build commands. The preceding b231f3d Phoenix run passes all thirteen steps. Both b231f3d and 114a2632 Engine runs are now terminal with all six jobs and 64 steps passing on attempt one, with no skipped steps. The strict frontend session consumer has bounded source/host acceptance: all 149 outer producer tests, ten new and four existing nested Solid tests, typecheck and production build pass. Independent review qualifies 42 unique probes through 30 protocol/controller passes, eleven original Solid passes and one corrected targeted SO09 pass; its original harness failure remains preserved. Root verifies all 65 selected inputs and both frozen packets. Missing server endpoints still produce unavailable state; authenticated backend integration remains pending. A private same-process dispatcher is selected to reuse the fixed ordinary bearer/workspace pipeline and safely project its response; it has bounded source/component acceptance after nineteen producer tests and eight fresh independent adversarial tests pass, with 35 compiled modules and no warnings. Both earlier harness failures and confirmed cleanup remain preserved. Actual default verifier/default Repo now has bounded local host qualification after all seven methods pass with zero warnings and complete Admission/component/OS cleanup. It covers real signed-token verification, restricted PostgreSQL17.11 reads, tenant denials, canonical pagination, committed revocation and transaction-context refusal. Independent review verifies all 1,003 inputs and terminal evidence. The three earlier failed fixtures remain preserved. Production provider/supervised lifecycle, server-held session-token provenance and browser/HTTP integration remain pending. It adds no cookie route or session authority. Production session admission, connected builds/releases, browser/provider operation and G22 acceptance remain pending.

The Swift CI checkout optimization has bounded offline acceptance after independent source review: it retains all required source, 645 policy manifests, complete consumed evidence packets and full Git history. The selected checkout is 5,054 files / 208,685,831 bytes, versus 330,288 files / 17,638,540,012 bytes. Only the checkout configuration changes; commands, pins, limits and other jobs remain identical. The accepted session consumer and Swift checkout change are pushed together as `ee9f6dc7` with 450 selected paths; Console and Phoenix CI pass, and Engine passes all six jobs and 64 steps on attempt one with no skipped steps. The changed Swift checkout took eleven seconds. Active Rust and backend selection lanes were excluded.

The Android owner host CI checkout has bounded offline acceptance after fresh independent review. It retains all 199 required inputs in 304 canonical files / 2,108,263 bytes; every command, pin, limit and the default fetch depth remains unchanged. The producer materialization and independent canonical-blob/rule checks pass with owned cleanup. The accepted dispatcher and Android checkout are pushed as `d04fd5cc` with 2,016 selected paths, including the frozen narrow Swift retention review and next lifetime contract. The Android owner job passes all eight steps on attempt one with a three-second checkout; Engine passes all six jobs and 64 steps on attempt one without skips. Phoenix fails its formatter gate before compilation or behavior tests. A formatting-only correction changes the four reported files, passes the explicit six-file formatter check and preserves all six parsed ASTs. The correction is pushed in `6f116c6a`; remote formatting and compilation pass. Phoenix then fails all six dispatcher component methods in setup because a prior suite leaves a stale admission-table reference; a test-only correction now passes nineteen absent-pointer and six dead-pointer tests while preserving the pointer and rejecting live/malformed tables before dispatch. The original six setup failures are reproduced; corrected `837e7084` Phoenix CI passes with 683 tests and two existing skips. The original remote failure is retained. Active new Rust implementation/review and the next checkout proposal were excluded. The earlier base CI pass does not validate this new workflow.

The Swift capability CI checkout has bounded offline acceptance after independent review of all 370 canonical inputs / 22,995,155 bytes and 393 Git rule controls. The checkout-only change preserves complete declared resources, nine historical input blobs and full history; every build/test command and pin remains unchanged. The accepted checkout and dispatcher formatting correction are pushed as `6f116c6a` with 773 selected paths, including the frozen bounded IR02 repair/review. Engine CI passes all six jobs and 64 steps on attempt one without skips. The capability job passes all ten steps, including a ten-second checkout. Phoenix passes formatting and compilation but fails six dispatcher fixture setups. Active default-authority and work/storage lanes are excluded from this delivery.

The isolated actual Rust input-owner candidate is returned for correction after independent review reproduces IR01: the generic acquisition token releases its storage while a correlated validator proof and four loader guards remain alive. The exact failed Debug witness is retained; all 49 review members pass root custody checks. The current outer caller destroys its child first and the native bridge refuses completion, so no reachable native refund is established. A separate correction permanently retains acquisition charge after any correlation scope is issued, including every matched/refused/extracted/forgotten result; the correction is frozen after 25 passing host methods in each mode and six intended negative compiler probes within the selected nine compiler/two host commands. Root accepts only the live-ledger IR01 token/refund repair after 31 passing methods in each independent mode, including 51 binary vectors, 230 provenance mutations in both optional-resource shapes and twelve read schedules. A separate IR02 review found that the prior owned results could outlive the original ledger, despite safe current outer-caller ordering. The exact facade signature, host witness and initial harness failure are preserved. The minimum accessible-result lifetime repair is selected with an opaque original-root carrier, fixed consuming leaf operation and independent preaccess checks. The isolated two-file repair now has bounded accessible-result lifetime acceptance: producer checks pass 38 host methods in each mode and eighteen intended compiler refusals; independent checks pass 42 methods in each mode, with four fresh methods / 22 finite subcases and six semantic compiler refusals. Two positive companions compile, and the historical signature correctly inherits the original root through lifetime elision. The independent reviewer verifies all 4,237 complete MIR items and reviews 42 relevant complete bodies; root verifies all 589 producer/reviewer packet members. Generated compiler outputs are removed. Canonical integration, actual File/VM leaf execution and full ownership remain pending. The new work/storage obligation inventory has bounded offline acceptance after independent reconstruction of 65 arguments, 580 local/return places and 2,873 selected MIR rows, with nineteen fresh inventory/proposal controls. It preserves 24 positive unresolved work/storage obligations and counts relocated leaf work once. A conditional layout proposal covers 28 named shapes plus the actual closure; no compiler query, numerical price, backing bound or funding is accepted. Forgotten-result/root funding, shutdown and full ownership remain pending. Added ownership storage and capture costs remain unpriced. The corrected callee interface retains bounded partial acceptance after seven fresh methods, 1,473 adverse controls and 532 equalities; thirty work and storage contexts remain unpriced. Root funding, native acquisition and GA acceptance remain pending.

Checkpoint `d6af738` is pushed with 1,546 selected paths and eight frozen packets: bounded accepted current-provider string rebind and synthetic affine input-owner correction, the returned incomplete callee proposal, and the services CI checkout repair. Twelve independent checkout controls and all 153 selected input files pass, with every existing services command and the Go pin unchanged. [CI](https://github.com/snowdamiz/mixer/actions/runs/40551094236) passes all six jobs and 64 steps on attempt one, with no skipped steps. The changed services checkout took four seconds; its full vet and race tests pass. The separate callee correction/review and actual Rust ownership selection were excluded. No actual Rust acquisition, current whole-host string bound, external prices, root funding, native/runtime or GA acceptance is claimed.

Checkpoint `9398732` is pushed with 547 selected paths and six frozen packets. [CI](https://github.com/snowdamiz/mixer/actions/runs/40545367451) is terminal: five jobs pass, while services is cancelled during checkout at its fifteen-minute job limit; service setup and tests are skipped. The changed VM job passes all twelve steps after a seven-second checkout. Parent `a96712b` retains six passing jobs and 64 steps after its VM-only retry, with the original cancellation preserved. A local services sparse checkout now preserves all commands, materializes all 153 selected inputs, and passes the focused descriptor test and intended missing-contract negative control; the later d6af738 checkpoint records its independent acceptance and remote validation. Canonical product sources, actual root funding, runtime/native and GA acceptance remain unchanged.

Root accepts the affine input-owner correction only as a synthetic trusted-local Python host model after 35 fresh independent methods and 58,904 independently enumerated small-extent read schedules. The current-provider string rebind has bounded exact-source/MIR acceptance after twelve qualifying command groups and 1,139 targeted controls; five `COMPILED=None` identities still cause `UnsupportedBuild`, and the conditional 5,080-byte envelope is not a selected whole-host string bound. The callee proposal is returned for omitted casts, macro-selected runtime interfaces and Option auto-borrow/helper work; a separate correction preserves explicit positive unresolved work/storage obligations. The subsequently selected Rust implementation preserves actual loader lifetimes, which differ from the model buffers. No actual acquisition authority, source policy, root funding, successful fixture execution or operational grant is selected.

The input-owner correction is returned after fresh independent review: seven methods pass and four desired-property methods fail, preserving six failure records. Early refusal can permit retry and storage release with live selected Files; synthetic session equality also accepts float identity fields. A focused C1–C2 correction now runs alongside the complete string-source rebind and fourteen callee-interface derivation. Checkpoint `a96712b` CI attempt 1 has five passing jobs and VM cancelled after its 20-minute checkout fetch timeout; all eight VM tool/test steps were skipped. One VM-only retry is requested, preserving that cancelled attempt. Original-source string binding and conditional provider accounting retain their bounded acceptance. Actual acquisition, current-source string selection, root funding, runtime/native qualification and all GA gates remain pending.

Provider source work/storage now has bounded root acceptance after independent reconstruction of all 193 roles and 565 operations, 20 methods, 1,013 adverse controls and a fresh read-only root check. The accepted conditional addition is `276580 + 1324*B` work and 9,696 logical P0 bytes, giving fixed P0 301,733. Fourteen standard-library prices, two upstream work terms and all ten inherited residual terms remain required; a separate callee-interface lane is active. Child-owned input correction and exact string review continue. Actual ownership, full funding, runtime/native qualification and all GA gates remain pending.

The child-owned acquisition model is returned for correction after four independent desired-property failures: partial handles escape retirement, storage can release with live handles, admission survives owner retirement, and equal incomplete provenance can dispatch. Sixteen independent controls and 100,842 read schedules pass; the existing trusted-local bootstrap and minimum existing-open correlation direction remain viable. A separate R1–R3 correction is active, preserving the original failures. String binding and provider accounting remain under fresh independent review; no acquisition authority, funding or GA acceptance follows.

Immutable-binding checkpoint `a96712b` is pushed with 1,459 selected paths and seven frozen packets. It records bounded scoped-lifetime and existing-owner source acceptance, the returned string review, and three string/acquisition/accounting candidates awaiting fresh independent review. [CI](https://github.com/snowdamiz/mixer/actions/runs/40538740144) was running at push; attempt 1 later ended with five passing jobs and VM checkout timeout, followed by a VM-only retry request; parent `b20cd3b` passes all six jobs and 64 steps. The three active independent review lanes were excluded. Canonical product source remains at `b4a9fd4`; actual acquisition, root funding, runtime/native qualification and every GA gate remain pending.

Three frozen candidates now have complete root custody checks and fresh independent reviews in parallel: exact string binding (64 producer host methods), child-owned prepaid input contract (28 methods), and provider work/storage (29 methods). The provider candidate measures the actual closure at 16 bytes and proposes 9,696 additional logical P0 bytes, with fourteen standard-library cost inputs and upstream work still unresolved. These remain candidates; string-bound selection, acquisition authority, root funding, runtime/native qualification and every GA gate remain pending.

The scoped immutable-binding source has bounded root acceptance with a mandatory full-MIR amendment: 6,006 constructs, including all 1,785 standalone constants omitted by the producer parser, remain equivalent; 46 layouts and 38 independent controls pass. The old conditional source work/storage counts are explicitly rebound to the lifetime-only tree. The appended existing-owner container also has bounded source/protocol acceptance after 18 producer and 14 independent host methods, one metadata/MIR compile and 20 layout observations. It remains unqualified: provider accounting, child-side prepaid acquisition, authenticated ownership and root funding are not selected. Exact string-binding correction, provider work/storage and the minimum acquisition/correlation contract proceed in parallel; runtime/native and GA remain pending.

The first string-provenance correction is returned after a fresh 17-method review preserves ten failed expectations: full authored identity/trait fallback, foreign specialization receivers, two actual selected malformed headers, and missing authored argument/result compatibility. A new exact-binding correction is active under the complete S1–S5 contract; L_str remains unselected. The borrow-only input-provider proposal is frozen after 18 pure host model methods and is in independent source/compiler review. It creates an explicitly unqualified container; child-side acquisition, authenticated ownership and prepaid upstream work/storage remain unresolved.

Constructor and outer-caller checkpoint `b20cd3b` is pushed with 1,112 selected paths and eight frozen packets. Conditional native-open correspondence and outer source work/storage have bounded root acceptance. The push preserves the returned string review and its first correction candidate, plus the scoped-lifetime source candidate awaiting independent acceptance. [CI](https://github.com/snowdamiz/mixer/actions/runs/40531429558) passes all six jobs and 64 steps on attempt one; parent `a32d056` passes all six jobs and 64 steps. Three active review/provider lanes were excluded. Canonical product source remains at `b4a9fd4`; actual fixture inputs, root funding, runtime/native qualification and all GA gates remain pending.

Root accepts the conditional compiled native-open constructor interface after independent raw-byte review of 438 instructions and 46 relocations, 39 hostile controls, and a fresh read-only root replay. The outer source work/storage interface also has bounded acceptance after 1,450 reconstruction assertions, 673 controls and root rederivation; all 130 roles remain charged through final-result consumption. Its actual provider, identities/backing and root funding remain pending. Fresh string-correction review has found full-target resolver and nested function-header parser defects, so the 5,080-byte string bound remains unselected. A separate lifetime source candidate has passed one positive and five negative compiler-only checks and is awaiting independent review; a borrow-only input-provider proposal is being prepared. No product runtime or native check ran, and no GA gate is verified.

Independent review returns the frozen string-provenance candidate for correction: six callback bodies, 29 edges and two nested-scope string transfers were omitted, and six adverse checks fail. The recovered 5,080-byte constant envelope remains conditional; no string bound or whole-host grant is selected. A separate correction must preserve the original candidate/failures and pass the complete typed graph and external-contract regressions. Outer-parent work/storage and compiled native-open correspondence continue under the native-runtime pause.

Host-interface checkpoint `a32d056` is pushed with 441 selected paths and four frozen packets. Fourteen exact logical-interface clarifications are selected after independent review; twelve external work inputs remain. The preceding `975b2e3` CI passes all six jobs and 64 steps, including the exact 103-command Rust 1.98.1 cache qualification. [CI](https://github.com/snowdamiz/mixer/actions/runs/40523809565) passes all six jobs and 64 steps on attempt one. The outer-parent source now has bounded acceptance after 964 assertions and one successful compiler-only check with owned cleanup; this later acceptance is not included in that push. Its new work/storage, actual immutable binding and all three selectors remain pending. String review and compiled native-open correspondence continue. Canonical product source, native runtime and GA status are unchanged.

CI evidence-directory correction `975b2e3` is pushed with 75 selected paths. Its complete cache fixture now passes on Rust 1.98.1: root verifies all 103 command output pairs, 29 controls and 86 pack members against this exact commit, with cleanup confirmed. The retained artifact also contains older local evidence, which is explicitly excluded from remote qualification. [CI](https://github.com/snowdamiz/mixer/actions/runs/40514213881) passes all six jobs and 64 steps on attempt one, including the repaired Swift selection and cache fixture steps. The workflow preserves existing evidence parents and still requires fresh per-run output. Canonical product source remains at `b4a9fd4`; whole-host funding, actual fixture/writer execution, native runtime and GA remain pending.

Root selects the fourteen remaining source146 logical-interface clarifications after complete producer/reviewer custody checks, 3,374 independent assertions and 366 adverse controls. Five fresh constructor allocation requests add 55,381 once in P4; the amended conditional expression retains twelve required external inputs. The original 35-symbol model and its failures remain unchanged. The private outer caller is frozen for independent source/lifetime review; its producer compiler receipt failure remains unqualified. The string-provenance candidate is frozen for independent review; compiled native-open correspondence is active. New outer work/storage, immutable binding and operational authority remain pending.

Host CI repair checkpoint `37804cf` is pushed with 1,339 selected paths and seven frozen source/review packets. The Swift test now owns and waits both process-group members; all 64 host tests and two fresh root controls pass. The cache-state fixture preserves all 1,003 malformed-context inputs while building its baseline once; 29 runner controls and all 103 complete local commands pass in 126 seconds on Rust 1.99.0, under unchanged limits. [Fresh CI](https://github.com/snowdamiz/mixer/actions/runs/40513618996) hit a setup failure before cache controls: retained evidence makes the runs parent exist after checkout. The workflow now creates those parents idempotently; three fresh controls preserve historical receipts and continue refusing file collisions. The per-run output remains fresh-only. That run is now terminal with five jobs passing and the setup job failing. The corrected 975b2e3 run separately requalifies the complete cache fixture on Rust 1.98.1; all six corrected-run jobs and 64 steps now pass. The original two CI failures and root harness setup/reporting failures remain preserved. Storage, whole-work, selected compiled-resource and native-interface evidence have bounded acceptance with their explicit amendments. The remaining-work interface amendment is selected; string provenance, outer-parent review and compiled native-open correspondence continue. Canonical product source remains at `b4a9fd4`; actual root funding, fixture/writer execution, native runtime and GA remain pending.

Source146 resource and storage checkpoint `c4d04e5` is pushed with 433 selected paths and seven frozen packets. [CI](https://github.com/snowdamiz/mixer/actions/runs/40507305688) finished on attempt one with four jobs passing and two failing. The Swift selection test could not confirm disappearance of its orphaned test group; a test-only owned-group correction now passes all 64 local host tests and two fresh root controls, with production policy unchanged. The cache-state fixture reached its final malformed-context case before its 60-second deadline; exact inputs and confirmed cleanup are retained and its exact baseline-clone correction now passes all 103 complete local commands and 29 controls under unchanged limits. Fresh Rust 1.98.1 CI remains pending. Storage lifetimes and the conditional whole-work composition now have bounded independent acceptance. The latter retains 35 symbolic inputs; a separate exact nine-adapter clarification is selected for a future amended composer. Selected compiled-resource correspondence now has bounded acceptance with seven independent checker amendments mandatory. Native interfaces and their explicit positive operand-storage amendment have bounded acceptance after 9,579 independent assertions. Remaining work-boundary, complete string-provenance and private outer-parent source lanes are active. Canonical product source remains at `b4a9fd4`; whole-host funding, actual fixture/writer execution, native runtime and GA acceptance remain pending.

Source146 host-work checkpoint `9905f5a` is pushed with 829 selected paths and twenty frozen packets. It preserves the loader callback finding and correction, accepted parent/loader rebindings, and bounded entry, leaf-shell and payload-destruction interfaces. Independent checks total 1,266 for entry, 6,352 for leaf/layout applicability and 6,153 for payload/layout applicability. All 55 concrete size/alignment observations are closed within those scopes; actual resource costs and complete host funding remain pending. [CI](https://github.com/snowdamiz/mixer/actions/runs/40502001348) passes all six jobs and 64 steps on attempt one. The three active callee-cost, resource-cost and storage-lifetime lanes were excluded. Official exact-revision Rust source is retained as platform evidence without changing the installed toolchain. Canonical product source remains at `b4a9fd4`; genuine loader/writer execution, healthy cleanup, native runtime and GA acceptance remain pending.

The retained full source146 compiler output supplies 3,072 layout records. A new compiler-only query closes 21 additional named types for the callee and storage lanes with 42 intentional diagnostics; no product code ran and owned scratch was removed. The callee interface now has bounded acceptance after 17 independent methods and 616 negative cases, with its capture amendment mandatory. The resource source interface has bounded acceptance after 23,347 independent source and 4,221 retained-IR assertions; compiled standard-library correspondence remains partial. Review found an omitted eighth outer-core closure capture in the callee query roster. A separate successful compiler-only build directly observes all six original closures, including the 64-byte outer closure and one zero-sized closure; the independently corrected eight-capture binding supersedes the erroneous seven-capture query plan. The storage lane binds 152 original-validator functions and 6,458 typed roles to 171,197 logical inline bytes, and all 9,403 complete loader/validator roles now total 644,008 logical inline bytes after observing the original 8-byte Bytes::put closure. Three additive function pointers force the original monomorphizations without changing their bodies; full compiler output is retained and owned scratch removed. The 30-member storage/lifetime candidate now has bounded root acceptance after 20 independent methods and 128 arithmetic cases. The complete symbolic work composition has bounded acceptance after 33,493 independent assertions and 246 adverse cases. Selected compiled-resource and native-interface evidence now have bounded acceptance; complete generic File constructor and actual caller correspondence remain pending; the nine direct-adapter contract clarification does not rewrite the frozen work model or select a grant. Complete standard-library correspondence, whole-host funding and actual fixture execution remain pending.

Private host-account and combined-source checkpoint `510c2e1` is pushed with 591 selected paths. It includes the five accepted source/review packets, exact fixture-source selection and terminal parent CI evidence. The first delivery preflight refused a historical nested seal before staging; that attempt and the unchanged historical file are preserved explicitly. [CI](https://github.com/snowdamiz/mixer/actions/runs/40493544954) passes all six jobs and 64 steps on attempt one. Canonical product files remain at `b4a9fd4`. The isolated source146 composition retains all 396 roles and 311,071 logical bytes, with nineteen fresh optimized synthetic tests and ninety concrete layout queries. The separate P0 account-work component now has bounded source145 acceptance after 3,306 independent checks; its `2628088 + 194231*I + 1039*U` expression still requires selected counts and all remaining caller/child cuts. The corrected loader component has bounded source145 acceptance after 3,270 new independent checks; both affected slice edges now fund 128 callbacks and the original defect remains preserved. The source146 P0 account-work rebind has bounded acceptance after 5,274 independent checks; the corrected source146 loader-work component also has bounded acceptance after 3,846 independent checks. Its checked cap quote remains 895,083,809,874,789,059 logical units, with no host budget or runtime grant selected. A fresh loader metadata/MIR compile retains all 219 functions with only the paid descriptor-count literal changed; the parent candidate preserves its formula. The setup/argument cost interface now has bounded acceptance after 1,266 independent checks: 119,922 source actions and 53 conservative destructor visits, with actual path/native/destructor cuts still mandatory. Its exact-toolchain probe qualifies a 24-byte cancellation backing request with alignment eight and no new clone allocation; allocator footprint and destruction remain unproven. The leaf-shell interface now has bounded acceptance after 6,352 independent assertions, including all 53 native-size substitutions. The payload-destruction interface has bounded acceptance after 6,153 independent checks, closing all thirteen missing extent observations while keeping resource cuts mandatory. One shared compiler-only query supplies all 55 concrete size/alignment pairs; its 110 intentional diagnostics are layout evidence, not a successful product metadata build. The compiler was waited and 146 owned scratch files were removed. Three active lanes now resolve authored callee costs, exact-toolchain resource costs, and complete host storage lifetimes. The latter two can use nineteen frozen official Rust source files at the exact compiler revision; no installed toolchain was changed. These work packets are excluded from the push. Complete host funding, genuine loader/writer execution and healthy cleanup remain pending; native runtime remains paused and no GA gate is verified.

Reviewed admission and source-composition checkpoint `f678177` is pushed with 600 selected paths. It preserves the original accounting finding, accepted common-storage correction, accepted combined-source interaction tests, frozen bootstrap preparation and terminal parent CI evidence. [CI](https://github.com/snowdamiz/mixer/actions/runs/40487821632) passes all six jobs and 64 steps on attempt one. Canonical product files remain at `b4a9fd4`; genuine loader/writer execution, complete host funding and healthy cleanup remain pending. The private host-account and typed-entry source now has bounded acceptance after nineteen independent host tests in each mode, thirteen negative compiler controls, a fresh metadata compile and 2,004 inventory checks. Its 396 roles total 311,071 logical bytes; the complete parent and child prices remain pending. The exact 146-file host/source composition now has bounded acceptance after nineteen fresh optimized synthetic tests, ninety concrete layout queries and an exact typed metadata compile. All 396 roles retain their measured 311,071 bytes. Loader review found two slice comparisons priced as one callback instead of 128; a direct ledger correction is active. The separate parent-account work component is frozen and under independent review; complete parent and child funding remain pending. The future fixture source and original validator limits are selected from frozen evidence; fresh executable/build/session binding remains pending. These follow-ons are excluded from the commit. Native runtime checks remain paused and no GA gate is verified.

Snapshot funding and lifetime checkpoint `32b5075` is pushed with 1,067 selected paths. It includes ten frozen packets covering constants-only funding, conservative reservation retention, the closed-route work-cost interface, exact source145/host11 descriptor preparation and their independent reviews. [CI](https://github.com/snowdamiz/mixer/actions/runs/40482914167) passes all six jobs and 64 steps on attempt one. Canonical product files remain at `b4a9fd4`; these accepted host/source slices do not qualify the real writer. The private-core work-admission slice now has bounded acceptance after the common-storage correction passes four fresh independent host tests and 394 finite checks. All 1,436 new shared bytes are charged to common storage; snapshot totals stay unchanged. Three initial compiler timeouts are preserved. Combined source145 now has bounded acceptance after four fresh independent interaction tests pass in each host mode, confirming atomic work refusal and same-ticket retention of 1,899,541 bytes. Its unit metadata output is empty, so that command proves typechecking only. The fresh private host-bootstrap leaf is frozen. The enforcing host-account source is also frozen with eleven pure account tests per host mode and three negative compiler controls; separate contract and source-inventory reviews are active. Its corrected inventory has 396 roles and 311,071 logical bytes. The loader work bound has compiled its exact source model and is undergoing operation and credit-cut review; 315 independent preaccess model cases pass. These follow-ons remain excluded from the pushed checkpoint. Native runtime checks remain paused, and no GA gate is verified.

Corrected storage-accounting checkpoint `9a8e8f7` is pushed with 457 selected paths, including the original findings, corrected recipe, independent reviews and terminal parent CI evidence. Its [CI run](https://github.com/snowdamiz/mixer/actions/runs/40476296395) passes all six jobs and 64 steps on attempt one. Canonical product files are unchanged from `b4a9fd4`; the previous Linux/host qualification retains that exact source attribution. The subsequent isolated constants-only funding integration has bounded independent acceptance: actual selected floors are 1,386,019 bytes in production and 1,467,930 in the unit configuration including host-caller accounting. The closed-route work interface passes 1,058 independent controls. The conservative phase-retention amendment now has bounded acceptance after eight independent actual-control tests and four fresh compiler builds; the baseline early-refund regression is rejected. Exact source145/host11 descriptor preparation has bounded acceptance after 53 independent pure controls, seven identity-negative pairs and a fresh production metadata compile; actual loader ingress remains unrun. Selected early-work admission passes seven focused tests in each host mode and keeps a zero counter on pre-grant failures. Independent review found its 1,436 new shared-template bytes must be charged to common storage; a const-only attribution correction is active. The 1,272-action selected quote is unchanged, and ordinary adoption has three additional source actions. The accepted ten-packet follow-on is delivered in the leading checkpoint; original work-admission and active correction/bootstrap implementation files remain excluded. Host bootstrap and pre-ingress ownership still require qualification. No writer admission or GA gate is promoted.

The canonical private diagnostic slice now has bounded host acceptance. All 44 focused methods pass in debug and release; fresh independent review passes all 430 reactor-enabled library methods in both modes, 68,256 scalar boundary cases per mode, fixture ownership controls and external privacy probes. The five-file change adds the unverified typed-result codec and finite original row helper with self-contained Cargo fixtures. Checkpoint `b4a9fd4` is pushed with 489 selected paths, including those five canonical files. [CI](https://github.com/snowdamiz/mixer/actions/runs/40472556591) passes all six jobs and 64 steps on attempt one. The retained Linux VM log confirms all 44 focused methods in debug/release under both tested feature sets, with all 460 combined-feature and 430 reactor-only library methods passing per mode; reactor-only Clippy passes. This qualifies the canonical diagnostic slice only; isolated loader/adoption/writer integration remains pending. The snapshot storage correction now passes independent review: all 29 alias findings are resolved, including 1,096 additional common bytes; 143 targeted controls pass. The accepted logical recipe is C78,240 / S941,467 / A430,175 with 81,327 separate host-caller bytes. Constants-only source integration now has the bounded acceptance recorded above; returned-diagnostic lifetimes and full work admission still require integration review. The separable emission-helper delta passes 744 independent checks and four compiler builds, accepting only its additional 17,728 selected bytes and 28 evaluator actions. Complete funding, work admission and writer execution remain pending.

Ownership checkpoint `5b80a99` is pushed with 1,143 selected paths. Its [CI run](https://github.com/snowdamiz/mixer/actions/runs/40465088896) passes all six jobs and 64 steps on attempt one. Independent follow-on review accepts the bounded encoder-callee inventory of 40,531 logical source bytes across 2,658 roles and the corrected writer cost interface after 262 new controls. These follow-on acceptances are local and retain separate source attribution. The constructor bookkeeping delta now has bounded acceptance after forty independent checks; its nineteen added actions must be funded before construction planning. Complete owner/caller storage remains in progress. The unused emission-bound helper now has bounded acceptance after six fresh independent groups pass in each mode and two deliberate mutations fail as expected; its 29 evaluator actions must be funded before evaluation. Its largest permitted geometry exceeds the unchanged work ceiling and must refuse; the new helper remains undispatched. Full writer execution, production caller integration and all GA gates remain pending.

The snapshot constructor ownership correction has bounded source/compiler acceptance: both selected entries require a private, single-use borrow of the actual scope, with fourteen producer and fourteen independent compiler checks and eighteen differential checks passing. The corrected writer cost interface and encoder-callee storage inventory have also passed independent review; complete caller storage and work admission remain pending. A source-only canonical integration review verifies 132 existing and 144 candidate members and identifies platform, fixture and Cargo qualification obligations. The private typed-result codec and original diagnostic row helper are implemented in five canonical files with self-contained host fixtures. All 44 focused methods pass in debug and release, along with production Clippy, feature-isolation and privacy probes. One equivalent codec iteration repair resolves a new compiler lint, with its original failed attempt preserved. Independent review has passed the broader canonical library suite; the leading checkpoint records its bounded acceptance and current delivery status. `WorkAuditPending`, conservative cleanup, paused native checks and all GA boundaries remain in place.

Development resumed at the user's October 25 request to continue PLAN.md. The
[saved handoff](docs/implementation-pause-2026-10-25.md) remains historical evidence.
Browser SQL, nine-migration integration, transaction-local JIT and trusted
configuration text validation now pass scoped independent development review;
the first pushed Phoenix run executes 615 passing methods but fails discovery
warnings. The four-path classification repair passes eight isolated Mix checks;
its next CI run stops earlier in storage setup. That fixture repair now passes
24 PostgreSQL 16 methods. Pure runtime constructors pass 30 producer and 25
independent methods with root acceptance. Pushed `4b458d6b` passes all Phoenix
CI steps, including storage/migrations and the broader hosted suite (645 passed,
two existing skips).
Ordered-diagnostic design checkpoint `ab5442a5` now passes all three Engine jobs.
Preauth checkpoint `72340253` now passes every Phoenix CI step, including
664 ordinary methods with two existing skips. Its Engine workflow now passes all three jobs.
Begin-login checkpoint `273a1e48` passes every Phoenix CI step, including
664 ordinary methods with two existing skips. Its Engine workflow passes all three jobs.
Callback-contract and recorded Swift-prototype review checkpoint `6d98de42`
now passes all three Engine CI jobs.
Selected finite Swift completion checkpoint `68468f8f` now passes all three Engine jobs.
Callback candidate `5595f7b6` is on the isolated `codex/browser-callback-ci` validation
branch. Phoenix CI passes 95 selected PostgreSQL 16 methods and 664 ordinary methods
with two existing skips. Its archive omits two hidden source inputs; a narrow upload
repair `9f15b11f` now passes every Phoenix step. Root verifies all 65 selected source
inputs and 123 outputs across both retained artifacts; all three Engine jobs pass. The earlier candidate VM job
exceeded its 20-minute limit after a 13-minute-47-second checkout; three later checks
were skipped. Independent storage acceptance remains pending.
Corrected analyzer design checkpoint `13ce0c2e` passes all three Engine CI jobs.
Accepted fixture framing checkpoint `4af8b7e1` passes all three Engine CI jobs.
Fixture contract and framing CI checkpoint `2e4ca9a3` fails its new framing CI step
before Rust compilation: Homebrew shim resolution selected rustup-init. The
retained artifact is complete; the repaired checkpoint is recorded below.
VM and services pass; subsequent Swift checks were skipped.
Rustup dispatch repair `05c1ebf0` passes all three [Engine CI jobs](https://github.com/snowdamiz/mixer/actions/runs/40247799000).
Generated Android source-export repair `99d63843` passes all 40 steps across three [Engine CI jobs](https://github.com/snowdamiz/mixer/actions/runs/40252047362).
Default appearance packaging `55985881` passes all 40 steps across three [Engine CI jobs](https://github.com/snowdamiz/mixer/actions/runs/40256207023).
Copied SDK/source-pair compatibility `1f114d8f` is pushed; [Engine CI](https://github.com/snowdamiz/mixer/actions/runs/40263504027) passed all 3 jobs and 40 steps.
Android host lifecycle core `4e48ac1a` is pushed; [Engine CI](https://github.com/snowdamiz/mixer/actions/runs/40267720327) passed all 3 jobs and 40 steps. The new Java suite has local host evidence and is not wired into this existing workflow.
Android observer/source-profile repair `b45963c0` is pushed; [Engine CI](https://github.com/snowdamiz/mixer/actions/runs/40272428143) passed VM/services, but Swift was cancelled at the 30-minute job limit in the existing capability step. Logs remain unavailable; the runner-capacity notice does not establish the stall cause.
Standalone Swift fixture-envelope CI `0b8e3fd8` is pushed; [Engine CI](https://github.com/snowdamiz/mixer/actions/runs/40273904826) passes all 42 steps across three jobs after one bounded Swift-only rerun. Actual Rust 1.98.1 envelope qualification is verified against all 252 artifact members. The first Swift attempt timed out at checkout and remains preserved separately.
Reviewed owner/cache-state contracts `69b0c522` pass all 42 steps across three [Engine CI jobs](https://github.com/snowdamiz/mixer/actions/runs/40284896791). This checkpoint contains contracts and retained evidence; active product implementation remains outside it.
Independent cache-state review preparation `5c1cf075` is pushed; [Engine CI](https://github.com/snowdamiz/mixer/actions/runs/40290654299) passes services and VM, but Swift fails one runner-timeout control before analyzer execution. A bounded test-readiness repair passes all 63 CI selection controls locally; corrected `137d3e1d` passes all 42 steps across three [Engine CI jobs](https://github.com/snowdamiz/mixer/actions/runs/40292240567).
Native runtime and capture remain paused.
Review evidence checkpoint `99f8a0a7` is pushed; [Engine CI](https://github.com/snowdamiz/mixer/actions/runs/40303522601) passes all 42 steps across three jobs. This checkpoint preserves immutable candidates/reviews and root metadata, with no canonical product or CLI changes.
Host review evidence `d275c072` is pushed; [Engine CI](https://github.com/snowdamiz/mixer/actions/runs/40308561680) passes all 42 steps across three jobs. It preserves candidate4/CLI review and 192 semantic cases; canonical implementation edits remain outside this checkpoint.
Private Android owner/profile3 integration `fb4c8f07` is pushed. [Engine CI](https://github.com/snowdamiz/mixer/actions/runs/40330490396) passes all four jobs and 50 steps after one bounded Swift-only retry. The first Swift attempt exceeded its 30-minute job limit during Android host binding and skipped generated-consumer integration; that failure remains retained. Host/source development acceptance is scoped; native runtime and public V2 remain pending.
Guarded Android environment/profile4 integration `5583fb2c` is pushed. [Engine CI](https://github.com/snowdamiz/mixer/actions/runs/40347513075) passes Android JVM, VM and services; Swift exceeds its 30-minute job limit during the TSan binding phase, so generated-consumer integration is skipped. The independently reviewed two-job Swift partition preserves all 37 existing steps and passes 63 local CI regressions. Repair `a2401148` is pushed. Its [Engine run](https://github.com/snowdamiz/mixer/actions/runs/40354171285) passes all five jobs and 56 steps after one targeted capability retry for the initial zero-step runner-capacity cancellation. Root verifies core/JVM artifacts and all 39 binding cases with 51 retained command logs in each Debug/Release/TSan mode. The original capacity failure and an artifact-checker marker correction remain retained. Private host/source acceptance is scoped; native runtime and public V2 remain pending.
Evidence checkpoint `811a3172` is pushed with the selected scalar-cursor source proof, Android editor source audits and terminal `a2401148` CI artifacts. Its [Engine CI](https://github.com/snowdamiz/mixer/actions/runs/40361869680) passes all five jobs and 56 steps without retry. Root verifies retained core/JVM/capability artifacts against the exact commit; active isolated implementation packets were excluded.
Host component checkpoint `8ac62416` is pushed with the accepted isolated scalar-cursor implementation, corrected Android cleanup contract and terminal `811a3172` artifacts. Its [Engine CI](https://github.com/snowdamiz/mixer/actions/runs/40366004814) passes all five jobs and 56 steps without retry; source-bound core/JVM/capability artifacts are accepted. Active Android implementation and Swift CI runner candidates remain excluded.
Closed cache-state CI checkpoint `db6332d4` is pushed with the accepted corrected runner, exact closed pack and independent sparse-checkout job. Its [Engine CI](https://github.com/snowdamiz/mixer/actions/runs/40373807988) passes all six jobs and 64 steps without retry; exact-source host artifacts and actual Rust1.98.1 fixture qualification are accepted. The frozen Android candidate remains unaccepted; its separate replacement correction and broader independent audit are excluded.
All eighteen work packages remain in scope:
sixteen are in progress and two are marked ready. No launch gate is verified;
[gates/ga.json](gates/ga.json) records eight running and thirty planned gates.
These gate counts are not an estimate of implementation percentage.
[The product plan](mixer-product-plan.md) remains the completion contract.

The repository contains independently authored Swift SDK/native adapters, a Rust
interpreter, signed update/verification components, a CLI, local reference
services, Phoenix components, the branded website/console and a separate FieldLog
repository. Accepted component slices do not establish the complete native,
hosted, store, customer or operational product.

Profile adapter and editor review checkpoint `30f94a63` is pushed. Its [Engine CI](https://github.com/snowdamiz/mixer/actions/runs/40382744111) passes all six jobs and 64 steps without retry; exact-source fixture/core/JVM/capability artifacts are audited. The later Android correction and subsequent independent review evidence were excluded from this commit; no canonical implementation or GA acceptance is implied.

Isolated row-body acceptance and frozen Android correction checkpoint `4e7c21ee` is pushed. Its [Engine CI](https://github.com/snowdamiz/mixer/actions/runs/40387011950) passes all six jobs and 64 steps without retry; 343 fixture and 63 terminal audit members bind retained host evidence to the exact source. The isolated row adapter is not yet part of that canonical CI fixture. The subsequent complete Android audit verifies 1,151 members and requires two corrections: preservation through eligible rollback and exact renderer ownership at scope completion. All prior producer replay and SDK37/D8 checks pass. The new 44-member correction protocol has a 13-member independent review with nine abstract controls. Root selects its two completion/phase amendments and starts isolated full-source implementation with separate preaccess test preparation. Swift header review passes 48 offline methods in 35 verified members; root selects its five amendments and a finite host-only budget, with the subsequent 210-member exact outcome/layout proposal independently reviewed in 19 members and 16 offline checks. Root selects its exact literals and 140 distribution plus 11 host support paths. The implementation is now frozen in 3,830 verified members: final 96-command behavior/configuration and 22 compiler-expectation checks pass; the independent 254-member preaccess packet and completed 1,045-member actual review are verified. All 149 fresh commands and 44 compiler observations pass, with all 29 preaccess controls dispositioned. Root accepts the isolated construction/header/row component and complete source-object/lifetime accounting under the unchanged limits; canonical integration, real binding and full-target qualification remain pending. Independent review identifies a configuration-specific receipt correction: production foundation is 269,080 bytes with 71,200 submitted headroom, while unit foundation is 269,616 with 71,688. Root verifies the 18-member finding and records an explicit addendum without changing source or limits; healthy zero cleanup remains distinct from the retained unit-only fault quarantine. A separate five-member finding identifies atomic callback retry scope: root selects 451,173,376 only as an abstract callsite-action plus requested-I/O ceiling, explicitly excluding retry-driven callback reevaluation. Independent same-unit reconciliation accepts that abstract ceiling only. A bound on all actual source evaluations or CPU/retry work remains unqualified. The Android independent preaccess packet is frozen in 504 members, with 15 prospective cases and ten actual-source review requirements. Root verifies the 9,791-member corrected candidate. The 465-member focused tail review is scoped positive. Root verifies the completed 1,009-member independent review: producer host/SDK37/D8 replay and 42,884 independent/witness assertions pass, while the ten-member hostile membership witness PC-C16 remains a required failure. The bounded Renderer-only correction is frozen in 13,430 verified members, with unchanged PC-C16, full prior replay and SDK37/D8 passing. Its independent 305-member preaccess packet and completed 1,297-member actual review are verified. All 114 selected commands pass, including unchanged PC-C16 and the exact own-forward expectation amendment; root accepts the isolated host/source development slice. Root verifies the 43-member inventory reconciliation and selects three exact optional canonical-only legacy/probe inputs, all forbidden in generated products. The accepted source-pair5 rebinding is sealed in 57 members with the unchanged 22 SDK and selected 24 adapter entries. The isolated CLI/export component and partial host migration are now root accepted after independent reviews in 683 and 1,573 verified members. Fresh CLI review passes 222 commands; host A passes 222 cases/1,180 assertions and B passes all 90 commands, including unchanged PC-C16. The corrected eight-file passive return probe is root accepted after 68 fresh independent commands and 2,840 verified review members; its first candidate remains rejected. The full compiled-boundary matrix, complete-frame capture, source-backed semantic applicability and execution-closure correction remain active; all 189 historical V2 dispositions and five separate V1 positive call sites are required. Canonical source promotion and coherent integration acceptance remain pending.

Frozen initial-profile amendments and Android preservation contracts checkpoint `e1c108f6` is pushed. Its [Engine CI](https://github.com/snowdamiz/mixer/actions/runs/40391006298) passes all six jobs and 64 steps without retry. The dedicated fixture job passes all 103 commands and 29 controls on Rust1.98.1, with 324 exact-source fixture and 63 terminal artifact audit members verified. The subsequent constructor/layout reviews, selected implementation and Android preaccess controls remain outside this checkpoint; canonical product sources and GA status are unchanged.
Reviewed initial-profile construction and Android preaccess checkpoint `eb9339ae` is pushed. Its [Engine CI](https://github.com/snowdamiz/mixer/actions/runs/40394687336) passes all six jobs and 64 steps without retry. The dedicated fixture passes 103 commands and 29 controls on Rust1.98.1; 324 fixture and 63 terminal artifact audit members bind the retained host evidence to the exact source. The checkpoint contains frozen reviews, exact implementation selection and terminal parent CI artifacts; active product implementations remain excluded.
Preservation review checkpoint `62db9518` is pushed. Its [Engine CI](https://github.com/snowdamiz/mixer/actions/runs/40400072603) passes all six jobs and 64 steps without retry; root verifies 321 fixture and 96 terminal artifact audit members against the exact source. The commit preserves the complete Android candidate, independent review and required PC-C16 failure, the selected membership correction, frozen Swift preaccess/build-configuration evidence, and terminal parent CI artifacts. The three active implementation/review folders are excluded; no candidate acceptance or canonical product change is implied.

Accepted component checkpoint `c4c6f3d8` is pushed. [Engine CI](https://github.com/snowdamiz/mixer/actions/runs/40406899898) passes five jobs but fails one Swift timeout-control assertion before analyzer execution; later Swift steps are skipped. A delayed-start reproduction confirms the missing startup handshake. The test-only readiness repair passes all 63 local CI selection tests plus two negative controls; independent source review and a fresh single-test replay pass. Corrected delivery is recorded below. The commit contains isolated Android membership and Swift initial-profile construction/header/row acceptance, completed independent reviews, exact scope corrections, source-pair5 rebinding/selection and terminal parent CI artifacts. The three active Android integration folders are excluded. Canonical product sources and all GA statuses are unchanged.

CI timeout-readiness repair `a9ea84aa` is pushed. Its [Engine CI](https://github.com/snowdamiz/mixer/actions/runs/40410911137) passes all six jobs and 64 steps without retry. Root verifies 321 fixture and 66 terminal artifact audit members against the exact source. All 63 local selection tests, two negative controls and an independent single-test replay pass; the production runner and deadlines are unchanged. The original failed run and raw log are retained. The Swift snapshot-binding and retained-descriptor composition proposal is frozen in 41 verified members with 26 finite host methods and 307 synthetic snapshot mutations. The 29-member independent review reproduces two required lifecycle corrections: stale closed wrappers can accept reused numeric descriptors, and close errors can abort remaining ancestor cleanup or drop still-open descriptor accounting. The original 26-method replay passes, while three independent controls correctly remain failed. Root selects an isolated host-prototype correction. Its 476-member candidate has a completed 66-member independent review: the unchanged 26-method suites pass, and five fresh independent cases confirm scoped R01 and retained-wrapper R02 behavior. One required C01 witness exposes terminal-stream false healthy-zero accounting and replacement of the structured primary error. Root selects an isolated stream-ownership correction, now active. All 142 retained producer cases and raw R02 cleanup/protocol conflicts remain recorded, with healthy-zero outcomes separated from unresolved synthetic uncertainty. Actual binding and canonical integration remain pending.

Reviewed source-pair5 component checkpoint `6450104d` is pushed. Its [Engine CI](https://github.com/snowdamiz/mixer/actions/runs/40418529771) passes all six jobs and 64 steps without retry. Root verifies 321 fixture and 65 terminal artifact audit members against the exact source. The initial server commit_refs rejection is preserved; one nonforce retry succeeded after verifying the unchanged remote. The commit records frozen isolated CLI/partial-host acceptance, corrected passive-probe utility selection, unaccepted compilation-policy proposals and terminal parent CI artifacts. Active authored matrix and Swift independent-review files were excluded; canonical product sources and GA statuses are unchanged. The later Android state replay passes 203 commands and 1,545 scoped rows, but full content/state/policy joins remain pending. Independent review reproduces an interpreter-startup gap in the v4 execution closure; its v5 correction is active. Root accepts the two additive host-leaf return wrappers after four fresh independent commands and 74 assertions; full matrix acceptance remains pending. Root verifies and selects the separate five V1 positive witnesses in 366 members: five bounded commands pass, including the unchanged ten original assertions and 1,433 witness checks (1,422 event-bound checks). Exact source/bytecode tuples and actual enclosing results are retained; fresh final-matrix consumption and complete execution closure remain pending. A frozen 346-file source overlay combines accepted CLI/host/probe bytes; its 27 new and 23 changed paths pass a prospective patch check against the current commit. The 394-member independent composition review passes and root accepts that byte-composition scope; final matrix/launcher additions and combined behavior qualification remain pending, and the patch is not applied. The v5 pre-Python execution-closure candidate is frozen in 463 verified members with 15 producer bootstrap and nine admission controls. Independent review and its evidence-finalization follow-up were stopped by automatic safety review reporting possible cybersecurity risk; its experiment is not retried, complete review remains pending and latest child cleanup certainty is unverified. Ordinary state/semantic work continues in separate lanes. A separate 34-member renderer proposal retains 24 exact subjects and all original case IDs, with 53 finite/enclosing/callback obligations and zero runtime joins; final policy selection and fresh execution remain pending.

## Current work and evidence

Accepted encoder checkpoint `79b948a` is pushed with the isolated pure snapshot encoder, its independent review, the bounded admission correction and preserved failed evidence. Its [CI run](https://github.com/snowdamiz/mixer/actions/runs/40459403052) passes all six jobs and 64 steps on attempt one. The commit preserves 16 genuine byte comparisons and 134 privacy controls; full writer execution still awaits complete storage and work accounting. Active writer source and work-audit lanes are excluded. The separate encoder work correction now has bounded acceptance after all 347 original and 20 additional independent controls pass; caller/control and complete storage accounting remain pending. Canonical product code, paused native checks and GA status are unchanged.

Guarded snapshot contract checkpoint `38084d6` is pushed with the corrected finite wire model, its fresh independent review, original failed evidence and completed parent CI audits. Its [CI run](https://github.com/snowdamiz/mixer/actions/runs/40454013004) passes all six jobs and 64 steps without retry. Product sources are unchanged from the prior audited commit; previous artifact audits retain their original attribution, and no new artifact audit is claimed. All 106 new independent controls and the exact five original regression fixtures pass. The pure encoder now has component acceptance after root verifies its 1,256-member candidate and 968-member independent review. Sixteen fresh genuine byte comparisons and 134 privacy controls pass; omitted storage shapes are separately measured and complete admission remains pending. Independent review found two storage/work design gaps: failure cleanup before the owning scope returns and the phase-to-guard shared borrow. The separate 63-member correction now has bounded acceptance after its 70-member independent review passes; healthy selected cleanup and operational admission remain unqualified. Canonical product code, paused native checks and GA status are unchanged.

Reviewed adoption and descriptor checkpoint `43cbfb9` is pushed with the corrected isolated Swift adoption scope, Android descriptor utility, original failed evidence and independent reviews. Its [CI run](https://github.com/snowdamiz/mixer/actions/runs/40450561458) passes all six jobs and 64 steps without retry. Root verifies the 344-member fixture audit: all 103 commands and 29 controls pass on Rust 1.98.1 against 91 canonical source paths. Root also verifies the complete 88-member terminal core/JVM/capability artifact audit; all five bounded phases pass with owned children reaped. The preceding `606c428` run and its 347-member fixture and 120-member terminal artifact audits are complete. New exporter preparation and active independent reviews are excluded; canonical product code and GA status are unchanged.

CI control repair `606c428` is pushed. Its [CI run](https://github.com/snowdamiz/mixer/actions/runs/40447941540) passes all six jobs and 64 steps without retry. Root verifies all 347 fixture-audit members: 103 commands and 29 controls on Rust 1.98.1, with 89 unchanged historical source members, the one explicitly amended test and README closing all 91 paths. The original failed run remains recorded. Root verifies all 120 terminal audit members against the exact commit. The five data-audit phases pass with owned children reaped; one failed polling evaluator remains separately recorded. This is retained host evidence, with native and GA qualification still pending.

Observation consistency checkpoint `dee2d199` is pushed with the reviewed Android archive and completed parent CI evidence. Its [CI run](https://github.com/snowdamiz/mixer/actions/runs/40446305993) exposes a Python test timing failure: the 50 ms cleanup control expired during postflight before reaching its intended retention hook. The runner correctly failed and preserved scratch; the compiler fixture step was skipped. Three other jobs passed and two remained running at the retained snapshot. A test-only stage-readiness repair now passes all 29 local and 29 independent tests, plus slow-predecessor and broken-timer/handler controls. Root accepts that narrow repair for delivery; production runner limits and engine code remain unchanged. The failed run is retained and no fresh CI pass is claimed.

Host acceptance checkpoint `da558f82` is pushed with the scoped Swift loader review, finite Android field-preservation observations, independent evidence and terminal parent CI audits. Its [Engine CI](https://github.com/snowdamiz/mixer/actions/runs/40441050306) passes all six jobs and 64 steps without retry. Root verifies the 73-member terminal core/JVM/capability artifact audit against the exact commit. Root verifies the 321-member closed-fixture audit: 103 commands and 29 controls on Rust 1.98.1, bound to 91 exact canonical source paths. This existing host fixture does not qualify the isolated new adoption or full Android replay. At that delivery, selected Swift adoption and full Android replay were active and excluded. The reviewed finite Android consistency archive is now prepared for delivery; Swift adoption and descriptor-join candidates now have completed reviews and separate corrections in progress. Canonical product code and all GA gates are unchanged.

Receiver-join checkpoint `3e105c20` is pushed with the selected Android typed/raw receiver utility, original failure candidates, the frozen Swift loader candidate and terminal parent CI evidence. Its [Engine CI](https://github.com/snowdamiz/mixer/actions/runs/40437321290) passes all six jobs and 64 steps without retry. Root verifies the 74-member terminal core/JVM/capability artifact audit, completed in five fresh bounded phases. The original collector exceeded its 60-second parent limit and remains an unaccepted diagnostic; its descendant reaping is unverified. The exact-source cache fixture passes 103 commands and 29 controls on Rust 1.98.1; its 321-member audit is verified. At delivery the loader remained under independent review; active full Android replay, new field-preservation controls and all protected hosted work were excluded. Canonical product sources and every GA gate are unchanged.

Reviewed host checkpoint `1734ea49` is pushed with the isolated Swift codec, accepted finite Android controls and terminal parent CI evidence. Its [Engine CI](https://github.com/snowdamiz/mixer/actions/runs/40433480424) passes all six jobs and 64 steps without retry. Root verifies 321 closed-fixture and 65 terminal artifact audit members against the exact commit. Those existing host workflows do not qualify the isolated new loader or unfinished full Android replay. All three active lanes and protected dirty hosted files were excluded. Root reproduced four consistency gaps in the new 103-subject validator despite its original 42 passing tests. The separate correction now passes all 57 retained and new tests, including the exact four root cases, and root selects only its typed-consistency utility scope. All original subject/case/invocation records remain intact. The original raw-event checker exposed a missing mapping between local and global receiver IDs. Root now selects the separate v2 correction after eight fresh JVM commands, 13 actual states, a two-receiver same-class fixture, 46 retained hostile controls and ten additional root controls pass. Both IDs are captured from the same actual event receiver. A corrected full host replay is active; all 280 subjects and 189 historical dispositions retain their unresolved behavior and execution-closure obligations.

The latest host continuation accepts three finite Android ledger methods (87 calls), six renderer predicates (142 producer cases plus 37 independent calls), two ledger/constructor facets (41 calls) and NativeState/AttachmentJournal constructor facets (85 calls plus three independent cases). Four additional FieldPreservation/Replacement bodies now pass 123 calls and 645 checks, fresh independent replay and four independent cases with 107 checks. Root verifies all four complete subject records against the original 280-subject checklist. These are finite host facets; enclosing authority, allocation failures and native runtime remain pending. The expanded partial replay retains 1,830 rows and 222 command logs; its 1,260 historical callback rows still require helper-outcome review. The selected v4 return probe and 346-file prospective source overlay remain isolated. The corrected typed utility covers 103 editor subjects and the selected receiver bridge supports the exact delegated overload while preserving all original obligations and nine editor replacement tuples (the tenth global replacement is outside that scope). A new four-method observation packet now has finite host acceptance after root verifies its 171-member producer and 55-member independent review: 56 finite invocations and 731 assertions, 22 actual getter outcomes, and seven separately attributed direct Input support returns. Final Record.input/view remain unchanged; subject Input invocation counts and BCIs remain pending. The independent review reproduces all 56 rows and adds two recovery controls with three actual calls. Shared.events is a constant, so event restoration is not established; fixture close catches exceptions, so full post-disposal state remains unasserted. The broader replay retains one timed-out historical child as failed; all seven unchanged states pass separate recovery. Root accepts finite observation consistency after independent checks of 98 invocations/99 aliases, all 84 query rows and 50 receiver controls. The complete 3,339-member archive passes independent custody review, preserving all 844 missing completion rows as pending. All 280 original subject records and 2,705 required cases retain their remaining semantic obligations. The separate 19-member descriptor-join candidate is frozen: its 24 producer tests pass and its compact pass joins 663 of 665 recorded completions. The two unmatched returns are inner View delegates, which cannot establish the enclosing Switch/TextView return; all 844 missing completions remain pending. Independent review reproduces the compact results but finds three generic utility defects: unresolved hook receivers can still be labelled joined, valid JVM class names are refused, and instance receiver slots are not included in parameter limits. Root accepts the corrected descriptor utility after verifying its 52-member candidate and 27-member independent review. Fresh review passes all 119 prior controls, 72 independent grammar/context controls and three unknown-receiver cases. The migrated 24-test suite passes; the unchanged suite retains its one documented stale grammar assertion. The sole compact replay matches every delivered row and preserves the two known inner-delegate findings, all missing observations and complete original records. Review-harness failures remain separately recorded; this acceptance is finite host source/data scope.

Swift C01 cleanup and R03 read completion retain finite host acceptance: all 63 unchanged independent cases and 16 boundary controls pass with unchanged limits; 51 deliberate uncertainty cases remain nonhealthy. The private typed-result codec is now root-accepted against actual VM types in its isolated 142-source tree. Its 235-member producer packet passes 27 methods per mode, 54 result combinations, lifetime/privacy controls and both production builds. The 83-member independent review freshly passes those 27 methods plus seven independent methods per mode, with no blocking findings. The original 165 owner layouts remain unchanged; codec storage is separately measured and not operationally accepted. The safe retained-File loader and private validated carrier now has scoped host acceptance: root verifies its 1,050-member producer and 635-member independent review. The review passes 157 fresh commands, including the complete 105-command producer replay plus six independent helper methods and 16 genuine entry cases per mode. Each producer mode has 37 genuine cases, 12 behavior helpers plus a no-context emitter method in its 13-method filter, separate genuine fixture emission, and 23 production layout comparisons. Exact source/build/session preimages and validation-error storage peaks are verified. Final metadata rechecks retain a nonblocking role-labeling defect R1 for correction in the next slice. Two invalid-UTF8 filesystem cases per mode and actual non-UTF8 argv0 remain unrun because their host harness rejects before loader entry. Acceptance assumes a trusted launcher and quiescent local host; operational storage admission remains pending. The selected sealed-provenance adoption candidate is frozen in 2,941 members, with 266 required final-source commands passing. The completed independent review records 328 passing expectations and one failure across 329 host commands: the original control suite was omitted, and one observation-admission assertion lacks four named storage floors totaling 89,720 unit bytes. The separate test-only correction now passes all 37 original controls in both modes in both producer and independent runs. Root accepts the corrected isolated selected-adoption host scope, preserving the original failure and all prior source attribution. The review found no other production or accounting defect. The next guard-bound snapshot exporter contract has a frozen 767-member independent review of its 639-member candidate. Ten of twelve fresh groups pass; five genuine subcase failures expose missing duplicated-field joins. The review also requires the actual Source identity wording and existing generic preparation method to be corrected. Root accepts the separate 165-member contract/model correction after verifying its 170-member independent review. All twelve retained methods, six format groups, the five exact original regression fixtures, three migration negatives and 106 fresh independent controls pass; the producer's 53 additional controls retain separate attribution. The 70-member work/storage/cancellation proposal now has a frozen 35-member actual independent review: 30 finite Python controls and four tiny Rust lifetime compilations confirm two required design corrections. Root accepts the bounded 63-member correction after verifying its 70-member independent review: four fresh compiler contexts, eight layout constants, twenty boundary cases and four precise lifetime negatives pass. Its post-Construction failure path explicitly retains the enlarged charge and cleanup invariant; healthy cleanup remains unqualified. Its 8,536-byte common-core and 29,256-byte selected-shell measurements are partial proposed inventories, not accepted floors. Root accepts the isolated pure encoder after verifying 1,256 producer and 968 independent members. Sixteen fresh genuine guard byte comparisons, four missing-provenance refusals, 128 internal and six external privacy controls pass. The independent addendum measures 58 helper shapes, including 31 absent from the producer roster, plus four capture shapes; exact occurrence/move accounting and a complete floor remain pending. Three review failures are retained, including one supplementary compile timeout with unverified descendant cleanup and reconstructed source attribution. The next source composition is being prepared in a separate lane from the accepted component and released layout addendum, with independent source-work accounting in parallel; new admitted writer execution awaits exact source/work/storage review. Actual writing and operational admission remain pending. Its original 31 preparation expectations remain separately attributed; integrated writer execution and new storage admission remain unselected. The original 300,000 storage grant still refuses the measured 366,896-byte unit foundation; separate higher-grant refusal controls do not raise the original limits. Both ordinary and selected owners must use the original shared admission and cleanup path, with full inline provenance charged throughout its lifetime. Canonical runtime adoption, authenticated package provenance, exporter and context admission remain pending. Canonical integration, paused native checks and every GA gate remain unaccepted.

| Area | Verified scope | Next required work |
| --- | --- | --- |
| Swift runtime | Decode-plan reuse is integrated under unchanged limits. Four complete host contexts pass 2,314 named executions with nine inherited ignores each; the fresh live private suite passes 340 with zero ignores. | One corrected full attribution diagnostic reproduces the Corpus 1 cache-work failure at 23,358,291 instructions. Valid measurements show 61,142 repeated decodes and 53.907% of the work budget spent rebuilding previously decoded functions. Final consuming usage is zero and owned scratch is removed. The isolated segmented-LRU candidate regresses to 8,746,437 instructions under the same limit and is rejected for integration. Final consuming usage is zero, owned scratch is removed, and the failed result passes independent audit. Corpus 2 remains unrun. |
| iOS shared UI | Private pan input has simulator evidence. V7 Settings passes; first Tab fails actual focus traversal. All five run-cleanup checks pass and the owned simulator is deleted. | The corrected frozen V7 diagnostic join and fresh app/runner builds are accepted. The V8 runtime packet passes 16 producer and nine independent host methods. The fresh V8 simulator run passes Settings but fails first Tab, with zero skips and all five cleanup checks passed. The result audit and source lifecycle diagnosis are accepted; a passive lifecycle observer passes 116 producer and 371 independent Foundation checks. The first generic build failed Swift 6 actor isolation; the minimal correction now passes a fresh app/runner build and independent review. Corrected V9 runtime preparation passes 16 producer and nine independent host methods; root accepts preparation, with no new native execution. Shared UI/public routing remains incomplete. |
| Android shared UI | Private style/coordinator/input slices have scoped API37 emulator evidence. The integrated component fixture passes all 45 cases and 239 assertions; the separate pointer matrix passes 429 assertions. Generated export/default packaging and exact copied-SDK source-pair admission now have scoped independent acceptance. CLI31 per Debug/Release, Python28 and independent copied Swift/Java/entrypoint controls pass; root verifies 2,623 implementation/review/preaccess members and 105 current source inputs. The isolated lifecycle decision core has host acceptance: 22 producer and 33 independent methods pass; root verifies 119 sealed members and 46 current inputs. The concrete observer repair and explicit source-pair.2 now have scoped acceptance: 161 producer/287 independent host cases, 22 fresh consumer/signature families and identical independent Java/D8 outputs. Root verifies 2,877 sealed members and 34 independent commands; producer app-owned Swift/JNI cross-build is audited. | Common Swift preaccess and one rendered driver policy enforce the selected internal source pair; all 75 native build inputs match the accepted package. Public V2 lifecycle/environment routing, complete visual/interaction parity, resources/OS support, TalkBack, immutable distribution and final physical comparison remain pending. |
| Hosted builds | Durable storage/coordinator components and registry/audit slices have host evidence. The isolated entry composition passes 922 groups; the defensive context-admission correction passes 79. | The broader entry review remains incomplete. Live Engine/entry composition, real worker/clock/provider operations, authentication, quotas and deployed schedule qualification remain pending. |
| Console | SolidJS Builds, Releases and Workspace use the website logo, colors and fonts. All 112 console host tests/typecheck/build pass; cookie transport and protocol prerequisites have independent review. | Implement durable sessions/provider login and connect live build/release/onboarding/billing workflows; browser visual and customer gates remain pending. |
| Hosted release/billing | Protected artifact upload/read/audit now has actual Phoenix Endpoint and PostgreSQL evidence: eight methods and 47 HTTP requests pass, with 32 transport tests and 46 combined independent controls. The earlier storage composition passes 97 methods and seven-migration checks. | Connect live console/customer sessions, complete tenant trust/lifecycle writers, distributed admission, Go migration parity, durable inbox/Oban reconciliation and selected-provider qualification. Frozen authority/inspector and rejected transport lanes remain unaccepted. |

The new single full Swift reactor attempt passes validation and Initialize, then
fails Corpus 1 at CacheWork 64,000,001 / 64,000,000 after 23,358,291 guest
instructions; the preceding attempt reached 15,753,076 instructions. Corpus 2
remains unrun. Root verified all 311 result members and final consuming cleanup:
all current reservations, live counts and tickets are zero, with no cleanup
invariant. Owned scratch is removed and the exact compressed binary is retained.
No work, memory,
ticket or time limit was raised, and no retry is selected. The integrated
optimization passes ordinary host regression but does not yet complete the full
workload. A bounded diagnosis establishes 11,828,480 planning credits (18.48%)
and locates the final failure inside rebuild decoding. The test-only attribution
observer passes four finite host tests, covering 409 work prefixes and 173
cancellation prefixes. Three independent tests pass and root accepts the observer
for diagnostic preparation. Fresh preparation passes five finite Rust executions
and fourteen host controls. Independent review found six malformed supplementary schema cases; the strict correction
now passes 38 host methods. One corrected full diagnostic reproduces the original
failure and instruction count. All five telemetry snapshots are valid: 61,627
completed decodes include 61,142 repeats across 485 distinct functions. Repeated
IR construction consumes 34,500,496 credits (53.907% of the unchanged work budget).
This points investigation toward retention; it does not prove a replacement policy
will finish the workload. The original Result and legacy false cleanup flag remain
visible separately from final zero consuming usage. Owned processes and scratch
are removed. The result passes independent audit and root acceptance for retained host
measurements only. See
[the independent audit](docs/swift-current-attribution-runtime-review.md),
[the measured result](docs/swift-current-attribution-runtime.md),
[the schema correction](docs/swift-attribution-schema-correction.md),
[the preparation review](docs/swift-current-attribution-preparation-review.md),
[the diagnosis](docs/swift-plan-cache-remaining-work-diagnosis.md),
[the selected packet](docs/swift-exact-reactor-after-plan-reuse.md),
[audited result](docs/swift-exact-reactor-after-plan-reuse-result.md)
and [integration](docs/swift-decode-plan-integration.md).

The segmented-LRU retention candidate passes finite correctness/accounting review,
but its one original-harness full comparison regresses: CacheWork exhausts at
8,746,437 instructions, versus the current engine's 23,358,291, with all limits
unchanged. Root rejects it for integration. Validation and Initialize pass;
Corpus 1 fails and Corpus 2 is unrun. The original failure stays intact; final
consuming reservations, live counts and tickets are zero. Owned scratch and the
restored executable are removed (78,039,492 bytes); sealed preparation artifacts
are unchanged. The live VM is untouched and no rerun is selected. Independent
result audit confirms this rejection. See [the rejected candidate result](docs/swift-retention-runtime.md)
and [the audit](docs/swift-retention-runtime-review.md).

The second isolated retention candidate weights eviction by estimated rebuild
cost and age. It passes 49 finite cache methods but increases work in all six
fixed comparison traces; the phase-change case uses 31.717 times the baseline
work. Root rejects integration and does not select a full-target run. The pristine
baseline has 39 cache methods; three common comparison methods bring it to 42.
Both copies pass five generic unit and ten integration methods with matching
output. Independent audit verifies the raw results, source archives, preserved
intermediate failures and cleanup. Root verifies 94 retained bindings and the
unchanged 132-file live VM closure. Owned scratch removal reclaims 218,566,668
logical bytes. This is rejection evidence, not candidate correctness or full
workload acceptance. See [the review](docs/swift-cost-retention-candidate-review.md).

An adaptive recency/frequency proposal now has 17 passing model controls and
seven finite access sequences. It reduces model decodes on several traces but
increases phase-change misses and adds four credits to every resident hit.
Implementation selection is withheld; this is a model result, not a new VM
implementation or performance receipt. Root verifies all eight sealed members,
an exact model replay and the unchanged 132-file VM closure. See
[the proposal](docs/swift-adaptive-retention-design.md) and
[the root audit](verification/swift-adaptive-retention-root-review/acceptance.json).

The count-plan-aware cold-insertion experiment passes 24 finite producer methods
and 18 independent methods, including 292 oracle cases and 46,550 transitions.
Root verifies 30 producer and 23 reviewer sealed members, 64 input bindings and
the unchanged 132-file live VM closure. Phase-change regressions remain; the
eight-credit miss cost remains model arithmetic. The separate Rust feasibility
experiment measures 57 added credits per miss, zero per hit, and 20,472 added
operation reservation bytes. Three of six complete work traces regress and
memory admission fails earlier. Two original policy observations remain failed.
An independent 23-method offline audit confirms the recorded rejection. Root
verifies 133 sealed members, three 132-file archives and the unchanged live VM.
Live integration/full-target retry remain unselected. The bounded ordered
cache-transition design now passes 25 producer and 16 independent finite model
methods after seven corrections, including finalization and premature-cap checks.
Root verifies 73 sealed bindings and the unchanged 132-file VM closure. The
isolated Rust prototype reproduces 340 pristine and 356 candidate methods.
Independent review adds five writer and five hook controls, but demonstrates
three malformed CAP streams falsely labeled valid and a Python owner undercount.
Initialization/Drop/serialization inventory remains incomplete. Root verifies
305 sealed members and accepts recorded finite evidence only. The separate finite
completion now passes 362 candidate methods, 21 custody controls and six independent
controls. Root verifies 380 sealed members and accepts six selected fixture paths
with the independent 19-phase inventory: 16,186 of 16,384 logical bytes, leaving
198 bytes. The separate 51,712-byte named-role union is not a simultaneous peak.
Inherited serializer inventory and CODE-buffer count mismatch remain open. Complete
diagnostic/analyzer/target acceptance remains pending. The corrected analyzer design now
passes 25 producer and 23 independent methods, including 35,694 policy cases
and 165 closed transitions. Root verifies 279 sealed members and accepts the
design only. The bounded safe-File-borrow framing foundation now passes 20
producer and 24 independent host methods. Root verifies 894 sealed members
and 845 unchanged upstream members, accepting this standalone fixture scope.
Its reviewed logical inventory is 14,248 bytes within 41,984 reserved bytes;
all limits remain unchanged. Framing observation grants no semantic prefix
validity. The first macOS CI attempt stops before Rust compilation at
rustup shim dispatch. Its narrow repair passes the unchanged 44-method closure
and 16 focused controls locally. The repaired macOS CI now passes all 44
methods under Rust 1.98.1; root verifies its 78-member artifact and exact
source bindings. All three Engine CI jobs now pass.
The corrected acquisition/lifecycle contract now passes 24 producer
and 38 independent methods, including 5,390 oracle comparisons. Root verifies
773 sealed members and both preserved archives, accepting this contract only.
The separate fixture-envelope candidate is frozen after 64 host methods
and 16,170 finite-model comparisons pass. Root verifies 796 sealed members.
Independent review finds an undercounted prior-read loop and inconsistent
private poison-latch gating; the candidate needs revision. Seven accounting
probes and 33 corrected public fixtures pass; one of ten private fault controls
fails. The 64-method independent replay times out and is not a pass. Combined
steps, layouts, lifetimes and implementation acceptance remain pending.
The second correction proposal passes independent accounting review: all 116
operation rows, 108 transfer entries and error-finalization funding reconcile.
Root selects leaf425/W24/B471/G112/T42/finish47/F42 under unchanged global caps.
The public debit becomes 534*S_paid + 47*F_paid + 425*N_B; zero-call framing
retains debit581 with no invented observation. The corrected-source producer now passes
70 host methods, 21,714 fresh model/threshold comparisons and 32 layouts. Root
verifies 306 sealed members and the 86-member source archive. Independent
review passes 18 methods but fails the absent-state debit control; eight API
rejection probes pass. The final 116-row accounting bounds remain supported,
but combined acceptance is withheld. A separate source, guard-funding and
caller-validation proposal passes 352 independent offline checks. Root selects
the exact correction and explicit guard ownership under unchanged amounts;
the host producer now passes 70 unchanged plus 8 focused methods, 21,714
comparisons and 32 layouts. Root verifies 177 proposal/accounting/implementation
members and 27 qualification command results. Independent review passes 14
exact-source methods, two separate counter-overlay methods and API controls;
the original ten absence debits are all zero. Root verifies 407 combined members
and accepts this corrected fixture-only host implementation and its selected
step/memory bounds. The first portable CI runner is rejected for ambiguous
compiler identity and unrelated API diagnostic spans. The corrected runner passes
32 normal/optimized controls and a fresh full Rust 1.99 host closure. Independent
review passes 346 parser cases per mode, separate blocker refusals and 39 response
refusals; root accepts the corrected runner and wires the narrow CI step. The pushed
change now passes its complete envelope closure on actual Rust 1.98.1: 92 methods,
nine API controls, 32 layouts and 21,714 comparisons, with all 252 artifact members
audited. See [the compiler qualification](verification/github-delivery-swift-envelope-ci/ci-1.98.1-qualification.json), the
[bounded acceptance](verification/swift-ordered-retention-analyzer-envelope-root-review/absence-implementation-acceptance.json) and
[selected numeric contract](verification/swift-ordered-retention-analyzer-envelope-root-review/correction-numeric-contract-selection.json).
Existing framing behavior, ABI and report remain fixed. Semantic replay, real adapters,
CLI/custody and target execution remain pending. See
[the contract review](docs/swift-ordered-retention-analyzer-fsm-contract-review.md),
[the CI wiring](docs/swift-ordered-retention-analyzer-framing-ci.md) and
[the framing foundation review](docs/swift-ordered-retention-analyzer-library-review.md). See
[the analyzer design review](docs/swift-ordered-retention-analyzer-review.md),
[the completion review](docs/swift-ordered-retention-diagnostic-completion-review.md), [the prototype review](docs/swift-ordered-retention-diagnostic-rust-review.md),
[the diagnostic design review](docs/swift-ordered-retention-diagnostic-design-review.md),
[the rejected Rust result audit](docs/swift-count-plan-retention-candidate-review.md),
[the independent review](docs/swift-retention-next-design-review.md) and
[the root acceptance](verification/swift-retention-next-design-review/root-acceptance.json).

The fixture cache-state source contract and terminal correction are accepted
after independent review; root verified 651 combined members. Eight finite review
methods pass per mode; three private paid-domain exclusions still require actual
receipt-construction proof. These are not Rust product tests. Independent raw
File fixtures, the sorted-victim oracle and 35 proof obligations are now sealed
in 173 members. Root selected the bounded Rust implementation in a separate
source closure. The independent execution driver is sealed in 1,479 members;
nine tooling methods and 372 checks pass per mode, with zero candidate accesses
or executions in that preparation phase. Root now verifies the 454-member Rust
candidate and admits independent public-File execution and all 35 source proofs.
Producer validation passes 114 distinct methods per host mode and 25 API controls.
Each mode has 29 fresh public and two private injected File cases; four older
raw folders receive no final-run credit. Independent implementation acceptance,
private review seams and source/work, memory, caller and lifetime qualification
remain pending. Independent execution passes 39 public fixtures and 15 API
controls. Seven private finalizer witnesses per mode produce three passes and
four failures, confirming incorrect inactive-mask checks and a missing pending
feasibility guard. The guard-only correction is frozen in 814 members; root
verifies its custody and the 899-member initial independent review. Producer
checks pass 119 distinct methods and 25 API dispositions per mode. Independent
replay passes 39 public fixtures, 15 API controls and all seven private guard
witnesses in both modes; root verifies 1,241 sealed result members. Scalar-work and lifetime proofs
remain open. Original source and failures are preserved. These private states
have no established public from-empty reachability. See
[the independent review](docs/swift-semantic-adapter-terminal-review.md) and
[root contract acceptance](verification/swift-semantic-adapter-root-review/combined-contract-acceptance.json).

Independent source review refutes the existing G6 iteration ledger under its
selected per-site block model: subtotal657 before administration; restore-only
literals would leave645. The bounds are conditional, not measured runtime
overruns. Root selects fixed-endpoint scalar-commit and restore copies under
unchanged caps, with complete corrected work/lifetime proofs still required.
The selected correction is frozen in 570 members. Producer qualification passes
122 distinct methods and 25 API dispositions per compiler mode, with 23 fresh
layouts; complete work and lifetime proofs remain open. Three admitted public batches on the
guard correction add 192 passing cases: 64 words, 64 transitions and 64 sequences.
Root verifies 1,416 result members and removal of all six hashed products. No new
private execution or work/lifetime acceptance follows from these semantic passes.
Two G3 comparison-load proposals remain unselected because their apparent fit
depends on an unselected scalar-operation granularity. The third per-comparison
view and fourth whole-sort view proposals expose further source-model obstacles;
no G3/G4 implementation change is selected. A separate G6 audit identifies a
conditional 665-group core. Independent review rejects the named zero-array
variant's inherited memory-role assignment and supports an anonymous-array
alternative with a clear-block bound of 189 groups. Root selects that alternative
for isolated correction3 through the explicit
[clear amendment](docs/swift-cache-state-clear128-selection.md). Correction3 is
frozen in 570 verified members. Fresh host qualification passes 122 distinct
methods, 25 API dispositions and 23 layouts per mode, including 29 public and two
private four-File cases. All fourteen owned products were hashed and removed.
The complete G6 component-source ledger is accepted after an independent
slice-receiver correction: 512 production groups and 514 with private faults,
within 640. Complete work accounting and independent implementation
acceptance remain open; the original exact 511-group claim stays preserved.
Independent review rejects the byte-index sorting proposal: its assignments alone
require at least 1,080 G4 groups against the 768 cap. Independent finite models pass,
but the proposal also changes primitive accounting and duplicates caller ownership.
A cached-head alternative also fails its finite G3/G4 bounds. Fixed-array
expansion still needs at least 2,605 G3 groups against 2,568 and is rejected;
the first-pass specialization also fails its G2 necessary bound: 2,660
groups against 2,560. The distinct row-view probe now has a selected independently
corrected G2 upper of 2,494 against 2,560, with scoped Control 1,220 against 1,280.
Original lower totals remain unaccepted. The same full proposal fails its
source-admitted G5 necessary bound: 642 against 640; public-File reachability is
not proved by that witness. An isolated subtraction proposal supplies a conditional
invariant proof, but its unchanged merge independently needs at least 2,569 G3
groups against 2,568. The scalar-local cursor source proof is selected after root verifies 95 producer/review members. Independent conservative G3/G4/G5 bounds 2508/701/561 and combined G1..G7 total 7048 fit unchanged caps; the whole logical union remains 29,344. The isolated Rust1.99.0 host component now has independent/root acceptance, with 1,767 verified members. Final Debug/-O coverage includes 122 distinct inherited methods, three producer controls and seven independent controls; 25 API dispositions and finite File observations pass. Original obsolete private assertions and the whole-suite Debug timeout remain retained. The first closed fixture CI runner passes 103 producer commands, but independent review requires owned temporary directories for every child and terminal cleanup deadline handling. The first correction fixes terminal cleanup expiry but still permits parent traversal in temporary paths. The second frozen correction rejects both traversal paths and passes 29 focused controls. Independent qualification passes all 103 commands in 162.551 seconds and verifies 132 distinct methods per mode, all API/File/layout observations and owned cleanup. The dedicated Actions job now qualifies the exact runner on actual Rust1.98.1 macOS arm64: all 103 commands pass within unchanged deadlines, with 346 artifact-audit members verified. Root accepts this closed host fixture only; all six Engine jobs now pass, with exact-source host artifacts audited. The actual validated-owner profile-row adapter contract and exact writer protocol now have independent/root selection after 153 sealed members are verified. The isolated row-body implementation now has independent/root host acceptance after 1,651 producer/preaccess/review members are verified. Fresh review passes 86 behavior and six layout commands: each mode has 17 exact, five independent behavior and one targeted layout method, plus 16 selected and 18 independent synthetic-context bridge calls. The complete independent fixed-place bound is 13,904 bytes, with retained source/metadata/validation costs separate; the producer provisional totals are superseded. This accepts the copied Rust1.99 macOS crate component only. Exact diagnostic closure and real profile-header preparation is frozen in 200 verified members with 32 offline design controls. Independent review passes 48 offline methods in 35 verified members and requires five amendments. Root selects local structural checks, common-control optional WASI ownership, a closed fresh-construction guard, exact positive-byte accounting and guard-derived row ownership. The exact constructor outcome/local-layout protocol is now frozen in 210 verified members: eight owned outcome variants, 165 matching Debug/optimized data-only type layouts and 18 offline controls. Independent contract/layout review passes 16 offline checks in 19 verified members with no concrete blocker. Root selects the exact local literals and 140 distribution plus 11 host support paths; isolated helper implementation is active. Independent preaccess is frozen in 254 verified members with 29 candidate controls pending; eight original-source-only controls pass per build mode. Actual lifetime/combined accounting remains unaccepted; a full diagnostic invocation remains unselected. Unit-test compilation exposes the original WASI test-only layout difference, so the unchanged production profile correctly refuses. Root selects a separate complete test literal and a fixed non-test host dispatcher; actual measurements, accounting and source review for both configurations remain pending. Canonical integration, real binding, new compiler/CI and full runtime acceptance remain pending. The correction 3
lifetime inventory is accepted with independent corrections: 29,344 logical bytes within the unchanged
41,984-byte reservation. Independently corrected old-C3 bounds are accepted for
G1 94/256, G7 178/248, setup 188/512, finish 227/256 and guard 14/128. Changed
sources do not inherit them automatically. Complete source accounting and isolated host implementation are accepted; CI/compiler-target qualification and live integration remain pending. No canonical integration, full-target retry or layout amendment is selected.
Zero-debit guard replies retain their separate terminal-guard ownership. No cap
increase or combined acceptance follows.

Independent iOS source review found two host-diagnostic completeness defects:
substituted original AX/app data and reordered callback references could be
labelled complete. The native verdict stays failed. A host-only correction now
binds exact immutable original packets and ordered callbacks. Independent review
passes 57 controls plus 38 producer methods, closing those two findings for frozen
V7 replay. Fresh app and runner builds pass with all 55 products newly built and
owned scratch removed. V8 runtime preparation and independent host review now
pass. The one selected V8 simulator attempt passes Settings but fails first Tab;
all five cleanup checks pass, and the owned instance and scratch are removed.
Root verified the result audit and its exact immutable raw packets. The new
diagnostics show focus leaving, briefly returning to, and leaving the same plain
UIKit reference. Source diagnosis identifies missing key-window/application/scene
state during the public-input interval. A passive observer passes 116 producer
and 371 independent Foundation checks. The original generic build exposed a Swift 6
actor-isolation error. The minimal correction now passes all eight generic build
commands and independent review, with 55 fresh products and owned scratch removed.
Corrected V9 runtime preparation passes 16 producer and nine independent host
methods, with 263 independently verified input bindings and root acceptance.
No new native attempt is selected.
The focus failure's cause remains unproven and native acceptance remains pending.
The candidate adds two helpers to the forty-member baseline and changes only its
app entry source; original oracle, input actions and transport limits remain fixed. See
[the correction review](docs/apple-focus-system-join-correction-review.md) and
[latest native result](docs/apple-focus-system-native-result.md).

The hosted entry review stopped on an automated safety check after 45 baseline
passes and 20 of 21 additional controls, which exposed the context-selection bug.
It was not retried. The isolated defensive correction passes 79 functional groups;
root verified its 114 artifacts and minimal source/compiled change. That does not
complete the interrupted broader review or select live integration. See
[the correction](docs/hosted-worker-entry-context-admission.md).

The ordinary Phoenix bearer identity Plug passes 47 targeted host tests, including
real RS256 verification, with build scratch removed. Independent review passes ten
groups after repairing malformed Content-Type parameters, empty subtypes and
duplicate response metadata. It grants identity only; no customer route, membership authorization,
login provider or console data connection is implemented by this slice. See
[the transport contract](docs/hosted-bearer-identity-transport.md).

The first pure customer permission policy passed 26 initial tests, but independent
review found an incomplete decision could be accepted without its policy callback.
The correction now passes 30 product tests and 23 independent probes, with
warnings-as-errors compilation. Root accepts this finite prerequisite. It requires server membership evidence and the exact
verified token scope for human artifact/audit actions.
The unavailable repository default prevents this prerequisite from becoming a public
authorization path. At that checkpoint, durable lookup, transaction/RLS/revocation
ordering and console integration remained pending. See [the policy](docs/hosted-customer-authorization.md) and
[the correction](docs/hosted-customer-authorization-correction.md) and
[the accepted review](docs/hosted-customer-authorization-correction-review.md).

The subsequent PostgreSQL adapter supplies current stored identity, credential,
membership and resource evidence to that pure policy. Twenty-five product tests
and seventeen independent probes pass on PostgreSQL 17.11. They cover scoped
FORCE RLS, six ordered revocation locks, tenant ancestry, bounded membership
reads, rollback, timeouts and restricted runtime roles. Independent review found
that predefined privileged roles were accepted; the correction rejects every
reachable reserved `pg_` role, including indirect membership. The exact shared
CI fixture helper and all five migrations pass focused apply, idempotence,
latest-two rollback and reapply checks after repairing migration policy
dependencies. The original failed attempts remain recorded and owned clusters
and scratch are removed.

This remains a read-only evidence prerequisite. It does not supply transaction-bound
domain authority, a fresh trusted-clock check immediately before an effect,
durable audit/idempotency or customer HTTP/console integration. The older pure Repository facade still
defaults to unavailable. The complete standard Phoenix CI suite, configured
with PostgreSQL 16 and including existing build-worker checks, passes at
checkpoint `d385adf3`. See
[the current scope](docs/hosted-customer-authorization-postgres-ci-integration.md)
and [the independent review](docs/hosted-customer-authorization-postgres-review.md).
Root acceptance verifies 656 retained bindings and 25 current inputs; see
[the acceptance receipt](verification/hosted-customer-authorization-postgres-root-acceptance/acceptance.json).

The subsequent transaction-owned facade now keeps authorization and local SQL
inside the same checked transaction. It binds the exact identity, action, target,
owner, connection, transaction and local settings; checks fresh time before
effects and finalization; and retains complete revision snapshots. Review fixed
a post-validation time gap and independently reproduced caught effect errors
that could commit prior writes. Corrected code rolls those writes back even
when the outer callback catches the error.

Eighteen product methods and twenty-one independent PostgreSQL methods pass.
The exact new CI fixture also passes all eighteen methods, and all six ordinary
migrations pass apply, idempotence, latest-three rollback and reapply. Root
verifies 424 retained files and 201 historical source copies; every owned test
cluster and scratch directory is removed. Full standard CI for that transaction
checkpoint passes at `9662eda1`. See [the review](docs/hosted-customer-authorized-transaction-review.md),
[the CI scope](verification/hosted-customer-authorized-transaction-ci/README.md)
and [root acceptance](verification/hosted-customer-authorized-transaction-root-acceptance/acceptance.json).

Protected artifact storage and staged metadata resolution, immutable v2 upload
audit, principal-bound retries and the internal customer application facade are
now accepted as local components. The corrected codec passes 39 producer and 49
combined independent methods; staged reads pass 63 producer/regression and 80
combined independent methods. Storage passes 19 producer and 22 independent
methods. The application facade passes 15 producer and 12 independent methods,
including actual commit failures that suppress upload receipts, private bytes and
audit results. Counts overlap and must not be added as distinct coverage.

The current-source combined CI fixture passes all 97 selected methods, and all
seven ordinary migrations pass apply, idempotence, latest-four rollback and
reapply. Root verifies 428 retained bindings and 45 current source bindings;
owned PostgreSQL instances and scratch are removed. At artifact checkpoint
`6fff5ab9`, the 132-file VM closure and 40 console bindings were unchanged. Earlier findings and failed attempts are
preserved, including the codec callback guard, SQL type and artifact/event
binding repairs, reserved-role matching and migration policy-drop ordering.
That storage checkpoint did not enable HTTP routes, deployment or live console data. The facade
uses one server-configured host/trust snapshot; tenant trust/lifecycle writers
and provider operations remain pending. See
[the integration scope](docs/hosted-customer-artifact-integration.md) and
[root acceptance](verification/hosted-customer-artifact-root-acceptance/attempt-2/acceptance.json).

The subsequent ordinary customer HTTP slice is accepted locally. Digest-bound
uploads pass 18 facade methods and 25 combined independent methods. Transport
passes 32 producer and 46 combined independent methods after review repaired
encoded/extra-slash route aliases. The actual production Endpoint, default bearer
verifier with synthetic TLS/JWKS, and restricted PostgreSQL transactions pass
eight methods and 47 real HTTP requests, with zero skips. Tests prove exact-byte
reads, authenticated HEAD with no wire body, revocation, tenant isolation,
idempotent retries and rollback after local writes. All owned listeners,
workers, PostgreSQL clusters and scratch are removed. Root verifies 244 retained
bindings and 56 current product inputs; console branding and VM sources are
unchanged. Counts overlap. Live console sessions/data, tenant trust/lifecycle,
distributed admission, provider deployment and full Go parity remain pending.
See [the HTTP checkpoint](docs/hosted-customer-artifact-http-checkpoint.md) and
[root acceptance](verification/hosted-customer-artifact-http-root-acceptance/attempt-2/acceptance.json).

The private Android owner contract and roster amendment are accepted after
independent review; implementation is selected. Root verified 303 sealed members.
Both host closures are mandatory, including fourteen actual product subjects,
184 V2 callback barriers and five unchanged V1 positive baselines. Root verifies
1,170 candidate members and 300 current source inputs. Producer checks pass
197 orchestration cases, 1,316 concrete matrix rows and unsigned cross-compilation.
The candidate can mislabel completed input cancellation as still in progress;
independent execution also finds focus invalidation posting before gate closure.
The terminal cancellation witness keeps the core retired and gates closed but
continues ordinary readiness probes. Explicit mutation-argument propagation and
private fixture acquisition cleanup also need correction. Narrow repairs and
source/host review are active. A Handler post failure after enqueue also skips
removal and falsely records cancellation complete, with the core still retired.
Independent review rejects candidate2 and preserves seven classified findings.
Corrected candidate3 is frozen: root verifies 1,215 members and 306 current
inputs; producer checks pass 214 orchestration cases, 1,323 callback rows and
Java/SDK/D8 cross-compilation. Independent review reproduces an open concrete
renderer gate during lifecycle-dirty successful completion, with shared draw/input
permissions still closed. Root verifies the 128-member witness and selects a
fourth candidate repair. CLI validation was held while partial profile3 edits
referenced candidate3. Public V2 routing remains unselected.
Candidate4 is frozen in 1,246 members and 309 current inputs; producer checks pass
216 orchestration cases, 1,323 callback rows and unsigned Java/SDK/D8 compilation.
Ten independent repair controls pass55 assertions. Exact profile3 CLI host
qualification is sealed in 1,011 members: Debug/Release builds, 13 Swift methods
and 30 Python methods per mode, copied consumers and 72 preaccess refusals pass.
Independent review adds 63 host commands, three copied-consumer methods and
48 refusals across eight fixtures. Root verifies 658 review members and accepts
the bounded CLI scope. Complete owner source/callback/legacy qualification and
canonical delivery remain open.
Final classification corrects direct callback coverage to 1,316 rows: 1,295
primitive/constructor rows and 21 exact helper-boundary witnesses. Seven
measure-helper rows still need direct debugger timing; their nested rows retain
complementary scope without duplicate credit. F09 is independently confirmed:
later fatal engine disposal replaces an earlier ordinary renderer failure in
the outer owner's primary slot. The core retires and gates remain closed.
The complete rejected review is frozen in 3,589 verified members. Its historical
source map binds 35 groups and 153 check sites; full expansion of the 447 reported
historical vectors and broader cancellation and decoder/IME families remains
pending. Root selects the narrow candidate5 repair to collect retained component
failures before the thrown fatal error. Candidate5 is frozen in 1,772 verified
members: 222 orchestration cases, 14,477 renderer checks and Java/SDK/D8
compilation pass. The strengthened tests reproduce candidate4's failure.
Exact source-profile CLI qualification now has independent host acceptance:
683 review members are verified, including stale candidate4-profile refusal
without lock mutation. The complete owner review is now accepted for bounded
private development: 8,550 members are verified, all 1,323 direct matrix rows and
514 continuation cases pass. Two observer-target replacement vectors remain
source-only/native-pending. Canonical integration is pushed as `fb4c8f07`; public V2 remains
unselected. The new JVM CI job passes on Linux/JDK17.0.20.1:
222 owner cases, 14,477 renderer checks and 162 observer cases. Root verifies all
817 retained artifact members against the pushed source. Services and VM also
pass. Swift attempt1 exceeded its 30-minute job limit during Android host binding,
with final consumer integration skipped. One bounded Swift-only retry passes,
completing all four jobs and 50 steps.
Native runtime tests stay paused.
The API28 prerequisite contract passes independent review. Bounded environment
observation/API-class isolation is selected for implementation with source profile4,
preserving both API36 guards and adding no rendering contexts. The exact native
implementation has private host/source acceptance after 76 independent JVM cases
and 661 assertions, official Java/D8 compilation and verification of 1,455
producer/review members. Profile4 also has independent host/source acceptance:
118 fresh commands, including 107 refusal commands, with actual creation/export
and exact copied descriptor checks. Canonical delivery is pushed as `5583fb2c`; three CI jobs pass and Swift times out.
Native runtime stays pending.
The profile4 JVM CI job passes on Linux/JDK17.0.20.1. Root verifies all 898 retained artifact members against `5583fb2c`, including 131 platform cases/671 assertions and the existing observer, owner and renderer regressions. Swift times out during binding; generated-consumer integration is skipped. A reviewed two-job partition retains every check and passes 63 local CI regressions.
The exact collection prerequisite now has source/compiler acceptance: root verifies 130 producer/review members, 851 independent checks and 170 emitted Java member references with an API floor no later than 28. No source rewrite is selected. Empty-factory mutation exceptions and Android runtime remain separate limits. Root verifies 203 frozen editor proposal/audit members. The cleanup contract and mandatory independent lifecycle/failure corrections now have root design acceptance after 91 sealed members are verified. The complete isolated source is frozen in 6,149 verified members. Its 38 host groups / 505 assertions and SDK37 javac/D8 pass, while two valid ACTION_SET_TEXT cases still fail and terminally retire the field. Independent review reproduces those failures plus five metadata/tuple control failures; root verifies 1,046 review members and requires changes. The corrected source is now frozen with 4,986 verified members: 52 host groups / 722 assertions and pinned SDK37 javac/D8 pass. Independent review reproduces that evidence and passes its prepared and hostile controls, but finds two additional real compatibility failures after a field previously held and lost focus: accessibility replacement refuses, and another field's ordinary edit becomes terminal. Root verifies the 20-member finding packet and selects a separate focus-history correction. The focus-history correction is now frozen in 5,325 verified members: prior 52 groups/722 assertions, both corrected ordinary cases, 13 new focus groups/598 assertions, 38 descriptors and SDK37 javac/D8 pass. Root verifies the separate 71-member preaccess packet and the completed 1,151-member independent audit. The audit reproduces all producer host/SDK evidence and passes 14 additional groups, while two required controls fail: a known engine rejection cannot restore a previously blurred field after attach returns, and an internal foreign-renderer end call corrupts scope/count ownership. The 22-member finding packet is preserved, and a separate 44-member completion/ownership protocol now has a 13-member independent review. Root selects PC-P01/PC-P02 and starts isolated corrective implementation. Independent preaccess is frozen in 504 verified members: 15 prospective cases, ten actual-source requirements, old-source-only typechecking and a 14-assertion three-field fixture. Both unchanged prior failure witnesses reproduce on old source. The corrected candidate is now frozen in 9,791 verified members; final host and SDK37/D8 runs pass original 52 groups/722 assertions, all prior controls, both unchanged findings witnesses and 12 new groups/1,660 assertions. The focused source/bytecode review finds no blocker under its immutable-product-path premise, but independent hostile PC-C16 duplicates one journal member and exposes a double release with an omitted held field. Root verifies the complete 1,009-member independent review, including passing producer host/SDK37/D8 replay and 42,884 independent/witness assertions, with PC-C16 separately retained as a required failed control. Root classifies this as a required selected-invariant correction without claiming ordinary reachability or an exploit. The bounded Renderer-only correction is now frozen in 13,430 verified members: unchanged PC-C16 passes 335 assertions, all prior replay and SDK37/D8 pass, and six new groups pass 45,255 snapshot-inclusive assertions across 46 hostile boundary cases. Root verifies the separate 305-member independent preaccess packet and releases the exact candidate for actual-source review. The review preserves a nine-member old own-forward expectation conflict; root selects only that row for the already-required once-only malformed-own failure policy, with every foreign identity row and isolated replacement coverage still required. Candidate acceptance and integration remain pending. Source-pair5 and host-test integration preparation is frozen in 657 verified members; its 15-member independent review supports the callback design and selects the explicit canonical-input/excluded-probe clarification. Integration still requires accepted corrected source and fresh binding/qualification. The correction remains unaccepted; canonical integration and native behavior remain pending, with existing SDK36 admission guards preserved.
See [the roster review](docs/android-private-owner-effect-roster-review.md) and
[root selection](verification/android-private-owner-effect-integration-root-review/implementation-selection.json).
The [selected clarification](verification/android-private-owner-effect-integration-root-review/dirty-result-clarification/selection.json) distinguishes recoverable lifecycle invalidation from stale concrete validation and permits only immediate scalar return of a completed input result after a live successor. The exact third mechanical leaf snapshot is accepted for bounded reuse after twelve independent controls and 82 assertions; it provides no product-test or Android-runtime acceptance.

## Customer workspace discovery and console composition

The authenticated workspace API and actual client are accepted locally through
production Endpoint/default verifier/default Repo. The console now routes
`/workspace` inside the website-branded shell and owns selection across routes.
Session changes synchronously hide stale rows and fence actions; pagination,
organization changes and disposal cancel obsolete work. All 100 console host
tests and the production build pass; 14 independent composition probes pass.
The four nested binding methods use the actual Solid reactive runtime and HTTP
client. Counts overlap. Review repaired an effect-order stale-state window and a
trailing-slash header mismatch. No browser/capture/native instance was started.

The cookie workspace adapter now uses fixed same-origin routes and shares the
bounded transport with the existing bearer client. All 112 console host tests,
type checking and production build pass. Browser-auth configuration, PKCE,
cookie, CSRF and callback primitives pass 39 selected host methods; independent
review passes 15 transport plus 15 protocol methods with no findings. Counts
remain separate. Selected protocol CI is wired. The mobile navigation adjustment
places the three route links below the website logo; visual verification is paused.

These are local components. The production entry still has no authenticated
session adapter and renders unavailable. The typed encrypted vault, configuration digest and closed stored-record decoder
now pass scoped host tests and independent review. Their producer suites pass
25, 20 (including 14 existing Config methods), and 11 methods respectively;
independent review passes 16 vault/digest plus 11 decoder groups. The SQL
lifecycle now passes 23 selected methods on PostgreSQL 16.15 and 17.11 after
review repaired NULL-scope admission and expiry after unique-key waits. Six
separate correction-review methods pass. The inert migration and all nine
ordinary migrations pass apply/rollback/reapply with independent review.
Browser Config text admission passes 26 producer and 32 combined independent
methods without changing valid digest bytes. Transaction-local JIT passes 86
selected PostgreSQL 16 methods and six independent controls with unchanged
deadlines and verified connection-setting restoration. Counts overlap. See
[the integrated component scope](docs/hosted-browser-session-integration.md).
Provider exchange/ID-token validation, runtime owner, routes, ingress and actual
login remain unimplemented or unqualified. The original storage contract defines 18 required cases;
its case count is not interchangeable with the new candidate test count. No launch gate is promoted. See
[cookie transport](docs/console-cookie-workspace-transport.md),
[protocol](docs/hosted-browser-auth-protocol.md),
[independent review](docs/browser-auth-prerequisite-review.md),
[session storage contract](docs/hosted-browser-session-storage-contract.md) and
[composition acceptance](verification/console-workspace-composition/root-acceptance/receipt.json).

The [browser runtime contract](docs/hosted-browser-lifecycle-runtime-contract.md)
passes eight producer and twelve independent structural checks after correcting
startup binding, existing PUBLIC-policy expectations, same-process trust-change
limits and first-slice preauth behavior. This accepts the implementation contract
only. Pure custody/runtime configuration now passes 30 producer and 25 independent
methods, zero failures/skips/exclusions. Root audited 51 source/dependency and
33 output bindings and cleanup. Exact constructor checks preserve supplied TLS,
separate all four roles, derive the fixed two-connection pool and disclose no
secrets. This proves neither live startup provenance nor secure external custody.
The existing URI HTTPS registry read is narrowly documented; drift fails closed.
Function/type catalog checks now pass 26 producer methods on PostgreSQL 17.11
and 20 independent methods on PostgreSQL 16.15. Root audited 14 source, 803
dependency and 49 output bindings and cleanup; selected warnings-as-errors
compilation passes. Three new PG17 probes exposed extra standalone browser
types and unchecked ACL grantors; the accepted V1/V2 candidate repairs both.
It passes 30 PG17 and 19 independent PG16 methods plus 10/12 compile-rejection
controls. Original catalog 26/20 and preparation SQL 39/38 methods pass separately.
Root verifies 464 reviewer-sealed members and six final source/output/dependency
packets. The inert additive migration now passes independent development review:
ten-migration integration passes separately on PG17 and PG16, alongside six
PG17 operator methods and eleven independent PG16 adversity methods. Root
verified 866 sealed members, 81 source, 1,137 dependency and 166 output bindings
and cleanup. Corrected broad ordinary CI now passes as recorded below. See
[the migration review](docs/hosted-browser-activation-preparation-migration-review.md)
and [the versioned review](docs/hosted-browser-catalog-v2-review.md).
Migration delivery `a6eaa8a5` passes selected storage/migration CI. Its broader
run reports 649 passed, fifteen invalid and two existing skips: build-storage
setup still expected nine migrations. The missing expected 00008 is corrected
and actual projectless formatting passes. Corrected `eec94804` now passes every
Phoenix CI step: 664 ordinary methods pass with two existing skips. Engine also
passes all three jobs. The preceding `d1ca1656` Phoenix run was
cancelled, not passed. Both preceding `a6eaa8a5` and `d1ca1656` Engine runs now
pass all three jobs.
The RelationCatalog prerequisite passes 233 PG16 and 234 PG17 methods with
65/66 actual mutations. Independent review passes 96 methods on each major,
including fourteen rejected mutations and two allowed naming equivalences. Root
verifies 746 review artifacts, 74 source, 758 dependency and 73 output bindings,
plus the producer preflight and cleanup. This accepts only the relation
prerequisite; all 48 complete runtime cases remain incomplete. The subsequent
fixed preauth Store/bootstrap/load composition passes 30 producer PG17 and 20
independent PG16 methods. Review repaired three caller-ownership failures and
added valid projected pending-attempt rejection. Root verifies 118 producer seal
entries, 358 review artifacts, final source/dependency/output bindings and cleanup.
Manual fixed storage composition is accepted; complete 44/40/18 matrices,
shared startup, active identity/provider and HTTP/console remain pending. The
fixed begin-login component now passes 30 PG17 controls, 30 unchanged preauth
regressions and 34 independent PG16 controls. Root verifies 103 producer and
284 review seal entries, exact source/output bindings and all owned cleanup.
Private preauth URL publication, pending replacement, audit-counter race rollback
and final caller deadline/continuity checks are accepted within this scope.
The callback contract passes independent source review and fourteen executable
contract-model methods; root verifies 154 sealed members. All 39 runtime cases
still lack complete matrix acceptance. The typed callback storage candidate passes
35 callback, 30 preauth and 30 begin producer methods on PostgreSQL 17. The PostgreSQL 16 review stopped before database creation after two archive
preparation failures and an automated safety interruption; its runtime checks
remain pending and owned scratch is removed. Separate portable Linux CI passes all 95 selected methods on PostgreSQL 16
and 664 ordinary methods with two existing skips. The uploaded selected packet
omits two hidden source inputs. Corrected `9f15b11f` passes every Phoenix step,
and root verifies all 65 sources and 123 outputs across its two retained artifacts.
This CI result does not complete the interrupted independent review. Complete supervised
ClaimOwner ownership, shared permit transfer and a retained wall handoff must
precede publishing a claim handle. Active identity/provider, startup
and HTTP composition remain pending. See [callback contract review](docs/hosted-browser-callback-claim-review.md)
and [begin-login review](docs/hosted-browser-begin-login-review.md).
See [the preauth review](docs/hosted-browser-preauth-store-review.md).
See [the relation review](docs/hosted-browser-relation-catalog-review.md).
This is only `:function_surface_verified`: tests explicitly
show that missing relation/policy/grant admission remains a separate requirement.
The preauth component now composes both partial checks on its own transaction;
no Application or authenticated-readiness wiring exists. The pure activation
preparation decoder passes 19 producer methods, 11 existing snapshot regressions
and 29 independent methods. Root audited 13 source and 38 output bindings and
actual Mix formatting. Its exact six-field result proves shape; the future owner
must compare the retained claim, current identity and current configuration.
The corrected relation contract passes 12 producer and 16 independent source
checks, with both incoming principal foreign keys included. Root verified 62
input, four read-only context and 99 output bindings. All 48 relation runtime
cases and forty owner runtime cases remain pending. PG16/17 representation
fixtures each pass 82 semantic checks and 23/24 actual mutation controls.
Independent review passes 427 main, 96 effect and 14 freeze/source assertions
with overlapping coverage. The subsequently implemented RelationCatalog has
now passed the separate bounded review described above. The additive preparation SQL helper passes 39 PG17
and 38 independent PG16 methods. Review found unexpected PUBLIC grants could
survive provisioning; initial and final exact new-object ACL checks now reject
them, including third-party/default grants and grant options. Root accepts this
component after auditing 22 source, 803 dependency and 62 output bindings. No
production migration, lifecycle caller or readiness is enabled. Explicit V2
function admission and the inert migration are separately reviewed prerequisites. See [catalog review](docs/hosted-browser-catalog-surface-review.md),
[contract review](docs/hosted-browser-lifecycle-runtime-contract-review.md) and
[constructor acceptance](verification/hosted-browser-runtime-constructor-review/root-acceptance.json).

The [decoder review](docs/hosted-browser-activation-preparation-decoder-review.md)
and [relation contract review](docs/hosted-browser-relation-admission-contract-review.md)
record the accepted component scope and remaining owner/runtime work.

## Delivery and pending qualification

The corrected additive SQL component is pushed as `97d436b4`; all 780
committed paths and bytes were verified. Phoenix `40222180472` passes every
step; Engine `40222180507` passes all three jobs. No migration or caller is installed.

The decoder and corrected relation source contract are pushed as `0a6f110d`;
all 317 committed paths and bytes were verified. Phoenix `40221267196` passes
all workflow steps; Engine `40221267164` passes all three jobs. The preparation SQL
component is accepted locally after its ACL correction. See
[SQL review](docs/hosted-browser-activation-preparation-sql-review.md) and
[root acceptance](verification/hosted-browser-activation-preparation-acl-correction/root-acceptance.json).

The reviewed partial catalog prerequisite is pushed as `9d5c40ee`; 365 explicit
paths and remote main were verified. Phoenix `40219535335` passes selected
storage/migrations, then fails Mix formatting before broader tests: one extra
terminal newline in each new product module. Root corrected only terminal LF
bytes and reran the actual formatter, selected warnings-as-errors compile,
26 PostgreSQL 17 producer methods and 20 independent PostgreSQL 16 methods.
All pass, with cleanup. Corrected `6baf9acc` Phoenix `40220447677` passes
every step; Engine `40220447676` passes all three jobs. The preceding catalog Engine
`40219535273` passes all three jobs. See [correction](docs/hosted-browser-catalog-format-correction.md) and
[delivery](verification/github-delivery-browser-catalog/receipt.json).

The reviewed constructor slice and storage-fixture repair are pushed as
`4b458d6b`; all 490 explicit staged paths and remote main were verified. Phoenix
`40214597512` passes all workflow steps, including browser storage/migration
checks and the broader hosted suite: 645 methods pass and two existing methods
remain skipped. Engine `40214597602` passes all three jobs. The separate catalog source and
current decoder/relation lanes were excluded. See
[delivery](verification/github-delivery-browser-runtime-constructors/receipt.json).

The discovery repair and reviewed runtime contract are pushed as `4492bbc7`;
remote main matches. Phoenix `40212854925` failed in storage fixture setup: the
raw ordinary directory query reached its unchanged five-second statement limit,
so all 23 methods were invalid and migration/broader checks were not reached.
A local replay of the original fixture passes all 23 methods, so the precise CI
cause remains unproven. A paired plan exposes 455 JIT functions: 133.830 ms with
JIT versus 0.279 ms with transaction-local JIT disabled. The narrow raw-directory
fixture alignment now passes 24 PostgreSQL 16 methods with unchanged deadlines,
commit/SQL-error rollback restoration and owned-container cleanup. Root accepts
that fixture repair. Engine `40212854904` passes all three jobs. Constructor/catalog
implementations were excluded from that push. See
[fixture evidence](docs/hosted-browser-storage-ci-fixture.md) and
[delivery](verification/github-delivery-browser-discovery/receipt.json).

The resumed slice is committed and pushed as `7e434330` to `origin/main`; remote
main matches. Phoenix `40211210237` fails after all 615 executed methods pass
(two existing skips): four selected fixture/spec files produce discovery warnings
under warnings-as-errors. The former 121-project deadline case passes in
449.6 ms. New browser storage and migration CI checks also pass. The narrow
four-path discovery repair passes eight actual Mix checks while retaining fatal
unknown-file/compiler warnings. Engine `40211210222` passes all three jobs. See
[delivery](verification/github-delivery-browser-lifecycle/delivery-receipt.json). Previous checkpoint `1257cbf8` Phoenix CI fails the
same first 121-project workspace read at its unchanged transaction deadline:
608/609 methods pass with two existing skips. Its exact output is preserved in
[the resume receipt](verification/implementation-resume-2026-10-25/receipt.json).
Local JIT measurements support the scoped correction but do not prove that CI
failure's cause. No new native, provider, deployment, FieldLog or GA evidence
is claimed.

Checkpoint `684bd524` is pushed to `origin/main`; remote main matches. It adds
reviewed cookie/protocol prerequisites, the mobile navigation adjustment and
retained CI timeout diagnostics. Console `40206420996` and Engine `40206420988` pass. Phoenix
`40206421015` fails the first workspace read's total transaction deadline
(566/567 methods passed, two existing skips); the separate protocol step passes. See
[delivery](verification/github-delivery-browser-auth-prerequisites/delivery-receipt.json)
and [current CI](verification/github-ci-684bd524/observation-4/receipt.json).
Root accepts the component slice with 112 console, 39 protocol and 30 independent
host methods; counts overlap. Live login and the prior Phoenix timeout remain
open, and no GA gate advances.

Checkpoint `f2aba240` is pushed to `origin/main`; remote main matches. It adds the
reviewed branded workspace route/session fencing and the CI fixture repairs.
Console CI `40204405241` passes. Phoenix CI `40204405232` fails one
121-project directory deadline test; the earlier migration and expiry repairs
pass. Query-plan diagnosis is in progress. Engine CI `40204405509` now passes all three jobs with no skips. See [delivery](verification/github-delivery-workspace-composition/delivery-receipt.json)
and [exact-push observation](verification/github-ci-f2aba240/observation-5/receipt.json).
Live login/session adapter and the broader qualification gates remain pending.

Workspace checkpoint `9a2bf16b` is pushed to `origin/main`; remote main matches.
It contains the reviewed workspace API/storage, website-branded selector, actual
console client, CI wiring and retained evidence. The local slice is accepted;
Console CI `40202578691` passes. Phoenix CI `40202578720` failed because five
fixtures expected seven migrations and the expiry-lock fixture missed its timing
window; the workspace HTTP/client join itself passed. Fixture repair passes 24 local workspace methods and eight-migration controls;
broader Linux fixture execution now confirms those repairs. Engine CI `40202578667` passes all three jobs. See
[fixture repair](docs/hosted-workspace-ci-fixture-repair.md). See [delivery](verification/github-delivery-customer-workspace/delivery-receipt.json)
and [the exact-push observation](verification/github-ci-9a2bf16b/observation-5/receipt.json).

Prior checkpoint `6ed7df4f` repairs the cold bearer pipeline compile order.
Phoenix CI `40199934265` and Engine CI `40199934237` both pass with no skips.
See [the completed observation](verification/github-ci-6ed7df4f/observation-3/receipt.json).

Prior checkpoint `c0334a99` was pushed to `origin/main` and remote main was verified.
It contains the reviewed customer HTTP routes, canonical path/digest binding,
ordinary CI fixture and retained local evidence. Phoenix CI `40197780896` failed
at cold router compilation; Engine CI `40197780881` passes with no skips. The
checkpoint therefore was not accepted as a complete exact-push verification.
The compile-order repair uses compiler-aware dependency checks and passes 64 scoped host tests, including a
regression that reproduced the original failure. See
[the repair](docs/hosted-bearer-cold-compile.md) and
[local evidence](verification/hosted-bearer-cold-compile/acceptance.json). See
[the delivery receipt](verification/github-delivery-customer-artifact-http/delivery-receipt.json)
and [CI observation](verification/github-ci-c0334a99/observation-5/receipt.json).

Prior console checkpoint `c4e1f571` is pushed to `origin/main`.
It contains the two reviewed console color corrections and updated delivery
evidence. Console CI `40195410847` and Engine CI `40195410870` both pass with no skipped steps.
Local console tests, TypeScript and production build already pass. See
[the delivery receipt](verification/github-delivery-console-contrast/delivery-receipt.json)
and [completed CI observation](verification/github-ci-c4e1f571/observation-5/receipt.json).

Artifact checkpoint `6fff5ab9` is pushed to `origin/main` and remote main was
verified. Its 2,198 changed paths contain the reviewed local customer artifact
composition, CI fixtures, seven-migration integration and retained producer/review
evidence. Phoenix CI `40195108526` and Engine CI `40195108524` both pass with
no skipped steps. See
[the delivery receipt](verification/github-delivery-customer-artifacts/delivery-receipt.json)
and [completed CI observation](verification/github-ci-6fff5ab9/observation-7/receipt.json).

The final console brand audit found two faint secondary text colors. Both now
use the website's existing muted token, increasing measured caption/footer
contrast from 4.05/3.39 to 5.25/5.38. All 32 existing tests, TypeScript and the
production build pass; logo bytes, palette, typography and layout remain intact.
This is a source/host verification supplement. Saved desktop/mobile images
predate the two color changes; no new browser or screen capture was performed.
See [the contrast receipt](verification/console-brand-contrast/receipt.json).

Prior checkpoint `9662eda1` is pushed to `origin/main`.
Its 506 changed paths include the reviewed transaction facade and rollback
correction, ordinary CI fixture/migration wiring, proposed artifact contract,
unselected adaptive retention model and current evidence indices. Phoenix CI
`40190910760` and Engine CI `40190910724` both passed for this exact revision:
one Phoenix job and three Engine jobs, with no skipped steps.
See [the delivery receipt](verification/github-delivery-authorized-transaction/delivery-receipt.json)
and [completed CI observation](verification/github-ci-9662eda1/observation-1/receipt.json).

Previous checkpoint `d385adf3` is pushed to `origin/main`.
Its 802 changed paths include the reviewed PostgreSQL lookup, scoped CI fixture
and migration repair, independently audited finite cache rejection, and accurate
evidence indices. Phoenix CI `40188545250` passes one job and eight steps;
Engine CI `40188545375` passes all three jobs and 38 steps. No steps are skipped.
See [the delivery receipt](verification/github-delivery-postgres-authorization/delivery-receipt.json)
and [terminal CI observation](verification/github-ci-d385adf3/observation-3/receipt.json).

Earlier checkpoint `cb56d4b9` is pushed to `origin/main`.
Its 621 changed paths include the reviewed pure customer permission policy,
callback-result correction and independently audited rejected retention experiment.
The live VM is unchanged. Phoenix CI `40185739942` passes its job and all eight
steps; Engine CI `40185739959` passes all three jobs and all 38 steps. Neither has
skipped steps. See [the CI receipt](verification/github-ci-cb56d4b9/observation-1/receipt.json)
and [the delivery receipt](verification/github-delivery-retention-authorization/delivery-receipt.json).

The branded Builds checkpoint is pushed in `ba9ad437`, with Console and Engine CI
passing. Prior checkpoint `b375e55de` records the reviewed iOS compile
correction and runtime preparation, strict Swift telemetry correction and independently
audited full diagnostic failure. All 389 changed paths are pushed and remote main
matches; the active retention candidate is excluded. Engine CI `40182820548`
passes all three jobs and all 38 steps without skips. See [the delivery receipt](verification/github-delivery-diagnostic-corrections/delivery-receipt.json).
The preceding `7b604864` adds the accepted bearer identity prerequisite, reviewed
source/host observers and then-unexecuted diagnostic preparation.
Phoenix CI `40179798794` passes its job and all eight steps without skips;
Engine CI `40179798720` passes all three jobs and all 38 steps without skips. See [the current CI receipt](verification/github-ci-7b604864/receipt.json). The preceding
`6b8aba35` records the full Swift failure, finite cache diagnosis, reviewed V8
execution and complete cleanup evidence; its Engine CI `40176959303` passes all
three jobs and all 38 steps without skips.
The preceding `6403eea9` checkpoint
integrates reviewed decode-plan reuse and fresh native builds; its Engine CI
`40174672304` passes all three jobs and all 38 steps without skips. See
[the terminal receipt](verification/github-ci-6403eea9-engine/terminal-receipt.json).
See [the latest terminal receipt](verification/github-ci-6b8aba35-engine/terminal-receipt.json).
No native/provider/GA acceptance follows from host CI.

The supported iOS baseline is 26.0, targeting iOS 26, 27 and onward. Current
private appearance evidence is narrower and records iOS 26.5. Section 8.3's
identical shared app design remains required on Android; platform-default public
paths are not complete parity. The latest user-supplied AGENTS override pauses
computer use, capture and native simulator/emulator tests. This HTTP slice starts
no native instances. Phones remain disconnected and their matrix is deferred to
final acceptance. When runtime tests resume, use one owned instance per lane,
clean up after every run and preserve unrelated projects.

Still required before completion: full public native/guest integration and OS
matrix; immutable published-package FieldLog consumption; signed clean-worker
builds; ready-for-testing distribution on both stores; connected customer console,
authorization and billing workflows; selected-cloud deployment, restore/failover,
security/operations and all specified accountable launch reviews. No implementation
slice replaces those requirements. See [PLAN.md](PLAN.md) for current execution
and [work-graph.json](work-graph.json) for every package's retained evidence.

Historical status text is preserved byte for byte in
[STATUS.history-2026-10-25.md](STATUS.history-2026-10-25.md). It records earlier
failures, intermediate selections and superseded pending states; consult the
current index and the source-bound receipts for present decisions.


2026-10-28 architecture selection: the corrected two-arm execution comparison passed independent source review (38 supplied pure tests, 412 independent checks, 11 mocked campaigns and 21 prefix cases). Root selected its unchanged finite limits and installed the manual workflow. Both optimized builds, finite/harness checks, actual geometry and cleanup must pass before either full run; at most two full attempts and eleven commands, no retries. Compilation, runtime results, feasibility and production-default promotion remain pending. The previous two-attempt cache campaign stays closed. The new network run at 8888d8e2 reaches both product methods and validates the exact 895-byte Rebar DAG capture, but both methods fail because :jose_jwk is unavailable; prepared archive timestamp correction is under source investigation. The 38-test FieldLog public host run remains pending. Native, device, UI/capture and held-process restrictions remain in force; gates stay 8 running, 30 planned, 0 verified.
