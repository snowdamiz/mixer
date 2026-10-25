#!/usr/bin/env python3
"""Build the actual immutable FieldLog corpus as a full Swift static reactor.

Trusted local compiler/Node diagnostics only. No owned execution/admission,
production feature ABI, persistent state, device or GA qualification.
"""
import argparse
import datetime
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tarfile

sys.dont_write_bytecode = True
from support import ROOT, descriptors, observations, source_mapping
from qualification_support import CommandRecorder, clean_environment, digest, strict_json, tool_identity
from analyze import link_map, wasm

HERE = Path(__file__).resolve().parent
SWIFTC = Path('/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swiftc')
SDK = Path('/Users/andreyyurlov/.swiftpm/swift-sdks/swift-6.3.3-RELEASE_wasm.artifactbundle/swift-6.3.3-RELEASE_wasm/wasm32-unknown-wasip1')
DEVELOPER = Path('/Applications/Xcode_26.6.app/Contents/Developer')
REVISION = '1587d2d4f02ab2dad9914df97f878727dd622296'
ARCHIVE_SHA256 = '3f64fd8ff770a5f5e3a233d7170cccdc54c27ea0abb6a273948b260399e291eb'
CORPUS = ROOT / 'compiler/Fixtures/FieldLogCorpus/main.swift'


def identity(path):
    path = Path(path)
    return dict(path=str(path), resolvedPath=str(path.resolve()), bytes=path.stat().st_size, sha256=digest(path))


def source_manifest():
    paths = [HERE / name for name in ['run.py', 'support.py', 'test_support.py', 'FieldLogReactor.swift',
                                     'BoundaryCheck.swift', 'oracle.mjs']]
    paths += [CORPUS, ROOT / 'compiler/qualification_support.py',
              ROOT / 'compiler/experiments/profile-budget/analyze.py']
    return {str(path.relative_to(ROOT)): digest(path) for path in paths}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', default='2026-10-23-observed')
    parser.add_argument('--fieldlog', type=Path, default=Path('/Users/andreyyurlov/Documents/dev/fieldlog'))
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}', args.name, re.ASCII):
        parser.error('name must be a bounded ASCII path component')
    evidence, local = HERE / 'evidence' / args.name, HERE / 'local' / args.name
    evidence.mkdir(parents=True, exist_ok=False)
    local.mkdir(parents=True, exist_ok=False)
    env = clean_environment()
    env['DEVELOPER_DIR'] = str(DEVELOPER)
    (local / 'tmp').mkdir()
    env['TMPDIR'] = str(local / 'tmp')
    commands = []
    recorder = CommandRecorder(evidence, commands, ROOT)
    manifest = source_manifest()
    snapshot = local / 'diagnostic-sources'
    for name, expected_hash in manifest.items():
        path = snapshot / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, path)
        if digest(path) != expected_hash:
            raise ValueError('diagnostic source changed while retaining snapshot')
    wrapper = snapshot / (HERE / 'FieldLogReactor.swift').relative_to(ROOT)
    boundary_check = snapshot / (HERE / 'BoundaryCheck.swift').relative_to(ROOT)
    receipt = dict(schemaVersion=1, status='running', observedAtUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        authorization=False, independentReview=False,
        selectedAgent=dict(model='gpt-6.1-sol', reasoningEffort='xhigh'),
        scope='test-only real immutable FieldLog corpus compiled as one coherent full Swift static reactor; local trusted-tool/Node diagnostics',
        fullSwiftSDK=True, embeddedSwift=False, ownedVMExecution=False, deviceRun=False,
        sourceManifest=manifest,
        sourceManifestDigest=hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
        retainedDiagnosticSourceDirectory=str(snapshot),
        commands=commands, tools={},
        environment=dict(DEVELOPER_DIR=str(DEVELOPER), TMPDIR=env['TMPDIR'], ambientOverrides='removed by existing clean_environment'),
        timingScope='Mac command wall time during concurrent development, not startup/p95/RSS/performance qualification',
        limitations=[
            'Node WASI is a development oracle, not an owned runtime or OTA admission receipt',
            'Scalar status/export is test-only; it carries no public authority or production wire contract',
            'Each invocation constructs the same fresh local Workspace; repeated parity does not prove persistent feature state',
            'The corpus covers actual models, not complete FieldLog app/UI/effects/storage/async/actor behavior',
            'No physical iOS/Android, immutable published-package consumer, store, reviewer or GA gate receipt',
            'Memory extent is before/after linear memory only, not peak allocation, physical residency or RSS',
            'Installed compiler/SDK/platform tools remain trusted; selected hashes do not attest complete source-build correspondence or complete SDK supply chain',
            'Stripped optimized artifact has no usable source-debugging receipt; original-source map is a wrapper diagnostic only',
            'No changed VM ceilings, full eager VM decode, new dependency graph or runtime substitution'])

    def run(name, command, **kwargs):
        result = recorder.run(name, command, env=kwargs.pop('env', env), **kwargs)
        print(f'{name}: exit {commands[-1]["exitCode"]}', flush=True)
        return result

    def save(name, value):
        path = evidence / (name + '.json')
        path.write_text(json.dumps(value, indent=2) + '\n')
        return identity(path)

    def oracle(name, mode, artifact, count, expected):
        output = run(name, [node, '--no-warnings', HERE / 'oracle.mjs', mode, artifact])
        result = observations(output, count, expected)
        prefixes = [line.removeprefix('FIELDLOG_ORACLE ') for line in
                    (evidence / (name + '.stderr')).read_text().splitlines() if line.startswith('FIELDLOG_ORACLE ')]
        if len(prefixes) != 1:
            raise ValueError('missing or duplicate oracle control receipt')
        control = strict_json(prefixes[0])
        if control['authorization'] is not False or control['mode'] != mode or control['statuses'] != [0] * count:
            raise ValueError('oracle mode/status receipt differs')
        if control['initializationCalls'] != (1 if mode == 'reactor' else 0) or control['invocationCalls'] != count:
            raise ValueError('oracle initialization/invocation count differs')
        return dict(observations=result, control=control)

    try:
        if shutil.disk_usage(local).free < 1024 * 1024 * 1024:
            raise ValueError('less than 1 GiB free; refusing bounded compilation')
        git, node = [Path(shutil.which(name, path=env.get('PATH', os.defpath))) for name in ('git', 'node')]
        for name, path in [('swiftc', SWIFTC), ('swiftFrontend', SWIFTC.parent / 'swift-frontend'),
                           ('clang', SWIFTC.parent / 'clang'), ('wasm-ld', SWIFTC.parent / 'wasm-ld'),
                           ('node', node), ('git', git), ('python', Path(sys.executable))]:
            receipt['tools'][name] = tool_identity(path)
        receipt['versions'] = dict(swift=run('version-swift', [SWIFTC, '--version']).strip(),
            linker=run('version-linker', [SWIFTC.parent / 'wasm-ld', '--version']).strip(),
            node=run('version-node', [node, '--version']).strip(), python=sys.version)
        if '6.3.3-RELEASE' not in receipt['versions']['swift']:
            raise ValueError('expected official Swift 6.3.3 toolchain')
        receipt['host'] = run('host', ['/usr/bin/sw_vers']).strip()
        receipt['mixerRevision'] = run('mixer-revision', [git, 'rev-parse', 'HEAD']).strip()
        run('diagnostic-tests', [sys.executable, '-B', HERE / 'test_support.py'])
        revision = run('fieldlog-revision', [git, '-C', args.fieldlog, 'rev-parse', '--verify', REVISION + '^{commit}']).strip()
        if revision != REVISION:
            raise ValueError('immutable FieldLog revision mismatch')
        receipt['fieldlogRevision'] = revision
        receipt['fieldlogTree'] = run('fieldlog-tree', [git, '-C', args.fieldlog, 'rev-parse', REVISION + '^{tree}']).strip()
        archive = local / 'fieldlog-source.tar'
        run('fieldlog-export', [git, '-C', args.fieldlog, 'archive', '--format=tar', '--output=' + str(archive), REVISION])
        if digest(archive) != ARCHIVE_SHA256:
            raise ValueError('immutable source archive mismatch')
        source = local / 'fieldlog'
        source.mkdir()
        with tarfile.open(archive) as stream:
            stream.extractall(source, filter='data')
        model = source / 'Sources/FieldLogModels/Workspace.swift'
        if sorted((source / 'Sources/FieldLogModels').glob('*.swift')) != [model]:
            raise ValueError('unexpected actual model source set')
        corpus = local / 'main.swift'
        shutil.copyfile(CORPUS, corpus)
        receipt['inputs'] = dict(archive=identity(archive), model=identity(model), corpus=identity(corpus),
                                authoredWrapper=identity(HERE / 'FieldLogReactor.swift'), wrapper=identity(wrapper))
        receipt['exactSourceMap'] = source_mapping(corpus.read_bytes(), wrapper.read_bytes())
        prior = ROOT / 'verification/local/fieldlog-corpus-qualified/receipt.json'
        frozen = strict_json(prior.read_text())
        if frozen['fieldlogRevision'] != REVISION or frozen['sourceArchiveSHA256'] != ARCHIVE_SHA256:
            raise ValueError('prior immutable oracle identity mismatch')
        expected = frozen['modelObservations']
        receipt['priorOracleReceipt'] = identity(prior)
        receipt['expectedObservation'] = expected

        # Direct compiles avoid any new SwiftPM/dependency graph or existing .o reuse.
        native = local / 'native'
        native.mkdir()
        mac_sdk = (DEVELOPER / 'Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk').resolve()
        native_flags = ['-v', '-target', 'arm64-apple-macosx14.0', '-sdk', mac_sdk,
                        '-module-cache-path', native / 'cache', '-Osize', '-gnone', '-whole-module-optimization']
        native_object = native / 'FieldLogModels.o'
        run('native-model-compile', [SWIFTC, *native_flags, '-parse-as-library', '-module-name', 'FieldLogModels',
            '-emit-object', '-emit-module', '-emit-module-path', native / 'FieldLogModels.swiftmodule', model, '-o', native_object])
        native_command = native / 'fieldlog-command'
        run('native-command-build', [SWIFTC, *native_flags, '-I', native, native_object, corpus, '-o', native_command])
        native_result = observations(run('native-command-run', [native_command]), 1, expected)[0]
        native_boundary = native / 'boundary-check'
        run('native-boundary-build', [SWIFTC, *native_flags, '-parse-as-library', '-I', native, native_object,
            wrapper, boundary_check, '-o', native_boundary])
        native_repeated = observations(run('native-boundary-run', [native_boundary]), 2, native_result)
        receipt['native'] = dict(command=identity(native_command), modelObject=identity(native_object),
            modelModule=identity(native / 'FieldLogModels.swiftmodule'), boundaryCheck=identity(native_boundary),
            observation=native_result, repeatedWrapperObservations=native_repeated,
            thrownErrorBoundary='actual shared boundary helper returned 1 after one deliberately throwing Swift closure, then returned 0 for success')

        guest = local / 'wasm'
        guest.mkdir()
        resource = SDK / 'swift.xctoolchain/usr/lib/swift_static'
        flags = ['-v', '-target', 'wasm32-unknown-wasip1', '-sdk', SDK / 'WASI.sdk',
                 '-resource-dir', resource, '-module-cache-path', guest / 'cache', '-static-stdlib',
                 '-Osize', '-gnone', '-whole-module-optimization']
        linker = ['-Xclang-linker', '-resource-dir', '-Xclang-linker', resource / 'clang']
        model_object = guest / 'FieldLogModels.o'
        run('wasm-model-compile', [SWIFTC, *flags, '-parse-as-library', '-module-name', 'FieldLogModels',
            '-emit-object', '-emit-module', '-emit-module-path', guest / 'FieldLogModels.swiftmodule', model, '-o', model_object])
        command = guest / 'fieldlog-command.wasm'
        run('wasm-command-build', [SWIFTC, *flags, *linker, '-I', guest, model_object, corpus,
            '-Xlinker', '--strip-all', '-o', command])
        command_result = oracle('wasm-command-oracle', 'command', command, 1, native_result)
        reactor = guest / 'fieldlog-reactor.wasm'
        link = guest / 'reactor.map'
        why = guest / 'reactor.why-extract.tsv'
        run('wasm-reactor-build', [SWIFTC, *flags, *linker, '-parse-as-library', '-I', guest,
            model_object, wrapper, '-Xclang-linker', '-mexec-model=reactor',
            '-Xlinker', '--export=mixer_fieldlog_corpus_v1', '-Xlinker', '--strip-all',
            '-Xlinker', '--Map=' + str(link), '-Xlinker', '--why-extract=' + str(why), '-o', reactor])
        reactor_identity = identity(reactor)
        receipt['candidateArtifactsBeforeOracle'] = dict(command=identity(command), reactor=reactor_identity,
            modelObject=identity(model_object), modelModule=identity(guest / 'FieldLogModels.swiftmodule'))
        descriptor = descriptors(reactor.read_bytes())
        exports = {row['name']: row for row in descriptor['exports']}
        if set(exports) != {'memory', '_initialize', 'mixer_fieldlog_corpus_v1'} or descriptor['startFunction'] is not None:
            raise ValueError('reactor export/start descriptor differs from frozen test interface')
        if exports['_initialize']['signature'] != dict(parameters=[], results=[]) or exports['mixer_fieldlog_corpus_v1']['signature'] != dict(parameters=[], results=['i32']):
            raise ValueError('reactor exact export signature differs')
        reactor_result = oracle('wasm-reactor-oracle', 'reactor', reactor, 2, native_result)
        if reactor_result['control']['exports'] != [dict(name=row['name'], kind=row['kind']) for row in descriptor['exports']]:
            raise ValueError('Node and original descriptor export inventories differ')
        if reactor_result['control']['imports'] != [dict(module=row['module'], name=row['name'], kind='function') for row in descriptor['imports']]:
            raise ValueError('Node and original descriptor import inventories differ')
        receipt['parity'] = dict(completeObjectEquality=True, nativeVersusCommand=True,
                                nativeVersusReactor=[True, True], command=command_result, reactor=reactor_result)
        receipt['descriptors'] = save('descriptors', descriptor)
        structure = wasm(reactor.read_bytes())
        receipt['structure'] = save('structure', structure)
        receipt['sourceDebugging'] = dict(qualified=False,
            customSections=[row['name'] for row in structure['sections'] if row['id'] == 0],
            flags=['-Osize', '-gnone', '--strip-all'],
            scope='exact wrapper/body byte mapping is retained; no DWARF/source-map/debugger usability qualification')
        attribution = link_map(link.read_text())
        receipt['linkAttribution'] = save('link-attribution', attribution)
        receipt['linkMap'] = identity(link)
        receipt['whyExtract'] = identity(why)
        receipt['guestBuild'] = dict(modelObject=identity(model_object), modelModule=identity(guest / 'FieldLogModels.swiftmodule'),
            commandArtifact=identity(command), reactorArtifact=reactor_identity,
            fullSwift=True, embeddedSwift=False, staticReactor=True, newPackageGraph=False, reusedModelObject=False)

        compressed = guest / 'fieldlog-reactor.wasm.gz'
        with reactor.open('rb') as src, compressed.open('wb') as dest:
            with gzip.GzipFile(fileobj=dest, mode='wb', filename='', compresslevel=9, mtime=0) as zipped:
                shutil.copyfileobj(src, zipped)
        receipt['size'] = dict(scope='one complete full Swift model reactor, not p95 production corpus',
            rawBytes=reactor.stat().st_size, gzip9Mtime0=identity(compressed), completeArtifactBudgetBytes=3_145_728,
            completeArtifactBudgetPassed=compressed.stat().st_size <= 3_145_728)

        tools_dir = local / 'tools'
        tools_dir.mkdir()
        original_vm = ROOT / 'vm/target/release/mixer-vm'
        vm_before = tool_identity(original_vm)
        vm = tools_dir / 'mixer-vm'
        shutil.copyfile(original_vm, vm)
        vm.chmod(0o500)
        if digest(vm) != vm_before['sha256'] or tool_identity(original_vm) != vm_before:
            raise ValueError('owned VM changed during snapshot')
        receipt['tools']['ownedVM'] = dict(source=vm_before, snapshot=tool_identity(vm), sourceBuildCorrespondenceAttested=False)
        strict = strict_json(run('owned-strict-validation', [vm, 'validate', reactor], expected=(2,)))
        inventory = strict_json(run('owned-table-memory-inventory', [vm, '--profile', 'mixer-table-memory-v3', 'inventory', reactor], expected=(2,)))
        if strict['valid'] or strict['profile'] != 'mixer-integer-v1' or strict['error']['message'] != 'module byte limit exceeded':
            raise ValueError('original strict-profile rejection changed')
        if inventory['valid'] or not inventory['inventory_complete']:
            raise ValueError('unexpected inventory admission/incompleteness')
        receipt['ownedStrictRejection'] = strict
        receipt['ownedDiagnosticInventory'] = inventory
        receipt['nesting'] = dict(maximum=None, scope='not measured: existing bounded per-body tool is pinned to old command artifact size; current general inventory does not expose nesting; no estimate used as evidence')

        sdk_inputs = [SDK.parent.parent / 'info.json', SDK / 'swift-sdk.json', SDK / 'toolset.json',
            SDK / 'WASI.sdk/include/wasm32-wasip1/wasi/api.h', SDK / 'WASI.sdk/lib/wasm32-wasip1/crt1-reactor.o',
            resource / 'wasi/wasm32/swiftrt.o', resource / 'wasi/static-executable-args.lnk',
            resource / 'clang/lib/wasip1/libclang_rt.builtins-wasm32.a', mac_sdk / 'SDKSettings.json']
        for item in attribution['archives_and_objects']:
            path = Path(item['input'])
            if path.is_file():
                sdk_inputs.append(path)
        receipt['selectedSDKAndLinkerInputs'] = [identity(path) for path in sorted(set(sdk_inputs))]
        receipt['sdkScope'] = 'official metadata, reactor startup, runtime objects, compiler-rt and actual map-attributed archives; not complete compiler-interface/header provenance or supply-chain attestation'

        if source_manifest() != manifest or identity(reactor) != reactor_identity:
            raise ValueError('source or reactor changed during run')
        if identity(model) != receipt['inputs']['model'] or identity(corpus) != receipt['inputs']['corpus']:
            raise ValueError('immutable qualification inputs changed during run')
        for name, item in receipt['tools'].items():
            if name != 'ownedVM' and tool_identity(item['path']) != item:
                raise ValueError('installed executable changed during run: ' + name)
        if any(digest(snapshot / path) != expected_hash for path, expected_hash in manifest.items()):
            raise ValueError('retained diagnostic source snapshot changed during run')
        receipt['status'] = 'full-swift-fieldlog-reactor-model-parity-passed; owned-runtime-and-product-gates-open'
    except Exception as error:
        receipt['status'] = 'failed'
        receipt['failure'] = str(error)
        raise
    finally:
        (evidence / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(dict(status=receipt['status'], evidence=str(evidence), rawBytes=receipt['size']['rawBytes'],
                          gzipBytes=receipt['size']['gzip9Mtime0']['bytes'])))


if __name__ == '__main__':
    main()
