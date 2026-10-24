# Bounded private Swift Load/Store behavior candidate

Fresh independent review and root acceptance are pending. No live VM file,
tracker, dependency, native process, Git commit or push is part of this lane.
See `docs/swift-memory-helper-behavior.md` for scope and limitations.

Run the frozen checker without creating Python caches:

```text
python3 -B verification/swift-memory-helper-behavior/verify.py --live-baseline
```

The source archives are authoritative; the scratch path in `session.json` is
historical and is removed after archiving. `receipt.json` binds all packet files,
command/source/output hashes, exact source archives and executable hashes.
`seal.json` binds the receipt. Reproduction scripts need a fresh owned scratch
with the archived baseline/candidate extracted under `baseline/vm` and
`candidate/vm`, plus an updated local session file in an unsealed copy. Never
modify a frozen packet to run a review.

Only `final2-*` and `layout-binary-*` commands qualify the final source. Other
attempts are historical and do not supply passes. The three failed attempts have
source archives replayed exactly against their recorded manifests. Historical
successful candidates and their preliminary matrices/layouts are retained.

`matrix-results.json` requires all sixteen frozen test names in all four
configurations. Its harness fixture count is supplemented by the one real
foreign-header owner in MM07; MM09 already counts both original owners per case.
The fixture/attempt counters are conservative finite harness bounds, not a full
dispatcher. Both before-charge and after-charge caller cancellation have explicit
output observations. All synchronous warmed allocation observations are zero.

Swift-only MM14 records Frozen feature absence. Its complete claim requires the
separate actual `final2-frozen-*` all-feature baseline/candidate Debug/Release
receipts. Their 28 finite fixtures per execution compare actual result/bytes/
trap/work/fuel/cache/allocation observations, and the original Frozen integration
suite also executes on each source/profile. A feature guard supplies no inner
execution evidence by itself.

Accounting is logical named-object accounting, not physical stack or RSS. The
original absent-cursor Cleanup diagnostic and unreconciled debt remain observable;
G08 is pending. Swift bulk memory/growth, full dispatch, Ready/public invocation,
native/physical/UI/full-target, published separate-repository FieldLog and all
release/GA qualification remain pending.
