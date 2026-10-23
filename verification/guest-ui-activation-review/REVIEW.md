# Signed guest UI activation review

Independent reviewer lane: `guest_ui_activation_review`. Reviewed the accepted
design and the root activation integration at HEAD
`32725fa3ff464890f541d50addc824426f4e66e1` plus the uncommitted input hashes in
`read-receipt.json`. Only this verification directory was written. No commits,
pushes, production changes, device runs or GA claims.

Final status: **no unresolved substantive activation integration finding in this
reviewed scope**. The P2 below was reproduced on candidate2, repaired by root,
then independently verified on candidate4 in debug, release and TSan. Final
source and binary hashes are in `final-receipt.json`; this is a bounded review,
not a complete release qualification.

## Resolved finding: post-intent UI failure omits the reopen diagnostic

**P2, reproduced.** In the reviewed `CapabilityRecoveryStore.swift`, the new
UI-protocol failure branch at lines 589–596 commits
`ui_protocol_after_effects`, clears the active attempt, and sets only its private
`recoveryRequired` flag. `CapabilityRecoveryControl.publish` at lines 215–217
derives `report.requiresReopen` exclusively from `poisoned`. A successful
post-intent failure transaction therefore leaves the public recovery and
activation snapshots' `requiresReopen` fields false, even though the disposition
is `.recoveryRequired`. `CapabilityGuestUIDiagnostics.swift` lines 27 and 46 copy
that false value. The accepted UI behavior requires reopen after intent entry,
including uncertainty before actual native enable.

The bounded executable probe stages an independently signed fixture through
the real store and native validator, consumes it, establishes the UI startup
latch, enters the real durable effects-intent path, and records a typed UI
presentation failure. It asserts the closed disposition, durable diagnostic,
empty trap/quarantine histories, and reopen snapshot. The post-intent assertion
fails; the before-intent control passes. It does not enable native effects or
claim a VM execution or native presentation receipt.

Root corrected publication to use `poisoned || (guestUI && recoveryRequired)`
and republishes after setting the recovery flag. This keeps the UI requirement
sticky in the current owner, preserves capability-only diagnostic behavior,
and neither casts the UI failure to a bridge error nor poisons native state.

## Checks and limits

- Source inspection found the intended signals-lock → exchange-lock ordering.
  Stop writes release the exchange guard before publishing bridge/local detail;
  commit and intent entry inspect the same exchange under the signals lock.
  The typed UI branch does not increment deterministic trap counters.
- Signed UI validation is selected at download finish, startup selection,
  one-shot consumption, and concrete construction. The public facade checks
  the installed marker/startup triple before reservation or store work and
  exposes no arbitrary executable, document, export, host or milestone input.
- `feature_started` follows actual owned enable and store confirmation.
  `first_screen` is consumed only from the private exchange receipt, with
  milestone/health entry rechecking the stop latch.
- The executable close-race probe stalls MainActor before presentation binding,
  waits for observation registration, then closes the public facade. Close
  remains pending until MainActor resumes. Startup rejects, presentation retires,
  the created consumer's actual return is joined, and the reservation retires.
  This supports the late consumer-registration branch; it does not qualify all
  native view/display races or logical consumer-tail scenarios.
- Startup fallback drops the old helper frame before joining the observation
  and concrete retirement, then admits the next selection. No new production
  edits were made to force or test a fallback.
- Follow-up consumption inspection confirmed that the added asynchronous UI
  validation precedes one-shot selection consumption. The code rechecks cutoff,
  signed evidence, operation cancellation and shared stop before taking it.
  Rejection invalidates prepared authority and durably removes the pre-effect
  attempt; failed cleanup requires reopen. Validator retirement is cleared
  only after the worker frame returns. This portion is source review, not an
  added deterministic consume-validation cancellation test.
- Terminal accepted-event result retention and presentation-model/window
  implementation are separate reviewer/implementation lanes, deliberately not
  duplicated here.

## Executed candidate

The original probe links the immutable integration candidate2 debug dylib:
`49f32736921913ea4e5824ad27096ebe4733d3a08016f2f1195a84ea4be72c77`.
The one native archive is the selected `guest-ui-1adb25c-v2/host` archive:
`4d3b6dc36ea034d5604299752d560cbbc0615002b6b5ef4e5c25bbb3cb7c6120`.
Swift 6.4, arm64 macOS host. The receipt retains exact link/run commands and
input hashes. Final original probe result: **3 tests, 1 expected product-finding
failure, 0 unexpected failures**. The first harness attempt omitted startup
initialization and failed with local `busy`; its superseded log/receipt are
retained and are not product findings.

`read-receipt.json` records the exact inspected sources. Root's presentation
file had already changed since candidate2; the receipt states both hashes.
The reviewed activation/store/control/signals/facade/diagnostic hashes matched
the compiled candidate2 inputs. Candidate2's own 109-test result was read from
its receipt, not independently rerun here.

For a fresh compiled candidate, rerun these probes with:

```sh
python3 verification/guest-ui-activation-review/run.py --name candidate-4-debug-repro --mode debug --base-receipt verification/guest-ui-activation/candidate-4/receipt.json
```

The final review rerun used candidate4 receipt SHA-256
`14531af2ee4d0b9b9d47f129d963e6df797be772da5b735122c36db4666c0970`.
All **3 review tests passed in each of debug, release and TSan**, with zero
failures. Both stages preserved empty trap/quarantine histories; post-intent
now reports `requiresReopen = true`, before-intent reports false. The close
probe again joined the delayed binding and actual consumer return. The final
receipt verifies the reviewed production inputs still equal candidate4's
captured sources. The original failing candidate2 logs remain intact.

Physical iOS/Android checks, iOS simulator, visible native-window integration,
Swift guest compiler semantics, immutable external FieldLog consumption, store,
customer, operational and GA gates remain unqualified by this review.
