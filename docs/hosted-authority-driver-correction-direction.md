# Authority driver correctness corrections

Root selects two reproduced correctness defects from the independent review's
completed local evidence. The review agent stopped after an automated safety
flag before producing a final review packet; its raw outputs remain preserved.
This direction records those observations without claiming completed independent
acceptance. All four of its owned environments report cleanup.

1. The active-context guard uses Elixir's non-strict comparison. Eight copies
   changed an integer to the numerically equal float and passed the guard,
   committing eight synthetic fixture effects. The changed fields include
   identity values, admission/decision revisions, a membership revision and
   backend PID. The review records no changed authority value. This violates
   the exact immutable context/type contract; use strict whole-context equality
   before guarded queries/effects. Keep equivalent immutable values with the
   original types valid. Preserve the original reference, owner, transaction,
   target and deadline checks.
2. `Rejected.message/1` interpolates a tuple reason that has no `String.Chars`
   implementation. A normal revoked-family denial produces `{:database,"42501"}`
   and formatting raises another exception. Return one fixed bounded sanitized
   message for every reason. Keep the existing structured internal reason for
   typed handling; never stringify arbitrary reason values into diagnostics.

Only these two implementation changes are selected. SQL schema/functions,
composite transport, locks, clocks, role privileges and dependencies remain exact.
The corrected copy must replay the original 56 cases and explicit regressions
for all eight type substitutions with no effects, correctly typed copies, normal
database denial formatting and arbitrary reason shapes. Preserve the previous
finding oracle separately and label the corrected rejection expectation. Record
actual commands, frozen source/dependencies, output, failed attempts and cleanup.

Own `verification/hosted-authority-driver-correction/` and its documentation only.
No live product integration, schema migration, HTTP or GA acceptance follows.
Independent acceptance remains pending.
