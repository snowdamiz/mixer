# Private dispatcher default authority candidate

Candidate 1 remains preserved and unexecuted. This revision uses distinct v2
filenames so every original candidate-1 reference remains byte-identical. The
source-review corrections give fixture children temporary restart policies,
retain a local TLS observation after normal default-verifier warmup, and tolerate
ExUnit stopping the supervised components before on-exit callbacks. The runner
tracks every Popen immediately for final cleanup and attempts a terminal receipt
from its final nested finally even if cleanup, input reads or scratch removal fail.

This is a source-frozen candidate for the next ordinary workspace slice. Runtime
qualification is pending. The only executable product inputs are the accepted
29-file ordinary bearer/workspace closure, the three canonical private dispatcher
modules, three existing authorization/workspace migrations, and the existing
identity TLS test fixture. The canonical dispatcher formatting correction is
included by its revised exact hashes; no product source is changed by this lane.

`default_authority_test-v2.exs` adds seven standalone ExUnit methods. They call the
fixed three-argument dispatcher with an actual RS256 bearer, normal registered
default KeyOwner/ConfiguredVerifier refresh and the default MixerHosted.Repo
connected as a restricted, nonowner, NOBYPASSRLS runtime role. The current database
projection, tenant isolation, paging, default-verifier token rejection, committed
membership/role changes, six identity-state controls, outside-context RLS and
transaction/dynamic-Repo refusal are executable assertions. No test constructs a
VerifiedIdentity, replaces a default module, or injects a dispatcher collaborator.
Read-only Ecto telemetry observes the canonical connection/transaction check on
each successful call; its assertions require the restricted current/session role
and ordinary directory context. The one-connection runtime pool is checked for
empty values of all 20 source-listed authorization GUCs after successful reads
and denials, together with caller Storage/Context/transaction cleanup. These
observations add no product hook or authority.

Existing test support is sufficient. KeyOwner's existing `Mix.env() == :test`
`start_fixture/1` redirects its normal trust-refresh flow to the existing dedicated
loopback JWKS TLS fixture. Actual default verifier success needs that local
transport; there is no honest socket-free success seam. The database needs only
migrations 003/004/006 and exact closed-role grants. There is no canonical source,
startup, dependency, browser-auth or callback prerequisite.

Preparation command (file reads/hashes/copies and Git revision only):

    /opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/console-dispatcher-default-authority-slice/prepare-v2.py --candidate candidate-2

The prepared `candidate-2/execution-plan.json` freezes exact sources, tests, tool
and dependency bytes, commands, sanitized environment, roster and cleanup. The
closed runner refuses to start until root writes that candidate's
`root-execution-release.json` with `released: true` and the exact plan SHA-256.
Then the sole proposed runtime command is:

    /opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/console-dispatcher-default-authority-slice/run-v2.py --candidate candidate-2

The runner copies individually verified dependency BEAM/app inputs into its own
scratch, compiles selected sources there with zero-warning admission, and starts
one disposable loopback PostgreSQL cluster. The test suite starts only ordinary
dependency applications, the three fixture/default repos, existing TLS fixture,
refresh workers and existing test-only default owner. It starts no MixerHosted
application, Endpoint, Router, HTTP console server, browser/provider integration,
browser_auth/callback/session/cookie path, Node/Worker lane, UI/capture or native
runtime. No broad hosted harness is imported or executed.

Work is bounded to 50 seconds and 262144 combined command/server output bytes,
followed by at most 5 seconds of owned cleanup. Every direct child has a new,
recorded private process group. Cleanup targets exact owned children/groups only,
reaps them, checks exact group and dedicated port absence, verifies ordinary
component/Admission cleanup and TLS key-directory removal, and removes only this
invocation's scratch. Incomplete PostgreSQL cleanup preserves scratch. Failures,
original bytes, exact commands and output remain retained. Global process
inventories are absent.
Before any database, role or schema mutation, a bounded read-only `SHOW
data_directory` query must match the exact owned scratch cluster while its
recorded postmaster is alive. A different listener on the selected port cannot
qualify this fence or authorize provision.

The host PostgreSQL 17 tools are byte-pinned; exact runtime PostgreSQL/OpenSSL
versions are unobserved before release. The database is disposable loopback with
trust authentication and no TLS. This does not qualify PostgreSQL 16 CI, Neon,
production credentials, public provider/DNS/custody/startup, transaction-race or
commit-fault matrices, browser session admission, customer workflows, W14/G22 or
GA. Computer use, capture and simulator/emulator runtime remain paused; physical
phones remain disconnected and final native acceptance is pending. Root owns
canonical metadata, workflow, acceptance and delivery.
