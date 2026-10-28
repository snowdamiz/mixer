# Ordinary KeyOwner lifecycle implementation candidate 1

The selected correction enables exit trapping in the shared initializer before
Admission publication. The sole ordinary close call now supplies its own table;
close/2 requires the exact current persistent-term pointer and ETS creator PID.
The existing registered-owner/supervisor lifecycle serializes publication and
cleanup. This is defensive ownership validation, with no atomic CAS claim.

KOL01-KOL07 are implemented against the real ordinary KeyOwnerSupervisor and
Admission with a disabled profile. Synthetic Lease values only test rejection of
old state. They never prove authenticated lease acquisition. The test helper
resumes its owned suspended component in after and registers exact component
cleanup before returning control to each test. Test-owned helper callers are
reaped by exact PID. No fixture success collaborator or network fixture is used.

The prepared standalone plan compiles the exact 18 ordinary identity sources
(excluding unrelated StartupConfig) with five already-recorded general-purpose
dependencies. It never loads the product application or cached MixerHosted BEAMs.
An original-beforeimage process first reproduces graceful parent shutdown leaving
a dead, fail-closed Admission pointer. That pointer is intentionally retained
until its isolated VM exits. A second process compiles corrected sources and runs
only seven lifecycle tests. Both processes use fresh compiler output and bounded
schedulers; no database, DNS/TLS fixture, provider fetch or physical device runs.

No Elixir, version, formatter, compiler or test runtime has run for this candidate.
Python -B offline preparation/audit checks establish byte custody and source
scope only. `prepared-1/execution-plan.json` and `prepared-1/freeze.json` are
immutable after creation. Root must independently review source/test/runner and
issue a separate exact-plan single-execution release before the runner can run.
The release must have status root-released-exact-plan, single_execution true,
and the exact execution_plan_sha256. The fixed execution directory prevents reuse.

The runner partitions 55 seconds into work through 40, exact-child/group cleanup
through 46, pin/artifact/durable-observation finalization through 52, and receipt
writing through 55. Signals are observed through a documented finite cutoff after
cleanup and durable observations. Owned scratch is removed only after the exact
retained child and owned process group are confirmed gone; any uncertainty
preserves scratch and fails. System shared libraries remain part of the host
environment rather than a hermetic tool copy. Any timeout, warning, missing
artifact, failed count, signal or cleanup fault fails the run.

KOL08/KOL09 real-flight/TLS drain, active-flight worker-supervisor death, application
startup/HTTP/browser/session/provider integration, production operation and all GA
gates remain pending. Computer use, capture, native simulator/emulator and phones
remain paused. No global process inventory, protected workflow/browser-auth file,
Wrangler state, repository metadata, commit or push is part of this candidate.
