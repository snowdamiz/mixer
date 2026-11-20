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

## Admit an Android starter

1. Register the Pair24 Android export in the existing managed worker with the `unsigned-android-local-v1` recipe. Use a private copy of the export and make its files, directories, and recipe read-only before registering them. Pin the resolved Mixer executable path in both the recipe and its tool map. SwiftPM's `build/debug` directory can be a symlink. Use the same startup config, worker ID, and port that the local processor uses.
2. Run `prepare-starter.py --from-worker` with that startup config and its exact SHA-256, worker ID, and port. The script runs the existing worker verifier without starting a build. It checks the registered export, lock, recipe, tools, Xcode installations, and dependency mirrors before writing the descriptor.
3. As `browser_schema_owner`, apply [the Android starter migration](../../../hosted/priv/local_android_source_selection/20261119000000_local_android_source_selection.exs) after installing the local workspace build schema. The migration installs `public.mixer_local_android_starters` and `public.mixer_local_android_starter_v1(text,text,jsonb,boolean,text)`. The earlier iOS migration uses its existing directory and writer.
4. As `browser_schema_owner`, register the descriptor summary in `public.mixer_local_android_starters`. Set `organization_id`, `project_id`, and `application_id` from `spec`. Set `input_id` from `id`, `registration_pin` from `pin`, `spec` from the complete JSON `spec`, and `worker_configuration_pin` from `worker.configuration_sha256`.
5. Set the six existing `MIXER_LOCAL_STARTER_*` settings on the API. Use the descriptor path and hash for `REGISTRATION` and `SHA256`, and use the startup config hash for `WORKER_SHA256`. The existing interface exposes one operator-selected starter. An organization owner selects it through `POST /console-api/v1/source-starters` with the scope and `starter_id`.

The POST persists one locked `android` input. Its receipt can be submitted to the ordinary build API. The runtime rechecks the descriptor, export, lock, recipe, and tool digests at selection. The managed worker rechecks its installation and mirrors at dispatch. Disable starter discovery and selection by removing the six API settings together. Previously selected build inputs remain available.

Run the API and restricted SQL proof from a checkout with locked hosted dependencies installed. The proof uses inert source and tool fixtures, and the API queues one build with processing disabled.

```sh
python3 -B tests/integration/free-project-starter/registration-runner.py "$PWD" --android-starter
```
