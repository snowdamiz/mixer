"""Correct shared-source attribution in an isolated compact overlay only."""
from pathlib import Path
import difflib
import hashlib
import json
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
ORIGINAL = HERE.parent / 'swift-guarded-snapshot-work-admission'
BASE = HERE.parent / 'swift-guarded-snapshot-funding-implementation'
OWNER = HERE.parent / 'swift-guarded-snapshot-owner-storage-alias-correction'
CONTROL = 'src/experimental_swift_reactor/control.rs'
TESTS = 'src/experimental_swift_reactor/control_tests.rs'
BASE_TREE = '7e3e861ca65d8c6359623443d6a7810b878c1029494a0ae557307d35ed43484b'
BASE_SEAL = 'e006b90b8c9e351e0d4dd504c6de309e2c7970b628fe9fc4f788cb30e77bedf7'
ORIGINAL_SEAL = 'e8fe23ee4800a76ac6ca1486604b98b114a1f4dbdec1a25f520641c4e9951940'
ORIGINAL_TREE = 'c909e78b0cd12c719f8366f5a701e871c86d8d640d90f34cb5dbe49ea9d5e712'
RELEASE = ROOT / 'verification/swift-semantic-adapter-root-review/guarded-snapshot-work-admission-independent-release.json'
RELEASE_SHA = 'e902912c64ecb585782fd92e164377e46aefa3c3c1e7771ce0760655c3316e3d'
OWNER_FUNDING_SHA = 'ebe01914744ed8ff07f83c3d762beef8e0951616b560d151d70b1bdfeca7089f'

def sha(data): return hashlib.sha256(data).hexdigest()
def canonical(value): return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
def write(name, value): (HERE/name).write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')
def row(path, data): return dict(path=path, bytes=len(data), sha256=sha(data))

def base_members():
    assert sha((ORIGINAL/'seal.json').read_bytes()) == ORIGINAL_SEAL
    seal = json.loads((ORIGINAL/'seal.json').read_text())
    assert len(seal['members']) == seal['member_count'] == 85
    assert sha(canonical(seal['members'])) == seal['manifest_sha256']
    for r in seal['members']:
        assert row(r['path'], (ORIGINAL/r['path']).read_bytes()) == r, r['path']
    assert sha(RELEASE.read_bytes()) == RELEASE_SHA
    assert sha((BASE/'seal.json').read_bytes()) == BASE_SEAL
    rows = json.loads((BASE/'source-manifest.json').read_text())['members']
    assert len(rows) == 144 and sha(canonical(rows)) == BASE_TREE
    for r in rows:
        assert row(r['path'], (BASE/'source/vm'/r['path']).read_bytes()) == r, r['path']
    original_rows = json.loads((ORIGINAL/'source-manifest.json').read_text())['members']
    assert sha(canonical(original_rows)) == ORIGINAL_TREE
    assert sha((OWNER/'funding.json').read_bytes()) == OWNER_FUNDING_SHA
    return rows

def main():
    assert not (HERE/'seal.json').exists()
    rows = base_members()
    original = (ORIGINAL/'overlay'/CONTROL).read_text()
    before = '''// Twenty new unoptimized compiler source roles total1436 logical bytes.
// No old role is credited; core and all existing closure captures are unchanged.
const SNAPSHOT_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1: usize = 1_436;'''
    after = '''// Twenty new shared, non-P-dependent unoptimized source roles total1436
// logical bytes. Charge every role to common C; no old role is credited.
const COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1: usize = 1_436;'''
    assert original.count(before) == 1
    corrected = original.replace(before, after)
    before = 'Some(original) => original.checked_add(COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1),'
    after = '''Some(original) => match original.checked_add(COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1) {
            Some(common) => common.checked_add(COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1),
            None => None,
        },'''
    assert corrected.count(before) == 1
    corrected = corrected.replace(before, after)
    before = '''Some(common) => match common.checked_add(SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1) {
            Some(selected) => selected.checked_add(SNAPSHOT_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1),
            None => None,
        },'''
    after = 'Some(common) => common.checked_add(SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1),'
    assert corrected.count(before) == 1
    corrected = corrected.replace(before, after)
    target = HERE/'overlay'/CONTROL
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(corrected)
    for filename, baseline, name in [('correction-delta.patch',original,'original-work-admission-source144'),
                                      ('source-delta.patch',(BASE/'source/vm'/CONTROL).read_text(),'accepted-funding-source144')]:
        (HERE/filename).write_text(''.join(difflib.unified_diff(baseline.splitlines(True), corrected.splitlines(True),
            fromfile=name+'/'+CONTROL, tofile='corrected-source144/'+CONTROL)))
    candidate = [row(r['path'],corrected.encode()) if r['path']==CONTROL else r for r in rows]
    write('source-manifest.json',dict(schema=1,members=candidate,source_members=len(candidate),
        source_tree_sha256=sha(canonical(candidate)),base_tree_sha256=BASE_TREE,base_seal_sha256=BASE_SEAL,
        original_tree_sha256=ORIGINAL_TREE,original_seal_sha256=ORIGINAL_SEAL,overlay_paths=[CONTROL]))
    (HERE/'inherited-source-role-delta.json').write_bytes((ORIGINAL/'source-role-delta.json').read_bytes())
    (HERE/'inherited-work-delta.json').write_bytes((ORIGINAL/'work-delta.json').read_bytes())
    (HERE/'host-controls.inc.rs').write_bytes((ORIGINAL/'host-controls.inc.rs').read_bytes())
    base_tests=(BASE/'source/vm'/TESTS).read_bytes()
    append=(HERE/'host-controls.inc.rs').read_bytes()+(HERE/'floor-controls.inc.rs').read_bytes()
    target=HERE/'test-overlay'/TESTS
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(base_tests+append)
    assertions=(HERE/'floor-assertions.inc.rs').read_bytes()
    target=HERE/'compiler-overlay'/CONTROL
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(corrected.encode()+assertions)
    write('overlay-bindings.json',dict(schema=1,production=row(CONTROL,corrected.encode()),
        test_overlay=row(TESTS,base_tests+append),base_test=row(TESTS,base_tests),
        inherited_seven_test_append=row('host-controls.inc.rs',(HERE/'host-controls.inc.rs').read_bytes()),
        correction_test_append=row('floor-controls.inc.rs',(HERE/'floor-controls.inc.rs').read_bytes()),
        compiler_assertion_overlay=row(CONTROL,corrected.encode()+assertions),
        compiler_assertion_append=row('floor-assertions.inc.rs',assertions),
        scope='test and compile-only assertions are separately hashed, never production source inventory'))
    write('input-custody.json',dict(schema=1,original_seal_sha256=ORIGINAL_SEAL,original_members_verified=85,
        original_source_tree_sha256=ORIGINAL_TREE,base_seal_sha256=BASE_SEAL,base_source_tree_sha256=BASE_TREE,
        source_members_verified=144,root_release_sha256=RELEASE_SHA,owner_funding_sha256=OWNER_FUNDING_SHA,
        original_evidence_immutable=True,active_independent_bootstrap_descriptor_folders_read=False,
        global_process_inventory=False,canonical_or_git_mutations=False))
    print(json.dumps(dict(source_members=144,source_tree_sha256=sha(canonical(candidate)),correction='common +1436; selected-only extra removed')))

if __name__=='__main__': main()
