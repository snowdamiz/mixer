# Pending active-fetch lifecycle implementation

Only KeyOwnerSupervisor and the new dedicated inflight lifecycle test are changed.
The beforeimage was retained before the supervisor edit. The test fixture
constructor and tuple init clause are both under Mix.env() == :test. Both starts
use the same initializer and derive the owner child from KeyOwner.child_spec;
only its start MFA differs. Production ordinary options, identity/Admission/
FetchFlight/DNS/transport behavior and existing TLSFixture are unchanged.

The two new methods use a completed real TLS handshake and parsed HTTP request
held at TLSFixture's response barrier. No JWKS response is released before the
fault, and no completed JWKS fetch or authenticated identity is claimed. A raw
checkout caller records explicit reply versus exit while the public caller uses
the real ConfiguredVerifier. Exact owned process/port monitors, held controller,
old table and pointer observations are retained. Cleanup failures remain in the
artifact even if a later recovery attempt succeeds. KOL09 must remain a failed
resource gate if its callback faults or replacement precedes old resources DOWN;
no hypothesized product cleanup fix is included.

The future test phase runs the seven unchanged ordinary regressions plus these
two cases: exactly nine methods. A fresh production VM first verifies missing
fixture exports, rejected fixture tuple init, rejected ordinary fixture options,
cleanup and loopback refusal. No Mix project or product application is loaded.
Both phases compile only the frozen 18-file identity closure and already
declared dependencies. No DB, Repo, endpoint, DNS fixture or provider starts.

The plan retains the validated runner's 40-second work, 46-second owned cleanup,
52-second durable observation and 55-second terminal receipt boundaries. Fresh
retained VM sessions/groups are the only OS process groups touched. TLSFixture's
three actual OpenSSL commands per fixture run through a pinned wrapper under the
test group; one explicit version invocation plus six fixture calls are recorded.
Each native child's arguments, PIDs, group, output, exit and timing are retained;
the wrapper reaps it and the outer runner confirms the retained group is gone.
Compiler diagnostics must be empty. OTP kill reports and callback exceptions
remain in full stdout without blanket log suppression. Exact recursive artifact
schemas validate every field/type; clean gate acceptance is checked separately.

No compiler, formatter, Elixir, OpenSSL/version process, TLS fixture or test has
run for this candidate. Prepare and audit use Python -B offline reads/hashes only.

The first review/release target is prepared-1/formatting-plan.json, invoked only
after its separate exact root release with:

    python3 -B verification/console-key-owner-inflight-lifecycle-implementation/prepared-1/runner.py --format-only --release ABSOLUTE_ROOT_RELEASE

That pass writes formatter output for only the two owned files to a fresh
executions/formatting-1 directory; it compiles/loads no product source, runs no
test/fixture/OpenSSL process, and writes no canonical source. Review/apply those
exact outputs and freeze a successor source/runtime candidate before releasing
the nine-method runtime plan. The current execution-plan.json preserves the
prospective exact host shape but is not ready for runtime acceptance: its
read-only five-file formatting check would reject unequal source. Neither plan
is an execution grant; both need exact plan-hash single-execution root releases.

The read-only packet audit is:

    python3 -B verification/console-key-owner-inflight-lifecycle-implementation/verify.py

Native/UI/capture/emulators/phones remain paused. Original KOL08 ordinary owner
crash, production network/provider/application/HTTP/browser/session integration,
custody, operational qualification, published-package FieldLog and all GA gates
remain pending. No central metadata, commit or push is part of this lane.
