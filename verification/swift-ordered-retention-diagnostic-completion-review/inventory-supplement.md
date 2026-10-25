# Independent selected-fixture lifetime and owner supplement

The frozen producer's 16,114-byte peak and 49,362-byte union are provisional.
This review charges previously unnamed full path/file owners and complete
return-transfer roles. The corrected selected-fixture source-value maximum is
**16,186/16,384 bytes**, leaving **198 bytes**. The separate conservative named
role union is **51,712 bytes**. Those union roles never all coexist.

`inventory-supplement.json` retains every original phase, every addition and the
extra initial exclusive-file-open phase. `inventory_supplement.py` checks all
nineteen corrected phase bounds. The new rows are not physical compiler-stack,
TLS-runtime, allocator, formatting/hash/FileIO implementation, kernel or RSS
measurements. The qualification applies only to the six new completion fixture
paths and their new serializer/readers. Inherited receipt helpers remain open.

Two executable probes establish the actual sizes with the same explicit Rust
1.99.0 toolchain. The standalone probe measures PathBuf/String/OsString and
Option<OsString> as 24 each, File as 4, io::Result<File> as 16, OpenOptions as 12,
and Option<[u8;512]> as 513. The actual copied-VM probe measures DispatchGuard
and its Option as 24, EndReceipt and its Option as 128, Rows as 56, Outcome as
3,888, its complete `(Outcome, Option<EndReceipt>)` return as 4,016, the complete
cleanup return as 1,624, and ReceiptWriter as 544. This one test-only source
addition has its own complete 132-file archive/manifest; all exact candidate
bytes were restored afterward. It does not replace the fresh 362-method run.

| Source interval | Complete-owner addition and lifetime |
| --- | --- |
| path() construction | The 416-byte PathConstructionValues group charges two String headers, Option<OsString>, two more OsString transfer owners, five PathBuf construction/return owners, complete thin/fat borrows, scalar arguments and checked return. Two bounded 128-byte name allocation roles are charged across the original phase plus supplement. The original four 512-byte path-capacity roles remain charged. A non-Copy move consumes its source before the destination can be used; duplicated transfer roles here are conservative. |
| outer path and receipt_path() | Every affected phase gains 24 for each of its one, two or four simultaneously retained PathBuf owners. Outer off/on paths and the temporary derived receipt paths retain separate header roles in the union. The function-local p moves into its return before the caller can use the returned owner. A derived-path temporary ends at its statement boundary. |
| initial exclusive open | A separate 6,878-byte phase explicitly charges three complete File transfers, two complete File Results and two OpenOptions values in addition to common storage, the complete path owner, Begin roles and literals. This phase precedes header construction. |
| header construction | The initial File remains live. Two whole 513-byte header Option transfer roles are added to the already conservative four full frame roles. They are not mistaken for 512-byte arrays. Header/encode locals return before caller h is initialized; the enlarged count covers both sides conservatively. Initial metadata serialization's lexical block has already ended. |
| Writer::new and Begin | Complete Writer/File and Option<Writer/File> owners are already 4,408 each. The sink argument's separate 4-byte transfer is added to Writer::new. Begin additionally charges two full 24-byte guard Option transfer roles, alongside the original whole guard return. The caller h, full TLS storage even while None, literals, arguments and borrow/checked-result groups remain charged. This produces the corrected maximum 16,186. No original operation Result has been created when start runs. |
| callback and original failure | Full pin/release Result owners, failure/usage copies, tokens, displaced ticket and allocation observations remain charged separately from callback groups. Source operation results are retained before observations; source-invalid moved pin/ticket owners are never reused. No supported error is substituted for an unknown original code. |
| End/footer | Two whole 128-byte EndReceipt transfer roles are added to the original receipt role. Original output values remain live. Footer construction, end argument, writer finish argument/return and encoding frame roles remain fully charged. End closes admission before reading flags; callback frames have already returned in these synchronous fixtures. |
| retirement | The corrected 16,130-byte row retains the original output group, caller receipt, full TLS storage and complete taken Option<Writer<File>>. End's nested footer/metadata frames have returned before retirement starts. File::drop has no claimed close Result; the full File owner is already inside the complete taken writer. |
| Outcome assembly | The complete original Copy fields coexist with the new Outcome during assembly; two Outcomes plus two receipts cover assembly and return transfers. The lexical run block ends before persist. The actual return tuple's 4,016 bytes equals the charged Outcome plus complete receipt. There is no third simultaneously source-valid non-Copy Outcome. |
| receipt serialization | Three complete 544-byte ReceiptWriter owners include all embedded Files and fixed buffers, including create/return/finish transfers. The supplement adds the actual complete open Result and OpenOptions temporaries. Full paths gain their owner headers. Three Formatter groups remain charged, including complete fmt::Arguments/descriptors, Formatter, authored write/error/checked/range/slice roles. The corrected serialization maximum is 15,542. No heap format! String is created. |
| nested Debug | The longest type path is original Option -> SwiftRunFailure -> after_cleanup Option -> SwiftRunUsage -> wasi Option -> WasiUsage -> WasiReservations: seven helper levels. The alternative reservations path ends in SwiftReservationUsage and is shorter. Eight measured values of every public Debug helper family remain charged; fields are formatted sequentially. Selected fixtures actually have wasi=None. Opaque standard formatter internals are outside this source-value claim. |
| row and parity readers | Rows gains a separate complete return owner; row/header readers gain actual File and File Result owners. Parity's already charged two File Results are retained and its two complete File owners are added. Fixed 128/512-byte buffers and full retained outputs stay charged. No Vec/read_to_end/collect storage is hidden. |

For the exact fresh-suite TMPDIR, the executable path probe observes name
capacity 30, environment/from capacity 134, joined capacity 268 and all five
receipt extension capacities at most 160. These are finite selected-source
observations; source checks still enforce name<=128 and final/derived path<=512.
The common four-capacity construction allowance is retained rather than reduced
to those smaller observations. No general arbitrary-path qualification follows.

Python custody's corrected named peak remains 103,777/131,072 bytes. An independent
wrapper counts complete FileIO object lifetime, not only descriptor closes:
seven owners are created, closed and destroyed; maximum live owners and maximum
open descriptors are both two; final live/open counts are zero. `_copy` returns
before `_inspect` begins. Metadata receipt reads use no-follow descriptors and
read(cap+1); an injected 200,000-byte growth requests exactly 2,049 bytes at a
2,048-byte cap and refuses. A separate actual-call counter proves the refusal at
32 reads and zero writes after 31 Interrupted results, with the sole exclusive
destination retained. These finite controls do not qualify hostile-process races
or opaque Python/JSON/hash/FileIO physical memory.
