# Independent envelope partition review

The frozen candidate is acceptable for **one root-selected hosted diagnostic**,
not an accepted Engine fix or production/default change. The canonical envelope
runner and all producer packet bytes remain unchanged. The original Engine
40801222690 timeout remains the baseline; this review establishes no speedup.

Root subsequently observed the unchanged canonical envelope step pass in ordinary
Engine 40806044568 at `c7648ab4`; its actual artifact replay is still pending.
That source-identical pass is evidence of variable whole-suite timing, not a
causal performance result or completed Engine acceptance. The partition remains
a proposed way to collect per-group timing and bounded completion evidence.

The 18 partitions preserve all 78 producer names in original lexical order:
17 exact root filters and one 61-method embedded group. Each process receives
separate fixture scratch. The independent 14-method binary remains one run.
Every command still shares the 480-second active deadline; each producer group
has at most 120 seconds, and retention/cleanup gets 60 seconds. Capture is capped
at 8 MiB per stream and 64 MiB across the invocation. The first failure stops
later groups. Unresolved child/group custody prevents another command and scratch
removal. Real process behavior remains untested in this review.

`review_controls.py` passes 18 guarded methods, including all 36 command/summary
failure boundaries, exact filters, capture/deadline/custody controls, all eight
API probes, compiler admission, and a full 40-command orchestration with fake
children and inert compiler products. No real nested process, signal, session,
group, wait, socket, compiler or product runtime was accessed. The initial review
harness failures and intermediate output remain local in ignored `logs/`.

The producer's `verify_packet.py` dereferences local preservation anchors in its
decision, including dirty protected files and the original whole `verify.yml`.
Those are not envelope runtime dependencies and cannot bind an ordinary fresh
checkout after the separate fixture adoption. Its test entry point also rewrites
`runner.diff`. Preserve both originals; the proposed workflow uses this review's
guarded controls and `admission.py` instead. `source-bindings.json` distinguishes
actual source/contract dependencies from local bookkeeping anchors.

Root may install `workflow-proposal.yml` byte-for-byte as
`.github/workflows/envelope-partition-diagnostic.yml`, then select one exact
committed SHA. The workflow is manual only, denies reruns, checks the supplied SHA
against the GitHub source SHA, and requires a GitHub-hosted macOS ARM64 runner.
It uses the already-present direct compiler at
`$HOME/.rustup/toolchains/stable-aarch64-apple-darwin/bin/rustc`; the frozen runner
admits only 1.98.1 or 1.99.0 ARM64 identities before compilation. There is no
installer, search, fallback or retry. Missing or changed compiler state fails.

The proposed job runs the candidate once and retains the complete artifact even
after failure. Terminal replay requires all 40 commands, 78+14 methods, 32 layouts,
21,714 comparisons, eight exact API refusals, output/source hashes, postflight and
scratch cleanup. It also refuses extra contradictory oracle-counter markers.
An independent review of the actual hosted artifact remains required. The workflow
enforces one invocation per first dispatch attempt; root's campaign selection
must enforce the single-dispatch limit across separate manual dispatches.

Run source checks only:

    python3 -B verification/envelope-partition-independent-review/review_controls.py
    python3 -B verification/envelope-partition-independent-review/admission.py verify

No workflow was installed or dispatched by this lane. All native/UI/capture,
physical-phone, local compiler/custody, Unit A, broad-hosted and FieldLog held
identities remain untouched. No GA gate or customer/OTA qualification changes.
