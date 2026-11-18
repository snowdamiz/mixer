# Select a starter for a free project

In the local `workspace-builds` profile, an organization owner can select a provisioned iOS starter for a newly registered application. Open the application’s build page. When its first input page is empty, select the starter. Reload the page to check the stored input ID and source digest. Repeating the selection returns the same receipt.

## Local replay

Set `DELIVERY="$CHECKOUT/tests/integration/free-project-starter"` and choose a fresh owned directory for `OWNED`. Use the previously built public `mixer` host executable and the checkout SDK. This review used the executable recorded by `verification/receipts/public-cli-halt-restore-41a05264.json`. It reused that binary for create, export, and config validation.

```sh
"$MIXER" create Starter --application example.source.app --platform ios \
  --directory "$OWNED/generated" --sdk-path "$CHECKOUT/sdk"
"$MIXER" export "$OWNED/exported" --directory "$OWNED/generated"
"$MIXER" config validate --directory "$OWNED/exported"

python3 -B "$DELIVERY/run-proof.py" "$CHECKOUT" "$DELIVERY/registration-runner.py" \
  "$OWNED/exported" "$MIXER" "$EXPORT_SHA256"
python3 -B "$DELIVERY/run-proof.py" "$CHECKOUT" "$DELIVERY/registration-runner.py" \
  "$OWNED/exported" "$MIXER" "$EXPORT_SHA256" --chrome "$CHROME"
```

Set `EXPORT_SHA256` to the public export command's digest. The runner uses the checkout's locked console and hosted dependencies, PostgreSQL 17, a fresh real Phoenix session issued by the loopback test identity provider, and disposable test data. Its read-only worker check uses the exact spec reconstructed from the SQL row after the browser action, authenticates a loopback query, verifies source and recipe bytes, and checks that the worker ledger recorded zero starts. The SQL and HTTP checks compare all persisted source, lock, and recipe fields, including the source reference.

Operator provisioning uses the opt-in migration at `hosted/priv/local_source_selection/20261118000012_local_source_selection.exs`. From the hosted checkout, run `python3 -B "$DELIVERY/prepare-starter.py" --from-worker "$DESCRIPTOR" "$STARTUP_CONFIG" "$STARTUP_SHA256" "$WORKER_ID" "$PORT"`. The descriptor omits the worker token. Install its exact organization, project, application, input ID, pin, and spec as a privileged provisioning action. The application runtime reads the descriptor and separate startup digest pin through `MIXER_LOCAL_STARTER_ORGANIZATION`, `MIXER_LOCAL_STARTER_PROJECT`, `MIXER_LOCAL_STARTER_APPLICATION`, `MIXER_LOCAL_STARTER_REGISTRATION`, `MIXER_LOCAL_STARTER_SHA256`, and `MIXER_LOCAL_STARTER_WORKER_SHA256`.

The proof covers one operator-provisioned iOS export for one fresh app. Phoenix and the console were built locally for the fixture. Worker admission was exercised with a signed query and zero starts. Product dispatcher setup, native build execution, SwiftPM package policy, device behavior, and release qualification are outside this result. This verifies the first-source slice of L06.
