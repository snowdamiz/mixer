# Native archive export correction

The fresh ab6461503 CI archive build failed because its frozen source export omitted vm/examples. Cargo requires the manifest-declared taskeditor_owned_command example even for a --lib build. The original compiler failure is preserved. Adding that first-party source directory fixes the closure; the regression fails before and passes after, including rejection of dirty working-tree bytes in favor of the frozen Git blob.

The corrected offline, locked release static archive compiles and passes all 28 public-symbol checks. No default features, profiles, budgets, ABI or signing policy changed. The two compiler-command bound was honored and all owned groups were observed absent. Cargo used default concurrency in this reproduction; jobs=2 was not explicitly enforced and no CPU-quota claim is made. Swift consumer tests and fresh hosted CI remain pending. Historical held jobs were not retried.
