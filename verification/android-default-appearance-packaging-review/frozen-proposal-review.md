# Frozen proposal review and recommended bounded contract

Recommendation: select **CLI-owned default descriptor packaging** first. Keep
copied-SDK default/ABI compatibility as an explicit pending prerequisite for
public V2 integration. The frozen proposal's internal asset path, adapter digest,
source admission and real APK verification are appropriate. Its create-time
copied-SDK compile/equality check and two-level process supervisor are additional
compatibility machinery; they are not necessary to establish the smaller
unsigned packaging guarantee while the public Activity remains V1.

This is a recommendation for root to select; it does not silently amend or
accept the frozen producer proposal. No implementation is authorized by this
review. The independently frozen preaccess baseline remains unchanged at
`docs/android-default-appearance-packaging-review.md` and its seal. This review
narrows its stronger direct-driver semantic-admission aspiration for the precise
CLI-owned contract described below.

Frozen reviewed proposal SHA-256:
`31f7983a5d5ecef5b90faeb540b28b4945e112d8821c6a550d57f89678c9f3b3`.
Frozen receipt SHA-256:
`68e5fff9d9647666b54ec385304ef2cab7ef79b3817bdf0d6989f8f0bbcba2a3`.
Frozen packet seal SHA-256:
`9170c192d00ebd1e30d2bdd8135c6f6d548990901cefd5960e0ffdc87646ef7f`.
The [executable review checker](review_frozen.py) verifies those handoff hashes,
all sealed packet files, the independent preaccess seal, retained command-output
bindings and the synthetic APK asset. Its [output](frozen-proposal-checks.json)
does not execute a codec, producer collector, compiler or product code.

## Findings affecting the handoff

1. **Separate packaging from a new SDK compatibility rejection policy**
   (proposal lines 118–140,168–179). The producer explicitly says the default is
   owned by the SDK linked into the CLI. That asset can be generated canonically
   and source-locked without running the separately selected `--sdk-path` SDK.
   The proposal's byte comparison proves only equality of that observed helper
   result with the CLI default. It does not establish arbitrary SDK behavior,
   native support or mixed-version ABI compatibility, as the proposal correctly
   acknowledges. Requiring it now rejects otherwise accepted source selections,
   adds a local compile to creation and requires child lifecycle machinery.
   That can be a deliberately selected later compatibility gate, but it is not
   logically required by the current data/packaging contract. Preserve SDK source
   selection and its existing lock without claiming semantic equivalence. A
   fresh acceptance consumer can use the qualified selected SDK and compare its
   observed API output as verification evidence without making that experiment
   an unconditional public create-time policy.

2. **Define one descriptor producer and an exact pass-through API**
   (proposal ownership table lines 99–102 versus step 3 at 136–138).
   `AndroidAppearance` returns approved bytes and `ProjectGenerator` passes
   them, but the table also says `AndroidProject` independently calls the codec
   to regenerate the default. These are two different handoff contracts. If the
   compatibility helper remains, the snapshot must write exactly the approved
   result; it must not discard it and regenerate a second value. For the smaller
   slice, one internal `AndroidAppearance` operation can call the CLI-linked
   `mixerDefaultV2()` / `canonicalData(_:)` once, validate shared mode, empty
   resources and system sans, and return those bytes. `AndroidProject.snapshot`
   should either call this operation itself or receive its exact result; choose
   one route. Write the bytes before computing `adapterDigest`. No executing
   helper, Python supervisor, Swift watchdog or copied-SDK compilation belongs
   to that selected subset.

3. **Make the entire final APK asset inventory explicit**
   (proposal lines 103,113–116,220–225). The proposal correctly requires a
   complete source asset inventory, including names omitted by general digest
   filters. Preserve it. Its final archive wording requires exactly one
   descriptor member; also require no additional asset entries. Check the
   complete aligned APK `assets/` inventory equals
   `[assets/MixerAppearanceV2/descriptor.json]`, with multiplicity one, and reject
   duplicate ZIP names before constructing a hash dictionary. Compare exact
   bytes and byte length to the admitted locked input. A hidden/extra source
   asset or unexpected final asset must fail, even when a recomputed local lock
   makes a broad source hash agree.

4. **Keep direct-driver admission claims at the actual validation layer**
   (proposal lines 103,201–207). A Python preflight can require the exact complete
   path inventory, ordinary directories and regular descriptor file, no symlink
   path/entry redirection, bounded nonempty size, and equality of SDK/adapter
   source digests with the local lock before touching `.mixer`. It cannot claim
   full canonical/default/resource/font semantics from those checks. Creation
   uses the real CLI-linked codec and fixed default; original-lock asset edits
   fail closed. A user who replaces the descriptor and recomputes the
   unauthenticated local lock can still supply layout-valid noncanonical or
   nondefault bytes. Do not call that semantically validated or signed. For this
   bounded V1 packaging slice, state the limitation rather than reimplementing
   the codec in Python or adding a compiler before every build. Tests with
   recomputed locks prove layout/size refusals only. Broader semantic admission
   needs an actual existing codec and a separate explicit contract.

5. **The optional emitter's process guarantees need an executable ownership
   design** (proposal lines 142–166). Keeping the general ProcessRunner unchanged
   is good scope. However, each compiler operation starts a separate owned
   process group, while the Swift watchdog owns the outer Python helper group.
   Killing the outer group alone does not define cancellation of the separate
   active compiler group. Before selecting this emitter, specify who retains
   compiler-group ownership when Python hangs, dies, ignores cancellation, or
   cannot return a structured result. Explicitly bound diagnostic spool growth
   while children run; limiting only returned diagnostics is insufficient. Define
   success cleanup, primary/fallback signal ordering, direct-child reaping,
   failure diagnostics and scratch removal without treating command return as
   proof that descendants exited. Synthetic tests must exercise hung supervisor,
   running child, output overflow, cancellation and cleanup failure. Limit claims
   to owned cooperating tool processes; the host package execution is not a
   hostile-code sandbox. These are pending helper obligations, not failures
   reproduced by this source-only review.

6. **Run closed asset type/size admission before hashing the asset tree.**
   `android-build.py`'s general `source_tree` passes listed input names to
   `digest`, which opens and reads them; it has no special-file admission before
   that open. An asset FIFO can therefore hang before a late asset preflight,
   and an oversized descriptor can be streamed before its intended size bound.
   Place the narrow closed-layout/directory/file/no-symlink/size preflight before
   `source_tree` can encounter the new asset, as well as before tools/output.
   Repeat relevant checks before packaging without claiming race-free isolation.
   Do not broaden this into an unrelated general source-tree rewrite. Original
   authored-Java mutations with a valid asset must still reach the existing lock
   rejection. The current `cli/build-tests/test_android_staging.py` constructs an
   empty adapter and empty digest, so give its fixture the minimum valid asset
   and matching digest; preserve every output-containment assertion. Add focused
   Python asset tests for the new preflight/ZIP contract. The supplemental source
   manifest binds this newly read test; no test was imported or executed here.

## Concrete smallest subset for root selection

| Owned surface | Selected contract |
| --- | --- |
| `cli/Package.swift` | Add the existing first-party MixerUI product explicitly to MixerBuild. |
| `AndroidAppearance.swift` or one clearly owned operation | Produce the CLI-linked existing canonical default once; validate the actual model with the existing codec; return exact bytes plus internally useful length/hash if needed. State CLI provenance. No copied table, SDK source scraping or fixture input. |
| `AndroidProject.snapshot` | Write those exact bytes to `app/assets/MixerAppearanceV2/descriptor.json` below the generated adapter before returning its digest. Keep all fourteen Java exports and the public V1 route. Reuse create's existing staging/final-move transaction. |
| Generated direct driver | Before any source hash can open the asset, enforce complete singleton internal asset inventory, ordinary directories, regular file/no symlink redirection and 1–65,536 bytes. Enforce both existing source locks and app resource refusal before output/tool work. Use AAPT2 `-A` for only that admitted tree. After alignment enforce complete singleton asset inventory, no duplicate names and exact locked-input bytes. Record descriptor/source/APK identity and existing local before/after observation scope. |
| Focused tests and fresh collector | Test CLI canonical generation and lock participation; original-lock edit/remove/rename/symlink drift; additional assets including hidden/excluded names and redirected ancestors; recomputed-lock layout/size failures; existing app-resource rejection; exact archive inventory/byte mismatch/duplicate failures. Build a fresh actual CLI-created unsigned consumer and inspect its full APK. Retain command/tool/source/artifact/cleanup bindings. |
| Explicitly pending | Copied-SDK default/API/ABI compatibility, installed V2 capture, public V2 switch and lifecycle, API28–35/private API36 gap, custom/platform-specific appearances, resources/fonts, native interaction/accessibility/design parity, physical-phone matrix, external immutable FieldLog consumption, signing/OTA/store/GA qualification. |

If `AndroidAppearance` is consumed inside `snapshot`, no new ProjectGenerator
descriptor parameter is necessary. If it is consumed in ProjectGenerator, use a
single explicit snapshot parameter and verify exact pass-through in tests.
Whichever route is chosen should avoid duplicated generation and preserve
iOS-only behavior. A narrow internal first-party helper is an ownership choice;
it need not become a new public configuration/API surface.

The result's precise claim is: **a project created by this CLI contains its
canonically validated CLI-default descriptor in the locked adapter, and an
original-lock build packages exactly those bytes as the only APK asset.** This
claim does not assert the separately copied SDK's default is equal, that a
rewritten local lock is authentic, or that the Activity consumes the descriptor.
Public V2 should remain blocked on an explicitly reviewed compatibility/native
join contract; physical and GA requirements remain binding.

Root has selected that narrow contract after this review. The product ownership
is limited to `cli/Package.swift`, `AndroidProject.swift`, `android-build.py` and
`AndroidProjectTests.swift`, plus a new implementation document/evidence packet.
The Python test ownership also includes the minimal valid-asset fixture update
in `cli/build-tests/test_android_staging.py` and one new focused asset test file;
its existing staging/containment assertions remain intact.
The single CLI-linked canonical producer will live in the owned AndroidProject
surface; no new AndroidAppearance operation file is selected. ProjectGenerator,
ProcessRunner, copied-SDK emitter, Python supervisor and Swift watchdog changes
are unselected. The frozen producer's broader helper discussion remains an
unselected alternative, together with finding 5's cross-group cancellation
obligations. No direct-driver codec claim under a recomputed lock is selected.

## Evidence and boundaries

The retained proposal experiment confirms an observed 9,587-byte descriptor with
SHA-256 `1aeab75c457c21e5c801ab8b446490971d510021c945d0841252360becd8ead3`
and a synthetic AAPT2 archive whose complete asset inventory is the singleton.
This reviewer independently reads and verifies those retained artifact bytes and
their command-output bindings. The producer's pure Swift/Java execution results
remain producer evidence; this reviewer does not rerun them or infer installed
capture, native rendering or full generated-APK completion from them.

No product/compiler/native runtime, process discovery, capture, UI automation or
device command ran. No product/root metadata or producer packet was edited; no
dependency was installed and no commit/push occurred. Only the review document
and this lane's verification directory are owned. No disposable native/capture
instance was started; nothing from another project was stopped or deleted.
