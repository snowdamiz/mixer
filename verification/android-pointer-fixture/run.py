#!/usr/bin/env python3
"""Frozen private pointer runner; explicit root dispatch only. Host imports never invoke a native command."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import re
from types import ModuleType
import common

HERE,ROOT=common.HERE,common.ROOT
CONTRACT=HERE/'runner-contract-2.json'
CONTRACT_SHA256='5226330d11b6754c8860396f5e38ba49fffc709fac3b07858b070e6401b2ba93'


def replacements(contract):
    before=contract['acceptedBuildBindings'];after=contract['buildBindings'];candidate=contract['candidate']
    return [
      ('pointer-build-directory',"BUILDS = ROOT / 'verification/android-coordinator-apk-packaging'","BUILDS = ROOT / 'verification/android-pointer-fixture'"),
      ('pointer-source-closure',"SOURCE_CLOSURE_SHA256 = '"+common.EXPECTED_CLOSURE+"'","SOURCE_CLOSURE_SHA256 = '"+contract['sourceClosureSHA256']+"'"),
      ('pointer-archive',"ARCHIVE_SHA256 = '"+before['built-artifacts.tar.gz']+"'","ARCHIVE_SHA256 = '"+after['built-artifacts.tar.gz']+"'"),
      ('pointer-build-bindings','BUILD_BINDINGS = '+json.dumps(before,indent=4,sort_keys=True),'BUILD_BINDINGS = '+json.dumps(after,indent=4,sort_keys=True)),
      ('pointer-bind-function',contract['acceptedBindSource'],'''def bind_candidate(built):
    if sha(_helper_path) != PROCESS_HELPER_SHA256:
        raise ValueError('accepted owned process helper drift')
    for name, expected in BUILD_BINDINGS.items():
        if sha(built / name) != expected:
            raise ValueError('pointer frozen build binding drift ' + name)
    return _pointer_bind(built)


'''),
      ('pointer-cli-help',"help='packaging corrected test-only candidate-1 only'","help='frozen private actual-pointer "+candidate+" only'"),
      ('pointer-cli-candidate',"if args.build != 'candidate-1' or not re.fullmatch", "if args.build != '"+candidate+"' or not re.fullmatch"),
      ('pointer-cli-error',"parser.error('bound packaging candidate-1 and fresh runtime-N required')","parser.error('bound pointer "+candidate+" and fresh runtime-N required')"),
      ('pointer-log-budget-state',"    emulator_log = None\n", "    emulator_log = None\n    emulator_reader = None\n    output_budget = _output.Budget()\n"),
      ('pointer-bounded-command-output',"        log.write_bytes(output)\n", "        output_budget.write(log, output, cleanup=name in _output.CLEANUP_NAMES)\n"),
      ('pointer-log-budget-failure',"        print(name + ': exit ' + str(code), flush=True)\n", "        print(name + ': exit ' + str(code), flush=True)\n        if output_budget.overflow and name not in _output.CLEANUP_NAMES:\n            raise RuntimeError('32MiB runner log budget exceeded; cleanup reserved and failure retained')\n"),
      ('pointer-emulator-bounded-reader',"""        process = subprocess.Popen(expected_argv, cwd=ROOT, stdout=emulator_log, stderr=subprocess.STDOUT,
                                   start_new_session=True)
""", """        process = subprocess.Popen(expected_argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        emulator_reader = _output.Reader(process, emulator_log, output_budget)
"""),
      ('pointer-instrumentation-arguments',"""        code, instrument = run('actual-native-join', adb + ['shell', 'am', 'instrument', '-w', '-e',
            'descriptorSHA256', metadata['descriptorSHA256'], PACKAGE + '/dev.mixer.android.CoordinatorJoinInstrumentation'],
            timeout=240, allow_failure=True)
""", """        code, instrument = run('actual-native-pointer', adb + ['shell', 'am', 'instrument', '-w',
            '-e', 'descriptorSHA256', metadata['descriptorSHA256'],
            '-e', 'apkSHA256', metadata['apkSHA256'],
            '-e', 'sourceClosureSHA256', metadata['sourceClosureSHA256'],
            '-e', 'sourceRevision', metadata['sourceRevision'],
            '-e', 'sourceTree', metadata['sourceTree'],
            '-e', 'fixtureSHA256', metadata['fixtureSHA256'],
            PACKAGE + '/dev.mixer.android.CoordinatorJoinInstrumentation'], timeout=180, allow_failure=True)
"""),
      ('pointer-preinstall-source-signature',"        save(out / 'apk-packaging-preinstall.json', _packaging_check_path(apk))", """        preinstall = bind_candidate(built)
        if preinstall['sourceClosureSHA256'] != metadata['sourceClosureSHA256'] or preinstall['apkSHA256'] != metadata['apkSHA256'] or sha(apk) != metadata['apkSHA256']:
            raise ValueError('preinstall frozen source/APK identity differs')
        save(out / 'source-identity-preinstall.json', {'sourceRevision': metadata['sourceRevision'], 'sourceTree': metadata['sourceTree'],
            'sourceClosureSHA256': metadata['sourceClosureSHA256'], 'sourceInputsRechecked': 105, 'liveNativeAndSDKInputsRechecked': 88,
            'apkSHA256': sha(apk), 'scope': 'frozen source plus unchanged live native/SDK content; disjoint repository commits do not alter the content authority'})
        _, signature = run('apk-apksigner-preinstall', [SDK / 'build-tools/37.0.0/apksigner', 'verify', '--verbose', '--print-certs', apk])
        certificates = re.findall(r'certificate SHA-256 digest: ([0-9a-f]{64})', signature.decode())
        if certificates != [metadata['debugCertificateSHA256']]:
            raise ValueError('preinstall private APK signature certificate differs')
        save(out / 'apk-packaging-preinstall.json', _packaging_check_path(apk))"""),
      ('pointer-bound-private-exports',contract['acceptedExportSource'],'''            exports = native.get('exports', {})
            if not isinstance(exports, dict) or not 1 <= len(exports) <= 128:
                raise ValueError('bounded private pointer export index required')
            export_bytes = 0
            for filename, value in exports.items():
                if not re.fullmatch(r'pointer-[a-z0-9-]+\\.(json|bin|jsonl)', filename):
                    raise ValueError('unsafe pointer export name')
                if set(value) != {'bytes', 'sha256'} or type(value['bytes']) is not int or not 0 <= value['bytes'] <= 8388608 or not re.fullmatch(r'[0-9a-f]{64}', value['sha256']):
                    raise ValueError('invalid pointer export binding')
                export_bytes += value['bytes']
                if export_bytes > 33554432:
                    raise ValueError('32MiB private metadata export budget exceeded')
                _, payload = run('export-' + filename, adb + ['exec-out', 'run-as', PACKAGE, 'cat', 'files/' + filename])
                if len(payload) != value['bytes'] or hashlib.sha256(payload).hexdigest() != value['sha256']:
                    raise ValueError('private pointer export differs from native binding')
                if filename.endswith('.bin') and len(payload) > 262144:
                    raise ValueError('packet exceeds 256KiB bound')
                (out / filename).write_bytes(payload)
            _pointer_validate_native(native, out, metadata)
'''),
      ('pointer-native-budgets',"        if native['status'] != 'passed' or native['operations'] != 8 or not 1 <= native['checks'] <= 256:\n", "        if native['status'] != 'passed' or native['operations'] != 20 or not 1 <= native['checks'] <= 512:\n"),
      ('pointer-success-scope',"receipt['status'] = 'actual-API37-private-ordinary-join-bounded-subset-passed'","receipt['status'] = 'actual-API37-private-pointer-bounded-subset-passed'"),
      ('pointer-runner-scope',"'scope': 'bounded actual API37 private ordinary JNI/Swift/coordinator/native subset only; no full native fault/IME/lifecycle, public/signed/physical/FieldLog/store/GA acceptance'", "'scope': 'bounded actual API37 private pointer delivery/state subset only; internal callbacks unobserved; native IME/accessibility/public/signed/physical/FieldLog/store/operational/GA pending'"),
      ('pointer-output-reader-cleanup',"""                if emulator_log is not None:
                    emulator_log.close()
""", """                if emulator_reader is not None:
                    try:
                        emulator_reader.finish()
                    except BaseException as failure:
                        cleanup_errors.append(repr(failure))
                        receipt['cleanup'] = 'failed'
                if emulator_log is not None:
                    emulator_log.close()
"""),
      ('pointer-final-output-budget',"        receipt['finishedUTC'] = datetime.datetime.now(datetime.timezone.utc).isoformat()\n", "        receipt['outputBudget'] = output_budget.report()\n        if output_budget.overflow:\n            receipt['status'] = 'failed-runner-output-budget'\n        receipt['finishedUTC'] = datetime.datetime.now(datetime.timezone.utc).isoformat()\n"),
      ('pointer-exact-root-seal',"and path.name != 'artifact-seal.json'", "and path != out / 'artifact-seal.json'"),
    ]


def transform(source,contract):
    deltas=[]
    for name,old,new in replacements(contract):
        count=source.count(old)
        if count!=1:raise ValueError('expected exact one source site '+name+'; observed '+str(count))
        source=source.replace(old,new,1);deltas.append({'name':name,'count':count,'beforeSHA256':hashlib.sha256(old.encode()).hexdigest(),'afterSHA256':hashlib.sha256(new.encode()).hexdigest()})
    return source,deltas


def validate_native(native,out,metadata):
    import oracle
    return oracle.validate(native,out,metadata)


def load_runner():
    if common.sha(CONTRACT)!=CONTRACT_SHA256:raise ValueError('frozen pointer runner contract drift')
    contract=json.loads(CONTRACT.read_text());adapter,inherited,original,_=common.accepted()
    if hashlib.sha256(original.encode()).hexdigest()!=contract['acceptedConcreteRunnerSHA256']:raise ValueError('accepted concrete runner drift')
    for name,value in contract['implementationBindings'].items():
        if common.sha(HERE/name)!=value:raise ValueError('pointer implementation drift '+name)
    for path,value in contract['toolBindings'].items():
        if common.sha(path)!=value:raise ValueError('pointer frozen tool drift '+path)
    source,deltas=transform(original,contract)
    if hashlib.sha256(source.encode()).hexdigest()!=contract['transformedRunnerSHA256'] or deltas!=contract['sourceDeltas']:raise ValueError('pointer concrete source drift')
    guard=common.load('pointer_runner_packaging',ROOT/'verification/android-coordinator-apk-packaging/apk_packaging.py')
    runner=ModuleType('mixer_private_pointer_runner');runner.__file__=str(HERE/'run.py')
    for name in ('_accepted_helper','_helper_path','_wifi_identity','_accepted_wifi_sha_globals'):setattr(runner,name,getattr(inherited,name))
    runner._packaging_check_path=guard.validate;runner._pointer_bind=lambda built:common.candidate(built,guard)
    runner._pointer_validate_native=validate_native
    runner._output=common.load('pointer_bounded_output',HERE/'bounded_output.py')
    runner._ADAPTATION=dict(inherited._ADAPTATION,pointerFixture={'contractSHA256':common.sha(CONTRACT),'wrapperSHA256':common.sha(__file__),'transformedRunnerSHA256':contract['transformedRunnerSHA256'],'sourceDeltas':deltas,'nativeRunAuthority':'explicit root dispatch only; host build is not native acceptance','directNativeCallbackCount':None})
    exec(compile(source,str(HERE/'transformed_runner.py'),'exec'),runner.__dict__)
    return runner,source,''.join(difflib.unified_diff(original.splitlines(keepends=True),source.splitlines(keepends=True),fromfile='accepted-packaging-concrete.py',tofile='private-pointer-concrete.py'))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--build',required=True,choices=['candidate-4']);parser.add_argument('--attempt',required=True);parser.add_argument('--execute-native',action='store_true');args=parser.parse_args()
    if not args.execute_native:parser.error('runtime NOT RUN; --execute-native requires explicit root dispatch')
    if not re.fullmatch(r'runtime-[1-9][0-9]*',args.attempt):parser.error('fresh runtime-N required')
    if (HERE/args.attempt).exists() or (HERE/args.attempt).is_symlink():parser.error('fresh output required; attempts immutable')
    runner,_,_=load_runner();runner.main()

if __name__=='__main__':main()
