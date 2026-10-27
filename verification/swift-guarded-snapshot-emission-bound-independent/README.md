# Independent snapshot emission arithmetic review

The frozen candidate is acceptable as an **unused, emission-only arithmetic
interface**, conditional on the already accepted encoder/writer/authority
interfaces. No candidate defect was found in this bounded review. This packet
selects no writer execution, operational debit, complete storage floor or GA gate.

Custody checks independently verified all58 producer members169951 bytes,
tree`b0877704d06924f65c7f15f23c9a7bca8b7ec8f28449ef90ad7f01b84a199e4b`;
the postseal freeze receipt is separately bound. The unchanged144-source base
tree`575b55d3391729749039dc2badccc9107449cb2c9a021d8ef67282c39b2e1896`
and exact two-file145-source overlay
tree`32e10cca35240748978ea635899cd14229814c61c0a6f7c988b1c2bed2980abc`
were reconstructed independently from actual bytes. The parent differs only by
the unused module declaration/comment. WorkAuditPending, actual begin callsite,
writer body and the complete control/budget source remain unchanged.

The accepted encoder call ceiling expands to
`26+68*515+39*(9*515)+139*513+4096=291214`. Composing the accepted encoder fixed
14224, writer`1217+4259B+122A`, native requested32E, and one4096 initializer gives
`19537+299377B+32E`, because A<=32B. The getter3 is already priced by the writer.
The accepted authority-routing extra19 belongs to earlier pre-admitted work.

The actual writer checks its guard counts and encoded extent before file
metadata/position/write operations. It returns at its first error, never retries
an encoder error, and breaks after the final block. It therefore needs at most
B nonempty cursor calls and no terminal None call. A failed call consumes a
prefix covered by the accepted nonempty-call ceiling. Each block has at most32
native write attempts; every request is at most that block's length. Summing
32 times each visited block length yields <=32E, including interrupted and
partial-write attempts. Early stops stay within the same whole planned envelope.
These are source/interface arguments; no encoder or writer was executed.

The helper has29 logical source actions under the accepted convention:
entry/return2, field fetches2, checked operations4, eager Arithmetic variants4,
ok_or inspect/Result construction8, three ? inspect/payload operations6, and
three bindings3. The four checked operations occur in order B*299377, E*32,
19537+transfers, and final addition. Any overflow returns Arithmetic; the first
three use ? and the final expression returns its Result directly. The error
prefixes cost at most9/17/24/29 under that convention. All terms are nonnegative,
so a successful value equals the mathematical sum without hidden wrapping.
This action convention is not CPU/instruction/time or stack/RSS measurement.

Fresh independent Rust tests imported the exact candidate helper and independently
reconstructed the real error/usage/shape declarations and original pure geometry
functions. Six groups passed in both debug and optimized host builds: exact
component/endpoints, all four checked edges and adjacent successes, an independent
u128 oracle grid plus4096 deterministic raw cases,2048 mixed valid geometry
counts/cap refusals, block-boundary/residue monotonicity and unchanged-budget
cutoff, and qualified host type observations. Synthetic raw integer shapes are
arithmetic controls; they are never runtime authority or proof fixtures.

Two retained mutants compiled and failed the intended tests with101: lowering
299377 by1 returned318913 instead of318914 at B1/E0, and replacing the first
checked multiplication with wrapping arithmetic returned278546 instead of
Arithmetic. These are expected controls, not accepted implementation variants.
The original helper is hashed before/after every compile/run and is unchanged.
The frozen full-source metadata negative independently demonstrates module
inclusion through its E0308 diagnostic in the actual helper module. No unresolved
inclusion question required a fresh full-source metadata compilation.

The maximum geometry still produces7331792842, exceeding the unchanged original
ExecutionWork ceiling1000000000. For the tested source-only geometry family,
E9515008 costs999952564 and E9515009 costs1000251973. These are pure comparisons,
not executed debits or budget grants. Zero counts yield E2560/B1 and400834;
that geometry does not prove an empty source is a validated Swift profile.
Host observations AError1096/8, Result1096/8, Option16/8, shape104/8 and reference8/8
do not select a simultaneous source-place floor or qualify device/target layout.

The following obligations remain binding:

- Count the transfer initializer4096 once. It is included here and also named
  by the future-begin7930 decomposition; those are the same occurrence.
- Pay helper29 under already admitted planning before computing its emission
  debit. That computed debit cannot fund its own prior calculation. Preserve
  caller ?/binding3 and review the actual future callsite.
- Fund helper reference/scalars/checked Option/eager Arithmetic/ok_or Result/
  ? success-error and return places before evaluation, which precedes the current
  storage commit. A later commit cannot retroactively pay those lifetimes.
- Close helper/caller simultaneous storage and target/compiler lifetime/layout
  obligations in the separate owner delta. Preserve shell, inherited, caller,
  stop, cleanup and F1 lifetime obligations. No active owner recipe was read or
  edited by this review.
- Correct and requalify the retained loader's parse_build checks144 source/11
  support against the145-source overlay and its exact support roster. Arithmetic
  and metadata acceptance do not establish genuine descriptor/profile binding.
- Preserve all canonical/native/OTA/FieldLog/store/customer/operational/GA gates.
  A canonical integration or complete work/storage selection needs its own review.

`commands/*` records actual argv, controlled environment, tool versions/source
preimages, outputs, exits, timing and owned child reaping. Each child has a45s
timeout; only its known process group can be killed. All children completed and
all newly owned scratch/binaries were removed. No global process inventory,
native/device/simulator/emulator runtime, UI, capture, prohibited hosted harness,
stopped Android experiment, canonical component folder or active owner-storage
closure was accessed or executed. Root owns Git and metadata delivery.

The initial review-script locator incorrectly assumed named descriptor fields;
the actual binary-offset checks were then inspected and the independent locator
corrected. `authoring-note.json` attributes that preliminary invocation separately.
All receipt-backed subsequent checks passed. Producer one-shot scripts were read
only where needed and never imported or executed.

`review.py` reproduces custody/type reconstruction into this review directory.
`run.py` is an intentionally one-shot evidence run: existing command directories
fail closed to retain prior attempts. `seal.py --verify` is read-only.
