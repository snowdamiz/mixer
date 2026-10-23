# Pure appearance foundation qualification

This lane owns only the five assigned SDK files and this verification folder. It
implements the accepted raw values and exact closed data codec from root's
`verification/ui-shared-appearance-root-review/acceptance.json`, the single embedded
1,906-byte default, and checked metric math. No external dependency was added.

`build-corpus.py` records all 50 sealed design-oracle input byte sets (3 accepted),
then real public-import Swift tests execute each one. Additional Swift tests cover
programmatic invalid graphs, both modes, bounded allocation preflights, exact
65,536-byte admission including LF, decoded duplicate keys, string escaping,
resource/font/geometry semantics, and fixed-point ties/extremes/nonfinite inputs.
`verify.py` freezes exact SDK, tests, contract and runner sources with per-file
SHA-256 plus tree digest, executes complete SDK Debug/Release tests and compiles
MixerCore/MixerUI modules for iOS arm64 and the official Swift6.3.3 Android arm64 SDK.
Platform module compilation is a compiler receipt; neither platform is executed.

The Python oracle checks font variants only for referenced faces. The accepted
prose requires scale1/locale `und`/neutral for all fontSFNT resources. Swift enforces
that stronger documented invariant for unreferenced fonts too, per root's explicit
clarification, with a regression test. The sealed oracle is unchanged. Metadata
acceptance proves no real font/PNG validity, identity, glyph coverage or licensing.

Canonical parsing checks input bytes before copying; enforces depth, value,
decoded ASCII string and array bounds before descending, retention or growth;
rejects duplicate decoded keys, noninteger lexical forms and UInt64 overflow; and
checks complete closed shape and semantic constraints before byte equality. Raw
programmatic resource/face array counts and string bounds are checked before new
graph retention. The nonrecursive fixed type graph stays under4096 values/depth16.
The writer measures every escaped byte before allocating output and checks byte
budget before each growth. No JSONSerialization/JSONDecoder is used by the codec.

Pending: native style resolver and all ten-kind adapter support; unchanged Apple
reference capture; Android actual widget styling; installed resource/index
packaging/extraction; private installed/signed capture; physical parity,
accessibility/performance; immutable published FieldLog, signing/store/customer
and all GA gates. Phones remain disconnected. No device discovery, native run,
reconnect request, production publication or other lane's mutation occurs here.
