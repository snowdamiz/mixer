# Reference-first focus diagnostic checkpoint

The next diagnostic starts from the existing plain UIKit button. Its new test
checks the authoritative accessibility sample before issuing one public Tab;
if that button is not focused, it stops before injection. The original six test
methods, observation timing, fixed three targets and strict traversal oracle
remain unchanged. This is a diagnostic source derivative, not native acceptance.

The 39-source derivative compiles its core, UI, app and runner with Xcode 26.6,
the iOS 26.5 simulator SDK and minimum iOS 26.0. Compiled products are retained in
the v1 archive; the classifier repair did not rerun compilation. Source and
product bindings were independently checked. Compiler warnings remain visible,
and the owned 164,590,153-byte compiler scratch was removed.

Independent review found three classifier defects, represented by eight failing
controls: Python equality accepted boolean-to-integer verdict changes, optional
integer reporting fields accepted equal floats, and a huge timestamp raised an
uncaught overflow. V2 requires exact JSON types, strict optional integers and a
structured failure for numeric/depth errors. All 34 producer controls and all
137 independent controls pass. The original v1 and its failed review remain
unchanged, including every counterexample and the original authored-first
runtime failure.

Root file-only verification rehashes four frozen handoffs and their 36, 12, 12
and 19 members. Acceptance is recorded in
`verification/apple-focus-reference-root-review/acceptance.json`. It covers the
source derivative, retained compilation and classifier consistency only.

No new simulator run is selected or executed. The classifier cannot establish
where data came from: a separately reviewed importer must bind official results
and unique attachments to the selected method, fresh run, device, source and
compiled products. That preparation is the next step. Missing evidence cannot
be treated as zero injections, and a synthetic passing verdict cannot become a
native observation. All original full-case, cursor, keyboard, carrier, FieldLog
and GA requirements remain open; physical phones remain deferred.

See the [V2 repair](apple-focus-reference-diagnostic-v2.md), its
[independent review](apple-focus-reference-diagnostic-v2-independent-review.md)
and the [preserved native failure](apple-focus-diagnostic-runtime-v1-checkpoint.md).
