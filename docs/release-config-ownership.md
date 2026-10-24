# Release server configuration ownership

`release.New` and `NewWithFault` now take an owned snapshot before validating
configuration or opening storage. The server retains its own token/root/host
arrays, root public-key bytes, host capability maps and PostgreSQL settings.
Scalar fields remain ordinary value copies. Nil and explicitly empty containers
keep their original meaning.

Previously, mutating a caller's configuration after successful construction could
change the running server's authorization and verification decisions. Independent
public API probes reproduced reader-to-publisher escalation, replacement bearer
credentials and tenant/audit identities, acceptance of a substituted signing key,
and changes to the registered host contract. Separate race-detector probes found
concurrent caller-write/server-read races at each retained mutable boundary. This
is an ownership defect at the embedding API; it does not establish a remote
unauthenticated attack path.

Callers must keep the configuration stable until construction returns. Afterwards
they can reuse or change their configuration without affecting the running server.
Those changes are not a live configuration or key-rotation API. Concurrent mutation
during construction remains unsupported. Configuration validation, v1/v2/v3 wire
formats, authorization rules and the production-mode prohibition are unchanged.

The product regression suite exercises public `New`/`ServeHTTP` behavior for all
three protocol versions. It preserves original token permissions, tenant scope,
credentials and committed audit identity; independently mutates both signing keys,
root records/revocation, host records/limits and map entries/deletion/replacement;
and rejects a newly introduced signer. Concurrent caller mutations run after
construction while distinct idempotency keys force fresh verification on every
upload and validation request. Invalid configuration still rejects before opening
durable storage.

Run the host verification with a new evidence directory:

```sh
python3 verification/release-config-ownership/run.py --name candidate-N
```

`candidate-1/receipt.json` binds 47 service/contract inputs and the exact Go tool,
module versions, commands and logs. The focused suite passes five top-level tests
and 30 subtests. The complete `go test -race -count=1 ./...` suite and `go vet ./...`
pass. The source tree is checked unchanged across the run. Independent evidence
is retained under `verification/release-config-ownership-review/`.

These are headless Go service checks with Go 1.26.4. The PostgreSQL integration
suite requires its separate build tag and private-cluster runner and is not part
of these results. Hosted identity, delivery workers, operational qualification
and the complete W11/W16 gates remain open. No deployment, credential change,
native execution or GA qualification is performed by this fix.
