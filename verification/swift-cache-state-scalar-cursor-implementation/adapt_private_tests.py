#!/usr/bin/env python3
"""Apply the root-authorized two-method private representation amendment only."""
from pathlib import Path
import json,hashlib,difflib,datetime
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=ROOT/'source/tests/cache_state_tests.rs';old=p.read_text();baseline=ROOT/'predecessor/correction-3/source/tests/cache_state_tests.rs';assert old==baseline.read_text()
archive=ROOT/'evidence/frozen-attempt1';archive.mkdir()
for f in list((ROOT/'evidence').iterdir()):
 if f==archive:continue
 if f.name.startswith(('rust-version.','compile-','tests-','regression-','frozen-regression-','source-before.','cleanup.')) or f.name=='public-cases':f.rename(archive/f.name)
newmax='''fn private_merge_maximum_timestamp_and_all64_slots() {
    // The accepted merge input is timestamp64 plus a physical-slot mask.
    // This oracle independently sorts eligible physical slots by (time, slot).
    let mut masks = vec![0u64, u64::MAX, 0xaaaa_aaaa_aaaa_aaaa, 0x5555_5555_5555_5555];
    for slot in 0..64 { masks.push(1u64 << slot); masks.push(!(1u64 << slot)); }
    let mut random = 0x1234_5678_9abc_def0u64;
    for _ in 0..128 {
        random ^= random << 13; random ^= random >> 7; random ^= random << 17;
        masks.push(random);
    }
    let mut checked = 0;
    for eligibility in masks {
        for pattern in 0..5 {
            let mut c = [0xa7; 2048];
            for slot in 0..64u64 {
                let timestamp = match pattern {
                    0 => u64::MAX,
                    1 => 63 - slot,
                    2 => slot.reverse_bits() >> 58,
                    3 => if slot % 3 == 0 { u64::MAX } else { slot % 5 },
                    _ => slot.wrapping_mul(0x9e37_79b9_7f4a_7c15),
                };
                st(&mut c, slot as usize * 8, timestamp);
            }
            st(&mut c, 640, eligibility);
            let before = c;
            let mut expected: Vec<_> = (0..64usize).filter(|s| eligibility & (1u64 << s) != 0).collect();
            expected.sort_by_key(|s| (ld(&c, *s * 8), *s));
            merge(&mut c);
            for (position, slot) in expected.iter().enumerate() {
                assert_eq!(c[512 + position], *slot as u8, "mask={eligibility:x} pattern={pattern} position={position}");
            }
            for position in expected.len()..64 { assert_eq!(c[512 + position], 255); }
            assert_eq!(&c[..512], &before[..512]);
            assert_eq!(&c[640..], &before[640..]);
            checked += 1;
        }
    }
    println!("SELECTED_MERGE_ORACLE_CASES={checked} REAL_MAX_TIMESTAMP_AND_255_ABSENCE_EXHAUSTED256_PRIVATE_ONLY");
}'''
newcounter='''fn private_actual_merge_exact_worst_case_counts() {
    for mode in 0..4 {
        let mut c = [0; 2048];
        for i in 0..64u64 {
            let key = match mode {
                0 => i.reverse_bits() >> 58,
                1 => 0,
                2 => 63 - i,
                _ => ABSENT,
            };
            st(&mut c, i as usize * 8, key);
        }
        st(&mut c, 640, u64::MAX);
        SORT_COMPARISONS.store(0, Ordering::Relaxed);
        SORT_MOVES.store(0, Ordering::Relaxed);
        merge(&mut c);
        let comparisons = SORT_COMPARISONS.load(Ordering::Relaxed);
        let moves = SORT_MOVES.load(Ordering::Relaxed);
        // Counters cover only five later passes. The 32 seed comparisons and
        // 64 seed outputs are uninstrumented and receive no full-cost claim.
        assert!(comparisons <= 289);
        assert_eq!(moves, 320);
        if mode == 0 { assert_eq!(comparisons, 289); }
        println!("actual_merge_later_five_passes mode={mode} comparisons={comparisons} moves={moves} SEED_COUNTER_CREDIT=0");
    }
}'''
def replace_function(text,name,new):
 start=text.index('fn '+name+'() {');depth=0;end=None
 for i in range(text.index('{',start),len(text)):
  if text[i]=='{':depth+=1
  elif text[i]=='}':
   depth-=1
   if depth==0:end=i+1;break
 assert end;return text[:start]+new+text[end:]
new=replace_function(old,'private_merge_maximum_timestamp_and_all64_slots',newmax)
new=replace_function(new,'private_actual_merge_exact_worst_case_counts',newcounter)
p.write_text(new)
(ROOT/'proofs/private-test-amendment.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='frozen-C3/cache_state_tests.rs',tofile='selected-cursor/cache_state_tests.rs')))
amend=REPO/'verification/swift-semantic-adapter-root-review/scalar-cursor-test-amendment.json'
(ROOT/'proofs/private-test-amendment.json').write_text(json.dumps({'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'root_authorization':{'path':str(amend.relative_to(REPO)),'sha256':sha(amend)},'old_sha256':sha(baseline),'amended_sha256':sha(p),'only_methods_changed':['private_merge_maximum_timestamp_and_all64_slots','private_actual_merge_exact_worst_case_counts'],'frozen_first_runs':'evidence/frozen-attempt1','old_failures_retained':True,'all_other_tests_vectors_expectations_changed':False,'selected_library_sha256':sha(ROOT/'source/library/cache_state.rs')},indent=2)+'\n')
print('Only two private methods adapted; first attempt archived; selected source unchanged',sha(ROOT/'source/library/cache_state.rs'))
