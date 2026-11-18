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
The mobile queue UI and partial photo upload require separate verification.

The client and server implementations are in the [FieldLog source patches](../../../verification/fieldlog-entry-sync/).
