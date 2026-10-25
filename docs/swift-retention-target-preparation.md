# Isolated retention-candidate full Swift diagnostic preparation

Prepared for root review and a later exact selection. **No full-target attempt
has been selected or executed.** The candidate is not integrated into the live VM.
The packet is `verification/swift-retention-target-preparation/`.

Root supplied revision context `b375e55ded9e3e10c327891ab681beff2a471e26`.
The live baseline closure is `16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd`;
the separate 132-file candidate closure is `d840933a706131e64c50b74812af771ead622912d57575336770434387f5b99d`, from candidate
seal `6507e85f869d0f1a052b9e8e5356ac07910c67813f87b309fa6a5b348e803c13`. The candidate seal and every member/external member were
checked as data. No Git query or live VM source read occurred. Root indexes are
archived context observations, not mutable seal inputs.

The only preparation source change is an absolute include of the original harness
at the end of the candidate's lifecycle test file. The copied build manifest is
`090ce41c7cebca128502f3c04f366674c826cdfa85a3560b615ebbea6903771e`. The harness remains byte-identical to
`verification/swift-exact-reactor-after-plan-reuse/harness.rs`, SHA-256
`d72da7bc7aaf4e31b7093fde497f357226d3a4dd954eb577909209102a0bfb00`. The newer attribution harness and observer are not used.
The original workload, native eleven-field oracle, parser, event emission,
phase sequence and Rust consuming cleanup remain exact. Original host tools,
process supervisor, parser, build, cleanup and ten host tests are literal copies;
the [driver diff](../verification/swift-retention-target-preparation/driver-changes.diff)
records isolated paths/source bindings, labels and the fresh review/selection guards.
The inherited prepare CLI and old live-source copying procedure were removed.

## Executable preparation evidence

The fresh offline Release no-run build passes in 12.401
seconds with two Cargo jobs. Listing selects exactly the original tiny control
and target test names. Cargo/Rust 1.99.0, Python 3.14.8, macOS 27.0.1 arm64,
tool identities, sysroot hashes, source manifests, exact argv, environment,
raw streams, process groups and deadlines are retained in the binding and receipts.

Both unchanged tiny synthetic harness controls pass. Each executes synthetic
Initialize once and Corpus twice, five guest instructions, and consuming cleanup
to zero current reservations, live tickets and live counts. They prove wiring
and cleanup only. The ten original mocked process observation tests pass;
eight additional host-only tests check accepted-review prerequisites, drift,
candidate/baseline substitution, historical path rejection and safe archive names.
Those eighteen host tests execute no guest instructions.

The initial assembly attempt rejected the source archive's timestamp-only PAX
metadata before source restoration or compilation. Its streams and exact scripts
are retained. The extractor now permits only bounded finite `mtime` metadata;
path/link metadata, duplicate or unknown names, links and non-regular files fail
closed. Extraction is limited to 132 members, 24 MiB total, 16 MiB per member and
a 2 MiB compressed archive, with every content hash checked before writes. The
corrected assembly, first build and every executable control pass.

## Exact proposal and selection boundary

The [proposed command](../verification/swift-retention-target-preparation/proposed-command.json)
uses the retained 4,986,496-byte executable, SHA-256 `76927bc5239984cf39520cbcaa0fb7871cce199e7278124b8998facd5b04de70`.
The outer command, still unselected, is:

```sh
python3 -B verification/swift-retention-target-preparation/diagnostic.py target
```

Its child argv selects only the original `exact_reactor_target_once` test with
`--exact --nocapture --test-threads=1`. Validation stays 120 seconds; runtime and
WASI stay cumulative 30 seconds. The outer limit stays 170 seconds plus the
original bounded 5+5-second exact-process-group cleanup. Residents/pins stay 64,
tickets 86, cache/entry limits 16/8 MiB, cache work 64 million and combined memory
256 MiB. All other original ceilings are retained. Initialize 35 and Corpus 62
twice share the same owner and cumulative accounting lifetime.

The 53,777,114-byte target remains immutable data, SHA-256
`24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994`.
It was hashed, never validated, compiled, instantiated or executed in this lane.
The native oracle output was read as historical data; no native oracle ran.

The [scope binding](../verification/swift-retention-target-preparation/proposal-scope.json)
preserves candidate tradeoffs: the hot-plus-scan trace used 6.3192% fewer cache-work
credits, cyclic 65 used 2.1100% more, and the cyclic 64 resident-hit work ratio was
22.7773. These finite traces do not establish actual-target improvement. No
budget or credit is relaxed to accommodate the policy.

The root-selection template deliberately refuses dispatch. Root must first
independently accept this sealed preparation and the finalized accepted review at
`verification/swift-cache-retention-review/`. The target guard hashes that review's
seal, summary and all sealed members, requires its finite acceptance with no
blocking findings, checks both distinct source closures and the original candidate
seal, and rejects target/integration/GA selection in that review. A new root
selection must bind the exact preparation seal, copied source manifest, executable,
harness, driver, tools, input binding, argv and budgets. Its timezone-aware timestamp
must follow both final seals. Historical root selections authorize nothing here.
The exclusive `target-attempt-started.json` marker permits one actual attempt;
neither it nor a root-selection file exists.

## Retention, cleanup and pending work

The source is retained as a verified 1,244,751-byte gzip archive;
the exact executable is retained as a verified 1,879,891-byte gzip.
All compiler products, the owned scratch tree and the uncompressed executable
were removed after exact scoped holder checks and device/inode checks. Cleanup
removed 29,269,937 logical bytes. Every preparation-owned process group
was observed absent, and no signals were needed. Other projects' processes and
native instances were not touched.

`restore.py` first runs the read-only verifier, then restores only these exact
products under this packet's `owned-scratch/vm` and `bin/exact-tests`. It refuses
existing products, selection or attempt markers, and never builds or runs code.
Root should archive its later attempt and cleanup evidence in a separate result
namespace; do not rerun preparation build/control/proposal/cleanup actions after
selection or overwrite these preparation receipts.

```sh
python3 -B verification/swift-retention-target-preparation/verify.py
python3 -B verification/swift-retention-target-preparation/restore.py
```

The first command only reads and hashes. The second is an optional bounded owned
restoration for root review; it was prepared but not executed by this lane.
Root alone selects any later target command after accepted independent review.
No source/product integration, Git, network, hosted/frozen lane, native/UI/device,
signing, publication or customer action occurred. Actual target benefit, full
regression, published-package FieldLog qualification, physical phones and all
accountable GA gates remain pending. This is preparation within W08 and preserves
the binding W01–W18/G01–G38 product scope.
