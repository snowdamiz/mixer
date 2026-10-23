# Native attachment publication repair

Hosted run39961877995 at35a9a36 exposed a production lifecycle defect after its
113 activation XCTests passed. SwiftUI was invalidating an NSHostingView graph
when representable dismantling called `detachNativeAttachment`. Publishing
`inputEnabled` synchronously reentered that graph and aborted the process. The
complete hosted log and job metadata remain in `../github-ci-35a9a36/`.

The model now publishes readiness separately from its computed attachment/live
input gate. Claim, duplicate-claim and detach callbacks mutate only native
authority/probe data; they do not send observable changes into SwiftUI's graph.
Detach still immediately rejects old actions and display tickets. A replacement
attachment reads readiness when its native subtree is constructed. The existing
sole consumer handles ordinary readiness/frame/stop publications; no extra Task,
dispatch item or notification queue was added.

Before an attempt is bound, a duplicate attachment latches failure and leaves the
observational state waiting. Binding publishes the same typed before-intent stop.
This avoids publishing during native construction while preserving fail-closed
startup and subsequent authorized fallback behavior.

The new regression finds five synchronous publications in the old source and
none in the repair. Debug/Release each execute13 tests with the visible positive
window check explicitly skipped; TSan executes12. Official iOS native-wrapper
and Android unsupported-platform module compilation pass. Exact commands/hashes
and local tool versions are in `receipt.json` and the linked candidate7 receipt.
The old-source publication regression is not a claim that the newer local OS
reproduces the older hosted SwiftUI crash.

To independently replay the old-source failure into a fresh directory:

```sh
python3 verification/guest-ui-teardown-repair/reproduce-baseline.py --output /tmp/mixer-teardown-baseline-new
```

To rerun the repaired scoped host/mobile matrix with a fresh receipt name:

```sh
python3 verification/guest-ui-presentation/verify.py teardown-new-run
```

Pinned hosted CI remains the required confirmation for its observed crash.
The previous actual signed Mac flow is preserved at5a0367d; this repair does not
claim a new signed visible-window, physical-mobile, full Swift, consumer-package
or GA qualification. Phones remain disconnected.
