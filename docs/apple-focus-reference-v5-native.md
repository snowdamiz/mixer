# Fresh V5 native diagnostic

The single selected native run **failed its Public Settings precondition** with
`bridge transport failure: request timeout within existing2second budget`.
`test000PublicSettingsFullKeyboardAccess` failed; the dependent
`test010ReferenceFirstTab` was correctly skipped, leaving application input
unrun. The diagnostic outcome is unknown and receives no pass or completion
credit. No retry or budget change occurred.

The [result](../verification/apple-focus-reference-v5-native/result.json) and
[offline explanation](../verification/apple-focus-reference-v5-native/official-failure-explanation.json)
preserve both raw official method identities and all `official_methods`
predicate comparisons. The names, node identifiers and URLs match the two
selected methods exactly. The importer subsequently fails closed because the
second result is `Skipped`, outside its accepted `Passed`/`Failed` set; mandatory
Settings-pass and zero-skipped predicates also fail. Its generic
`Foreign/duplicate/incomplete selected test identity` error is secondary to the
Settings transport failure. The importer remains unchanged. Both raw attachment
owner identifier/URL pairs also match the selected methods; these attachments
grant no pass credit.

The official run timestamps are `1792900606.969` and `1792900656.355`
(`2026-10-25T03:56:46.969000+00:00` through
`2026-10-25T03:57:36.355000+00:00`). The retained terminal messages do not identify
the timed-out request ID. All 221 durable Settings attempts have committed
outcomes. The final committed record is sequence 220, PNG chunk index 20 of 71,
slot `settings-0195-png`, generation
`e365195b-f758-41b5-89f9-9bbe4cf5e749`; it is not inferred to be the timed-out
request.

The dispatcher exited 1 after 86.814 seconds; its selected XCTest exited 65
after 54.045 seconds. Both outer/native streams reached EOF, both recorded
process groups were absent, and no timeout or cleanup signal was needed. All
five native cleanup resources passed. The selected simulator was deleted,
secret configuration retired, and unchanged product/source scratch verified
before removal. An independent
[final inventory](../verification/apple-focus-reference-v5-native/final-inventory.json)
confirmed the owned simulator absent, all four baseline devices preserved in
Shutdown state, and no unexpected devices. Original producer members are checked
individually by the collection command; the producer is not re-frozen.

The reviewed correction packet is
`6c57bc5552a4f7e0e21ff1fdd589b270aa98b483f366f78bd88de2e26c0fd7dc`.
The compile-source tree remains
`696bfdd8a31be7b4d9ba49f57783625c7edbb75c126bb4696e31acc5aa0f238a`;
the immutable native product archive remains
`0941185e39cc0171b0bf5d2aeb72738588e88b9c7b3d676f893b70c3bf644fa8`.
Products, oracles, actions, windows and budgets are unchanged. The selection
contains only `test000PublicSettingsFullKeyboardAccess` and
`test010ReferenceFirstTab`, for `keyboard-enabled-off`: one reference-first Tab
diagnostic with no acquisition loop or completion credit.

The [read-only baseline](../verification/apple-focus-reference-v5-native/preparation-baseline/receipt.json)
at `2026-10-25T03:54:43.252299+00:00` found four existing iOS 27 simulators, all
Shutdown, zero iOS 26.5 instances and no pinned Simulator frontend. Preserve the
four instances and their data. Xcode 26.6 build 17F113, Swift 6.3.3, Python
3.14.8, xcresulttool 24757 and the available arm64 iOS 26.5 build 23F77 runtime
were observed. Exact commands, outputs and tool hashes are retained alongside
the receipt. This advisory baseline must be refreshed by root before creation.

Root owns creation of one `com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro`
instance on `com.apple.CoreSimulator.SimRuntime.iOS-26-5`, named
`MixerFocusReferenceV5-<unique suffix>`. The reviewed runner requires that
instance already to exist; it boots it if Shutdown, then shuts down/deletes only
that owned instance during cleanup, including failed diagnostic runs.

The root selection has exactly these ten keys:

| Field | Required value |
|---|---|
| `schema` | `mixer.apple-focus-reference-root-selection.5` |
| `runID` | Fresh canonical lowercase UUID |
| `packetSHA256` | Accepted correction packet above |
| `selectedAtUTC` | Canonical ISO timestamp, no more than 300 seconds old at dispatch |
| `ownedSimulatorIdentity` | Exactly `udid`, `name`, `runtime`, `build`; uppercase UDID, required name prefix, runtime above, build `23F77` |
| `sourceTreeSHA256` | Compile-source identity above |
| `productArchiveSHA256` | Native-product identity above |
| `developerDirectory` | `/Applications/Xcode_26.6.app/Contents/Developer` |
| `baselineDevices` | Complete root pre-creation `simctl list devices --json` object; excludes owned UDID |
| `baselineFrontends` | Exact ordered pinned frontend identities from the method below |

Collect frontends with `/bin/ps -axo 'pid=,lstart=,comm='`. Retain each
`line.strip()` only when it ends with
`/Applications/Xcode_26.6.app/Contents/Developer/Applications/Simulator.app/Contents/MacOS/Simulator`.
No frontend is launched or signalled by the reviewed native runner.

Root selected run `e7108fc8-281b-4c59-831a-f3697609017d` on owned simulator
`936A83B7-6E83-4423-85AB-C5812236073D`, named
`MixerFocusReferenceV5-e7108fc8`. The
[selection](../verification/apple-focus-reference-v5-root-selection/selection.json)
was sealed by SHA-256
`6753aca655b5b0404005bce2010e91229c43ff858fb34d9ae65f20968e1f157a`.
The recorded command was executed once:

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -B /Users/andreyyurlov/Documents/dev/mixer/verification/apple-focus-reference-v5-native/observe_dispatch.py --root-selection /Users/andreyyurlov/Documents/dev/mixer/verification/apple-focus-reference-v5-root-selection/selection.json --root-selection-sha256 6753aca655b5b0404005bce2010e91229c43ff858fb34d9ae65f20968e1f157a
```

The [outer observer](../verification/apple-focus-reference-v5-native/observe_dispatch.py)
has SHA-256
`1583eb5fb86a07d52e56a63d082992941807d9252dc1133e2a314f2d1610373c`.
It launches the correction's `prepare.py dispatch` exactly once, with the
accepted packet hash and supplied selection path/hash. The runner writes fresh
`native-run-v5-<runID>` evidence under the correction directory; frozen producer
members and handoffs are not regenerated. Product/source scratch is verified
before removal; native result and observation evidence remains.

The outer ceiling is 1,200 seconds, followed by SIGINT and 120 seconds for the
embedded cleanup, then bounded eight-second TERM/KILL grace periods for the
still-owned outer group. It retains both stream EOF/hash evidence and group
absence evidence. EPERM is unknown; a bounded complete process-table fallback
can independently establish group absence. Unknown observation remains
incomplete. Any timeout or incomplete observation requests root emergency
reconciliation; the observer never signals child sessions or deletes devices.
The reviewed 600-second XCTest, 120-second boot, 30/45-second test allowances,
eight-second command-group cleanup, and 660-second official timing window are
unchanged. No retry is authorized.

Six mocked outer group-observation controls passed, including EPERM with absent,
present and failed process-table observations. These host controls invoked no
native process. The
[compact handoff](../verification/apple-focus-reference-v5-native/handoff.json)
binds this document, tool/source/product identities, original frozen-member
checks, exact collected official JSON and a hash-only full output tree. The
collector creates no recursive archive or duplicate product package.
Its first offline collection attempt stopped on a single-link assertion for
durable Settings captures, which retain their designed hard links to staging
journals. The preserved attempt receipt records this collection failure. Native
output hashing now includes link counts without requiring a single link;
original frozen-member verification retains its strict single-link check.

Physical phones remain disconnected and deferred. This diagnostic cannot grant
keyboard/carrier completion, the full six-case matrix, immutable published
FieldLog dogfood qualification, signing, store, operational or GA acceptance.
