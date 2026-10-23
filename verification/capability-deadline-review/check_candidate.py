#!/usr/bin/env python3
"""Test-only prototype of the proposed narrow fix; SDK files never edited."""
from pathlib import Path
import difflib,hashlib,json,subprocess,time
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent;SCRATCH=ROOT/'.build/capability-deadline-review';SOURCE=SCRATCH/'original';BUILD=SCRATCH/'build'
r=json.loads((OUT/'receipt.json').read_text());r['candidate_commands']=[]
def sha(b):return hashlib.sha256(b).hexdigest()
original=(SOURCE/'sdk/Sources/MixerCapabilities/Host.swift').read_text()
fixed=original.replace('''        var timer: Task<Void, Never>?
''','''        var timer: Task<Void, Never>?
        var deadline: ContinuousClock.Instant?
''')
old_timeout='''        let timeout: UInt32
        if case .http(let request) = call.operation { timeout = min(request.timeoutMilliseconds, defaultTimeoutMilliseconds) } else { timeout = defaultTimeoutMilliseconds }
'''
assert fixed.count(old_timeout)==1
fixed=fixed.replace(old_timeout,'')
launch='''        slots[index].work = Task.detached { [weak self] in'''
fixed=fixed.replace(launch,old_timeout+'''        let deadline = ContinuousClock.now.advanced(by: .milliseconds(Int64(timeout)))
        slots[index].deadline = deadline
'''+launch)
fixed=fixed.replace('try await Task.sleep(nanoseconds: UInt64(timeout) * 1_000_000)','try await ContinuousClock().sleep(until: deadline)')
fixed=fixed.replace('''            do {
                let result = try await invoke()''','''            do {
                guard ContinuousClock.now < deadline else {
                    #if !os(WASI)
                    lease?.adapterExited() // No adapter was invoked; join with returned() below.
                    #endif
                    throw CapabilityFailure.deadlineExceeded
                }
                let result = try await invoke()''')
fixed=fixed.replace('''        terminal(index, outcome: outcome)
        #if !os(WASI)
        if slots[index].exitLease != nil { return }''','''        guard let deadline = slots[index].deadline else { return }
        let selected: CapabilityOutcome = ContinuousClock.now >= deadline ? .failure(.deadlineExceeded) : outcome
        terminal(index, outcome: selected)
        #if !os(WASI)
        if slots[index].exitLease != nil { return }''')
fixed=fixed.replace('''slots[index].terminal = false
        #if !os(WASI)''','''slots[index].terminal = false; slots[index].deadline = nil
        #if !os(WASI)''')
fixed=fixed.replace('''        terminal(index, outcome: .failure(.deadlineExceeded)); slots[index].work?.cancel()''','''        guard let deadline = slots[index].deadline, ContinuousClock.now >= deadline else { return }
        terminal(index, outcome: .failure(.deadlineExceeded)); slots[index].work?.cancel()''')
assert fixed!=original and fixed.count('var deadline: ContinuousClock.Instant?')==1
(OUT/'proposed-fix.patch').write_text(''.join(difflib.unified_diff(original.splitlines(keepends=True),fixed.splitlines(keepends=True),fromfile='a/sdk/Sources/MixerCapabilities/Host.swift',tofile='b/sdk/Sources/MixerCapabilities/Host.swift')))
(SCRATCH/'derived/Host.proposed-only.swift').write_text(fixed)
instrumented=fixed.replace('''            do {
                guard ContinuousClock.now < deadline''','''            await ReviewCandidateHooks.beforeWorkerDeadlineCheck() // TEST ONLY
            do {
                guard ContinuousClock.now < deadline''')
instrumented=instrumented.replace('''            await self?.complete(call.identity, outcome: outcome)''','''            await self?.complete(call.identity, outcome: outcome)
            await ReviewCandidateHooks.beforeInvocationReturn.hold() // TEST ONLY''')
instrumented=instrumented.replace('''        slots[index].timer = Task.detached { [weak self] in
''','''        slots[index].timer = Task.detached { [weak self] in
            await ReviewCandidateHooks.watchdog.hold() // TEST ONLY
''')
instrumented+='''\n// TEST ONLY forwarding to exercise first-terminal immutability after the cutoff.\nextension CapabilityHost {\n    func reviewDeliverExpiredWatchdog(_ id: CapabilityRequestID) { deadline(id) }\n}\n'''
(OUT/'candidate-test-only.patch').write_text(''.join(difflib.unified_diff(fixed.splitlines(keepends=True),instrumented.splitlines(keepends=True),fromfile='proposed/Host.swift',tofile='test-instrumented/Host.swift')))
host=SCRATCH/'derived/Host.candidate-instrumented.swift';host.write_text(instrumented)
inputs=[SOURCE/p for p in r['sources'] if p.endswith('.swift') and '/MixerCapabilities/' in p and not p.endswith('/Host.swift')]
def run(name,args):
 p=subprocess.run(list(map(str,args)),cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);log=OUT/(name+'.log');log.write_bytes(p.stdout);r['candidate_commands'].append({'name':name,'argv':list(map(str,args)),'exit_code':p.returncode,'log':str(log.relative_to(ROOT)),'log_sha256':sha(p.stdout)});(OUT/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(name+': exit '+str(p.returncode),flush=True)
 if p.returncode: print(p.stdout.decode(errors='replace'),flush=True);raise SystemExit(p.returncode)
 print(p.stdout.decode(errors='replace').strip(),flush=True)
exe=BUILD/'deadline-proposed-candidate'
run('compile-candidate',['swiftc','-swift-version','6','-parse-as-library','-I',BUILD,'-I',SCRATCH/'c-module','-L',BUILD,'-lMixerCore','-Xlinker','-rpath','-Xlinker',BUILD]+inputs+[host,OUT/'CandidateProbe.swift',BUILD/'lock.o','-o',exe])
for mode in ['late','timely','late-admission']:
 store=SCRATCH/('store-candidate-'+mode);store.mkdir(exist_ok=True);run('run-candidate-'+mode,[exe,mode,store])
for rel,expected in r['sources'].items(): assert sha((ROOT/rel).read_bytes())==expected,rel
r['candidate_scope']='Derived Host-only prototype plus separate, documented test-only watchdog/return gates and expired-watchdog forwarding; no production edit, no WASI/Android/iOS qualification'
r['candidate_probe_sha256']=sha((OUT/'CandidateProbe.swift').read_bytes());r['candidate_driver_sha256']=sha(Path(__file__).read_bytes());r['proposed_host_sha256']=sha(fixed.encode());r['instrumented_candidate_host_sha256']=sha(instrumented.encode());r['candidate_result']='Late completion and delayed worker admission selected deadlineExceeded; late admission did not invoke adapter or mutate storage; timely success remained first terminal after later deadline; installed exit join retained slot after complete until invocationReturned in all cases'
(OUT/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
