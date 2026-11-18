# Replay an interrupted FieldLog entry sync

This macOS test saves an entry and JPEG in FieldLog while offline. A loopback
backend commits the entry and photo to SQLite, then cuts the response short.
FieldLog reopens with the event still queued. Retrying that event must return a
matching receipt, remove only that event from the queue, and leave exactly one
copy of the JPEG on the server.

From the Mixer checkout, use macOS with Xcode, Git, Python 3.12 or newer, and
a local FieldLog checkout containing commit `552559d2d3278abb9b1aa7dcf0288102c09a202b`.
Set `FIELDLOG_CHECKOUT` to that checkout.

```sh
python3 -B tests/integration/fieldlog-entry-sync/run.py "$FIELDLOG_CHECKOUT"
```

The runner extracts the pinned Swift models, storage code, and repository
tests into private scratch. It applies the two downstream patches there,
builds the Swift client, and starts the HTTP server on an ephemeral loopback
port. It provisions two synthetic identities. The run needs no account setup,
payment service, or mobile device. To retain the JSON result, append
`--receipt /path/to/new-receipt.json`.

The result includes the saved event ID, remote row counts, JPEG size and
SHA-256, and cancellation and retry outcomes. This fixture covers one JPEG
per entry and retries the complete event after an incomplete acknowledgement.
The original replay checks the full-entry upload path.

The client and server implementations are in the [FieldLog source patches](../../../verification/fieldlog-entry-sync/).

## Replay a resumable photo upload

Use the same pinned FieldLog checkout. The runner applies the committed
entry-sync and backend fixtures, then applies the photo resume patch in a
private copy of the pinned sources. You can run it with local changes in
FieldLog because it reads the pinned Git object.

```sh
python3 -B tests/integration/fieldlog-entry-sync/resume.py "$FIELDLOG_CHECKOUT"
```

Use `--receipt /path/to/new-receipt.json` to save the result. Use
`--exclude-port PORT` for each reserved port. The listener binds to an ephemeral
IPv4 loopback port, and the runner verifies that the port can be rebound
after the listener and its request threads close.

The replay drops a chunk receipt, cancels an in-flight Swift task, and resumes
from the SQLite prefix verified by SHA-256. It cuts the final receipt short and
reopens the workspace before retrying. The remote database must contain one
event and one byte-identical JPEG. The local repository must retire only the
selected event and preserve both JPEGs and the unrelated outbox entry.

The backend returns the exact chunk-end offset for a byte-identical retry,
including a retry after finalization. Query the manifest route for the current
durable offset. Conflicting chunks and unauthorized scopes leave the database
unchanged. The original inline upload can also finalize an exact partial upload.

The replay covers the macOS repository and loopback HTTP with synthetic
accounts and SQLite. Mobile queue UI, public SDK capability transport, and
deployed authentication require separate verification.
