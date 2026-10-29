# Independent host proposal review

Accept the frozen proposal for root selection of one bounded hosted attempt,
with the two evidence limits below. This review does not select, install or
dispatch a workflow, admit Rust results, or repeat the accepted candidate's full
semantic review. No execution-authority blocker was found.

The input packet is exactly 18 members, seal SHA256
`2012b4f0aabe97ebc2c10a501ea0f1dcc06791b0b4dcc5db5bb80c371fb28238`,
tree SHA256
`b3bb8c60d2a14213b48e7a203b97618cce8214fd78b09219f9d779fd3ef7359c`.
Independent source admission reproduces the accepted 136-member candidate,
15 overlays, closure
`7f188bd7b0fe12244936bcbde3f1e4b2f9d9d3fedd43cacbf750d4ba55684748`.
The parent-supplied revision is
`6d57e05e58e6d614e58a0a4dc0fad661264fb46f`; no Git verification was performed.

The six sequential commands are compiler identity, Node identity, standard
rustfmt over precisely the 15 overlays, locked/offline all-feature/all-target
Clippy with `-D warnings`, full Debug and full Release. Their maxima are
30/30/60/300/600/600 seconds, totaling 1,620 seconds. The driver provides 1,800
active plus 60 cleanup seconds, six children, 8 MiB per stream and 32 MiB total.
The helper also refuses a full next timeout that cannot fit its deadline.
Clippy exit 101 retains diagnostics but cannot admit tests. Both profiles
require 699 terminal `ok` lines, zero ignored tests, and all nine oracle names
exactly once. No baseline run, fallback, Node installation or automatic retry
is present.

The materializer verifies the correction seal, every producer member, baseline
and candidate rosters/digests, exact overlay paths, canonical VM bytes, source
member sizes and aggregate source size. It executes no producer preparation
module and never reads historical raw CI locations. Each managed command checks
source, Rust tool hashes and Node identity before launch; independent source
and binary postflights preserve a primary failure. Formatting with a stable
roster retains the exact 15 before/after files, diff and closure identities.
Subsequent commands use that observed formatted tree.

Node policy B is implemented: one existing regular executable is resolved once
outside checkout and runner temp; real path, hash and filesystem identity are
frozen. A managed identity child records exact version and component data and
requires matching execPath/Linux/x64. The real path is passed as `MIXER_NODE`;
the private first-in-PATH `node` link covers the one hardcoded caller. Both are
checked before/after every managed command. The allowlist excludes Node options,
module paths, preload/library hooks, Rust wrappers and ambient flags.

Source review covered all nine ignored oracles in `differential.rs` (3),
`experimental_oracle.rs` (1), `float_differential.rs` (3), and
`table_memory_differential.rs` (2). Fixed nonempty case construction reaches an
unconditional Node spawn; missing executables, I/O errors and unsuccessful child
status panic/fail instead of silently skipping. The seven differential comparison
paths check result count and values; the mutation oracle checks reference
validation for accepted candidates; the experimental oracle executes a script
that rejects any fixture mismatch. No available-Node check or early success
return bypasses a reference call. Scripts use finite fixed fixtures and Node's
filesystem/WebAssembly APIs without process/network imports. Ordinary Rust
Command/wait_with_output launches have no session/group override, so normal
Node descendants inherit the managed Cargo group. Taken piped stdin is dropped
after the write statement; wait_with_output collects output and waits.

The helper starts a new managed session, refuses outliving descendants, kills
its own group on failure, and requires direct-child reap plus group absence.
Scratch cleanup checks evidence ownership and scratch identity; unresolved
custody preserves scratch. This is same-group custody only. Escaped sessions,
whole-provider disposal, individual Node reap receipts, explicit EOF/sink-close
flags and Node's internal pipe byte caps are not established. Shared libraries
and transient privileged replacement are not frozen by executable hashes.

The workflow is manual, read-only checkout, non-cancelling concurrency, fixed
Ubuntu/Rust version and finite step/job timeouts. Its Rust 1.99.0 provisioner
is a distinct two-minute workflow step; its installer descendants and output
are outside the six-child helper's custody/caps. Artifact retention is 30 days
and excludes scratch, including any scratch preserved on the runner by a
custody hold. Root's earlier guarded YAML-parser availability check found no
trusted parser. No dependency was installed or parser/tool subprocess run here;
workflow assessment is structural source review, not YAML/actionlint validation.

Two nonblocking limits were independently reproduced:

1. `format_evidence` rejects a changed source roster before creating its
   formatting receipt or retaining the 15 before/after files. The command
   receipt still records failed source postflight and binary postflight. If
   custody is resolved, outer cleanup can remove the scratch. The complete
   before/after retention claim therefore applies to stable-roster postflights,
   not every possible formatting failure.
2. `test_evidence` accepts appended contradictory `test result: FAILED` summary
   text because it scans only `ok` summaries. The actual command still requires
   exit zero, so an honest Cargo test failure is rejected. This parser is not
   independent proof against fabricated harness output. Tightening it would be
   defense in depth for the fixed trusted source.

Eleven independent guarded controls passed with zero live API attempts. They
verify frozen admission, exact bounds, environment stripping, private-link
directory injection refusal before launch, failed Node identity with both
postflights failing, strict Clippy refusal/diagnostic retention, partial
formatter failure retention, roster-change retention limits, and missing,
duplicate or ignored oracle rejection. Existing producer 27 host and eight
source controls were inspected and remain frozen; they were not rerun or
rewritten. The new controls are mocked/source evidence, never live custody or
compiler receipts.

Only this owned review directory was written. No local compiler, Rust, Node,
Swift, Elixir, product runtime, native/UI/capture, phone, process inventory,
held-process probe, Git/gh, dispatch, publication, credential or customer action
occurred. Pure scratch was removed. All stated local holds and FieldLog run
40802230894 PGID 2424/PID 2621 remain unchanged and unprobed. Root selection,
actual hosted execution, artifact interpretation and canonical integration
remain pending; native/physical/published-package FieldLog and GA gates remain
pending.
