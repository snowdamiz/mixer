# Independent dead-supervisor correction review

The exact two-file candidate is accepted for root's ordinary remote CI validation.
No source correctness blocker was found. Corrected behavior, compilation and
formatting remain unverified; the original KOL09 failure is retained.

The owner's catch accepts only the observed `noproc` call envelope, pinned to
the same worker-supervisor identifier and tracked flight PID. After either a
normal return or that catch, the original monitor reference and PID must deliver
DOWN before owner termination can finish. An already queued DOWN is eligible;
a consumed DOWN cannot remain tracked because the existing handler removes the
flight. The wait has no timeout or replacement fallback. The unchanged
`one_for_all` supervisor cannot publish replacement children until old owner
termination completes.

The forced controller exit is confined to FetchFlight `terminate(:killed, s)`.
Its PID was accepted only after matching the flight's worker and raw port,
checking that port's connected owner, and installing the exact controller
monitor. The correction closes that raw port, signals only the stored PID, and
retains raw-port, controller and worker DOWN waits. There is no name lookup or
global process scan. Normal worker-DOWN, deadline, cancellation and graceful
shutdown do not gain the forced-controller branch. Existing KOL08 and K07f/g/h
held-controller assertions remain byte-identical and must stay enabled.

This is a causal source barrier for the observed tracked, registered-controller
case, not a universal bounded recovery guarantee. A flight already executing
its normal worker-DOWN handler may be inside the existing controller wait and
cannot dispatch a parent exit until that callback finishes. Admission and
replacement remain closed behind the owner/flight monitor waits. Direct
untrappable process kills, registration-in-progress cases and VM death are not
newly qualified. Other supervisor-call failure envelopes remain visible.

Both PG16/17 relation manifests have equal sets of 29 source bindings, all
currently matching. Neither changed identity module is among those bindings,
so this correction needs no relation manifest or source-pin edit. The separately
held UnitA callback collector expects an older RelationManifest module hash.
Root confirms that collector and its dirty workflow insertion are excluded
from this correction. The committed `41af4a3` workflow was separately retained;
it invokes the full ordinary Phoenix collector and has no selected callback
collector invocation. The held-lane mismatch is an existing out-of-scope
limitation, not an ordinary-CI or two-file-correction blocker.

`audit.json` binds the 35 packet members, candidate beforeimages to Git HEAD,
canonical candidate bytes, 22 unchanged inputs, immutable original failure,
relation sources and committed workflow. `decision.json` is the source decision
and pending remote evidence contract. `freeze.json` seals this new review
directory. No source, tests, fixtures, collectors, dependencies, workflow,
global metadata or other lane files were edited. No product runtime, compiler,
formatter, TLS, process probes, native/UI/simulator or capture work was run.
