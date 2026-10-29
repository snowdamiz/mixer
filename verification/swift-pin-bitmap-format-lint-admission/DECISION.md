# Formatting and lint proposal

This is a source-only proposal for one manual GitHub-hosted diagnostic. Root
review and explicit selection are pending; no workflow is installed or dispatched.
It unlocks review of the exact formatter delta and Clippy findings before any
canonical VM installation. The independent lifecycle regression remains a
separate selected test sequence; this proposal neither changes nor runs it.

The input builder is the exact hash-bound lifecycle admission materializer. It
verifies all 60 frozen packet members, all 136 canonical VM baseline members,
the public/contract bindings and the exact four-overlay corrected composition.
The input closures are baseline
`af0db424af7b08f013d2c6a8894f4d156f76bc5f493620c6f2c0b85d3bf4c48b`
and corrected candidate
`674242606ec1f81e8bf53d6d10c0ae390c94c75e78d0a5c0e695bfb36b5eec20`.
The lifecycle packet seal remains
`b3b502ab5027615d1ff6bcb396f893554407e7f4f983ca89c2e3a499b4291ab6`.
Raw actual-CI paths and local dirty hosted.yml/store.ex preservation anchors
are never opened as hosted inputs. No frozen producer tests are imported.

One existing-host rustup step installs exact Rust 1.99.0 with its standard
rustfmt and Clippy components, minimal profile, into the job's fresh explicit
RUSTUP_HOME. This ordinary two-minute provisioning step is outside Commands:
installer/descendant custody, its command-output cap and provider disposal are
not established by this proposal. The five managed children use fixed absolute
toolchain binaries. The identity child verifies rustc release and host; the
receipt hashes rustc, rustfmt, cargo, cargo-clippy, clippy-driver and the installed
component manifest. Separate rustfmt/Clippy version strings are unavailable
under this five-child allowance; hashes and exact co-installed toolchain
selection are retained. This is not independent toolchain provenance proof.

The five managed children, in order, are compiler identity, baseline rustfmt,
candidate rustfmt, baseline Clippy and candidate Clippy. Each arm uses a complete
fresh materialized source, separate fresh Cargo home, target directory and HOME;
temporary paths remain under marked owned scratch. Both sources are checked
before and after every command, including command exceptions and pre-spawn
refusals. Cargo is locked, offline and incremental-disabled; ambient Rust flags,
wrappers, loader hooks and Cargo configuration are excluded. Inherited Cargo
and Clippy configuration is refused. CLIPPY_CONF_DIR selects the fresh arm HOME.

Standard rustfmt receives edition 2021, file output and one explicit config file
containing only that edition. Exactly these four paths are passed in each arm:

- `src/experimental/cache/borrowed.rs`
- `src/experimental_swift_reactor/cache.rs`
- `src/experimental_swift_reactor/cache_tests.rs`
- `src/experimental_swift_reactor/lifecycle_tests.rs`

No whole-crate cargo-fmt command, style override, formatter suppression or
unrelated formatting is selected. Before/after copies of all four complete files,
per-file hashes, complete source closure hashes and unified diffs are retained
for each arm. Added/missing source files or any changed path outside those four
fail admission. Formatted source becomes the immutable input for that arm's
Clippy command; formatting does not authorize a semantic source change.

`vm/README.md` already prescribes Clippy `--all-targets -- -D warnings`. Both
arms preserve this warning policy and add identical `--all-features`, `--locked`,
`--offline`, `--message-format=json` settings. No lint is allowed or suppressed.
Cargo exit 101 is retained as a failed lint/compile result only when its complete
JSON stream has exactly one false build-finished and an error diagnostic. After
verified command custody, that known baseline result may advance to the
independent preselected candidate comparison. It is never counted as a lint
pass. Compilation errors remain visible alongside lint errors. Unknown exits,
malformed/incomplete diagnostics, timeouts, caps, postflight or custody failures
stop the sequence; there is no retry or weakened-policy fallback.

Full stdout, stderr and compiler-message JSON are retained. A supplementary
multiset comparison groups code, level, message and source filename while
ignoring line-number shifts caused by formatting. It reports shared,
baseline-only and candidate-only diagnostics with multiplicities. Candidate-only
does not claim semantic causation. Both individual lintPassed values remain
explicit even if the diagnostic workflow successfully collected two failures.

Caps are five managed children; 30/30/30/300/300 seconds (690 summed); 900 active
seconds plus 60 cleanup; 8 MiB per stream; 32 MiB aggregate child output. The
driver step is capped at 17 minutes, leaving startup margin beyond the internal
16-minute active/cleanup allowance; the entire workflow is capped at 25 minutes.
Source members are capped at 16 MiB each and 64 MiB per materialized tree. These
are diagnostic limits, with no production resource-default change. The copied
reviewed Commands helper changes only these finite policies, adds a bounded
0/101 exit set and counts aggregate retained output. Its existing direct-child
reap, owned-group checks, retained command logs and failure cleanup stay intact.
These receipts do not independently prove reaping of every nested compiler
child. A live command-custody uncertainty preserves the complete owned scratch.
No process inventory or unrelated-group probe is used.

All 26 guarded source/filesystem/mock controls pass with no real nested process,
session, group, signal, wait, socket or resource calls. They cover exact inputs,
argv, isolation, formatting artifacts and scope, JSON/comparison failures,
both-arm postflights, known baseline failure continuation, timeout/cap stops and
scratch preservation under unknown custody. Mocked custody is not live evidence.
Every disposable pure-test scratch directory was removed.

No Git/gh, installation, Rust/Swift/Elixir compiler, formatter, Clippy, product
runtime, native/UI/capture, process inventory or held probe ran locally. Only
this new verification directory changed in this lane. Protected dirty
hosted.yml/store.ex/.wrangler and every local hold stay unchanged. Remote
FieldLog 40802230894 PGID 2424/PID 2621 remains held without probes, signals or
disposal assumptions. Actual formatting/lint and review of their exact results
remain pending, independently of semantic regression, production defaults,
canonical installation, native/phone/published-package FieldLog and all GA gates.
