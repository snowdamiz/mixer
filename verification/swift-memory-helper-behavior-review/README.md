# Independent Swift Load/Store review: request changes

The behavior selections pass. MR01 blocks accounting acceptance: both unit
configurations omit the actual pinned caller's promoted LocalKey backing and
returned reference, requiring eight fields/64 named unit bytes. See
`docs/swift-memory-helper-behavior-review.md` for the finding and scope.

Check the frozen packet offline without Python cache writes:

```text
python3 -B verification/swift-memory-helper-behavior-review/verify.py --live-baseline
```

A successful checker means the evidence and recorded request-changes finding are
consistent. It does not mean accounting, root, integration, release or GA
acceptance. All authoritative engine archives remain in the immutable producer
packet and are bound by hashes. The two independently modified test-source
archives live here. `session.json` records an already removed owned scratch.

The review reproduces exact MM01–16 in four configurations, prior regressions,
six independent adversarial selections in four configurations, four actual MIR
configurations, 16 paired layouts, 39 expanded Frozen methods, separate concrete
baseline/candidate Frozen parity and original Frozen integration suites. No live
source, dependency, tracker, commit, push, mobile native runtime, UI runtime or
other project process was modified. Failed reviewer attempts remain evidence,
never qualifying passes. No build command needs to be repeated for this review.
