# Authored toggle pointer checkpoint

The repaired candidate passes the complete original 20-action private coordinator
pointer matrix on API37 arm64: 429 native assertions, 124 MotionEvents and
23,839 ms of instrumentation execution. All three repetitions of the previously
failing P03 drag now turn the toggle on and commit exactly one revision.
Tap, hold, reverse drag, cancellation, scrolling and disabled/stale/retired
authority cases retain their unchanged fixture and oracle.

Root verifies all 124 synchronous worker/Activity delivery intervals, with a
maximum measured scheduling lateness of 21 ms, 573 observations, 73 exported
files and 107 command outputs. The retired G03 target returns false for its two
events without an exception; the root review's initial assumption that every
Activity dispatch returned true is retained as a failed review attempt. No
native rerun or fixture change was needed to correct that review assumption.
See [baseline acceptance](../verification/android-authored-toggle-runtime-root-review/baseline-acceptance.json).

Candidate source closure:
`509ef6a00bbaf034ebbe9dd6d8d3b8716fe96d9600e7fe8fa92fac41ebca3f99`.
APK SHA-256:
`24d75ecc19d08f44adc95e2db123936687929ca5a9fcd71f19189865240f6d18`.
Independent host review reproduces the compositional Java/DEX build and passes
33 producer policy tests plus 3,556 independent assertions. Runner review passes
55 previous and 23 new host controls; root separately repeats the 23 controls.
These counts are separately attributed and do not substitute for native results.

The separate component supplement crashed before writing its result file. Its
runtime cause is unobserved because no crash-buffer export was captured. No
preview, keyboard, accessibility or component-cancellation assertion is accepted
from that attempt. Fixture-only main-thread failure forwarding and bounded crash
collection are being prepared without changing production code or case assertions.
See [supplement failure review](../verification/android-authored-toggle-runtime-root-review/supplement-failure-review.json).

An earlier predispatch attempt omitted the pinned JAVA_HOME and failed official
APK verification before any emulator started. Correcting that command-local
environment enabled the successful baseline run; the runner and APK were unchanged.
Every attempt retains its own evidence. Both started emulators, owned child
groups and ports were stopped; 172,984,646 baseline and 172,979,648 supplement
scratch bytes were removed after holder and identity checks. Unrelated projects
were preserved. No physical phone was queried.

This accepts the bounded baseline matrix, while live Android integration awaits
the remaining component evidence. Full renderer authority/lifecycle coverage,
shared Apple appearance parity, public/signed transport, immutable FieldLog
packages, physical phones, store/customer/operational evidence and G06/GA remain
pending. Mac access is now available again; a separate Apple runtime preflight is
preparing the preserved candidate for one owned iOS simulator.
