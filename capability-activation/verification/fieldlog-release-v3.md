# Signed FieldLog release-v3 host replay

Run from a graphical macOS session with Xcode, the pinned SwiftPM and Go dependencies, and Accessibility access for the
test application and its AX client. The replay requires both Wasm payloads
and the owned VM archive from
[the compact Swift FieldLog receipt](../../verification/receipts/fieldlog-compact-abi2-41a05264.json).
It checks their digests before compiling or serving them.

```sh
python3 -B capability-activation/verification/fieldlog-release-v3.py fieldlog-v3-fresh
```

The run uses an owned AppKit test window, an isolated loopback
`services/cmd/mixer-service` process and store, and one app-private recovery
directory. The test presses the real SwiftUI buttons through a separate Accessibility
client restricted to the parent test application. It observes the actual
native display path. It builds
the host once and closes each owner before opening the next launch. It verifies
the selected candidate, effect readiness, visible-screen health, event delivery,
and state read back from disk. The offline reopen follows a partial write to
the installed download store after sequence 4 is accepted. The service has
exited before that reopen.

## Reuse the public fixtures

Use `verification/local/<run>/public-fixtures/` as a unit. It contains the exact
payloads, their separately signed manifests, assignments 1–4, pinned public root,
identity, host registration, and checked installed materials. The key is generated
in memory for the run. The fixture uses the two imported Swift module bytes
directly, with no guest capability grants. The source-map file is an empty
development metadata object.

1. Register `host.json` and `roots.json` in the development service. Use an
   independent local publisher token scoped to organization `mixer-local` and
   project `fieldlog`.
2. For each variant, PUT to `/v3/orgs/mixer-local/projects/fieldlog/artifacts/<digest>`
   and POST to that project's `/releases/validate` route. The PUT body has
   `signed_manifest` containing the corresponding manifest file's JSON value
   and `payload` containing the base64 of the exact Wasm file. The validation
   body has `artifact_sha256`. The digests are the `assignment.artifact_sha256`
   values in sequences 1 and 2. Give each mutation a unique idempotency key.
3. POST `{"signed_assignment": <signed assignment value>}` to the project's
   `/channels/beta/publish` route for sequences 1 and 2. Post sequence 3 to
   `/channels/beta/rollback` to return to baseline. Sequence 4 uses `publish`
   again and is the partial-write control.
4. Fetch `/v3/updates` with the host's complete scope and runtime,
   `channel=beta`, and `installation=fieldlog-local-1`. Fetch the returned
   scoped artifact. Pass the decoded signed envelopes and payload to
   `beginDownload`, `appendDownload`, and `finishDownload` on the owner before
   calling `start`.

## Native consumer handoff

The Apple consumer can construct `InstalledCapabilityExecution` from the exact
identity, trust roots, and material files, then open `CapabilityGuestUIRuntime`
with its app-private directory. Mount `MixerGuestScreen` with the runtime's
`presentation` to earn native first-screen health. For an application with its
own linked identity, issue a fresh development fixture bound to that exact
identity and platform. Editing the test descriptor invalidates these existing
assignments and manifests. The host proof uses test metadata for the iOS
descriptor and an actual macOS VM archive. It supplies no build attestation.

Android's ABI2/UI1 presentation lifecycle and C progress endpoints exist in
`CapabilityGuestUIAndroidBinding.swift` and `CapabilityGuestUIAndroidProgress.swift`.
The public durable Guest UI runtime currently compiles only with SwiftUI and
MixerApple. An Android embedding needs the signed durable core connected to the
Android binding and its retirement owner, with real Android first-screen
observation, before it can consume a separately scoped Android fixture.
The bundled Feature UI V3 route is a different contract.

The exact compact guest keeps task state in memory. Durable evidence from this
run covers installed release state, previous health, assignment high-water, and
the partial payload offset. App-private FieldLog task data migration and
persistence require the full FieldLog product integration.
