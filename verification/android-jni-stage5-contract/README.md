# Stage 5 contract proposal evidence

The deliverable is `docs/android-jni-stage5-seams.md`, the exact declaration
inventory in `api.json`, and 50 **pending** named implementation cases in
`acceptance-matrix.json`. No product/native implementation was made. Root must
review/accept the seams and assign ownership before any implementation.

`input-lock.json` freezes content hashes against accepted host checkpoint
`61c5c8b2e0af59ea98d3ff85f208ad97df069411`, separately identifies the updated
product-plan §8.3 design-parity section, and binds proposal/API/spec-reference
inputs. Its content digest is independent of a concurrently moving HEAD.
`spec-inputs.json` records seven official documentation URLs, fetched body hashes
and independently written requirements summaries; downloaded bodies are not
vendored. This is specification provenance, not platform qualification.

Run from the repository root:

```sh
python3 verification/android-jni-stage5-contract/collect.py
python3 -O verification/android-jni-stage5-contract/collect.py
python3 verification/android-jni-stage5-contract/collect.py --plan
python3 -m unittest discover -s verification/android-jni-stage5-contract -p 'test_*.py'
```

The collector verifies inputs, immutable bridge declaration consistency and
complete pending case inventory. `--plan` prints future runner argv without
executing them. A runner path in this proposal is not an installed implementation.
The tests force audit failure for descriptor/ABI/input/bounds/inventory drift,
scope promotion or a device action. They are collector tests, not JNI tests.
Optimized Python must make the same fail-closed decisions; no `assert` is used
for collector validation. Optional `--check-network-specs` re-fetches official
pages and fails on drift rather than changing the lock.

The native authority prerequisite 5N and shared appearance prerequisite 5T require
separate explicit root acceptance/coordination. Existing host receipts have no
conversion to native types. SDK packet generation must consume authoritative
snapshot identities, independently bound custom-limit snapshots and preserve
authored UTF-8. Current canonical Swift String identity collisions remain unchanged;
JNI additionally rejects byte-different equivalent aliases before routing.

S4-21 dynamic stale JNI delivery remains pending until the real native backend,
JNI weak slots, entry functions and actual Android Looper execute. S4-29 optimized
Release injection is separately pending. Draw marker mechanics require a bounded
real-Window experiment before observation code; it issues no health receipt.
Full signed core/Prepared/factory/VM/KV/coordinator integration is stage 6.

Phones remain disconnected: no discovery, physical runs or reconnection requests.
Physical side-by-side iOS/Android design parity, published separate-repository
immutable FieldLog packages, signing/store/customer/operational and GA gates are
pending. There is no full dynamic32, native, release or GA pass in these artifacts.
