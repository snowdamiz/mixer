# Independent native capability boundary review

The bounded independent review passed with no remaining blocking findings. This
lane made no production edits and operated no device. The candidate is identified
by the exact 90-input source manifest, not the mutable checkout's Git HEAD:

`76372fd254e646141e991b3289b14c8380f13ea68602b21d4aa746080fddc8cf`

`receipt.json` records original public-C execution against copied frozen inputs;
`owner-audit.json` records the separate audit of the owner's Rust, C, symbol and
official mobile compile/link evidence. `owner-receipt.json` and
`owner-archive-provenance.json` preserve the exact audited receipts. Logs retain
commands, versions, outputs and hashes. Source hashes were checked before and
after review execution and again after the owner-evidence audit.

| Independent host C execution | Checks | take/close races | ack/close races |
| --- | ---: | ---: | ---: |
| Debug native-only V3 archive | 4517 | 48 | 48 |
| Release native-only V3 archive | 4589 | 48 | 48 |

The assertion totals depend on which branch a race reaches. Both configurations
passed. The stable archives were copied before linking and verified by SHA256:

- Debug: `66519ab92e7779121a450914698f9fe1f00760bbcbcafdee3c29975d8302e640`
- Release: `db04bf0baa4a844f12facbda682a557fef4e467e8a2f213c8341e00f60ac9f58`

The independently authored client and original tiny Wasm builder check the shared
sixteen-slot old/new family pool, retained closed dispatches, new session and
request generations, actual mailbox authority for repeated acknowledgement,
cancellation controls, trap cleanup, argument snapshots, memory bounds, unaligned
structures, report-inclusive alias rejection with unchanged sentinels, pointer
overflow, null reports, all limit fields and old profile rejection. After each
race group the client fills and releases all sixteen slots to detect leaked
capacity. No native I/O is started: opaque trusted completion bytes exercise the
public C transport contract.

Source inspection found the intended ownership and lock ordering coherent:

- The registry synchronizes dropping a transient Arc while its matching retained
  Live/Closing Arc prevents final destruction. Only a sole Closing Arc with zero
  outstanding work and no quarantine can enter Reclaiming. Final destruction
  occurs outside the registry; generation reuse waits for it to finish.
- Registry code never acquires the native ledger or mailbox. The guest instance
  and native ledger each acquire the mailbox without a reverse lock edge found.
- Eight owning ticket entries count only issued Call messages. First successful
  actual acknowledgement decrements; repeated acknowledgement still consults the
  retained mailbox lease. A new generation replaces only an acknowledged entry.
- The take commit guard covers ledger/count and public output publication.
  Quarantine is monotonic; successful close/cancel cleanup can return zero while
  quarantine continues to deny ordinary/ack access and pin capacity.
- New C preflight includes the report before any write. Invalid or aliased report
  ranges return three without writing. Old ABI layouts and implementations retain
  their existing contract; wrong session families fail closed.

Pre-freeze findings were corrected by the production owners: after-ack versus
existing-terminal precedence was clarified without changing the frozen mailbox;
published-session unwind guards were added, including expire; quarantined cleanup
success was explicitly documented and tested. The independent client follows the
corrected precedence: an existing unconsumed terminal yields kind one even after
acknowledgement; early acknowledgement without a terminal rejects post/deadline.

The owner audit verified all 90 live source hashes, 14 legacy inputs byte-for-byte
against `cc0ac37abf45c59df7c85f59ebbb038af7c0a251`, the driver and provenance
script hashes, 76 matrix logs and two supplemental archive logs. It independently
reparsed default 91 and all-feature 185 passed tests per mode, matched all nine
normally ignored oracle names to their explicit successful runs per mode, and
checked explicit legacy destructor, mixed-registry destructor, four public API
and allocation tests in both modes. Ledger poison/unwind/quarantine tests passed
inside the all-feature suites. It matched 14 real C smoke outputs and the exact
legacy 12 versus native 27 exported symbols. All six retained iOS/Android arm64
archive/object/linked-client hashes matched; recorded file outputs identify the
expected arm64 Mach-O and aarch64 ELF binaries. Those binaries were not executed.

The common host target was overwritten as the owner switched feature modes.
Default/guest/all host archive and dylib hashes remain build-time owner records,
supported by the source-bound driver and command logs. They are not claimed to
have been independently rehashed later. The retained native release archive is
independently rehashed and matches the primary native matrix archive.

`attempt-1/` preserves the first green review before a default-feature Clippy-only
source correction. `attempt-2/` preserves the second green review against V2.
After the owner mixed-feature matrix, a native-only debug rebuild changed archive
bytes while all 90 source hashes remained identical. The owner preserved the
initial strict-equality failure and build log; its cause was not investigated.
Fresh logged V3 copies were therefore replayed here. Release bytes stayed equal.
No bit-reproducible-build claim follows from any receipt.

Reproduce the host execution and then finalize the evidence audit:

```sh
python3 verification/capability-native-review/review.py
python3 verification/capability-native-review/audit-owner.py
```

The runner pins this Mac's official compiler/SDK and exact retained archives.
The C11/pthreads client and Python fixture builder use portable interfaces by
inspection; Linux CI must supply its own Linux archive and linker flags. No
Linux execution was performed here.

The public races are bounded stress, not exhaustive model checking or panic
injection at every possible C boundary instruction. Standard allocator/OOM aborts,
foreign framework code, dangling pointers and invalid caller-owned memory remain
outside the declared containment and numeric-preflight contract. Requested-byte
allocation observations are not RSS, global resource caps or process OOM proofs.
Native acknowledgement relies on a trusted caller observing actual resource exit;
these tests do not prove OS destruction, rollback or native I/O behavior. There is
no Swift/JNI async bridge, physical mobile lifecycle, signing/store, FieldLog,
operational, release or GA qualification. Phones stayed disconnected.
