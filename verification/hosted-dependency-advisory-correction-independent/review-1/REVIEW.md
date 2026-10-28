# Independent dependency lock-resolution source review

Do not release resolution-v2 yet. Two narrow controller/environment corrections
are required; neither changes the two selected dependency versions or authorizes
product compilation/tests. The source-only audit verifies controller
f4369b8fa608521da8e95a301c85966aae34fa5303f122a2edc1eccae83cc556 and
plan c0cd50892185a8e0614486c1e3f478c997ba7a8c7405935dcdf361d72e71df1c.

## R01 — cancellation after work can report success (P2)

The signal handler sets CANCELLED and STATE.cancelled. guard deliberately ignores
cancellation during reserved cleanup/posthash. After successful_work is set, a
SIGINT/SIGTERM during those stages therefore does not add an error. The final
success condition checks work/errors/scratch but not CANCELLED, allowing
resolved_two_pins_only and exit zero with cancelled: true. This is a source-derived
receipt counterexample, not a replayed fault.

Require a documented finite signal observation cutoff after cleanup/posthash and
before the bounded final receipt. Cancellation received or pending through that
cutoff must prevent resolved status and exit zero; retain it explicitly. Preserve
nonraising handlers and reserved cleanup despite cancellation. Signals later than
the documented cutoff must be outside the receipt's stated observation scope.

## R02 — native hostname helper is outside proven custody (P2)

Installed primary OTP 29.1.1 sources establish the dispatch path without a process
or DNS probe. inet_config.erl sets lookup to [native] by default. inet.erl routes
that method to inet_gethost_native, whose do_open_port starts the inet_gethost
executable with open_port(spawn_executable). The controller accounts only for
its retained command process group, so that group's absence alone is not proof
about a separate port helper. This review makes no assumption about the helper's
PGID and does not claim it was launched by this unexecuted controller.

Select a private prewritten, hash-bound ERL_INETRC containing
{lookup, [dns, file]}. before all five commands. inet_config reads that file after
OS defaults; inet's dns/file branches use inet_res and inet_hosts. Exhausting
those methods does not append native fallback. inet_res performs the DNS client
work through OTP UDP sockets. This removes the known ordinary native-lookup
helper path without a broad process inventory or a DNS probe. Pin/recheck the
file and environment in the successor and record the selected policy. No native
fallback or automatic retry is selected if resolution fails.

Root intentionally retains the shell HOME under environment guidance. That is
compatible with the explicitly narrower private Mix/Hex/config/cache/project
isolation; this is not an OS sandbox. If BEAM startup-home isolation is needed,
use a scratch -home argument without changing shell HOME. Root separately checked
the current user .erlang absent and waitid/WNOWAIT available; those are root
observations, not independent runtime probes in this review. The primary source
hashes and relevant excerpts are retained in audit.json.

## Otherwise scoped and reviewable

The controller uses a private marked scratch, copies only the 133 hash-bound Hex
2.5.1 archive files, clears inherited environment, and directs Mix/Hex/deps/build
state into scratch. Five exact sequential commands are version/version/unlock
Bandit+JOSE/get prod/offline locked recheck; no local.hex, deps.update, compile,
test, application, DB, provider, OpenSSL or callback harness is selected. HTTPS,
registry-signature and repository-origin checks remain enabled.

Each command has only the remaining 40-second work budget. WNOWAIT retains the
direct leader until final group signals/reap, with no group signal after reaping.
Unknown custody/closure preserves scratch and fails. Output caps, private-tree
disk/entry/symlink checks, 46/52/55-second reserved stages and per-entry marked-tree
cleanup are explicit; OS syscalls are accurately excluded from a real-time quota
claim. These are source properties, not tested platform cleanup behavior.

The only proposed mix.exs changes are Bandit 1.14.0 and JOSE 1.11.13. Success
requires actual Mix-generated 21-entry output, official saved candidate outer
checksums, all nineteen other complete-entry hashes unchanged, identical bytes
after the offline locked recheck, closed groups, stable sources/tools and removed
scratch. No checksums or lock records are invented by this review. The five-member
successor seal, original sixteen-member preparation, seventeen input pins,
thirteen canonical inputs, thirteen selected tool files, Hex archive and prior
fifteen-entry advisory packet all pass fresh byte checks.

Recommend a separately sealed successor containing only the coordinated signal
and resolver-policy corrections, then focused review and exact root release.
This review imported/executed no controller and ran no Mix/compiler/process/DNS
probe. A successful resolution will still need lock-diff review and later
functional/remote CI validation; it cannot qualify HTTP/2 wire behavior,
deployment, provider, native/device or GA gates.
