# Current-source signed Mac window build

`builds/current-caaa005-1/build-receipt.json` records a successful build-only
handoff using Xcode 27.1 / Apple Swift 6.4. The run name was selected before
another lane's commit advanced HEAD; the authoritative captured source revision
is `92e93b21add0d2f41cd43037b48c181f35d9f293`, which contains teardown repair
`5a5b395`. The 208-file immutable input manifest has tree digest
`7904f8169b44f126a0b096472480dbb880f221c7c029764181dbab94567cc46d`.
All captured inputs still matched their working-tree origins after building.

The app is:

`verification/guest-ui-teardown-window/.build/current-caaa005-1/MixerSignedGuestUITeardown.app`

Its bundle identifier is `dev.mixer.signed-guest-ui-teardown-verification`.
The harness and `Bundle.module` adapter are byte-for-byte copies from the
existing signed Mac window verification harness. The signer and bytecode
builder are copied from the current activation test sources; they remain
test-only. The current bytecode builder contains the existing compiler-friendly
array-construction refactor rather than the older candidate4 source spelling.

All owned Swift and C modules in the signed UI runtime's dependency closure
were compiled independently from the frozen source copy and linked into a new
runtime dylib. No old candidate4 object, Swift module, or dylib was reused.
The native VM archive remains the pinned retained archive with SHA256
`4d3b6dc36ea034d5604299752d560cbbc0615002b6b5ef4e5c25bbb3cb7c6120`.
Swift Crypto 5.0.3 was compiled from an already present, clean local checkout at
`c2cbadd7263439d8015189668f96ff5b5be565ce`; its Apple path exports system
CryptoKit. These dependencies are already inventoried in `THIRD_PARTY.yml`.
No network fetch or dependency installation was performed.

The build receipt retains all 33 commands, log hashes, tool versions, source
manifest, independently linked library and executable hashes, and full app
manifest. Both the runtime dylib and app passed strict ad-hoc signature
verification. The app links `@rpath/libMixerGuestUITeardownRuntime.dylib` from
its bundled Frameworks directory.

This build never launches the app. With a normal no-argument app launch, the
unchanged harness reads its evidence base from the new bundle's Info.plist and
uses these default paths:

- Progress: `verification/guest-ui-teardown-window/runs/candidate-2/progress.json`
- Data root: `verification/guest-ui-teardown-window/runs/candidate-2/data`

They did not exist at build handoff. The build receipt also offers optional
explicit launch arguments for a separately named run; they are proposed
arguments, not an executed launch command or runtime receipt. Root owns native
launch, Start signed guest, Save sample, Close and verify storage, and Quit.
The public runtime performs display-health observation itself. The harness
does not inject health, native display receipts, guest events, or internal
completion callbacks.

Rebuilding requires a fresh name, for example:

```sh
python3 verification/guest-ui-teardown-window/build.py --name another-capture
```

The driver refuses existing output directories. Source snapshots, binary
products, module maps, and caches are ignored under `.build/`. Source snapshots
are read-only; receipt and manifest files remain reviewable outside `.build/`.
Keep the original receipt and artifacts when collecting later native evidence.

Compilation and signing are not a visible-window result, physical iOS/Android
receipt, published-package consumer, distribution-signing approval, or GA gate.
