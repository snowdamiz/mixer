# Fixed-chunk Settings and first-Tab simulator result

The one selected iOS 26.5 simulator attempt passes the public Settings
precondition and fails the first Tab focus-traversal assertion. Both tests run;
neither is skipped. Xcode exits 65. The diagnostic dispatcher exits zero because
it successfully imports the original failing verdict with verified provenance;
that exit does not mean the native tests passed.

Root selected the independently reviewed V7 packet at source revision
`4a28261b333c28b4fce386f370a19b93e735c8d2`. The fresh runner uses the reviewed
4,992-byte chunk protocol, unchanged original application, and original
keyboard oracle and limits. Run `ddd94f80-4cb3-4a29-8fdd-c6868a343df4` uses
owned device `8415E228-91B8-4831-887F-BA2A96F056B7`, iOS 26.5 build 23F77.
The [root manifest](../verification/apple-settings-fixed-chunk-native/result-manifest.json)
binds 2,428 files with SHA-256
`ccb7ce47693677fcfc43f68939fdb9eeaa86bdeb6090ee9cfb5a5257a232382c`.

Before the single public `typeKey` Tab action, the plain UIKit reference has AX
focus. Afterward, none of the three observed elements reports AX focus. The
authored toggle reports no app focus before or after, so the paired app/AX
observations agree. The focus-update predicate is true because authored focus
does not change; it does not prove a new authored focus event. The original
verdict fails actual native focus traversal. This is captured behavior, without
an inferred cause or equivalence waiver. Independent offline event/source
review is underway before any correction or further native attempt.

All five cleanup requirements pass: receiver shutdown and close, thread join,
ephemeral capability workspace removal, and owned simulator/baseline
reconciliation. The owned instance is deleted, four baseline simulator states
are preserved, secret configuration is removed, and source/product scratch is
removed after exact verification. Both command streams reach EOF; the outer
observer reports no timeout or emergency reconciliation.

Two root selection-script errors precede native execution: a script name
shadowed Python's `select` module, then an incorrect packet field name stopped
selection after device creation. Their source and error receipts remain
preserved. Selection resumed for that same shutdown instance; there was one
native attempt. The supplemental local Settings failure record has no marker
and grants no acceptance. Its conservative false flag does not override the
official Settings pass.

First-Tab, the full six-case keyboard matrix, native keyboard/carrier
qualification, physical phones, immutable published FieldLog package use and
GA remain pending. Physical phones remain disconnected and deferred.
