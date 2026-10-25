# Exact full Swift reactor after grouped-index reservation: result

Root selected one unchanged host diagnostic at commit
`4a28261b333c28b4fce386f370a19b93e735c8d2`, exact 132-file VM closure `3ffa1055e462be74c10ee9830bf891bbd196a896dfc7a66dc6befe2a6d9bb70f`.
Its selection SHA-256 is `28465c0768a098eb34949beaebd6848ea9c4ee6c5690f6a17fce8b87357d674e`. The original 53,777,114-byte module,
original harness/workload, 86-ticket limit, 64 residents and all other budgets,
hooks, counters and cancellation contracts remained unchanged. The fresh
4,746,352-byte executable SHA-256 is `c02fbaf29353ddb91c3d2e59516144012f229ab783e66e73b6e13599db6b286e`. Source-freeze context
`be472ce6424a691de5673e3438d2768264827d23` remains distinct from root's later commit.
The prepared packet and historical preparation document remain frozen.

The sole guest attempt failed in Corpus 1: `Cache / WorkExhausted /
swift_run_work / CacheWork`, attempted 64,000,001 against limit 64,000,000,
function 3416, byte offset 1077688. It had charged 64,000,000 cache work and
15,753,076 instructions, with 85 live and 86 peak tickets. Validation and
Initialize completed. Corpus 2 did not run. Guest stdout and stderr remained
empty; native parity and full diagnostic completion did not pass. The child
exited 101 and the unchanged driver returned failure. No timeout, process signal
or retry occurred. Counts are scope evidence, without a CPU or performance claim.

Root's earlier label audit omitted the word `cache` in human-label normalization.
The subsequent dispatch refused absent selection before a marker or guest child.
That check failure and rejected dispatch are preserved in root's
`preselection-failure.json` as nonattempts. Root then compared the actual function
ASTs, split dependent calls and separately selected the one recorded attempt.
There is exactly one target marker and one `commands/target-once` receipt.
The unrelated failed static preparation assembly also remains preserved.

The first typed CacheWork failure remains identical in `final_failure`, apart
from its appended cleanup observation. `cleanup_empty=false` and
`ownedCleanupEmpty=false` remain unchanged success-oriented flags because the
failure is retained. The final consuming snapshot separately reports every
current reservation category, live count and ticket zero, with no cleanup
invariant. `final_failure.after_cleanup` was copied before foundation consumption:
it retains three foundation tickets, construction 269,424 plus shared 1,744 =
combined 271,168 bytes. `finish_owned_cleanup` then consumes the actual foundation
closure and returns the final zero ledger. The nested final WASI submeter is a
historical copied observation; the runtime ledger's WASI current reservation is
zero. [Cleanup audit](consuming-cleanup-audit.json) binds that boundary to the
unchanged source and harness.

Only constructed and successful Initialize checkpoints are compared with the
immediate prior run. Their guest counters, live shapes and cache behavior match.
Constructed tickets are 21 versus 22; Initialize tickets are 85 versus 86. At
both checkpoints the observed fixed cache reservation is 89,232 versus 89,376
bytes, and combined current reservations are 1,608 bytes lower. These are exact
ownership observations. The two Corpus 1 failures occurred at different cursors
and are not compared as equivalent ownership or performance checkpoints.
[Ownership comparison](ownership-comparison.json) retains the arithmetic.

Target PID/PGID `68901` is absent. All earlier owned groups are absent;
raw stdout/stderr reached EOF and their pre-signal failure evidence is preserved.
Source, input, tool binaries/sysroot, driver, harness and executable bindings were
rechecked. Before removal, exact owned path/inode and empty holder checks passed.
The unchanged cleanup command ran once, removed 77,766,655
logical bytes of owned scratch and retained the executable losslessly as
`bin/exact-tests.gz` (1,785,394 bytes,
SHA-256 `7c856c1adf6c3b4495d7c18bb7d225116acfcfe2b815f05011ea5701c66b4bb8`). Its decompressed
bytes match the selected original executable. No other project's process or data
was touched.

[Result receipt](result-receipt.json), [classification](target-once-classification.json)
and [result seal](result-seal.json) bind raw evidence, exact commands, tools,
PID/PGID/EOF, source, root selection and cleanup. Verify read-only:

```sh
python3 -B verification/swift-exact-reactor-after-grouped-index/verify-result.py
```

No new diagnostic, target, compiler, native, UI, phone, provider, hosted or Git
operation was used to classify this result. Guest parity, full completion, full
SL matrix, public/signed/native execution, production accounting/caller stack,
size/startup/memory/performance, immutable published FieldLog packages consumed
from a separate repository, physical phones, store, customer/operational and GA
acceptance remain pending. Physical phones remain disconnected and deferred.
