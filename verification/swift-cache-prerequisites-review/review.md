# Independent Swift cache prerequisite review

Scoped acceptance, 2026-10-23. No unresolved product finding in the nine frozen
prerequisite files listed in `freeze.json`. This accepts the descriptor and
control/WASI observation prerequisites only. It does not accept or implement the
cache v2 contract, an executor, a target runner, a release, or any GA gate.

The review used binding `mixer-product-plan.md`, `AGENTS.md`, the proposed Swift
execution stage design, cache stage contract revision 2, and the two prerequisite
contracts. The actual descriptor canonical receipt is
`verification/swift-execution-descriptors/2026-10-23-host-v2/receipt.json`.
The requested `canonical2026-10-23-host-v2` spelling was a dispatch typo, resolved
with root. No producer receipt, historical attempt, or product file was edited.

## Frozen source and receipt audit

The independent source is immutable baseline
`bd8a8967d32692765de0d4dd14f5d88b7d5009ff` with exactly the nine requested
overlays, containing 417 VM files. `frozen-source-manifest.json` has SHA-256
`9e34639aa3e4060dc7a952ef5925b8df48bccfd91c88e7a804eeec8acab1fe80`.
All nine final live overlay hashes still match that frozen input.
Concurrent Android/website work is excluded. The source copies and build outputs
are under this review directory's ignored `.build/`; no root build directory or
producer sealer was used.

Every one of the descriptor producer's 136 stdout/stderr logs and the control
producer's 8 complete logs matches its receipt hash. The producer overlays match
the independent frozen input exactly. Existing failed attempts were preserved;
the isolated-1 category-versus-combined expectation error remains historical,
while isolated-2 uses an input that isolates the combined limit.

`source-audit.json` records 19 exact comparisons against baseline. The literal
stored RuntimeControl, ReservationTicket, AdoptedProof, AccountedWasi, Swift proof,
legacy proof, metadata and public SegmentView definitions are unchanged. The
entire old `ValidatedSpans` descriptor implementation and complete actual
AccountedWasi dispatch body are unchanged. Frozen metadata/validator/cache/
decoder/executor, standalone WASI, Cargo manifests/lock and library wiring files
are unchanged. These source comparisons supplement executable tests; they are
not release authorization.

## Source conclusions

- Absolute function lookup subtracts the sealed 34 imports with checked
  subtraction, rejects imported and absent indices, and borrows the original
  defined-body span. Signature lookup follows the metadata's separate absolute
  import/definition mapping; type lookup uses type indices.
- Body, global initializer, data and element cursors use original sealed spans.
  Initializers include their ending `end`; empty payloads retain their exact
  offsets. Segment order, overlaps and encoded element LEB bytes are preserved.
  Effective memory/table maxima are the stored 768/46,713 values; declaration
  maxima and the separate 65,536 policy table ceiling remain distinct.
- New accessors/types remain crate-private immutable borrows. They allocate and
  mutate nothing. No public authority, mutable view, source constructor, legacy
  conversion, new policy variant or dependency is introduced. Existing public
  proof and view layouts remain exact.
- Observed methods carry the supplied observation through checks, inventory,
  category/combined arithmetic, entry-size, construction, capacity, work, live
  count and cleanup faults. The old methods retain their signatures and delegate
  `None`; order and atomic reservation commits remain exact.
- `check_adopted_owner` checks both original sealed tickets by borrow. It neither
  consumes proof authority nor performs admission/work/cancellation checks.
  `reservation_owner_matches` tests only exact nonzero identity; the subsequent
  full ownership/accounting check remains necessary.
- `checked_usage` reads the actual header. Missing header and foreign owner
  originate an unattributed `None` failure. Same-owner accounting faults retain
  actual context counters; success returns those counters. Valid pairing remains
  usable for terminal cleanup. A previously latched first failure stays immutable.
- Cleanup destroys actual owned storage before refund, attempts both original
  proof-ticket refunds even after the first fails, and conservatively retains
  rejected charges. The prerequisite does not supply the future cache consuming
  rejection or cleanup-tail implementation; those remain contract requirements.

## Independent executable results

`receipt.json` retains 13 commands with complete stdout/stderr, hashes, paths,
versions, expected exit codes and source stability checks. Toolchain is
Rust/Cargo 1.99.0 on `aarch64-apple-darwin` with LLVM 23.1.1; exact verbose version
output is retained.

| Check | Observed result |
| --- | --- |
| Original frozen combined all-feature library, debug | 103 passed, 0 failed/ignored |
| Original frozen combined all-feature library, release | 103 passed, 0 failed/ignored |
| Seven independently authored reviewer probes, debug and release | 7 passed per mode, 0 failed/ignored |
| Public frozen span/cache/standalone-WASI and allocator regressions | 37 passed, 0 failed/ignored |
| Default-feature library | 7 passed, 0 failed/ignored |
| All-feature library/binary clippy | Passed with warnings denied |
| External public positive compile control | Passed |
| External private control/ticket/adopted and accounted-WASI imports | Both failed as expected with E0603 |

The seven reviewer probes cover both original tickets and all three borrowed
ledger-underflow branches; zero identities including a zero control; valid
borrowed checks after terminalization/cancellation/deadline expiry; six
construction cleanup invariant branches and actual supplied storage destruction;
the second proof refund after first source-owner failure with actual proof
allocation deallocations; nine old-method/`None` specialization comparisons;
missing actual WASI header with `None` attribution and unchanged storage; and
repeated actual context observation under sticky/cancelled/expired control with
no work, admission, host call or allocation effect. Private corruption probes are
explicit internal invariant tests and restore recoverable owners before cleanup.
The nonzero observation sentinels in control-only tests check propagation only;
actual-context tests perform real adapter dispatch before sampling counters.

`control_probes.rs` and `wasi_probes.rs` are independent reviewer code. Their only
source-copy changes are two appended `include!` statements and two new test files,
listed exactly in `probe_only_differences`. The complete source including probes
is retained in `probe-source.tar.gz`, bound by `probe-source-manifest.json`.
Extract it into a fresh directory, point `CARGO_TARGET_DIR` outside it, and run
the receipt's cargo arguments with `--manifest-path vm/Cargo.toml` from that
directory to reproduce the tests. `run.py` and `audit.py` retain the collectors.

## Limits and remaining gates

No 53,777,114-byte reactor was instantiated, initialized or invoked. This review
adds no cache/executor evidence or permission for such an attempt. Cache contract
v2's concrete layouts, transient bounds, implementation, 18 required named
synthetic tests and later source-bound root acceptance remain pending. No new
physical-device discovery or runs occurred; disconnected-phone checks remain
pending. These host allocator observations concern requested operations and
logical storage accounting, not RSS, compiler stack size or allocator overhead.
Published separate-repository FieldLog consumption, mobile/store, customer,
operational, performance and GA gates remain unqualified. Root owns integration,
status/work-graph changes, commits, pushes and publication decisions.
