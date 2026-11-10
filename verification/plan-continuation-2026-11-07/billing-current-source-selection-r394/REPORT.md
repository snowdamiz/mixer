# R394: reviewed billing composition and current identity source selection

The isolated integration is ready for root review and application. `combined.patch` contains exactly 19 application files; `application-map.json` records each operation, expected before/after length and SHA256, and purpose. `afterimages/` contains those exact resulting bytes. A fresh baseline application of that patch matched all 19 afterimages, preserved 303 other copied inputs, and passed actual current-source admission. Canonical files and all 313 original input hashes remain unchanged. No root Git command, canonical write, remote mutation or subchild was used.

The patch SHA256 is `3ddbadbab5d67ed0a54c6b8c88cd45f139a0c385b1f5f35d20901401798ab7c7` (109,087 bytes). Root owns review, integration, project-index updates and fresh ordinary CI. Qualification remains **false**.

## Source authority and binding

R382 correctly located authority in the compiled collector and its immutable 178-source v2 amendment. This integration preserves `FROZEN_MANIFEST`, `SELECTED_SOURCE_DIGEST`, all other historical constant values, all 131 historical metadata files, the historical source/metadata validators, and their existing accepted verdict. The old gate still accepts its exact 178 members and refuses the current 185. No historical digest or contract packet was refreshed.

The explicit successor is `current-hosted-r338-r325-r354-r394-v1`, at `verification/identity-network-current-source-v1/selection.json`, with:

- Selection SHA256: `14868be39631a86c79f4ba7b6bfb9386c6d80062ef4d0ddebbf55aea833afc96`.
- Current product count: **185**.
- Current product manifest digest: `07bb7b5d7b518f487e4981dc4aa0e911f16c99a5bbbf96ea0bdc204d9455ccd9`.
- Exact 13-row delta against historical v2: seven reviewed billing additions, and six existing test fixtures (foundation, test helper and four build fixtures). The coordinator delta also retains the already accepted R338 regression.

The successor selection's exact bytes are independently pinned in the collector. Its full manifest is bound by that pin and the compiled current digest/count. Caller-selected digests, changed locks, missing/foreign members, modified metadata, and an untrusted manifest attempting to authorize itself all refuse. Future product changes require an explicit successor selection; collection cannot automatically recompute authority.

The workflow includes the new metadata in its triggers and sparse checkout, then executes `--check-source` before inert controls and the unchanged network command. That pure preflight reads actual selected source files without Git, Docker or network activity. Runtime still binds exact delivered Git blobs to current authority, validates both historical metadata and the new selection before any Docker operation, archives the selected source, supplies the current manifest helper, checks preparation and archive membership, compares restore/compile/final input manifests, and compares the database migration versions to the pinned current members. Existing image, bootstrap, resource, namespace, custody and two-method network contracts remain unchanged. The existing runtime archive/compile gates now use the explicit current source validator; historical source and amendment validators remain byte-identical.

## Billing and fixture composition

All seven R325/R354 additions exactly match their reviewed afterimages. The admission patch remains `8ce95ff7c43fadca86118761cccc06e4b0042eefdc17b0e93ab3aee3d5b2645f`; the route patch remains `31b79e4a834793e792073fbed3393a3cba1cfe0a58c77d2b2f068112b8797d13`. R343 and R380 acceptance is reused for unchanged billing code. All existing production application, authorization, build, configuration and lock inputs remain byte-identical.

The private POST `/api/v1/webhooks/stripe` contract is unchanged: no query; server-only configuration; invalid configuration returns 503 before capture; ambient transactions refuse; successful acknowledgment follows its own committed transaction; ordinary API remains unmounted. Only test workers ran. A real reconciliation worker, provider client, trusted customer-to-tenant binding and billing-state/usage integration remain pending. There is no production default worker or successful no-op implementation.

`MixerHosted.Test.Migrations` in the existing `test/test_helper.exs` now owns the exact eleven reviewed migration filenames/versions from R354. Full-migration foundation/storage/admission/aggregate/coordinator setup uses that one list, rejects missing or foreign migration filenames before execution, and checks the exact newly applied versions. No copied fixed eleven-count assertions were introduced. The foundation test executes extra/missing-file refusals. Aggregate's targeted down/up test still asserts each explicit version and its negative/state invariants, with billing included and eight rollback steps.

The R338 regression body and assertions are byte-identical, SHA256 `b46e4277958d97064c44991586d0bc13181eac68076891680f6e79102f9eb772`. Only its containing file's migration setup changed. Its real completion-versus-lease-replacement and tenant-isolation regression passed in the combined run.

## Executable results

`commands.json` records argv, cwd, PID/PGID, timeout, duration, exit and raw log location. `tested-source.json`, `preservation.json`, `selection-identity.json`, `application-check.json` and `result.json` identify the exact inputs and conclusions.

- `logs/combined-hosted-r3.log`: **160 passed**, exit 0, seed 0, trace and `--warnings-as-errors`. This single combined selection covers the reviewed admission/signature/transport and product route, five foundation tests including membership refusal, build storage/admission/aggregate/coordinator, and lifecycle/journal regressions. It includes real PostgreSQL, atomic writes and rollback/retry, delayed synthetic worker execution, durable HTTP acknowledgment, outer COMMIT failure, replay/conflict, trusted scope/configuration refusals, R338 and aggregate migration rollback/reapply.
- `logs/collector-normal-r2.log` and `collector-optimized-r2.log`: **147 passed in each mode**, including the existing 141 controls and six new current-authority controls. These are repeated runs of 147 unique controls, not 294 unique tests. A simulated corrupt current selection is refused before any Docker call.
- `inert-normal.json` and `inert-optimized.json`: **25 additional controls pass in each mode**, with child/shell/socket operations denied. They check actual 185-file admission, current/historical separation, mutant refusals, exact accepted billing bytes, historical constants and validator preservation, unchanged production source, and the exact R338 body.
- `logs/applied-source-preflight.log` and `application-check.json`: the delivered patch applies to a fresh copied baseline, reproduces exact afterimages, and admits the same 185-file identity.

Tools: Python 3.14.8, Elixir 1.20.4, OTP 29, PostgreSQL 17.11 on Darwin 27 arm64. Tool/version and initial format probes used four BEAM schedulers. Compilation and combined tests used **three** (`ERL_FLAGS=+S 3:3`) after the aggregate-contention instruction; no all-core build was launched. Locked dependencies were copied into isolated source/cache paths from accepted R380, and only the installed local Hex 2.5.1 archive was copied into owned MIX_HOME. No dependency-fetch command was invoked.

The raw final combined log retains **14 Oban notifier configuration error messages** about a missing Repo database option in existing build test fixtures. Their domain/job and lifecycle assertions pass; this run does not qualify notifier delivery or recovery. Initial cold dependency compilation also retains third-party xref deprecation warnings. Neither limitation is hidden by the zero-exit test result.

## Preserved failures and cleanup

The first driver attempted the additional inert script before it existed and recorded exit 2; `logs/inert-normal.log` is retained. An initial helper import refused an existing source directory before any integration write; its entrypoint guard was corrected. The first database attempt reached Mix but had no isolated Hex archive and ran no tests. The second recorded **148 passed, 12 invalid** because the runner omitted the admission fixture's separate `MIXER_BILLING_DATABASE_PORT`; its complete log remains. The final attempt used a separate fresh cluster and supplied both port variables. These earlier outcomes are not passing evidence.

All three owned clusters bound only to loopback with UNIX sockets disabled. Each exact-directory stop exited 0, each subsequent status exited 3/no server running, and every postmaster PID file is absent. `owned-cleanup.json` records all three; inactive data and raw logs are retained. Test BEAM commands exited; no descendant-absence claim is inferred from direct command exit. No held process, held namespace, device, signing resource, credential, provider, deployment or production resource was inspected or operated on.

The named unlock is now concrete: after root review/application, fresh ordinary identity CI can admit the explicit current source and execute its unchanged network test command. No Docker or network collector was launched here. Fresh identity runtime results, full hosted-suite coverage, provider reconciliation, deployment and GA acceptance remain pending.

Scope deviation: the initial filename-discovery command was broader than necessary and listed unrelated nested verification filenames outside the hosted domain, although it excluded the root `verification/` tree. No contents at those unrelated paths were read. Subsequent discovery/read operations used exact named inputs or bounded hosted source paths. The initial enumeration is not claimed as compliance with the task’s no-broad-verification-scan instruction.
