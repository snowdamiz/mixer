# Cache fixture Debug timeout investigation

The exact `8888d8e2c8431ee311c68e94a1abbb280f84802a` Engine artifact failed its
60-second child wall deadline while running a finite, expensive context-schema
test. Existing cleanup evidence supports completion of cases 0 through 985 and
identifies active case 986, `context-reserved-1011`. This is forward-progress
evidence, not a precise phase trace or a recovered pass.

The source method has 1,003 ordered vectors: 23 scalar mutations, 976 reserved
words and four lengths. Every invocation allocates and initializes an 8 MiB
arena through 1,048,576 budgeted eight-byte extensions before context validation.
The entire method therefore has 1,051,721,728 such Debug iterations. It also
clones and rewrites the unchanged 2,560,512-byte profile for every vector. The
retained active case has complete stream/profile/context input lengths and an
empty report. Saved artifacts do not distinguish CPU cost, filesystem cost,+scheduling pressure or a stalled OS file operation in that last case.

`report.json` binds the command, sources, raw retained evidence, exact current
revision/tree and limitations. `ordered-context-vector-inventory.json` records
all 1,003 ordered input identities and matches the retained active context bytes.
`git-source-bindings.json` records read-only Git object observations: both prior
`56ff14c9` and current `8888d8e2` have fixture subtree
`ccf670a18d2d28ccb67220c8a1cae414476ef8f5` and workflow blob
`c739fa726fd8f6a67390654eb76262b42b9ed73d`.

The prior `56ff14c9` fixture job succeeded; its exact raw method timing is not
locally retained. Embedded `c4d04e56` history has the same pack/test/analyzer
bytes and a 27.153708-second method pass, but its Rust 1.99.0 compiler and runner
hash differ from current Rust 1.98.1. That comparison cannot identify the cause
of a timing difference. The remote job uses a sparse fixture-only checkout;
the local SDK tree size is not evidence of its remote runtime disk payload.

The root-selected proposal is confined to
`candidate/source/regression/independent_tests.rs` and
`context-harness-proposal.diff`. It preserves the closed canonical pack. The
original general `run()` function remains byte-identical; the context-only
method writes immutable shared baseline stream/profile files once, clones only
context bytes, opens fresh read-only input handles per vector and explicitly
asserts every input/output cursor starts at zero. Context and report remain
fresh per case. The copied result/report assertions are byte-identical.

The candidate checks shared file content and read-only permissions before and
after all vectors. It removes each case only after assertions and handle
closure, and removes shared files only after the final 1,003-case count and
content checks. A failure retains shared inputs under owned scratch for the
unchanged runner's recursive content retention. Progress every 64 completed
cases records preparation, analysis, report/assertion and cleanup wall costs.

`candidate-source-audit.json` verifies all 1,003 candidate vector bytes/order and
the exact assertion block against the bound original source. It grants no
compiled, runtime, performance, semantic or release authority. A real compiled
fixture test is pending. All arena allocations, replay/IO budgets, capability
guards, original failure evidence and 60-second child/600-second active limits
remain unchanged. The proposal eliminates 2,565,633,024 bytes of profile file
rewrites and 2,568,193,536 bytes of profile cloning; the large arena cost remains.

Before delivery, root must review this source and create a coherently repinned
candidate pack/runner without editing historical packets. One bounded remote
diagnostic on the declared compiler should retain phase timing and per-child
CPU user/system usage. If analysis dominates and the same deadline still
expires, review finite subcase partitioning with complete ordered coverage and
the same total active bound. Do not infer a pass from a timeout increase or a
single-method result; the complete exact-source fixture closure is required.

Executed commands were source/JSON reads, read-only Git object comparisons, and
the two pure Python preparation/audit scripts. Their audit hooks deny child,
socket and process-signal operations. The initial audit attempt blocked
`platform.platform()`'s hidden `uname` child before spawn; this is preserved in
`audit-initial-failure.json` and corrected with `sys.platform`. No Rust, Swift,+compiler/runtime, native UI, capture, process/custody probe, Git mutation,+dispatch or retry was performed. Canonical and frozen files were preserved.
