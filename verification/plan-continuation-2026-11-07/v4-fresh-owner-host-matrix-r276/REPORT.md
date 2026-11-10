# R276 owner-host regression

PASS after one isolated test-only correction. Exact frozen product inputs; no product edits.

- **B:** 189 distinct compiled/runtime bindings, all 1,323 callback cases, all 15 helper final-boundary obligations, no missing cases. `PASS concrete actual16 host checks=14671; platform/JNI leaves, native runtime pending`. Runner elapsed 282.408s.
- **A:** `PASS actual owner/core/coordinator/observer closure A cases=231 assertions=1253; renderer leaf only, native runtime pending`. Runner elapsed 4.855s.
- Three compilation admissions total: baseline failed with javac exit 1; corrected B and A exited 0. JDK/javac 25.0.4.1, release 17, assertions enabled, 256 MiB JVM heap, ActiveProcessorCount=2. Each owned command has reaped-child/EOF/group-absence/terminal-custody facts in its commands.json.

The preserved baseline failed because the canonical map pins old product hashes and the controlled Canvas fixture lacks the `clipRect(int,int,int,int)` call at frozen NativeAppearanceViewsV2.java:790. `clipRect-compiled-proof.json` proves the real compiled invocation. `test-only.patch` adds that leaf declaration with entry/beforeReturn probe events and records its rectangle. It refreshes 48 source positions, the two FieldRemoval invocation anchors/opcodes, moved helper frame lines and map hash pins. All 189 IDs, seven-case vectors, 15 helpers, boundary targets and assertions remain unchanged (`correction-invariants.json`). No runner/controller/product changes. R264's read-only lead matches all 48 independently derived sites.

Final renderer SHA256: a065e2bef70d9ed886fd09fc29357318360a9ad14e4b98bb9d21f1784eb8c1d3. Views SHA256: d83c99a3cfd91cd7506476405caae81880439662aef60bacaebfd2e1032940a7. `product-inputs.json` gives all selected product hashes; each closure's source-map.json/inputs records exact compiled inputs. `snapshot-files.json` identifies the fresh copied static snapshot without Git operations. `membership.json` and B/barrier-preflight.json retain all actual compiled binding identities; B/barrier-cases.json contains the 1,323 raw runtime cases and B/helper-boundaries.jsonl the 15 helper traces.

Raw commands/output: baseline/commands.json, B/commands.json, A/commands.json and their numbered stdout/stderr files. Raw result: result.json and each closure receipt.json. Reusable correction: test-only.patch and test-afterimage/. All runner scratch and the exact fresh owned userdata snapshot were removed after terminal custody. Evidence inputs/classes remain. Campaign elapsed through packaging: 582.2s, below the 600s active bound; cleanup remains within reserve.

Scope: host JVM and controlled Android/JNI leaves. No native, device, signing, release, published-package, adoption or GA qualification. No canonical edits, commits, pushes, remote operations, child tasks, or held-resource access. R264 outputs and every historical hold remain untouched.
