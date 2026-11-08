"""Child-free, read-only evidence audit; writes only this directory's audit.json.

No imports of the runtime controller, execution of platform tools, scratch reads,
process observations, device commands, or network access. Hashing is chunked and
bounded by 120 seconds. The deleted R2 test APK is deliberately never accessed.
"""
from pathlib import Path
import datetime
import hashlib
import json
import sys
import time
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = HERE.parent
PREP = BASE / 'native-custody-premise'
RUN = PREP / 'runtime-attempt'
START = time.monotonic()
CHECKS = []
HASHES = {}
HELD = {40708,40709,40711,23663,20745,20770,20780,20817,20842,20851,20866,2424}

def require(value, label):
    if not value:
        raise RuntimeError(label)
    CHECKS.append(label)

def identity(path):
    path = Path(path)
    # None of the admissible inputs is scratch, including removed fresh scratch.
    if str(path).startswith(('/tmp/', '/private/tmp/')):
        raise RuntimeError('scratch reads forbidden')
    h = hashlib.sha256()
    size = 0
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            if time.monotonic()-START > 120:
                raise RuntimeError('read/hash budget exhausted')
            h.update(block)
            size += len(block)
    result = {'bytes': size, 'sha256': h.hexdigest()}
    HASHES[str(path)] = result
    return result

def read(path):
    identity(path)
    return json.loads(Path(path).read_text())

def digest(files):
    return hashlib.sha256(''.join(p+'\0'+v['sha256']+'\n' for p,v in sorted(files.items())).encode()).hexdigest()

receipt = read(RUN/'receipt.json')
commands = read(RUN/'commands.json')
binding = read(PREP/'prepared-source-binding.json')
reuse = read(PREP/'prepared-native-reuse.json')
prospective = read(BASE/'native-custody-review/review.json')
lock = read(RUN/'source-lock.json')
require(receipt['status'] == 'passed-smoke' and receipt['runtime']['passed'], 'runtime reports passed-smoke')
require(receipt['sourceRevision'] == binding['baseRevision'] == '96f03ab65966a6374e958e780fa09a3eed814c0b', 'exact product revision')
require(receipt['sourceTree'] == binding['baseTree'] == '6dacea5d2f5cd55d6934142cce556a4bd0fcd1c0', 'exact product tree')
require(prospective['verdict']=='ACCEPT', 'prospective controller review accepted')
for name, expected in prospective['candidateIdentities'].items():
    require(identity(PREP/name) == expected, 'prospective identity '+name)
require(identity(PREP/'run_native_probe.py')['sha256']=='4c582cea9e208f42212e55c185d0332748958f2a7a6028b1a116219e8c6c7f2a', 'controller exact requested hash')
for rel, expected in {**binding['canonicalInputs'], **binding['implementationFiles'], **reuse['nativeSourceFiles']}.items():
    require(identity(ROOT/rel)==expected, 'source identity '+rel)
require(len(binding['canonicalInputs'])==101 and digest(binding['canonicalInputs'])==binding['canonicalDigest']=='a10a62cc79145bc80bfd780257589f437cc82e2f1ebaad6ccde39c134d56e0ca', 'source101 digest')
policy = (ROOT/'cli/Sources/MixerBuild/AndroidSDKCompatibility.swift').read_text()
profile = json.loads(policy.split('Data(#"""\n',1)[1].split('\n        """#.utf8)',1)[0])
require(profile['id']=='mixer.android-source-pair.9', 'policy pair9')
for kind,count,expected in [('sdk',22,'bc03288599ece5612cc4dce8b80fc404942584e0477ec9333bd39c0fa7d352d0'),('adapter',24,'ee9414d3b68f9d66ba275c93339018e5eaebb161a7dc25d7056538c652305d89')]:
    files = profile[kind+'_files']
    require(files==binding['projections'][kind]['files'] and len(files)==count and digest(files)==expected, kind+' projection identity')
paths = {'scripts/ci/check-android-generated-java.py','cli/Sources/MixerBuild/AndroidSDKCompatibility.swift','cli/Sources/MixerBuild/Resources/android-build.py','scripts/ci/check-android-binding.py'}
for package in ('cli','sdk','updates'):
    paths.update(str(p.relative_to(ROOT)) for p in (ROOT/package/'Sources').rglob('*') if p.is_file())
    paths.update(str(p.relative_to(ROOT)) for p in (ROOT/package).glob('Package.*') if p.is_file())
paths.update('native/android/'+('engine/' if p.startswith('Sources/') else '')+p for p in profile['adapter_files'])
require(paths==set(binding['canonicalInputs']), 'independently reconstructed source roster')
require(len(lock['files'])==105, '105 frozen runtime inputs')
for rel, expected in lock['files'].items():
    require(identity(ROOT/rel)['sha256']==expected, 'runtime frozen source '+rel)
    retained = RUN/'canonical-inputs'/rel
    if retained.is_file():
        require(identity(retained)['sha256']==expected, 'retained canonical input '+rel)
closure = hashlib.sha256(json.dumps(lock['files'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
require(closure==lock['sourceClosureSHA256']==receipt['sourceClosureSHA256'], 'runtime source closure digest')
instrumentation = identity(ROOT/'native/android/tests/NativeCoordinatorV2IntegrationInstrumentation.java')
require(instrumentation==prospective['instrumentation']==binding['instrumentation'], 'unchanged reviewed instrumentation')
old_test = BASE/'android-toggle-oracle-integrated/canonical-inputs/native/android/tests/NativeCoordinatorV2IntegrationInstrumentation.java'
identity(old_test)
old_text = old_test.read_text()
new_text = (ROOT/'native/android/tests/NativeCoordinatorV2IntegrationInstrumentation.java').read_text()
for first,last in [('    private void awaitPresentation(', '    private static byte[] retained('), ('            check(Build.VERSION.SDK_INT', '            int checksBeforeMotion'), ('            stage = "runtime-toggle-oracle";', '            result.putInt("originalSmokeChecks"')]:
    old_last = {'            int checksBeforeMotion':'            stage = "runtime-toggle-oracle";', '            result.putInt("originalSmokeChecks"':'            result.putString("scope"'}.get(last,last)
    require(new_text.split(first,1)[1].split(last,1)[0] == old_text.split(first,1)[1].split(old_last,1)[0], 'unchanged original smoke/readiness block '+first.strip())
toolmap = {**reuse['currentToolsEqualOriginalBuildTools'], **receipt['tools']}
for path,expected in toolmap.items():
    require(identity(path)=={k:expected[k] for k in ('bytes','sha256')} and str(Path(path).resolve())==expected['realPath'], 'tool identity '+path)
require(len(toolmap)==33, '33 tool/library identities')
retained_apk = reuse['retainedAPK']
require(identity(retained_apk['path'])=={k:retained_apk[k] for k in ('bytes','sha256')}, 'historical retained library donor APK identity')
native = read(RUN/'native-reuse.json')
require(native==receipt['nativeReuse'], 'native reuse record matches receipt')
accepted = read(BASE/'android-toggle-oracle-integrated/receipt.json')
accepted_lock_path = BASE/'android-toggle-oracle-integrated/source-lock.json'
accepted_lock = read(accepted_lock_path)
require(identity(BASE/'android-toggle-oracle-integrated/receipt.json')['sha256']==native['acceptedReceiptSHA256'] and identity(accepted_lock_path)['sha256']==native['acceptedSourceLockSHA256'], 'historical accepted receipt/lock identities')
differences = [p for p,h in accepted_lock['files'].items() if lock['files'].get(p)!=h]
require(set(differences)=={'native/android/app/src/dev/mixer/android/NativeEnvironmentPlatformV2.java','native/android/tests/NativeCoordinatorV2IntegrationInstrumentation.java'}, 'exact two intentional source differences from prior accepted smoke')
original_build_path=Path(native['originalBuildReceipt'])
original_build=read(original_build_path)
original_lock=read(original_build_path.parent/'source-lock.json')
require(identity(original_build_path)['sha256']==native['originalBuildReceiptSHA256'] and identity(original_build_path.parent/'source-lock.json')['sha256']==native['originalSourceLockSHA256'], 'original native build provenance hashes')
require({p:v for p,v in original_build['artifacts'].items() if p.startswith('lib/')}==native['nativeLibraries']==accepted['nativeReuse']['nativeLibraries'], 'original/accepted/actual native library records agree')
require(native['nativeLibraries']==reuse['nativeLibraries'] and len(native['nativeLibraries'])==18, '18 reused native identities')
with zipfile.ZipFile(retained_apk['path']) as archive:
    require({p for p in archive.namelist() if p.startswith('lib/')}==set(native['nativeLibraries']), 'library donor ZIP closure')
    for name,expected in native['nativeLibraries'].items():
        data = archive.read(name)
        require({'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}==expected==receipt['artifacts'][name], 'donor library '+name)
pack = read(RUN/'packaging-validation.json')
require(pack['apkSHA256']==receipt['apkSHA256']=='d8cd6cbbbe4942eec416309cc346f8035b6c78893387b161ae923eb2c17091cc', 'R2 APK recorded hash agreement only')
for name,expected in native['nativeLibraries'].items():
    entry=pack['entries'][name]
    require({k:entry[k] for k in ('bytes','sha256')}==expected and entry['compressionMethod']==0 and entry['localDataOffsetMod16384']==0, 'recorded R2 packaged library '+name)
require(pack['entries']['classes.dex']['sha256']==receipt['artifacts']['dex/classes.dex']['sha256'], 'recorded dex agreement')
require(pack['entries']['assets/MixerAppearanceV2/descriptor.json']['sha256']==receipt['descriptorSHA256'], 'recorded descriptor agreement')
require(commands==receipt['commands'] and len(commands)==50, '50 matching command records')
total=0
for i,c in enumerate(commands):
    require(c['state']=='TERMINAL' and all(c[k] for k in ('terminal_custody','direct_child_reaped','stdout_eof','stderr_eof','owned_group_absent')) and not c['cleanup_errors'] and c['stop'] is None, 'terminal command '+str(i))
    require(c['owned_pgid']==c['pid'] and c['owned_pgid'] not in HELD, 'owned non-held group '+str(i))
    count=0
    for stream,path in c['logs'].items():
        require(Path(path).parent==RUN, 'log location '+str(i)+' '+stream)
        count+=identity(path)['bytes']
    require(count==c['output_bytes']<=c['output_limit']==8388608, 'exact output bytes '+str(i))
    total+=count
require(total==receipt['cleanup']['aggregateBytes']==27901 and total<67108864, 'aggregate output accounting')
require([c['label'] for c in commands if c['long_lived']]==['owned-adb-server','owned-emulator','app-logcat-before-startup'], 'three owned services')
require(all(c['exit_code']==-9 and c['signals']==['SIGKILL'] and c['group_probes']>=1 for c in commands if c['long_lived']), 'service terminal records have explicit signal/absence observations')
require(all(c['exit_code']==0 or (c['label'] in ('boot-0','boot-1') and c['exit_code']==1) for c in commands if not c['long_lived']), 'expected short-command exits')
for c in commands:
    if '/platform-tools/adb' in c['argv'][0] and c['label'] not in ('adb-version','disposable-adb-key'):
        require(c['argv'][1:5]==['-P','63338','-s','emulator-5570'], 'private serial-scoped adb '+c['label'])
require(commands[13]['argv'][1:6]==['--release','17','-Xlint:all','-Werror','-proc:none'] and len([x for x in commands[13]['argv'] if x.endswith('.java')])==21, 'strict 21-file production Java compile')
require(commands[14]['argv'][-2:]==[receipt['scratch']+'/inputs/native/android/tests/'+n for n in ('NativeCoordinatorV2IntegrationActivity.java','NativeCoordinatorV2IntegrationInstrumentation.java')], 'canonical two test compile inputs')
require(commands[15]['argv'][1:4]==['--min-api','28','--lib'], 'D8 min28 is packaging only')
require(commands[48]['argv'][5:]==['shell','am','instrument','-w','-r','dev.mixer.android.coordinator.test/dev.mixer.android.NativeCoordinatorV2IntegrationInstrumentation'], 'one exact instrumentation invocation')
require(sum(c['label']=='canonical-instrumentation' for c in commands)==1, 'no instrumentation retry')
output=Path(commands[48]['logs']['stdout']).read_text()
fields={}
for line in output.splitlines():
    if line.startswith('INSTRUMENTATION_RESULT: '):
        key,value=line.removeprefix('INSTRUMENTATION_RESULT: ').split('=',1)
        require(key not in fields, 'unique instrumentation field '+key)
        fields[key]=value
require(output.strip()==receipt['runtime']['instrumentationOutput'] and 'INSTRUMENTATION_CODE: -1' in output, 'exact successful runtime output')
require(not any('failure' in key.lower() for key in fields), 'no instrumentation failure fields')
for key,value in {'checks':'104','motionChecks':'93','originalSmokeChecks':'11','motionOriginalRaw':'<absent>','motionOriginalRawPresent':'false','motionOriginalEffective':'1.0','motionChangedEffectiveTarget':'0.0','motionRemovalQuietFlushes':'25','motionRemovedListenerCallbackCount':'1'}.items():
    require(fields[key]==value, 'result '+key)
for key in ['motionEffectiveRestoredBeforeRaw','motionEffectiveRestored','motionRawRestored','motionTestListenerRemoved','motionNoCallbackAfterRemove','motionAllTestHandlesClosed','motionOwnerListenerRemoved']:
    require(fields[key]=='true', 'result '+key)
for key,scale,generation,motion in [('motionChanged','0.0','6','true'),('motionRestored','1.0','7','false')]:
    value=fields[key]
    require('main=true, scale='+scale in value and 'committedGeneration='+generation in value and 'reduceMotion='+motion in value and 'exactPacketIdentityAndBytes=true' in value, 'callback facts '+key)
    completed=value.split('; completed=',1)[1]
    require('phase=LIVE' in completed and 'dirty=false' in completed and 'pendingDrain=null' in completed and 'operation=null' in completed, 'completed owner '+key)
restoration=read(RUN/'restoration-before-cleanup.json')
require(restoration==receipt['restoration'] and restoration['beforeCleanup'] and not restoration['instrumentationRetried'] and restoration['settingWrites']==0, 'restoration record agreement and no retry/write')
require(restoration['raw']=={'status':'verified','before':'null','after':'null','matched':True} and restoration['effective']['status']=='verified', 'raw/effective restoration records')
for i in (47,49):
    require(Path(commands[i]['logs']['stdout']).read_text().strip()=='null', 'raw external observation '+str(i))
require(read(RUN/'source-postflight.json')=={'changedInputs':{},'frozenInputCount':105}, 'source postflight')
require(read(RUN/'baseline-postflight.json')=={'byteForBytePreserved':True}, 'recorded baseline postflight')
baseline=read(RUN/'baseline-manifest.json')['files']
baseline_dir=BASE/'android-runtime'
require({str(p.relative_to(baseline_dir)) for p in baseline_dir.rglob('*') if p.is_file()}==set(baseline), 'retained baseline exact roster')
for rel,expected in baseline.items():
    require(identity(baseline_dir/rel)==expected, 'retained baseline '+rel)
require(receipt['cleanup']['allTerminalCustody'] and receipt['cleanup']['hold'] is None and receipt['cleanup']['scratchRemoved'] and receipt['cleanup']['privateADBKeysRemoved'] and not receipt['cleanup']['privateKeyRetained'] and not receipt['apkRetained'], 'recorded cleanup complete; no fresh absence probe')
require(receipt['sourceStable'] and receipt['baselineByteForBytePreserved'] and receipt['nativeInstancesStarted']==1 and not receipt['physicalTargetsQueried'] and not receipt['nativeAcceptance'] and not receipt['gaAcceptance'], 'narrow scope flags')
historical_dir=Path('/Users/andreyyurlov/.t3/worktrees/mixer/t3-c9ee386d/verification/plan-continuation-2026-11-07/android-motion-callback-runtime')
historical=read(historical_dir/'receipt.json')
identity(historical_dir/'app-logcat-before-startup.log')
require(historical['status']=='failed-smoke' and not historical['runtime']['passed'] and 'V2 requires UI owner thread' in (historical_dir/'app-logcat-before-startup.log').read_text(), 'historical Binder-thread and restoration failure remains failed')
held=read(BASE/'android-controller-custody-holds/receipt.json')
held_details=read(BASE/'android-controller-custody-holds/new-custody-holds.json')
require(held['state']=='HELD_UNKNOWN' and held['groups']==[40708,40709,40711] and not held['probeSignalRetryAllowed'] and 'Operation not permitted' in json.dumps(held_details), 'historical controller EPERM holds remain unknown')
result={'status':'PASS','createdUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsedSeconds':round(time.monotonic()-START,3),'command':[sys.executable,'-B',str(Path(__file__).resolve())],'python':sys.version,'checks':len(CHECKS),'source101':binding['canonicalDigest'],'projections':{k:binding['projections'][k]['sha256'] for k in ('sdk','adapter')},'runtimeSourceCount':105,'toolIdentityCount':len(toolmap),'nativeSourceCount':len(reuse['nativeSourceFiles']),'donorLibrariesIndependentlyRehashed':18,'commandsAudited':50,'recordedOutputBytes':total,'instrumentation':instrumentation,'instrumentationFields':fields,'testAPKIndependentRehash':False,'custodyIndependentlyProbed':False,'scope':'Child-free data/source/hash audit of retained actual API37 arm64 R2 run. Deleted test APK, scratch, live devices and process state not accessed.','checked':CHECKS,'identities':HASHES}
result['auditScript']=identity(__file__)
result['nonblockingNotes']=[{'field':'nativeReuse.matchingInputsExceptInstrumentation','recorded':native['matchingInputsExceptInstrumentation'],'actualMatchingInputs':len(accepted_lock['files'])-len(differences),'intentionalDifferences':differences,'handling':'Preserve historical receipt; parent should use the exact 103/105 comparison, not the stale 104 counter.'}]
(HERE/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('checked','identities','instrumentationFields','python','command')}))
