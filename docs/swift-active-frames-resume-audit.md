# Private active-frame resume audit

This lane audits the saved host packet for the exact 119-file VM tree
`4f16367b0985d924564b80b00b556f799cb42e3426a9b08fd8aca53b2a0015a4`.
Root owns actual source acceptance and delivery. This audit does not advance a
GA gate or authorize public invocation, native execution or release.

Run `python3 verification/swift-active-frames-resume-audit/audit.py` from the
repository. It records current HEAD, tool versions, commands, stdout/stderr
digests, exact input hashes and its scoped decision in a fresh `results/` receipt.
It invokes both unchanged saved-evidence verifiers, including worktree equality,
and independently checks the full current VM source closure and command lineage.
It does not compile or execute any retained binary.

The bounded manual source review followed `original_owners`, frame prepare and
cleanup reacquisition, entry/pin acquisition and synchronous rollback, finish,
drain, completion, the construction-ticket leaf, the zero-frame value barrier and
consuming cleanup. Entry checks activity before capturing fresh lengths; rollback
debits are limited to this attempt. Failed actual releases retain their original
pins at indexed positions, and a processed suffix is retried only after explicit
cleanup reacquisition. The unpublished guard stays independent. Sticky live debt
and nested/outer restore debt prevent completion. Fixed caller storage ends before
the construction reservation shrinks. The original borrowed-cache release checks
the actual record and live-pin decrement before changing slots or usage, and
returns the same pin on rejection. No additional blocker was found in this
bounded recheck; this does not replace root's independent source decision.

The final packet has 229 producer command records: 204 imported and 25 fresh.
Final candidate runtime origins are `20261024T050048420640Z` on `4f16367b`;
baseline runtime origins are `20261024T045149763486Z` on `4df46815`.
The historical `f10e1fef` candidate does not qualify the final source. All source,
timestamps, argv and output hashes remain attached to the original executions.

Eight producer layouts and two independent exact-field layouts establish the
saved logical bounds. Production permanent/header/active/full-frame bytes are
1,086,648 / 1,378,536 / 929,872 / 1,049,448. Unit bounds are 1,945,656 /
2,238,504 / 1,505,296 / 1,624,872. The value component is 119,576 bytes and State
424 bytes. Production/unit field counts are 9,345/17,865. These are explicit
logical ownership bounds, not arbitrary optimized machine-stack measurements.

Broad Clippy remains a failure with the same 26 source-associated baseline
diagnostic identities. AF15's caller-capacity rejection is a derived defensive
fault injection, not a naturally reachable valid-owner failure. Neither limitation
is hidden by the passing host evidence. The independent review closed R01–R08;
its exact decision, review seal and document are bound to the producer packet.

Computer use, screen capture, UI automation and simulator/emulator/device runtime
activity remain paused. Native and physical-phone checks, public invocation and
dispatch, signed immutable packages consumed by separate-repository FieldLog,
store/customer operation and GA acceptance remain pending. No product source,
previous evidence, tracker, commit or push is changed by this lane.

Delivery must preserve the existing producer/reviewer seals byte-for-byte. Their
path sets include historical attempts and binaries, so a final-only subset cannot
claim to run the unchanged full-seal verifiers without restoring the omitted
files. Deliver both unchanged sealed packets with an exact allowlist. The observed
packets contain 1,985 files / 676,638,725 bytes; whole-file content deduplication
would yield 435 blobs / 432,001,766 bytes. Their 44 tar/gzip archives contain 31
unique outer archives. Unique outer archives contain 2,972 regular members /
836,675,983 bytes, including 415,318,191 bytes of repeated member content. These
figures describe possible compression savings; no custom pack or materializer is
used. Every individual file is below 100 MiB. Root measures Git transfer/object
size and coordinates delivery. `measure_delivery.py` records the reproducible
inventory in the audit command log. No evidence is deleted.

An initial audit attempt could not resolve `rustc` on the current PATH before it
reached either verifier. That failed tooling receipt remains historical. The final
audit uses Python and Git only, binds the saved Rust/Cargo versions and correctly
makes no claim about a current compiler installation or new compilation.
