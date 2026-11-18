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
work. The API has no queues, staging, leadership or plugins.

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
