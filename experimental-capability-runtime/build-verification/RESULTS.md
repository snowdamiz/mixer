# 2026-10-23 frozen builder qualification

The completed receipt is [2026-10-23-final-v3/receipt.json](2026-10-23-final-v3/receipt.json),
SHA-256 `2744db5cb31d67286b4cf81bbfe9b8be6df8db95f7feb9d6e246801eb20f8b91`.
The independently authored builder candidate is
`e7e34079d7af7d26162ccfc0c43cc6d269fb500ed42bd5e1aef91765e2fee076`.
The five qualification source inputs remained unchanged during the run; their
manifest digest is `ef66b2a73613fa3606b017d4c4c091e24fe0ec02d3c8ff5a880dea87ca39ade5`.
Root's independent public CLI review is maintained separately under
`verification/capability-builder-review/`.

All archives were actually built with the explicit nondefault native feature from
commit `b25e3b7de2391a80d12e7fd75e60903495bec120`. The 81 regular committed inputs
produce source manifest `47ecc06679f61be0da8a53839830be72876889bb90c9a8e5834c8661f9312aa6`
and regular-only canonical source tar
`218dd785df1e19ec32e2c3d6621df3317be27525ba071f660edd8e248cf04add`, equal across
all four targets. No mutable SDK checkout or VM working-tree source is consumed.
Exact compiler/LLVM/linker paths, resolved tool hashes, version strings, sanitized
environment, command arrays, command outputs and archive/header hashes are in each
copied target builder receipt and log. This records provenance and does not claim
bit-for-bit binary reproducibility.

| Target | Staged static archive SHA-256 | Bytes | Scope |
| --- | --- | ---: | --- |
| macOS arm64 | `a015ff65980422dd0b9c5cad2e28741d1e5ba478e0f657dcaedf75477d553b72` | 19,301,552 | C execution |
| iOS arm64 | `0e74a76241a5fc3417d7ebc6ec6d013e25c1f6c37f5b543c3745135b911077f2` | 18,997,296 | layout compile and C link |
| iOS simulator arm64 | `de2563672a9d4fdefa043fc4ec5a1ad7cb51bc418694d6173742e07100e54122` | 18,994,768 | layout compile and C link |
| Android arm64 | `74d06f044320f6a095fb35990a74c325024046208ee014edc79d2dccdf120eea` | 25,310,640 | layout compile and C link |

The large artifacts remain locally under
`local/qualified-final-v3/{host,ios,ios-simulator,android}/`. Each `lib/` contains
only `libmixer_vm_capability_experimental.a`. Each `include/` contains precisely the
matching capability header (`9213c34ebf0f14d14f3319172e83647f704f3a02a60d413b4de990884357b4a6`)
and unchanged legacy header (`18c2498d0d1deae2c998ef9f4b3f811b2184c45e8169610012b05e99342385fd`).
All archives expose the expected 27 C symbols. Source exports, native binaries and
Cargo caches are ignored by Git; small receipt and command-log evidence is retained.

The 22 successful outer commands include 22 original boundary test functions in
normal Python and again under `-O`; the actual unittest counts are parsed. Original
Git fixtures cover moving-ref/short/noncommit rejection, dirty-source exclusion,
missing feature/header/input, build script, external source/dependency, Git symlink,
output aliases/exclusive writes, cache symlink/special/external-hardlink rejection,
internal hardlinks/locking/quarantine, source tar bytes, archive copying and compiler
selection. Process tests exercise timeout/output overflow/nonzero/success-orphan
writers and interrupt while the cache is held. Descendant writers stop; inability
to observe a group disappear is failure/quarantine, not inferred completion.

The host C smoke executes 27 status/alias checks with the actual public layout
assertions. A separate original public C client performs 52 checks from one staged
archive: eight legacy plus eight capability sessions fill the shared sixteen-slot
pool, both seventeenth creates reject with status3, cross-family closes reject,
correct closes succeed, and a replacement succeeds. The three other targets compile
the full C layout assertions and link the native C client without executing it.
No Cargo dynamic-library directory or default archive is linked by these clients.

The initial real host compile succeeded but Apple LLVM21 `nm` rejected Rust LLVM23
bitcode during archive inventory; staging stopped. Its failure and command logs
are retained in final-v3. The builder now requires the matching installed official
Rust LLVM tools. An initial suite also exposed macOS `killpg(...,0)` permission
denial while observing an adopted descendant group; this is conservatively treated
as exit not established, with a cache quarantine, rather than success.

Two earlier full verifier attempts failed in the *new C test oracle*, without
native or builder changes. The first omitted required defined memory zero; the
second incorrectly expected status2 instead of the documented status3 on shared
pool exhaustion. Their [failure receipts](2026-10-23-final/failure.json),
[second failure receipt](2026-10-23-final-v2/failure.json), logs and original fixture
bytes are retained. The fixture hashes match each failed receipt's source manifest.
The corrected fixture then passed52; final-v3 is the completed run.

These checks do not qualify Swift bridge behavior, SDK identity, signed activation,
release selection, published packaging, native I/O, a full Swift/FieldLog runtime,
mobile lifecycle, a simulator launch, or any physical device. Existing profile,
ABI, quota and OOM limitations are unchanged. The cache/tool trust and process
containment limits are stated in [README.md](README.md).
