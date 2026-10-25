from pathlib import Path
import json,hashlib,shutil,difflib
H=Path(__file__).resolve().parent;R=H.parents[1];S=H/'owned-scratch'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def enc(x):return (json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
original=json.loads((H/'input-source-manifest.json').read_text())
assert all(sha(R/'vm'/n)==s for n,s in original.items())
D=H/'implementation-source';assert not D.exists()
for n in original:
    p=D/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(R/'vm'/n,p)
cache_path='src/experimental_swift_reactor/cache.rs'
test_path='src/experimental_swift_reactor/cache_tests.rs'
before=(D/cache_path).read_text()
grouped=(S/'grouped'/cache_path).read_text()
assert grouped.count('\n#[cfg(test)] mod diagnosis_layout {')==1
production=grouped.split('\n#[cfg(test)] mod diagnosis_layout {')[0]
assert production.endswith('\n')
patch=''.join(difflib.unified_diff(before.splitlines(True),production.splitlines(True),fromfile='a/'+cache_path,tofile='b/'+cache_path))
assert patch==(H/'grouped-prototype.patch').read_text()
(H/'implementation-production.patch').write_text(patch)
(D/cache_path).write_text(production)
production_manifest={n:sha(D/n) for n in original}
(H/'production-only-source-manifest.json').write_bytes(enc(production_manifest))
test_before=(D/test_path).read_text(); tests=test_before
assert tests.count('cache_header_bytes().unwrap() + expected')==1
tests=tests.replace('cache_header_bytes().unwrap() + expected','cache_header_bytes().unwrap() + expected - 192')
assert tests.count('assert_eq!(ledger.reservations.live_tickets, 74);')==1
tests=tests.replace('assert_eq!(ledger.reservations.live_tickets, 74);','assert_eq!(ledger.reservations.live_tickets, 73);')
assert tests.count('assert_eq!(c.usage(None).reservations.live_tickets, 74);')==2
tests=tests.replace('assert_eq!(c.usage(None).reservations.live_tickets, 74);','assert_eq!(c.usage(None).reservations.live_tickets, 73);')
a='''        header + patch_bytes - 1,
        header + patch_bytes,
        header + patch_bytes + 191,
        header + patch_bytes + 192,'''
assert tests.count(a)==1
tests=tests.replace(a,'''        header + patch_bytes - 1,
        header + patch_bytes,''')
assert tests.count('if ceiling == header + patch_bytes + 192 {')==1
tests=tests.replace('if ceiling == header + patch_bytes + 192 {','if ceiling == header + patch_bytes {')
# The executed final test source is exactly clean test source plus the saved controls.
assert (S/'grouped'/test_path).read_text()==tests+'\n'+(H/'controls.rs').read_text()
(D/test_path).write_text(tests)
(H/'implementation-accounting-expectations.patch').write_text(''.join(difflib.unified_diff(test_before.splitlines(True),tests.splitlines(True),fromfile='a/'+test_path,tofile='b/'+test_path)))
final_manifest={n:sha(D/n) for n in original}
(H/'implementation-source-manifest.json').write_bytes(enc(final_manifest))
changes=[n for n in original if original[n]!=final_manifest[n]];assert changes==[cache_path,test_path]
result={'inputClosureSHA256':sha(H/'input-source-manifest.json'),'productionOnlyClosureSHA256':sha(H/'production-only-source-manifest.json'),'productionAndAccountingClosureSHA256':sha(H/'implementation-source-manifest.json'),'members':132,'productionChangedFiles':[cache_path],'accountingExpectationChangedFiles':[test_path],'productionPatchSHA256':sha(H/'implementation-production.patch'),'accountingPatchSHA256':sha(H/'implementation-accounting-expectations.patch'),'noDiagnosisWiringOrControls':True,'cleanClosureExecuted':False,'executedPrototypeProductionByteIdentical':True,'executedPrototypeTestsEqualCleanPlusSavedControls':True,'selectionRequiredByRoot':True}
(H/'clean-handoff.json').write_bytes(enc(result))
print(json.dumps(result,indent=2))
