# Signed cold-start execution

`MixerActivation` composes the durable `MixerUpdates` verifier/store with the owned
`MixerRuntime` session API. It executes the currently bounded Wasm profiles. Full
Swift/WASI guest execution, capabilities, UI transport and FieldLog adoption remain
open; this package does not represent D3–D5 or mobile lifecycle qualification.

The installed app constructs `InstalledExecution` with its exact runtime
fingerprint, explicit VM profile, native ceilings and startup export. The fingerprint
must describe the complete installed native build, including this policy. Generating,
signing and publishing that immutable build identity remain separate work. A release
cannot select a profile, entry point or native adapter. This slice rejects any
installed capability map or signed grant requiring a guest capability import.

Open `ColdStartRuntime` with pinned `ReleaseVerifier` and `ColdStartConfiguration`.
Supply the signed manifest, signed assignment and bounded download chunks, then
finish download. The store verifies signatures, compatibility, replay and payload
hash before the owned VM validates the complete executable. `VMValidator` does not
instantiate memory or reserve a session, so verification can run when session
capacity is occupied. No accepting validator hook is exposed by this composition.

`start(now:)` selects exactly once per feature process session. Its verified token
and copied bytes travel together. It starts a native-owned VM session and invokes
the configured zero-argument startup export off the UI actor. Signed memory/fuel
limits intersect the installed ceilings. `memory_bytes` bounds linear memory in
whole pages, rounded down; the VM's unchanged decoder/frame ceilings still apply.
This does not establish a total process RSS budget.

The signed startup duration includes selection and executable validation, then
construction and export invocation. A watchdog cancels the published session and
a monotonic check discards late results even if the watchdog is delayed. Validation
and construction have fixed profile bounds but cannot be forcibly preempted by a
wall-clock timer. A cancellation arriving before session publication retires the
subsequently created instance. The host should close the runtime at lifecycle end;
close invalidates ownership while admitted native work unwinds. Cancellation does
not roll back already executed instructions.

Successful startup returns `.guest` with its source, artifact identity and typed
result. Further `invoke` calls retain guest memory/globals and admit one operation
at a time. No raw guest session or pointer escapes this owner. Installed host code
calls `markHealthy` after actual required UI/restoration milestones; the updater
also enforces its monotonic observation period. A guest return value is not health.

A failed provisional startup records only known VM traps as deterministic guest
failures. Cancellation, native argument errors, unsupported floating-point host
state and uncertain native failures do not count as guest traps. The updater
quarantines repeated deterministic failures. At most one retained healthy guest
is attempted after candidate startup failure; a second failure selects native
fallback. A failure after successful startup closes that guest and returns an
error with a `.nativeFallback` snapshot; it does not switch to another guest during
an active feature flow. The installed application must launch its real compiled
fallback and reconcile its app state. Healthy-guest execution failures select
native fallback for this process; durable healthy-guest quarantine policy and full
state/effect migration remain open.

If opening the durable store itself fails, the embedding handles that error by
launching its compiled native feature. It must not erase replay state to recover.
The package has no HTTP download adapter. Offers/chunks are supplied before
startup; background delivery while an active feature runs is not yet exposed.

```sh
python3 runtime/build-vm.py --revision 64123c5 --target host --output activation/.build/native-vm
swift test --package-path activation -Xlinker -L"$PWD/activation/.build/native-vm/lib"
```

Tests generate ephemeral signing keys and originally authored small Wasm fixtures.
They execute the real interpreter through both strict v1 and signed v2 metadata,
retain memory, earn health, reopen offline, enforce actual signed limits, recover
from traps, preserve unrelated draft bytes and exercise close/cancellation. They
do not execute full Swift guests or qualify physical OS kills/power loss, minimum
devices, performance, stores, hosted publication or complete security review.
