# Shared work-admission source attribution correction

This compact source144 overlay corrects the original work-admission packet
sealed as `e8fe23ee4800a76ac6ca1486604b98b114a1f4dbdec1a25f520641c4e9951940`.
It reconstructs from the separately frozen accepted funding source144 tree
`7e3e861ca65d8c6359623443d6a7810b878c1029494a0ae557307d35ed43484b`.
Every original85 member and accepted144 source member is verified before use.
`correction-delta.patch` is the entire correction to the original candidate;
`source-delta.patch` is the complete overlay over accepted funding source144.
Only this packet is written. All original successful, failed and source evidence
remains immutable. No active independent, bootstrap or descriptor folder is read.

The accepted owner-storage recipe inventories raw unoptimized shared
`adopt_body_core_v1` closure roles as common C. The original work shell adds20
non-P-dependent roles totaling1,436 logical bytes to that same closure. All20
therefore belong to common C. The correction renames that constant to
`COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1`, adds it with checked arithmetic
after the existing78,240 common increment, and removes the selected-only1,436
increment. Existing S remains941,467, A430,175 and test H81,327; no old role or
callee-template credit is taken. The exact original20-role and work ledgers are
retained as separately hashed inherited evidence, with the corrected attribution
in `correction-accounting.json`.

Actual recorded compiler floors are:

| Configuration | F0 | Common | Selected | Admitted |
| --- | ---: | ---: | ---: | ---: |
| production | 366,312 | 445,988 | 1,387,455 | 1,817,630 |
| unit, including selected H | 366,896 | 446,572 | 1,469,366 | 1,899,541 |

The unit selected floor before H is1,388,039. F0 and both configurations' selected
and admitted totals are unchanged from the original work candidate. **Ordinary
common storage increases by1,436** from444,552 production /445,136 unit. Ordinary
source still evaluates the outer policy predicate: its bool role is included in
the common inventory, and its logical fetch/compare/decision costs3 source
actions. Specialization or constant folding does not remove those source roles
under the accepted convention. Successful ordinary adoption still leaves the
execution-work counter0. This packet does not claim ordinary source is unchanged
relative to accepted funding, or that a selected counter newly funds ordinary
source or timing overhead.

The correction itself moves only const arithmetic. The exact runtime branch,
associated policy values, counter0 before charging, successful same-counter
commit before NEXT_OWNER and all admissions, validation/deadline/stop precedence,
all diagnostics, refusal/retirement paths and final cleanup remain byte for byte
as in the original work candidate. Fresh production and unit unoptimized MIR
matches the respective original adoption functions exactly after removing only
source locations and comments. No runtime local or action is added by relocation.
The fixed selected price stays451,814,442; the branch upper-sum stays1,272.
Planning16,384 and emission `19537+299377B+32E` stay separate later debits.
The one-billion work ceiling and256 MiB combined memory ceiling are unchanged.

Fresh exact production/unit metadata compilation passes. A separately hashed
compile-only assertion overlay proves actual production F0/common/selected/
admitted floors; that overlay also checks unit floors in the filtered test builds.
The original seven private policy/control tests pass in debug and release.
Two separately named host tests per mode verify the actual unit floors and the
changed ordinary combined-admission boundary at the old floor, new floor-1,
equality and+1. These controls use an actual in-memory parser/validator proof and
a synthetic private policy core; no authentic selected ingress is dispatched.
The other468 tests remain undispatched. Standalone exact const-recipe tests pass
237 integer/overflow controls per configuration, including None propagation,
every increment's exact overflow boundary, selected H and admitted A. Synthetic
scalar F0 inputs are distinct from the actual compiler-checked product floors.

Three initial concurrent whole-source unit/debug/release compiler attempts hit
their55-second limits. All outputs, source bindings and cleanup receipts remain
under their original command labels. Sequential retries with explicit180-second
caps pass; no source or product budget was changed for a timeout. Every host
execution remains bounded at30 seconds. Full commands, environments, Rust1.99
aarch64-apple-darwin version and compiler hashes, source manifests, exact outputs
and owned-process-group cleanup are recorded under `commands/`. Compiler stdout
uses lossless gzip with uncompressed hashes. The former runner is copied into
initial command folders before adding the retry timeout option. Only owned
groups are rechecked; scratch and binaries are removed. No global inventory runs.

Trusted bootstrap grants, pre-ingress H ownership/funding, authentic selected
loader ingress, complete source work funding, operational release, healthy final
cleanup qualification, immutable-package FieldLog dogfood and every GA gate
remain pending. Source storage attribution does not fund pre-commit work.
`WorkAuditPending` continues refusing before A commit and writer admission.
No loader, guest, cache construction, snapshot scope/construct or writer executes.
No phase-retention or descriptor change is integrated. Native/device/simulator/
emulator/UI/capture runtime checks remain paused and pending.

This packet is frozen after verification. Rebuild scripts must only run in a new
unfrozen copy; reconstruct each compiler input using the source manifest and its
explicit production/test/compiler overlay binding.
