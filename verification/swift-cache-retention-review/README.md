# Independent finite Swift cache-retention review

The decision is `result-summary.json`; `../../docs/swift-cache-retention-review.md`
describes the finite acceptance and its limits. The seal binds every retained
probe, command, source manifest, failure correction, audit and cleanup receipt.

`python3 verify.py` performs read-only integrity and acceptance checks. It invokes
the producer's read-only verifier and does not extract sources or run a guest.
The accepted producer's immutable archives plus the independently retained probe
source reproduce the reviewed closure. Review-owned extraction/build/tmp paths
were retired and are ignored. Historical failed reviewer expectations and the
generic API typo remain separately bound; final passing commands are
`commands/independent-swift-corrected`, `commands/independent-generic-corrected`
and `commands/independent-ties`.

This review accepts only a finite correctness/accounting prerequisite. Root must
separately select any one isolated same-budget diagnostic; actual target benefit,
live integration, four complete regression contexts, native parity, physical
phones, signing, published-package FieldLog consumption and GA remain unaccepted.
