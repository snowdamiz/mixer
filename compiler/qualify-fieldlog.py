#!/usr/bin/env python3
"""Compile an immutable FieldLog revision with the full official Swift SDK.

This is compiler/model evidence. Node is a development oracle, never a product
runtime. Owned VM rejection remains an open acceptance gate in every receipt.
"""
from pathlib import Path
import argparse, hashlib, json, os, shutil, subprocess, tarfile, time

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--fieldlog', required=True, type=Path)
parser.add_argument('--revision', required=True)
parser.add_argument('--output', required=True, type=Path)
parser.add_argument('--cross-swift', required=True, type=Path)
parser.add_argument('--developer-dir', required=True, type=Path)
parser.add_argument('--swift-sdks', type=Path, default=Path.home()/'.swiftpm/swift-sdks')
parser.add_argument('--wasm-sdk', default='swift-6.3.3-RELEASE_wasm')
parser.add_argument('--adb', type=Path)
parser.add_argument('--device')
parser.add_argument('--libcxx', type=Path)
args = parser.parse_args()
if bool(args.device) != bool(args.adb) or bool(args.device) != bool(args.libcxx):
    parser.error('--device, --adb and --libcxx must be provided together')
output = args.output.resolve()
output.mkdir(parents=True, exist_ok=False)
commands = []

def run(name, command, *, env=None, expected=(0,), timeout=300):
    command = [str(x) for x in command]
    started = time.monotonic()
    result = subprocess.run(command, text=True, capture_output=True, env=env, timeout=timeout, cwd=ROOT)
    (output/(name+'.stdout')).write_text(result.stdout)
    (output/(name+'.stderr')).write_text(result.stderr)
    commands.append({'name':name, 'command':command, 'exitCode':result.returncode,
                     'elapsedSeconds':round(time.monotonic()-started,3)})
    if result.returncode not in expected:
        raise RuntimeError(f'{name} failed ({result.returncode}); see {output/name}.stderr')
    return result.stdout

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def artifact(path):
    return {'path':str(path.relative_to(output)), 'bytes':path.stat().st_size, 'sha256':digest(path)}

receipt = {'schema':1, 'status':'running', 'scope':'actual FieldLog model compiler/oracle qualification only',
           'ownedSwiftExecutionQualified':False, 'deviceOTAQualified':False, 'commands':commands}
try:
    revision = run('source-revision',['git','-C',args.fieldlog.resolve(),'rev-parse','--verify','--end-of-options',args.revision+'^{commit}']).strip()
    if len(revision) != 40 or any(c not in '0123456789abcdef' for c in revision):
        raise ValueError('Expected a full Git commit identity')
    receipt['fieldlogRevision'] = revision
    archive = output/'fieldlog-source.tar'
    run('source-export',['git','-C',args.fieldlog.resolve(),'archive','--format=tar','--output='+str(archive),revision])
    source = output/'fieldlog'; source.mkdir()
    with tarfile.open(archive) as tar: tar.extractall(source, filter='data')
    receipt['sourceArchiveSHA256'] = digest(archive)
    harness = output/'Sources/FieldLogCorpus'; harness.mkdir(parents=True)
    shutil.copyfile(ROOT/'compiler/Fixtures/FieldLogCorpus/main.swift',harness/'main.swift')
    receipt['harnessSHA256'] = digest(harness/'main.swift')
    (output/'Package.swift').write_text('''// swift-tools-version: 6.0
import PackageDescription
let package = Package(name: "FieldLogCorpus", platforms: [.macOS(.v14)],
    products: [.executable(name: "fieldlog-corpus", targets: ["FieldLogCorpus"])],
    dependencies: [.package(path: "fieldlog")],
    targets: [.executableTarget(name: "FieldLogCorpus", dependencies: [.product(name: "FieldLogModels", package: "fieldlog")])])
''')
    env = dict(os.environ, DEVELOPER_DIR=str(args.developer_dir.resolve()))
    receipt['toolVersions'] = {
        'nativeSwift':run('native-version',['swift','--version']).strip(),
        'crossSwift':run('cross-version',[args.cross_swift,'--version'],env=env).strip(),
        'node':run('node-version',['node','--version']).strip()}
    run('native-build',['swift','build','--package-path',output,'-c','release','-j','4'])
    native = json.loads(run('native-run',[output/'.build/release/fieldlog-corpus']))
    run('wasm-build',[args.cross_swift,'build','--package-path',output,'--scratch-path',output/'.build/wasm',
                      '--swift-sdks-path',args.swift_sdks,'--swift-sdk',args.wasm_sdk,'-c','release','-j','4'],env=env)
    wasm = output/'.build/wasm/wasm32-unknown-wasip1/release/fieldlog-corpus.wasm'
    oracle = '''import {WASI} from 'node:wasi'; import {readFile} from 'node:fs/promises';
const wasi=new WASI({version:'preview1',args:['fieldlog-corpus'],env:{},preopens:{},returnOnExit:true});
const module=await WebAssembly.compile(await readFile(process.argv[1]));
const instance=await WebAssembly.instantiate(module,wasi.getImportObject());
process.exitCode=wasi.start(instance);'''
    wasm_result = json.loads(run('wasm-oracle',['node','--input-type=module','-e',oracle,wasm]))
    if native != wasm_result: raise AssertionError('Native/Wasm model observations differ')
    run('android-build',[args.cross_swift,'build','--package-path',output,'--scratch-path',output/'.build/android',
                        '--swift-sdks-path',args.swift_sdks,'--swift-sdk','aarch64-unknown-linux-android28',
                        '--static-swift-stdlib','-c','release','-j','4'],env=env)
    android = output/'.build/android/aarch64-unknown-linux-android28/release/fieldlog-corpus'
    receipt['artifacts'] = {'wasm':artifact(wasm), 'android':artifact(android)}
    receipt['modelObservations'] = native
    receipt['nativeVersusWasmOracle'] = 'passed'
    receipt['androidExecution'] = 'not-run'
    if args.device:
        remote = '/data/local/tmp/mixer-fieldlog-corpus-'+revision[:12]
        adb = [args.adb,'-s',args.device]
        run('device-mkdir',adb+['shell','mkdir','-p',remote])
        run('device-push',adb+['push',android,args.libcxx,remote+'/'])
        run('device-chmod',adb+['shell','chmod','700',remote+'/fieldlog-corpus'])
        actual = json.loads(run('android-run',adb+['shell','env','LD_LIBRARY_PATH='+remote,remote+'/fieldlog-corpus']))
        if actual != native: raise AssertionError('Physical Android/native model observations differ')
        receipt['androidExecution'] = 'passed'
        receipt['androidDevice'] = {key:run('device-'+key,adb+['shell','getprop',key]).strip()
                                    for key in ['ro.product.model','ro.build.version.release','ro.build.fingerprint']}
    vm = ROOT/'vm/target/release/mixer-vm'
    inventory = json.loads(run('owned-vm-inventory',[vm,'inventory',wasm],expected=(0,2)))
    validation = json.loads(run('owned-vm-validation',[vm,'validate',wasm],expected=(0,2)))
    receipt['ownedVMValidation'] = validation
    receipt['opcodeInventoryFile'] = 'owned-vm-inventory.stdout'
    receipt['status'] = 'compiler-model-checks-passed' if args.device else 'compiler-model-checks-passed-android-execution-not-run'
    receipt['limitations'] = ['No owned full Swift execution receipt', 'No UI, effect, storage or OTA qualification',
                              'Source snapshot is for diagnostics, not immutable published SDK adoption',
                              'Timing is command wall time, not an app performance measurement']
except Exception as error:
    receipt['status'] = 'failed'; receipt['failure'] = str(error)
    raise
finally:
    (output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
