# Frozen encoder logical-work audit

This packet audits the unchanged encoder sealed by
`../swift-guarded-snapshot-encoder-implementation/seal.json` SHA256
`eadbe533d23459573ead21c7a9bac54ae929b98cdbc76dd47aebe34b5ceb2b1f`.
It does not select a debit, grant work, execute a selected writer, or qualify OTA,
device, operational or GA behavior. No active composition/review source is read.
The executable counter is an independent finite geometry/reference control,
not a replay of the frozen host/wrapper runner and not a runtime operation trace.

## Interface suitable for a future composition

All arithmetic below must itself be checked in the future consumer. An audit
credit is the logical action defined in `cost-convention.md`; it is not elapsed
time, CPU instructions, byte traffic, allocations or RSS. Original ExecutionWork
is the only candidate account; this packet neither changes its limit nor proves
the missing caller/writer/control work.

* `borrow_snapshot_v2` plus `into_cursor`: **14,221** credits, fixed, on success
  or any earlier error. No source/metadata record scan occurs here.
* One `next_block`: **26 + 68 I + 39 D + 139 W + Q**, where I is progress-loop
  entries, D is directory probes, W is `record_word` calls including a failing
  call, and Q is bytes explicitly copied before return/error. Each call has
  I <= 515, D <= 9I, W <= 513, Q <= 4096; a pre-call ceiling is **291,214**.
  It is indivisible with respect to a caller's stop observation. These bounds
  include partial progress/error branches; `emitted` changes only on success.
* Each opaque scalar/slice getter (`encoded_extent`, `emitted_extent`, block
  `bytes`, `offset`, `is_final`) costs at most **3** separately. Its caller's
  bindings, comparisons, stop checks, debits, writing and result moves are not
  part of this encoder interface.
* Terminal `next_block -> None` is bounded by the same fixed 26, with I=D=W=Q=0.
  An entire traversal includes at most B nonempty calls and one terminal call.
  No global ceiling permits retries after an encoder error or a completed None.

The `26 + 419 I + 139 W + Q` form is convenient when the caller knows only the
per-call ceilings. For a whole successful traversal, use the tighter cumulative
relations in `geometry.md`, rather than B times the worst-case 515 iterations.
The resulting **encoder-only** bound is

```
14221 + 26(B+1) + 68(1+C+W) + 39(C+sum((sid+1)*W_sid)) + 139W + E
```

where C counts source chunks and W_sid metadata word visits. This also bounds a
single non-retried failing prefix by truncating actual counters (or retaining
the full-stream upper bounds). It cannot cover repeated failed calls, native
write attempts, metadata/seek syscalls, work arithmetic, stop observers, scope
cleanup or their result/control propagation. No costs are invented for them.

## Finding about the old P/R proposal

The old P=16,384 and R formula were conditional proposed implementation
contracts, not a proof for this encoder. Its 64N rationale says every Buffer
element is visited once. In the frozen body, `record_word` reloads, validates and
rebuilds the entire record for **each encoded word**. An import record does this
five times, plus a possible split-word revisit. Each metadata iteration also
searches up to nine directories. `results.json` retains a finite witness and
reports the old proposed P/R separately from this encoder-only bound.

That invalidates the old once-per-record explanation. It does **not** alone prove
that the numerical whole R inequality fails: the 4E/16L/fixed terms might cover
some repeated actions, and writer/control work is unimplemented here. This
audit does not move work between terms to assert either total inequality.
P is not reusable encoder allowance; it was intended for separate planning.

`cost-ledger.json` contains expanded branch/helper counts and source locations;
`cost-convention.md` defines all actions and `geometry.md` proves the counters.
Run `python3 verification/swift-guarded-snapshot-encoder-work-audit/audit.py`
from the repository root to verify input custody, ledger arithmetic and finite
controls. After sealing, this command verifies the packet and deterministic
outputs without writing it. `command-receipt.json` records the command, Python version, current
repository revision, immutable 144-member source digest, output and scope.

The earlier coefficients sent during coordination are retained in
`superseded-proposals.json`. Their omitted carrier/propagation actions were
corrected before this interface was frozen. No earlier coefficient is selected.
The first sealed replay's tuple/list comparison error and its complete small
audit packet are retained under `attempt-history/002-first-seal`; the corrected
verifier compares normalized JSON and preserves the same work coefficients.

Native simulator/emulator/device/UI/capture activity remains paused. This packet
starts none. Mac host reference controls are not native or physical receipts.
No canonical source, metadata, index, Git commit/push, active lane or immutable
input is modified by this audit.
