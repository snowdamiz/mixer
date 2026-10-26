# Closed cache-state fixture workflow proposal

This packet proposes one additional independent `swift-cache-state-fixture` job
for `.github/workflows/verify.yml`. It is preparation only. The corrected runner
has not been read or accepted by this lane, and no canonical file was edited.

`proposed.verify.yml` is the original workflow's exact byte prefix followed by
`job.yml`. The original five jobs and all 40 step objects are parsed identical.
The top-level events and permissions are unchanged. `baseline.json` binds the
original workflow and checkout revision/tree at preparation time. Root must
rebase this additive proposal if the canonical workflow changes before selection.

The new macOS 15 job uses a depth-one, non-cone sparse checkout containing only
`/verification/swift-cache-state-ci/`. This directory must contain exact accepted
`check_cache_state.py`, `test_runner.py`, and the complete closed `pack/` tree.
The runner's existing `HERE/pack` and `HERE/runs` layout then needs no runner
source change. Its read-only Git HEAD/tree queries do not require full history
or independently pinned native sources. The job creates fresh owned `logs/` and
`runs/` directories. `proposed.gitignore` is intended as that directory's
`.gitignore`; its two anchored rules ignore only those generated outputs.

The focused step runs the whole accepted `test_runner.py -v` suite, expected to
contain 28 focused controls after independent acceptance. This workflow packet
does not itself establish that accepted suite count. The next step passes the
explicit result of `command -v rustc` to `--rustc` and a fresh direct child of
`HERE/runs` to `--out`. `RUSTUP_AUTO_INSTALL=0` is forced for the job. There is no
installation, fallback search, `+toolchain` argument, or `RUSTUP_TOOLCHAIN`
override. The accepted runner must resolve the existing launcher's actual
compiler and admit only stable 1.98.1 or 1.99.0 on aarch64-apple-darwin with all
fresh obligations. An unavailable or unsupported default compiler fails the
job; image/compiler availability has not been qualified by this lane.

The runner retains its fixed 600-second active, separate 60-second cleanup, and
60-second child limits. A 12-minute enclosing step leaves one minute of overhead
beyond that full eleven-minute runner allowance. Focused controls have a separate
three-minute step cap, preparation two minutes, and upload five minutes. The
outer job cap is 30 minutes. The existing Swift core job was reported by root as
about 12m24s in the earlier observation and about eleven minutes in the latest
observation, with checkout variation. Those observations are historical context,
not a new timing measurement here. An independent shallow job avoids adding
the full eleven-minute runner allowance to the existing shared core job's
30-minute budget. Checkout, scheduling, compiler availability, and artifact
upload timing remain subject to actual Actions execution. No additional
compiler invocation is silently added to the runner allowance.

The final upload uses `if: always()`, retains the complete candidate directory
including hidden inputs, source, logs, and all run evidence for 14 days, and names
the artifact with commit, run ID, and attempt. This also retains evidence on
earlier step failure. `if-no-files-found: warn` makes a missing directory visible.
An Actions job hard timeout or infrastructure cancellation can prevent an upload;
the workflow is not an artifact-durability guarantee. No `needs`, retry, or
`continue-on-error` behavior is introduced.

Run `python3 -B verification/swift-cache-state-ci-workflow-review/test_workflow.py -v`
from the original checkout for structural and shell-behavior checks. The tests
use local Ruby/Psych and inert recorder scripts in owned temporary directories;
they do not run any candidate fixture/compiler or native runtime. They verify
byte and parsed preservation, the exact sparse inputs, output paths, step caps,
launcher argument, raw success/failure logging, rejection of existing outputs,
and complete always-on artifact retention. This is not an Actions execution,
runner-source review, compiler qualification, or OTA authorization. The source
runner's exact 28-control suite, full closed invocation, final independently
accepted source seal, and actual CI result remain root's integration gates.

No native runtime, simulator/emulator, UI, capture, physical phone, signing,
store, production publication, customer/operational, separate-repository
immutable FieldLog package, or GA qualification is claimed. This lane started
no such processes. Its temporary shell probes are removed after each test,
including failure probes. Other projects' processes were not inspected.

Run `python3 -B verification/swift-cache-state-ci-workflow-review/verify_seal.py`
to verify the sealed proposal without executing a writing runner. The seal binds
every packet file except the seal itself. Its exact bytes are frozen for review;
copy selected source files out of this packet before adapting them.
