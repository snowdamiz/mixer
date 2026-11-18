# Resolve competing offline FieldLog task edits

Run from the Mixer root on macOS with Swift 6, Python 3 and a local FieldLog checkout. The replay saves edits in two independent workspaces while the backend is offline, reconnects to a local SQLite service, and resolves the title conflict while retaining the peer's assignee. It also retries after a lost acknowledgement and checks that a later edit and unrelated outbox events survive.

```sh
mixer=$PWD
fixture="$mixer/tests/integration/fieldlog-task-sync"
run=$(mktemp -d "$mixer/verification/local/fieldlog-task-sync.XXXXXXXX")
mkdir "$run/source"
git -C "$FIELDLOG_CHECKOUT" archive 552559d2d3278abb9b1aa7dcf0288102c09a202b | tar -xf - -C "$run/source"
cd "$run/source"
git init -q
git apply "$fixture/fieldlog-task-conflict.patch"
git apply "$mixer/verification/fieldlog-entry-sync/fieldlog-552559d2-local-backend.patch"
git apply "$fixture/fieldlog-saved-task-sync.patch"
python3 -B verification/host/replay-saved-task-sync.py "$run/replay"
```

This exercises the ordinary editor model, the on-disk repository, and authenticated loopback HTTP with synthetic tokens. Mobile screens and automatic background sync need their own checks.
