#!/usr/bin/env python3
"""Apply only root-selected constant/test parameter delta; no old collector imports."""
from pathlib import Path
import hashlib,json,shutil,difflib
P=Path(__file__).resolve().parent
R=P.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
sel=R/'verification/swift-ordered-retention-analyzer-envelope-root-review/correction-numeric-contract-selection.json'
assert sha(sel)=='199dfa75b024d04eeef28f2f40165115797a0bbb3d09a2405426172d8339867c'
assert json.loads(sel.read_text())['numeric_contract_selected'] is True
B=P/'baseline';B.mkdir(exist_ok=False)
for part in ('src','tests','inputs'):
 (B/part).mkdir()
for name in ('analyzer.rs','envelope.rs'):shutil.copy2(P/'src'/name,B/'src'/name)
for q in (P/'tests').glob('*.rs'):shutil.copy2(q,B/'tests'/q.name)
for n in ('fsm-model.py','oracle.bin','oracle.json'):shutil.copy2(P/'inputs'/n,B/'inputs'/n)
shutil.copy2(sel,P/'inputs/root-correction-numeric-contract-selection.json')
orig=(P/'src/envelope.rs').read_text()
assert sha(P/'src/envelope.rs')=='e86ef43a99f99245c78308666f91f5147981859ca03fa3f97e62d46993667535'
repls=[('const FINISH_ENVELOPE: u64 = 8;','const FINISH_ENVELOPE: u64 = 47;'),('const RECORD_ENVELOPE: u64 = 128;','const RECORD_ENVELOPE: u64 = 425;'),('const SETUP_WRAPPER: u64 = 20;','const SETUP_WRAPPER: u64 = 42;'),('const FINAL_WRAPPER: u64 = 44;','const FINAL_WRAPPER: u64 = 42;'),('const UNDERFUNDED_GUARD: u64 = 36;','const UNDERFUNDED_GUARD: u64 = 112;'),('// HISTORICAL, UNQUALIFIED numeric constants; operation proposal does not select them.','// Selected operation-ledger partition W01..W09; outer F42 includes early-error13.'),('const WRAPPER_GROUPS: [u64; 12] = [4, 3, 3, 5, 4, 3, 3, 3, 3, 3, 3, 5];','const WRAPPER_GROUPS: [u64; 9] = [1, 3, 1, 2, 3, 2, 1, 5, 6];'),('    + WRAPPER_GROUPS[8] + WRAPPER_GROUPS[9] + WRAPPER_GROUPS[10] + WRAPPER_GROUPS[11];','    + WRAPPER_GROUPS[8];'),('// Current historical orchestration prepays128. Its unqualified guard reserve,','// Selected orchestration prepays425. Its separate fixed112-credit guard,')]
s=orig
for a,b in repls:assert s.count(a)==1,a;s=s.replace(a,b)
(P/'src/envelope.rs').write_text(s)
# Exact original20 remains in baseline. The active20 is derived only by this
# explicit selected numeric/test-input adaptation, not historical requalification.
q=P/'tests/envelope_tests.rs';t=q.read_text();original=t
repls=[('COMBINED_RECORD, 192','COMBINED_RECORD, 471'),('542','581'),('670','1006'),('1054','2281'),('798','1431'),('926','1856'),('581 + 128 *','581 + 425 *'),('581 + 11 * 128','581 + 11 * 425'),('remaining: 128','remaining: 425'),('(0, 128)','(0, 425)'),('poisoned(128)','poisoned(425)'),('for remaining in [0, 127, 128, 129]','for remaining in [0, 424, 425, 426]'),('p.debit += 128','p.debit += 425'),('remaining: 127','remaining: 424'),('(127, 0)','(424, 0)'),('0, 10, 2, 128, 0, 0]','0, 10, 2, 425, 0, 0]'),('REPORT_RESERVE - 7','REPORT_RESERVE - 46'),('REPORT_RESERVE - 8 - 35','REPORT_RESERVE - 47 - 111'),('../inputs/oracle.bin','../inputs/oracle-425.bin')]
for a,b in repls:
 assert a in t,a;t=t.replace(a,b)
t+='\n#[path = "selected_tests.rs"]\nmod selected_contract;\n'
q.write_text(t)
q=P/'tests/correction_tests.rs';t=q.read_text();oldcorrection=t
for a,b in [('debit: 670','debit: 1006'),('99, 128, 0, 0]','99, 425, 0, 0]'),('remaining: 128','remaining: 425'),('1054','2281')]:assert a in t,a;t=t.replace(a,b)
q.write_text(t)
# Accepted model bytes stay unchanged; new test model changes only its debit.
model=(P/'inputs/fsm-model.py').read_text();assert model.count('RECORD_DEBIT = 128')==1
(P/'inputs/fsm-model-425.py').write_text(model.replace('RECORD_DEBIT = 128','RECORD_DEBIT = 425'))
changes={}
for name,old,new in [('src/envelope.rs',orig,s),('tests/envelope_tests.rs',original,(P/'tests/envelope_tests.rs').read_text()),('tests/correction_tests.rs',oldcorrection,(P/'tests/correction_tests.rs').read_text()),('inputs/fsm-model-425.py',model,(P/'inputs/fsm-model-425.py').read_text())]:changes[name]=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='baseline/'+name,tofile=name))
(P/'selected-contract-delta.json').write_text(json.dumps({'schema':1,'root_selection_sha256':sha(sel),'baseline_proposal2_source_sha256':sha(B/'src/envelope.rs'),'selected_source_sha256':sha(P/'src/envelope.rs'),'analyzer_parent_unchanged':sha(P/'src/analyzer.rs')==sha(B/'src/analyzer.rs'),'diffs':changes,'scope':'Only root-selected constants/compile-time W partition/comments and separately derived test/model numeric expectations. Accepted historicalmodel/test/source bytes retained in baseline; no production control-flow/owner change.'},indent=2)+'\n')
print(json.dumps({'source_sha256':sha(P/'src/envelope.rs'),'model425_sha256':sha(P/'inputs/fsm-model-425.py'),'baseline_tests20_sha256':sha(B/'tests/envelope_tests.rs')},indent=2))
