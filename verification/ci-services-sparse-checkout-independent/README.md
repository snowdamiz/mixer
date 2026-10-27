# Independent services sparse-checkout review

Accept the checkout selection within this review's scope. The actual workflow is
byte-identical to the producer's frozen candidate, SHA-256
`2c701a47ef42129547048623eff7db7db721fb2fe39d3dabf4bb7bb6d1f939a0`.
Against base `9398732c23648a82097d5a72b02b1c77af818e41`, the entire workflow
diff is the six checkout-input lines in `workflow.diff`. All pre-existing job
commands, working directories, Go 1.26.4 pin, runners and timeouts are preserved.
The service commands remain `go mod verify`, `go vet ./...`, and
`go test -race ./...`.

The reviewer independently enumerated the base Git tree and recomputed each
selected Git blob identity, byte count and SHA-256 against the working files.
All 152 service files plus `contracts/release-v2.json` are present: 153 files,
4,379,716 bytes. This exactly matches the producer's inventory. Complete service
selection includes package-local fixtures, module manifests, all testdata and
the embedded `release/migrations/001_release.sql`. No root Go module/workspace,
submodule configuration, or root attributes file exists at the selected base;
the service module has no local `replace` dependency.

An independent offline Go 1.26.4 `go list -mod=readonly -json ./...`, selecting
Linux/amd64 with CGO enabled, enumerates all six service packages and 35 local
package-file records without package errors. It confirms the embedded migration
and four `postgres_integration` files ignored by this untagged job. This command
enumerates packages; it does not run, compile, or qualify the service tests.
Twelve Python structural policy controls pass, including rejection of missing
or narrowed selection, race/vet/toolchain/timeout drift, cone-mode drift and
changes to another job. The unrelated-root control checks that this precise
policy selects no VM, other contract, or historical root verification file.

The external-read review is explicit in `source-read-closure.json`. The untagged
protocol tests read six package-local JSON fixtures and the external frozen V2
contract. That contract is the sole repository input outside services read by
the selected tests. Other active file operations use caller-supplied runtime
configuration or test-owned temporary state; the command's `main` is compiled
by the job but not executed by `go test`. The fixture generators are under
`testdata/` with `//go:build ignore`, and PostgreSQL process controls require an
unselected integration build tag. No generator, PostgreSQL, HTTP test harness,
product service, native runtime, UI or capture process was started here.

The frozen producer seal
`244417580cacbd04fcb79685e5a15d376314320d9c70f40be49d2df2194f071f`
and all 31 members/120,762 bytes independently match. The reviewer checked all
producer command output hashes and the retained real sparse-materialization
fixture evidence: the existing cross-language descriptor test passes, and
removing only the external contract produces the intended missing-file failure
with exit 1. The producer's owned scratch is absent. Its numeric PID/PGID values
were not retained, so those historical identities cannot be independently
reconstructed; its cleanup assertions remain producer-reported. This limitation
does not require rerunning that completed focused fixture.

`capture.json` owns audit PID/PGID 84769. `commands.json` owns exactly seven
read-only Git/Go command groups, with argv, clean environment, executable hashes,
stdout/stderr hashes, exit, elapsed time and numeric PID/PGID for each. All exit
0, all children are reaped, and every recorded owned group is absent. The audit
completed in 3.43 seconds. Temporary package-list cache/scratch was removed;
existing module caches and other projects' processes were preserved. Python
ran with `-B`; no global process inventory or Git mutation was used. The
workflow and producer custody were rechecked at the end of the audit.

Historical run 40545367451, services job 122334424079, was cancelled during its
fifteen-minute checkout; no service tests ran. The terminal observation was
provided by root during review. It motivates the repair and supplies no remote
proof for the changed job. Remote checkout transfer behavior and the complete
unchanged service race job remain pending. This review does not accept the full
services suite, hosted Phoenix/Neon operation, native/device behavior, OTA
eligibility, operational qualification or any GA gate.

The frozen packet's read-only custody checker is:

```sh
env -i PATH=/opt/homebrew/bin:/usr/bin:/bin LC_ALL=C LANG=C \
  PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3 -B \
  verification/ci-services-sparse-checkout-independent/audit.py --check
```

It checks this packet's exact manifest, the complete producer packet, actual
workflow/candidate equality, all 153 selected source hashes and scratch absence.
It performs no subprocess or write. The producer audit is one-shot and must not
be rerun against its frozen directory.
