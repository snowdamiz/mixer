# Remote framing CI repair verification

The exact framing step and its receipt upload pass at commit
`05c1ebf0378fb479ba8595d71cde577f447d0025` in
[Engine CI run 40247799000](https://github.com/snowdamiz/mixer/actions/runs/40247799000).
The artifact confirms **44 methods passed, zero ignored and zero filtered**.
This accepts only the existing standalone fixture framing host scope. Both
`storedPrefixValidated` and `fullReplayAccepted` remain false. The binding
scope remains `mixer-product-plan.md`.

The workflow API records framing step 6 successful at `2026-10-26T00:10:40Z`
and its `always()` artifact upload step 7 successful at `00:10:41Z`.
Artifact `12619786212`, named
`analyzer-framing-host-05c1ebf0378fb479ba8595d71cde577f447d0025`, contains
78 exact nonhidden members in 118,243 compressed bytes. Its downloaded SHA-256
matches the GitHub API digest:
`a67d36f65202dea55318beedeb0ee873e7b79de1b32f2df859cfdea99d263c92`.
The ZIP is retained and inspected as data; no artifact code is imported,
compiled or executed locally.

All 38 selected sources match Git blobs at `05c1ebf` and are unchanged from
accepted baseline `4af8b7e1e451077aefc5ffbb213f84bf1b3d02e2`. The executed
collector matches the repaired source hash
`8e51065e0666c71260d947ad1168c87f036de0e392191555b3faba8f1d6cb837`.
The test-only appended source equals the unchanged analyzer, one LF and
unchanged private probes; it also matches frozen independent review run-2:
`7d49836d83db32854172a0f399aa1b4fe9409b724c80abb4b531d8a930eb7747`.
Listed, executed and recorded method names all match the exact frozen
44-method inventory. The nine command receipts and every stdout/stderr hash
match their retained artifact bytes.

The original PATH launcher is `/Users/runner/.cargo/bin/rustc`, resolving to
`/opt/homebrew/Cellar/rustup/1.29.0/bin/rustup-init`, with recorded shared-binary
hash `b54b2b2cdbf23377fd840d95be5fcea540b1f5c5529db0d0ee6afa96c861ff52`.
The successful sysroot query invokes the original launcher with
`RUSTUP_AUTO_INSTALL=0`. Version and both compile commands then invoke
`/Users/runner/.rustup/toolchains/stable-aarch64-apple-darwin/bin/rustc`.
Its actual verbose identity is Rust **1.98.1**, commit
`48a229ceaefd4985c50990b14116b6d856af0985`, LLVM 22.1.8,
`aarch64-apple-darwin`; remote Python is **3.14.7**. The compiler's recorded
executable hash is
`766eda9d8f53afd6fc7f27b3cd2e444dd22afacb5afa710a5625fc8e45b8c941`.
Executable hashes are remote receipt observations: binaries were not downloaded
and independently rehashed. Both direct library and test compilation retain
`-Dwarnings`.

The remote runner reports all 894 frozen framing members unchanged before and
after. The audit matches those recorded inventories to the exact commit's two
pinned seals; the published artifact independently supplies the selected
38-member source closure. All 17 historical sidecars and stream joins match
their captured bytes and remain `invalid`/failure 15. The output retains seven
footer refusals and ten footer-only observations without reclassification.
All nine surviving test-created files match their receipt hashes. The ownership
marker matches, and scratch cleanup records removal after children returned.

Evidence is in
`verification/swift-ordered-retention-analyzer-framing-ci-rustup-remote/`:
download/API/command/tool receipts, the exact ZIP, read-only audit source and
result, remote receipt data and expected Git source snapshots. The audit uses
Python 3.14.8 and GitHub CLI 2.102.0. It performs no local product run, native
runtime, capture, process discovery, product source change or publication.

Root tracks overall Engine CI separately; this packet qualifies only the
framing check and its upload. Linux remains unselected and unqualified. Semantic
replay, real adapters/custody, target/native/device/signing/store/customer,
operations, published-package FieldLog and GA gates remain withheld. The
historical 108-member packet and 186-member repair packet remain unchanged.
