# Replay recovery during an iOS Starter build

Use macOS arm64, Python 3.14, and the selected Xcode 27.2 (27B52). The build
uses the generic iOS Simulator destination and disables code signing. It
requires no booted device.

## Prepare and admit the Starter inputs

Run from a clean Mixer checkout. The fixture needs these three Git objects.
If your clone is shallow, fetch any missing object from the Mixer remote.

| Input | Commit |
| --- | --- |
| Restore launcher | `57f3ed4f17b80f15fc6d646b14c6dbfa05bd7eea` |
| Starter CLI and helpers | `201ead70ff68bfe18de24c0642f518701459e0a4` |
| Starter SDK | `fad0d0b3e65fd3be3b49675601693e5d91999fbe` |

```sh
python3 -B tests/integration/hosted-expiry-restore/replay-starter.py --stage-only
```

The preparer builds the pinned CLI with its locked SwiftPM dependencies,
exports the iOS Starter, and writes `PASS_STAGE` and the receipt path. It
checks the pinned source, Swift lock correction, and dependency archives. It
starts no hosted service and sends zero build POSTs. A fresh debug CLI can
have a different hash because its build paths differ.

Set `stage_receipt` to the reported `result.json` path and use a new preflight
receipt path.

```sh
stage_dir="${stage_receipt%/*}"
stage_sha256="$(shasum -a 256 < "$stage_receipt" | cut -d ' ' -f 1)"
starter_cli="$(python3 -B -c 'import json, sys; print(json.load(open(sys.argv[1]))["commands"]["starter-export"]["argv"][0])' "$stage_receipt")"

python3 -B tests/integration/l07-ios-active-custody/run.py \
  --live --preflight-only \
  --stage-receipt "$stage_receipt" --stage-sha256 "$stage_sha256" \
  --cli "$starter_cli" --export "$stage_dir/starter/exported" \
  --receipt verification/local/l07-ios-preflight.json
```

Successful preflight records `live-inputs-admitted` and zero Xcode build
invocations. It checks the exact CLI, exported sources, lock, provenance,
and Xcode tool hashes against the staged input.

## Run the worker interruption

Use PostgreSQL 17, Elixir 1.20.4 on OTP 29, and Hex 2.5.1. Prewarm the
Hex registry cache and locked test dependency archives. If the cache or
Mix archives use private directories, pass `--hex-cache` or `--mix-archives`.
Use `--pg-bin` if PostgreSQL is installed outside the Homebrew default.

Repeat the preflight command without `--preflight-only` and with a new
receipt path. The replay interrupts only its original worker after the
owned Xcode launch. The replacement reopens the original ledger and
observes terminal custody, one Oban settlement, two logs, and three
authenticated downloads. See the recorded [live recovery receipt](../../../verification/receipts/l07-ios-active-native-recovery-20261120.json).

Remove only the stage directory created by your run once its command
receipt and the replay receipt confirm closure. Preserve any scratch
with a `HOLD.json` and use its custody record to locate the unresolved step.

## Attach one fresh v74 Simulator build

`attest_settled.py` is a separate, opt-in step for the operator of a fresh
managed compile on `44aecbeb6a82a4a93321cff6a8ab86c5aa421900`. The recovery
launcher above uses its pinned v55 overlay and removes its scratch at exit.
Call this step from the fresh v74 harness after the worker and processor have
closed and before the ordinary Phoenix server, PostgreSQL, and retained output
are torn down. Supervise the step with the harness's owned command runner.

Use a fresh private run root at mode 0700 with `pg/` and
`worker/operations.sqlite` in the maintained layout. Write a mode-0600
`settlement.json` in that root from the current run's observations:

- `base` is the v74 commit. `xcodeInvocations` is 1 and
  `liveCustodyPending` is false after positive closure.
- `commands.worker` and `commands.processor` have `exit: 0` and
  `groupAbsent: true`. Use the final worker if the harness reopened it.
  Copy `liveClosure` from the live receipt, including the exact terminal
  `claim`, `xcodeExit: 0`, and `xcodeReceiptSHA256`.
- Copy the live `binding` with `record_id`, `operation_id`, `ref`, `spec`,
  and `deadline_ms`. Copy `settled.journal` with its start and completed
  rows, `settled.artifacts` with the three descriptors, and
  `settled.manifestSHA256` from the same worker operation.

Keep the synthetic operator's subject and project membership stable on
this run. Supply a fresh browser session for completion and downloads and a
fresh human bearer with `mixer.build.attest` for the same fixture operator.
Keep both token files and the development key files at mode 0600 outside the
build root. Create the Ed25519 key after worker and processor closure, as in the
[prior local proof](../../../verification/receipts/l05-native-development-attestation-41a05264.json).
Enroll its public SPKI on the
ordinary Phoenix API using the [local attachment writer setup](../../../services/cmd/mixer-native-attest/README.md#configure-the-local-phoenix-attachment-writer).
Preserve the fixed IPv4 loopback origin, current database, and retained directory
if the API needs to restart for enrollment. The key files stay with the operator.
Pass the SHA-256 of the enrolled SPKI DER and the SHA-256 of the fresh receipt.

```sh
python3 -B tests/integration/l07-ios-active-custody/attest_settled.py \
  --run-root "$fresh_root" --settlement-sha256 "$settlement_sha256" \
  --api-port "$api_port" --pg-port "$pg_port" \
  --session "$session_file" --bearer "$bearer_file" \
  --private-key "$development_private_pem" --public-key "$trusted_public_pem" \
  --enrolled-spki-sha256 "$spki_der_sha256"
```

The PostgreSQL readback uses the maintained fixture database and loopback
administrator. Use `--pg-database`, `--pg-user`, or `--psql` to match the
fresh fixture. The step reads the exact operation and custody claim in one
worker-ledger snapshot. It requires the successful v74 launch and terminal
claim, the matching Swift and Xcode receipts, and the settled journal and
products. It authenticates and hashes all three downloads before compiling the
stock Go signer from the pinned successor Git tree using v74's module files.
The wrapper passes the admitted statement to `sign -expected-statement`. The
signer independently reads the products and checks that statement before
signing. The stock attach command submits the same envelope twice.
The step checks PostgreSQL after each response for one exact stored envelope and
the unchanged journal. Save the JSON output with the root run's evidence.

The step creates `attestation/` under the run root for the Go build, private
envelope state, and per-command stdout, stderr, and custody receipts. All
external commands have deadlines. A top-level `HOLD.json` remains if terminal
custody is unconfirmed, and the wrapper exits 74 without starting another
command. Preserve that run root and its logs. Root can clean a completed run
after observing terminal custody. If an attachment response is unconfirmed
and command custody closed, use the existing envelope and the stock attach
command to reconcile it after database readback.

```sh
python3 -B -W error::ResourceWarning -m unittest discover -v \
  -s tests/integration/l07-ios-active-custody -p test_attest_settled.py
```

## Replay one lost attach acknowledgement

Apply the fixture changes on public Mixer
`6c53e629dcbd396895a8072e6e6bb570152862c1`. The scoped starting point is
the [managed iOS stock-attachment receipt](../../../verification/receipts/l05-managed-ios-stock-attestation-20261121.json).
From the patched checkout, run the no-build admission first. This checks the
ordinary authenticated writer and proves that a selected response reaches a
clean TCP EOF with zero HTTP bytes. A missing bearer and a different target
return their normal HTTP errors. The exact target subsequently returns 404
because this control creates no build or attachment.

```sh
python3 -B tests/integration/l07-ios-active-custody/run.py \
  --v74-preflight --lost-attach-ack \
  --receipt verification/local/l07-lost-ack-preflight.json
```

For the root-owned replay, prepare the Starter inputs above from a clean
checkout using the pinned staging launcher. Use those same staged inputs and
a fresh receipt path.

```sh
python3 -B tests/integration/l07-ios-active-custody/run.py \
  --v74-attest --lost-attach-ack \
  --stage-receipt "$stage_receipt" --stage-sha256 "$stage_sha256" \
  --cli "$starter_cli" --export "$stage_dir/starter/exported" \
  --receipt verification/local/l07-lost-ack-root.json
```

The ordinary API keeps the exact IPv4 loopback signing origin. The fixture arms
one endpoint response after the signer has closed. Its one-shot marker matches
the stock POST's exact origin, route, and pins. Once the writer commits and
Phoenix selects 201, the fixture shuts down the connection's write half before
Bandit writes a status line. The first stock attach must exit 1 with its
unconfirmed-transport error and positive process closure. The wrapper opens a
new read-only PostgreSQL connection and requires one exact copy of the signed
envelope, the same settled build and closed lease, and an unchanged worker
ledger. Only then does it send the stored envelope once more with the public
key and require HTTP 200 duplicate. It rechecks the envelope file, PostgreSQL
row and worker ledger after the retry.

Expect stage `v74-attach-ack-replayed`, one build POST and Xcode invocation, one
sign, two attaches, and `attachmentHTTP: [null, 200]`. The suppressed 201 is
recorded in `lostAcknowledgement.selectedHTTP` along with the pre-retry database
observation and terminating command facts. On failure after attachment begins,
keep the indicated run and operator roots per the custody receipt. The
`attestation/persisted-before-retry.json` checkpoint is written only after the
fresh read confirms persistence. For manual reconciliation use the existing
envelope, the exact original origin and a fresh authorized fixture bearer.
