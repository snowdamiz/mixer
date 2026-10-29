# Envelope partition workflow context correction

This sibling corrects the authored manual workflow's invalid job-environment
reference to `${{ runner.environment }}`. The exact expression is now in `env`
on both context-consuming steps: begin/invoke and finish/replay. Job environment
keeps the reviewed SHA input and literal policies. Workflow script, sparse-checkout
and artifact paths route to this sibling; the source-control step also checks
the context correction and the installed workflow bytes before invocation.

The frozen parent review seal is
`057e500afa3ee57e0469e377c3c4f947053e1fe163f258f52e57ccc80cd5be73`.
Its original workflow and seal are preserved here as regression witnesses.
`correction-basis.json` identifies the parent, producer and reused official
context evidence. The parent's historical decision is not a decision over these
corrected bytes. `decision.json` records this correction's separate scope.

`admission.py`, `offline_guard.py`, `review_controls.py` and
`source-bindings.json` are byte-identical parent members. The actual producer,
canonical runner, frozen pack and compiler/lint contracts are unchanged. Admission
verifies this sibling's HERE-local seal; installed mode requires exact equality
between this sibling's proposal and the installed manual workflow. The complete
40-command terminal replay, source/context admission, output oracles and custody
requirements remain intact. The workflow stays manual, first-attempt only and
bounded to one invocation; root must enforce any campaign dispatch limit.

The original 18 guarded controls are rerun from this copy with fake children,
clocks and inert compiler products. The focused controls reproduce the original
job-env rejection, reject arbitrary `runner.*` properties at job scope, require
the exact step placements, compare the complete allowed transformation and
exercise seal/installed-workflow rejection paths. Parser functions and context
allowlists come from `cache-fixture-workflow-context-v4`; they are bound to their
frozen hashes. These are **narrow structural checks**, not execution of an
official Actions validator, GitHub parsing, Bash, a compiler or the product.

Run the source checks from the repository root:

    python3 -B verification/envelope-partition-workflow-context-correction/review_controls.py
    python3 -B verification/envelope-partition-workflow-context-correction/test_context.py
    python3 -B verification/envelope-partition-workflow-context-correction/verify_candidate.py
    python3 -B verification/envelope-partition-workflow-context-correction/admission.py verify

Raw test output and intermediate receipts stay in ignored `logs/`. The inherited
18-control reporter embeds its historical parent command and baseline; the new
`controls.json` records the actual sibling invocation and source identity scope.
The installed-workflow comparison control mocks only the file read; this is not
an installed-workflow or hosted run receipt.

Root reports that ordinary Engine 40806044568 at `c7648ab4` passes all six jobs
and independently verifies the original envelope's 23 commands, 78+14 methods
and 96.206916-second producer. The earlier 120-second failure remains preserved.
This source-identical variability supplies no causal speedup claim. The manual
partition remains useful for per-group timing and bounded completion evidence,
but this correction does not select, install, dispatch or qualify it.

No canonical/global file, Git/gh state, compiler/product runtime, process
inventory, held identity, native instance, UI or capture is touched. Local and
remote FieldLog, local compiler/custody, Unit A, broad-hosted, disconnected-phone
and native/UI/capture holds remain. No customer, OTA, production/default,
published-package dogfood or GA acceptance follows.
