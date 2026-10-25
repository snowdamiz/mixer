#!/usr/bin/env python3
"""Apply measured fixture corrections only, preserving every original assertion kind."""
from pathlib import Path
import difflib, hashlib, json, subprocess
H=Path(__file__).resolve().parent
S=H/'source/src/experimental_swift_reactor'
rows=[]
def replace(file, old, new, count=1):
    p=S/file;s=p.read_text();assert s.count(old)==count,(file,old,s.count(old),count)
    p.write_text(s.replace(old,new));rows.append({'file':file,'before':old,'after':new,'occurrences':count})
replace('cache_tests.rs','assert_eq!(alloc.allocations, 4);','assert_eq!(alloc.allocations, 5);')
replace('cache_tests.rs','assert_eq!(s.allocations, 4);','assert_eq!(s.allocations, 5);')
replace('cache_tests.rs','''        + 512 * size_of::<decode::Patch>()
        + 192;''','''        + 512 * size_of::<decode::Patch>()
        + 192
        + 28_672; // Measured 512 optional scan-plan cells, grouped under the header.''')
replace('cache_tests.rs','cache_header_bytes().unwrap() + expected - 192','cache_header_bytes().unwrap() + expected - 192 - 28_672')
replace('cache_tests.rs','assert_eq!(n, 4);','assert_eq!(n, 5);')
replace('cache_tests.rs','for ordinal in 0..4 {','for ordinal in 0..5 {')
replace('cache_tests.rs','assert_eq!(stats.attempts, 2);','assert_eq!(stats.attempts, 3);')
replace('cache_tests.rs','assert_eq!(c.usage(None).cache_work, 832);','assert_eq!(c.usage(None).cache_work, 4_928);')
replace('cache_tests.rs',r'\"constructorWork\":832',r'\"constructorWork\":4928')
replace('execution_tests.rs','assert_eq!(allocations.allocations, 14);','assert_eq!(allocations.allocations, 15);')
replace('execution_tests.rs','assert_eq!(cleanup.deallocations, 24); // 14 payloads + 10 adopted/foundation backing allocations.','assert_eq!(cleanup.deallocations, 25); // 15 payloads + 10 adopted/foundation backing allocations.')
replace('execution_tests.rs','for ordinal in 0..13 {','for ordinal in 0..15 {')
replace('execution_tests.rs','assert_eq!(stats.attempts, 9 + ordinal);','assert_eq!(stats.attempts, 10 + ordinal);')
replace('execution_tests.rs','assert_eq!(stats.allocations, 11);','assert_eq!(stats.allocations, 12);')
replace('execution_tests.rs','assert_eq!(stats.allocations, 8); // Cache and WASI only; no State allocation.','assert_eq!(stats.allocations, 9); // Cache and WASI only; no State allocation.')
replace('execution_tests.rs','''            SwiftRunFailureKind::CombinedExhausted,
            11,''','''            SwiftRunFailureKind::CombinedExhausted,
            12,''')
replace('execution_tests.rs','assert_eq!(stats.allocations, 14);','assert_eq!(stats.allocations, 15);')
replace('execution_tests.rs','assert_eq!(stats.deallocations, 24);','assert_eq!(stats.deallocations, 25);')
replace('lifecycle_tests.rs','// Constructor writes 29 slots, 64 pin records, 512 patch entries and 192 index cells.','// Constructor writes 29 slots, 64 pin records, 512 patches, 192 index cells\n    // and eight charged semantic cells for each of 512 scan-plan entries.')
replace('lifecycle_tests.rs','assert_eq!(start.cache_work, 29 + 64 + 512 + 192);','assert_eq!(start.cache_work, 29 + 64 + 512 + 192 + 512 * 8);')
replace('lifecycle_tests.rs','// Cold cost = 108 + pin records + 2*encoded body bytes + 3*instructions.','// Cold cost adds 13 actual probe/publication credits to the original\n    // 108 + pin records + 2*encoded body bytes + 3*instructions.')
replace('lifecycle_tests.rs','108 + 1 + 2 * 14 + 3 * 6','108 + 1 + 2 * 14 + 3 * 6 + 13')
replace('lifecycle_tests.rs','assert_eq!(initialized.cache_work, 952);','assert_eq!(initialized.cache_work, 5_061);')
replace('lifecycle_tests.rs','(108 + 1 + 2 * 7 + 3 * 3) + (108 + 2 + 2 * 19 + 3 * 9)','(108 + 1 + 2 * 7 + 3 * 3 + 13) + (108 + 2 + 2 * 19 + 3 * 9 + 13)')
replace('lifecycle_tests.rs','assert_eq!(first.cache_work, 1259);','assert_eq!(first.cache_work, 5_394);')
replace('lifecycle_tests.rs','assert_eq!(second.cache_work, 1276);','assert_eq!(second.cache_work, 5_411);')
replace('lifecycle_tests.rs','// Constructor797; cold no-op init B2/I1:108+1+4+3=116.','// Constructor 4,893; cold no-op init B2/I1:108+1+4+3+13=129.\n    // Keep the synthetic limit exactly at completed initialization so the\n    // later invocation still fails without resetting cumulative work.')
replace('lifecycle_tests.rs','cache_work: 913,','cache_work: 5_022,')
replace('lifecycle_tests.rs','assert_eq!(observed(&o).cache_work, 913);','assert_eq!(observed(&o).cache_work, 5_022);')
replace('lifecycle_tests.rs','assert_eq!(f.at_failure.cache_work, 913);','assert_eq!(f.at_failure.cache_work, 5_022);')
# Format only the three added observation appendices. Keep legacy source bytes.
F=H/'fixtures';F.mkdir(exist_ok=True)
format_records=[]
for file in ('cache_tests.rs','execution_tests.rs','lifecycle_tests.rs'):
    p=S/file;s=p.read_text();i=s.index('\n#[test]\nfn full_regression_observe_')
    original=s[i+1:];q=F/file;q.write_text(original)
    cmd=['/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin/rustfmt','--edition','2021',str(q)]
    run=subprocess.run(cmd,capture_output=True,text=True,timeout=30,check=True)
    format_records.append({'argv':cmd,'exitCode':run.returncode,'stdout':run.stdout,'stderr':run.stderr,'beforeSHA256':hashlib.sha256(original.encode()).hexdigest(),'afterSHA256':hashlib.sha256(q.read_bytes()).hexdigest()})
    p.write_text(s[:i+1]+q.read_text())
(H/'fixture-migration.json').write_text(json.dumps({'scope':'test-only measured corrections; all production bytes preserved','measurementCommand':'fixture-observations','secondaryFailureCommand':'admission-next-original-failure','replacements':rows,'firstAdmissionReplacementAlreadyObserved':{'before':8,'after':9,'command':'original-swift-debug'},'observationFormatting':format_records},indent=2,sort_keys=True)+'\n')
patch=''
P=H.parent/'swift-decode-plan-reuse-diagnosis/source'
for file in ('cache_tests.rs','execution_tests.rs','lifecycle_tests.rs'):
    n='src/experimental_swift_reactor/'+file
    patch+=''.join(difflib.unified_diff((P/n).read_text().splitlines(True),(H/'source'/n).read_text().splitlines(True),fromfile='producer/'+n,tofile='regression/'+n))
(H/'fixture.patch').write_text(patch)
print('Applied measured fixture corrections; expanded integrated fault enumeration to all15 actual ordinals.')
