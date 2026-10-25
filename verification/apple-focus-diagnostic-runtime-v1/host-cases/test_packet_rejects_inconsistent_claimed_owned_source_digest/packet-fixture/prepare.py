#!/usr/bin/env python3
"""Prepare a byte-bound diagnostic packet. Default actions never run native tools."""
import argparse
import datetime
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import signal
import stat
import sys
import tarfile

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
V3 = ROOT / 'verification/apple-toggle-keyboard-full-case-preparation-v3'
BUILD = ROOT / 'verification/apple-toggle-keyboard-focus-diagnostic-v1-build'
SCRATCH = BASE / 'scratch'
PRODUCT_SHA = '5ff6e5b7a7a6c11b251e9841a63c6c3afe669f42cf62679f8d7995f985e20bba'
SIX_SHA = '91e86b048aa920917e1882f062ef32cea278e23a4529b973e75179c27e819969'
OBSERVER_CLOSURE = '34361470e25311398bdd0f4b44acace06a4a181b9a61c937a60bb4c27fe8658a'
OBSERVER_SHA = 'c712724207fb5d327da0f6367e7a7f598494b3bb43f8b25fdfefcf94d3aefa88'
OBSERVER_RECEIPT_SHA = '0431d45ed1e02689769aeefcb0ffb92ec223ca26381599b100fde0e54362436a'
METHODS = ['test000PublicSettingsFullKeyboardAccess', 'test010EnabledFromOff']
CASE = 'keyboard-enabled-off'
OWNED_SOURCE_NAMES = ('prepare.py', 'join_support.py', 'test_join.py', 'verify_host.py')


def require(value, message):
    if not value:
        raise ValueError(message)


def stable(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    path.write_bytes(stable(value))


def file_row(path):
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and path.resolve() == path and info.st_nlink == 1,
            'Noncanonical regular input: ' + str(path))
    data = path.read_bytes()
    return {'kind': 'file', 'bytes': len(data), 'mode': stat.S_IMODE(info.st_mode), 'sha256': sha(data)}


def safe_name(name):
    path = PurePosixPath(name)
    require(name and not path.is_absolute() and '..' not in path.parts and str(path) == name,
            'Unsafe archive name: ' + name)
    return path


def ancestors(names):
    return {str(parent) for name in names for parent in PurePosixPath(name).parents if str(parent) != '.'}


def archive_payload(path, expected, archive_sha, prefix=''):
    """Validate all bytes/types/modes and exact implied directory set before writes."""
    require(file_row(path)['sha256'] == archive_sha, 'Archive hash changed')
    prefixed = {prefix + name: item for name, item in expected.items()}
    directories = ancestors(prefixed)
    values, seen = {}, set()
    with tarfile.open(path, 'r:gz') as archive:
        require(len(archive.getmembers()) <= 256, 'Archive entry bound exceeded')
        for member in archive:
            safe_name(member.name)
            require(member.name not in seen, 'Duplicate archive entry')
            seen.add(member.name)
            if member.isdir():
                require(member.name in directories and member.mode == 0o755 and member.size == 0,
                        'Unexpected archive directory or mode')
                continue
            require(member.name in prefixed, 'Unmanifested archive payload')
            item = prefixed[member.name]
            require(member.mode == item['mode'], 'Archive payload mode changed')
            if item['kind'] == 'symlink':
                target = PurePosixPath(member.linkname)
                require(member.issym() and not target.is_absolute() and '..' not in target.parts
                        and member.linkname == item['target'], 'Unsafe or changed archive symlink')
                values[member.name.removeprefix(prefix)] = None
            else:
                require(item['kind'] == 'file' and member.isfile() and member.size == item['bytes'],
                        'Archive payload type/size changed')
                require(member.size <= 32 * 1024 * 1024, 'Individual archive payload too large')
                data = archive.extractfile(member).read(member.size + 1)
                require(len(data) == item['bytes'] and sha(data) == item['sha256'], 'Archive payload changed')
                values[member.name.removeprefix(prefix)] = data
    require(seen == set(prefixed) | directories, 'Archive entries incomplete')
    return values


def tree(path, strict_directories=True):
    info = path.lstat()
    require(path.resolve() == path and stat.S_ISDIR(info.st_mode)
            and (not strict_directories or stat.S_IMODE(info.st_mode) == 0o755),
            'Unexpected materialized root directory')
    rows, directories = {}, set()
    for item in sorted(path.rglob('*')):
        if item.is_symlink():
            rows[str(item.relative_to(path))] = {'kind': 'symlink', 'target': os.readlink(item),
                                               'mode': stat.S_IMODE(item.lstat().st_mode)}
        elif item.is_file():
            rows[str(item.relative_to(path))] = file_row(item)
        else:
            require(item.is_dir() and (not strict_directories or stat.S_IMODE(item.stat().st_mode) == 0o755),
                    'Unexpected materialized directory')
            directories.add(str(item.relative_to(path)))
    if strict_directories:
        require(directories == ancestors(rows), 'Materialized directory set differs from exact implied directories')
    return rows


def archive_sources(path, source, manifest):
    """Create a deterministic source-only tar; no build product is duplicated."""
    require(not path.exists() and tree(source) == manifest, 'Fresh archive and exact selected source required')
    directories = ancestors({'selected/' + name for name in manifest})
    with path.open('xb') as output, gzip.GzipFile(filename='', mode='wb', fileobj=output, mtime=0) as compressed, tarfile.open(fileobj=compressed, mode='w') as archive:
        for name in sorted(directories):
            info = tarfile.TarInfo(name); info.mode = 0o755; info.type = tarfile.DIRTYPE
            archive.addfile(info)
        for name, expected in sorted(manifest.items()):
            info = tarfile.TarInfo('selected/' + name); info.mode = expected['mode']
            if expected['kind'] == 'symlink':
                info.type = tarfile.SYMTYPE; info.linkname = expected['target']; archive.addfile(info)
            else:
                value = (source / name).read_bytes()
                require(sha(value) == expected['sha256'] and len(value) == expected['bytes'], 'Selected source changed during archive')
                info.size = len(value); archive.addfile(info, io.BytesIO(value))
    row = file_row(path)
    archive_payload(path, manifest, row['sha256'], 'selected/')
    return {'schema': 1, 'scope': 'Selected runtime source and selection metadata only; no compiled products',
            'files': manifest, 'treeSHA256': sha(stable(manifest)), 'directoryMode': 0o755,
            'directories': sorted(directories), 'archive': row}


def materialize(destination, manifest, payload):
    require(not destination.exists() and destination.resolve() == destination, 'Fresh owned destination required')
    destination.mkdir(parents=True, mode=0o755)
    destination.chmod(0o755)
    for name in sorted(ancestors(manifest), key=lambda value: (len(PurePosixPath(value).parts), value)):
        target = destination / name
        target.mkdir(mode=0o755)
        target.chmod(0o755)
    for name, row in manifest.items():
        target = destination / name
        if row['kind'] == 'symlink':
            target.symlink_to(row['target'])
        else:
            target.write_bytes(payload[name])
            target.chmod(row['mode'])
    require(tree(destination) == manifest, 'Materialized tree mismatch')


def once(value, old, new):
    require(value.count(old) == 1, 'Derivation anchor missing/ambiguous: ' + old[:80])
    return value.replace(old, new, 1)


def derive_runtime(originals, overlays):
    result = dict(originals)
    for name in ['keyboard_bridge.py', 'focus_diagnostic.py']:
        result['inputs/runtime/verification/apple-toggle-keyboard-focus/' + name] = overlays[
            'runtime/verification/apple-toggle-keyboard-focus/' + name]
    def edit(name, old, new):
        result[name] = once(result[name].decode(), old, new).encode()
    # Source relocation affects the import origin only, never the native artifact contract.
    apps = 'inputs/runtime/verification/apple-toggle-pan-origin-correction/apps.py'
    edit(apps, 'ORIGINAL = ROOT / "verification/apple-toggle-native-failure-analysis"',
         'ORIGINAL = BASE.parent / "apple-toggle-native-failure-analysis"')
    edit(apps, '    expected = {".", "Frameworks", "_CodeSignature", *manifest["files"]}',
         '    expected_dirs = {"."} | {str(parent) for name in manifest["files"] for parent in pathlib.PurePosixPath(name).parents if str(parent) != "."}\n    expected = expected_dirs | set(manifest["files"])')
    edit(apps, '        category = role(path, config)',
         '        category = "directory" if path in expected_dirs else role(path, config)')
    harness = 'inputs/runtime/verification/apple-toggle-pan-origin-correction/harness.py'
    edit(harness, 'import argparse\n', 'import argparse\nimport join_support\n')
    edit(harness, '        started = time.monotonic()\n        env = {**os.environ,',
         '        if join_support.is_selected(argv):\n            return join_support.run_observed(self, argv, timeout, check, retained_stdout_filter)\n        started = time.monotonic()\n        env = {**os.environ,')
    edit('inputs/runtime/verification/apple-toggle-pan-origin-correction/bridge.py',
         'require(set(documents) == {"diagnostic", "comparator"}, "Two fixed app containers required")',
         'require(set(documents) == {"diagnostic"}, "Only selected diagnostic app container required")')
    edit('orchestration.py', 'import workspace_ownership\n', 'import workspace_ownership\nimport join_support\n')
    edit('orchestration.py', "name='MixerTogglePanOrigin-'+str(h.uuid.uuid4())",
         "name='MixerFocusDiagnosticV1-'+str(h.uuid.uuid4())")
    value = result['orchestration.py'].decode()
    begin = value.index('        original=list(h.PRODUCTS.glob(')
    end = value.index('        result_path=ephemeral/', begin)
    value = value[:begin] + (
        '        ephemeral=join_support.prepare_session(h,lifecycle)\n'
        '        allocation_returned=True\n'
        '        h.write(h.RUN_DIR/\'lifecycle.json\',lifecycle)\n'
        '        config_path=join_support.session_configuration(h,ephemeral,server.server_port,capability)\n'
    ) + value[end:]
    value = once(value, '        xctest_exit=commands.run(argv,timeout=600,check=False)[0]',
                 '        join_support.select_command(h,argv,ephemeral)\n        xctest_exit=commands.run(argv,timeout=600,check=False)[0]')
    value = once(value, 'lambda:workspace_ownership.remove(h,lifecycle)', 'lambda:join_support.retire_session(h,lifecycle)')
    result['orchestration.py'] = value.encode()
    value = result['composition.py'].decode()
    value = once(value, 'ROOT=BASE.parents[1]', 'ROOT=pathlib.Path(json.loads((BASE/"runtime-selection.json").read_bytes())["repositoryRoot"])\nOUT=pathlib.Path(json.loads((BASE/"runtime-selection.json").read_bytes())["outputBase"])')
    value = once(value, 'import orchestration\n', 'import orchestration\nimport join_support\nimport command_observer\n')
    value = once(value, 'summary_module,orchestration]', 'summary_module,orchestration,join_support,command_observer]')
    begin = value.index('class CandidateApps:')
    end = value.index("METHODS=", begin)
    value = value[:begin] + 'CandidateApps=join_support.candidate_apps(artifact,BASE,selection)\n\n\n' + value[end:]
    value = once(value, "METHODS=['test000PublicSettingsFullKeyboardAccess']+[value['method'] for value in oracle.SPECS.values()]", 'METHODS=selection["methods"]')
    value = once(value, 'exporting_commands(CANONICAL_COMMANDS,h,BASE,settings_passed,inventory)', 'exporting_commands(CANONICAL_COMMANDS,h,OUT,settings_passed,inventory)')
    value = once(value, "h.BASE=BASE;h.ROOT=ROOT;h.PRODUCTS=BASE/'build/Build/Products';h.PRODUCT_ARCHIVE=BASE/'test-runner-products.tar.gz'", 'h.BASE=OUT;h.ROOT=ROOT;h.PRODUCTS=pathlib.Path(selection["productsRoot"])/"runner-products";h.PRODUCT_ARCHIVE=pathlib.Path(selection["productArchive"])')
    value = once(value, "h.RUN_DIR=BASE/'runtime';h.packet=CandidateApps;artifact.expected_manifest=CandidateApps.expected_manifest", "h.RUN_DIR=OUT/'runtime';h.packet=CandidateApps;artifact.expected_manifest=CandidateApps.expected_manifest")
    value = once(value, "h.SCOPES={'interaction':{'cases':oracle.CASES,'methods':METHODS}}", "h.SCOPES={'interaction':{'cases':set(selection['cases']),'methods':METHODS}}")
    value = once(value, 'h.runtime_summary=lambda *args:summary_module.runtime_summary(BASE,h,oracle,setup_ready,*args)',
                 'h.runtime_summary=lambda *args:join_support.runtime_summary(OUT,h,oracle,setup_ready,*args)\n    h.verify=lambda:join_support.verify_packet(BASE)')
    result['composition.py'] = value.encode()
    result['join_support.py'] = (BASE / 'join_support.py').read_bytes()
    result['command_observer.py'] = (ROOT / 'verification/apple-command-finalization-observer-v2/observer.py').read_bytes()
    require(sha(result['command_observer.py']) == OBSERVER_SHA, 'Accepted observer source changed')
    return result


def verify_inputs():
    lock = json.loads((BASE / 'input-lock.json').read_bytes())
    for name, row in lock['files'].items():
        require(file_row(ROOT / name) == row, 'Bound input changed: ' + name)
    return lock


def prepare():
    require(not SCRATCH.exists() and not (BASE / 'packet.json').exists(), 'Preserve prior packet; fresh preparation required')
    lock = verify_inputs()
    products = json.loads((BUILD / 'product-manifest.json').read_bytes())
    sources = json.loads((BUILD / 'source-manifest.json').read_bytes())
    prepared = json.loads((ROOT / 'verification/apple-toggle-keyboard-focus-diagnostic-v1/prepared.json').read_bytes())
    require(products['archive']['sha256'] == PRODUCT_SHA and sources['acceptedSixSourceTreeSHA256'] == SIX_SHA
            and prepared['preparedSourceTreeSHA256'] == SIX_SHA,
            'Wrong accepted products/source closure')
    observer_root = ROOT / 'verification/apple-command-finalization-observer-v2'
    require(file_row(observer_root / 'receipt.json')['sha256'] == OBSERVER_RECEIPT_SHA, 'Accepted observer receipt changed')
    require(json.loads((observer_root / 'root-review/acceptance.json').read_bytes())['sourceTreeSHA256'] == OBSERVER_CLOSURE,
            'Wrong observer acceptance closure')
    product_payload = archive_payload(BUILD / 'products.tar.gz', products['products'], PRODUCT_SHA)
    source_sha = json.loads((BUILD / 'receipt.json').read_bytes())['products']['acceptedSourcesArchive']['sha256']
    source_payload = archive_payload(BUILD / 'accepted-sources.tar.gz', sources['materializedSources'], source_sha, 'accepted/')
    for name, row in prepared['preparedSources'].items():
        require(sha(source_payload[name]) == row['sha256'], 'Accepted source overlay changed')
    selected = json.loads((V3 / 'runtime-selection.json').read_bytes())
    originals = {name: (V3 / name).read_bytes() for name in selected['files']}
    require(all(sha(value) == selected['files'][name] for name, value in originals.items()), 'V3 runtime input changed')
    derived = derive_runtime(originals, source_payload)
    SCRATCH.mkdir(mode=0o755)
    materialize(SCRATCH / 'products', products['products'], product_payload)
    materialize(SCRATCH / 'accepted', sources['materializedSources'], source_payload)
    runtime_rows = {name: {'kind': 'file', 'bytes': len(data), 'mode': 0o644, 'sha256': sha(data)} for name, data in derived.items()}
    materialize(SCRATCH / 'selected', runtime_rows, derived)
    selected.update(schema=1, scope='Two-method first-case diagnostic only', repositoryRoot=str(ROOT), outputBase=str(BASE),
                    productsRoot=str(SCRATCH / 'products'), productArchive=str(BUILD / 'products.tar.gz'),
                    productManifest=products, methods=METHODS, cases=[CASE], files={name: row['sha256'] for name, row in runtime_rows.items()})
    selected['moduleAliases'].update(join_support='join_support.py', command_observer='command_observer.py', focus_diagnostic='inputs/runtime/verification/apple-toggle-keyboard-focus/focus_diagnostic.py')
    save(SCRATCH / 'selected/runtime-selection.json', selected)
    changes = {name: {'beforeSHA256': sha(originals[name]) if name in originals else None,
                      'afterSHA256': sha(data)} for name, data in derived.items() if originals.get(name) != data}
    save(BASE / 'derivations.json', {'schema': 1, 'changes': changes, 'acceptedPythonOverlays': 2,
                                   'oracleSourcesUnchanged': all(originals[name] == derived[name] for name in originals if 'oracle.py' in name),
                                   'allCompiledProductsUnchanged': tree(SCRATCH / 'products') == products['products']})
    outputs = {'products': tree(SCRATCH / 'products'), 'acceptedSources': tree(SCRATCH / 'accepted'),
               'selectedRuntime': tree(SCRATCH / 'selected')}
    save(BASE / 'output-manifest.json', outputs)
    source_archive = archive_sources(BASE / 'selected-runtime-sources.tar.gz', SCRATCH / 'selected', outputs['selectedRuntime'])
    save(BASE / 'selected-runtime-source-manifest.json', source_archive)
    own = {name: file_row(BASE / name) for name in OWNED_SOURCE_NAMES}
    packet = {'schema': 1, 'status': 'prepared-not-native-selected', 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'preparationCommand': [sys.executable, '-B', str(BASE / 'prepare.py'), 'prepare'],
              'python': sys.version, 'pythonExecutable': str(Path(sys.executable).resolve()),
              'methods': METHODS, 'cases': [CASE], 'sourceRevisionLabel': sources['sourceRevisionLabel'],
              'sourceRevisionMeaning': 'Inherited compilation label; no Git query in this lane.',
              'inputLockSHA256': sha(stable(lock)), 'outputManifestSHA256': sha(stable(outputs)),
              'ownedSourceFiles': own, 'ownedSourceTreeSHA256': sha(stable(own)),
              'selectedSourceArchive': source_archive['archive'],
              'selectedSourceArchiveManifestSHA256': sha(stable(source_archive)),
              'documentation': file_row(ROOT / 'docs/apple-focus-diagnostic-runtime-v1.md'),
              'acceptedSixSourceTreeSHA256': SIX_SHA, 'productArchiveSHA256': PRODUCT_SHA,
              'observerAcceptedSourceClosureSHA256': OBSERVER_CLOSURE,
              'observerSourceSHA256': OBSERVER_SHA, 'observerReceiptSHA256': OBSERVER_RECEIPT_SHA,
              'nativeExecuted': False, 'nativeInstancesQueried': False, 'runtimeSelected': False,
              'physicalPhones': 'disconnected-deferred', 'fullSixCaseQualification': False, 'gaAccepted': False}
    save(BASE / 'packet.json', packet)
    print('PASS: compact archives verified and fresh selected packet prepared; no native commands')


def verify():
    packet = json.loads((BASE / 'packet.json').read_bytes())
    lock = verify_inputs()
    require((BASE / 'input-lock.json').read_bytes() == stable(lock)
            and sha(stable(lock)) == packet['inputLockSHA256'], 'Packet input-lock digest differs from exact canonical lock')
    require(set(packet['ownedSourceFiles']) == set(OWNED_SOURCE_NAMES), 'Owned source membership changed')
    actual_owned = {name: file_row(BASE / name) for name in OWNED_SOURCE_NAMES}
    require(actual_owned == packet['ownedSourceFiles'], 'Owned preparation source changed')
    require(sha(stable(actual_owned)) == packet['ownedSourceTreeSHA256'], 'Claimed owned source digest differs from actual source files')
    require(file_row(ROOT / 'docs/apple-focus-diagnostic-runtime-v1.md') == packet['documentation'], 'Owned documentation changed')
    outputs = json.loads((BASE / 'output-manifest.json').read_bytes())
    require(sha(stable(outputs)) == packet['outputManifestSHA256'], 'Output manifest changed')
    for key, folder in [('products', 'products'), ('acceptedSources', 'accepted'), ('selectedRuntime', 'selected')]:
        require(tree(SCRATCH / folder) == outputs[key], 'Prepared output changed: ' + folder)
    source_archive = json.loads((BASE / 'selected-runtime-source-manifest.json').read_bytes())
    require(sha(stable(source_archive)) == packet['selectedSourceArchiveManifestSHA256'], 'Selected source archive manifest changed')
    require(source_archive['files'] == outputs['selectedRuntime']
            and source_archive['treeSHA256'] == sha(stable(outputs['selectedRuntime'])), 'Selected archive source closure changed')
    require(source_archive['directories'] == sorted(ancestors({'selected/' + name for name in outputs['selectedRuntime']}))
            and source_archive['directoryMode'] == 0o755, 'Selected source archive directory contract changed')
    require(file_row(BASE / 'selected-runtime-sources.tar.gz') == packet['selectedSourceArchive'] == source_archive['archive'],
            'Selected source archive bytes/mode changed')
    archive_payload(BASE / 'selected-runtime-sources.tar.gz', outputs['selectedRuntime'], source_archive['archive']['sha256'], 'selected/')
    return {'packetSHA256': sha((BASE / 'packet.json').read_bytes()), 'nativeExecuted': False,
            'scope': 'Byte/mode/source-closure verification only'}


def run(reviewed_packet):
    verified = verify()
    require(reviewed_packet == verified['packetSHA256'], 'Separate root dispatch requires reviewed exact packet hash')
    require(not (BASE / 'runtime').exists(), 'One attempt only; preserve prior runtime')
    selected = SCRATCH / 'selected'
    sys.path.insert(0, str(selected))
    spec = importlib.util.spec_from_file_location('composition', selected / 'composition.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules['composition'] = module
    spec.loader.exec_module(module)
    def stop(signum, frame):
        raise KeyboardInterrupt('Root diagnostic runner interruption')
    previous = {kind: signal.signal(kind, stop) for kind in [signal.SIGINT, signal.SIGTERM]}
    try:
        return module.h.run(sha((selected / 'runtime-selection.json').read_bytes()))
    finally:
        for kind, handler in previous.items(): signal.signal(kind, handler)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'verify', 'run'])
    parser.add_argument('--reviewed-packet')
    args = parser.parse_args()
    if args.action == 'prepare': prepare()
    elif args.action == 'verify': print(json.dumps(verify(), sort_keys=True))
    else: run(args.reviewed_packet)
