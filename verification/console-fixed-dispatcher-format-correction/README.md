# Dispatcher formatter correction

The Phoenix job for commit `d04fd5cc71bc72061f18203e414b90869129b4ca` failed at `mix format --check-formatted`, before application compilation or tests. The original failure is preserved in `remote/original-phoenix-failed-log.stdout`; the exact remote artifact members are `remote/ci-format.log`, `remote/ci-elixir-version.log`, `remote/ci-revision.log`, and `remote/ci-receipt.json`. Run: `40567963706`; job: `122414195493`; artifact: `12764551723`. The archive was read in memory and discarded after extracting those exact four members. The initial basename-only metadata extraction error is explicitly superseded by `commands/remote-artifact-download.json`.

The installed Homebrew Elixir/Mix 1.20.4 formatter, running on Erlang/OTP 29 with two schedulers and one async thread, changed exactly the four files named in the remote formatter log. The two other dispatcher product files were already formatted. All six explicit inputs pass the formatter check. All six before/after files parse and produce exactly equal ASTs after removing parser location metadata; all forms, arguments, and literals are preserved. `git diff --check` also passes. See `receipt.json`, `ast-equivalence.json`, `source-before.json`, `source-after.json`, and the captured command records/output under `commands/`.

The exact formatter command was run from `hosted/`:

```sh
env ERL_FLAGS='+S 2:2 +A 1' /opt/homebrew/bin/mix format --dot-formatter .formatter.exs \
  lib/mixer_hosted_web/browser_workspace_dispatcher.ex \
  lib/mixer_hosted_web/browser_workspace_dispatcher/capture_adapter.ex \
  lib/mixer_hosted_web/browser_workspace_dispatcher/request.ex \
  test/mixer_hosted_web/browser_workspace_dispatcher_capture_adapter_test.exs \
  test/mixer_hosted_web/browser_workspace_dispatcher_request_test.exs \
  test/mixer_hosted_web/browser_workspace_dispatcher_test.exs
```

The check uses the identical explicit file list plus `--check-formatted`. `.formatter.exs` has only `inputs`, with no plugins or imported dependencies; the project has no `format` alias. Installed launcher/formatter hashes and unchanged project inputs are recorded in `tool-and-formatter-closure.json`. The one-shot `run.py` collector verifies the original preimages before formatting, so it refuses to overwrite an already formatted checkout. `before/` preserves the exact six preimages and the unchanged formatter/project/dependency configuration.

The protected working-tree bytes of `.github/workflows/hosted.yml` and `hosted/lib/mixer_hosted/browser_auth/store.ex` remain equal to their captured prehashes. This packet does not alter any earlier producer or independent-review packet. Every owned command group is absent after completion, as recorded by direct group probes in `cleanup.json`; no global process inventory was taken. No services, persistent scratch directory, native instances, capture, or UI automation started.

This receipt establishes a formatting correction and parsed program equivalence. Behavior tests were not rerun for this whitespace-only change; the previous producer/independent test results remain historical. Application compilation, PostgreSQL/Repo harness execution, new remote CI, and production acceptance are outside this correction. The new remote CI result remains pending delivery. Phones remain disconnected, native runtime/computer-use checks remain paused, and no GA gate or release is qualified here.
