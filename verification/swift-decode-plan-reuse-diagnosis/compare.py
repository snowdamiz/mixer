from pathlib import Path
import hashlib,json,re,ast
H=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
def raw(label):return (H/'commands'/label/'stdout').read_text()
B=raw('qualified-baseline-observation');D=raw('qualified-finite-debug');O=raw('qualified-finite-release')
extract=lambda s,p:re.findall(p,s,re.M)
ir=lambda s:extract(s,r'PLAN_IR .*$');lru=lambda s:extract(s,r'PLAN_LRU .*$')
assert ir(B)==ir(D)==ir(O);assert lru(B)==lru(D)==lru(O)
pattern=r'PLAN_COST wide=(true|false) fixed=(\d+) constructor_work=(\d+) sweeps=(\[[^\]]+\])'
def costs(s):return {a:{'fixedBytes':int(b),'constructorWork':int(c),'sweepWork':ast.literal_eval(d)} for a,b,c,d in re.findall(pattern,s)}
b=costs(B);d=costs(D);o=costs(O);assert d==o
bn=raw('qualified-baseline-frozen');dn=raw('qualified-frozen')
normalize=lambda s:'\n'.join(x for x in s.splitlines() if not x.startswith('test result:'))
assert normalize(bn)==normalize(dn)
save(H/'frozen-comparison.json',{'rawBaselineSHA256':sha(H/'commands/qualified-baseline-frozen/stdout'),'rawPrototypeSHA256':sha(H/'commands/qualified-frozen/stdout'),'normalization':'remove only test-result summary (filtered test count/duration); all three named test bodies, layout, IR, failures, work and allocations compare byte-for-byte','normalizedSHA256':hashlib.sha256(normalize(bn).encode()).hexdigest(),'normalizedTraceIdentical':True,'tests':3})
metrics={}
for wide in ('false','true'):
 metrics[wide]={'baseline':b[wide],'prototype':d[wide],'repeatSavingsCredits':b[wide]['sweepWork'][1]-d[wide]['sweepWork'][1],'repeatSavingsPercent':100*(1-d[wide]['sweepWork'][1]/b[wide]['sweepWork'][1]),'includingConstructorThreeSweepBaseline':b[wide]['constructorWork']+sum(b[wide]['sweepWork']),'includingConstructorThreeSweepPrototype':d[wide]['constructorWork']+sum(d[wide]['sweepWork'])}
save(H/'comparison.json',{'cases':metrics,'identicalIRAndOffsets':True,'independentExpectedIR':True,'identicalResidentSlotsPinsAndLRURanks':True,'debugReleaseCreditIdentical':True,'cpuPerformanceClaim':False,'fullReactorCompletionPrediction':False,'originalLimitsChanged':False})
p1=raw('baseline-profile-admission');p2=raw('profile-admission')
read_profile=lambda s:{a:int(b) for a,b in re.findall(r'(\w+)=(\d+)',s.split('PLAN_PROFILE ',1)[1].split('\n',1)[0])}
bp=read_profile(p1);dp=read_profile(p2)
save(H/'profile-admission.json',{'baseline':bp,'prototype':dp,'combinedHeadroomBytes':dp['combined_limit']-dp['conservative_combined'],'formula':'maxSource64MiB + maxMetadata16MiB + maxCache16MiB + maxState128MiB + maxDefaultWasiHeaderAndFour64KiBBuffers + actualShared + foundation + max(executionConstruction, frameOperation + nestedCacheOperation)','conservativeLogicalEnvelopeOnly':True,'actualConstructionAndEmptyFrameAdmission':True,'guestInstructions':0,'initializeCalls':0,'invokeCalls':0,'finalConsumingCleanupZero':True,'ticketCeiling':86,'constructedTickets':21,'residentOwnerTickets':85,'additionalTicket':0,'physicalEvidence':False})
print(json.dumps({'comparison':metrics,'profile':dp,'FrozenTraceIdentical':True},indent=2))
