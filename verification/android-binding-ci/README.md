# Fresh Android binding host checks

`scripts/ci/check-android-binding.py` copies the actual activation and SDK sources,
fixed host fixture, and C transport into a fresh SwiftPM package. It rebuilds those
sources and their locked Swift Crypto/ASN.1 dependencies. No retained Swift module
or object is a build input. The separately built experimental capability VM archive
and all three headers must match their supplied receipt; CI additionally requires
the archive's source revision to equal the checked-out commit.

Run each mode into a new directory:

```sh
python3 -B scripts/ci/check-android-binding.py --mode debug \
  --native-root /absolute/path/to/receipt-bound-host-vm \
  --expected-native-revision COMMIT \
  --output /absolute/path/to/new-output-directory
```

The other modes are `release` and `tsan`. Each runs the 39 ordinary scenarios in
separate processes and requires both a successful exit and the exact scenario
success marker. The runner checks actual dependency checkout revisions and clean
status before and after the scenarios. Native receipt/header/archive, dependency,
source, and success-marker checks remain active with optimized Python.

`qualified-1/receipt.json` binds the final runner, three local executions, source
archive, command logs, tool versions, native archive identity, and SDK dependencies.
`test-inputs.json` additionally identifies the CI regression helper sources.
The original local VM source is commit `1adb25c48a8723f56ed2649712fe5e357920c53e`;
it is explicitly recorded separately from the current Swift source. CI instead
uses its freshly built current-commit VM archive. Hosted execution of this new
step with the pinned Swift 6.2.4 compiler is still pending.

These results cover host ownership behavior. They do not replace the literal
debugger matrix, real JNI/Looper/widgets/draw checks, signed core integration,
physical devices, immutable published consumers, or GA acceptance. Thread
Sanitizer covers the fresh Swift/C build; the separately supplied Rust archive is
not instrumented by this runner. `collect.py` seals the specific local `*-3`
qualification and deliberately refuses to overwrite its existing output.
