# Actual native full-note draft and commit

PASS on the owned API37 arm64 emulator with staged V4, viewport clipping and whole-screen FieldRemoval routing. The real test-only OS InputMethodService entered a 100,000-UTF-8-byte decomposed note and Unicode title. Save draft produced one durable draft, with the original six tasks and ten outbox records unchanged.

A fresh app process restored the complete draft. The OS IME replaced its note with 25,000 emoji (exactly 100,000 UTF-8 bytes). One real Commit click preserved the draft UUID/date/category/attachment references, removed the draft and produced one entry and one entrySaved outbox record. Final state: six tasks, eleven outbox records, one entry, zero drafts. Prior task/outbox records and the separate original app were unchanged.

Direct results: result-draft.json and commit-action/result-commit.json. Full-note hashes, command output, installed APK identity and repository observations accompany those records. The commit-action run took 63.45 seconds. The original commit/ setup error and commit-r2/ selector error remain failed historical attempts; neither performed a mutation. Their separately retained outputs are not overwritten.

Every completed run restored original IME settings, removed the test IME and shut down the exact owned emulator. Final serial absence and unchanged external baseline were observed. The subsequent one-byte-over native refusal and recovery pass is recorded in ../fieldlog-ime-boundary-native-r268/REPORT.md.

These are emulator development results. Public V4 source-pair/generator adoption, UIKit, full IME/window/accessibility parity, physical phones, immutable packages and GA remain pending. No historical hold was released.
