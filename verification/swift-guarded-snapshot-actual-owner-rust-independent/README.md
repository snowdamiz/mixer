# Independent actual Rust input-owner review

The candidate is returned for required IR01 correction. One fresh independent
desired-property test fails: a complete acquisition token releases storage from
1,000,000 to zero while the real validator-created proof retains its original
1,947-byte source Box and all four loader guards remain live. Only the thirteen
acquisition guards have ended. The exact source, witness and failed output are
retained in `finding-retirement.json`, `retirement_witness.inc.rs`,
`witness-source/` and `commands/witness-run-001/`.

This is a shared generic accounting-core invariant failure under private host
construction. It does not establish a currently reachable native refund: the
actual outer caller destroys its child result before acquisition retirement,
the native File bridge refuses complete tokens, and bootstrap/admission remain
Pending. A correct positive caller order does not make the generic token prove
all charged result carriers have ended. `correction-interface.json` bounds the
matched/refused carrier, adoption/result, acquisition token and compiler subcase
requirements. This review selects no correction implementation or extra budget.

Preparation passed over 91 unchanged inputs with no producer access. Root then
explicitly released frozen producer seal
`3592011c00794c12dcb76cecc41d4d2913e01a3d6e97612f3ce90f10cb4e5e23`.
Independent offline custody/source/MIR review passes in 4.85 s: all 1,799 packet
members/209,640,941 bytes are exact, every original source origin is hashed,
only the selected two members change, and host11 plus `host_account_v1.rs` are
byte-exact. The unchanged entire original loader prefix is 51,173 bytes, SHA256
`ebe88f37d2721c41371c9f726aeefaf533451cc9b6309b296053bc3b327240b9`.
Five final command manifests bind source146 tree
`338ef290399450c712b140736fb714031a333891dc1acf5439c758ae97602564`
and exact host11 bytes.

The independent complete retained MIR inventory accounts for 6,207 items:
2,141 functions, 2,059 consts, seven statics, one standalone typed constant and
1,999 allocation blocks. Initial/final candidate items agree after only display
comment/impl/closure-span normalization; allocation identities/bytes remain.
Historical unchanged source146 MIR is unavailable. `source-mir-report.json`
contains focused ownership/drop observations and revision attribution;
`mir-item-inventory.json` binds every item to immutable retained MIR. Source
review confirms whole-outcome capture, strict admission, private association,
original buffer lifetimes and the H09/H10 corrections. These are source and
retained-evidence observations, not fresh full-suite behavior passes.

All eight retained producer negative probes were reviewed without replay.
`compiler-coverage-review.json` records their exact diagnostic/subcase coverage:
the omitted Clone, correspondence, proof-source/root-reservation lifetime and
separate privacy sites remain unrun. Producer passes are not independent runs.

Root authorized one Debug build and one exact IR01 run. Only a private cfg(test)
method was injected into copied sources; all product core bytes are unchanged.
The build passes in 6.60 s. The exact run fails its desired property in 0.256 s
(0 passed, 1 failed, 496 filtered out; exit 101). Owned PID/PGIDs 8053 and 8260
were waited and confirmed absent. Exact argv/environment, tool version/hash,
source manifests/tree, full output and cleanup are retained. No further Rust
command ran and the compiler lane is released. `cleanup.json` hashes the removed
binary and 156 unchanged copied sources; the exact injected loader remains.

No broad independent matrix ran. The preaccess 51 binary substitutions,
230 provenance substitutions and 12 read schedules remain available for the
corrected candidate. The overall H01-H13 actual component review is incomplete.
9398732 is the historical frozen baseline, d6af738 root orchestration, and
b231f3d at release a console-only change. No contemporaneous producer HEAD query
was made; exact command manifests establish source bytes.

Navigation/authoring are preparation. Missing guessed filenames were resolved
from custody; no test retry was minted. The memory search supplied no relevant
technical fact or test source. No real File/FD adapter, native acquisition,
genuine loader/fixture/writer/healthy close, UI/browser/capture, simulator/
emulator/phone, global process inventory, stopped Android v5 action, Git mutation,
dependency, publication or other-lane write occurred. Native custody/policy/
allocator, actual prices/layouts, root funding, immutable separate-repository
FieldLog, store/operations/OTA and every GA gate remain Pending.
