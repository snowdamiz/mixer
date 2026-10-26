# Profile-row adapter protocol amendment

This closes the preparation protocol for independent contract review. It does
not select implementation by itself. The preparation seal is
`02f16c13fcea823444a5b775b45e778209f877259fd7222fbfbc7936c19ac412`.
Its real validated-owner seam, unchanged public APIs and deferred real profile
header/construction/result/ledger/custody obligations remain binding.

## Fixed writer

Use one 4,096-byte output block: 128 little-endian 32-byte rows. Exactly 80,000
rows produce 625 complete blocks and 2,560,000 acknowledged bytes. Do not retain
a whole row vector or row-body copy. Each block permits at most 32 actual write
calls, at most 20,000 per file. No 33rd call for a block is permitted. Existing
per-command time limits and all analyzer/VM reservations remain unchanged.

Count every actual write call, including Interrupted, ordinary error, zero and
overreport. Increment the attempt coordinate once before calling the writer.
Only a returned count from 1 through the requested remainder advances the
acknowledged byte coordinate. Interrupted advances attempts only and retries
within the same block allowance. Other errors, zero and overreport stop
immediately; an overreported count is never added. If call 32 completes the
block, it succeeds. If it is Interrupted or leaves an incomplete block, report
exhaustion without a 33rd call. A non-Interrupted error/zero/overreport on call 32
keeps its specific failure code. Global counters retain prior completed blocks.

The safe File borrow must be a regular, initially empty file at offset zero.
The caller keeps the output/open-file-description offset quiescent: no concurrent
writer, truncation or alias seek during this operation. The module never reopens,
truncates, retries a different path, transfers ownership or closes the File.
Partial output is retained. Success means that the fixed row body was encoded
from the validated owner and all 2,560,000 bytes were acknowledged by writes under
that assumption. It does not establish immutable artifact custody, durability,
fsync, digest, physical state after a fault or absence of an adversarial writer.
No finish-time syscall or durability operation is implied. Actual-file tests must
independently read and verify the complete positive body and retained partial
failure bytes; later descriptor hashing/custody remains a separate prerequisite.

## Exact fixed errors

The fixed error fields remain code:u32, stage:u32, offset:u64, output_bytes:u64,
output_attempts:u64. Error values contain no owner, File, string or body borrow.
Use these numeric values, with no success code in an error:

| Code | Meaning | Stage |
| --- | --- | --- |
| 1 | Unsupported/inconsistent validated snapshot policy or global metadata | 1 |
| 2 | Requested absolute row is outside 0..80,000 | 2 |
| 3 | Missing descriptor inside the declared defined range | 2 |
| 4 | Descriptor absolute/type/offset/length identity is inconsistent | 2 |
| 5 | Output metadata query failed | 3 |
| 6 | Output is not a regular file | 3 |
| 7 | Output position query failed | 3 |
| 8 | Output length or initial position is nonzero | 3 |
| 9 | Non-Interrupted write error | 4 |
| 10 | Write returned zero | 4 |
| 11 | Write returned more than the requested remainder | 4 |
| 12 | Block write-call allowance exhausted before completion | 4 |
| 13 | Checked arithmetic/narrowing failed | Current stage |

Stages are 1 snapshot admission, 2 row derivation, 3 output admission, 4 writing
and 5 finish/observation. Stage 5 arithmetic failure may use code 13; there is no
invented I/O at finish. A preflight offset is zero. Row errors use the requested
absolute index times 32 as their wire coordinate, including out-of-range helper
requests; that multiplication widens before multiplying. Write/finish errors use
the global acknowledged byte cursor. A standalone row helper has zero output
bytes/attempts. If that helper fails inside the writer, retain its row offset but
attach the writer's current global acknowledged bytes/attempts. No returned
counter claims unacknowledged physical file changes have been rolled back.

Freeze the exact VM source closure before copied-crate compilation. The validator
and its shared validation dependencies must match the selected source. Disclosed
cache/control differences do not acquire construction or diagnostic acceptance.
Measured row/observation/error/full Result/caller layouts, all simultaneously
live places, complete loop/instruction/error work and snapshot ownership costs
remain required implementation evidence. These protocol numbers do not prove
those layouts or reuse the fixture component's accounting allowance.

## Exact executable coverage

Freeze a required method-name roster covering row, actual File, writer fault,
layout and owner-immutability obligations before qualification. Use compiler
listings to verify the entire selected test namespace and expected total/filtered
counts. Reject empty, missing, unexpected, duplicate or ignored selections.
Execute every selected method in Debug and optimized builds; a `rows_` filter
alone is insufficient. Retain exact passed/failed/ignored/filtered results and
raw output. Any necessary partition must cover the same frozen roster exactly
and retain prior timeouts without a performance-equivalence claim.

Freeze a separate complete bridge-invocation roster for both modes, including
positive actual validated rows, each selected semantic negative and literal-false
authority checks. No zero-invocation, skipped, duplicate-only or missing case can
receive runtime credit. Method-name validation supports actual source execution;
it does not substitute for independently encoded expected rows/offsets/File
bytes or review of the implementation and error paths.
