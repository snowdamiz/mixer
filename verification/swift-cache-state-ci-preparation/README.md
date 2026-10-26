# Closed scalar-cursor cache-state CI candidate

This isolated candidate passes the exact selected three-file safe-File fixture
closure on actual Rust 1.99.0 / aarch64-apple-darwin.
Its final unchanged runner completed 103 owned commands in 178.658s
(active 175.417s; longest child 38.151s),
within fixed 600-second active / 60-second cleanup and 60-second child limits.
The source is unchanged f98f7801925bc280e0e2a9c08ec2b4841b7ffc2942d2fedf6c4d3b4c1796bf1b,
including its historical comments. The parent analyzer and envelope are exact.

The closed pack contains 86 members / 8,836,866 bytes, including 78 selected
source/fixture files (17 original source/oracles, 25 API sources, 34 historical
framing vectors/sidecars, two selected private control sources). Manifest
`6c52eb0ed737530d92011ce63e1eda593159c670b262a5f7bcf8b54b5338d857` and tree
`c2234a9107ac48bf6ecb7e20572a66d9b43d476a082d28348950f6b49f2eea7c` are pinned in the runner. No predecessor/failure tree
or historical runner is imported or executed. Existing framing/envelope CI
packs/runners/tests are unchanged.

Per Debug and optimized mode, fresh exact inventories execute 84 host, 108
producer, 98 inherited-independent, and 94 full derivative methods. Their
common overlap is 84; the base normalized union is 122. Three additional
producer private controls and seven independent methods bring the distinct
union to 132, with 384 method invocations per mode. The derivative copies all
17 exact source/oracle files plus two control sources and appends only the
fixed cfg(test) module declarations. All 94 derivative methods run, with zero
ignored/filtered tests. Exact 19-file derived source inventories match before
and after execution. Debug producer's 108 methods run as 17 exact named roots
(each 107 filtered) plus the 91-method embedded group (17 filtered), with disjoint
complete coverage. The original producer single-command 60-second timeout
remains failed historical evidence; grouped coverage is not performance equivalence.

Per mode all 25 API dispositions pass: two positive executions and 23 intended
compile refusals with all 38 exact primary source spans. The independently
predeclared API contract's two authoring expectation corrections are retained
in the independent lane; this pack pins its validated final probe bytes/contract.
All 23 complete accounting layouts match the fixed inventory, including the
488-byte aggregate and Result. Host and full derivative executions capture the
same 31 distinct exact File cases: 29 public cases (27 full32 plus two outer
errors without aggregate) and two private injected poison cases. Complete
result first lines and every input/report hash match. Dynamic input stamp
observations are retained as observed values. The ten added private methods
also check fixed finite output counters and independent complete layout values;
none grants general public File reachability credit.

Twenty-two focused runner controls pass. Every owned child/group returned,
all 14 final compiler products were hashed before deletion,
and owned scratch is absent. Verified content retention preserves test data and
errors by hash; commands retain raw stdout/stderr, exact argv, tool versions,
PID/PGID, source revision/tree, outputs and terminal exits. Pre/post checks bind
runner, interpreter and compiler launchers, actual compiler, full closed pack,
full derived sources and output identity. Caller compiler/test/scratch hooks
are scrubbed and RUSTUP_AUTO_INSTALL=0 is forced before launcher commands.
The scope assumes a quiescent trusted checkout and makes no adversarial custody claim.

The first candidate failed before inherited API compilation because a fixed
probe identifier contained a slash in an owned command/product name; raw
failure and the exact failed runner are retained under runs/rust-1-99-attempt1.
The corrected complete success runs/rust-1-99-attempt2 is superseded by stricter
source/output/negative-child checks. The first final invocation passed all
fixture checks but remains failed because root changed HEAD/tree during it;
runs/rust-1-99-final preserves this checkout-identity failure. Root then held Git
mutations and the unchanged final runner passed under runs/rust-1-99-final2.
No engine or pack source changed between these attempts.

This candidate is now ready for fresh independent runner review. Rust 1.98.1
remains pending; no toolchain installation or fallback search occurred. The
source feature prerequisite slice::as_chunks stabilized in Rust 1.88 per official
documentation, but that is not a whole-closure compiler qualification.
Canonical CI integration/workflow placement is not selected. Root must reserve
the full eleven-minute allowance in the chosen 30-minute job and assess actual
job timing (current Swift core about12m24s incl checkout; capability about18m30s).
No source-work/logical-lifetime proof is newly measured here; root's conditional
source model remains separate from compiler ABI/stack/allocator/RSS claims.
No arbitrary public File admission, live VM/target, native runtime/UI/capture,
phones, signing/store, immutable published-package separate-repository FieldLog,
customer/operational or GA gate is qualified. Phones remain disconnected and
native runtime/UI/capture remains paused.

For read-only closure verification run python3 -B verify_seal.py. Never replay
writing runners/builders inside this frozen packet. For independent actual
execution, copy only exact check_cache_state.py and the complete pack directory
to a separately owned directory under the same original repository, and create
an empty runs directory there. Supply the existing actual compiler path and a
fresh output directly under that copy's runs directory. No pack/hash/readiness/
budget/expectation override exists. The runner derives ROOT as HERE.parents[1];
for a nested owned copy that may be the original repository's verification
directory. The four git rev-parse commands remain read-only and discover the
same original Git checkout through parent directories. Do not initialize,
modify, or replace Git, and do not bypass before/after checkout identity checks.
Coordinate a quiescent repository with root for the complete invocation.
