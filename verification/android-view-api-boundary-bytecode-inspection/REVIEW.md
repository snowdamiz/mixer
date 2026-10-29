# Finite emitted-artifact inspector preparation

Prepared `inspect_artifacts.py` for in-process use by the separately selected
hosted collector. Import is inert. `inspect_classes(classes_root,
platform_jar=...)` and `inspect_dex(dex_file)` only read bounded files and return
JSON-serializable evidence or raise `Refusal`; neither starts a process, writes a
file, imports product code, uses a timer or accesses the network.

The selected producer is candidate115 freeze
`c458497920a6cf454433f2f96bbcdf42fbf8b6945e55e5a76c813dddb00af8ff`, manifest
`e52dd5bd9c415a68c843724a24fec03c72c64dbce7fae2d18377c646a4b35834`, product16
tree `d767f19554c88bd24f58663de268d7a80119522380cfeb4043c37d35b432a21e`.
The caller must independently verify those source bytes and bind the actual
compiler, official SDK37, D8 min28 commands and outputs. The inspector deliberately
reports that its source-binding constants do not themselves establish custody.

Classfile inspection decodes each emitted product source group and nested class,
all product constant-pool method references, complete Code instruction boundaries,
branches and handlers. It requires the three exact API helpers, actual
InnerClasses/NestHost metadata, inert private constructors and no helper fields.
Their finite straight-line instructions preserve the exact cursor/center/left/
right native calls, distinct authored Cursor/Handle constructors with the same
Record, original receiver/value and original `Mutation.require()` immediately
after each V2 setter. Constructor/bind `requireMutation()` remains a distinct
source/runtime entry obligation; it is not substituted for the original setter
postcheck. V1 has no Mutation contract.

The actual callers are `NativeAppearanceViewsV2$Record.bind` and
`NativeRenderer.bind`. SDK29/30 evidence requires actual
`android/os/Build$VERSION.SDK_INT:I` field reads and instruction-level comparison
branches. CFG checks include exception handlers, reject entrances into the middle
of the SDK-read/constant/branch chain and require the comparison to dominate its
helper call while the unsupported successor cannot reach it. V2 callers must pass
the original Mutation parameter, and API29 passes original Record `this`.
The two separate API36 comparisons are decoded and reported. General all-path
semantic denial and actual lower-API execution remain focused-test obligations.

The four API29 constant-pool owners are the actual `NativeField` symbolic class.
The inspector resolves `NativeField → EditText → TextView` using the product
superclass plus the exact supplied official platform jar's class bytes; it records
the declaring class and platform jar identity. It does not relabel every owner
TextView. Mechanical host classes and the known host probe/test/JNI families are
enumerated separately; a product owner cannot spoof a different source family.

DEX evidence is independently decoded from one DEX039, with SHA1/Adler32, header,
map, section-local bounds, ID tables, class data, code, payloads, invocation and
handler checks. The finite helper register analysis preserves original parameters,
distinct drawable identities and immediate Mutation postchecks. CFG must-alias
analysis checks original Mutation/Record arguments at V2 caller sites, including
exception paths. Later native calls outside the exact three helpers refuse,
including unreviewed D8 API outlining. Unrelated synthetic classes are enumerated.
DEX annotation/debug/encoded-value semantics, complete verifier correctness and
independent DEX API36 denial are not claimed. Platform resolution in DEX is paired
with the separately pinned classfile/jar evidence, not ART execution.

`check_inspector.py` installs process/session/group/signal/timer/wait/socket mocks
and an audit hook before importing the subject. Its 33 controls include authored
in-memory binary helpers/guards, wrong setter order, Record/Mutation identity,
fake SDK owner, guard jump-in, malformed/truncated/trailing classfiles, historical
DEX structural parsing, checksum and repaired-checksum structural/opcode/map
corruption, and register-alias overwrite controls. The historical DEX is only a
parser fixture; it is not evidence for the changed candidate. The independent
reviewer adds separate hand-encoded controls and records their own exact result.
The DEX helper data controls also refuse hoisting a later drawable constructor
ahead of the preceding setter/postcheck; object-register moves may intervene
without changing the required observable constructor/call/check sequence.

The DEX decoding skeleton/opcode-width table was narrowly adapted from the
independently reviewed `class Dex` block in
`verification/android-api28-collections-independent/review.py`; that historical
script was read as data, never imported or run. The new class parser, helper
proofs, guard checks, register dataflow and controls are authored in this packet.
`provenance.json` binds those reads, fixture and frozen inputs. Setup failures and
the one owned Python import-cache cleanup are preserved separately.

Static review of the collector/custody drafts found the explicit host103/sdk17
compile closure, one focused main, D8-only cross path, repeated immutable input/
tool/output checks and failure retention consistent with this interface. The
reviewed custody design pins the direct leader with WNOWAIT, retires signal
authority before direct reap, then makes at most one terminal numeric absence
observation; present/inaccessible groups fail held without further access. No
collector/custody runtime function was invoked here. Provider/tool identity and
actual hosted dispatch remain root selection obligations.

No compiler/JVM/product/Node oracle, native instance, process probe/signal, UI,
capture, phone, Git/gh/network, publication, source-pair promotion or canonical
edit occurred in this lane. No ART/native parity, lower-API V2 admission,
complete-matrix/BCI equivalence, OTA/release or GA authority is granted.
