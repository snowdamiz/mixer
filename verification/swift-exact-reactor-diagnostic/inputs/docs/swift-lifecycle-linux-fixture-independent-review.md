# Swift lifecycle Linux fixture repair: independent review

Reviewer: `/root/swift_lifecycle_linux_fixture_review`. Root owns integration, push, hosted CI, and accountable acceptance. Recommendation: accept the exact test-only repair for development, subject to root review. There are no blocking findings.

The reviewed source context is `ccd8e4c3d96f96876a1339a51dc4297f4175d4fc`; the exact 132-file candidate closure is `6d4b1deed091d6c0f0a2ae0c101c98afbd0e27fdc3c2b2992a999e08565a3fe8`. Producer seal `3c5271daec4cfcb0333130b1492c07641263ef2a79a2fe7fddb6bb4fdbdad38d` and all 208 internal members plus its document were independently hashed. The live source matched the final producer candidate. The accepted historical remaining-matrix packet was read only.

The source delta changes only `control.rs` and `lifecycle_tests.rs`. Removing the exact new expiry method from the existing `#[cfg(test)]` implementation restores the baseline control source byte for byte. The other 130 input files, production request path, deadline carry, budgets, accounting, and layouts match the accepted baseline. The lifecycle module remains unit-test-only, and all 49 identities are preserved.

The original Linux CI output reports 388 passes and three construction failures at the 200 ms deadline, with 50,738,224 bytes of state reservation, 38,319,741 execution work, and zero instructions. The repair uses ordinary construction allowances, then moves only the prepared test control's deadline to the current instant; it does not wait for expiration. The helper requires a healthy, unexpired fixture and preserves origin, budgets, counters, and failure state. SL01 proves ordinary expired misuse is nonexecuting. SL10 proves the real carried WASI deadline equals the common start plus 20 seconds and precedes the original run deadline before injection. SL14 captures the deadline before Initialize, proves the successful call does not reset it, then proves the failed Corpus call preserves the expired deadline and executes no additional instructions or cache/execution work.

Independent execution used macOS 27.0.1 on arm64, Rust/Cargo 1.99.0, a fresh exact source copy, and one owned Cargo target. Every command records its arguments, source manifest, tool paths/hashes/versions, environment, outputs, timing, and process cleanup in `verification/swift-lifecycle-linux-fixture-independent-review/commands/`.

| Check | Observed result |
| --- | --- |
| Exact final candidate, all-features Debug, three affected identities | 3 passed, 0 failed, 0 ignored; 388 filtered |
| Review-only mutation disabling expiry while retaining the same test cases | All 3 failed at the actual failed-operation expectation, as required |
| Exact restored candidate, ordinary all-features `cargo check --lib --locked --offline` | Passed |
| Review-only ordinary same-module caller invoking the helper | Failed solely with E0599: method `test_expire_deadline` not found |
| Sealed producer evidence and read-only verifier | Four configurations, 49 identities each: 196 passes; four production checks passed |

The two negative controls changed only the review-owned copy; exact final source restoration was verified after each. Compressed positive and negative test binaries, exact mutations, manifests, and outputs remain in the review packet. No processes held the owned source or target before removal; both were removed, recovering 84,019,582 bytes. Other projects' processes and simulator data were untouched.

The producer's broad rustfmt failure is retained as historical evidence, with a passing check of the changed lifecycle file and exact added helper. Two existing `dropping_copy_types` warnings remain in unchanged tests. This review did not rerun the repaired Linux job or broad library matrices, the full 53 MB reactor, native/device/emulator execution, compiler qualification, external published FieldLog packages, signing, store, customer, operational, accounting, full SL-row, release, or GA gates. Phones remain deferred. One initial read-only `git status` was issued during discovery; no Git mutation, commit, push, tracker edit, or live source edit occurred.

Read-only packet verification: `python3 verification/swift-lifecycle-linux-fixture-independent-review/verify.py`.
