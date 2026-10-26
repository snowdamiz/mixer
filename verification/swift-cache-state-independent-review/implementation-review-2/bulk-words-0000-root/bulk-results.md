# Initial admitted bulk results

The first 64 word, 64 transition and 64 sequence cases all passed through the
unchanged sealed content-dedup runner and comparator: 192 public four-File cases,
zero failed cases and zero orchestration failures. The batches ran serially in
that order. No additional batch, API control, private control or probe ran.

Before execution, the reviewer identified that the runner completes an admitted
batch before reporting failure, while the first receipts' stop wording could
mean a stop between cases. Root preserved those receipts and supplied immutable
v2 receipts clarifying completion of each bounded batch, with no next batch after
any failure. Only v2 receipts were executed. Neither tooling nor expectations
changed. All three batches exited zero and had no case failures.

Each case retains all 32 expected/actual words, raw driver stdout/stderr, exact
exit/timeout/output-cap status, inherited diagnosis/report bytes, report hash,
input hashes and role/content object references. Every logical stream, profile
and context byte can be recovered exactly. Shared profiles remain ordinary
quiescent input Files, opened at zero in each separate driver process. The result
sealer rechecks the retained comparator and lossless mapping without executing
any candidate again.

The exact compiler remains the root-bound Rust 1.99.0 Apple arm binary. All 201
actual version/compiler/driver child commands have UTC starts, durations,
60-second deadlines and one-MiB-per-stream caps. Parent argv, observed exits,
empty outer output and exec session identities are retained. Exact parent wall
duration was not separately instrumented; it is not reconstructed from child
durations or filesystem metadata. The six returned owned library/driver products
were hashed before deletion, after their children returned. Sources and all raw
evidence remain. No process discovery, native, UI or capture activity occurred.

The correction-control 1,241-member seal, transport 252-member seal, initial
899-member review and corrected 814-member candidate were reverified unchanged.
These finite semantic executions do not supply budget, complete lifetime,
implementation or GA acceptance. Separate source accounting blockers and all
remaining unadmitted public/private matrices remain open.
