# FieldLog iOS local account replay

The ordinary iOS app uses a separate account route in Debug when launched
with `--fieldlog-local-account`. A regular launch opens the legacy workspace.
Account preferences and workspace files live under
`FieldLog-Accounts/<account>/<workspace>/<project>` in Application Support.

The app opens the FieldLog-owned local issuer in the system browser and
accepts `com.fieldlog.dev.ios://account/callback` at its root. Before exposing
the workspace or the TaskSync grant, it confirms the exchanged bearer on
`GET /v1/account/session` and checks the account, workspace, project, expiry,
and the current request generation. It saves the confirmed expiry in the
native credential store. See the [backend contract](../fieldlog-account/README.md)
for disposable synthetic account provisioning and the wire format.

## Replay on a Mac

Use two empty private directories. The host test needs port 8765 free.

```sh
fixture="$PWD/tests/integration/fieldlog-account-ios"
bash "$fixture/prepare.sh" "$owned_source"
sh "$fixture/run-checks.sh" "$owned_source/source/fieldlog" "$owned_host"
```

The prepared tree is `ebb53f9e95534c342966d701ee9dfd45374b267e`.
Its shared `FieldLogAccount.swift` has Git blob
`d6e383eeca9756d249c692cd01173951b8b9a419` and SHA-256
`e0511a3d374ccbd27d1ea38beb9e55d437e730513c9902f1289c04a25d23eacc`.

The replay uses the production Apple HTTP adapter, the actual SQLite
listener, TaskSync, and the ordinary workspace repository. The harness
drives the browser form over HTTP, delivers the returned URL to the shared
owner, and uses an in-memory credential store. It checks confirmation,
late response refusal, sign-out, and draft, photo, and outbox preservation.
The unsigned generic iPhoneOS build verified the callback registration.
Native browser delivery, Keychain, and ordinary UI behavior remain open.
[Verification receipt](../../../verification/receipts/fieldlog-ios-account-confirmed-owner-ebb53f9e.json)
