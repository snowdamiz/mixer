# Independent frozen controller V2 review

Read `docs/hosted-worker-controller-v2-independent-review.md` and `receipt.json`.
`handoff.json` gives final SHA-256 bindings. This packet recommends only the exact
bounded local development slice; root owns integration. No GA/live acceptance.

`verify_and_copy.py` first verifies the supplied receipt and every explicit
source/archive/artifact/dependency/runtime binding, then creates an owned copy.
No candidate/dependency code executes before those checks. `run_review.py` runs
one copied command, retains its stdout/stderr, binds source/executable identities,
and removes its exact scratch/storage. It never runs producer collectors in place.

The actual command sequence, from the workspace root, was:

```
python3 verification/hosted-worker-controller-v2-independent-review/verify_and_copy.py
python3 verification/hosted-worker-controller-v2-independent-review/run_review.py baseline baseline
python3 verification/hosted-worker-controller-v2-independent-review/run_review.py build build
python3 verification/hosted-worker-controller-v2-independent-review/run_review.py producer producer
python3 verification/hosted-worker-controller-v2-independent-review/run_review.py regressions regressions
python3 verification/hosted-worker-controller-v2-independent-review/run_review.py focused focused
python3 verification/hosted-worker-controller-v2-independent-review/run_review.py noncooperative noncooperative
python3 verification/hosted-worker-controller-v2-independent-review/run_review.py independent independent
python3 verification/hosted-worker-controller-v2-independent-review/run_review.py closure closure
python3 verification/hosted-worker-controller-v2-independent-review/run_review.py inventory inventory
python3 verification/hosted-worker-controller-v2-independent-review/run_review.py ast ast
python3 verification/hosted-worker-controller-v2-independent-review/run_review.py independent-final independent
python3 verification/hosted-worker-controller-v2-independent-review/finish.py
```

Baseline exit 1 is intentional: its original three assertions fail unchanged.
All final V2 groups and 17 distinct independent groups pass. The second independent
run adds a migration-overflow rollback control; both exact executed sources and
all per-run runner versions remain retained. Do not silently deduplicate their
cleanup or process evidence into unique test counts.

`frozen-inputs.tar.gz` contains the full verified 356-file union of producer
artifacts, 172-input closure, receipt and source/archive manifests, preserving
workspace-relative paths under `frozen/`. `frozen-input-manifest.json` binds those
members. The expanded copy was disposable and is removed at completion.
`review-fixtures.tar.gz` retains every consulted instruction/document and executed
review/fixture source, per-run bindings, source snapshots and compiled-output
manifests. `review-fixture-manifest.json` binds its members. Installed dependency
and runtime executable bytes are hash-bound rather than redistributed; only their
owned scratch copies were executed and removed. Node itself is the pinned,
verified existing tool executable. Jason bytes are verified but not executed.

Scripts retain exact original paths as audit evidence and refuse existing run
names. A fresh repetition requires a newly owned output directory/scratch,
recorded path relocation and the same pinned dependency bindings; extract archived
inputs only into that new owned tree. Never replay into either frozen producer
packet or rewrite historical outputs. An installation, if needed elsewhere, must
use the existing lock and `npm ci --ignore-scripts --no-audit --no-fund`, with its
own receipt; this review performed none.
