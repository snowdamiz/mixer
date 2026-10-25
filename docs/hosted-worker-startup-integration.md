# Hosted worker startup integration candidate

The isolated candidate under `verification/hosted-worker-startup-integration/`
connects the selected worker client to hosted startup configuration. Live hosted
files remain unchanged until the repaired client and composed startup are reviewed.

`RuntimeConfig.load!/1` loads the worker configuration with the same trusted DER
roots used for the identity client. API processes can only use the exact disabled
worker configuration. Disabled mode rejects leftover configuration or token
variables and publishes no dispatcher. Configured processors select the actual
`WorkerHTTPAdapter` with a 6,000 ms coordinator call timeout, 30,000 ms lease and
1,000 ms polling interval. Operator values cannot choose another callback module
or expand those bounds. Inspection excludes all credentials.

The runtime configuration publishes the validated worker configuration and dispatch
selection before application startup. The application requires the bound worker
setting, validates the configured object again, and starts Repo, WorkerTransport,
then processor Oban. Reverse supervisor shutdown stops the queues first. The
transport child remains temporary: application wiring must not defeat the V2
generation quarantine by automatically replacing an uncertain execution domain.
The startup test fixture gains the same explicit disabled binding.

The collection compiles only the production branches of the four client modules,
their six approved contexts, three pure identity configuration helpers, and the
two startup modules. It executes the original four runtime configuration tests
and twelve new integration controls. An actual supervisor starts the real
transport before a test queue probe and proves that its temporary child is not
restarted after owner death. The probe is not Oban; this is not a complete hosted
application startup test. The endpoint is not compiled or started, and only its
unexecuted `config_change/2` call is excluded from undefined-call warnings. No
catalog or authority module may be loaded. No database, cloud worker, native test
instance or signing process is started.

Bind the final client receipt by its independently selected hash with
`python3 verification/hosted-worker-startup-integration/bind_inputs.py SHA256`, then
run `python3 verification/hosted-worker-startup-integration/run.py`. Each execution
retains an immutable attempt directory with exact input hashes, command, tools,
outputs and cleanup. The first collection passes all 16 tests with no skipped or excluded tests. It
compiles the production branches, starts and retires the actual transport under
a supervisor, and leaves no owner, guard, marker or build directory. The source
map binds 80 inputs; no complete application, Oban, database or endpoint was
started. See the attempt receipt under `attempts/20261025T023022458017Z/`.

Independent transport review, complete application/Oban integration, production
release and CI, deployment resource limits, real controller/provider operation,
authorization, source/result verification, signing, dogfood and GA remain open.
