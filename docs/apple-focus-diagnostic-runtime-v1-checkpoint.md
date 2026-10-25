# Apple focus diagnostic runtime checkpoint

The selected iOS 26.5 simulator run produces a valid official result: public
Settings setup passes and the first enabled-off Tab test fails. The unchanged
oracle still rejects `actualNativeFocusTraversal`; no cursor completes. This is
accepted failure evidence, not keyboard or G06 acceptance.

Preparation passes 34 producer controls and seven independent controls. The
selected packet is `d7c4c0f146434eeb7323036809acb5b4a80d41ff10f596eed8c25bdaa314e783`.
It uses the previously compiled app and runner, Xcode 26.6 (17F113), the iPhone
17 Pro simulator on iOS 26.5 (23F77), and the accepted command observer V2.
The original three-target oracle, time bounds and compiled product bytes are
unchanged. The earlier default-Xcode probe did not dispatch native work; the
actual run uses the pinned Xcode 26.6 installation.

The command exits 65 after 58.214 seconds; both output streams reach EOF and its
owned process group is absent. The earlier 600-second finalization stall is not
reproduced. Its cause is still unproved, and the observer is not claimed as a fix.
All five cleanup operations pass. Root independently records the owned simulator
and command group absent, no active simulators, and retirement of the ephemeral
configuration. Prepared scratch (123 files, 29,245,884 bytes) is removed after
post-run source/product verification. No physical device was queried.

[Offline analysis](apple-focus-diagnostic-v1-analysis.md) passes 39 checks and
reproduces the complete unchanged oracle result. During the 322.307 ms Tab call,
the same attached carrier loses focus, regains it, then loses it again. Eight
context entries contain only that carrier and explicit null endpoints. No new
focus destination is identified. Final app and authoritative AX observations
agree; the later 16.070 ms focus-only check also reads all three targets false.
Sequential reads are neither atomic nor continuous observations. No product
cause or safe product repair follows from this trace alone.

The smallest proposed next diagnostic starts the first Tab from the existing
plain UIButton reference under the same environment and strict predicates. It
requires a separately reviewed diagnostic fixture and has not been selected or
run. Comparator coverage, the full keyboard matrix, physical phones, published
FieldLog packages, signing, store, operational and GA requirements remain open.

Root's [runtime review](../verification/apple-focus-diagnostic-runtime-v1-root-review/runtime-review.json)
rehashes all 2,726 retained runtime files, 61 independent review files and the
analysis inputs/outputs. The complete 100,640,374-byte runtime archive and raw
xcresult/media/compiled copies remain local, bound by the published manifest.
Compact official JSON, observations, command logs, source and review evidence
are committed. The publication manifest records this distinction explicitly.
Frozen preparation receipts describe their earlier preparation-only scope;
this checkpoint and the root runtime review record the subsequent failed run.
The selected packet must not be replayed after its owned scratch retirement.
