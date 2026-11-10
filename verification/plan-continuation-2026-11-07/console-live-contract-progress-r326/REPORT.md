The workspace’s **Try again** action now recovers an unavailable browser session through the existing `/auth/session` read and resumes directory loading after a valid authenticated answer. A ready session continues to retry the failed organization page with its original cursor. No API or authentication authority changed.

`change.patch` contains six files: four frontend wiring/binding sources and two test files. `afterimages/console/` contains the exact changed-file bytes; `changed-files.json` contains before/after SHA256 values. Standard patch dry-run and actual application to copied beforeimages both passed. The canonical changed files still matched their initial digests when packaging finished.

Validation:

- The original-source witness failed: retry issued no second session request. Raw output is `baseline-test.stdout`.
- Final focused tests pass all seven top-level cases, including 14 nested browser-session controls and four nested workspace-binding controls. These counts overlap. Controls cover session failure/recovery, preserved directory cursor, repeated failure, signed-out answers, hidden/disposed rejection, and existing epoch fencing.
- Strict TypeScript checking and the Vite production build pass (`build.stdout`).
- The broader isolated run passes 147/149 top-level tests. Two parity cases fail because the console-only copy lacks website branding and hosted Scope source inputs. Those failures remain in `full-test.stdout`; the full suite is not claimed passing.
- An intermediate focused run retained an existing exact-JSX assertion failure after adding the retry prop; its expectation was updated and final focused execution passes.

`commands.json`, `tool-versions.json` and `source-inputs.json` record exact commands, tool versions, environment and source digests without using Git. Four test-file workers ran alongside one short production build on the 15-core / 48-GiB host; no resource failure was observed. These functional runs establish no performance result.

Root can apply `change.patch` and review the exact afterimages. Remaining composition work is a real authenticated same-origin browser/session run and the full console suite with website/hosted parity inputs available. Build/release live transports and billing are outside this slice. Session checks retain the existing unavailable state while pending. No browser, native, device, deployment, published-package or GA qualification is claimed.

Only this task’s installed packages, npm cache, dist output and temporary patch-check copy were removed. Source scratch, raw failures and all delivery artifacts remain. Test cleanup hooks completed; no device or long-running service was created. Historical held paths and groups were not inspected or operated on. Canonical integration and one independent slice review remain with root.
