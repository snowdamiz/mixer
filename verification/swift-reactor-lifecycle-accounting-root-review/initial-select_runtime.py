"""Root accepts exact source/accounting evidence and selects scoped host tests."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
P = ROOT/'verification/swift-reactor-lifecycle-accounting'
R = ROOT/'verification/swift-reactor-lifecycle-accounting-independent-review'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
seals = {str(P.relative_to(ROOT))+'/seal.json':'02b53f531a4cb4852cc7e99104d13bb09e969f9d6b018c4d5d8fd6cd0d3dbbdd',
         str(R.relative_to(ROOT))+'/seal.json':'7a1d93a3990b50b29f51bd838b5fd8bc59514d817d0e4fa3b28dd5776614737c'}
counts = {}
for name,digest in seals.items():
    assert sha(ROOT/name)==digest
    packet=json.loads((ROOT/name).read_text())
    for path,expected in packet['files'].items():
        p=ROOT/path
        assert p.is_file() and not p.is_symlink() and sha(p)==expected,path
    counts[name]=len(packet['files'])
review=json.loads((R/'receipt.json').read_text())
assert review['independentReviewPassed'] and review['findings']==[]
assert (review['runtimeBodies'],review['disjointRolePositions'],review['exactSelectedFinitePositions'],review['individualExactParentFieldCTFEProofs'])==(268,21364,256,384)
assert review['pairedCompilerLayoutsAudited']==16 and review['expandedFrozenMethodsExact']==39
assert review['candidateClosure']=='0b36b551e2175aa713d698627493519249b6bfea023f05e13de730e6b06f977f'
argv=[sys.executable,'-B',str(P/'verify.py'),'--live']
run=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=120)
for stream in ['stdout','stderr']:
    (OUT/('runtime-selection-preflight.'+stream)).write_bytes(getattr(run,stream))
assert run.returncode==0,run.stderr.decode()
coverage=json.loads((P/'authored-coverage.json').read_text())
assert len(coverage['rows'])==23 and 'unsupported' in next(x for x in coverage['rows'] if x['id']=='SL12')['remaining']
selection={'schema':'mixer.swift-lifecycle.root-accounting-and-runtime-selection.1',
    'accountableReviewer':'/root','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'sourceRevision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    'seals':seals,'sealedFilesVerified':counts,'reviewReceiptSHA256':sha(R/'receipt.json'),
    'scriptSHA256':sha(Path(__file__)),'sourceCandidateClosure':review['candidateClosure'],'liveBaselineClosure':review['liveClosure'],
    'preflight':{'argv':argv,'exitCode':run.returncode,'stdoutSHA256':sha(OUT/'runtime-selection-preflight.stdout'),'stderrSHA256':sha(OUT/'runtime-selection-preflight.stderr'),
        'tool':{'path':str(Path(sys.executable).resolve()),'version':sys.version,'sha256':sha(Path(sys.executable).resolve())}},
    'sourceAndLogicalAccountingAccepted':True,'runtimeSelected':True,'runtimeAccepted':False,
    'ownership':['verification/swift-reactor-lifecycle-runtime/**','docs/swift-reactor-lifecycle-runtime.md'],
    'selectedRuntimeScope':[
        'Create an exact isolated copy of the132-file sealed candidate. Verify closure before each execution; preserve source and every assertion unchanged.',
        'Run23 exact authored swift_lifecycle_ tests in Swift-only and all-features Debug/Release, locked offline, test-threads=1. Require identity-level nonzero results, not only exit zero.',
        'After focused success, run existing Frozen39, full-library Swift/all-feature Debug/Release, default and span regressions using the previously qualified compiler/Node environment and explicit PATH; preserve command/test identities and actual source closure.',
        'Retain complete command outputs, tools, executable and artifact hashes, durations, failures, all-outcome bounded scratch/process cleanup. Do not rerun a failed unchanged test merely to obtain a pass.',
        'On failure diagnose against actual source/ownership contracts and report a precise repair proposal. No sealed source edits or live integration.',
        'Map each authored passing assertion to actual coverage; keep full original matrix and all remaining gaps. SL09 family assertions are not exact per-dimension qualification; SL12 unchanged-table reads are not guest table mutation.'
    ],
    'coverageLedgerSHA256':sha(P/'authored-coverage.json'),'originalMatrixSHA256':coverage['originalMatrixSHA256'],
    'originalLimits':{'State':134217728,'Combined':268435456,'tickets':86,'Frozen':2912},
    'full53MBTargetSelected':False,'nativeRuntimeSelected':False,'liveIntegrationSelected':False,'gaAccepted':False,
    'physicalPhones':'disconnected-deferred'}
destination=OUT/'runtime-selection.json'
assert not destination.exists(),'Selection already exists'
destination.write_text(json.dumps(selection,indent=2)+'\n')
print(json.dumps({'verifiedFiles':counts,'selectionSHA256':sha(destination),'runtimeSelected':True}))
