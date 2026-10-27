"""Static custody assertions supplement compiler tests; grant no authority."""
from pathlib import Path
import hashlib,json,re
ROOT=Path(__file__).resolve().parent
BEFORE=ROOT.parent/'swift-guarded-snapshot-encoder-implementation/source/vm'
AFTER=ROOT/'source/vm'
def sha(data):return hashlib.sha256(data).hexdigest()
def declaration(text,start):
    at=text.index(start);return text[at:text.index('\n}',at)+2]
def source(relative):return (BEFORE/relative).read_text(),(AFTER/relative).read_text()
results=[]
def check(name,ok,detail):
    assert ok,(name,detail)
    results.append({'name':name,'passed':ok,'detail':detail})
initial='src/experimental_swift_reactor/cache/initial_profile_v1.rs'
before,after=source(initial)
for symbol in ['enum InitialProfileConstructionOutcomeV1 {','pub(crate) struct InitialProfileBorrowV1']:
    a=declaration(before,symbol);b=declaration(after,symbol)
    check(symbol,a==b,{'before_sha256':sha(a.encode()),'after_sha256':sha(b.encode())})
a=before[before.index('fn write_initial_profile_rows_v1'):before.index('fn compare_budget_v1')]
b=after[after.index('fn write_initial_profile_rows_v1'):after.index('fn compare_budget_v1')]
check('original-row-function-identical',a==b,sha(a.encode()))
for relative in [initial+'/selected.rs',initial+'/header.rs']:
    # Member path is initial_profile_v1/<member>, not .rs/<member>.
    relative=relative.replace('initial_profile_v1.rs/','initial_profile_v1/')
    a=(BEFORE/relative).read_bytes();b=(AFTER/relative).read_bytes()
    check(relative,a==b,sha(a))
before,after=source('src/experimental_swift_reactor/control.rs')
a=declaration(before,'pub(crate) struct RuntimeControl {');b=declaration(after,'pub(crate) struct RuntimeControl {')
check('RuntimeControl-fields-identical',a==b,sha(a.encode()))
a=(BEFORE/'src/experimental/swift.rs').read_bytes();b=(AFTER/'src/experimental/swift.rs').read_bytes()
seam=b'\n'+(ROOT/'implementation/encoder_measurement.rs').read_bytes()
assert b.count(seam)==1
recovered=b.replace(seam,b'',1)
check('frozen-encoder-behavior-bytes-recovered-exactly',recovered.startswith(a),{'frozen_bytes':len(a),'frozen_sha256':sha(a),'measurement_seam_sha256':sha(seam),'appended_only':'root-released private const/static measurement seam plus fixed actual Buffer count bridge outside frozen encoder'})
all_source='\n'.join(p.read_text() for p in sorted(AFTER.rglob('*.rs')))
guard_literals=re.findall(r'let initial\s*=\s*InitialProfileBorrowV1\s*\{',all_source)
check('one-original-guard-literal',len(guard_literals)==1,len(guard_literals))
loader=(AFTER/'src/experimental_swift_reactor/retained_profile_loader_v1.rs').read_text()
check('one-private-authentic-selected-capability-literal',loader.count('let selected_body=SelectedSnapshotBodyV1(')==1,1)
check('one-authentic-selected-body-literal',loader.count('AdoptionBodyV1 { proof,selected:Some(provenance) }')==1,1)
check('no-new-engine-source-members',len([p for p in AFTER.rglob('*') if p.is_file()])==144,144)
check('work-audit-explicitly-fails-closed','Err(AError::WorkAuditPending)' in all_source,'no operational debit/floor selected')
(ROOT/'source-truth.json').write_text(json.dumps({'schema':1,'checks':results,'scope':'static source/custody controls only; no runtime or operational authorization'},indent=2)+'\n')
print(json.dumps({'passed':len(results),'source_members':144}))
