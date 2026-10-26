# Retained delivery command output

The exact `git ls-tree -r -z 0b8e3fd8bdd86902f7d9d28e0cba01bcdbb5ce1c`
output is preserved as the sole `base-tree.stdout` member in
`base-tree.stdout.zip`. Expand that archive in this directory to recover the
original path referenced by `stage-commands.json`. The expanded local copy is
excluded from the later delivery checkpoint to avoid duplicating 27 MB of
repository path inventory. No command output was changed.

```json
{
  "raw_bytes": 27473754,
  "raw_sha256": "9ec56dcc4413cedeb1d7ce6c1f72e1b3b641e5b4e6155553dd3eb365c662bd3b",
  "archive_bytes": 3358478,
  "archive_sha256": "a044d01dfecd0ccda1891ef1883d5d8302b8f708c9a3107622e6c6307096400a"
}
```
