"""Read-only semantic audit and seal of this review's bounded evidence."""
from pathlib import Path
import hashlib,json
out=Path(__file__).resolve().parent
candidate=Path('/Users/andreyyurlov/.t3/worktrees/mixer/t3-efc61fb9')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
receipt=json.loads((out/'receipt.json').read_text())
audit=json.loads((out/'input-audit.json').read_text())
assert receipt['terminalCustody'] and receipt['sourceStable']
assert receipt['commands'][-1]['exit_code']==1
assert all(sha(candidate/name)==h for name,h in audit['sourceHashes'].items())
assert all(sha(out/'input'/name)==h for name,h in receipt['sources'].items())
original=(candidate/'cli/Tests/MixerBuildTests/StoreReconciliationTests.swift').read_bytes()
review=(out/'input/cli/Tests/MixerBuildTests/StoreReconciliationTests.swift').read_bytes()
assert review==original+(out/'review-tests.swift').read_bytes()
log=(out/'003-r2-review.stdout').read_text()
assert log.count('recorded an issue')==6 and '17 tests in 2 suites failed' in log
end=log.index('Suite StoreR2IndependentReviewTests failed')
saturation=log.index('◇ Test credentialHistorySaturationPreservesSafeProgressAndClosesAdmission() started.')
assert end<saturation
assert '✔ Test credentialHistorySaturationPreservesSafeProgressAndClosesAdmission() passed' in log
for name in ['scratch','temporary']:assert not (out/name).exists()
summary={'verdict':'REQUEST CHANGES','blockers':[{'severity':'P2','path':'cli/Sources/MixerBuild/StoreReconciliation.swift','lines':[123,211,212,213,214,215,216,246],'finding':'The seventeenth distinct <=256-byte credential permanently blocks safe observation admission.'}], 'candidateBase':audit['base'],'candidateBaseTree':audit['baseTree'],'candidatePatchSHA256':audit['patchSHA256'],'candidateSourceDigest':audit['sourceDigest'],'compiledSourceDigest':receipt['sourceDigest'],'commandsTerminalCustody':True,'compileAttempts':1,'testOutcome':{'totalGroups':17,'groupsReportedPassed':15,'groupsReportedFailed':2,'issues':6,'classification':'Shared scripted fixture raced between two internally serialized suites; new successful-JWT-rotation probe inconclusive, not a product finding.','candidateGroupsAfterOverlapPassed':12,'originalEightPassedAfterOverlap':True,'saturationCounterexamplePassedAfterOverlap':True,'crossProcessAndMigrationQualification':'not promoted because fixture overlap existed'},'jwtLengthControl':audit['jwtLengthControl'],'candidateAll139SourcesUnchanged':True,'originalEightAndHelpersUnchanged':audit['files']['originalEightAndHelpersUnchanged'],'scratchRemovedWithTerminalCustody':True,'officialTokenDocs':json.loads((out/'official-docs-receipt.json').read_text()),'limitations':['No live ASC','No native or devices','No power-loss or filesystem-fault campaign','No fresh independent success-only rotation reproduction','Root 103 owning-input rebind and six canonical consumers pending','No full W13, Play, D6, FieldLog or GA qualification']}
save(out/'review-receipt.json',summary)
manifest={str(p.relative_to(out)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(out.rglob('*')) if p.is_file() and p.name not in ['artifact-manifest.json','hash-seal.json']}
save(out/'artifact-manifest.json',manifest)
seal={'algorithm':'SHA-256','artifactCount':len(manifest),'artifactBytes':sum(v['bytes'] for v in manifest.values()),'manifestSHA256':sha(out/'artifact-manifest.json'),'reportSHA256':sha(out/'REPORT.md'),'reviewReceiptSHA256':sha(out/'review-receipt.json'),'candidatePatchSHA256':audit['patchSHA256'],'testStdoutSHA256':sha(out/'003-r2-review.stdout'),'testStderrSHA256':sha(out/'003-r2-review.stderr')}
save(out/'hash-seal.json',seal)
print(json.dumps(seal,indent=2))
