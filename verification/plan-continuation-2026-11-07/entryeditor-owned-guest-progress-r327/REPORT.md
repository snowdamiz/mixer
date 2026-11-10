The real shared FieldLog EntryEditor passes native and owned-guest execution. The
complete outputs match: 600 stdout bytes and empty stderr on both sides. The
unchanged owned command runner validates all 80,544 function bodies in the
60,920,658-byte Wasm module, executes it to guest exit 0 and reports completed
logical cleanup with zero retained reservations and live tickets.

The fixture exercises draft save, opening a new EntryEditor with the saved draft,
exact Unicode note bytes at commit, title trimming, duplicate UI submission,
exactly one entry and one `entrySaved` outbox operation, exact retry, conflicting
retry and draft resurrection rejection. Controlled continuations prove that a
cancelled old result cannot finish a replacement generation, and that closing
fences a late result while its known waiter drains. All feature instances close.

Storage is an explicitly scoped in-memory port. It calls the real
`EntrySaveIntent.apply`, Workspace validation and `EntrySaveIntent.result` inside
a copied transaction value. It does not exercise the filesystem or process
restart. Exact intent retries preserve entry/outbox effects while incrementing
the transaction revision, matching the repository contract.

Only five fixture/harness files are authored. Canonical product and policy/index
files are untouched. The shared EntryEditor extracted from the R290 completed
archive matches R206 byte for byte. Copied VM and MixerCore inputs match the
canonical source at packaging; exact hashes are in `source-manifest.json`.
Root Git was prohibited, so no current Git revision is asserted.

Native uses Apple Swift 6.4.2 on arm64 macOS 27. Guest compilation uses Swift
6.3.3 and its Wasm SDK. The preserved first native compiler failure rejected
the newer SDK's `-target-arch-variant` argument. The first app fixture also failed
on both native and guest because its port omitted the repository transaction's
revision increment. The isolated fixture correction supplies that increment;
the original source, native assertion and guest trap remain recorded. A premature
debug launch and an optional failed SDK-version query remain recorded separately.

Production/default profiles and ceilings are unchanged. Strict TableMemoryV3
still rejects module size; the fixed reactor rejects 80,544 functions against its
79,966 limit. Successful execution uses the existing
`swift-command-diagnostic-v1` route. Its expected `GuestExit(0)` terminal record
is successful according to `SwiftCommandReport.succeeded()`.

Reviewable delivery:

- `entryeditor-fixture.patch`, `afterimages/`, `afterimages.json`: five added
  fixture/harness files; patch applied in an empty owned directory and every
  resulting file compared to its afterimage.
- `inputs.zip`, `source-manifest.json`: frozen compilation inputs; every archive
  member checked against its source hash.
- `artifacts/`, `artifacts.json`: retained native binary, Wasm module and owned
  VM runner.
- `COMMANDS.txt`, `logs/`, `comparison.json`, `versions.json`, `receipt.json`:
  exact commands, failures, final results and scope.
- `python3 compare.py`: rerun the complete output comparison.
- `bash reproduce.sh`: compile and run in a fresh owned replay directory using
  the frozen inputs and standard local tools. It retains its exact replay path.

Completed disposable build directories and expanded input copies were removed;
compact inputs, executable artifacts and raw outputs are retained. No device,
shared frontend, held namespace, remote mutation or process signal was used.
Direct payload children were reaped; independent process-group absence is not
claimed. Details are in `cleanup.json`.

Root reconciliation and the slice's independent review remain pending. This is
development evidence for the in-memory app flow. Filesystem durability,
device/UI behavior, immutable published-package consumption, release and GA
qualification remain unverified.
