"""Read-only independent packet rehash and reconstruction; no compiler/runtime."""
from pathlib import Path
import hashlib, json, sys
sys.dont_write_bytecode=True
import independent as I
HERE=Path(__file__).resolve().parent
def rows():
    result=[]
    for path in sorted(HERE.rglob('*')):
        if path.is_dir():continue
        if path==HERE/'seal.json':continue
        assert not path.is_symlink() and '__pycache__' not in path.parts
        result.append(I.record(path,path.relative_to(HERE).as_posix()))
    return result
def check(*,sealed=True):
    if sealed:
        seal=I.load(HERE/'seal.json');actual=rows()
        assert seal['members']==actual and seal['member_count']==len(actual) and seal['total_bytes']==sum(r['bytes'] for r in actual)
        assert seal['member_table_sha256']==I.digest(I.canon(actual))
    before=I.closure_snapshot();report=I.reconstruct()
    I.validate_documents(report,I.load(I.P/'candidate.json'),I.load(I.P/'phase-roster.json'),I.load(I.P/'required-input-contracts.json'))
    assert I.canon(report)==I.canon(I.load(HERE/'reconstruction.json'))
    custody=I.load(HERE/'input-custody.json');assert custody['unchanged'] and before==custody['before']==custody['after']==I.closure_snapshot()
    latest=I.load(HERE/'review.json')['final_host_receipt'];path=HERE/latest['path'];assert I.digest(path.read_bytes())==latest['sha256']
    receipt=I.load(path);assert receipt['success'] and receipt['scripts_unchanged'] and len(receipt['commands'])==3
    for name,row in receipt['scripts'].items():
        assert (HERE/name).stat().st_size==row['bytes'] and I.digest((HERE/name).read_bytes())==row['sha256']
        assert (path.parent/('snapshot-'+name)).read_bytes()==(HERE/name).read_bytes()
    for cmd in receipt['commands']:
        assert cmd['exit_code']==0 and not cmd['timed_out'] and cmd['child_reaped'] and cmd['owned_group_absent'] and cmd['elapsed_seconds']<55
        for field in ('stdout','stderr'):
            row=cmd[field];data=(HERE/row['path']).read_bytes();assert len(data)==row['bytes'] and I.digest(data)==row['sha256']
    controls=I.load(HERE/'controls.json');assert controls['methods']==20 and controls['adverse_cases']==len(controls['controls']) and controls['adverse_cases']>=1000
    review=I.load(HERE/'review.json');assert review['accepted_scope']=='conditional source-work and logical typed-slot interface only' and not review['operational_grant_or_OTA_or_GA']
    if sealed:assert rows()==actual # The replay itself must not write evidence.
    return {'success':True,'scope':'read-only custody/source/MIR/LLVM/arithmetic; no compiler/product/native runtime','roles':report['roles'],'operations':report['operations'],'logical_P0_addition':report['P0_addition'],'source_work':report['work'],'host_methods':controls['methods'],'adverse_cases':controls['adverse_cases'],'new_compiler_or_runtime_invocations':0}
if __name__=='__main__':print(json.dumps(check(),sort_keys=True))
