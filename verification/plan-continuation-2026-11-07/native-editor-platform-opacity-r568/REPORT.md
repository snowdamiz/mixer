R568 separates platform Editor opacity from authored control appearance. This is an isolated candidate; canonical source, Git, signing, devices, remotes, dependencies and held resources were not changed.

`Cursor` and `Handle` now extend a distinct `EditorDrawable`. Editor opacity starts at 255, accepts only 0–255, has a main-thread `getAlpha`, and modulates the paint's authored ARGB alpha as `(authoredAlpha * opacity + 127) / 255`. RGB and geometry remain authored. Changed opacity invalidates once inside the captured `Mutation` checks; callback revocation is propagated. Color filters remain rejected. ControlDrawable and Empty retain their original immutable-alpha and color restrictions, with an explicit opaque getAlpha. Existing draw/record/input/owner gates and editor connection/selection/composition behavior are preserved.

The supplied R556 first fatal was verified at line 30680, 20:05:35.932, PID 2207: OwnedDrawable.setAlpha:1879 from Editor.InsertionHandleView.updateDrawable:6097 during onTouchUpEvent. Its exact excerpt is delivered. The prior R540 attribution remains historical and premature; no Back-harness change is included.

Observed results:

- The unmodified actual Handle rejects a legitimate fade callback (`setAlpha(0)`) with the same `authored alpha only` exception. Raw baseline stack is retained.
- Candidate: 65,662 host assertions, including all 65,536 authored/presentation alpha combinations, endpoint/midpoint draw colors, shape preservation, changed/same invalidation counts, invalid integers, color filters, thread access, terminal drawing, terminal mutation and revocation during invalidateSelf.
- Existing EditorTransactionHostTests: 3 cases / 30 checks passed. Host controls execute the real product bodies with controlled Android/JNI leaves; they do not execute Android's Editor or the OS IME.
- Strict SDK37 / JDK25.0.4.1 `--release 17 -Xlint:all -Werror -proc:none -sourcepath ''` product build passed, compiling the 20 safe R492 SDK Java afterimages plus both exact app Java files. Fresh D8 minAPI36 output, targetAPI37 manifest, and 16 KiB zipalign checks passed. No old classes or DEX were reused.
- Unsigned APK changes only classes.dex. All 18 native libraries and every non-DEX member are byte exact to the supplied R492 SHA. Exact app-source ZIP is retained: 66 app members plus Resources/, 67 total, with ordered membership preserved. No source-profile/binding changes are included.
- All newly launched command groups were observed absent. No device or signing operation occurred.

The two meaningful compiler batches used three javac invocations: baseline host; candidate host and strict product. One packaging correction campaign fixed a 66-versus-67 total-member assertion. The continuation then exposed two missing-variable assembly errors, one before strict compiler launch and one after all build checks; both are retained explicitly. Product compilation/testing was not retried. These assembly errors are not product passes and are not hidden. `run.py` is the corrected complete fresh-namespace recipe; the raw command list and separate failure records describe the actual run.

Independent review, root canonical adoption, signing and the actual same API36 OS IME run remain pending. Physical/final acceptance and immutable published-package qualification remain pending. No GA/release claim is made. Root should preserve every historical custody hold.

Artifacts and hashes are in SHA256SUMS and receipt.json. `SDK-r568-source-afterimage.zip` contains all 22 exact compiled Java inputs; only NativeAppearanceViewsV2.java differs from R492. The minimal patch targets the canonical path for root review/adoption.
