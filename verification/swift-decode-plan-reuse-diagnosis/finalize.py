from pathlib import Path
import datetime,hashlib,json,re,sys
H=Path(__file__).resolve().parent;R=H.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
assert not (H/'owned-scratch').exists()
selection=json.loads((H/'source-selection.json').read_text());base=json.loads((H/'baseline-manifest.json').read_text())
assert all(sha(R/'vm'/n)==v for n,v in base.items())
assert all(sha(H/'source'/n)==v for n,v in json.loads((H/'source-manifest.json').read_text()).items())
rows={}
for p in sorted((H/'commands').glob('*/receipt.json')):
 r=json.loads(p.read_text());label=p.parent.name;stdout=(p.parent/'stdout').read_text()
 m=re.search(r'test result: (\w+)\. (\d+) passed; (\d+) failed; (\d+) ignored;',stdout)
 test=any(x=='test' for x in r['argv'])
 count=int(m.group(2))+int(m.group(3)) if m else None
 qualified=r['passed'] and (not test or (m is not None and count>0 and int(m.group(3))==0))
 rows[label]={'exitCode':r['exitCode'],'driverPassed':r['passed'],'testCommand':test,'selectedTests':count,'passedTests':int(m.group(2)) if m else None,'failedTests':int(m.group(3)) if m else None,'qualifyingCommand':qualified,'zeroTestNonqualifying':test and count==0,'sourceManifestSHA256':r['sourceManifestSHA256'],'stdoutSHA256':r['stdoutSHA256'],'stderrSHA256':r['stderrSHA256'],'sourceUnchanged':r['sourceUnchanged'],'streamsClosed':all(r['streamEOF'].values()),'ownedGroupAbsent':r['ownedGroupAbsent']}
 assert rows[label]['streamsClosed'] and rows[label]['ownedGroupAbsent']
assert rows['qualified-finite-debug']['passedTests']==9 and rows['qualified-finite-release']['passedTests']==9
assert rows['qualified-frozen']['passedTests']==3
assert sum(rows[f'sealed-inherited-{n:02}']['passedTests'] for n in range(1,15))==12
zero=[n for n,r in rows.items() if r['zeroTestNonqualifying']];assert len(zero)==4
save(H/'command-audit.json',rows)
# Repair reference line numbers in read-only integration inventory only.
p=H/'pending-full-suite-updates.json';s=p.read_text().replace('"lines":[2316]','"lines":[2315]').replace('"lines":[704,743]','"lines":[704,744]').replace('"lines":[952,953,965,970,980,996,1003]','"lines":[952,953,965,969,980,982,996,1004]');p.write_text(s)
receipt={'completedScope':'finite isolated diagnosis and prototype only','liveAcceptance':False,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sourceSelection':selection,'diagnosticTestsDebug':9,'diagnosticTestsRelease':9,'actualInheritedTests':12,'frozenTestsEachSide':3,'zeroTestNonqualifyingCommands':zero,'fullSuiteRun':False,'exactPhaseHelperRun':False,'independentIRHelperRunViaEnclosingDecoderTest':True,'independentReview':'pending','rootAccountingReview':'pending','sourceCompilerMatrix':'pending','budgetLimitsChanged':False,'extraReservationTickets':0,'metadataSlots':512,'metadataPayloadBytes':28672,'fixedCacheBaselineBytes':89232,'fixedCachePrototypeBytes':118240,'constructorBaselineCredits':832,'constructorPrototypeCredits':4928,'tinyBodyRepeatRegressionPercent':2.1394831897749267,'largeBodyRepeatSavingsPercent':36.52996941662789,'coldSweepAdditionalCredits':1248,'cpuClaim':False,'fullTargetPrediction':False,'scopeBoundaries':{'Git':False,'network':False,'nativePlatform':False,'UI':False,'phones':False,'fullReactor':False,'InitializeInvoke':False,'liveTrackersChanged':False,'forbiddenLanesReadImportedExecuted':False},'fullReactorHistoricalFailureUnchanged':{'cacheWorkAttempted':64000001,'cacheWorkLimit':64000000,'function':3416,'offset':1077688,'instructions':15753076,'InitializePassed':True,'Corpus1Failed':True,'Corpus2Unrun':True,'resultSealSHA256':'91c71f2c6b6520e141b9226f7675a4578d0d37865aa1dfcfafc9e4dad31acb8c'},'failedCommandEvidence':[n for n,r in rows.items() if r['exitCode']!=0],'commandAuditSHA256':sha(H/'command-audit.json'),'comparisonSHA256':sha(H/'comparison.json'),'profileAdmissionSHA256':sha(H/'profile-admission.json'),'frozenComparisonSHA256':sha(H/'frozen-comparison.json'),'cleanupSHA256':sha(H/'cleanup.json'),'toolsSHA256':sha(H/'tools.json'),'pythonExecutable':sys.executable,'pythonSHA256':sha(Path(sys.executable)),'documentationSHA256':sha(R/'docs/swift-decode-plan-reuse-diagnosis.md'),'remainingOriginalFixtureUpdates':'pending-full-suite-updates.json','cleanupStatus':'owned scratch removed after absent group, holder and inode checks; three final executables retained losslessly'}
save(H/'receipt.json',receipt)
print(json.dumps({'sourceClosure':selection['prototype132FileClosure'],'commands':len(rows),'actualInheritedTests':12,'debugTests':9,'releaseTests':9,'zeroTestNonqualifying':zero,'failedEvidence':receipt['failedCommandEvidence'],'receiptSHA256':sha(H/'receipt.json')},indent=2))
