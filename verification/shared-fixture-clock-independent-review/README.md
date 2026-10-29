# Independent review: ordinary fixture mocked clock

**Decision: ready for root adoption and fresh remote ordinary-job execution.**
No actionable findings. This is a source and guarded mocked-control review,
not a completed remote fixture or acceptance gate.

The reviewed correction is bound to candidate seal SHA-256
`2c4b7f295d275694b5541113f17f0e9216a073a864b01b95b0078632d4145d71`:
16 members, 92,848 bytes. Independent closure verification passed. The original
123 dependency rows are byte/hash unchanged; exactly the original adoption's
13 sealed members plus its seal are added, giving 137 dependencies. All are
covered by the proposed sparse checkout. The three copied adoption files are
byte-identical. Compiler and fixture policy objects are unchanged, and the
runner reuses the exact ordinary compiler-validator function and its globals.

The effective source differs only by `c.deadline=clock.monotonic()+20` in
`accounting_row`, before the original timeout side-effect assignment. The exact
original 27,413-byte preimage and corrected source hashes verified. All 36
original test method names and AST bodies match. Intercepting only
`unittest.main` while executing the actual wrapper in an actual `__main__`
module discovers 36 methods. Its `__file__`, `HERE`, imported runner path and
compiled test filename remain at frozen v2. The source-only helper insertion
preserves the original optimized-child cwd, retention destinations and teardown.

The workflow is exactly the frozen original job with only the sibling adapter
path, runner-control route, sparse-checkout entry and archive entry changed.
The sequential 16 adoption, nine materializer and 36 original runner controls
still precede the sole complete 103-command fixture. Installed-job equality,
source pre/postflight, existing Rust launcher/identity policy,
`RUSTUP_AUTO_INSTALL=0`, 60/600/60-second limits, 8 MiB per stream, always-run
postflight and hidden-file-inclusive 14-day archive remain intact. Canonical
workflow was still the original job when the review ran; root owns installation.

The independent executable added only four boundary timeout checks and one
in-memory ordering mutant; it did not repeat the producer's 16 adoption controls
or its full low/high four-control matrix. At host origin 80.0, the baseline has
zero remaining synthetic budget and creates no receipt; the corrected source
passes the original timeout method. At 80.5 both pass. All passing rows retain
`timed_out=true`, elapsed 1.0 seconds, effective timeout 0.5 seconds and the exact
original CPU delta. Moving the reset after side-effect assignment exhausts the
timeout sequence with `StopIteration`, so the negative mutant is rejected.

Command, Python version, input hashes and observations are in `summary.json`;
`checks.json` binds the successful command's output and executable source.
Actual process/session/group/signal/timer/wait/socket operations were denied or
mocked before subject imports. The filesystem guard confined new writes to this
review folder, including teardown through tracked directory descriptors. There
were zero denied operation attempts, and owned scratch was removed. Raw output
and expected negative tracebacks stay in ignored `logs/`.

The source explains a clock-domain defect; the failing remote host's actual
monotonic origin was not retained and is not asserted here. Engine
40810235312/revision `836fc67b` history and the producer's broader local results
were reviewed as supplied frozen evidence, without Git or GitHub calls. No
original full-36 local run, compiler, fixture, product/native runtime, UI/capture,
process inventory or held-process probe ran. The remote 16+9+36 controls,
103-command fixture and installed-job pre/postflight remain pending. All
physical-phone, native/UI/capture, custody, Unit A, hosted and GA holds remain;
this review grants no release, publication, dogfood or GA authority.
