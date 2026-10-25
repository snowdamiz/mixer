# Independent analyzer design review packet

Verdict: accepted corrected bounded design only; root acceptance is required
before implementation selection. This packet qualifies no analyzer, CLI,
source preparer, original target, native runtime or GA gate.

The exact final decision is `final-receipt.json`; the final replay is
`commands/run-3/result.json`. Original and amended producer freezes are retained
separately in `inputs/` and `inputs-amended/`. Raw finite outputs and exact
executed runner/test sources are retained for all three review attempts.
`history-audit.json` verifies the amended packet's original 59-member archive.
`historical-sidecars.json` binds 17 unchanged invalid/failure15 sidecars.

Read-only verification:

```
/opt/homebrew/bin/python3 -B verification/swift-ordered-retention-analyzer-review/verify.py
```

It checks this review seal and every current upstream member, then replays the
25 frozen and 23 independent finite methods and the retained owned layout probe.
It creates no evidence member or bytecode. This does not recompile or run an
analyzer, original workload, source preparer or native target.

A fresh explicit review replay (mutates this owned packet and requires resealing):

```
/opt/homebrew/bin/python3 -B verification/swift-ordered-retention-analyzer-review/run_review.py --snapshot inputs-amended --design-seal c52828b9bbd2aea835871f1f6b68c6dd29281499ee080e5e52fefe525d1e92a8
```

The review runner hashes every archived candidate source member without
restoring/importing/executing it; compiles only the isolated `layout.rs`; and
never starts or discovers native, capture, UI or product processes. No hosted
harness or catalog-inspector/authority-driver/rejected-worker source is imported.
All synchronous children finish and are reaped. Owned evidence binaries are
retained; no disposable source/build scratch is created or left behind.

The 41,984 transient reservation and immediate/source-preparer inventories
remain proposed bounds. The 13 data/stdio FD count excludes disclosed opaque
launch internals and preexisting host stdio; it is not proof of a safe CLI.
Private unsafe FD adoption is unimplemented and requires trusted-wrapper source
review. Source verification's separate 64M receipt prerequisite is unavailable.
Rust never authoritatively sets fullReplayAccepted. All historical sidecars stay
invalid. Native/capture/device and full-target work remain paused or unselected.
