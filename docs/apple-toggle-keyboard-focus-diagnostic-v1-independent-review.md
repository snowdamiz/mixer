# Apple keyboard focus diagnostic V1: independent source review

No blocking defect was found in the compact source preparation. The 19,426-byte
patch reproduces exactly against all eleven bound inputs; its six proposed
source outputs and manifest are deterministic. This review accepts only the
source preparation boundary. It selects no build, native attempt, retry, or
release and grants no runtime or product acceptance.

The review reran the producer's 17 controls without invoking its writing runner,
then ran 12 independent controls under Python 3.14.8. All 29 passed with zero
failures, errors, or skips. The independent runner writes only
`verification/apple-toggle-keyboard-focus-diagnostic-v1-independent-review/`.
An audit hook refuses repository code execution outside the three producer host
modules and six explicitly reviewed pure oracle modules; it also refuses writes
outside that review directory, process launches, and socket connect/bind calls.
All reviewed producer/original files retained their exact pre-review hashes.

## Direct retained oracle result

The producer's failed-cursor test is a local retained-verdict double. This review
additionally inspected the complete pure dependency chain of both bound keyboard
oracles: the pan-commit, pan-origin, interruption, and semantic oracle modules,
plus three JSON case tables. These modules use standard-library data operations
and import no authority driver, bridge, composition, selected harness runtime,
process, network, native, or UI module. Only this reviewed pure chain was loaded.

The original retained before/after observations and keyboard witness were passed
directly to the retained V2 keyboard oracle. Every oracle-produced field equals
the original retained verdict. Its three bridge-added annotations (`actionIndex`,
`generation`, and `ownedSimulatorIdentity`) are the only excluded fields.
`passed` remains false, `observedFocusBefore` is `authored-toggle`,
`observedFocusAfter` is null, and exactly one predicate is false:
`actualNativeFocusTraversal`. The resulting complete oracle verdict is retained
as `direct-oracle-verdict.json` in the review directory.

Favorable follow-up focus, nested purported passing decisions, malformed binding,
boolean generation, oversize, nonfinite, and nonserializable diagnostic payloads
cannot replace the witness or change that direct full-oracle result. Invalid
envelopes retain incomplete receipts. A diagnostic storage exception propagates
before evaluation; it grants no progress. The adapter validates the diagnostic
envelope and size, not every nested telemetry field; its content carries no
decision authority.

## Source and progress isolation

Removing the new diagnostic import and pre-evaluation retention call restores
the original keyboard bridge bytes exactly. Both oracle source files are absent
from the patch. The original first acquisition Tab, public key calls, fixed
three-ID membership, semantic methods, completion guard, and failed-verdict
branch remain unchanged. No initial-focus shortcut or favorable-sample selection
is present.

The actual pure cursor accepts the retained setup commands and checks the
witness. Applying the unchanged bridge branch's explicit failure latch leaves
acquisition count, phase, completion, and last-after unchanged; the actual pure
cursor then refuses a further baseline. The existing composition guard requires
the prior cursor's `complete is True` before a next begin, so this failed cursor
cannot satisfy it. The bridge and composition are source-verified only and were
never imported or executed; this is not a runtime integration receipt.

The focus context trace has its own revision, storage, and exact dropped count.
It leaves the original strict trace methods byte-identical. A 259-transition
host control retains sequences 1–128 and reports 131 drops. Null endpoints have
explicit null state and null metadata; outside-ID and anonymous non-null items
remain distinguishable as item state. Controller/carrier hooks call `super` and
record public metadata without adding focus requests or redirects. App persistence
observes the independent context revision through the existing side channel.
Swift/UIKit behavior remains uncompiled and unverified.

Each full AX row is timed around its existing wait and sequential reads. These
intervals remain explicitly non-atomic and outside the closed witness. The
original witness end timestamp is retained; four collection records are kept per
action with further collections counted as dropped. The one follow-up starts
only after the authoritative witness is fixed and cannot assign its `after`.

## Budgets and remaining limits

The follow-up queries each of the same three IDs at most once and admits no new
row after the earlier of 250 ms from pass start or the original witness's
12-second window end. Host controls cover an already-expired deadline and a
synchronous read that returns late. That late read is retained as
`incomplete-budget` and stops the pass. A public synchronous XCUI query cannot be
preempted: this is a bounded call count and admission deadline, not a proven hard
wall-clock ceiling. Extra reads can affect runtime timing.

The existing request/method source prefix is byte-identical. The original
12-second request/13-second wait, strict 12-second witness window, 8,192-byte host
body limit, and 600-second command ceiling are unchanged. The diagnostic record
is capped at 4,096 bytes with an incomplete marker on overflow. No command-runner
or test configuration file is patched. Command finalization instrumentation is
still a separate pending slice.

The full-app AX hierarchy/focused-item inventory proposed in the failure analysis
is absent from this derivative. Its observation scope is public focus endpoints
and a follow-up over the three existing IDs. That is a recorded scope limitation;
no whole-tree inventory or native destination result is claimed.

No native/compiler/build/simulator/emulator/device/process inventory/network/
server/UI/capture/Git operation was run. There is no materialized source tree or
execution packet. Physical phones remain disconnected and deferred. Native,
carrier, OTA, immutable published-package dogfood, store, operational, and GA
gates remain pending. Root owns any later selection.

## Reproduction and source binding

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-toggle-keyboard-focus-diagnostic-v1-independent-review/review.py
```

The inherited source revision label is
`ba9ad4372f94463ba4d363cdfd76dd565c96413f`; it was not queried through Git.
The original execution seal remains
`7baff6c525359b0647caa2808d0fa73b7d1e8cc54146408d904570eabd80e3b7`.

| Item | SHA-256 |
| --- | --- |
| Eleven-input tree | `a1b254cd94628cc63fcf086dcb80310bf166877c46f39c2af1cefa9c75577fb2` |
| Six prepared sources | `91e86b048aa920917e1882f062ef32cea278e23a4529b973e75179c27e819969` |
| Compact patch | `5d86c026f5356491a0e759552144f8e50304bece3eb17a266837b37022216adb` |
| Direct full-oracle failed verdict | `4d2bf98c27623f4d1fccfb52be36a22b4ac1192e8f057e3975f4539bc524f195` |

`receipt.json` records the command, tool version, exact reviewed source hashes,
test counts, output hashes, executed module allowlist, and limitations. Tree
digests are SHA-256 of sorted indented JSON descriptors with a trailing newline;
they seal preparation and review data, not an executable packet.
