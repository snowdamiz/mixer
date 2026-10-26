# Preserved remote envelope artifact

`envelope.zip` is the exact GitHub artifact 12631406070 from Engine run
40273904826, attempt 2, source commit
`0b8e3fd8bdd86902f7d9d28e0cba01bcdbb5ce1c`. Its SHA-256 is
`353ef152950ed788ace0c466340931ccaf2a686deb65807fa303acca9d4f6d51`,
matching the authenticated artifact metadata. The 566,414-byte archive preserves
all 252 members / 63,625,543 expanded bytes. No artifact code was executed.

`extraction-manifest.json` records every expanded path, length and SHA-256.
`audit.stdout.json` records the successful root read-only evidence audit;
`audit.command.json` binds its exact helper and command. The audit checked actual
Rust 1.98.1, source revision/tree, accepted fixture/runner identities, all command
streams and per-command receipts, methods, API diagnostic spans, layouts,
comparison counts, retained files and cleanup.

Paths under `output/` in audit commands are local expanded recovery paths. For
delivery, the ZIP is the lossless source of those files; retaining the expanded
directory as ordinary Git files is unnecessary. To recover it, use a fresh owned
directory, reject absolute/parent/duplicate/link paths, bound member count and
expanded bytes to this manifest, and verify every member before consuming it.
Do not execute recovered sources or binaries. The root audit helper consumes
recovered output as data and imports only the separately hash-bound accepted
repository validator.

This artifact qualifies the standalone fixture envelope on that compiler. The
whole workflow's terminal status is recorded separately. Failed attempt 1 is
preserved separately and contributes no successful test evidence. No semantic,
live VM, native/device or GA qualification follows.
