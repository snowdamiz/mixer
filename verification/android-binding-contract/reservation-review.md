# Bounded independent review of the presentation reservation prerequisite

Reviewed the root-owned `CapabilityAttemptReservation.swift` and complete
`CapabilityAttemptReservationTests.swift` after root declared them frozen.
The exact hashes are recorded by `collect.py` in this directory's source manifest.
No implementation or test edit was made by this lane, and root's active runner
was not rerun or relabelled as this lane's execution.

No new defect was found under the existing trusted lifecycle-owner contract:

- `presentationIssued` makes issue once-only across retirement and fallback;
  `presentationID`, owner and retiring flag are independent of store/adapter.
- Presentation retirement moves the retained owner outside the reservation lock,
  leaves its retiring flag set while that reference is destroyed, and then checks
  all three independent IDs/retiring flags before outer pool release.
- Reservation deinit and abandoned presentation obligation quarantine a live or
  retiring presentation. A later reserve/retain against retired ID rejects.
- Tests hold each of the three kinds' destructor while the other two retire,
  check all-16 capacity, cover competing presentation admission, once-only issue,
  double retain/retire, and independent presentation abandonment.

The API remains a trusted internal assertion. `retainOwner` and final retirement
must be serialized by the future binding's setup/sole retirement owner, as for the
existing obligations. A duplicate concurrent `retire()` may return before the
first caller's destruction completes; its return must not be treated as a second
independent destruction receipt. The corrected contract assigns one final
retirement owner and requires every other resource-owning alias to be relinquished
before calling it. The reservation itself cannot prove those external aliases.

Scope: bounded source/test review only. Full activation linkage, binding, actual
Task joins, JNI/Android runtime, devices, release and GA gates remain pending.
