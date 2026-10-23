# Private durable I/O foundation

`final-receipt.json` joins the frozen owner matrix and independent review.
The five new/changed source files are listed in `inputs.json`; all 139 frozen
dependencies are retained under the recorded ignored source-export path.

The internal directory pins an open fd, holds an exclusive lock and uses relative
no-follow opens, regular-file/link checks, fsync and rename. Reads are capped at
4 MiB, append chunks at 1 MiB, state at 1 MiB, and prune inventory at 1,024 entries.
Pruning inventories before mutation, deletes only owned names and keeps operating
on the original directory after its pathname is replaced. Legacy updater I/O and
its C shim remain byte-identical; the new shim has a distinct symbol.

The seven new tests plus sixteen material tests pass in debug, release and Swift
Thread Sanitizer. Independent review adds 29 checks against the unchanged library,
including directory replacement, exact/+1 inventory, special files and closed
operations. Its `@testable` probe is explicitly internal. Official iOS and Android
module/object builds pass; these are not application links or device runs.

`run.py` records exact host commands and hashes; `cross-receipt.json` records exact
cross commands, environments and ten actual output hashes. `seal.py` audits both
matrices, retained artifacts, old source preservation and the independent seal.
`development-relative-link.log` preserves an initial test-harness link-path failure.
No bit-reproducible artifact claim is made.

This is a synchronous private filesystem primitive. The future store actor must
perform it off the UI executor and retain its outer reservation until actual close
and validation retirement. It creates no signed selection, adapters, execution,
health or recovery authority. Phones remain disconnected and all product gates open.
