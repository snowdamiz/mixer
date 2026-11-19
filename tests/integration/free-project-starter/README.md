# Select a starter for a free project

In the local `workspace-builds` profile, an organization owner can select a provisioned iOS starter for a newly registered application. Open the application’s build page. When its first input page is empty, select the starter. Reload the page to check the stored input ID and source digest. Repeating the selection returns the same receipt. Existing legacy inputs remain readable, and an exact legacy registration can replay its stored selection.

## Local replay

Set `DELIVERY="$CHECKOUT/tests/integration/free-project-starter"` and choose a fresh owned directory for `OWNED`. Use a public `mixer` host executable built from an intact source tree. The retaining build reads that tree for its provenance.

Extract `sdk` from Mixer commit `fad0d0b3e65fd3be3b49675601693e5d91999fbe` into `$OWNED/pinned`. In a separate acquisition step, use `git archive --format=tar` at the revisions in [the SDK lock](../../../sdk/Package.resolved) to create `swift-crypto.tar` and `swift-asn1.tar` under `$OWNED/archives`. Use the repositories recorded in [the dependency inventory](../../../THIRD_PARTY.yml).

```sh
export MIXER_STARTER_WORKER_CODE="$CHECKOUT/hosted/priv/development"
"$MIXER" create Starter --application example.source.app --platform ios \
  --directory "$OWNED/generated" --sdk-path "$OWNED/pinned/sdk"
"$MIXER" export "$OWNED/original" --directory "$OWNED/generated"
python3 -B "$DELIVERY/prepare-starter.py" --local-sdk \
  "$OWNED/local-sdk" "$OWNED/pinned/sdk" "$OWNED/archives"
"$MIXER" upgrade "$OWNED/derived" --directory "$OWNED/original" --sdk-path "$OWNED/local-sdk"
EXPORT_SHA256=$(python3 -B "$DELIVERY/prepare-starter.py" --complete-export "$OWNED/derived")
"$MIXER" export "$OWNED/exported" --directory "$OWNED/derived"
"$MIXER" config validate --directory "$OWNED/exported"

python3 -B "$DELIVERY/run-proof.py" "$CHECKOUT" "$DELIVERY/registration-runner.py" \
  "$OWNED/exported" "$MIXER" "$EXPORT_SHA256"
python3 -B "$DELIVERY/run-proof.py" "$CHECKOUT" "$DELIVERY/registration-runner.py" \
  "$OWNED/exported" "$MIXER" "$EXPORT_SHA256" --chrome "$CHROME"
```

Compare `EXPORT_SHA256` with the digest printed by the final `mixer export`. The local SDK contains the verified dependency sources and notices. The starter registration binds that SDK, the complete CLI export, and the new build recipe.

The selection runner uses the checkout's locked console and hosted dependencies, PostgreSQL 17, a fresh Phoenix session from the loopback test identity provider, and disposable test data. After selection, it verifies the SQL input against an authenticated worker query and checks for zero starts.

Operator provisioning uses the opt-in migration at `hosted/priv/local_source_selection/20261118000012_local_source_selection.exs`. From the hosted checkout, run `python3 -B "$DELIVERY/prepare-starter.py" --from-worker "$DESCRIPTOR" "$STARTUP_CONFIG" "$STARTUP_SHA256" "$WORKER_ID" "$PORT"`. The descriptor omits the worker token. Install its exact organization, project, application, input ID, pin, and spec as a privileged provisioning action. The application runtime reads the descriptor and separate startup digest pin through `MIXER_LOCAL_STARTER_ORGANIZATION`, `MIXER_LOCAL_STARTER_PROJECT`, `MIXER_LOCAL_STARTER_APPLICATION`, `MIXER_LOCAL_STARTER_REGISTRATION`, `MIXER_LOCAL_STARTER_SHA256`, and `MIXER_LOCAL_STARTER_WORKER_SHA256`.

This replay checks starter selection with Phoenix, PostgreSQL, and the console. The worker receives a signed query and records zero compiler starts.
