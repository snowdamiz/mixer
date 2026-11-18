# First source selection review

Apply `product.patch` and then `admission.patch` to application-registration commit `668815561d4e54379ca096f6d55ea84877c8610d`. The review used an isolated Git projection. Both patches also applied and reversed cleanly on the observed later checkout head `e7982e3204342e4dc14a12b1c4a8290876de4546`.

The starter picker appears for an organization owner in the opt-in workspace-builds profile after a terminal, empty first input page. The committed empty-application registration gate stays in force. The server checks the live organization-owner membership before reading the pinned export and rechecks the browser lease before querying or writing the starter record. The first selection records one catalog input, identical replays return the same receipt, and a fresh catalog read returns the stored input. The existing retained-build log paths and contracts retain their hosted v37 bytes.

The hosted v38 source selection adds six paths and changes fourteen, for 404 pinned sources. Its predecessor is the exact hosted v37 authority, including its preimages. The 20 default hosted migrations retain their committed inventory. The source-selection migration is an explicit opt-in after the build-create catalog. Source150 changes only at the sealed workflow binding.

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
