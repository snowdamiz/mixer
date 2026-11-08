from pathlib import Path
import datetime, hashlib, importlib.util, json, os, shutil, sys, time
sys.dont_write_bytecode = True
O = Path(__file__).resolve().parent
S = O / 'candidate'
R = O / 'cleanup_control.py'
def h(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p, v): p.write_text(json.dumps(v, indent=2, sort_keys=True) + '\n')
def size(p): return sum(f.stat().st_size for f in p.rglob('*') if f.is_file() and not f.is_symlink())
state = json.loads((O / 'state.json').read_text())
assert state['attempts'] < 2 and all(r['terminal_custody'] for r in state['commands'])
deadline = state['deadline']
remaining = deadline - time.time()
assert remaining > 20
assert h(R) == '8885f85a8d49ffbce813dd4221dc381ca88feef98f0f3905e67f4610381365df'
state['attempts'] += 1
A = O / ('attempt-' + str(state['attempts'])); A.mkdir()
sources = {str(p.relative_to(S)): h(p) for p in sorted(S.rglob('*')) if p.is_file()}
save(A / 'source-hashes.json', sources)
shutil.copyfile(S / 'cli/Tests/MixerBuildTests/StoreReconciliationTests.swift', A / 'StoreReconciliationTests.swift')
scratch = O / 'scratch'; scratch.mkdir(exist_ok=True)
tmp = scratch / 'tmp'; tmp.mkdir(exist_ok=True)
swift = Path('/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift')
env = {k: os.environ[k] for k in ['PATH', 'HOME', 'USER', 'LOGNAME', 'LANG', 'LC_ALL', 'SHELL'] if k in os.environ}
env.update(DEVELOPER_DIR='/Applications/Xcode_26.6.app/Contents/Developer', SDKROOT='/Applications/Xcode_26.6.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX26.5.sdk', TMPDIR=str(tmp) + '/', MIXER_STORE_TEST_CLI=str(scratch / 'build/debug/mixer'))
spec = importlib.util.spec_from_file_location('custody', R); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
c = m.Commands(A, env, deadline=time.monotonic()+remaining, output_bytes=4194304, total_output_bytes=33554432-state['usedOutput'], cleanup_seconds=5)
receipt = {'sourceHashes': sources, 'sourceDigest': hashlib.sha256(json.dumps(sources,sort_keys=True,separators=(',',':')).encode()).hexdigest(), 'runnerSHA256': h(R), 'driverSHA256': h(Path(__file__)), 'swiftSHA256': h(swift), 'environment': env, 'TOOLCHAINS': 'unset', 'bounds': {'swiftTestCommands': 2, 'perTestSeconds': 600, 'taskSeconds': 900, 'jobs': 2, 'scratchBytes': 1073741824, 'combinedCommandOutputBytes': 4194304, 'aggregateOutputBytes': 33554432}, 'parentHEAD': '62ce9b76840b2fa56306736fc4c4fe2962780adf', 'candidateSourceDigest': 'a188d2391aa55b5301c85d8c40836a9e07832420bd98b642d93592bdfaf06088', 'peakScratch': 0, 'scope': 'offline macOS host tests, synthetic tokens and responses, no live ASC; dependency network not instrumented'}
save(O / 'state.json', state); save(A / 'receipt.json', receipt)
try:
    if state['attempts'] == 1:
        receipt['swiftVersion'] = c.run('swift-version', [swift, '--version'], S)
        receipt['xcodeVersion'] = c.run('xcode-version', ['/usr/bin/xcodebuild', '-version'], S)
        receipt['sdkVersion'] = c.run('sdk-version', ['/usr/bin/xcrun', '--sdk', 'macosx', '--show-sdk-version'], S)
    item = c.start('swift-tests', [swift, 'test', '--package-path', S/'cli', '--scratch-path', scratch/'build', '--disable-automatic-resolution', '--skip-update', '-j', '2', '--filter', 'StoreSubmissionReconciliationTests'], S)
    until = min(time.monotonic()+600, c.deadline-5); next_size = 0
    while not c.hold:
        if time.monotonic() >= until: item['record']['stop'] = 'timeout'; break
        c.pump(.02)
        if c.hold or c.limit: break
        if time.monotonic() > next_size:
            receipt['peakScratch'] = max(receipt['peakScratch'], size(scratch)); next_size = time.monotonic()+1
            if receipt['peakScratch'] >= 1073741824: item['record']['stop'] = 'scratch-limit'; break
        if c.reaped(item) and item['record']['stdout_eof'] and item['record']['stderr_eof']: break
    c.stop(item); c.persist(item)
    receipt['passed'] = item['record']['exit_code'] == 0 and item['record']['terminal_custody'] and not item['record']['stop'] and not c.hold and not c.limit
except BaseException as error:
    receipt['error'] = repr(error)
finally:
    receipt['sourceStable'] = all(h(S/p) == v for p,v in sources.items())
    receipt['cleanup'] = c.cleanup(scratch)
    receipt['commands'] = c.records
    receipt['logHashes'] = {p.name: h(p) for p in A.iterdir() if p.suffix in ['.stdout', '.stderr']}
    state['commands'] += c.records; state['usedOutput'] += c.used_output
    save(O / 'state.json', state); save(A / 'receipt.json', receipt)
    print(json.dumps({k: receipt.get(k) for k in ['passed', 'error', 'sourceStable', 'cleanup', 'peakScratch']}))
