# R426 usage ledger and current source composition

The isolated composition is ready for root adoption. It combines the exact four
reviewed R398 files with the locally installed R394 billing source. The combined
PostgreSQL run passed 177 tests, including the unchanged 17 ledger tests. A
separate migration test passed under an unprivileged schema owner. Both normal
and optimized Python passed 153 collector controls. Qualification remains false.

Root owns canonical application, project-index updates, delivery and ordinary CI.
This task made no canonical write, Git operation, remote mutation, device action,
signing action or child delegation. All writes stay in this R426 directory.

## Application artifacts

`incremental.patch` changes 15 files from the current canonical state with R394
installed. Its SHA256 is
`4f039b9fdeb8736e9772911f260205ef67f483bd03905cec4985639abe66b16d`.

`full.patch` changes 29 files from R394's exact beforeimages. It includes the R394
billing route and source selection. Its SHA256 is
`e1d0a2af0205c6fab7d416ab29cdb1def1877ce7e5113689381af6317a79e04e`.
The owned full baseline came from reversing the exact R394 patch on a copy and
checking every resulting R394 beforeimage. No repository Git metadata was read.

`application-map.json` is the incremental map. The explicit maps are
`application-map-incremental.json` and `application-map-full.json`. Each records
the operation and exact before and after lengths and hashes. `afterimages/`
contains the final bytes for the union of both maps.

`apply.py --root <checkout> --mode incremental` checks all beforeimages and performs
a standard patch dry run. `--apply` then applies the patch and verifies all
afterimages. Select `--mode full` for the pre-R394 baseline. No application command
ran against canonical source. Both guarded applications ran against fresh owned
copies and admitted the resulting source. A deliberately changed beforeimage
refused before any write. The raw logs and `application-check.json` and
`guard-negative.json` retain these observations.

## Source authority

The new explicit selection is
`verification/identity-network-current-source-v2/selection.json`, identity
`current-hosted-r394-r398-r420-r426-v2`.

- Selected product members: 190.
- Product manifest digest:
  `4d2eefb1fe856f83507fc643c46ba9f2171b5f11810ffad3942c345b209e9eab`.
- Selection SHA256:
  `bfeca22fb174a283206c8b9db0ffd858ba52849444384eeea62b728717b24272`.

The collector pins the new selection, digest and count separately through
`SUCCESSOR_*`. Runtime preparation, archive admission, compilation checks,
restoration and final migration-version checks use that successor. The workflow
includes its metadata in triggers and sparse checkout. `--check-source` selects
the successor before the existing inert and network steps. The two network test
methods and their runtime policy remain unchanged.

All historical uppercase definitions, the frozen178-v2 and current185-v1 manifests,
their metadata, and their source validators remain byte-identical. The old v1
metadata and manifest still pass their original validators. Runtime validates
the old v1 metadata before the successor metadata. The old validator refuses
the new source, and the new validator refuses the old source. The v1 actual-tree
control now checks retained v1 authority and verifies refusal of the changed
working tree. Its historical pins and other acceptance assertions are retained.
Six new successor controls test actual source, changed or foreign members,
caller-chosen authority, metadata corruption, and refusal before Docker.

No manifest is automatically authorized by scanning current files. The explicit
successor starts with the pinned 185 members, adds only the four reviewed R398
files and the new shared migration list, and records exact fixture deltas.

## Migration fixtures and retained contracts

`hosted/test/support/reviewed_migrations.json` owns the closed twelve-filename
list. `test_helper.exs`, the browser migration driver and its Elixir specification
consume that list. Extra and missing files still refuse before the shared
foundation migrator executes. The existing foundation controls exercised both
refusals against the complete twelve-file directory.

Aggregate rollback derives the suffix starting at its explicit aggregate version
and rolls back `length(latest)` steps. The test proves the ledger table disappears
and returns while the held worker, lease, build data and closed admission behavior
remain intact. The browser fixture derives activation-and-later and
aggregate-and-later rollback lengths from the same list. It exercises partial
and complete rollback and reapply under a non-superuser schema owner, preserving
browser object identities, ACLs, constraints, data and runtime privilege refusals.

The ordinary hosted driver provisions the three separate billing and ledger test
databases and supplies both additional port variables. The actual new driver
block executed on a second fresh owned PostgreSQL cluster. SQL observed exactly
`mixer_billing_r325`, `mixer_billing_r354` and `mixer_usage_r398`.
`ordinary-ci-provisioning.json` retains that result. The complete ordinary hosted
driver was not run.

All four R398 afterimages exactly match the independent R420 review inputs.
`UsageLedger` API and units remain unchanged: `build_elapsed_milliseconds`, raw
app-installation-month units, and `storage_byte_seconds`. R420's independent
17-plus-nine result is retained evidence, not a new run of those nine attacks.
The entire R338 coordinator file is unchanged from the current canonical input.
Its completion-versus-lease-replacement and tenant-isolation regression passed.

## Executed evidence

The actual combined command used `mix test --warnings-as-errors --seed 0 --trace`
with ledger, route, inbox, signature, transport, foundation, storage, admission,
aggregate, coordinator, lifecycle and journal selections. The raw
`logs/combined-hosted-db1.log` ends with 177 passed and exit 0. The separate
`logs/migration-rollback-db1.log` ends with one passed and exit 0. These are
178 tests across two commands. The 17 ledger tests are included in the 177.

Final `logs/collector-normal-r2.log` and `collector-optimized-r2.log` each end
with 153 tests and OK. They repeat the same 153 controls. The pure import and
control guards forbid real processes and socket operations inside those suites.
Both applied-patch source preflights also passed.

The combined log retains 69 migration module redefinition warnings and 15 Oban
notifier errors about missing database configuration. These do not change its
observed zero exit and test outcome. This run does not qualify notifier behavior.
The database suite preceded the final correction of an unused-in-that-suite
Python provisioning expression. Its Elixir test and product bytes are unchanged
in delivery. The corrected Python block was then executed against real PostgreSQL,
and final collector controls bind the delivered complete source selection.

Tools were Elixir 1.20.4, OTP 29, PostgreSQL 17.11 and Python 3.14.8 on Darwin arm64.
The host had 15 CPUs and load averages 11.41, 13.51 and 16.00 at preparation.
Three BEAM schedulers were chosen for these finite runs. This is not a user CPU
limit. Existing locked dependencies, build caches and the local Hex archive came
from the exact R398 owned source. No dependency was fetched or added.

`commands.json` retains the first tool and database command records. Later phases
use separate `commands-controls.json`, `commands-provision.json`,
`commands-deliver.json` and `commands-guard-check.json`. These record argv, cwd,
PID and PGID, deadline, exit and raw output. `tested-source.json` records the
delivered tree and control hashes. Source identity uses those hashes because
root Git access was expressly forbidden.

## Preserved failures and cleanup

Two composition marker mistakes stopped before writing the collector. A later
delivery import failed before launching a command because the recorder expected
an absent CLI argument. Their summaries remain in `logs/composition-select-r1.log`,
`composition-select-r2.log` and `delivery-import-r1.log`. The corrected marker,
runtime-section name and recorder default are in the delivered scripts.

Parallel initial controls and database work shared a command-record file. Database
progress overwrote the normal-control completion and optimized-control metadata.
The raw logs and direct runner zero exits remain. `command-recorder-correction.json`
records the defect. Final normal and optimized controls reran with separate complete
metadata. No product test failure or UNKNOWN resource was hidden by this correction.
Source inspection also corrected the new CI provisioning block to use the actual
`args.pg_bin` and `run` names before its real PostgreSQL execution.

The database suite owned only loopback port 65304 and `postgres-db1`. The
provisioning control owned only loopback port 51210 and `postgres-provision`.
Both disabled UNIX sockets. Each exact-directory stop exited 0, each subsequent
`pg_ctl status` exited 3, and both postmaster PID files are absent. The two cleanup
receipts retain these facts. Inactive data and raw logs remain. Direct command
exits do not establish absence of arbitrary descendants or release historical
custody holds.

`preservation.json` checks 328 named canonical and reference inputs with no
mismatch. All historical held namespaces and processes remain untouched.
Physical devices, frozen lanes, signing, providers, customer data and deployment
were outside this task. Trusted producer adapters, metering authenticity, consumer
integration, pricing, HTTP authorization, reconciliation, immutable packages,
production migrations, fresh ordinary CI, network runtime acceptance and GA gates
remain pending. This composition unlocks coherent root adoption only.
