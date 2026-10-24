#!/usr/bin/env python3
"""Source-bound independent arithmetic; never executes compiler/test/VM code."""
from pathlib import Path
import gzip, hashlib, json

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'candidate'

def sha(raw): return hashlib.sha256(raw).hexdigest()
def save(name, value): (HERE/name).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
def bound(path, first, last):
    raw = (SOURCE/path).read_bytes()
    lines = raw.decode().splitlines(keepends=True)
    return {'path':path,'fullSourceSHA256':sha(raw),'firstLine':first,'lastLine':last,'text':''.join(lines[first-1:last])}

construction = [
    {'operation':'initial memory bytes','expression':'584 * 65536','credits':584*65536},
    {'operation':'initial table slots','expression':'46713','credits':46713},
    {'operation':'initial global slots','expression':'4','credits':4},
    {'operation':'four global initializer fixed credits','expression':'4 * 16','credits':4*16},
    {'operation':'one data segment range check','expression':'1','credits':1},
    {'operation':'one data payload precharge','expression':'17','credits':17},
]
assert sum(r['credits'] for r in construction[:3]) == 38319741
assert sum(r['credits'] for r in construction) == 38319823

cache = []
for function, label, body_bytes, instructions, pin_records in [
    (35,'initializer',14,6,1),
    (62,'first corpus outer',7,3,1),
    (36,'first corpus indirect callee',19,9,2),
]:
    charges = {'functionLookup':1,'pinRecordSearch':pin_records,'residentMissSearch':29,
               'scanSignatureLookup':1,'scanPatchReset':512,'scanDescriptorParameterCheck':1,
               'scanEncodedBytes':body_bytes,'scanInstructionAccounting':instructions,
               'planningSlotSearch':29,'planningEvictionBitCount':64,
               'buildSignatureLookup':1,'buildPatchReset':512,'buildDescriptorParameterCheck':1,
               'buildEncodedBytes':body_bytes,'buildInstructionAccounting':instructions,
               'buildInstructionPush':instructions}
    cache.append({'function':function,'label':label,'bodyBytesIncludingZeroLocalGroups':body_bytes,'instructions':instructions,'charges':charges,'total':sum(charges.values())})
assert [r['total']for r in cache] == [1198,1175,1218]
fixed = {'definedSlotInitialization':29,'pinRecordInitialization':64,'patchInitialization':512}
constructor_cache = sum(fixed.values())
assert constructor_cache == 605
warm = [
    {'function':62,'label':'second corpus outer','functionLookup':1,'pinRecordSearch':1,'residentHitSearch':2,'total':4},
    {'function':36,'label':'second corpus indirect callee','functionLookup':1,'pinRecordSearch':2,'residentHitSearch':3,'total':6},
]
derived = [constructor_cache,constructor_cache+cache[0]['total'],constructor_cache+sum(r['total']for r in cache),constructor_cache+sum(r['total']for r in cache)+sum(r['total']for r in warm)]
assert derived == [605,1803,4196,4206]

failure = gzip.decompress((HERE/'attempts/swift-debug/execute-stderr.gz').read_bytes()).decode()
assert 'attempted: 38319741, limit: 0' in failure
assert 'left: 4206\n right: 4196' in failure

save('independent-source-traces.json',{
    'schema':'mixer.swift-lifecycle.runtime-source-diagnosis.1',
    'candidateClosure':'0b36b551e2175aa713d698627493519249b6bfea023f05e13de730e6b06f977f',
    'method':'Independent arithmetic from exact engine charge sites and literal synthetic fixture operations; no additional execution or observed-number substitution.',
    'SL09':{'constructorExecutionWorkOperations':construction,'firstConstructorCharge':38319741,'successfulConstructorTotal':38319823,'proposedOriginalLifetimeBudget':38319823,'proposedInitializeFirstEntryAttempt':38319824,'cursor':{'stage':'Initialization','function':35,'offset':None},'diagnostic':{'kind':'WorkExhausted','code':'swift_run_work','resource':'ExecutionWork','attempted':38319824,'limit':38319823},'newBoundaryRuntimeStatus':'unrun-proposed','zeroLifetimeConstructionObserved':{'stage':'Invocation','function':34,'offset':211,'kind':'WorkExhausted','code':'swift_run_work','resource':'ExecutionWork','attempted':38319741,'limit':0}},
    'SL13':{'constructorCacheOperations':fixed,'coldOperations':cache,'warmOperations':warm,'derivedCumulativeCacheWork':{'constructed':derived[0],'initialized':derived[1],'firstCorpus':derived[2],'secondCorpus':derived[3]},'actualObservedOnly':{'firstCorpus':4196,'secondCorpus':4206},'residentOrder':[35,62,36],'warmCallExpected':{'cacheWorkDelta':10,'hitsDelta':2,'missesDelta':0,'decodesDelta':0,'evictionsDelta':0,'residentBytesDelta':0,'liveTicketsDelta':0},'sourceDerivationNotRuntimeInstrumentation':True},
    'sourceBindings':[
        bound('src/experimental_swift_reactor/lifecycle_tests.rs',150,262),
        bound('src/experimental_swift_reactor/lifecycle_tests.rs',358,381),
        bound('src/experimental_swift_reactor/lifecycle_tests.rs',643,693),
        bound('src/experimental_swift_reactor/lifecycle_tests.rs',788,821),
        bound('src/experimental_swift_reactor/execution.rs',1087,1288),
        bound('src/experimental_swift_reactor/execution.rs',1368,1510),
        bound('src/experimental_swift_reactor/execution.rs',139,204),
        bound('src/experimental_swift_reactor/frame_operations.rs',420,455),
        bound('src/experimental_swift_reactor/frame_operations.rs',555,637),
        bound('src/experimental/cache/borrowed.rs',672,858),
        bound('src/experimental/cache/decode.rs',1,92),
        bound('src/experimental/cache/decode.rs',150,164),
        bound('src/experimental/cache/decode.rs',196,244),
        bound('src/experimental/cache/decode.rs',442,462),
        bound('src/experimental_swift_reactor/cache.rs',1610,1680),
        bound('src/experimental_swift_reactor/cache.rs',1856,1894),
    ]
})
print(json.dumps({'constructorExecutionWork':38319823,'derivedCacheCumulative':derived,'newRuntimeRuns':0},sort_keys=True))
