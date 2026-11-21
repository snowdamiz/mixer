# Mixer hosted service

The new control plane follows product-plan §§13.2–13.5. This initial foundation
uses Phoenix/Plug/Bandit, Ecto/Postgrex and open-source Oban. It preserves the
existing Go service under `services/` as a compatibility reference. No customer
route or authoritative release dispatcher has moved.

The only HTTP route is `GET /health/live`, returning `{"status":"alive"}` with
`Cache-Control: no-store`. It reports process liveness, **not readiness**. Unknown
routes return a generic JSON 404. There are no identity, tenant, release, signing,
billing or administrative endpoints yet. No session/cookie or body parser is
installed; those belong to their later authenticated contracts.

## Run host verification

Use Elixir 1.20.4 and Erlang/OTP 29.1.1 from `.tool-versions`:

```sh
cd hosted
mix deps.get --check-locked
python3 scripts/test-local.py --output ../verification/local/phoenix-check
```

Each output directory must be new. `--pg-bin` selects the installed PostgreSQL
tools (the default is Homebrew PostgreSQL 17). The collector creates a disposable
loopback-only database with synthetic data, records source/commands/logs, executes
all tests, stops its PostgreSQL instance and removes its own database directory.
It neither discovers nor starts mobile runtimes. `mix test` alone requires
`MIXER_TEST_DATABASE_PORT` pointing to a fresh disposable database; use the
collector to avoid accidentally touching an existing database. Configuration-only
tests can run with `mix test test/runtime_config_test.exs`.

The PostgreSQL fixture uses local trust authentication without TLS. Tests verify
production TLS settings, but do not establish a successful or rejected real TLS
handshake. A local scheduled job running without HTTP traffic does not qualify
Cloudflare container wake, failover or recovery. The domain table and worker used
to demonstrate Ecto.Multi commit/rollback exist only in tests.

## Runtime configuration and roles

Normal startup requires explicit settings; there is no development credential or
database fallback. `MIXER_HOSTED_ROLE` is exactly `api` or `processor`.

Both roles require `MIXER_DATABASE_HOST`, `MIXER_DATABASE_NAME`,
`MIXER_DATABASE_USER` and `MIXER_DATABASE_PASSWORD`. Use a direct Neon DNS endpoint;
pooler labels are rejected. Connections verify certificate trust and hostname,
use port 5432, and have bounded timeouts. The host guard is a configuration check,
not a network egress allowlist or DNS rebinding defense. The runtime inventory
uses the system CA store; trust-store maintenance still requires operations work.

`MIXER_DATABASE_POOL_SIZE` is 2–20, default 8. Oban's direct Postgres notifier adds
one connection per process. Replica counts multiply that bound; migrations and
administration require their own explicit capacity. Neon scale-to-zero must be
disabled and notification/reconnect behavior qualified before deployment.

The API requires `MIXER_SECRET_KEY_BASE` of at least 64 bytes. It binds loopback
port 4000 unless `MIXER_HTTP_BIND` is explicitly `0.0.0.0` and/or `MIXER_HTTP_PORT`
is set. Cloudflare proxy, network admission and TLS termination remain deployment
work. The backend listener uses HTTP/1.1. It disables Bandit's HTTP/2 listener
because its warning logs can include request data. The API has no queues,
staging, leadership or plugins.

The processor has no HTTP endpoint. It uses database-backed leadership and a
one-second stager, with separate `builds`, `signing`, `submissions`, `releases`,
`telemetry` and `billing` queues. Each defaults to concurrency 1; the corresponding
`MIXER_QUEUE_<UPPERCASE_NAME>_CONCURRENCY` accepts 1–8. These are per-node limits,
not global customer quotas. No product workers are implemented yet. Job rescue,
fences, external effects, admission, pruning and Cloudflare liveness are pending.

The included migration pins Oban schema version 14. Migration execution is
explicit and does not run on normal service boot. Production migrations need a
separate privileged role, while the runtime must use a restricted non-owner role;
tenant tables/RLS and role validation will be implemented with the identity seam.

Dependencies are pinned in `mix.exs`/`mix.lock` and inventoried in the repository's
`THIRD_PARTY.yml`. This scaffold is not a production deployment or a GA gate pass.

### Local signed v3 release delivery

Follow the local release delivery runbook to register one target and serve its
committed signed offers and artifacts through the loopback API. Delivery adds one
direct PostgreSQL connection. [Provision local signed release delivery](../docs/operations/local-signed-release-delivery.md)

### Local native dispatch and build cancellation

For the restricted `builds_v1` processor, provision migrations 498–500 and the
durable-intent grant before startup. Set
`MIXER_BUILD_OPERATION_INTENT=durable_intent_v1` and
`MIXER_BUILD_DISPATCH=native_development_v1`. Configure
`MIXER_NATIVE_WORKER_PORT`, `MIXER_NATIVE_WORKER_ID`,
`MIXER_NATIVE_WORKER_TOKEN`, and `MIXER_NATIVE_RETAINED_ROOT` to match the
operator-owned worker. The adapter connects only to IPv4 loopback. The retained
root must be a canonical absolute path. A loopback `builds_v1` API can set
`MIXER_NATIVE_RETAINED_ROOT` for downloads without the worker settings. Omit
these settings to leave native dispatch and retained native downloads disabled.

#### Run a reusable iOS worker on macOS

Add an `ios_custodian` object to the private native worker JSON. Set `version`
to the integer `2`, `authority_id` to a stable 64-character lowercase hex ID
for this ledger, and `runtime_sha256` to the pinned runtime digest map. The
worker also uses the existing `worker_id`, `tenant`, `registration`, and
`policy` to bind the ledger. Keep those values and the custody settings fixed
across listener restarts and build operations. Keep the token in the private
configuration file.

Set `worker_python` to the absolute path of the Python executable for both
roles. To inspect the digest map from your trusted checkout, run the following
from the repository root. Compare it with the approved runtime before setting
`runtime_sha256`.

```sh
custody_entry="$PWD/hosted/priv/development/ios_build_custody.py"
"$worker_python" -IBS - "$custody_entry" <<'PY'
import json
import runpy
import sys

runtime = runpy.run_path(sys.argv[1])
print(json.dumps(runtime["runtime_image"]()[1], sort_keys=True))
PY
```

Set `worker_config` to the private JSON path and `worker_state` to the
canonical absolute path of the private retained root. The worker creates the
state directory with mode `0700` if needed. Its parent must already exist.
Calculate the SHA-256 of the exact JSON bytes. Start the listener in one
service and wait for it to listen on its configured loopback port.

```sh
worker_config_sha=$(shasum -a 256 "$worker_config" | cut -d ' ' -f 1)
"$worker_python" -IBS "$custody_entry" worker \
  "$worker_config" "$worker_config_sha" "$worker_state"
```

Start the supervisor in a separate service under the same local user. Use
the same configuration file, digest, state path, and Python executable.

```sh
"$worker_python" -IBS "$custody_entry" supervisor \
  "$worker_config" "$worker_config_sha" "$worker_state"
```

Keep the supervisor running when you replace the listener. Each operation
has one admission plan and one claim. For a released CLI, the supervisor
records closure after reaping the CLI, observing group absence, and validating
the CLI's acknowledgment and nested receipts. The listener uses a current
authenticated request for the same operation to validate and settle that proof.
Until then, the ledger retains capacity for that operation. The same config
can read its retained artifacts after later builds.

Send `SIGTERM` or `SIGINT` to drain the supervisor. It finishes handling the
current claim before exit. To cancel a build, send the authenticated worker
stop request. Exit 3 means another supervisor holds the ledger lock. Exit 74
means the supervisor could not establish authority or custody. Preserve the
ledger and retained paths when a claim lacks terminal proof. A replacement
supervisor refuses to take over that claim, including after the CLI exits.

For the legacy single-operation configuration, use the existing
`operation_id` and `runtime_sha256` fields with the `worker` and `observe`
roles. Keep the legacy configuration, its pinned runtime, and the retained root
to read legacy artifacts.
Before switching to reusable mode, positively verify closure of every legacy
operation and shut down the legacy worker. Then set `worker_state` to a new
private retained root. A legacy operation with unproven closure still occupies
worker capacity.

#### Enable build cancellation

To enable cancellation, install the SQL emitted by
`mix run --no-start priv/unselected_build_cancel/print_install_sql.exs` as
`browser_schema_owner` after provisioning the existing restricted build-create
and processor schemas. Then set `MIXER_BUILD_CANCEL_ENABLED=true` on the
`builds_v1` API with build creation enabled. Startup never installs SQL.

Send `POST /console-api/v1/builds/cancel` with the same selection query as
`GET /console-api/v1/builds`, an empty body, a live browser session, and its
matching `Origin` and `X-Mixer-CSRF` headers. The build-create scope and active
owner, administrator, or developer membership authorize the operation. The
response contains `outcome` and the current `build` snapshot. HTTP 202 means
the processor is still reconciling the stop. HTTP 200 means the build is
cancelled. Repeating an accepted request returns `duplicate` without adding a
second event or job. A build that already finished independently returns HTTP
409. The processor retains capacity for a started attempt until it records
definitive terminal evidence. The flow uses no payment service.
