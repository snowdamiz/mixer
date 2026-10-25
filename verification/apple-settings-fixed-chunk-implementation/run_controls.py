"""Run exact host-only test modules with EOF/process ownership receipts."""
import hashlib,json,pathlib,subprocess,sys,time,unittest
B=pathlib.Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()

def main():
 sys.dont_write_bytecode=True;sys.path.insert(0,str(B))
 import fixtures,test_fixed_chunk,test_retained_proof,test_retained_persistence
 modules=[test_fixed_chunk,test_retained_proof,test_retained_persistence]
 suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(m) for m in modules)
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 report=dict(schema=1,syntheticHostOnly=True,nativeExecuted=False,methodsRun=result.testsRun,passed=result.wasSuccessful(),errors=len(result.errors),failures=len(result.failures),fixedFormatControls=test_fixed_chunk.RESULTS,persistenceControls=test_retained_persistence.RESULTS,excludedHistoricalControls=['original network/listener V9 method','unrelated historical V6 source replay method','previous Swift resolver output fixture method'],directAdapterStatusIsHTTP=False,framingCapabilityNetworkAndNativeUnverified=True)
 (B/'controls.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
 raise SystemExit(0 if result.wasSuccessful() else 1)
if __name__=='__main__':main()
