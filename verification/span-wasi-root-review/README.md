# Root integration review: cached execution and standalone WASI

The final combined host matrix (`combined-2/receipt.json`) passes 244 tests in
each Debug and Release configuration, followed by all nine explicitly selected
development reference checks per configuration. Focused Clippy with warnings as
errors and formatting pass. The complete current VM source manifest and every
command output are bound in `receipt.json`; `seal.py` checks those bindings.
The earlier combined-1 logs preserve a regression-test lint and formatting failure,
both repaired before final validation.

The new Rust-only executor consumes its sealed function cache, owns bounded
mutable memory/table/globals and live frame/control/value arenas, pins decoded
functions only while live, preserves typed source failures and keeps lifetime
fuel/work/host budgets. No mutable cache/memory or arbitrary host callback escapes.
Independent review found a constructor diagnostic error for a consumed pre-pinned
cache. Root repaired the current pin count after destruction, while preserving
the attempted count. Four independent probes then pass in each mode. Original
failing source and logs remain available.

The separate WASI adapter resolves exactly the selected 34 Preview1 signatures,
requires explicit native grants, uses private OS entropy/clocks, validates guest
ranges and aliases before writes, bounds captured output, and fails unsupported
operations closed. It has no VM admission or execution connection. Its owner
suite passes 18 tests per mode, including construction allocation failures and
allocation-free dispatch. Six independent external-consumer probes pass per mode,
including 1,156 argv pointer pairs and 66 write-output offsets. All six adapter
source/test files match the independently reviewed receipt.

Existing frozen profile limits, import admissions, native ABI, signing/update
routes and package pins remain unchanged. CI now explicitly includes both new
features with the existing streaming/cache/native checks. This local result does
not establish hosted Linux behavior, full Swift reactor execution, total session
RSS, mobile performance, release provenance or GA. Physical phones remain
unavailable and were not queried. The next full-Swift stage requires an explicit
separate policy/proof identity and complete validation before execution.
