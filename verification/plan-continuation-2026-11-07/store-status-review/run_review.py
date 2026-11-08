"""Bounded review-only host runner. Never executes a provider or device command."""
import datetime,hashlib,importlib.util,json,os,pathlib,sys,threading,time
sys.dont_write_bytecode=True
P=pathlib.Path
OUT=P(__file__).resolve().parent
ROOT=OUT.parents[2]
SOURCE=OUT/'input'
SWIFT=P('/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift')
DEV=P('/Applications/Xcode_26.6.app/Contents/Developer')
SDK=DEV/'Platforms/MacOSX.platform/Developer/SDKs/MacOSX26.5.sdk'
RUNNER=ROOT/'scripts/ci/check-android-generated-java.py'
def save(p,v): p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('managedCommands',RUNNER)
managedCommands=importlib.util.module_from_spec(spec);spec.loader.exec_module(managedCommands)
statepath=OUT/'state.json'
state=json.loads(statepath.read_text()) if statepath.exists() else {'attempts':0,'usedOutput':0,'commands':[]}
assert state['attempts']<2
assert all(r['terminal_custody'] for r in state['commands'])
state['attempts']+=1
attempt=OUT/('attempt-'+str(state['attempts']));attempt.mkdir()
scratch=OUT/'scratch'
if state['attempts']==1: scratch.mkdir()
assert scratch.is_dir() and SWIFT.is_file() and SDK.is_dir()
seconds=1200-(time.time()-json.loads((OUT/'started.json').read_text())['epoch'])
assert seconds>0
env=dict(os.environ,DEVELOPER_DIR=str(DEV),SDKROOT=str(SDK),PATH=str(SWIFT.parent)+os.pathsep+os.environ['PATH'],MIXER_STORE_TEST_CLI=str(scratch/'debug/mixer'),TMPDIR=str(OUT/'temporary')+'/')
env.pop('MIXER_ASC_BEARER_TOKEN',None)
(OUT/'temporary').mkdir(exist_ok=True)
commands=managedCommands.Commands(attempt,env,seconds=seconds,command_seconds=600,output_bytes=2097152,total_output_bytes=8388608-state['usedOutput'])
receipt={'scope':'independent review: offline host only; candidate snapshot plus review probes','attempt':state['attempts'],'runnerSHA256':digest(RUNNER),'wrapperSHA256':digest(P(__file__)),'swiftSHA256':digest(SWIFT),'environment':{k:env[k] for k in ['DEVELOPER_DIR','SDKROOT','MIXER_STORE_TEST_CLI','TMPDIR']},'sources':{str(p.relative_to(SOURCE)):digest(p) for p in sorted(SOURCE.rglob('*')) if p.is_file()},'bounds':{'commandSeconds':600,'totalSeconds':1200,'outputBytes':8388608,'jobs':2,'maxAttempts':2}}
save(statepath,state);save(attempt/'receipt.json',receipt)
stop=threading.Event()
def interim():
    while not stop.wait(.5): save(attempt/'interim-commands.json',commands.records)
monitor=threading.Thread(target=interim,daemon=True);monitor.start()
passed=False
try:
    if state['attempts']==1:
        receipt['swiftVersion']=commands.run('swift-version',[SWIFT,'--version'],cwd=SOURCE)
        receipt['xcodeVersion']=commands.run('xcode-version',['/usr/bin/xcodebuild','-version'],cwd=SOURCE)
        receipt['sdkVersion']=commands.run('sdk-version',['/usr/bin/xcrun','--sdk','macosx','--show-sdk-version'],cwd=SOURCE)
        receipt['parentRevision']=commands.run('parent-revision',['git','rev-parse','HEAD','HEAD^{tree}'],cwd=ROOT)
        receipt['candidateRevision']=commands.run('candidate-revision',['git','rev-parse','HEAD','HEAD^{tree}'],cwd='/Users/andreyyurlov/.t3/worktrees/mixer/t3-b92773b5')
    commands.run('store-tests' if state['attempts']==1 else 'review-probes',[SWIFT,'test','--package-path',SOURCE/'cli','--scratch-path',scratch,'-j','2','--filter','StoreSubmissionReconciliationTests' if state['attempts']==1 else 'StoreIndependentReviewTests'],cwd=SOURCE,diagnostics=True)
    passed=True
except BaseException as error: receipt['error']=str(error)
finally:
    stop.set();monitor.join(timeout=1)
    state['commands']+=commands.records;state['usedOutput']+=commands.used_output
    receipt.update(status='passed' if passed else 'failed',terminalCustody=commands.custody_terminal(),sourceStable=all((SOURCE/p).exists() and digest(SOURCE/p)==h for p,h in receipt['sources'].items()),commands=commands.records,aggregateOutputBytes=state['usedOutput'])
    save(statepath,state);save(attempt/'receipt.json',receipt)
    print(json.dumps({k:receipt.get(k) for k in ['attempt','status','error','terminalCustody','sourceStable','aggregateOutputBytes']}),flush=True)
sys.exit(0 if passed else 1)
