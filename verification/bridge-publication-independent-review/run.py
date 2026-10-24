#!/usr/bin/env python3
"""Bounded independent schedule review; writes only this verification lane."""
from pathlib import Path
import argparse, datetime, hashlib, io, json, os, subprocess, tarfile, time

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
PRODUCER = ROOT / 'verification/bridge-native-exit-ci-repair'
STAGE = PRODUCER / 'native-26943ac'
ENV = os.environ | {'DEVELOPER_DIR': '/Applications/Xcode_26.6.app/Contents/Developer'}
parser = argparse.ArgumentParser(); parser.add_argument('--name', default='candidate-v1'); parser.add_argument('--full', action='store_true'); args = parser.parse_args()
assert args.name and '/' not in args.name and args.name not in {'.','..'}
RUN = OUT/args.name; RUN.mkdir(exist_ok=False)
FILES = ['experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime/Session.swift',
         'experimental-capability-runtime/Tests/MixerExperimentalCapabilityRuntimeTests/HTTPTests.swift']
def sha(raw): return hashlib.sha256(raw).hexdigest()
def save(name, data): (RUN/name).write_text(json.dumps(data, indent=2)+'\n')
def manifest(source):
    return {str(path.relative_to(source)): sha(path.read_bytes()) for path in sorted(source.rglob('*'))
            if path.is_file() and not {'.build', '.swiftpm'}.intersection(path.relative_to(source).parts)}
def command(name, argv, cwd=ROOT):
    start = time.monotonic()
    result = subprocess.run(argv, cwd=cwd, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=600)
    (RUN/(name+'.log')).write_bytes(result.stdout)
    record = {'command': argv, 'cwd': str(cwd), 'environment': {'DEVELOPER_DIR': ENV['DEVELOPER_DIR']},
              'exitCode': result.returncode, 'elapsedSeconds': time.monotonic()-start,
              'output': name+'.log', 'outputSHA256': sha(result.stdout)}
    save(name+'.json', record)
    print(name, result.returncode, round(record['elapsedSeconds'], 3), flush=True)
    return record

started = datetime.datetime.now(datetime.timezone.utc).isoformat()
revision = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
tree = subprocess.check_output(['git','rev-parse',revision+'^{tree}'],cwd=ROOT,text=True).strip()
before_files = {name: sha((ROOT/name).read_bytes()) for name in FILES}
producer_receipt = json.loads((STAGE/'receipt.json').read_text())
closure = {'library': producer_receipt['library'], 'headers': producer_receipt['headers']}
for entry in [closure['library'], *closure['headers'].values()]:
    assert sha(Path(entry['path']).read_bytes()) == entry['sha256'], entry['path']
source = RUN/'source'; source.mkdir(exist_ok=False)
archive = subprocess.check_output(['git','archive',revision,'sdk/Package.swift','sdk/Sources','sdk/Tests',
                                  'experimental-capability-runtime/Package.swift','experimental-capability-runtime/Sources',
                                  'experimental-capability-runtime/Tests','experimental-capability-runtime/verification/with-loopback.py'],cwd=ROOT)
with tarfile.open(fileobj=io.BytesIO(archive)) as reader: reader.extractall(source, filter='data')
for name in FILES: (source/name).write_bytes((ROOT/name).read_bytes())
(source/'experimental-capability-runtime/Tests/MixerExperimentalCapabilityRuntimeTests/ScheduleProbe.swift').write_bytes((OUT/'ScheduleProbe.swift').read_bytes())
before = manifest(source); save('source-manifest.json', before)
tools = [command('swift-version',['swift','--version']), command('xcode-version',['xcodebuild','-version']),
         command('host-version',['uname','-a']), command('python-version',['python3','--version'])]
results = []
for mode, options in [('debug',[]),('release',['-c','release']),('tsan',['--sanitize','thread'])]:
    argv = ['swift','test','--package-path',str(source/'experimental-capability-runtime'),
            '--scratch-path',str(OUT/'.build'/args.name/mode),*options]
    if args.full:
        argv = ['python3','-B',str(source/'experimental-capability-runtime/verification/with-loopback.py'),
                '--output',str(RUN/(mode+'-tls')),'--'] + argv + ['-Xswiftc','-DMIXER_EXPERIMENTAL_LOCAL_TLS_TEST']
    else: argv += ['--filter','independentPublication|publicOwnerDeinitRetainsActualNativeExitAndConstructionBudget']
    argv += ['-Xcc','-I'+str(STAGE/'include'),'-Xlinker','-L'+str(STAGE/'lib'),'-Xswiftc','-warnings-as-errors']
    results.append(command(mode, argv, source))
save('receipt.json', {'startedUTC':started, 'completedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'sourceRevision': revision,'sourceTree':tree,'gitSourceArchiveSHA256':sha(archive),'candidateFilesSHA256':before_files,
    'sourceManifestSHA256':sha(json.dumps(before,sort_keys=True).encode()),'snapshotUnchanged':before==manifest(source),
    'rootCandidateFilesUnchanged':before_files=={name:sha((ROOT/name).read_bytes()) for name in FILES},
    'sdkAndBridgeCommittedChangesSinceNativeArchive':subprocess.check_output(['git','diff','--stat',producer_receipt['source_revision'],revision,'--','sdk','experimental-capability-runtime'],cwd=ROOT,text=True),
    'nativeArtifactReuse':{'producerReceipt':str((STAGE/'receipt.json').relative_to(ROOT)),
                         'receiptSHA256':sha((STAGE/'receipt.json').read_bytes()),
                         'sourceRevision':producer_receipt['source_revision'],'hashesRechecked':True, **closure},
    'fullExistingSuiteAndScheduleProbes':args.full,
    'tools':tools,'commands':results,'scope':'Independent local host schedule probes of actual API/native construction; no product hooks or mocks; reused pinned capability VM archive, not current whole VM or Swift TSan-instrumented archive; no devices/release/GA evidence; hosted Swift 6.2.4 replay pending'})
raise SystemExit(0 if all(record['exitCode']==0 for record in results) else 1)
