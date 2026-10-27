"""Prepare a compact, private source overlay; never execute Mixer."""
from pathlib import Path
import difflib
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
BASE = HERE.parent / 'swift-guarded-snapshot-funding-implementation'
CONTROL = 'src/experimental_swift_reactor/control.rs'
TESTS = 'src/experimental_swift_reactor/control_tests.rs'
BASE_TREE = '7e3e861ca65d8c6359623443d6a7810b878c1029494a0ae557307d35ed43484b'
BASE_SEAL = 'e006b90b8c9e351e0d4dd504c6de309e2c7970b628fe9fc4f788cb30e77bedf7'
WORK_RECEIPT = ROOT / 'verification/swift-semantic-adapter-root-review/guarded-snapshot-full-work-host-acceptance.json'
WORK_RECEIPT_SHA = 'ca79a84f7c6aa4277ca9a00a5f64c8d214a3c43c051a14577b9614a39b1a59b9'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':')).encode()

def write(name,value):
    (HERE/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')

def base_members():
    assert sha((BASE/'seal.json').read_bytes()) == BASE_SEAL
    manifest=json.loads((BASE/'source-manifest.json').read_text())
    rows=manifest['members']
    assert len(rows)==144 and sha(canonical(rows))==BASE_TREE
    for row in rows:
        data=(BASE/'source/vm'/row['path']).read_bytes()
        assert (len(data),sha(data))==(row['bytes'],row['sha256']),row['path']
    assert sha(WORK_RECEIPT.read_bytes())==WORK_RECEIPT_SHA
    return rows

SHELL='''            // Private selected admission shell. Budget/deadline/stop checks
            // above retain precedence. No host bootstrap grant is minted here.
            // Only the sealed policy selects this source-derived fixed price.
            if P::FIXED_EXECUTION_WORK_V1 != 0 {
                if P::FIXED_EXECUTION_WORK_V1 > control.budget.execution_work {
                    return Err(control.fail(
                        cursor,
                        Fault::new(SwiftRunFailureKind::WorkExhausted, "swift_run_work")
                            .limit(SwiftRunResource::ExecutionWork,
                                P::FIXED_EXECUTION_WORK_V1, control.budget.execution_work),
                        None,
                    ));
                }
                // The prepaid interval starts after this same-counter commit.
                // Refusal leaves the counter and all reservations unchanged.
                control.execution_work = P::FIXED_EXECUTION_WORK_V1;
            }
'''

CONSTANTS='''// Closed source144 logical prefix, ingress, and both optional terms are
// conservatively prepaid once. The exact new shell branch upper-sum is 1272.
// Planning16384 and the separately gated emission quote remain later debits.
const SNAPSHOT_FIXED_EXECUTION_WORK_V1: u64 =
    451_703_621 + 33_613 + 68_781 + 7_155 + 1_272;
// Initial metadata probe uses zero only until all newly introduced compiler
// source roles are measured. It must not be frozen or dispatched as funding.
const SNAPSHOT_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1: usize = 0;
'''

def main():
    assert not (HERE/'seal.json').exists()
    rows=base_members()
    text=(BASE/'source/vm'/CONTROL).read_text()
    marker='            control.check(cursor)?;\n            control.owner = NEXT_OWNER'
    assert text.count(marker)==1
    text=text.replace(marker,'            control.check(cursor)?;\n'+SHELL+'            control.owner = NEXT_OWNER')
    text=text.replace('    type Retirement;\n    fn foundation()', '    type Retirement;\n    const FIXED_EXECUTION_WORK_V1: u64;\n    fn foundation()')
    text=text.replace('    type Retirement=();\n', '    type Retirement=();\n    const FIXED_EXECUTION_WORK_V1: u64 = 0;\n')
    text=text.replace('    type Retirement=Result<(),SwiftRunFailure>;\n', '    type Retirement=Result<(),SwiftRunFailure>;\n    const FIXED_EXECUTION_WORK_V1: u64 = SNAPSHOT_FIXED_EXECUTION_WORK_V1;\n')
    marker='const SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1: usize = 941_467;'
    assert text.count(marker)==1
    text=text.replace(marker,CONSTANTS+marker)
    marker='Some(common) => common.checked_add(SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1),'
    text=text.replace(marker,'''Some(common) => match common.checked_add(SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1) {
            Some(selected) => selected.checked_add(SNAPSHOT_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1),
            None => None,
        },''')
    out=HERE/'overlay'/CONTROL
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(text)
    (HERE/'source-delta.patch').write_text(''.join(difflib.unified_diff(
        (BASE/'source/vm'/CONTROL).read_text().splitlines(True),text.splitlines(True),
        fromfile='accepted-source144/'+CONTROL,tofile='candidate-source144/'+CONTROL)))
    candidate=[]
    for row in rows:
        p=HERE/'overlay'/row['path']
        candidate.append(dict(path=row['path'],bytes=p.stat().st_size,sha256=sha(p.read_bytes())) if p.exists() else row)
    write('source-manifest.json',dict(schema=1,base_tree_sha256=BASE_TREE,base_seal_sha256=BASE_SEAL,
        work_receipt_sha256=WORK_RECEIPT_SHA,members=candidate,source_tree_sha256=sha(canonical(candidate)),
        source_members=len(candidate),overlay_paths=[CONTROL],candidate_runtime_selected=False))
    write('preparation.json',dict(schema=1,source_contract='private selected compare/store after unchanged bootstrap validation before owner allocation and five admissions',
        fixed_work=451814442,action_delta=1272,provisional_storage_delta=True,
        bootstrap_pregrant_qualified=False,H_pre_ingress_qualified=False,WorkAuditPending_preserved=True,
        writer_dispatch=False,canonical_changes=False))

if __name__=='__main__':
    main()
