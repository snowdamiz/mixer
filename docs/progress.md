# Progress details

The [README](../README.md#progress) has the summary. This page describes what
each local gate has verified and what remains open. The implementation plan
requires all eight gates to pass on iOS Simulator and Android emulator with the
supporting services running locally. A separate
[launch checklist](../gates/ga.json) tracks release qualification. The full
history is in [STATUS.md](../STATUS.md).

## Local gates

**L01 Setup, adoption, and export: passed.** Independent review passed on
November 18. The public CLI and SDK create, export, and build starter apps for
both targets, and the importer reports on FieldLog's iOS source.
[L01 decision](../verification/receipts/l01-independent-final-review-41a05264.json)

**L02 Shared app and native UI: in progress.** The installed iOS and Android
apps passed their scoped local account lifecycles, including recovery and
confirmed deletion. The side-by-side design review for native reference
screens and the iOS Settings locale, Larger Text, and diagnostics checks
remain open.
[iOS account replay](../verification/receipts/l02-ios-account-system-browser-native-20261122.json) ·
[Android renewed deletion](../verification/receipts/l02-android-renewed-deletion-native-20261123.json) ·
[L02 decision](../verification/receipts/l02-independent-retained-review-20261123.json)

**L03 Compiler and owned runtime: passed.** Independent review passed the
supported local Swift scope. On iOS, an installed diagnostic mapped a VM trap
back to its Swift source and freed the VM on close.
[Installed runtime receipt](../verification/receipts/l03-installed-ios-taskcompletion-current-vm-20261122.json)

**L04 Safe OTA and recovery: passed.** Both installed FieldLog apps completed a
signed update and rollback from the same local origin. Both reopened offline
during an interrupted delivery and kept their data.
[Shared delivery receipt](../verification/receipts/l04-fieldlog-shared-delivery-native-20261122.json)

**L05 Local platform workflow: passed.** The console completed real builds on
both targets, showed their logs, and downloaded verified artifacts. Review also
covered cancellation, development signing, promotion and rollback, and store
protocol fixtures.
[L05 decision](../verification/receipts/l05-local-platform-acceptance-20261121.json)

**L06 Free accounts and administration: passed.** A free owner built,
downloaded artifacts, exported, and left the workspace without any payment
configuration. Leaving revoked access and kept the build history.
[L06 decision](../verification/receipts/l06-local-acceptance-20261119.json)

**L07 Security and local reliability: passed.** Independent review passed the
signed runtime, signer and worker recovery, restore, and privacy checks.
[Evidence](../STATUS.md#local-security-and-reliability-gate)

**L08 FieldLog and documentation: in progress.** Six of eight required FieldLog
milestones have passed. D2 still needs paired ordinary workflows and greater
shared Swift coverage. The installed F10 private fixtures passed on both
targets. The stock public runtime still refuses F10's UI schema, so the D8
public OTA count is unchanged. F11 live delivery, note editing, and rollback
passed on iOS.
[Android F10 replay](../verification/receipts/l08-d8-f10-android-live-replacement-20261123.json) ·
[iOS F11 replay](../verification/receipts/l08-d8-f11-ios-live-delivery-20261123.json)

## FieldLog milestones

FieldLog is the app used to test Mixer end to end. L08 needs the local version
of every milestone except D7. Statuses come from
[`dogfood/receipts/milestones.json`](../dogfood/receipts/milestones.json).

| Milestone | Status |
| --- | --- |
| D0 Baseline | Passed |
| D1 Engine adoption | Passed |
| D2 Shared Android | In progress |
| D3 Interpreted parity | Passed |
| D4 OTA delivery | Passed |
| D5 Recovery | Passed |
| D6 Platform workflow | Passed |
| D7 Production use | Deferred, not required |
| D8 Scenario confidence | In progress |

D2 covers the shared-app workflow on both targets. D8 covers repeated recovery,
upgrade, and export, plus a reviewed set of 20 update changes.

## Known limitations

- Physical-device qualification is pending. Simulator, emulator, and host tests
  do not count toward it.
- The local backend is not a hosted product.
- Published SDK packages and native VM, updater, and activation binaries do not
  exist yet.
- Release signing and store distribution are unfinished.
- On Android, OS keyboard behavior, window parity, and broader lifecycle and
  device coverage are pending.
- General YAML parsing for `mixer.yml` is unfinished.
