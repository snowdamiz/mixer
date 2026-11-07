#!/usr/bin/env python3
"""Explicit authored group/copy budget; pending independent source audit.

Groups are bounded Rust source operations, never CPU instructions or runtime.
One group covers at most16 bounded scalar operations or one<=128-byte copy.
Every fixed slot is charged, including inactive/error arms; no refunds.
"""
import hashlib
import json
from pathlib import Path

BASE=Path(__file__).resolve().parent
WRAPPER=[
 ('record admission/iteration/combined debit call wrapper',4,'walk_fixture_envelope_v1: preflight through atomic combined Budget call; fixed new-wrapper argument/control receiving places'),
 ('cumulative128 reservation counter update',3,'walk_fixture_envelope_v1: p.debit update before any read, plus holder borrow/source/destination'),
 ('decoded-record construction and caller/callee borrow',3,'walk_fixture_envelope_v1: FixtureDecodedRecordV1 with private immutable128 backing borrow'),
 ('latch eligibility and leaf_pending call/return',5,'leaf_pending + new walk condition; absent/Observed/status refusal branches charged regardless of branch'),
 ('StepBudget construction and complete argument handoff',4,'new walk: two-u64 source/owner and four leaf borrows including Vec-to-slice view'),
 ('complete received reply source/return/caller128',3,'observe_fixture_envelope_v1 return and received local128; each complete<=128 fixed copy has a slot'),
 ('progress reply install and reply_valid transition',3,'new walk: p.reply=received then reply_valid=1; no initialObserved projector'),
 ('normal debit postcondition audit',3,'reply_debit_valid funded branch and caller boolean/error control'),
 ('underfunded guard debit postcondition audit',3,'reply_debit_valid Steps0 branch; inactive fixed slots remain paid'),
 ('audit-failure fixed poison constructor/source/return',3,'poisoned128 plus new walk source/return copy; fixed error arm always reserved'),
 ('audit-failure destination/latch handling',3,'new walk: poisoned128 into p.reply; no subsequent eligible leaf call'),
 ('latched skip/source-scope exit and result/error receiving',5,'new walk: branch/source lifetime exits and complete fixed receiving/error borrow places after earlier refusal/poison'),
]
SETUP=[
 ('Progress zero128 source + Reply128 constructor',2),
 ('Progress144 source/destination/conservative move, each split<=128',6),
 ('fixed main wrapper setup/report admission calls and complete error receiving',4),
 ('Progress borrow/initial private discriminator/debit scalar bookkeeping',4),
 ('separate guard reservation call/error/return before mutation',4),
]
FINAL=[
 ('returned input-error classification and fixed error borrow/receiving',6),
 ('private input-success/complete/limited eligibility and absence projection dispatch',5),
 ('limited-boundary/refusal firstreason projection dispatch',4),
 ('unsupported-status/state fixed public unavailable projection dispatch',4),
 ('closed leaf reason to fixed typed enum conversion',4),
 ('public observation eleven conditional extent fields and debit/authority constants',6),
 ('complete observation128 source/return/caller/project movement',4),
 ('aggregate232 source/destination/Result/public/caller moves split<=128',8),
 ('outer public/error receiving and fixed final return handling',3),
]
GUARD=[
 ('twelve checked prior loads: <=16scalar/check/borrow/Pair-return operations plus one8-byte fixed array copy',24),
 ('complete prior96 initializer/source/destination',2),
 ('twelve bounded iteration/index/control groups',3),
 ('complete128RefusedSteps/prior source/return/caller reply handling',4),
 ('underfunded predicate/prepaid guard bookkeeping and no-mutation return',3),
]
# Actual source bound deliberately does not force its sum to prepaid128.
# Unused contract credits are never reused/refunded. Review every source group.
LEAF=[
 ('private entry/subdivision debit/predicate',2),
 ('twelve checked prior loads and fixed loop bookkeeping',27),
 ('retained-state discriminator/invariant checks',2),
 ('closed wire shape helper: common and maximum kind arm, including Options',12),
 ('sequence/work/instruction/terminal coordinate guards',3),
 ('complete prior-to-next96 source/destination copy',2),
 ('phase/release/failure/acquire/stage/publication transition maximum fixed arm',9),
 ('twelve bounded candidate8byte stores; all destination ranges prechecked by priorloads and sized candidate',24),
 ('twelve prechecked commit fixed copies and address/loop work',24),
 ('complete fixed observed/refused/poison reply source/return/error handling',6),
]

def main():
    w=sum(n for _,n,_ in WRAPPER);t=sum(n for _,n in SETUP);f=sum(n for _,n in FINAL);g=sum(n for _,n in GUARD);leaf=sum(n for _,n in LEAF)
    assert (w,t,f,g,leaf)==(42,20,44,36,111)
    b=22+128+w;assert b==192 and b<=8192 and leaf<=128
    value=dict(schema=1,status='authored-actual-source-group-proof-awaiting-independent-review',source_sha256=hashlib.sha256((BASE/'src/envelope.rs').read_bytes()).hexdigest(),group_rule='at most16boundedscalar source operations OR one<=128-byte fixed copy; bounded loops charged each iteration; allbranches conservativelyreserved; never CPU/RSS qualification',record=dict(framing=22,envelope=128,wrapper=w,combined=b,mandatory_preflight=8192,wrapper_groups=[dict(name=s,groups=n,source=m) for s,n,m in WRAPPER],leaf_groups=[dict(name=s,groups=n) for s,n in LEAF]),fixed=dict(envelope_setup=534,envelope_finish=8,wrapper_setup=t,wrapper_final=f,underfunded_guard=g,wrapper_setup_groups=[dict(name=s,groups=n) for s,n in SETUP],wrapper_final_groups=[dict(name=s,groups=n) for s,n in FINAL],guard_groups=[dict(name=s,groups=n) for s,n in GUARD]),reservation_order=['Budget.new reserves IO263584+report3000000','wrapper setup20 and report44 admission before arena/progress/input work','reviewed output safety and Arena allocation/initialization','reviewed context/profile/header admission','main setup534 succeeds then debit+=534','main report8 succeeds then debit+=8','main report guard36 succeeds before candidate initializer/cell mutation','single Candidate2048 initializer and twelve cells','before each record require8192 then atomic main replay192 then debit+=128 then decode','leaf128 is a subdivision; guardSteps0 may runatmostonce, latchesRefused','complete/limited/error table after all required metadata','fixed report and finalResult; no refunds'],envelope_debit='534*S+8*F+128*N; includes failed reads/framing and skipped latched calls; zeroextent never zeroes truthful debit',step_ceiling=268435456,setup_cap=65536,report_reserve=3000000,io_reserve=263584,arena_init=1048576,profile=640000,record_cap=4194304,full_cap_promised=False,leaf_slots_versus_contract='128 total unchanged; exact typed-borrow Rust operation mapping refines finite-contract illustrative schedule and requires root/independent confirmation before acceptance',overlap='Framing22 owns reviewed decode/closed profile identity/coordinate work; leaf128 owns acquisition transition; W owns added typed-record/progress/latch/StepBudget/reply handoff only. Fixed setup534 and finish8 retain leaf work; T20/F44/G36 own named added wrapper/guard work. No paidcreditis reused, refunded or silently drawn from spare margin.',limitations=['authoredlogicalsourcegroups, notcompilerCPUinstructions','no fulltarget or throughput acceptance','independent review required before accepting actual combined proof'])
    (BASE/'step-inventory.json').write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps(dict(B=b,W=w,T=t,F=f,G=g,leaf=leaf,scope=value['status'])))
if __name__=='__main__':main()
