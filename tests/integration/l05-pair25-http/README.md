# Ordinary Pair25 Android build

Run from the fixture checkout. The launcher archives local commit
`ffbd472419c4fd5bb3bf32735738155a9caa9cc8` into its own scratch, uses its locked
hosted sources, and compiles in `MIX_ENV=test` with Hex offline. It extends the
existing loopback integration test and its signed issuer fixture in scratch.

The host needs Python 3.12 or newer, Elixir 1.20.4 on OTP 29, Hex 2.5.1, local
Rebar, all `hosted/mix.lock` packages in the local Hex cache, and PostgreSQL 17
binaries. Use an existing scratch parent with a short canonical path. Every
ancestor of the scratch must be owned by root or the replay account with no group
or other write bits, for the stock retained-store and log readers. The launcher
creates one private scratch under the supplied path. Its disposable
PostgreSQL cluster listens only on loopback with trust auth and no Unix socket.
Phoenix, the signed test issuer, the key fixture, and the native worker also use
ephemeral loopback ports. No billing service or credentials are needed.

The API fixture starts the ordinary `:workspace_builds` graph with the restricted
create repo and API Oban queues disabled. Its operator setup installs the stock
build-create surface, builds processor grants and policies, and the exact
durable-intent migrations 498 through 500. The operator registers the pinned
Linux export, projected lock and recipe in the existing verified-input table.
The Linux input uses the ordinary authenticated create path with a signed session,
active tenant membership, CSRF and one idempotency key.

The separate processor loads `RuntimeConfig` with `builds_v1`,
`durable_intent_v1`, `native_development_v1`, concurrency one, and the restricted
`mixer_build_processor` login. The fixture changes the stock repo's TLS and port
for its ephemeral local cluster. After confirming the queue is paused and the
sole POST returns 201, it drains just the `created` job with stock Oban.
`Storage.read` and `Dispatch.operation_id` return the running record, worker
reference, operation ID and exact 20-minute attempt deadline. The scheduler
stays paused with just the `start` job available and no durable operation intent.
The launcher binds the same operation grant into the runner and worker
configurations, checks listener startup, then resumes that queue. Fresh owner
and unrelated-tenant sessions read the terminal detail, logs and three artifact
routes after worker shutdown.

The fixture records a row count and SHA-256 for each billing table before the
build and after terminal readback. Both snapshots must match.

## Select the managed Linux Starter

Add `--select-starter` to use hosted commit
`f6577616a8394ca1104f2ba8c430d7ac124ea095` and provision the opt-in managed
Linux Starter catalog. The fixture starts with an empty verified-input table.
It registers the approved projection, Linux lock, rendered driver, and Docker
recipe after ordinary app onboarding. The owner lists and selects the Starter
through `/console-api/v1/source-starters` while the worker and runner are down.

Two selections must return the same input and leave one verified row. An
unrelated tenant and an unknown Starter ID receive HTTP 404. A build with a
changed source digest receives HTTP 409 with no enqueue. The launcher submits
the accepted build using the selected response. Before resuming Oban, it
matches the committed attempt with the approved registration and grants the
worker and runner access to that operation.

```sh
mkdir -p verification/local
python3 -B tests/integration/l05-pair25-http/run.py --select-starter \
  --scratch "$HOME/.t3/userdata" --receipt verification/local/pair25-selected-inert.json
```

Include `--select-starter` in the real command below to build from the selected
input using the approved stage.

### Loopback browser

The browser mode archives the ordinary hosted and console sources from
`26000a3fa85a96e5e1e13df221528ac7df8b9add`. Have that commit locally and put
Node 22.18+ and npm on `PATH` in addition to the hosted prerequisites above.
The mode bundles the stock console with Vite's `local-workspace-builds` mode.
It installs from a private copy of the locked npm tarballs already present in
`$HOME/.npm`. Use `--npm-cache` to point to a different populated cache. Hex
and npm dependency resolution are offline.

```sh
mkdir -p verification/local
python3 -B tests/integration/l05-pair25-http/run.py --browser queue \
  --seconds 180 --scratch "$HOME/.t3/userdata" \
  --receipt verification/local/pair25-browser-queue.json
```

The fixture prints the path to a private JSON file after it is ready.
Open that file locally and navigate to its one-use `url` in an isolated
browser session. Use `localhost` as written so that the browser accepts the
Secure cookie. Keep the URL and the file out of logs and evidence. The file
also contains the exact `starterId`, application scope and `finishFile` path.

1. In **Pair25 owner**, choose **Pair25 project**, click **View builds**, and
   select **example.source.app**. Click **New build**.
2. Observe **No admitted source inputs**, then click **Select local starter**.
   Confirm the Android row contains the exact `starterId` from the handoff.
3. In queue mode, select that row and click **Create build** once. Observe
   **Submission confirmed** and **Queued** for the same build ID.
4. After collecting browser evidence, touch the private `finishFile`.
   The launcher also closes the fixture when the handoff window expires.

Use `--browser select` for steps 1–2 only. This mode verifies that selection
leaves zero builds and jobs. Queue mode leaves one revision-zero build and one
available `created` Oban job. The launcher compares the submitted idempotency
key with both the persisted request key and the journal without recording its
value. Both modes require exactly one verified Android input, no worker
listener, no dispatch intent, reservation or coordinator lease, and unchanged
billing snapshots. The receipt includes scoped HTTP outcomes, bundle hashes,
and teardown observations. The bridge issues the synthetic session only once
and forwards the browser's cookie, CSRF header and idempotency key to the local
Phoenix endpoint. These commands use inert Pair25 inputs and stop before worker
or runner startup.

Run the HTTP smoke using a separate receipt path.

```sh
python3 -B tests/integration/l05-pair25-http/run.py --browser smoke \
  --scratch "$HOME/.t3/userdata" --receipt verification/local/pair25-browser-smoke.json
```

The smoke loads the served HTML and JavaScript bundle over loopback. Python
performs the selection, create and detail requests through the same bridge.
Rendered UI and browser-originated actions require the interactive run above.

### Complete the queued browser build

Add `--complete` to pass the one verified submission to the ordinary paused
processor. The receipt ties the completed Oban `created` job to the same job ID
observed at queue time. Terminal detail and download routes must match the
original build scope and source pins. Owner, outsider, and anonymous reads
must return HTTP 200, 404, and 401 respectively for detail, logs, and all three
downloads. Billing snapshots must match before submission, after queueing, and
after terminal readback.

For an inert replay, run the HTTP smoke through completion. The stock runner
protocol returns synthetic artifacts and known log counters.

```sh
mkdir -p verification/local
python3 -B tests/integration/l05-pair25-http/run.py --browser smoke --complete \
  --seconds 45 --scratch "$HOME/.t3/userdata" \
  --receipt verification/local/pair25-browser-complete-inert.json
```

For a live replay, prepare a fresh operator stage and daemon as described in
[One real run](#one-real-run).

```sh
mkdir -p verification/local
python3 -B tests/integration/l05-pair25-http/run.py --browser queue --complete \
  --seconds 900 --scratch "$HOME/.t3/userdata" --operator /absolute/path/pair25-operator.json \
  --receipt verification/local/pair25-browser-complete-live.json
```

Follow the four browser steps above. Touch the private `finishFile` after
capturing the queued build ID. With `--seconds 900`, you have 300 seconds to
finish the browser steps and a separate 900 seconds for settlement. Once the
bridge closes, the launcher dispatches the build and uses fresh authenticated
API sessions to verify the logs and downloads.

If offline Hex reports a missing registry entry, warm a disposable copy
before starting the fixture. Substitute your configured Hex cache path for
`$HOME/.hex` if needed.

```sh
prep=$(mktemp -d "$HOME/.t3/userdata/p25-hex.XXXXXXXX")
mkdir "$prep/hex" "$prep/source"
cp -R "$HOME/.hex/packages" "$HOME/.hex/cache.bin" "$prep/hex/"
git archive 26000a3fa85a96e5e1e13df221528ac7df8b9add hosted | tar -x -C "$prep/source"
(
  cd "$prep/source/hosted" &&
  env -u HEX_OFFLINE MIX_ENV=test HEX_HOME="$prep/hex" HEX_HTTP_TIMEOUT=8 \
    TMPDIR="$prep" mix deps.get --check-locked
)
```

Set `HEX_HOME="$prep/hex"` when you run the fixture. Remove the disposable
cache and source after the replay and its cleanup checks finish.

### Console selection control

Use Node 22.23.3 and Elixir to run the compiled console tests in a disposable
source projection. The overlay adds a test to the existing Solid event fixture.
It checks that selecting the managed Starter reloads its admitted Android input
and that creating from that row sends the scoped pins and displays the exact
queued build. The test supplies fixture responses for the API.

From the checkout root, set `scratch` to a new empty directory that you own.

```sh
recipe="$PWD/tests/integration/l05-pair25-http"
git archive 9c14c70b5a2b8bd8b99b2b632fd5e67a590375e5 \
  console website/src/styles.css website/public/assets \
  hosted/lib/mixer_hosted/authorization/scope.ex | tar -xf - -C "$scratch"
(
  cd "$scratch" &&
  git apply "$recipe/console-managed-starter.patch" &&
  cd console &&
  npm ci --ignore-scripts --no-audit --no-fund --cache "$scratch/npm-cache" &&
  npm run typecheck &&
  node --test --test-concurrency=1 tests/*.test.mjs src/*.test.mjs
)
```

Remove the disposable projection after the commands exit. The ordinary API
and real worker are exercised by the separate runs below.

## Zero-native-build control

```sh
mkdir -p verification/local
python3 -B tests/integration/l05-pair25-http/run.py \
  --scratch "$HOME/.t3/userdata" --receipt verification/local/pair25-inert.json
```

The inert adapter writes three synthetic artifacts and puts the driver counters
in `readback.json`. The stock runner protocol and importer deliver those counters
to the authenticated worker, which publishes the customer log. The stock logs
endpoint must return exactly two events to the owner. The driver event has exit
code 0, 320 stdout bytes, 80 stderr bytes, and no truncation. The build command
event has exit code 0. The endpoint returns 404 to the other tenant and 401 to
anonymous callers. The worker also refuses a changed deadline and an expired
guard on the same operation.

## One real run

Prepare a fresh dedicated daemon and an operator-approved Noble stage by
following the [managed layout](../managed-android-local-linux-pair25/MANAGED-LAYOUT.md)
at the pinned candidate. Install the approval as root-level `projection.json`,
stage `managed_worker.py` as `recipe/worker.py`, and provision the case-sensitive
toolchain volume under the name and labels returned by `Pair25Layout.read`.
The launcher uses that layout's exact source, driver, and Linux lock pins.
The stock runner checks the daemon, the image, and the volume before launch.

Supply a JSON file with `pair25_root`, `docker`, `daemon_socket` and
`daemon_id` for this exact stage and daemon. The first three values are
absolute canonical paths. If the daemon reports the config digest as the image
ID, include that exact value as `image_id`. The default is the approved image
manifest digest. The optional `command_timeout` defaults to 0.5 seconds. Keep
the stage immutable and make only its dedicated `outputs/` available for the
runner-managed output binds. The launcher derives the recipe digest and writes
the private worker and runner configs for the operation.

```sh
mkdir -p verification/local
python3 -B tests/integration/l05-pair25-http/run.py \
  --scratch "$HOME/.t3/userdata" --operator /absolute/path/pair25-operator.json \
  --seconds 900 --receipt verification/local/pair25-live.json
```

The run requires the same log response codes as the inert control. The owner's
two events must match the sealed readback for the real driver. Root owns the
daemon, operator inputs, and volume retirement. After service closure and port
reuse, the launcher removes its scratch. If the live operation or a process
remains unresolved, the receipt records the retained scratch path.

## Cancel a running build

Add `--cancel` and use a new `--receipt` path. With no `--operator`, the inert
runner stays running after its first start until the ordinary owner request
reaches the stock stop protocol. With `--operator`, use a fresh operation on
the prepared stage. The fixture reads the runner's Docker journal and checks
the exact container against the pinned daemon, identity, image, and mounts.
It waits for an `aarch64-unknown-linux-android` Swift frontend in that
container before posting to `/console-api/v1/builds/cancel` as the owner.
`--seconds` covers running observation and settlement in cancellation mode.

The fixture requires a 202 response, one matching capacity release by the
restricted Oban processor, one original start in each ledger, and a stopped
runner with the matching worker tombstone and closure diagnostic. It also
checks the worker artifact request and all three Android download routes for
the exact cancelled build. The real variant verifies that Docker removed the
observed container and its output directory without sealing a bundle.

```sh
python3 -B tests/integration/l05-pair25-http/run.py --cancel \
  --scratch "$HOME/.t3/userdata" --receipt verification/local/pair25-cancel-inert.json
```

## Recover after an abrupt worker exit

Run the L07 replay with the inert runner backend. The fixture archives product
commit `11b9cb43e3d90de5580efda9b9e2e3a47e387be3` for this mode.

```sh
mkdir -p verification/local
python3 -B tests/integration/l05-pair25-http/run.py --cancel --worker-crash \
  --seconds 75 --scratch "$HOME/.t3/userdata" \
  --receipt verification/local/pair25-worker-crash.json
```

The fixture sends SIGKILL to its owned worker PID after both ledgers record the
original start. The independent runner stays live. During the outage, restricted
Oban retries the original job, PostgreSQL holds the capacity reservation, and
the console build, logs, and artifact APIs enforce the original scope. The
fixture waits for direct reap, process group absence, and an exact loopback bind
with the stock socket options. It then reopens the same config and SQLite store.
The existing Oban job must reach the original runner with a fresh guard. The
receipt captures the first owner detail HTTP status, projected build fields,
and runner and worker observations before checking the response.

The default inert recovery keeps the original operation active for one owner
cancellation. Add `--inert-finish-on-reopen` and use a fresh receipt path to
exercise natural completion. That option lets the inert adapter finish after
the worker reopens, then waits for settlement before the first owner read. It
requires zero cancellation requests. Both controls use the same outage
assertions and product pin. The focused controls use the stock Python runner
and worker with inert HTTP responses. Run them with
`python3 -B tests/integration/l05-pair25-http/test_recovery.py -v`.

For a live follow-up, use a fresh stage and dedicated daemon from the real run
instructions. The live mode requires an Android Swift frontend in the pinned
container before the worker exit. If an Android Swift frontend is active in
the same container after recovery, the fixture sends one owner cancellation.
If compilation finishes during recovery, the fixture verifies native success
on the same operation, including the exact container's successful exit and
removal, one capacity release, three authenticated downloads, owner logs, and
stable final revision. A stock 409 conflict at the sole cancel POST covers the
race with completion only when that same success proof passes. The receipt
records the attempted POST and reports cancellation as unexercised in that
case.

```sh
python3 -B tests/integration/l05-pair25-http/run.py --cancel --worker-crash \
  --seconds 900 --scratch "$HOME/.t3/userdata" \
  --operator /absolute/path/pair25-operator.json \
  --receipt verification/local/pair25-worker-crash-live.json
```
