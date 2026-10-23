# Signed Mac window verification

The real local native window flow passed on October 23, 2026. The authoritative
result is `receipt.json`, bound to `build-receipt.json` and
`runs/candidate-2/progress.json`. The app links the exact candidate4 runtime dylib
`500891f340d46e25216e32a59b2c91e25db7e50de17c1643e427446201138820`.

Root used native accessibility controls through `mcp__cua_repl` to open the app,
press **Start signed guest**, click the guest's **Save sample**, inspect the
rendered **Saved sample** screen, and press **Close and verify storage**. The
guest produced revisions1,2,3. The runtime reported a committed healthy candidate
through its public recovery snapshot. After public close completed, the public
KV reader found the expected four bytes (`AAH+/w==`), with no cleanup pending.
The app was then quit and absent from the running-app inventory.

Only public runtime open/download/start/presentation/recovery/close APIs are used
by `SignedWindowHarness.swift`. It does not inject native-display receipts, health
milestones, UI events or guest completion. The original test-only signer and
bytecode builder are copied exactly from candidate4's immutable source export.
The fixture's `@testable` import supports installed fixture metadata; it does not
grant the harness an internal presentation or runtime-control path.

`build.py` builds and ad-hoc signs the outer `.app` without changing its already
signed nested runtime library. It never launches or interacts with the app.
The build receipt contains commands, compiler output, source hashes, copied
resources and executable hashes. Re-running the same data directory is rejected.
For another run use fresh absolute `--output` and `--run-root` arguments, or a
fresh default run location in a new captured harness build. Preserve old receipts
and source snapshots before rebuilding. All runtime data directories are ignored
by Git; terminal progress records remain evidence.

The first harness required foreground/key-window status, which this app-control
surface did not supply. Its cleanly closed, unqualified run remains in
`runs/default/progress.json`; its original source and build receipt are under
`history/candidate-1/`. Candidate2 replaces only that harness startup condition
with an explicit native Start button. Production display checks and the runtime
binary stay identical. Earlier compile/signing attempts are retained as logs,
not successful flow receipts.

This is a local Mac signed bytecode/native-control/storage/display/close flow.
It is not a full compiled Swift guest, FieldLog feature, immutable published
consumer, linked release provenance, mobile lifecycle/accessibility/performance,
physical iOS/Android, store or GA qualification. AppKit `displayIfNeeded` observes
native display; it does not prove compositor timing. CUA screenshots were
inspected in the chat, but no separate pixel artifact is stored here.
