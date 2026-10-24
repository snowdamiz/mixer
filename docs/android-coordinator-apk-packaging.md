# Android coordinator private APK packaging correction

The root-dispatched click-fixture runtime booted but failed installation before
any app assertion. Android reported `-124`: applications targeting R or later
must package `resources.arsc` uncompressed with a four-byte-aligned data offset.
The failed receipt and install log under
`verification/android-coordinator-click-fixture/runtime-1` remain immutable and
are bound by the new runner. Root stopped the owned emulator/group, cleared its
ports, and removed its 177-file extraction. No native assertion passed in that
attempt.

The earlier repack preserved uncompressed entry bytes but changed the resource
table's compression method. Actual local ZIP metadata shows:

| APK | resources method | actual data offset | modulo 4 |
| --- | --- | --- | --- |
| original coordinator candidate-2 | stored (0) | 840 | 0 |
| rejected corrected-click candidate-1 | deflated (8) | 832 | 0 |
| packaging candidate-1 | stored (0) | 840 | 0 |

The table's uncompressed SHA-256 is identical in all three APKs:
`1fa3cb291285348ec1b33c85e7317d989467707f4791c4e5302f2d312d1e18c8`.
`compare_packaging.py` retains actual ZIP metadata and runs the new validator
against each exact hash-bound APK. It rejects the previously failed APK.

The new candidate copies all 105 frozen corrected input files unchanged, and
reuses all 176 non-APK artifacts without recompilation. Production classes,
corrected instrumentation, DEX, Swift/JNI libraries, the descriptor, and all eight
operations/assertions remain byte-identical. The builder repacks only the APK,
explicitly stores `resources.arsc`, and preserves the other compression methods.
It runs Android `zipalign -P 16 4` before fresh disposable test signing. Both
pre-sign and final signed APKs receive the executable metadata/ELF guard and an
official `zipalign -c -P 16 -v 4` check; signature verification also passes.
Android documents the required alignment/signing order and native library
alignment in its [zipalign reference](https://developer.android.com/tools/zipalign).

Only the APK artifact differs from the rejected click candidate. The only entry
whose uncompressed bytes change is `META-INF/DEBUG.RSA`, reflecting the fresh test
certificate. The other 25 entries, including `classes.dex` and the resource table,
are byte-identical. The retained archive and APK identities are:

| Item | SHA-256 |
| --- | --- |
| APK | `78af8c5df197fb6f163f3010825648a1b1a50427c9ab963b1c5aeca1e513b3ba` |
| compiled archive | `7305ff2bd05843ea26b7e82429767416ec219ec35e0587d4bcdc273204b9f4de` |
| unchanged source closure | `00c269c70199ffb376b39394db1c2367f8e9053d92ce6a863741d2a154359c04` |

The guard reads actual local file headers, checks agreement with the central
directory, rejects compressed/misaligned resource tables, checks every stored
entry's four-byte alignment, and requires all 18 arm64 native libraries stored
with 16 KiB data offsets and compatible ELF load segments. It rejects unsupported
entry forms rather than inferring acceptance from filenames or central-directory
offsets. Minimal negative ZIP fixtures exercise compression, alignment, local
header mismatch, missing/duplicate resources, and ELF identity/alignment. This
is a contract for this private APK; it is not a general-purpose APK parser.

The separate runner applies nine exact deltas to the accepted click-fixture
concrete source. It binds the new archive/metadata/path, runs the actual packaging
guard inside `bind_candidate` before any native command, records that result,
then rechecks the extracted APK and executes official `zipalign` immediately
before installation. All app assertions, Wi-Fi fallback, exact executable/PID/
PGID ownership checks, and finally-based emulator/extraction cleanup remain
inherited. Tool binaries, validator source, source manifests, failed install
evidence, and concrete runner/diff are hash-bound.

The private signing key was deleted in `finally`. After an empty holder check,
the builder removed its owned 180-file, 345,794,691-byte scratch directory.
Host tests run real packaging validation and host process/extraction guards;
SDK/native operations in runner lifecycle fixtures are synthetic. They cannot
qualify APK installation or Android app behavior.

After frozen packet review, root alone may dispatch:

```sh
python3 -B verification/android-coordinator-apk-packaging/run.py \
  --build candidate-1 --attempt runtime-1 --execute-native
```

Fresh installation and app assertions remain pending. Physical phones remain
disconnected and deferred. Full native fault/IME/lifecycle qualification,
public/signed release, immutable external FieldLog, store, customer, operational,
and GA acceptance remain pending.
