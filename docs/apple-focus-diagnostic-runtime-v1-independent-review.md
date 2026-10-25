# Apple focus diagnostic runtime V1 independent review

The corrected prepared packet **passes the independent host review**: seven
controls, zero failures, errors or skips. The three initial findings are closed.
This is a host review of a possible later two-method diagnostic run. It grants
no native result, full six-case/comparator credit, keyboard qualification, or GA
acceptance. Physical phones remain disconnected and deferred. Root alone selects
and dispatches any later simulator attempt.

The accepted review input is packet
`d7c4c0f146434eeb7323036809acb5b4a80d41ff10f596eed8c25bdaa314e783`
and independently recomputed owned source tree
`12908f345de89df7c8a586a3acef337be413cc5239af0b321829663718283aa8`.
The passing independent source, command, Python version, output and receipt are
preserved under `attempts/review_2/`. `acceptance.json` binds the exact reviewed
inputs, receipt and final report; `freeze-manifest.json` records this lane's
source/evidence files. No further source or test-result changes are implied.

The reviewed initial packet SHA-256 is
`19d573479e5f016c7fbd0b8599400f46bf962c4a9a87dfdd594b80dce0147f33`;
its independently recomputed owned source tree is
`99570be6c8e3fa6b328fb15f68555f4a94250fe06d31dc56b4d2042d4d6a1988`.
The review owns only this document and
`verification/apple-focus-diagnostic-runtime-v1-independent-review/`.

## Findings from the first review

All three findings below describe the preserved initial packet. The corrected
packet checks the exact canonical input lock and its packet digest, checks exact
four-file membership plus the recomputed observed source digest, and rejects
extra/missing materialized directories and non-0755 roots/directories. The same
negative fixtures now reject; the unchanged fixture must first verify before
either lock/digest negative is applied. The empty-directory control observes
both tree implementations independently with subtests.

1. **The reviewed packet does not enforce its external input-lock binding.**
   `prepare.py:263` calls `verify_inputs()` without comparing its returned lock
   digest to `packet.inputLockSHA256`. An isolated fixture preserved the exact
   reviewed packet, sources and output manifest, replaced only the input lock
   with `{"files": {}}`, and `verify()` still returned the reviewed packet SHA.
   This permits external tool/source/archive bindings to be removed or rewritten
   after review without changing the packet selected for dispatch. Require the
   lock digest to match the packet before accepting the lock's rows.
2. **The claimed owned source tree is not checked for internal consistency.**
   Every owned source row is checked, but `ownedSourceTreeSHA256` is never
   recomputed. The isolated inconsistent-digest fixture is accepted. This is a
   receipt consistency gap, narrower than the external-lock bypass: changing the
   packet itself still changes the root-reviewed packet hash. Recompute the
   digest from the observed owned source rows.
3. **Materialized directory membership is not closed.** `prepare.tree()` and
   `join_support.product_tree()` check directory modes but omit their names from
   returned rows. An added mode-0755 empty directory leaves the returned tree
   unchanged. Archive enumeration correctly checks exact implied directories,
   and installed-app validation later rejects extra app directories, so this
   does not demonstrate an installed payload bypass. It does leave the prepared
   output/product closure claim too broad. Require observed materialized
   directories to equal the directories implied by the payload manifest.

The first independent attempt ran seven controls with four passes and three
failing controls. It is preserved under `attempts/review_1/`, with the exact
executed review source, command, Python version, retained log and receipt. The
empty-directory control stopped at its first failed assertion; the revised
review source uses subtests so both materialized-tree implementations are
independently observed on the next coordinated attempt. No producer file was
mutated by these controls.

## Verified review scope

The independently implemented archive and filesystem walkers checked all 49
external input rows and all prepared file bytes, sizes, modes and directory
membership. Both compact archives matched their exact payload/directory sets:
55 compiled product files and 39 accepted source files. All 28 selected runtime
source/data files plus `runtime-selection.json` match the output manifest; the
nine claimed changed files match the actual V3-to-selected delta. The new
source-only archive contains exactly those 29 files and 11 implied directories,
with no compiled products. Its bytes, modes, entry types, sizes, file hashes and
packet/manifest relationships were inspected independently. It is 83,971 bytes,
SHA-256 `a2dc43359e23b0c4fec0f7bc7f8224ed9a5ba678f32d2e7fc571b98093e24715`;
the canonical archive manifest SHA-256 is
`ee87c94bfd001b2ac07b54fa6536ec8d0046594afeba94a0353897f5e90c430d`.
Every oracle source remains byte-identical. The accepted
observer source is
`c712724207fb5d327da0f6367e7a7f598494b3bb43f8b25fdfefcf94d3aefa88`.
The initial producer's 26 passing host controls and the corrected producer's 34
passing host controls are retained evidence, separately scoped from the seven
independent controls.

An executable import control rejects a preloaded shadow `join_support` module,
then imports the actual selected composition with process and socket creation
blocked. The runtime guard also rejects a function whose module attribute
claims `join_support` while its compiled code origin is foreign. The selected
scope is exactly settings plus `test010EnabledFromOff`, and only the diagnostic
app/container. The extra-method and missing-method commands reject. Official
two-method result matching rejects a substituted method. Synthetic official
results alone cannot set `runPassed` or any broader qualification credit.

The capability control creates a private owned session, derives the mode-0600
configuration, refuses retirement while the secret has a hard link, then retires
it after that owned negative fixture is corrected. Result evidence remains, the
derivation receipt contains no capability, and absence is recorded. Source
inspection confirms the once-only exact selected command, 600-second command
ceiling, 30/45-second method allowances, original environment/cwd and check=False
exit handling. The unchanged oracle retains the three fixed focus IDs, initial
Tab, 12-step acquisition and 12-second witness limits. The diagnostic overlay
strips only its optional telemetry before the original witness branch and cannot
advance a failed cursor.

Root has separately reviewed the adapter and failure-independent cleanup path.
This review did not repeat every producer or observer test. It used no Git,
native/compiler/device/simulator/UI/capture operation, service, hosted
catalog-inspector source, or authority-driver source. Native behavior, first-Tab
failure resolution, Xcode finalization, full six-case qualification, physical
phones, carrier, signing, store, immutable-package FieldLog, customer,
operational and GA gates remain unverified.
