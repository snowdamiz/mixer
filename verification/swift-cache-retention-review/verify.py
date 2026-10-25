#!/usr/bin/env python3
"""Read-only independent review integrity checker; does not select execution."""
from pathlib import Path,PurePosixPath
import hashlib,json,subprocess
H=Path(__file__).resolve().parent;ROOT=H.parent.parent;P=ROOT/'verification/swift-cache-retention-candidate'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
seal=json.loads((H/'seal.json').read_text());assert sha(H/'seal.json')==(H/'seal.sha256').read_text().strip()
for name,digest in seal['members'].items():
    n=PurePosixPath(name);assert not n.is_absolute() and '..' not in n.parts
    assert sha(H/name)==digest,name
for name,digest in seal['externalMembers'].items():assert sha(ROOT/name)==digest,name
summary=json.loads((H/'result-summary.json').read_text())
assert summary['schema']==1 and summary['status']=='finite-correctness-accounting-prerequisite-accepted'
assert summary['finitePrerequisiteAccepted'] and not summary['blockingFindings']
assert summary['candidateSealSHA256']==sha(P/'seal.json')=='6507e85f869d0f1a052b9e8e5356ac07910c67813f87b309fa6a5b348e803c13'
assert summary['candidateManifestSHA256']==sha(P/'candidate-manifest.json')=='d840933a706131e64c50b74812af771ead622912d57575336770434387f5b99d'
assert summary['baselineClosureSHA256']==sha(P/'baseline-manifest.json')=='16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd'
assert not summary['fullDiagnosticSelected'] and not summary['liveIntegrationAccepted'] and not summary['gaAccepted']
for name,count in [('independent-swift-corrected',5),('independent-generic-corrected',1),('independent-ties',1)]:
    folder=H/'commands'/name;r=json.loads((folder/'receipt.json').read_text())
    assert r['exitCode']==0 and f'test result: ok. {count} passed; 0 failed; 0 ignored' in (folder/'stdout').read_text()
    for field,file in [('sourceManifestSHA256','source-manifest.json'),('stdoutSHA256','stdout'),('stderrSHA256','stderr')]:assert r[field]==sha(folder/file)
    manifest=json.loads((folder/'source-manifest.json').read_text());original=json.loads((P/'candidate-manifest.json').read_text())
    changed=[n for n in original if original[n]!=manifest[n]]
    expected=['src/experimental_swift_reactor/cache_tests.rs']if name=='independent-ties'else['src/experimental/cache/tests.rs','src/experimental_swift_reactor/cache_tests.rs']
    assert changed==expected
for name in ['cleanup.json','cleanup-ties.json']:
    d=json.loads((H/name).read_text());assert d['ownedProcessesAbsent'] and d['holdersAbsent'] and d['deviceInodeAndMutationChecksPassed'] and d['signalsSent']==0
producer=subprocess.run(['python3',str(P/'verify.py')],cwd=ROOT,capture_output=True,text=True,check=True)
print(json.dumps({'verified':True,'sealedReviewMembers':len(seal['members']),'externalReportMembers':len(seal['externalMembers']),'independentMethodsPassed':7,'candidateBindingAccepted':True,'finitePrerequisiteAccepted':True,'producerVerification':json.loads(producer.stdout),'fullDiagnosticSelected':False,'liveIntegrationAccepted':False,'gaAccepted':False}))
