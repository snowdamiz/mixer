# Hosted selected-test discovery correction

Phoenix CI run `40211210237` for `7e434330cad8e3566a4a21a6d7ff996da3bc4967`
completed with **615 passed, two skipped**, then failed under
`mix test --warnings-as-errors`. The [retained CI log](../verification/github-delivery-browser-lifecycle/phoenix-ci-tests.log)
has SHA-256 `043646ad2f5b60b57fb12bce2aa00a7c107e7935796fe8e1c1d5256917f35936`.
The four selected PostgreSQL-runner files were potential tests that matched neither
Mix's default test loader nor an ignore filter:

- `test/mixer_hosted/authorization/jit_policy_spec.exs`
- `test/mixer_hosted/browser_auth/migration_spec.exs`
- `test/mixer_hosted/browser_auth/storage_fixture.exs`
- `test/mixer_hosted/browser_auth/storage_spec.exs`

`hosted/mix.exs` now lists those four exact project-relative paths in
`test_ignore_filters`. No glob or directory-wide exclusion is added. The default
test pattern, `_test.exs` loader, helper/support treatment and warnings-as-errors
behavior remain selected. The existing isolated PostgreSQL runners continue to
load their explicitly selected files.

## Fatal warning diagnosis

The primary evidence is the installed **Elixir/Mix 1.20.4**, compiled with
**Erlang/OTP 29**; execution used OTP 29 / ERTS 17.1 on this Mac. The runner
retains `mix help test` and extracts the relevant official Mix implementation
from the installed BEAM abstract-code chunks, including module paths, BEAM
SHA-256 values and compile metadata. It does not load hosted dependencies,
application modules or tests.

`Mix.Tasks.Test.classify_test_files/3` first applies the load filters, then ignore
filters, then warns for every remaining file. String filters use exact equality.
`get_test_ignore_filters/2` prepends Mix's built-in `_helper.exs` and
`elixirc_paths` predicates to the configured list. The correction therefore needs
only the four exact paths; copying or replacing those built-in predicates is
unnecessary.

`Mix.Tasks.Test.do_run/3` includes a nonempty set of unmatched files in its
warnings-as-errors abort condition after successful tests. The isolated baseline
reproduces that failure with all four paths, one passing ordinary test and no
module-redefinition warnings. This proves the discovery warning is sufficient to
cause the observed terminal CI failure.

The CI log also contains 57 runtime migration-module redefinition warnings.
`Mix.Compilers.Test.require_and_run/3` captures test-load compiler diagnostics
before awaiting ExUnit completion. A separate synchronous test emits a real
runtime `Code.compile_string/1` module-redefinition warning and exits successfully
under warnings-as-errors. Another control emits a load-time compiler warning and
fails. These controls distinguish the two warning classes; the migration warnings
are preserved, and no suppression of compiler warnings is added.

## Executable verification

Run from the repository root:

```sh
python3 verification/hosted-selected-test-discovery/run.py
```

The runner evaluates only `MixerHosted.MixProject.project/0`, asserts the exact
four-path configuration and unchanged default loader/pattern, and transfers the
actual discovery settings plus alias to dependency-free temporary Mix projects.
Each case executes a fresh `mix test --warnings-as-errors --seed 0 --no-color`
with `MIX_ENV=test` and bounded Erlang schedulers. The real hosted alias supplies
`--no-start`. Every case asserts that an ordinary ExUnit test actually passed.

| Control | Required result |
| --- | --- |
| Four selected files before the correction | Discovery warning, one test passes, exit 1 |
| Exact four exclusions plus default helpers/support | One test passes without warnings, exit 0 |
| Unknown sibling `browser_auth/future_spec.exs` | Still warns and exits 1 |
| Typo `ordinary_tests.exs` | Still warns and exits 1 |
| Unknown sibling `browser_auth/future.ex` | Still warns and exits 1 |
| Test-load unused-variable compiler warning | Still warns and exits 1 |
| Synchronous runtime module redefinition | Real warning, passing test, exit 0 |
| Explicitly selected otherwise ignored file | Test still executes, exit 0 |

The runner records exact command arguments, working directories, selected
environment, tool versions, exit status, stdout/stderr and hashes, source revision,
selected source hashes/tree digest, historical CI-log binding and owned cleanup.
Receipts are written under
[`verification/hosted-selected-test-discovery/attempts/`](../verification/hosted-selected-test-discovery/attempts/).

The first local attempt failed in the verification fixture itself: its support
tripwire was accidentally named `not_a_test.exs`, which correctly matched the
default test loader. Renaming that tripwire to `non_test_support.exs` corrected the
fixture. The subsequent eight controls pass. Both attempts remain as evidence;
the failed attempt is not product acceptance. A later rerun binds the committed
CI-log copy above so the runner does not require the untracked downloaded artifact
directory. The [final producer receipt](../verification/hosted-selected-test-discovery/attempts/20261025T163528.110910Z/receipt.json)
passes all eight controls, binds the working source tree digest
`31b835bb0f19345c27631f9b90b958cf95f78cc2adf28b9a1f0d6b925e31b6dd`
under revision `7e434330cad8e3566a4a21a6d7ff996da3bc4967`, and confirms that
the selected sources remained unchanged and all owned temporary projects were
removed.

## Scope and pending evidence

This is a host-only discovery configuration correction. It does not rerun the
whole Phoenix suite or its PostgreSQL fixture, and it does not establish
exact-push CI success. The two CI skips remain skips. The temporary Mix projects
and their build products are removed after each attempt, including failure.
No database, browser, capture, simulator/emulator, native application, frozen
hosted catalog-inspector/authority-driver or rejected outbound Worker transport
V2 lane is loaded or executed. Provider, operational, customer/FieldLog and GA
acceptance remain pending; paused browser/native runtime checks remain pending.
