The selected host attempt failed at Clippy and correctly refused both full
regression children. This review validates the retained failure evidence; it
does not accept the candidate or claim a successful regression run.

Run [40822264739](https://github.com/snowdamiz/mixer/actions/runs/40822264739),
attempt 1, used head `88c32d7fe9a5596d269ad29eb63c380dc5e820b4` and workflow
400216662. Independent GitHub connector reads confirmed the exact run, candidate
job 123277206864, artifact 12874169678, and exact-ref workflow bytes. The workflow
SHA256 is `d7af6cff1238e02982be50dbd27634a15119a626128549409d9d278c0465625e`.
The guarded controls, Rust installation, and artifact upload succeeded. The
managed-child step failed. No retry was made; the sole selected attempt is spent.

The artifact is 394,698 bytes, SHA256
`c56be30a98b59e7b300ae981a04ebfe26f80806b0070a8ab47bb44691a3acf4a`.
Acquisition used the connector-returned transient URL in a separate bounded
network phase: eight MiB and 60 seconds. The URL and full download response were
neither printed nor saved. A single guarded Python 3.14.8 data bootstrap checked
ZIP paths, types, duplicates, CRCs and decompression limits before extracting
55 regular members totaling 2,091,377 bytes. It strictly decoded 14 JSON documents
and 39 Clippy JSON lines, rejecting duplicate keys and nonfinite values. The
bootstrap denied nested processes, sessions/groups, signals, timers, waits and
sockets before any subject import; no subject code was imported or executed.

The 27 host controls and 16 evidence controls passed in this actual job, with
zero failures, errors, skips, or live API attempts in their result records. Both
exact-head control sources match the selected source bytes. The job log confirms
the 27/16 suite counts. The executed `admit.py` and `bounded_commands.py` snapshots
are byte-identical to the corrected selected runner and helper. Local review
made 209 independent source/data assertions with zero evidence-check failures.
These are evidence checks, not additional product tests.

The original complete 136-member candidate closure is
`7f188bd7b0fe12244936bcbde3f1e4b2f9d9d3fedd43cacbf750d4ba55684748`;
its baseline closure remains
`af0db424af7b08f013d2c6a8894f4d156f76bc5f493620c6f2c0b85d3bf4c48b`.
The formatter changed seven of the selected fifteen overlays. The exact actual
formatted closure is
`1c24099923de0e10835957cb7a8cdc744750014aae360dac5ffe8dccb3f9b60a`.
All fifteen before/after pairs match their inventories; the retained 204,467-byte
unified diff independently applies to produce the retained after bytes. The other
121 source members are unchanged. All nine exact Node oracle function names
remain in the source roster. The ignored raw artifact and exact after bytes are
preserved locally at the paths recorded in `sanitized-result.json` for later
review. No source was installed or promoted.

Four children ran sequentially: compiler identity (0.008399 s, exit 0), Node
identity (0.027998 s, exit 0), exact fifteen-file rustfmt (0.226095 s, exit 0), and
Clippy (8.642611 s, exit 101). Their limits were 30/30/60/300 seconds. Both planned
600-second regression children were not started. All six planned argv are
retained, including exact `-D warnings`, `--include-ignored`, and the offline,
locked all-feature profile. The four output stream pairs match their hashes and
total 44,591 bytes, within the eight MiB per-stream / 32 MiB aggregate bounds.
The aggregate 1,800 active plus 60 cleanup seconds remained unchanged.

Rust identified itself as 1.99.0, commit
`b940084d7eb6a299eb4bfeb8e34901bc051e7ac4`, Linux x86_64, LLVM 23.1.1. The
receipt contains five Rust executable hashes and the required rustfmt/Clippy
component manifest. Node policy B observed `/usr/local/bin/node`, v22.23.4,
SHA256 `94efd062ed066c1a0b332e18249859c905e920eeada5df55d24c99b919629a90`.
The corrected runner source binds that existing executable and private `node`
link, strips ambient injection options, and rechecks source/binaries around each
managed command. All four retained postflights confirm the 136-source closure
and six executable identities. No Node installation or fallback occurred in the
selected workflow; this does not qualify an external Node release.

Clippy emitted exactly one error, `clippy::blocks_in_conditions`, at formatted
`src/experimental_swift_reactor/cache_tests.rs:1219-1223`. The `match` scrutinee
contains a block that creates `returned`, calls `construct`, then unwraps the
result. Clippy's machine-applicable suggestion binds the block result before
the `match`. Its JSON stream contains 37 compiler-artifact records, one diagnostic,
and exactly one `build-finished` record with `success:false`, consistent with
exit 101. The runner retained the diagnostic and raised
`Clippy findings: regression not admitted`. Debug/Release have no command or
result artifacts, so neither 699-pass expectation nor any Node oracle runtime
result is claimed.

Every started child has retained direct-reap and owned-group-absence terminal
facts, no timeout/output cap/custody hold, and consistent sequential aggregate
child resource accounting. The final ownership check and cleanup receipt report
the owned scratch removed and no other project touched. Scratch is excluded from
the uploaded artifact; this is receipt/source evidence of cleanup, not an
independent provider-disposal probe.

The installer remains outside helper custody/output bounds. Explicit VM pipe
EOF/sink-close flags, Node internal pipe caps, and individual Node grandchild reap
receipts remain absent. Arbitrary escaped descendants, whole-provider disposal,
and shared-library identity remain unproven. No local compiler, product, Node
oracle, native runtime, simulator/emulator, UI, capture, physical phone, Git/gh,
held-process probe, or extra-agent action occurred in this review. FieldLog run
40802230894 PGID 2424/PID 2621 and all other holds were untouched. Native/physical,
published-package FieldLog, store/customer and GA acceptance remain pending.
