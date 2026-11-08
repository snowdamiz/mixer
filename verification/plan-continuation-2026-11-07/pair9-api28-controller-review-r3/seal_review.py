"""Seal observed review evidence and validate admission in memory; no child or native entrypoint."""
import datetime
import importlib.util
from pathlib import Path
import shlex
import sys

OUT = Path(__file__).resolve().parent
BASE = OUT.parent
P = BASE/'pair9-api28-controller-fix-r3'
R2 = BASE/'pair9-api28-controller-fix-r2'
spec = importlib.util.spec_from_file_location('admission_only', P/'run_api28.py')
r = importlib.util.module_from_spec(spec); spec.loader.exec_module(r)
pre, post = (r.load(OUT/('frozen-'+phase+'.json')) for phase in ('preflight','postflight'))
r.require(pre['status'] == post['status'] == 'passed', 'frozen checks failed')
for path, expected in post['selectedFiles'].items():
    r.require(r.identity(path) == expected, 'evidence drift during sealing: '+path)
frozen = r.load(P/'controller-packet.json')
normal, optimized = (r.load(OUT/('independent-'+mode+'.json')) for mode in ('normal','optimized'))
for receipt in (normal, optimized):
    r.require(receipt['status'] == 'passed' and receipt['tests'] == 62 and receipt['fakeScratchRemoved'], 'independent controls incomplete')
    r.require(not receipt['failures'] and not receipt['errors'], 'control failures')
    r.require(receipt['controller'] == r.identity(P/'run_api28.py') and receipt['packet'] == r.identity(P/'controller-packet.json'), 'independent control identity')
supervisor = r.load(OUT/'control-supervisor/receipt.json')
r.require(supervisor['status'] == 'passed' and len(supervisor['commands']) == 2, 'supervision count/status')
r.require(supervisor['cleanup']['allTerminalCustody'] and supervisor['cleanup']['scratchRemoved'], 'outer cleanup not terminal')
for record in supervisor['commands']:
    r.require(record['exit_code'] == 0 and all(record[k] for k in ('direct_child_reaped','stdout_eof','stderr_eof','owned_group_absent','terminal_custody')), 'test child custody incomplete')
for mode in ('normal','optimized'):
    producer = r.load(P/('host-'+mode+'.json'))
    r.require(producer['status'] == 'passed' and producer['tests'] == 53, 'producer controls incomplete')
probe = r.load(P/'inherited-client-refusal/receipt.json')
r.require(probe['status'] == 'passed' and len(probe['commands']) == 1, 'retained probe failed')
r.require(probe['commands'][0]['argv'] == [str(r.ADB), '-s', 'emulator-5678', 'get-state'], 'probe supplied host/port flags')
r.require(probe['commands'][0]['exit_code'] == 1 and probe['commands'][0]['terminal_custody'], 'probe custody/exit')
r.require(probe['cleanup']['allTerminalCustody'] and probe['cleanup']['scratchRemoved'], 'probe cleanup')
stderr = (P/'inherited-client-refusal/000-no-autostart-refusal.stderr').read_text()
r.require('cannot start server on remote host' in stderr and 'daemon started' not in stderr and 'starting now' not in stderr, 'probe evidence')
official = r.load(R2/'official-sources.json')
for name, expected in official.items():
    path = R2/('official-'+name.replace('/','-'))
    r.require(r.identity(path) == {k:expected[k] for k in ('bytes','sha256')}, 'official source mismatch')
checker_spec = importlib.util.spec_from_file_location('source_profile_only', r.ROOT/'scripts/ci/check-android-generated-java.py')
checker = importlib.util.module_from_spec(checker_spec); checker_spec.loader.exec_module(checker)
profile = checker.load_profile(r.ROOT)
r.require(len(profile['sdk_files']) == 22 and checker.source_digest(profile['sdk_files']) == post['sdk22Digest'], 'SDK22 digest')
r.require(len(profile['adapter_files']) == 24 and checker.source_digest(profile['adapter_files']) == r.ADAPTER_SHA, 'adapter24 digest')
r.require(not (P/'runtime-attempt').exists(), 'root attempt already reserved; do not issue fresh acceptance')
command = shlex.split((P/'root-command.txt').read_text())
r.require(command[2] == str(P/'run_api28.py') and command[-1] == str(OUT/'review.json'), 'root command binding')
review = {
    'verdict':'ACCEPT', 'scope':'ONE_API28_ARM64_RUNTIME_ATTEMPT',
    'reviewKind':'Fresh independent R3 prospective controller admission; no runtime execution or acceptance',
    'reviewer':'gpt-6-astra xhigh review sub-agent',
    'recordedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'controllerSHA256':r.identity(P/'run_api28.py')['sha256'],
    'packetSHA256':r.identity(P/'controller-packet.json')['sha256'], 'lifecycleSHA256':r.LIFECYCLE_SHA,
    'controlsSHA256':r.identity(P/'host_controls.py')['sha256'],
    'descriptorHelperSHA256':r.identity(P/'server_fd_exec.py')['sha256'],
    'hostReceipts':{mode:r.identity(P/('host-'+mode+'.json')) for mode in ('normal','optimized')},
    'sourceRevision':post['sourceRevision'], 'sourceTree':post['sourceTree'],
    'sourceDigest101':r.SOURCE_SHA, 'sdk22Digest':post['sdk22Digest'], 'adapter24Digest':r.ADAPTER_SHA,
    'apk':post['apk'], 'bounds':frozen['bounds'], 'limits':frozen['limits'],
    'findings':[],
    'resolvedFindings':[
        {'id':'R1-P1', 'status':'addressed', 'evidence':'Retained listener, identical sealed binary and explicit numeric clients; unchanged R2 safeguards and executable controls retained.'},
        {'id':'R2-P1', 'status':'addressed', 'evidence':'Inherited numeric socket/address before every relevant launch; modeled delayed -s-only child remains remote after UNKNOWN and outer listener release; R2 negative control takes local launch branch; retained root no-H/no-P exact-binary refusal corroborates selection.'},
        {'id':'R1-P2', 'priorR2Status':'addressed', 'status':'remains addressed', 'evidence':'Exact authored PNGs survive known-terminal failures; closed admission prevents retrieval, including between images; original failure and pending visual review retained.'}],
    'independentControls':{
        'invocations':2, 'maximumInvocations':2, 'maximumSecondsEach':120, 'testsEach':62,
        'candidateControlsRetained':53, 'baseline':34, 'producerR2':16, 'producerR3':3,
        'reusedIndependentR2':6, 'newIndependentR3':3,
        'normal':r.identity(OUT/'independent-normal.json'), 'optimized':r.identity(OUT/'independent-optimized.json'),
        'normalElapsedSeconds':normal['elapsedSeconds'], 'optimizedElapsedSeconds':optimized['elapsedSeconds'],
        'supervisorReceipt':r.identity(OUT/'control-supervisor/receipt.json'),
        'acceptedLifecycleSHA256':r.LIFECYCLE_SHA, 'outerTestChildrenTerminal':True,
        'scratchRemoved':True, 'insideControlsRealChildren':0, 'insideControlsRealNativeCommands':0,
        'insideControlsRealGroupOperations':0, 'outputLimitBytes':supervisor['outputBytes'],
        'aggregateLimitBytes':supervisor['totalOutputBytes'],
        'selectionModelLimitation':'Executable model from retained official source; not execution of ADB or emulator machine code.'},
    'retainedRootInheritedClientProbe':{
        'reviewerInvocations':0, 'rootInvocations':1, 'receipt':r.identity(P/'inherited-client-refusal/receipt.json'),
        'adb':probe['adbIdentity'], 'argv':probe['commands'][0]['argv'],
        'exitCode':1, 'elapsedSeconds':probe['elapsedSeconds'], 'terminalCustody':True,
        'scratchRemoved':True, 'serverStarts':0, 'emulators':0,
        'observed':'Remote-host refusal; macOS Operation timed out; no -H/-P in argv; port reserved through cleanup.'},
    'frozenPreflight':r.identity(OUT/'frozen-preflight.json'),
    'frozenPostflight':r.identity(OUT/'frozen-postflight.json'),
    'packetBindingsVerified':1169, 'externalBindingsUnchanged':1164,
    'sourceAndMachineEvidence':{
        'officialSourcesManifest':str(R2/'official-sources.json'),
        'adbSocketSourceLines':'official-socket_spec.cpp:165-193',
        'adbEnvironmentSourceLines':'official-client-commandline.cpp:1646-1683',
        'adbRefusalSourceLines':'official-client-adb_client.cpp:254-282',
        'installedAdbAddresses':['0x1000a2f70-0x1000a3048','0x1000041e0-0x1000041f0','0x10000427c','0x100004368'],
        'emulatorSource':'pair9-api28-controller-review-r2/official-emulator-AdbInterface.cpp:555-604; QemuMiscPipe.cpp:360-379',
        'installedEmulatorAddresses':['0x100c17618','0x100c18718','0x100c18760-0x100c18768','0x100c187f8'],
        'retainedR2ArtifactsVerified':post['retainedR2ManifestVerified'],
        'freshDisassembly':False, 'sourceBinaryReproducibilityClaim':False},
    'priorFailurePreserved':{'testsBeforeStop':52, 'fixtureOnlyCorrection':r.identity(OUT/'fixture-correction.diff'),
        'firstFailure':r.identity(P/'first-control-failure/host-normal.json'),
        'firstSupervisor':r.identity(P/'control-supervisor/receipt.json'),
        'correction':'Rename fixture dictionary captured to key_environment; controller unchanged.'},
    'rootAttemptAuthorizedByThisReview':True, 'prospectiveRootAttemptsAdmitted':1,
    'runtimeAuthorized':'ONE prospective exact root attempt only', 'runtimeAttemptsExecutedByReviewer':0,
    'nativeAcceptance':False, 'visualAcceptance':False, 'gaAcceptance':False,
    'prospectiveCommand':command, 'artifactDetails':'decision.md',
    'conditions':[
        'Consume exactly the bound review/controller/packet/host receipts through existing admission and fresh binding checks.',
        'One exclusive runtime-attempt reservation; no retry, including failed attempts.',
        'Sticky UNKNOWN retains scratch and prohibits further process probes, signals, or native actions.',
        'All historical process/scratch, FieldLog, v5/frozen-hosted, phone and reserved iOS holds remain unchanged.'],
    'limitations':[
        'Native acceptfd handoff, emulator integration, API28 ART/JNI, native cleanup and screenshots remain unexecuted here.',
        'The independent selection discriminant is a model corroborated by retained official source, installed-binary evidence and the root client-only probe; it is not a real delayed emulator-child run.',
        'Admission covers reviewed accidental owned-server loss with unchanged listener and same-binary safeguards; ADB retains a separate version-mismatch restart path.',
        'Earlier failed probes and original rejected-DEX history remain preserved; no historical failure is recast as a pass.',
        'No native, visual, FieldLog immutable published-package, release or GA qualification follows.',
        'No network, ADB/JVM/emulator/compiler/device/UI/AX/capture, held process query, delegation, commit or push occurred in this review. Only assigned review directory written.']}
r.save(OUT/'review.json',review)
r.admission(r.load(OUT/'review.json'),frozen,review['controllerSHA256'])
r.save(OUT/'admission-check.json',{'status':'passed','command':[sys.executable,'-B',str(Path(__file__).resolve())],
    'python':sys.version, 'review':r.identity(OUT/'review.json'),
    'scope':'Actual candidate admission() called on written review; main()/execute() not called; no new control invocation',
    'runtimeAttemptDirectoryAbsent':True,'childrenSpawned':0,'nativeCommands':0})
r.save(OUT/'session-receipt.json',{'startedUTC':'2026-11-08 02:33:29 UTC',
    'completedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'maximumMinutes':12,
    'testInvocations':2,'maximumTestInvocations':2,'testInvocationMaximumSeconds':120,
    'networkCalls':0,'nativeCommands':0,'delegations':0,'commits':0,'pushes':0,
    'sourceRevisionCommand':['git','rev-parse','HEAD','HEAD^{tree}'],
    'sourceRevision':post['sourceRevision'],'sourceTree':post['sourceTree'],
    'gitVersionCommand':['git','--version'],'gitVersion':post['gitVersion'],
    'python':sys.version,'writeScope':str(OUT),
    'holds':'No held processes, retained scratch, devices, reserved iOS resource or frontend were inspected or mutated.'})
manifest = {str(path.relative_to(OUT)):r.identity(path) for path in sorted(OUT.rglob('*'))
            if path.is_file() and path.name != 'artifact-manifest.json'}
r.save(OUT/'artifact-manifest.json',manifest)
print('ACCEPT: exact written review passes candidate admission; 62/62 normal and optimized; one prospective root attempt only.')
