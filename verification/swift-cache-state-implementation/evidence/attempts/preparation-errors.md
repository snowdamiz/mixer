# Preserved preparation and coordinator failures

These are explicitly incomplete authoring attempts, not passes. The initial
interactive tool outputs are retained here as transcript excerpts/summaries,
not mislabeled as full raw per-command stdout/stderr. All final commands use
separately retained raw stdout/stderr/exit/PID/PGID/source bindings.

1. The first interactive tool probe used `rustc` on PATH and returned127:
   `zsh:1: command not found: rustc`. The actual installed absolute Rust1.99.0
   toolchain was then selected and its verbose identity retained.
2. The first old embedded-test compilation found the copied closure incomplete:
   `couldn't find file .../tests/selected_tests.rs`. The exact admitted old source
   was copied. The next compile found `../focused_controls.rs` missing; the next
   found `../inputs/oracle-425.bin` and `oracle-budget-425.bin` missing. Those exact
   immutable old inputs were copied and subsequently hash-audited.
3. The first66-method run passed62 and failed four old methods because their
   required scratch/historical environment variables were absent. No expected
   values were changed. The runner was corrected to provide owned scratch and
   the admitted immutable historical footer-only inputs. Later full closures pass.
4. The private fault control initially omitted its envelope-call counter
   insertion. Both compiler modes failed the expected count (observed0 versus8).
   Full raw stdout/stderr/receipts are in `fault-counter-before-correction/`.
   The actual envelope call counter was inserted and all controls rerun.
5. An attempted helper-layout insertion script matched an obsolete formatting
   substring and raised `ValueError: substring not found` before modifying its
   target. The insertion was then applied to the actual formatted source and
   fresh helper layouts are present in the final test receipts.
6. The initial final coordinator applied60 seconds to the whole regression script,
   which includes a roughly53-second debug producer run plus later independent
   and optimized commands. Python raised `subprocess.TimeoutExpired` while the
   next owned host Rust child was active. That interrupted multi-command run is
   incomplete, never passed. The root-authorized one anchored child lookup and
   disappearance-only result are in `interrupted-coordinator-owned-child.json`.
   Its output exit was not observed or invented. The wrapper was replaced by
   same-process serial orchestration and per-command PID/PGID-owned deadlines,
   output caps and group cleanup. Current final receipts belong to that corrected
   coordinator, and removed partial artifacts are in `pre-final-owned-cleanup.json`.

No accepted source-contract packet, immutable old pack, independent preaccess,
live VM, native/runtime/capture process or unrelated project was changed by
these corrections. The three partial-paid flag exclusions have zero runtime
pass credit throughout.
