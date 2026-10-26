# Platform reference oracle provenance

This evidence packet retains official Android framework source from the AOSP
`android-16.0.0_r1` tag. Every retained `.java` file in `official/aosp36/` keeps
its original copyright and Apache License 2.0 header. The probe compiles the
unmodified `InputConnectionWrapper.java` from that directory; its copy in
`probe-source/android/view/inputmethod/` is byte-identical. These files are official
platform reference/oracle material permitted by AGENTS, not an authored Mixer
engine implementation. They must not be copied into a product repair.

`collection.json` records each exact official source URL, bytes and SHA-256.
Official SDK37 metadata/jar and the existing installed OpenJDK compiler/runtime
are tooling. No dependency package was installed. Authored finite annotation,
interface-descriptor, Preconditions, record/owner/focus and reflection-proxy
leaves provide controlled host behavior only; they are not Android behavior.
`extracted-source.json` separately identifies exact unchanged selected production
method/class blocks copied solely to expose current dispatch controls in that
finite environment. This is not a generated product implementation or a future
adapter candidate.

Root delivery action, if retaining the executable source oracle: add a specific
verification-only provenance/dependency entry for **Android AOSP framework source
reference oracle**, origin `https://android.googlesource.com/platform/frameworks/base/`,
version `android-16.0.0_r1`, license `Apache-2.0`, purpose `source-authority-and-
extracted-inputconnection-dispatch-review`, distribution `verification-only-
platform-reference-source-not-linked-into-product`, and point to this packet's
official URL/hash inventory. The existing OpenJDK and Android SDK/NDK entries
cover installed tooling, but do not explicitly describe retaining and compiling
framework source as an oracle. This lane does not modify `THIRD_PARTY.yml`.

License text: [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0).
The official source's existing notices are preserved; artifact retention is not
a product redistribution or release-license qualification.
