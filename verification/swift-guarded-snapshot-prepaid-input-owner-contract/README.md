# Child-owned prepaid immutable input contract

This is a source/interface proposal plus independent pure-host state tests. It
implements no product entry, root policy, allocation adapter, native bridge,
loader route or operational grant. No compiler or product executable was run.
The three existing production selectors remain Pending. Root approved preparing
this packet, not selecting its policy or funding. The frozen lifetime review
is evidence of lifetime preservation; root acceptance and the provider review
are separate. No active provider-independent/string-correction files were read.

The current provider source146 proposal is
`acce2edaeb41d2e032cd9417897f828caa1c713721e162d2f455663600076e3d`;
provider seal SHA is
`7af047d181125c0e3da36f2d4585d4a31204bedf8f367793300022391aca02de`.
It only describes already-borrowable slices. The frozen lifetime base is
`69068367d2eaf334d6881a624cac9142a0b4ecfeed50f23382724ae29e51d5e7`,
with seal `84a9bf52a127f5fcebd5d6db3dedb9c0e65fc9ef9cfd57b432c8e1f65f8e5ed2`.
The independent lifetime packet seal is
`e11d9eff0eda83ccf46563526e3c7025172cc8e05513b4a9ba1a5a0d9c13344a`.
This packet rehashes these frozen members and all146 proposed source members
through explicit custody, rather than trusting labels. These are input evidence
identities, not authority constructors. The11 host members remain a separate
roster; they must be rebound with the eventual final source and tool closure.

## The bootstrap boundary that is missing today

The existing `host_account_v1.rs` makes `TrustedRootPolicyV1` and its account
constructor private. `selected_parent_account_v1()` returns `RootPolicyPending`;
no production path can call that constructor successfully. Its numeric fields
and `source_and_review_binding` do not establish external allocation, identity
or trust. Tests fabricate counters for pure accounting tests only. The loader
explicitly assumes a trusted, quiescent local macOS launcher and provides
correlation, not package authentication.

A concrete fixture-only way forward is to extend this existing trusted-local
assumption, in source, with a private `FixtureBootstrapPolicyV1` and exactly one
private entry compiled under the fixture cfg. The accountable source/root
reviewer establishes its finite numeric costs from the final implementation,
compiler layouts and exact native/std allocation/diagnostic contracts. A
separately reviewed launcher reserves its own work/storage and provisions the
child startup frame, inherited handles, initial policy/account records and all
failure/retirement places BEFORE spawn. The child's fixed source-selected
bootstrap reserves the complete acquisition maximum BEFORE adopting or probing
an input handle. No length, digest, review JSON, argv/environment variable,
requested limit or FD integer supplied by the payload may create this policy.

`BootstrapLedgerV1::from_preexisting_fixture_startup_v1()` is the exact private
acquisition-root constructor proposed in `interface.inc.rs`; internally it calls
`FixtureBootstrapPolicyV1::selected_fixture_v1()`. Neither accepts caller-supplied
limits, digest or authority arguments. They must eventually use only
source-reviewed constants under that cfg. Quantities are not invented here.
Its first call/return frames are covered by the launcher's preexisting child
startup provision; a counter created inside an unpaid frame cannot fund itself.
The same source-root process establishes the launcher's preexisting provision.
This is the explicit external trust anchor, not an infinite chain of accounts
that mint one another. Nothing currently selects that anchor in product code.

This mechanism works only for the existing trusted local fixture threat model.
It does not authenticate an adversarial launcher or provide a transferable OTA
grant. Arbitrary launchers cannot gain guest/product access because no public
entry or production selector is added. If the intended scope includes hostile
launchers, an independent existing OS/provisioning authority and authenticated
channel must first be specified; a numeric FD convention is insufficient. No
new signature scheme, private key, acceptance witness or approval rule is
introduced here.

## Concrete transfer and child ownership

The proposed launcher protocol inherits exactly13 role-fixed regular-file
descriptors, in a reviewed fixed contiguous range starting at a still-selected
`FD_BASE`. Slots0..11 are source, build, session, actual output executable,
compiler executable, compiler-version stdout, compile manifest, compile argv,
compile environment, process argv, process environment and review. Slot12 is
one5-path packet. The parent opens every actual object, verifies exclusive
immutable custody, installs each exact child FD with inheritance enabled, closes
unrelated capabilities in its child launch configuration, and launches once.
It retains its owners and forbids writes/rename/replacement until all child
owners/results retire. Parent addresses and Rust borrows cross no process
boundary. FD slot numbers identify roles only; the trusted launcher assumption,
actual handles, metadata and bytes establish custody. Native descriptor
installation, no-collision/no-extra-handle guarantees and actual launch/image
mapping remain native bridge obligations, not tested host facts.

Before any `from_raw_fd`, metadata, seek, read, hash, parse or allocation, the
source-selected bootstrap commits the entire finite acquisition quote. Fixed
array storage and all argument/result/return overlap already belong to P0.
The proposed private native bridge runs before any threads or handlers that can
close/reassign these slots, accepts no FD argument, validates each fixed slot
with prepaid native descriptor/metadata operations, and adopts it exactly once
only after validity succeeds. A startup adoption bitmap and partial-owner table
are already in P0; no preexisting Rust `File` owns a slot. The launcher must
provide those facts, forbid duplicate slots and install13 pairwise distinct
device/inode objects. Child aliases, close/reuse races and unsupported startup
conditions refuse before unsafe ownership conversion. The parent retains OS
handles but never reads/seeks/writes them after the prelaunch reset to offset0,
because an inherited open-file description can share an offset across processes.
The reviewed native bridge must establish this contract; a checked integer or
an unchecked `File::from_raw_fd` call is not that bridge. Already-adopted owners
return on every refusal; no arbitrary `Read`, callback or trait object can mint
a trusted acquisition. Regular-file metadata gives an actual
extent. Checked conversion, role cap, remaining paid storage and planned work
must all succeed before a payload allocation or read. Every payload block is
at most4096 bytes, each block/EOF request has at most32 attempts including
Interrupted, and every metadata/offset/seek/hash operation has a prepaid ticket.
Partial/zero/overreported reads, extra data, bad position, non-regular files,
alias violations, changed metadata, arithmetic overflow or unsupported native
behavior fail closed. There is no reopen, retry entry or guessed success.

Each of the12 full identity preimages receives its own owned immutable buffer.
The5-path packet is `MIXPTH01`, version1, header64, total length, then five
positive u64 lengths at offsets24..64, followed by the exact5 raw path bodies
with no tail. A separate source-selected cap for each fixture path and a checked
packet cap are required; the loader's4096 executable-path/cwd cap DOES NOT
bound these5 paths. Decoding is length-bounded and prepaid. The child separately
allocates five native-pointee byte buffers and five retained byte buffers. It
copies the packet bodies twice under the reservation; equality/aliasing offers
no credit. A native `Path` borrows `Path::new(OsStr::from_bytes(&native[i]))`
within an inner scope. This avoids an unpriced PathBuf growth operation and a
self-referential owner. All paths are nonempty and contain no NUL. Raw non-UTF8
bytes survive. The packet buffer's peak backing is still charged until its
actual destruction, even though it is not one of the22 final bodies.

Allocation needs a concrete private adapter whose reviewed contract bounds
requested extent, capacity/slack and failure backing BEFORE invoking it. A
post-allocation `Vec::capacity() == len` check does not pay for an earlier
oversized allocation. `try_reserve_exact` alone supplies no such guarantee.
Logical requested-byte accounting must be distinguished from allocator/RSS
accounting. No native or allocator implementation of this adapter is supplied.

## Authentication and the non-circular build order

Authentication is two separate things: the external trusted local launcher
provides the reviewed fixture policy/object custody, and the child verifies
cryptographic/content/record correspondence under that provision. Hash
agreement alone supplies neither authority nor file immutability. The child
hashes each actual owned body with the existing standard CommonCrypto primitive
through a narrowly exposed private paid helper, or an equivalently reviewed
standard implementation. The current loader helper is private and is not yet
callable from the provider. No hashing callback is accepted as a trust anchor.

The child verifies all twelve digests, selected source1947 and SHA
`9804738523f3053f2b7a0093ecd5b324ecf54b1d43094993cdb2ee7d63747806`,
build/session framing and reserved bytes, source146/host11, target, all section
hashes and full-byte correspondence. The manifest remains opaque to the old
loader, so the acquisition verifier must also check the exact reviewed full
distribution/compiled-source/host/tool/orchestration closure, with bounded
decoding or a reviewed fixed binary schema. Merely checking146/11 does not do
this. The final changed source needs a new external roster; no hash listed
above identifies future source automatically.

1. Freeze final distribution/source146 and host11, tools, orchestration and the
   reviewed fixed bootstrap policy. Before compilation retain exact manifest,
   argv, compiler executable, compiler-version stdout and compile environment.
   Exclude exactly the five existing injected compile-identity keys from that
   environment preimage. Compile embeds only those five precompile digests.
2. Compile once under a separately reviewed bounded plan. The final executable
   is knowable only afterward. Externally retain its actual bytes, hash/extent
   and actual File identity, then construct the immutable build record. The
   compile manifest and source do not embed their own hash or that output hash.
3. Externally generate the fresh session record from the actual source File
   identity64, source/build/executable hashes, exact validator limits, fresh OS
   nonce, actual process argv/environment and cwd. Process environment excludes
   exactly the two session/nonce keys. Inject those two values separately.
4. Freeze an external bounded review artifact over the actual source/build/
   executable/session identities and original policy. Its own hash is supplied
   by trusted launcher custody, not contained inside that artifact, compiled
   source or session. A review JSON saying it approves itself is untrusted data.
   The external artifact must identify its accountable source-root provenance;
   this packet creates no review acceptance. Compiled code receives neither its
   own final hash nor an artifact that includes itself before compilation.
5. Transfer actual File owners and bytes under the trusted local launch
   provision. The child verifies its observed process bytes/session/nonce and
   actual executable handle/image custody; the native bridge must establish
   image-to-handle correspondence under exclusive quiescent launcher control.
   The old pathname reopening is insufficient to prove this new relationship.

This removes three cycles: acquisition funding comes from preexisting P0, never
the later child account/refund; compile identities exclude the injected values;
the executable/build/session/final review are external postcompile products,
never self-embedded compiler inputs. Review/custody of those external values is
a trusted-local launch contract, not a hash fixed point or newly minted grant.

## Existing route compatibility and private source changes

The current `setup_files_once_v1` opens source/build/session by path and
`load_inner` opens the observed executable. Different handles alone do not
violate the existing trusted quiescent launcher assumption. `load_inner` already
rehashes all four actual bodies, checks embedded build identities, expected
session/nonce/process, source FileIdentity64, four-file anti-aliasing and all four
final metadata records. These checks must not be described as absent. The gap
is the link from the newly admitted child owner to that independently opened
loader result: `run_prepaid_fixture_v1` currently dispatches the selected result
straight to the leaf, while the loader's provenance fields are private.

The minimum compatible design retains existing setup/open/read behavior and
adds a private `correlate_admitted_loader_v1` in the loader. Before the leaf, it
compares source/manifest/build/session/executable/nonce/validator limits/extent
and all four actual FileIdentity64 records to the admitted child's retained
values. The source-root launcher supplies immutable path-to-object custody for
the full interval; the child still checks actual native path bytes. Refusal
retains the original loader result/files and the new original correlation
diagnostic under the same reservation. This changes the execution entry's
pre-leaf branch and adds helper/view/diagnostic/caller work and storage; it does
not require replacing the existing parser, validation or setup algorithm.
All reopened loader buffers/File owners coexist with the12 input-preimage
owners, and both sets are paid in full. Hash equality gives no sharing credit.

An alternative private route, `run_prepaid_admitted_fixture_v1`, moves the SAME
source/build/session/executable `File` owners into a new
`load_preopened_selected_retained_profile_v1`; setup then opens only the two
outputs with create_new. Rewind to offset0 is separately prepaid and followed
by same-handle identity checks. It removes inter-stage pathname reopens but
requires larger source/cost/ownership rebind and actual native bridge review.
It keeps the same validation/equality/hash/anti-alias/final metadata obligations
and full buffer prices, and does not prove image mapping by itself. Neither
route is selected here. The minimum compatible route is the proposed first
implementation choice within the existing threat model. The old eight claims
remain unverified original claims.

An admitted owner is produced only after all actual checks. It owns all backing
and handles, and supplies no mutable access. A second inner lexical scope builds
`ReviewedFixtureBindingV1<'p0>`, the existing candidate and request as views of
that owner; the owner stays alive through final returned result consumption.
The execution entry consumes the request once; acquired handles remain owned
through result consumption (or move once on the optional same-handle route). Its
complete six-component child reservation occurs before output setup or loader
work. All17 original product fields stay explicit; only execution_work1B and
combined_bytes256MiB are selected constraints today. The five original validator
limits and existing original diagnostic payloads are preserved. Admission does
not mint a validator proof, quote, child account, release/close receipt or GA.

The old conditional work2706170 and fixed inline292037 apply only to their
original exact-source scope. Add the new acquisition/bridge/owner/provider and
new caller/loader routes, error backing, future upstream inline/temporary places
and destruction work/storage. Original diagnostics stay charged through real
destruction; no flattening, reconstruction, formatting or `Error::source`
callback is used. All acquisition refusals retain every actual original
diagnostic/partial buffer/File under P0. Counter release follows actual complete
owner/carrier destruction; unwind/no token conservatively retains the charge.
No observed token proves a healthy OS close. The native/std allocator and error
backing closure are not priced yet, so native acquisition must remain disabled.

## Exact outstanding inputs and validation scope

`contract.json` enumerates computable loader caps and every missing policy cost
and target contract. Ten identity caps are derivable now. Compiler full-preimage,
review artifact, five fixture paths and their packet caps need explicit source
selection after observing the final bounded fixture. Caps are finite limits,
not prices or approved allocation. All prices, native syscall behavior, descriptor
ownership/install rules, image correspondence, allocation failure capacity,
diagnostic backing and complete source/layout work remain unpriced.

`model.py` is independently written and uses no producer oracle/parser/runner.
It models prepayment, handle identity/cap/offset checks, finite reads, exact
storage admission, independent owner bodies, immutable admission, no reopen,
atomic refusal, original result retention and retirement. Its positive budgets,
metadata and digests are synthetic TEST DATA only. It produces no authority.
`test_model.py` includes adverse cases and reads/rechecks actual frozen inputs.
Those tests establish the proposed model invariants, not native code, the Rust
sketch's compilation, actual File/allocator effects, trust authentication or
operational selection. String Lstr5080/native proof remain pending. No device,
UI, capture, runtime, FieldLog, OTA, customer or GA qualification is claimed.

Reproduce with `python3 -B verification/swift-guarded-snapshot-prepaid-input-owner-contract/run_host.py unique-label`.
Run once before freeze; the retained command records source/tool/input custody,
argv, stdout/stderr, terminal status and scope. After freeze,
`python3 -B .../check.py --read-only` rehashes members without writes or programs.
No native child/scratch resource exists to clean up; other projects were not
inventoried or touched. Early source-navigation errors/truncated outputs are
retained in `exploration.json` and are not silently counted as verification.
