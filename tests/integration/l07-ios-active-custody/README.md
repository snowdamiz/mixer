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
