# Independent descriptor preparation review

Accepted for the exact private source145/host11 descriptor preparation scope.
No blocking product-code defect was found. This review does not authorize real
loader ingress, execution, writer admission, release or a GA gate.

The root release SHA256 is
`1b438498f50bad81ee701d7e7d7c3c65c80686468c1789c4109da446db33a1e9`.
All 208 producer members / 1,258,701 bytes were freshly hashed against seal
`5e11885ef1a1189dc10ef8de5b82f4cd969573a8a1130e0a25f146725c23d7ea`.
All funding225 and emission58 sealed members were verified, plus only the
fourteen selected historical loader members (eleven support members, support
manifest, contract, historical runner). This is not full loader1050 replay.
The upstream emission packet also has `freeze-receipt.json` outside its seal;
it is explicitly recorded as an unsealed nonmember, and is not relied on.

The independent recipe starts with accepted funding144
`7e3e861ca65d8c6359623443d6a7810b878c1029494a0ae557307d35ed43484b`.
Only the literal loader count changes from 144 to 145, the private unused module
declaration is added, and the exact unused helper
`ef14f2fe335eb822141ae802f822ddf41a3ba81729d2e5b436d3940cf1946c8a`
is added. Recomputed source145 is
`450b6d9b3a05d160e19fa888b68173286b8f6af20ecc7216fdf86283f09b308a`;
unchanged host11 is
`027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2`.
The compact overlay has exactly those three paths. The complete patch and
manifest are reconstructed independently without calling producer Python code.
Reversing the sole loader literal restores the complete accepted loader bytes:
parser grammar, option_env keys, types/layout declarations, capability privacy,
ownership, budgets, File/session/executable/source checks are unchanged.
Reversing the private module declaration restores the complete funding/phase
file. `WorkAuditPending` remains and no call to the emission helper exists.
No phase-retention or work-admission lane was composed or reviewed here.

All twelve producer compiler preimages were independently decoded and matched
to actual command receipts. All five keys were reconstructed from complete
canonical manifest, counted argv, counted sorted clean environment, live
compiler bytes and exact compiler-version output. SDK declarations, Python,
new runner/controls/proposal are identified separately from host11. Retained
MIXLBD01 header, section lengths/digests, target/reserved bytes, 145/11 counts,
artifact extent/digest, injected key variants and removal evidence match.
Producer debug/optimized production/unit metadata builds and 82 pure controls,
plus 6 missing/malformed/stale build/run pairs, are supported by retained raw
command output. Unit metadata emits two existing dropping-Copy warnings;
zero-byte unit metadata artifacts do not prove a test executable ran.

Fresh independent Rust 1.99.0 / aarch64-apple-darwin evidence consists of 19
commands: version, Git context, eight optimized pure compiles/executions and
one real source145 production metadata compile. The 53 pure controls cover
header, target/reserved bytes, old/foreign cardinalities, caps, malformed counted
argv/environment, digest corruption, same 145/11 valid-JSON hash drift with a
recomputed header, all five digest commitments, and hex grammar. Seven fresh
negative compiles/executions cover stale identities at all five key positions,
one missing key and one malformed key. The independent pure parser/hash/identity
body comes verbatim from the candidate. Only the unrelated validation error
name is stubbed; no actual loader, validator, proof, guest, VM, engine or writer
is linked or executed by that scaffold. Production metadata uses actual source
types but is not runtime or physical layout qualification.

Two positive limitation controls intentionally accept altered output digest and
extent at this extracted boundary. The unchanged real loader authenticates
those later; its entry is unrun here. H/bootstrap, all pre-ingress host/storage/
source/work admissions, real caller and final composition remain pending. A
later composition requires fresh complete manifests and compile keys.

Producer failure history remains in the frozen producer packet: first Path
ordering preparation refusal is a transcribed/reconstructed exception record;
first pure scaffold pub(super) compile refusal has actual compiler output.
Four independent reviewer attempts are preserved here: upstream directory
closure assumption, legacy-seal field assumption, target-padding arithmetic
mistake, and an expected-refusal mistake for a valid empty argv entry. The first
three have recorded exception summaries and exact scripts; the fourth includes
actual command output/preimages and owned scratch inventory/cleanup. Empty
argv entries are valid under the unchanged parser and are identity-bound.
These were reviewer-only corrections; producer bytes were unchanged.

Final independent metadata/binaries were measured then removed. All nineteen
owned child groups were reaped and recorded absent; owned scratch was removed.
Only owned groups were queried; no global process inventory occurred. Native,
UI, capture, simulator/emulator and physical-device runtime checks remain paused
and unrun. Canonical integration, publication, separate-repository immutable
FieldLog packages, OTA/store/customer/operations and GA remain pending.

`review.py` refuses a frozen packet and should not be rerun in place.
`python3 verification/swift-guarded-snapshot-descriptor-rebinding-independent/verify.py`
is read-only: it verifies the frozen review, producer custody, fresh command
outputs/preimages and cleanup without compilers or runtime dispatch.
