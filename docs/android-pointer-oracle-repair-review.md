# Independent candidate 5 pointer oracle repair review

**Native dispatch remains held: two oracle findings reproduce.** Candidate 5's
source, archive, APK packaging and runner bindings pass this host review. The five
earlier repair findings now reject, but the repaired oracle accepts five further
impossible synthetic observations. This review ran no adb, emulator, simulator,
physical-device, app or UI command and changed no producer, tracker or Git state.

## Findings

**F06 — Activity delivery is not correlated with its worker injection interval
(blocking for evidence acceptance).** In `oracle.py:109–123`, worker and Activity
intervals are checked independently inside the action interval. Neither is joined
to the other by the delivered event's sealed `eventTime`. The oracle accepts all
three independent P01 controls: both Activity callbacks one millisecond before
`workerBefore`; callbacks one millisecond before the event's own `eventTime`; and
callbacks after the matching `workerAfter`. Each preserves action bounds, event
payloads, state, revision acknowledgements, export hashes and nonoverlapping
Activity intervals. These receipts still return the oracle's passed status.

The private source records `workerBefore` before `sendPointerSync` and
`workerAfter` after its return (`CoordinatorJoinInstrumentation.java:263–270`).
The Activity observer records uptime immediately before and after its single
superclass dispatch (`CoordinatorJoinActivity.java:29–47` and instrumentation
lines 173–183). Android documents that `sendPointerSync` waits for the recipient
to finish handling the event. Thus these three observations contradict the frozen
source and platform contract. They are synthesized parser acceptances, not
observed Android behavior. [Official Instrumentation contract](https://developer.android.com/reference/android/app/Instrumentation#sendPointerSync(android.view.MotionEvent)).

The minimal safe correction is to index the already validated worker records by
the sealed current event time and require, for every Activity entry/exit pair:

```text
matching.workerBefore <= activity.entryUptime
    <= activity.exitUptime <= matching.workerAfter
event.eventTime <= activity.entryUptime
```

Use inclusive comparisons because separate monotonic uptime reads may land in
the same millisecond. The existing per-action, per-worker and per-Activity order
checks remain necessary. For a coalesced MOVE, match the **current** MOVE to its
worker interval; historical MOVE samples may correspond to earlier sends and
must not be forced into the current worker interval. Preserve their sealed
time/coordinate/pressure and strict cross-delivery sample checks. The positive
coalesced control still has a valid current-worker interval and seven earlier
historical sample times.

**F07 — non-MOVE history can substitute for all delivered MOVEs (blocking for
evidence acceptance).** `oracle.py:125–133` checks each historical sample's sealed
MOVE time, coordinate and pressure, but omits a check on the containing event's
action. Removing all eight P03 Activity MOVE pairs and putting those samples in
the terminal UP's history still passes with 124 requested events and only 116
Activity entries. The same substitution passes on P05's terminal CANCEL. Both
controls retain correct final coordinates and the real-history raw/local offset.
The final MOVE endpoint requirement is satisfied by an impossible terminal
history array. Android specifies a zero history size for every action other than
MOVE. The passive observer obtains this array directly from
`MotionEvent.getHistorySize()`; it does not author or synthesize it
(`CoordinatorJoinInstrumentation.java:166–170`).
[Official MotionEvent history contract](https://developer.android.com/reference/android/view/MotionEvent#getHistorySize()).

Require `event.history` to be empty whenever the containing event is not MOVE,
and continue requiring each actual historical sample to be a sealed MOVE. Apply
the same semantics to requested worker events; these frozen worker requests
contain no batching. Preserve genuine history on MOVE and the dropped
intermediate-delivery positive control.

## Executed evidence

The exact command `python3 -B
verification/android-pointer-oracle-repair-review/review.py` completed in
`host-review-2/`. Its [receipt](../verification/android-pointer-oracle-repair-review/host-review-2/receipt.json)
records command arguments, UTC times, tool versions/hashes, repository revision
and tree context, frozen artifact identities and empty-holder/device/inode
scratch cleanup. Python 3.14.8 and the bound OpenJDK 25 ran the host checks.

- All 42 producer tests passed. Five original finding classes rejected again in
  independent mutations (including obscured flags 1, 2 and 3).
- Nineteen independent probes ran: four positives accepted, ten intended
  negatives rejected, and five intended negatives unexpectedly accepted across
  F06/F07. [Exact results](../verification/android-pointer-oracle-repair-review/host-review-2/adversarial-results.json)
  and complete, hash-bound failing fixtures are retained under `reproductions/`.
- Baseline injection/delivery is 124/124; genuine MOVE batching is 124/117;
  retained final MOVE with dropped intermediates is 124/117. Equal millisecond
  worker/Activity boundaries pass. The two impossible terminal-history controls
  are 124/116. Offset tampering, duplicate history times and overlapping Activity
  intervals reject.
- The producer packet replay passed before and after review with 284 host
  bindings; the earlier 507 producer and 42 independent-review files remain
  immutable. Only the designated runtime subtree is excluded, nested receipt
  files remain bound, invalid/reused attempt paths reject, and symlinks reject
  even within excluded runtime evidence.

The first review attempt is retained as `host-review-1/`: its 42 tests and 19
probes ran, but the shell apksigner launcher could not find Java without
`JAVA_HOME`. This is a reviewer environment failure. `host-review-2/` explicitly
sets the bound JDK path; official apksigner and zipalign then pass. Both attempts'
scratch directories were checked for empty open holders and matching device/inode
before removal. No failed attempt was discarded.

## Source, artifact and wrapper review

The [independent artifact receipt](../verification/android-pointer-oracle-repair-review/host-review-2/independent-artifact-review.json)
checks all 179 archive members by exact name/type/size/hash, all 105 frozen source
inputs, and the unchanged 88 live native/SDK inputs. Relative to candidate 4,
only private Instrumentation source changed; only its class, full DEX and APK
changed. All 155 production class artifacts and 18 native libraries are
unchanged. Candidate 5's already completed fresh Javac/four-class/full-DEX replay
is recursively bound by the packet; this review did not repeat historical
compilations. Local ZIP/ELF validation and official `zipalign -c -P 16 -v 4`
and `apksigner verify --verbose --print-certs` pass for the exact retained APK.
The expected v3 signing certificate is
`2efe3ce0e8808d1a8fe3fc0b276030bdf140e046a19b2ab5bf8a64278bc1346b`.

The concrete runner first revalidates source closure, live native/SDK bytes,
archive/extracted APK identity, local packaging, official alignment and exact
signing certificate, before its first adb/emulator tool command. Immediately
before installation it repeats source/APK, local packaging, official alignment
and signing checks. Its selected concrete source is reproduced by exact
single-site transformation and its hash matches the designated runner contract.
The source retains bounded output/export budgets, explicit runtime dispatch,
serial targeting, owned process cleanup and recursive runtime sealing. After
successful extraction cleanup removes `.build`, its runtime seal excludes its
own exact root seal while retaining nested receipts. Failed extraction cleanup
remains a failed runtime receipt; extraction scratch is excluded from that seal.
The runtime wrapper itself was inspected and loaded without calling its native
entry point.

The passive Activity still has exactly one superclass dispatch and preserves its
Boolean result and exception. Gesture input is worker `sendPointerSync`, with no
direct pointer callback, `performClick` or checked-change listener invocation.
Ordinary setup dispatches remain separately declared. Geometry, schedules,
assertions, production inputs and dependencies were not changed in this review.

## Frozen identities and disposition

| Binding | SHA-256 |
| --- | --- |
| Host packet seal | `275e733bbc31262c12bf65402fc12e110a43c9f5d14cb41ad157be7a5d755fd5` |
| Packet | `d9511187a6466b9d3253ccfdfa971aa95fb10cdcfdd73d058c1e2e28bf22c98b` |
| APK | `57e82e4e98cdc61581c0639603ec6efa500a66d8d2754f6b47ece89c8165d714` |
| Archive | `847de52459dbe90b8fd5abbe186aaf2f936cce38981cbc28ce86b36bcdc9249b` |
| 105-input source closure | `9082e2de1327bd0784d752db5dfbe4484751d565b3410e01e78664321467f5ce` |
| Selected runner contract 4 | `a757865ecd435422d3cc1da98d4a0669d34ab7a5b0d14c3ed6ed97265541b63f` |
| Concrete runner | `bd7cd16883a831aac29fa13d162eabf6fae78c88c6b523919e4d9b38c0103b31` |
| Wrapper | `3aa02d1b8469ca3f14c355738f16ed774a2c0431007df9f03474b87c99a188d5` |
| Oracle | `969dc86860e5b1bbce4941645eef68694401fc9839debf7b137c4dcaf9181dcf` |

Repair F06/F07 in a separate preserved packet using the identical candidate 5
APK, source closure, geometry and schedules. Root should independently accept
that corrected oracle and runner before any native dispatch. This review grants
no native, physical, release, customer, operational or GA acceptance; the
disconnected physical-phone matrix and broader product gates remain pending.
