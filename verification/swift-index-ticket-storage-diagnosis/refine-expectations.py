from pathlib import Path
import json,hashlib,difflib
H=Path(__file__).resolve().parent; S=H/'owned-scratch/grouped'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def enc(x):return (json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
p=S/'src/experimental_swift_reactor/cache_tests.rs';before=p.read_text();t=before
a='assert_eq!(ledger.reservations.live_tickets, 74);';assert t.count(a)==1
t=t.replace(a,'assert_eq!(ledger.reservations.live_tickets, 73);')
a='''        header + patch_bytes - 1,
        header + patch_bytes,
        header + patch_bytes + 191,
        header + patch_bytes + 192,'''
b='''        header + patch_bytes - 1,
        header + patch_bytes,'''
assert t.count(a)==1;t=t.replace(a,b)
a='if ceiling == header + patch_bytes + 192 {';assert t.count(a)==1
t=t.replace(a,'if ceiling == header + patch_bytes {')
p.write_text(t)
(H/'grouped-test-expectations.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),t.splitlines(True),fromfile='before/cache_tests.rs',tofile='after/cache_tests.rs')))
names=json.loads((H/'input-source-manifest.json').read_text())
(H/'grouped-final-source-manifest.json').write_bytes(enc({n:sha(S/n) for n in names}))
(H/'expectation-correction.json').write_bytes(enc({'onlyCopiedTestExpectationsChanged':True,'beforeSHA256':hashlib.sha256(before.encode()).hexdigest(),'afterSHA256':sha(p),'preservedFailingCommand':'commands/grouped-cache','productionPrototypeChanged':False,'reason':'Three test expectations encoded former separate index-payload ticket/bytes; contract now groups payload under header.'}))
print('Copied test expectations now express grouped header ownership; failure receipt retained.')
