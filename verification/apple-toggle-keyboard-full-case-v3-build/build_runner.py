#!/usr/bin/env python3
"""One selected generic runner compile; no instance/frontend/runtime operations.

This independent recorder never imports a historical evidence collector.
"""
import datetime
import hashlib
import json
import os
import pathlib
import plistlib
import signal
import stat
import subprocess
import sys
import tarfile
import time

BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[1]
PREP = ROOT / 'verification/apple-toggle-keyboard-full-case-preparation-v3'
REVIEW = ROOT / 'verification/apple-toggle-keyboard-full-case-independent-review-v3'
SELECT = ROOT / 'verification/apple-toggle-keyboard-full-case-root-review/v3-source'
DEVELOPER = pathlib.Path('/Applications/Xcode_26.6.app/Contents/Developer')
BUILD = PREP / 'build'
PRODUCTS = BUILD / 'Build/Products'
PINS = {
    'producer': '2d600f0289324591cfab82b3ff3d0d987dcdfce9e081a0ff2571d47d6c844039',
    'review': '5a3e441332174e477527943b0d23f3eb66db952c8a0b8d9d0bc688904ed20c9c',
    'acceptance': '5759e23e8d9b37ae775eea1c62cbe7d5b34b89712489eda697bd6d4bd7d62ede',
    'selection': '682ef08ec1d586322fc08a0373ba3411ba6831b3294869634220c2a828a1633a',
    'proposal': 'ffdd848d96ea96c3ce5aa7bd812727b111d877907a2b562a683d534fa5b59733',
}


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def absent_canonical(path):
    require(path.resolve() == path and not os.path.lexists(path), 'Fresh absent canonical destination required: ' + str(path))


def file_record(path):
    info = path.lstat()
    record = {'mode': stat.S_IMODE(info.st_mode)}
    if stat.S_ISREG(info.st_mode):
        record.update(kind='file', bytes=info.st_size, sha256=sha(path))
    elif stat.S_ISDIR(info.st_mode):
        record.update(kind='directory')
    elif stat.S_ISLNK(info.st_mode):
        record.update(kind='symlink', target=os.readlink(path))
    else:
        raise ValueError('Special file refused: ' + str(path))
    return record


def tree(folder):
    require(folder.is_dir() and not folder.is_symlink() and folder.resolve() == folder, 'Canonical real tree required')
    result = {'.': file_record(folder)}
    for directory, dirs, files in os.walk(folder, followlinks=False):
        for name in sorted(dirs + files):
            path = pathlib.Path(directory) / name
            row = file_record(path)
            if row['kind'] == 'symlink':
                require(not pathlib.Path(row['target']).is_absolute() and path.resolve().is_relative_to(folder), 'Escaping product symlink refused')
            result[str(path.relative_to(folder))] = row
    return dict(sorted(result.items()))


def bound_files(mapping):
    result = {}
    for name, expected in sorted(mapping.items()):
        path = pathlib.Path(name) if name.startswith('/') else ROOT / name
        require(path.is_file(), 'Bound file absent: ' + name)
        require(sha(path) == (expected['sha256'] if isinstance(expected, dict) else expected), 'Bound file changed: ' + name)
        row = file_record(path)
        if row['kind'] == 'symlink':
            row.update(resolved=str(path.resolve()), resolvedMode=stat.S_IMODE(path.stat().st_mode), sha256=sha(path))
        result[name] = row
    return result


def selected_argv():
    return [str(DEVELOPER / 'usr/bin/xcodebuild'), 'build-for-testing', '-project',
            str(PREP / 'harness/MixerToggleUITests.xcodeproj'), '-scheme', 'MixerToggleUITests',
            '-sdk', 'iphonesimulator', '-destination', 'generic/platform=iOS Simulator',
            '-derivedDataPath', str(BUILD), 'CODE_SIGNING_ALLOWED=NO', 'ARCHS=arm64']


def revalidate():
    paths = {'producer': PREP / 'packet-seal.json', 'review': REVIEW / 'review-seal.json',
             'acceptance': SELECT / 'acceptance.json', 'selection': SELECT / 'compile-selection.json',
             'proposal': PREP / 'compile-proposal.json'}
    for name, path in paths.items():
        require(path.is_file() and not path.is_symlink() and sha(path) == PINS[name], 'Selected ' + name + ' changed')
    acceptance = read(paths['acceptance'])
    selection = read(paths['selection'])
    proposal = read(paths['proposal'])
    require(acceptance['sourceAccepted'] is True and acceptance['nativeAccepted'] is False, 'Exact source-only acceptance required')
    require(acceptance['producerSealSHA256'] == PINS['producer'] and acceptance['reviewSealSHA256'] == PINS['review'], 'Acceptance seal mismatch')
    require(selection['sourceAcceptanceSHA256'] == PINS['acceptance'] and selection['proposalSHA256'] == PINS['proposal'], 'Selection input mismatch')
    require(selection['proposal'] == proposal and proposal['argv'] == selected_argv() and proposal['cwd'] == str(ROOT), 'Exact generic build selection required')
    require(selection['maxAttempts'] == 1 and proposal['timeoutSeconds'] == 180, 'One 180-second attempt required')
    for field in ['nativeRuntimeSelected', 'appRebuildSelected', 'nativeInstanceQuerySelected']:
        require(selection[field] is False, 'Unselected native action: ' + field)
    producer, review = read(paths['producer']), read(paths['review'])
    require(len(producer['files']) == 80 and len(review['files']) == 117, 'Selected seal file count differs')
    source = {'producer': bound_files(producer['files']), 'review': bound_files(review['files']),
              'inputBindings': bound_files(read(PREP / 'input-bindings.json')),
              'selectionFiles': {str(path.relative_to(ROOT)): file_record(path) for path in paths.values()},
              'runner': tree(PREP / 'harness')}
    runner = {name: row['sha256'] for name, row in source['runner'].items() if row['kind'] == 'file'}
    require(digest(runner) == '946ab559edadd5352912d5747629256a6287d9ca892d5aad0fbd0a7ce4d81e2c', 'Exact runner source tree differs')
    require(len(source['inputBindings']) == 2537, 'Input count differs')
    return source


def tool_metadata():
    toolchain = DEVELOPER / 'Toolchains/XcodeDefault.xctoolchain'
    sdk = DEVELOPER / 'Platforms/iPhoneSimulator.platform/Developer/SDKs/iPhoneSimulator26.5.sdk'
    paths = [DEVELOPER.parent / 'Info.plist', toolchain / 'ToolchainInfo.plist', sdk / 'SDKSettings.json',
             DEVELOPER / 'usr/bin/xcodebuild', pathlib.Path('/usr/bin/xcrun'), pathlib.Path('/usr/bin/codesign'),
             pathlib.Path(sys.executable).resolve()]
    paths += [toolchain / 'usr/bin' / name for name in ['swiftc', 'swift-frontend', 'clang', 'ld', 'dsymutil', 'lipo']]
    records = {str(path): {**file_record(path), 'resolvedSHA256': sha(path)} for path in paths}
    info = plistlib.loads((DEVELOPER.parent / 'Info.plist').read_bytes())
    tc = plistlib.loads((toolchain / 'ToolchainInfo.plist').read_bytes())
    settings = read(sdk / 'SDKSettings.json')
    return {'files': records, 'XcodeVersion': info['CFBundleShortVersionString'], 'XcodeBundleBuild': info['CFBundleVersion'],
            'toolchainMetadata': tc, 'SDKCanonicalName': settings['CanonicalName'], 'SDKVersion': settings['Version'],
            'pythonVersion': sys.version, 'pythonExecutable': str(pathlib.Path(sys.executable).resolve()),
            'versionObservation': 'Fresh bundle/toolchain/SDK metadata; compiler-dispatched version probes retained in raw build stdout. No separate native version command.'}


def archive_tree(folder, manifest, target):
    require(tree(folder) == manifest, 'Product changed before archive')
    with target.open('xb') as raw:
        with tarfile.open(fileobj=raw, mode='w:gz', dereference=False) as archive:
            for name, row in manifest.items():
                info = tarfile.TarInfo(name)
                info.mode = row['mode']
                info.mtime = 0
                if row['kind'] == 'file':
                    info.size = row['bytes']
                    with (folder / name).open('rb') as stream:
                        archive.addfile(info, stream)
                elif row['kind'] == 'directory':
                    info.type = tarfile.DIRTYPE
                    archive.addfile(info)
                elif row['kind'] == 'symlink':
                    info.type = tarfile.SYMTYPE
                    info.linkname = row['target']
                    archive.addfile(info)
    verify_archive(target, manifest)
    require(tree(folder) == manifest, 'Product changed during archive')


def verify_archive(target, manifest):
    observed = {}
    with tarfile.open(target, mode='r:gz') as archive:
        for member in archive.getmembers():
            name = member.name.rstrip('/') or '.'
            require(name == '.' or (not name.startswith('/') and '..' not in pathlib.PurePosixPath(name).parts), 'Unsafe archive name')
            require(name not in observed, 'Duplicate archive entry')
            row = {'mode': member.mode}
            if member.isfile():
                stream = archive.extractfile(member)
                payload = stream.read()
                require(len(payload) == member.size, 'Archive size differs')
                row.update(kind='file', bytes=member.size, sha256=hashlib.sha256(payload).hexdigest())
            elif member.isdir():
                row.update(kind='directory')
            elif member.issym():
                row.update(kind='symlink', target=member.linkname)
            else:
                raise ValueError('Unsupported archive entry')
            observed[name] = row
    require(observed == manifest, 'Archive bytes, modes, or membership differ')
    return observed


def compile_once():
    require(not (BASE / 'attempt-started.json').exists(), 'Single build attempt already spent')
    before = revalidate()
    tools = tool_metadata()
    absent_canonical(BUILD)
    save(BASE / 'source-before.json', before)
    save(BASE / 'tools-before.json', tools)
    temporary = BASE / 'compiler-tmp'
    absent_canonical(temporary)
    temporary.mkdir(mode=0o700)
    env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'HOME': str(pathlib.Path.home()),
           'USER': os.environ['USER'], 'LOGNAME': os.environ['LOGNAME'], 'TMPDIR': str(temporary) + '/',
           'DEVELOPER_DIR': str(DEVELOPER), 'PYTHONDONTWRITEBYTECODE': '1', 'LANG': 'en_US.UTF-8', 'LC_ALL': 'en_US.UTF-8'}
    command = dict(schema=1, observedUTC=utc(), argv=selected_argv(), cwd=str(ROOT), environment=env,
                   timeoutSeconds=180, attempt=1, maxAttempts=1, sourceRevision=read(SELECT / 'acceptance.json')['sourceRevision'],
                   revisionObservation='Root acceptance metadata; no Git query', recorderSHA256=sha(pathlib.Path(__file__)),
                   nativeRuntimeSelected=False, applicationRebuildSelected=False, nativeInstanceQuerySelected=False)
    # The exclusive persistent marker spends this lane's only attempt before process creation.
    save(BASE / 'attempt-started.json', command)
    started = time.monotonic()
    failure = None
    process = None
    with (BASE / 'compiler.stdout').open('xb') as stdout, (BASE / 'compiler.stderr').open('xb') as stderr:
        try:
            process = subprocess.Popen(command['argv'], cwd=ROOT, env=env, stdout=stdout, stderr=stderr, start_new_session=True)
            command['pid'] = process.pid
            try:
                process.wait(timeout=180)
            except subprocess.TimeoutExpired:
                command['timedOut'] = True
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
                raise
        except BaseException as error:
            failure = error
            command['failure'] = {'type': type(error).__name__, 'message': str(error)}
        finally:
            command.update(exitCode=process.returncode if process else None, elapsedSeconds=time.monotonic()-started,
                           finishedUTC=utc(), stdoutSHA256=sha(BASE / 'compiler.stdout'), stderrSHA256=sha(BASE / 'compiler.stderr'))
            save(BASE / 'command.json', command)
    after = revalidate()
    save(BASE / 'source-after.json', after)
    after_tools = tool_metadata()
    save(BASE / 'tools-after.json', after_tools)
    require(before == after, 'Accepted source/input modes or bytes changed during compile')
    require(tools == after_tools, 'Tools changed during compile')
    if failure is not None:
        raise failure
    require(process.returncode == 0, 'Compiler failed; no retry selected')
    products = tree(PRODUCTS)
    configurations = [name for name, row in products.items() if row['kind'] == 'file' and name.endswith('.xctestrun')]
    require(len(configurations) == 1, 'One exact runner xctestrun required')
    configuration = plistlib.loads((PRODUCTS / configurations[0]).read_bytes())
    require('MixerToggleUITests' in configuration, 'Runner xctestrun target absent')
    archive = BASE / 'test-runner-products.tar.gz'
    archive_tree(PRODUCTS, products, archive)
    manifest = dict(schema='mixer.apple-toggle.keyboard-full-case-v3-build-products.1', observedUTC=utc(),
                    productsPath=str(PRODUCTS), products=products, productTreeSHA256=digest(products),
                    productArchiveSHA256=sha(archive), archiveManifestVerified=True,
                    archiveVerification='Every file payload, byte count, mode, directory, symlink target and member checked without extraction',
                    sourceBeforeSHA256=sha(BASE / 'source-before.json'), sourceAfterSHA256=sha(BASE / 'source-after.json'),
                    toolsBeforeSHA256=sha(BASE / 'tools-before.json'), toolsAfterSHA256=sha(BASE / 'tools-after.json'),
                    commandSHA256=sha(BASE / 'command.json'), xctestrun=configurations[0],
                    xctestrunConfiguration=configuration, genericRunnerCompiled=True, applicationCasesExecuted=0,
                    nativeRuntimeExecuted=False, nativeAcceptancePending=True, physicalPhones='disconnected-deferred', carrierAccepted=False, gaAccepted=False)
    save(BASE / 'build-products-manifest.json', manifest)
    print(json.dumps({'status': 'one-selected-generic-runner-build-passed', 'elapsedSeconds': command['elapsedSeconds'],
                      'productTreeSHA256': manifest['productTreeSHA256'], 'productArchiveSHA256': manifest['productArchiveSHA256']}))


if __name__ == '__main__':
    require(sys.argv[1:] == ['compile-selected-once'], 'Only explicit selected single compile action is available')
    compile_once()
