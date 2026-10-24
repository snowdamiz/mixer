# Native toggle input checkpoint

Android's authored V2 toggle input is integrated into the live tree after the
reviewed API37 emulator results. The 20-action coordinator matrix passes 429
assertions. The component fixture passes all 45 cases, with 213 original and
26 setup assertions. The finite offline collector correction preserves the
original collection failure and every native predicate. All 89 product inputs
match the tested candidate, and the live compositional rebuild reproduces all
163 class artifacts and DEX bytes. See the
[integration details](android-authored-toggle-integration.md).

Official XCTest now establishes real iOS 26.5 input delivery. The standalone
pan, blank-list scrolling, vertical scrolling starting on the carrier and all
six tap transitions pass their native predicates. All four directional carrier
pans receive movement but reject admission: the last observed finger displacement
before admission exceeds nine points while the recognizer reports only about two
points to the carrier's six-point policy. A separate candidate is correcting
that measurement using the public touch origin, preserving the threshold,
directional dominance and existing preview/release behavior.

The iOS run remains failed and incomplete. Fourteen of fifteen action evaluations
were collected, nine passed, four pans failed, and the comparator's original
strict direct suite failed. The diagnostic direct test reports `invalidResponse`;
its separately captured native observation contains only 11 of 19 checks and
still says running. The precise bridge error was not durably saved. All 12
XCTest methods reported completion, but xcodebuild did not exit before its
600-second bound and was terminated. No missing result is counted as passed.
The [root review](../verification/apple-toggle-xctest-root-review/runtime-review.json)
binds full observations, interrupted command output and cleanup.

Both owned test instances are gone. The Android ports and command groups are
empty; the iOS simulator was deleted, the capability workspace removed, and the
bridge server/thread closed. Baseline simulator identities/states and the
Simulator frontend were preserved. Physical phones remain disconnected and are
deferred to final acceptance.

The console check at `ef751004` passes strict TypeScript checking and nine host
tests. The preceding `fb7eb45d` engine run passes all three jobs and 38 steps.
GitHub also reports the `ef751004` engine run and jobs successful, but its detailed
Swift step statuses are inconsistent; that limitation is retained separately.

Swift dispatch accounting and the private Linux webhook resource harness remain
in progress. Full shared appearance parity, public application routing, physical
accessibility, immutable external FieldLog packages and all GA/dogfood gates
remain pending.
