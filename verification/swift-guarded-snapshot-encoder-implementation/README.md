# Pure guarded MIXSNB02 encoder component

This is an isolated implementation over the accepted144-member Rust source.
All new encoder and host code is inline in existing source members, and the exact
eleven host-support members are bound in each fresh loader build preimage. The
immutable released interface proposal remains unchanged. `source-delta.patch`
and `final-source-manifest.json` identify the complete implementation delta.

`borrow_snapshot_v2` accepts only a borrow of the actual sole
InitialProfileBorrowV1. Its opaque view consumes into a non-Clone2600-byte cursor
with one2560-byte fixed header. `next_block` fills the caller's borrowed4096-byte
array continuously across boundaries and returns opaque bytes/offset/final state.
No whole-snapshot allocation, I/O, callback, foreign proof/digest/bool, guard
constructor, reset, work grant or stop token exists in the encoder interface.
Actual proof fields, Buffer inventories, five retained digests, opaque nonce,
four identities, runtime budget, actual WASI configuration and actual34 resolved
enum values supply the bytes. Enum matches are exhaustive. Fixed checks happen
at cursor initialization; record checks occur lazily within each block call.

There are twelve genuine selected-guard byte comparisons: unit and ordinary
production-host builds, each Debug/optimized, each testing the unchanged1947-byte
baseline and a separately actual-validator-accepted1967-byte derivative with
data/element records, with and without a same-owner WASI context. The outputs
are9355/9439 bytes in three continuous blocks. Actual parameter capacity has
eleven spare elements. An independent Python Wasm reader and byte builder matches
every byte; the accepted corrected finite parser also accepts every artifact.
Encoder calls observe zero allocation/reallocation calls. The host artifact
collector allocates separately and is explicitly outside this claim.

Four ordinary adoptions refuse MissingSelectedProvenance while the original
primary header/rows still succeed. Thirty internal negative compiler controls,
two internal positives and six external privacy negatives pass with no unrelated
diagnostic codes. Ordinary production-default Debug/optimized metadata/libraries
compile, and exported symbol inspection finds no host/encoder export. Enum,
Option and span-bound unit checks pass. Fifty-two layout identities agree across
the four builds;27 additional helper-place shapes have unit/production
Debug/optimized compiler assertions. `host/source-places.json` and
`host/loops.md` provide the source-place map and finite per-call loop ceilings.
They are inputs to later admission composition, not a selected simultaneous floor.

The exact host observation hook follows the unchanged sole guard literal.
Original guard fields, eight primary outcomes, constructor ordering, header,
rows, tickets, cleanup and original300000/400000 refusal selections remain
unchanged. The existing complete17 host budget is reused literally. The test
module's cfg gains only mixer_snapshot_encoder_host, with a private module import;
production default omits all host observation/entry/allocator code. This is the
reviewed placement amendment to the immutable proposal.

The first compile failure and two layout-log parser failures are retained under
commands/runner-failures/attempt-history. The compile repair corrected a type
path and nested observation visibility. The parser repairs handle the unit test
harness prefix and multiline stringify output. The encoder's genuine positive
bytes passed before and after those runner repairs. Historical directories were
relocated beneath attempt-history; their raw bytes, source/support versions,
preimages and receipts remain preserved. Compiler products are intentionally
removed after collecting final hashes and layouts; paths in old execution
receipts identify the historical execution locations.
The supplemental compiler assertions also preserve an initial failed assumption
about standard Result layout: fixed-array-reference results use an8-byte null
pointer niche, and the byte-array result uses9 bytes/alignment1. The corrected
sizes are checked by the compiler in all four configurations. An early freeze
attempt refused before that supplemental receipt existed and created no seal.

This component does not implement or accept the writer, original-control
work/storage/stop admission, selected owning scope, independent outer result,
all-eight operational export behavior, consuming exporter-place accounting,
File acquisition/alias/close/name/hash custody, full workload, canonical
integration, native/physical matrix, immutable separate-repository FieldLog
packages, OTA/signing/store/customer/operational qualification or GA. Original
control cleanup observations cover the original owners only. Zero new-floor
admission follows from test success. Native/device/simulator/emulator/UI/capture
and process inventories remain paused. No canonical source, Git index, commit,
push, foreign process or frozen source packet is modified.
