# Focus-system V8 native result

The single selected V8 attempt completed with **Settings Passed and first Tab
Failed**, zero skips, and Xcode exit **65**. The strict original verdict remains
failed: `actualNativeFocusTraversal` is false; all nineteen other original
predicates are true. One public `XCUIElement.typeKey(_:modifierFlags:)` Tab
returned. AX focus was on `plain-uibutton-reference` before it and on none of the
three fixed targets afterward. There is no paired app/AX focus disagreement or
missing app focus-update signal. This evidence does not establish a defect in
the authored toggle.

Run `d9a1ae2b-ef02-4db2-b2ff-4979213c8236` used the selected arm64 iOS 26.5
simulator build `23F77`, Xcode 26.6, SDK 26.5 and minimum iOS 26.0. The owned
simulator was `MixerFocusReferenceV8-d9a1ae2b`, UUID
`9CDA64A8-4057-4327-99B1-2ECE73C07EC2`. The root selection binds packet
`70dcc748cf67ce6573215b3815736aca4689707cc081d34c8069f9b5f13c3a82`,
compile-source tree
`ddd4036d785c1c5f0161f8146ee7295b8df8dcd2bd615b45eebefc4112fcfb0d`,
and the fresh product archive
`681059d32edbd63128c8f4552af2ed161d6dce05847397ffa6ce57b5402364d9`.
The prior independent host review and accepted preparation handoffs are pinned.
Revision `6403eea98031207f6e40a72b55dfd3bd4e7e6ec2` is the root-reported context;
this audit issues no Git query.

The [audited result](../verification/apple-focus-system-native-result/result.json)
binds official summary/tests, the exact observed native argv, full observer
streams and EOF, official exported attachments, original application packets,
selected source/products, durable one-attempt marker and recorded cleanup. The
complete retained attempt contains 2,367 files / 109,513,018 bytes. Their paths,
types, modes, link counts, lengths and hashes are retained in the
[evidence manifest](../verification/apple-focus-system-native-result/native-evidence-manifest.json),
alongside complete recorded root-selection and outer-observation inventories.
No native raw data is copied. The 140 directly bound input files and sealed
upstream members are checked separately. No runner, oracle or frozen V7
supplemental join is imported or executed by this audit.

The outer Python dispatcher exits zero because observation and collection
completed; it records no timeout, retry, observation error or remaining owned
process group. That is distinct from the observed XCTest exit 65. Official
results contain exactly two selected executions, one passed and one failed.
The retained importer records `provenanceAccepted: true`,
`one-strict-original-verdict-failed`, and no bridge, session or reporting
failure. Original verdict/witness bytes agree with both their selected official
attachments and retained application packets. Public Settings evidence is
complete and durable: 182 requests, thirteen uploads and 767,082 declared decoded
bytes. The original oracle, actions and budgets are unchanged.

All five recorded cleanup operations pass: server shutdown, server close,
thread join, ephemeral capability-configuration retirement and owned-simulator/
baseline reconciliation. Recorded shutdown and deletion of the owned UUID exit
zero; the final recorded inventory contains no owned simulator and preserves all
four pre-existing simulator UUID/state pairs. Before/after frontend inventories
are both empty. The secret `session.xctestrun`, staged sources and staged products
are absent; retained session/result evidence remains. These conclusions use
recorded command returns and lifecycle evidence; this audit makes no new native
or process query.

Root separately selected the exact immutable originals in
`original-selection.json`, SHA-256
`1cee9899bcbd1739787a6ba991a82e6e1fb924f3225420640a82f2d4040ae8f3`.
Their collected mode `0644` remains historical metadata; their current mode is
the explicitly selected `0444`. Bytes remain unchanged:

| Original | SHA-256 |
| --- | --- |
| Before | `814043886038e21a4d593fc1a021a3db130f4666f907c9ec9be49b1482a87362` |
| After | `1e7b50e24f5b02e45a2b469849bcf8b8a88c71bcaed90b5eff851677fc389d80` |
| Witness | `05eca28abe52b510e949609edfbf35770cf271e5e70584f17635f3d9cd8f04a9` |

The [bounded supplemental extraction](../verification/apple-focus-system-native-result/supplemental-extract.json)
retains exact original paths, hashes and zero-based JSON pointers. Both
`focusSystemDiagnostic` packets explicitly say `authoritative: false` and
`atomic: false`, with complete capture and zero dropped entries. Before has 27
entries; after preserves those exact 27 and adds five. The relevant literal
samples are:

| Original and entry index | Recorded focus-system observation |
| --- | --- |
| Before `/observation/focusSystemDiagnostic/entries/26` | System present; plain UIKit reference focused. |
| After `…/entries/27` | Controller callback, context 2: system present, focused item null. |
| After `…/entries/28` | Snapshot: system unavailable; all fixed controls unfocused. |
| After `…/entries/29` | Controller callback, context 3: different system identity; same plain reference focused. |
| After `…/entries/30` | Controller callback, context 4: focused item null again. |
| After `…/entries/31` | Snapshot: system unavailable; all fixed controls unfocused. |

The three appended controller callbacks are also retained at after-original
`/observation/focusContexts/1`, `/2` and `/3`: plain reference → null, null → the
same reference, then reference → null, each with heading zero. Their recorded
times fall within the returned key interval; the final unavailable-system
snapshot follows it. These are supplemental samples of loss, brief reacquisition
and loss of the reference. They neither identify the cause nor prove a successful
traversal. No candidate diagnostic supplies an original identity, no new anchor
is created, and the frozen V7 join remains replay-only. The historical V7 failure
is unchanged.

The [sealed handoff](../verification/apple-focus-system-native-result/handoff.json)
binds this report, audit source, result, manifests, exact excerpts and complete
host audit command receipt. The verifier rechecks all recorded identities and
the same failure/cleanup conclusions without writing files, importing selected
code, querying native devices or launching another process:

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-focus-system-native-result/audit.py verify
```

This result grants no carrier, broader keyboard/UI, physical-device, FieldLog,
store, operational or GA acceptance. Phones remain disconnected and deferred.
The narrow next action is to investigate the unchanged **plain-reference
app/window and public-key delivery contract**: `PrototypeDelegate` key-window
creation and scene association, `PrototypeController.preferredFocusEnvironments`
and controller callbacks, and `launchCase` → `XCUIApplication.typeKey`. Exact
selected members and lines are retained in
[source excerpts](../verification/apple-focus-system-native-result/source-slices.json).
The system-identity turnover around the plain UIKit reference supports examining
that lifecycle/input boundary before attributing the result to the authored
component. The cause remains unproven; preserve the original oracle, actions and
budgets.
