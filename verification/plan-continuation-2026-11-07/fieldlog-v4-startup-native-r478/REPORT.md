# Public V4 native entry flow on API36

PASS for exact public Mixer416 and the reviewed R454 FieldLog V4 app. Four real instrumentation phases use distinct app PIDs: Save Draft, reopen, Commit, verify. The public native editor accepts the exact 100,000-UTF-8-byte Unicode/newline note; refuses 100,001 bytes without truncating the accepted note; and accepts valid recovery input. Save Draft is invoked once, and Commit is invoked once.

Root observes repository bytes after each phase. Draft and reopened snapshots are byte-identical. Commit and the subsequent fresh-process verification are byte-identical. The draft UUID becomes the one durable entry UUID; the draft disappears and exactly one `entrySaved` outbox record is added. The original project/outbox record, task list and attachments remain unchanged. This instance began with zero tasks and one project-created outbox record; it does not establish Task Save or preservation of an existing populated production workspace. Other app stores were not used.

Exact note SHA-256: `9130b7d9e643c9ec1ab1940d76a55a5a47b4d28599e1a24e3d04542ae5affdef`.

`acceptance.json` and `result.json` identify the signed APK, per-phase workspace hashes and distinct PIDs. Each `instrument-*.stdout` records its PASS marker, code0 and `cleanupComplete=true`. The first launch screenshot/hierarchy and full logs are retained. That screenshot reveals a separate app-private system-bar contrast regression; R492 is restoring the previously accepted R202 implementation without changing the V4 contract.

Cleanup positively observes emulator exit0, owned process-group absence, serial absence and unchanged external device baseline before deleting the exact disposable AVD. No historical hold is released. The prior R468 initial-form timeout is retained and remains unattributed; its expected output constants are not interpreted as actual Save evidence.

This is API36 arm64 emulator development acceptance through public View/InputConnection and public SDK boundaries. OS IME/keyboard parity, TalkBack, UIKit/PhotosUI, physical phones, immutable published packages and GA remain pending. Fresh Apple AX trust R490 is false; no iOS Simulator was created or booted.
