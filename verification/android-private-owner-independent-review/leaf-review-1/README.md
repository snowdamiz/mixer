# Independent mechanical leaf review

Recommend root select exact leaf 3 for bounded host-test reuse. This packet is
not product implementation acceptance. It contains the three separately admitted
immutable snapshots and preserves the leaf-2 runtime rejection.

The admitted snapshots contain 74 files each: the same 73 Android/JNI FQCNs and
one probe. Leaf 1 is 96,681 bytes, leaf 2 is 96,764 bytes, and leaf 3 is 96,805
bytes. `delta-custody-comparison.json` records all manifest/probe hashes and the
sole probe changes. `per-file-audit.json` records complete-body independent
inspection of every leaf-1 source; the 73 unchanged bodies retain that audit.
`probe-delta-audit.json` independently reviews the later probe-only changes.
`semantic-limits.json` lists the host models' exact practical limits.

`IndependentLeafSanity.java` contains independently authored leaf-only controls.
It compiles zero actual product subjects. Its explicitly synthetic trace marker
matches the probe's name filter only to test instrumentation, never to stand in
for a product body or count toward actual14 execution. Leaf 1 passes 12 controls /
80 assertions. Leaf 2 compiles but fails with UnsupportedOperationException for
missing RETAIN_CLASS_REFERENCE. Leaf 3 supplies that option and passes 12 controls /
82 assertions, including retained descriptor/BCI equality with the independent
synchronous hook. The same-line witness has offsets 3 and 9, confirmed by retained
class hashes and javap output. These outcomes use OpenJDK27 targeting Java17; an
actual Java17 runtime was not run.

`run_leaf_sanity.py` owns one child at a time and enforces wall, heap and output
bounds. It strips implicit JVM options, compiles an explicit source list with
empty class/source paths, retains commands/tool-binary/source/class hashes,
streams and results, then reaps children and deletes exclusive scratch. The
failed leaf-2 streams and bytecode are retained. No scratch remains.

`findings.json` distinguishes the leaf-1 retained-trace limitation from the
leaf-2 executable failure and their leaf-3 resolution. `receipt.json` states the
reuse recommendation and pending product gates. Actual-site completeness,
actual TextWatcher/owner/renderer successor behavior and full seven-case coverage
remain pending frozen product admission; no mutable product/test/parent evidence
was accessed. The sealed preaccess plan remains intact.

Run `python3 -B verification/android-private-owner-independent-review/leaf-review-1/verify_and_seal.py --check`
to verify exact source/evidence custody. Its seal covers every file in this
directory plus `docs/android-private-owner-leaf-review.md`, excluding only the
three fixed metadata files `manifest.json`, `manifest.sha256` and deterministic
`seal-result.json`; it verifies those sidecars separately. The executable review
helpers add no dependency. Native/UI/capture/process discovery, network/install,
git/CI, credentials/publication, public V2/OTA and GA actions remain unperformed.
