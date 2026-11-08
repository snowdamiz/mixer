"""One bounded offline host compile/test attempt. Never retry after custody failure."""
import hashlib, importlib.util, json, os, pathlib, shutil, sys, time
sys.dont_write_bytecode = True
P = pathlib.Path
OUT = P(__file__).resolve().parent
RUNNER = OUT.parents[2] / 'scripts/ci/check-android-generated-java.py'
SOURCE = OUT / 'input'
SWIFT = P('/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift')
DEV = P('/Applications/Xcode_26.6.app/Contents/Developer')
SDK = DEV / 'Platforms/MacOSX.platform/Developer/SDKs/MacOSX26.5.sdk'
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p, value): p.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
assert digest(RUNNER) == 'c758c9685ef536968db06dfaf9f25450eac47db83fd2531a8caa2000cf793e1a'
assert not (OUT / 'receipt.json').exists()
assert shutil.disk_usage(OUT).free > 2 * 1024**3
sources = {str(p.relative_to(SOURCE)): digest(p) for p in sorted(SOURCE.rglob('*')) if p.is_file()}
assert sum(p.stat().st_size for p in SOURCE.rglob('*') if p.is_file()) < 5_000_000
spec = importlib.util.spec_from_file_location('managedCommands', RUNNER)
managedCommands = importlib.util.module_from_spec(spec); spec.loader.exec_module(managedCommands)
scratch = OUT / 'scratch'; scratch.mkdir()
temporary = OUT / 'temporary'; temporary.mkdir()
env = dict(os.environ, DEVELOPER_DIR=str(DEV), SDKROOT=str(SDK), PATH=str(SWIFT.parent) + os.pathsep + os.environ['PATH'], MIXER_STORE_TEST_CLI=str(scratch / 'debug/mixer'), TMPDIR=str(temporary) + '/')
env.pop('MIXER_ASC_BEARER_TOKEN', None)
commands = managedCommands.Commands(OUT, env, seconds=600, command_seconds=600, output_bytes=4194304, total_output_bytes=33554432)
receipt = {'attempts':1, 'scope':'offline macOS Swift; synthetic JWTs from ephemeral test key; scripted responses; no provider access', 'sources':sources, 'sourceDigest':hashlib.sha256(json.dumps(sources,sort_keys=True,separators=(',', ':')).encode()).hexdigest(), 'runnerSHA256':digest(RUNNER), 'wrapperSHA256':digest(P(__file__)), 'swiftSHA256':digest(SWIFT), 'environment':{key:env[key] for key in ['DEVELOPER_DIR','SDKROOT','MIXER_STORE_TEST_CLI','TMPDIR']}, 'freeBeforeBuild':shutil.disk_usage(OUT).free, 'bounds':{'compileAttempts':1,'commandSeconds':600,'reviewSeconds':1200,'jobs':2,'streamBytes':4194304,'aggregateBytes':33554432,'sourceBytes':5000000,'scratchBytes':1073741824}}
save(OUT / 'receipt.json', receipt)
try:
    receipt['swiftVersion']=commands.run('swift-version',[SWIFT,'--version'],cwd=SOURCE)
    receipt['xcodeVersion']=commands.run('xcode-version',['/usr/bin/xcodebuild','-version'],cwd=SOURCE)
    receipt['sdkVersion']=commands.run('sdk-version',['/usr/bin/xcrun','--sdk','macosx','--show-sdk-version'],cwd=SOURCE)
    commands.run('r2-review',[SWIFT,'test','--package-path',SOURCE/'cli','--scratch-path',scratch,'-j','2','--filter','StoreSubmissionReconciliationTests|StoreR2IndependentReviewTests'],cwd=SOURCE,expected_failure=True,diagnostics=True)
    receipt['status']='expected-failure-command-completed; inspect assertions'
except BaseException as error: receipt.update(status='failed',error=str(error))
finally:
    receipt.update(terminalCustody=commands.custody_terminal(),commands=commands.records,aggregateOutputBytes=commands.used_output,sourceStable=all(digest(SOURCE/p)==h for p,h in sources.items()))
    save(OUT/'receipt.json',receipt)
    if commands.custody_terminal():
        cleanup={'freeBefore':shutil.disk_usage(OUT).free,'removed':[]}
        for p in [scratch,temporary]:
            n=sum(x.stat().st_size for x in p.rglob('*') if x.is_file());cleanup['removed'].append({'path':str(p),'bytes':n});shutil.rmtree(p)
        cleanup['freeAfter']=shutil.disk_usage(OUT).free;save(OUT/'cleanup.json',cleanup)
    print(json.dumps({k:receipt.get(k) for k in ['status','error','terminalCustody','sourceStable','aggregateOutputBytes']}))
