# Independent affine-refusal C1–C2 review

Recommendation: **accept this frozen Python host correction within its stated
synthetic trusted-local scope**, subject to root acceptance. No blocking finding
was reproduced. This is not native/Rust implementation, compiler, pricing,
root-funding, operational, FieldLog, OTA, or GA acceptance.

The reviewed candidate is
`verification/swift-guarded-snapshot-prepaid-input-owner-affine-refusal`, seal
`2270f59809b80c49df907a7ea9c20faf4dd45735cabad275ae61065efc19c50b`
(67 members, 1728034 bytes; tree
`414e52ca03e3e1aab03a234287ad0bea32e499de021817bc8b5a456dd94d3a6f`).
The model hash is
`e18bdf16f9de346d3ab553a525d49b735c240ce86c0bdf9717b7a175767fed7f`;
the interface hash is
`4be6917189b7e37e660ff77e62535d6902be9c3bb320ae7140cb3ff4f19a5e4a`.
The binding C1–C2 correction contract is
`b023b8e816c5a68cfe565f0cf901676998ec50b189aca1ead0bb49dbce142d51`,
with prior independent-review seal
`a64f0cbb775265509b98bea63faca5e144e6d4b8f685898251ea12d506c8840a`
and root return
`97aa4d370d6c490e37302ad036e2af029cb6607972147c40c7dd63c410a28c9c`.
Root's frozen release hash is
`ef722611a7318031cdf656622263096f629741eb93008405688ce827aa631d39`.

Complete README, report, model, interface and contract were read before authoring
`review_controls.py`. These fresh tests and fixture bytes were written from the
contract and model API. They import only the frozen candidate model and this
review's custody helper; no producer or prior-review test or fixture is imported.
Earlier producer methods are audited as existing regression evidence only.

The final exact-source command passes **35 methods**, zero failures:

```text
/usr/bin/env -i PATH=/opt/homebrew/bin:/usr/bin:/bin LANG=C LC_ALL=C TZ=UTC PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 /opt/homebrew/bin/python3 -B verification/swift-guarded-snapshot-prepaid-affine-refusal-independent/run_review.py complete-final review_controls
```

The C1 four-Files/three-buffers witness now refuses after retaining all four safe
Files and three paid buffers. A same-carrier retry raises the identical refusal;
those represented owners retire in 46 steps before charge release. A different
later valid carrier never reaches leaf and permanently prevents complete release.
The forbidden old expected-dictionary call owns and consumes its attempt too;
dropping the fourth argument cannot make a same-carrier retry succeed. Its safe
complete owner set retires in the ordinary 47 steps.

Adjacent controls cover copied/foreign/stale/wrong views, dead/foreign/wrong
selected carriers, missing/duplicate/oversized/unknown collections, invalid/dead/
raw/foreign/already-adopted/malformed Files and foreign/unregistered/dead/shared/
uninitialized buffers. Known safe owners retire through the fixed captured roster.
Unknown/unsafe/foreign/unrepresentable obligations retain the whole charge and
cannot obtain a complete release token. Foreign owners are neither adopted nor
closed. An unknown collection's iterator, length and indexing hooks are never
called. No model handle's public close method is used.

Twelve synthetic work and storage units debit the existing reservation before
admission publication; cleanup remains unchanged. Eleven remaining units in either
dimension cannot publish admission. Post-admission operation exhaustion still
consumes the attempt and retains the original refusal. Generation replacement
cannot renew prepayment or an attempt. Same-carrier replay tests reuse the original
error without further tickets, owners, budget debit or collection walk; success
has one prepaid replay-refusal slot. Retiring and releasing the owner prevents
carrier resurrection.

This finite capture is not an unlimited public-call or whole-host resource grant.
The first attempt examines at most four slots per exact built-in collection. One
replay reference and sticky unresolved retention do not pay for arbitrary later
caller-created carriers, extra enumeration, call/argument/exception frames or
backing. Those remain external caller obligations, exactly as the candidate states.

C2 integration controls reject float extent/inode/mtime_ns witnesses, all eight
identity fields containing bool/float/string/null/list/object values, missing/extra
keys, wrong nested object type, unsigned/signed range errors and nonregular modes
before admission. Extent, all five limits, digests/nonce and exact top-level keys
remain strict. Typed but mismatched complete identities and extent cannot be
normalized into acquired values. Negative signed timestamps, including both signed
i64 boundaries in their allowed positions, pass full identity correlation and
complete retirement. The decoder remains a synthetic JSON parser with no real
manifest authentication or native bridge authority.

Independent retained-contract controls exercise all 13 adoption refusal positions,
39 acquisition operation cutoffs, 47 retirement failure positions plus 47 unwind
positions, cleanup 46/47, allocation requested/slack/original-error backing,
external startup/cycle rejection, nine closed provenance groups, all five limit
differences, and all 32 full identity field substitutions. A normal distinct-handle
positive still reaches only the synthetic model leaf and retires in exactly 47
steps. No native healthy-close claim follows from a synthetic live bit.

Fresh read controls enumerate **58904** successful schedules for extents 1–4
under the actual 32-attempt program, independently checking each extent count as
`choose(31 + extent, extent)`. They also cover all 0–31 EOF interruptions, refusal
at 32 interrupted attempts, short/overreported/bool/extra reads and block edges
4095/4096/4097/8192. The earlier producer's **100842** read-schedule evidence and
110-method final command remain audited regression evidence; they are not counted
as this review's independent enumeration or fresh methods.

`contract-attempt1` passed 31 methods. `complete-attempt1` passed 33. Two coverage
gaps, exact prepayment ordering and dead/foreign selected carrier states, were then
added; `complete-final` passes the final 35 methods. No command failed. Exact source
snapshots, argv, cwd, actual parent/child environment, Python version and executable
hash, output hashes, exits, duration and before/after input custody are retained
per command. All three children had 55-second deadlines, were reaped and had their
exact owned PID/PGID confirmed absent. There is no scratch or native process cleanup.

Every command rehashes the complete 479 declared prior input paths, the full
68-file current candidate packet, and the separate frozen root release: **548
paths**. Membership and all member hashes/tree/count/byte totals are checked for
all eight declared frozen packet seals. All inputs stayed unchanged before and
after every command and again at review freeze. Mutable PLAN/HEAD changes are not
priced frozen inputs; the source revision is taken only from the frozen root
release (`9398732c23648a82097d5a72b02b1c77af818e41`). No Git operation was performed.

The initial older preparation's absent historical environment is not reconstructed
or qualified here. Its statements and all earlier failed packets remain immutable.
This review's source reading/editing is preparation, not test evidence; the bounded
commands are the execution evidence. A lightweight MEMORY registry read supplied
only workflow/qualification boundaries; it supplied no test fixture, expected
value, source identity or current technical fact.

All 17 policy fields, 15 unselected policy fields, eight unverified claims, three
Pending selectors and six Pending upstream needs remain. FD_BASE, compiler/review/
path/packet caps, all actual prices, root funding, native ownership/image/allocator/
diagnostic bridges and fresh compiler/layout/work/storage/retirement bindings
remain pending or unselected. Historical source146
`acce2edaeb41d2e032cd9417897f828caa1c713721e162d2f455663600076e3d`
and host11 `027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2`
remain exact historical identities, not future-source bindings.

Existing setup/loader opens followed by private complete correlation before leaf
remain the minimum direction; all existing loader checks remain required and
same-handle loading stays optional and unselected. Trusted quiescent local launcher
assumptions are unchanged; arbitrary hostile Python mutation is not supported.
No compiler/query/product/native/runtime/phone/simulator/emulator/UI/capture/
computer-use, stopped Android v5, hosted driver, broad harness, global process
inventory, other-lane edit, dependency, publication or delivery operation occurred.
Root acceptance and all actual native/device/store/operational/FieldLog separate-
repository immutable-package/OTA/GA qualification remain pending. No GA gate passes.

`seal.json` records every other review file. All files are read-only after freeze.
The own read-only verifier is `python3 -B` with `seal_review.py --check` in this
directory; it performs custody hashing only and launches no old runner.
