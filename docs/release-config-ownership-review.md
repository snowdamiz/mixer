# Release configuration ownership review

The candidate closes the reproduced configuration alias boundary. No unresolved
finding remains within the reviewed constructor ownership scope. This review
supports a bounded W11/W16 development slice under product-plan §§13.1–13.2 and
18.1; it does not accept either full workstream or a GA gate.

The defect required a caller in the Go process to retain and mutate configuration
passed to `release.New`. The public HTTP requests below demonstrate the resulting
authorization and trust changes. This is not evidence that a remote HTTP client
can directly mutate server configuration.

## Exact field graph and correction

The review inspected the actual `Config`, `Token`, `protocol.Root`,
`protocol.Host`, `protocol.Scope`, `protocol.Limits` and `PostgresConfig` types.
The mutable references reachable from `Config` are:

| Config field | Mutable descendants | Candidate ownership |
| --- | --- | --- |
| `Tokens []Token` | Slice elements; each token contains only strings | Clone the slice |
| `Roots []protocol.Root` | Slice elements and each `PublicKey []byte` | Clone the slice and every public-key byte slice |
| `Hosts []protocol.Host` | Slice elements and each `CapabilityHashes map[string]string` | Clone the slice and every capability map |
| `Postgres *PostgresConfig` | Pointee; its fields are one string, one int32 and one uint64 | Copy the pointee when nonnil |
| Other `Config` fields | Booleans and strings | Ordinary value copy |

Root/host scopes and limits contain only value fields. Capability grants and their
entry/permission/origin/method/namespace slices belong to request manifest DTOs,
not `Config`. A general grant deep copy would therefore be unrelated to this fix.

The source audit confirms `NewWithFault` calls `snapshotConfig` before
`ValidateConfig` and storage selection/open. The exact copied values are validated
and retained by the server. Both public constructors share that path. Typed copies
preserve nil and explicit empty values. No wire schema, signature domain, storage
migration, authorization rule or production-mode guard changed.

The constructor requires stable caller input until it returns. This review did
not mutate inputs concurrently with construction and does not claim such usage
is safe. Copying before validation prevents the validated snapshot from later
following caller writes; it does not synchronize arbitrary callers.

## Observed regression and candidate behavior

The independently authored probe calls public `release.New` and `ServeHTTP` using
local temporary storage and test-only Ed25519 keys/credentials. The same frozen
probe ran against committed baseline `45465134e264c2f385e82ab891c3eb3a6f571cfa`
and the candidate snapshot.

| Caller mutation after successful construction | Baseline observation | Candidate observation |
| --- | --- | --- |
| Reader token role changed to publisher | Upload changes from HTTP 403 to 201 | Upload remains 403 |
| Token organization changed | Original tenant becomes 403; substituted tenant becomes 200 | Original tenant remains 200; substituted tenant stays 403 |
| Token digest replaced | Original bearer becomes 401; replacement bearer becomes 200 | Original bearer remains 200; replacement bearer stays 401 |
| Token actor changed | Upload audit records caller's forged actor | Audit retains original authenticated actor |
| Trusted public-key bytes replaced | Previously rejected signer changes from 422 to 201; original signer becomes 422 | Foreign signer remains 422; original signer succeeds with 201 |
| Root slice record marked revoked | Original signed upload becomes 422 | Original signed upload succeeds with 201 |
| Host capability-map value replaced | Incompatible signed schema changes from 422 to 201; original schema becomes 422 | Substituted schema remains 422; original schema succeeds with 201 |
| Host state version changed | Compatible signed upload becomes 422 | Upload succeeds with 201 |
| V3 host capability-map entry deleted | Original signed V3 upload becomes 422 | Upload succeeds with 201 |

Five separate baseline race probes reported `WARNING: DATA RACE` between caller
writes and actual server authorization/verification reads of token elements, root
elements, public-key bytes, host elements and capability maps. Each writer begins
only after `New` returns. Candidate probes pass under `-race` while those callers
continue writing their own original containers. Race probes write unchanged
values to exercise memory ownership independently of authorization decisions.

The V3 control also mutates nested origin, method and namespace values in the
caller's request DTO after its serialized upload. Candidate release validation
still succeeds, and an authenticated read returns the original persisted signed
grant values. This is an observed request-serialization control, not a new
configuration grant feature or proof of native execution authority. The baseline
combined test stops at its earlier host-map failure, so it does not establish a
before/after change for that control.

The candidate's product regression tests additionally exercise v1/v2/v3 token
authority and nine trust/host mutations for every version, the full upload,
validation and signed publication workflow, introduced-key rejection, concurrent
caller writes with distinct idempotency keys, and rejected construction before
durable storage creation. Two isolated reviewer-only helper tests demonstrate
PostgreSQL pointee isolation in both directions and preservation of nil/explicit
empty containers. Those helper checks do not claim PostgreSQL integration or
runtime database qualification.

## Frozen evidence and verification boundary

Evidence lives in `verification/release-config-ownership-review/`. The baseline
service archive is stored once. `candidate-delta.tar.gz` contains the three exact
changed service files; `support-inputs.tar.gz` contains the committed
`contracts/release-v2.json` fixture required by the service suite.
`candidate-inputs.json` records every frozen module file hash, probe hashes and
archive hashes. The candidate module tree digest is
`cd908d8600bbfa806fd5accb2aee6cb1d3683b8bf901f03572af40dd8e91460c`.

Recorded toolchain: Go 1.26.4 on darwin/arm64, Apple clang 21.0.0, CGO enabled;
Python 3.14.8 drives the archive/run bookkeeping. `environment.json` and
`toolchain.log` retain the exact outputs. `baseline-runs.json` and
`candidate-runs.json` retain argument arrays, timestamps, status and logs.

Observed candidate results:

- Independent public ownership and post-construction race probes pass: five
  top-level tests and thirteen subcases.
- Product ownership tests and two reviewer-only helper tests pass under `-race`.
- `go test -race -count=1 ./...` passes for the complete frozen service closure,
  including release, protocol, updater and review probe packages.
- `go vet ./...` passes.

An initial broad run failed only because the services-only scratch archive lacked
`../../contracts/release-v2.json`. Its failure log is preserved as
`candidate-services-race.log`. The contract was then frozen from the same
committed baseline and the unchanged candidate suite passed in
`candidate-services-race-with-contract.log`. The failed fixture run is not counted
as a product pass or omitted from the receipt.

Reproduce with
`python3 verification/release-config-ownership-review/reproduce.py candidate`.
Use `baseline` to reproduce the expected ownership/race failures or `all` for
both. The script verifies input hashes and uses self-cleaning isolated temporary
directories. New runs can have different random HTTP request IDs, audit times,
addresses and durations; the asserted behavior and source inputs are fixed.

These are headless macOS Go tests. PostgreSQL integration tests guarded by
`postgres_integration` were not enabled. No cloud services, production hosting,
credentials, customers, native runtimes, simulators, emulators, devices, screen
capture or UI automation were used. Production mode remains disabled. Native and
physical-phone acceptance, hosted identity/isolation/operations and full W11/W16
acceptance remain pending under their existing gates. No OTA publication is
authorized by this review.
