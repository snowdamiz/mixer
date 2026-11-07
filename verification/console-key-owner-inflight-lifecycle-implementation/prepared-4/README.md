# Prospective custody implementation and separate plans

prepared-4 implements the root-selected ownership contract and OCR-A1/A2/A3 in
wrapper/runner/evidence plumbing only. Canonical source and all nine lifecycle
methods remain byte-for-byte unchanged from prepared-3, including the selected
~c charlist literal. Prior packets, failed run and later exact-group observation
remain immutable. Nothing here is a runtime acceptance or execution grant.

custody.py provides capped typed messages and publication by exclusive temporary
file, file fsync, hard link to a final path that refuses replacement, directory
fsync and temporary unlink. Immutable request/ACK/child/completion/exit messages
and journal transition state reject replay/conflicts. The runner retains a
proven leader/group in memory before a fallible durable journal write or ACK.
The journal binds PID/PGID/SID, nonce, phase, ordinal, recipe and request hash.

Only test phase can obtain work. Ordinals 0..6 identify version, first fixture's
CA/leaf/sign and second fixture's CA/leaf/sign recipes. The two fixture identities
mean successive fixture constructions; they do not assert ExUnit method order.
Each three-call recipe binds its exact private key directory. At most seven ACKs
are issued. ACKs bind the complete request, plan and deadlines. Signal delivery is
blocked for the final grant check/publication. Closing future grants does not
revoke a capability already issued: a cancellation-racing native launch remains
registered, bounded and cleanup-owned. A wrapper-observed signal keeps its local
launch path closed.

The wrapper never Popen's native work before exact ACK validation. Its child is
started without a new session/group option; exact child PID/group or rapid-exit
wait is recorded before output processing. Nonblocking output is capped at 64KiB;
native work is capped by five seconds and remaining work budget. Exact native
terminate/kill/wait and durable completion occur on failure. The wrapper holds
its group leader until a hash-bound exit grant or shared cleanup cutoff. Root
polls custody while reading stdout and during cleanup, retires the VM groups,
then drains every proven registered group before scratch removal.
The wrapper is single-threaded; its child pre-exec restores the previous signal
mask so the brief local spawn gate does not leave native TERM/INT/HUP blocked.

Lost leader and terminal group states never re-arm because a number reappears.
An incomplete handshake, prepublication/startup gap, journal error, missing exact
wait or group-loss uncertainty fails and preserves scratch. No unknown group is
discovered or killed. This remains a guarded local lifecycle, not an atomic OS
process-generation handle or whole-VM descendant guarantee. Arbitrary OS stalls
or hard kills may prevent bounded completion. Full failed state is retained.

Two independent prospective plans require separate exact single-execution root
releases after source review:

- control-plan.json runs only nine bounded fake-child custody controls. No
  Elixir/compiler, TLS or actual OpenSSL process is used. Controls cover happy
  custody; no ACK; journal failure before ACK; ACK/cancel race; native timeout;
  no-replace/typed phase/run and sticky terminal/lost identity checks;
  out-of-order registration; prepublication failure; and post-Popen/pre-child-
  record failure. Expected uncertainty cases must preserve scratch. Control pass
  means those safety assertions held, not that their deliberate failed scenarios
  became clean real-runtime runs.
- execution-plan.json runs fresh production/test VMs, retains the unchanged
  seven ordinary and two active-TLS methods, and adds exact typed custody
  evidence as the eighteenth required JSON artifact. It uses the real pinned
  OpenSSL executable through seven acknowledged recipes. Existing compiler
  zero-warning, KOL09 adverse-failure, source pins, output caps, strict output
  membership and 40/46/52/55 cutoffs remain in force.

Controls and real runtime have distinct fixed output directories and cannot be
replayed by either release. Mode-specific fake pause/failure seams are available
only to the controls' root-owned config; real config selects mode=real and the
actual pinned OpenSSL. No new service, dependency, product cleanup or separate
CI/security-investigation change is introduced. No control, compiler, formatter,
native-child or TLS execution occurred while authoring/freezing these sources.
