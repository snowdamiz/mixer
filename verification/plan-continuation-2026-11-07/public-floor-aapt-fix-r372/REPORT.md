# R372: concrete R360 P1 AAPT2 minimum-field correction

FIXED in an isolated combined R346 candidate. The production APK inspection now requires exactly one complete `minSdkVersion:'<admitted floor>'` line from the pinned official AAPT2. It rejects duplicate declarations, malformed minimum lines and ambiguous `sdkVersion` aliases. The five original real-packaging failures now pass. Canonical source was not edited. Root independent slice review and integration remain pending.

## Delivered artifacts

- `candidate/`: complete three-file R346 floor proposal with the minimal driver correction applied.
- `source-and-test.patch`: combined original-floor-to-final patch, including R346's Swift regression test.
- `minimal-fix.patch`: only the concrete correction relative to the reviewed R346 candidate; two inserted lines and one replaced condition.
- `test_packaging.py`: rerunnable real-tool packaging and exact production-boundary regression; no replacement parser or mocked tool badging for the packaging cases.
- `review_floor.py`, `matrix.json`, `logs/admission-after.stdout`: unchanged R360 admission harness, freshly executed against this final candidate.
- `source-identities.json`: exact original, reviewed R346 and final SHA256 values for every delivered source/test file.
- `original-r360/`: original report, full five-case command/output reproduction, initial failing output and reproduction script, preserved as historical evidence.
- `results-before.json`, `results-after.json`, `commands-before.json`, `commands-after.json`, `logs/packaging-*.stdout`: fresh before/after observations, full raw AAPT2 stdout/stderr and commands.

R346's named `afterimages` directory does not exist. Its actual `proposal/` files were hash-checked against R360's reconstructed candidate identities before copying. All three pins matched.

## Minimal change and preserved contracts

The old guard searched for a complete `sdkVersion` line. Pinned build-tools 37.0.0 actually emits `minSdkVersion`. The final guard collects only minimum-field declarations at the beginning of lines and compares the complete list with the one expected exact pinned-tool declaration. `targetSdkVersion` and strings inside package metadata do not own the minimum field. Including the obsolete alias in the declaration filter ensures that mixed old/new fields fail closed rather than selecting one arbitrarily.

The final driver SHA256 is `5111372e8e0da0ba07f61dda99348805cf439860ca0cfdee8003a971f30c6073`.

Its reviewed R346 before-fix SHA256 is `5d64896eecf4614314fcbef56411a1ee7e9f03d91240f7e39ce334ae274f1faf`. The original pre-floor driver SHA256 is `04675e4b320a68ed89d4f06f7a232fdde87ff0316e9f569a0725c9a02c1fea28`.

Public V3/V4 generated minimum remains 36, Legacy remains 28, target remains 37, and D8/AAPT2 still use the admitted minimum. Application floor remains separate from the unchanged Android28 ABI/toolchain identity. No API28 high-contrast observation is synthesized. Every Python top-level definition except the containing `build` function is AST-identical to R346, including manifest admission, source/profile selection and source-pair checks; see `unchanged-python-contracts.json`. The public generator and Swift regression are byte-identical to R346. All six narrowly named canonical source hashes remain unchanged; see `canonical-preservation.json`.

## Executed results

**Before: expected failure, exit 1.** The new executable check ran against the exact reviewed R346 driver. It retained 34 outcomes: 23 met expectations, 11 exposed the defect. All five otherwise valid fresh manifest packages were refused: public-v3 minimum 36/37, public-v4 minimum 36/37 and Legacy28. The hash-checked saved R320 Legacy APK was also incorrectly refused. The old guard additionally accepted the obsolete alias and an ambiguous alias-plus-correct-field input. Original R360's independent five failures are separately retained without modification.

**After: 34/34 pass, exit 0.** Real official AAPT2 link/dump ran for seven fresh packages: the five valid cases above plus actual below-admission public35 and Legacy27 packages. The valid five pass the exact production minimum inspection; both below-floor packages refuse. Every real fresh package reports target37. These are unsigned manifest-only APKs, using exact generated manifest inputs with only the tested minimum varied; they do not contain compiled app/native code.

Two existing complete app APKs were hash-checked before dumping and again afterward:

- R320 Legacy APK: `f80e320cd0b8cfb48040d9334cf35d06db176fad116c94e44d2477834e559ea2`; actual minimum28/target37; final inspection accepts the admitted Legacy28 minimum.
- R304 public-v4 APK: `04db9758aac50fb28aa9c36aff46010fa042a96a717bcccbf055d45a3864ccea`; actual minimum28/target37; final inspection correctly refuses admitted public36. This old APK was not relabeled or rebuilt.

The other 25 controls cover exact field ownership, target-only and package-contained text, missing values, old aliases, duplicate matching/conflicting declarations, malformed extra declarations, whitespace, quotes, unresolved/noncanonical numbers, same-line ambiguity, and mismatching minimums. Synthetic strings are confined to these parser-boundary cases; all real-package cases use complete unmodified tool output.

**Admission: 120/120 pass, exit 0.** Both public profiles retain36/37 admission and below36 refusal; implicit/explicit Legacy retain28+. Malformed/duplicate/unresolved/symlink manifests, invalid host values and unsupported floors refuse before sources/tools/output. Existing artifact and receipt sentinels remain unchanged. This is the unchanged R360 harness run freshly against the final driver.

**Patch reconstruction: pass.** `/usr/bin/patch -p1 --batch --fuzz=0` applied the combined patch onto the two exact original source files in an owned reconstruction directory. All three outputs, including the new Swift test, match the delivered final hashes byte-for-byte; `patch-verification.json` retains command, version, output and comparisons.

The pinned tool is `/opt/homebrew/share/android-commandlinetools/build-tools/37.0.0/aapt2`, version `2.20-15087165`, SHA256 `13a206c0b022ba3b92f21b6f142f3a4b2d0f3bb1ac0bddfa820ee2c6b00c4c99`. Official SDK37 android.jar SHA256 is `bf1b4387cc7ca94fc6ef684f040d9d16fbf16248e181819f020736ea2053f177`. Before/after tool identities match exactly. Python/platform versions and commands are retained in `tools-*.json` and `environment.json`.

## Reproduction

From the repository root:

```sh
python3 verification/plan-continuation-2026-11-07/public-floor-aapt-fix-r372/test_packaging.py before
# Expected exit 1: retained reviewed R346 defect, including all five valid packages.
python3 verification/plan-continuation-2026-11-07/public-floor-aapt-fix-r372/test_packaging.py after
# Expected exit 0: 34/34 controls.
python3 verification/plan-continuation-2026-11-07/public-floor-aapt-fix-r372/review_floor.py
# Expected exit 0: 120 admission controls.
```

Each official tool call has a ten-second bound. No Swift build was needed for this parser correction. R360's two Swift generator tests remain prior review evidence, not a fresh R372 test claim.

## Root's separate next executable tests

1. **Source116 rebinding:** root admits the concrete combined candidate into its chosen source snapshot and records its current source116/CLI resource binding. This task does not assert that the old source116 binding covers these changed bytes.
2. **Root CLI build:** root builds/assembles its selected CLI and creates/builds a fresh public-v4 project with minimum36 through the actual complete driver. Check final APK `minSdkVersion:'36'`, target37 and receipt `application_min_api:36`; retain all source/profile/refusal checks.
3. **API36 runtime:** root installs that exact reviewed APK on its owned API36 instance and exercises draft input/Add/toggle. Ordinary installation below the floor must refuse, with no SDK-check bypass. This is separate from parser and manifest-packaging acceptance.

This task runs only the exact production minimum-inspection block, extracted between the unchanged APK identity check and DEX inspection. It does not claim a complete successful driver build or rerun the identity/ABI/native checks. No SDK install, emulator/device, signing, Git, remote operation, subchild or held namespace was used. Returned command sessions establish only the recorded direct command results; no broad descendant-absence claim is made. All artifacts remain inside this task's output except read-only hash/dump reuse of the two explicitly authorized APKs and official SDK inputs. All historical holds and physical-phone restrictions remain in force. Full API28 product acceptance, native acceptance, immutable-package qualification and GA remain pending.
