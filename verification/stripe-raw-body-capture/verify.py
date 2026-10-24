"""Read-only check of all sealed producer files, archive members and current pins."""
import hashlib, json, tarfile
from pathlib import Path, PurePosixPath
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def archive_inputs(archive,expected):
    observed={}
    with tarfile.open(archive,'r:gz') as tar:
        for member in tar.getmembers():
            path=PurePosixPath(member.name)
            assert member.isfile() and not path.is_absolute() and '..' not in path.parts
            assert member.name not in observed
            observed[member.name]=hashlib.sha256(tar.extractfile(member).read()).hexdigest()
    assert observed==expected,archive
    return observed

def main():
    top=json.loads((HERE/'seal.json').read_text())
    actual={str(p.relative_to(REPO)) for p in HERE.rglob('*') if p.is_file() and p!=HERE/'seal.json'}|{'docs/stripe-raw-body-capture.md'}
    assert set(top)==actual,'unsealed or missing producer files'
    for name,expected in top.items():
        p=REPO/name
        assert p.stat().st_size==expected['bytes'] and sha(p)==expected['sha256'],name
    accepted=json.loads((HERE/'acceptance.json').read_text())
    latest=HERE/accepted['authoritativeRun']
    for run in sorted(HERE.glob('run-*')):
        seal=json.loads((run/'seal.json').read_text())
        actual={str(p.relative_to(run)) for p in run.rglob('*') if p.is_file() and p.name!='seal.json'}
        assert set(seal)==actual,run
        for name,expected in seal.items():
            assert (run/name).stat().st_size==expected['bytes'] and sha(run/name)==expected['sha256'],(run,name)
        archive_inputs(run/'candidate-source-closure.tar.gz',json.loads((run/'source-inputs.json').read_text()))
        archive_inputs(run/'dependency-source-closure.tar.gz',json.loads((run/'dependency-source-inputs.json').read_text()))
        assert json.loads((run/'receipt.json').read_text())['cleanup']['scratchRemoved']
    pins=json.loads((HERE/'pinned-dependency-identity.json').read_text())
    assert sha(REPO/'hosted/mix.lock')==pins['lockSHA256']
    for name,h in pins['source'].items(): assert sha(REPO/'hosted/deps'/name)==h,name
    for name,h in pins['beams'].items(): assert sha(REPO/'hosted/_build/test/lib'/name)==h,name
    for name,identity in pins['toolchain'].items(): assert sha(Path(name))==identity['sha256'],name
    inputs=json.loads((latest/'source-inputs.json').read_text())
    for p in list((HERE/'candidate').rglob('*'))+list((HERE/'tests').rglob('*'))+[HERE/'run.py',HERE/'pinned-dependency-identity.json']:
        if p.is_file(): assert inputs[str(p.relative_to(HERE))]==sha(p),p
    upstream=json.loads((latest/'accepted-hosted-inputs.json').read_text())
    assert len(upstream['sourceInputs'])==69
    for name,h in upstream['sourceInputs'].items(): assert sha(REPO/name)==h,name
    for phase in ['component','wire']:
        policy=json.loads((latest/phase/'production-policy.json').read_text())
        assert policy['testClockAtomPresent'] is False and policy['productionClockSpoofIgnored'] is True
    matrix=json.loads((HERE/'matrix.json').read_text())
    frozen=json.loads((REPO/'verification/stripe-raw-body-contract/test-matrix.json').read_text())
    assert [(r['id'],r['cases']) for r in matrix['rows']]==[(r['id'],r['cases']) for r in frozen['rows']]
    assert len(matrix['rows'])==13 and matrix['allRowsPassed'] is False
    assert accepted['publicAdmissionAccepted'] is False and accepted['g23Accepted'] is False
    print(f'PASS: {len(top)} sealed producer files, all run archives/nested receipts/current pins; 13 original matrix rows; no public admission claim')
if __name__=='__main__': main()
