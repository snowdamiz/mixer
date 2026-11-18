# Replay an installed FieldLog iOS upgrade

Build two versions of FieldLog with the same bundle ID, `dev.mixer.fieldlog`.
The test creates an ordinary workspace, imports a PNG through the iOS Files
picker, and replaces the installed app. It then reopens the saved draft,
edits it, and checks the committed entry after a cold launch. This covers the
installed-app portion of Mixer product plan §22.2.13.

## Build from pinned local checkouts

Use Apple silicon, Xcode 27.2 (27B52), Git, and Python 3.12 or newer. The
build and replay use the same Xcode selection. Set `DEVELOPER_DIR` for all
commands if the pinned Xcode differs from the active `xcode-select` installation.

Use local checkouts of `snowdamiz/fieldlog` and `snowdamiz/mixer` that contain
the following public Git objects. The scripts read the pins directly, so the
checked-out branches and uncommitted changes can differ.

| Checkout | Revision | Role |
| --- | --- | --- |
| FieldLog | `552559d2d3278abb9b1aa7dcf0288102c09a202b` | Both app builds |
| Mixer | `63a76a4c34ff01f50b9b38a936bc81c87f462c95` | SDK for 0.1.0 (1) |
| Mixer | `1a56d6d0f28298c8805dfd6c1e5738819dcf9a7d` | SDK for 0.1.1 (2) |

Set `MIXER_CHECKOUT` and `FIELDLOG_CHECKOUT` to the absolute checkout paths.
From the Mixer checkout, run:

```sh
test_dir=tests/integration/fieldlog-ios-installed-upgrade
work=$(mktemp -d "${TMPDIR:-/tmp}/fieldlog-ios-upgrade.XXXXXXXX")

python3 -B "$test_dir/build-pair.py" \
  --mixer-git "$MIXER_CHECKOUT" --fieldlog-git "$FIELDLOG_CHECKOUT" \
  --output "$work/products"

python3 -B "$test_dir/run.py" --artifacts "$work/products" --check
python3 -B "$test_dir/check-verifiers.py" \
  --fieldlog-git "$FIELDLOG_CHECKOUT" --artifacts "$work/products"
```

The builder exports the pins to disposable directories and applies the
included Files import overlay to each FieldLog export. The test selects the
image with `UIDocumentPickerViewController`. FieldLog uses its ordinary JPEG
resize and attachment storage path. Xcode builds for the generic iOS Simulator
destination. The builder signs the two apps and the test runner ad hoc and
removes the intermediate exports, logs, and build caches when it returns.

The receipts identify both source trees, the exact bundle and executable
hashes for this build, and the Mixer SDK objects in the app link maps.
Fresh builds can produce different binary hashes. The host checks verify
the signatures and all four XCTest manifests. They also exercise the pinned
FieldLog repository and JPEG readback on macOS and use mocked device
responses to check exact targeting, cleanup, and custody holds. The build
and host checks need no device, account credentials, or payment service.

## Run on a root-owned Simulator

Use the repository's Accessibility and keyboard-readiness procedure in
`AGENTS.md` before running XCTest. Choose a new output directory under
ignored `verification/local/`. The wrapper checks Accessibility before
device discovery and again before creating its disposable iPhone 17 Pro on
iOS 27.0 (24A434).

```sh
python3 -B "$test_dir/run.py" --artifacts "$work/products" \
  --output "verification/local/fieldlog-ios-upgrade.$(/usr/bin/uuidgen)"
```

The wrapper excludes the held Simulator from its inventory. Pass
`--exclude-simulator UUID` for each additional held UUID. It compares the
other devices before creation and after retirement. It boots, tests, shuts
down, and deletes only the newly registered UUID. A custody hold preserves
the run and the owned device for root. A terminal pass requires verified
device removal and matching external identities, registrations, and states.
The raw snapshots also retain usage timestamps and data and log sizes, which
can change while another device is in use.

The host seeds the PNG in Documents and writes a random continuity marker in
Library before the first app launch. XCTest creates the project, task and draft
through the app and imports the PNG through the system picker. The runner
removes the seed from the app's current Documents folder, then cold-reopens
the draft before installing build 2 over build 1.

Each readback checks the installed app tree and executable, the installed
test executable, and the original marker. The snapshots record the container
path and filesystem device and inode numbers when available. The direct
replacement must preserve the physical directory when both observations
have an identity. If XCTest moves the data to a new path, the runner records
both identities and verifies continuity through the marker and durable data.

The replacement must preserve the workspace and JPEG bytes before its
first launch. The edit must preserve the project, task, attachment and
earlier outbox records, commit the original draft as an entry, and add one
entry operation at the new revision. The final cold launch reads the edited
entry, photo and pending queue. The run writes snapshots, screenshots,
command receipts and `result.json` under the selected output directory.

Delete your disposable products directory after the host checks or root run.
Keep any runtime output identified by a custody hold.
