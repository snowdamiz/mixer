#!/usr/bin/env python3
"""Independently verify the retained test-only build without native SDK commands."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = ROOT / 'verification/android-coordinator-join/candidate-2'
spec = importlib.util.spec_from_file_location('click_candidate_local_adapter', HERE / 'run.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check():
    contract, _ = adapter.load_contract()
    runner, _, _ = adapter.load_runner()
    built = HERE / 'candidate-1'
    receipt = runner.bind_candidate(built)
    seal = json.loads((built / 'artifact-seal.json').read_text())
    observed = {str(p.relative_to(built)) for p in built.rglob('*') if p.is_file() and p.name != 'artifact-seal.json'}
    if observed != set(seal) or any(p.is_symlink() for p in built.rglob('*')):
        raise ValueError('build evidence membership drift')
    for name, value in seal.items():
        p = built / name
        if sha(p) != value['sha256'] or p.stat().st_size != value['bytes']:
            raise ValueError('build seal drift: ' + name)
    old = json.loads((BASE / 'source-lock.json').read_text())['files']
    new = json.loads((built / 'source-lock.json').read_text())['files']
    if set(old) != set(new) or len(new) != 105:
        raise ValueError('source membership drift')
    changed_inputs = [name for name in old if old[name] != new[name]]
    source_name = 'verification/android-coordinator-join/CoordinatorJoinInstrumentation.java'
    if changed_inputs != [source_name]:
        raise ValueError('product source changed')
    original_source = (BASE / 'inputs' / source_name).read_text()
    derived_source = (built / 'inputs' / source_name).read_text()
    spec = adapter.load_module('click_candidate_builder', HERE / 'build.py')
    if derived_source != spec.corrected(original_source) or sha(HERE / 'build.py') != contract['builderSourceSHA256']:
        raise ValueError('instrumentation correction or builder drift')
    artifacts = json.loads((built / 'built-artifacts.json').read_text())
    old_artifacts = json.loads((BASE / 'built-artifacts.json').read_text())
    expected_changes = {'coordinator-join.apk', 'dex/classes.dex',
        'test-classes/dev/mixer/android/CoordinatorJoinInstrumentation.class'}
    if set(artifacts) != set(old_artifacts) or {name for name in artifacts if artifacts[name] != old_artifacts[name]} != expected_changes:
        raise ValueError('unexpected compiled artifact delta')
    apk_bytes = None
    with tarfile.open(built / 'built-artifacts.tar.gz', 'r:gz') as archive:
        members = archive.getmembers(); runner.validate_members(members, artifacts)
        for member in members:
            stream = archive.extractfile(member)
            digest = hashlib.sha256()
            if member.name == 'coordinator-join.apk':
                apk_bytes = stream.read(); digest.update(apk_bytes)
            else:
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(block)
            if member.size != artifacts[member.name]['bytes'] or digest.hexdigest() != artifacts[member.name]['sha256']:
                raise ValueError('compiled archive drift: ' + member.name)
    entries = json.loads((built / 'apk-entries.json').read_text())
    old_entries = json.loads((BASE / 'apk-entries.json').read_text())
    if set(entries) != set(old_entries):
        raise ValueError('APK membership drift')
    expected_entry_changes = {'classes.dex', 'META-INF/DEBUG.RSA', 'META-INF/DEBUG.SF', 'META-INF/MANIFEST.MF'}
    if {name for name in entries if entries[name] != old_entries[name]} != expected_entry_changes:
        raise ValueError('product APK entry changed')
    with zipfile.ZipFile(io.BytesIO(apk_bytes)) as archive:
        if set(archive.namelist()) != set(entries):
            raise ValueError('retained APK membership mismatch')
        for name, value in entries.items():
            data = archive.read(name)
            if len(data) != value['bytes'] or hashlib.sha256(data).hexdigest() != value['sha256']:
                raise ValueError('retained APK entry mismatch: ' + name)
    if ((built / '.build').exists() or receipt['buildScratchCleanup']['status'] != 'removed'
            or receipt['privateKeyRetained'] or any('.keystore' in name for name in artifacts)):
        raise ValueError('scratch/key cleanup failed')
    if any(c['exitCode'] != 0 or c['ownedCommandGroupCleanup']['after'] for c in receipt['commands']):
        raise ValueError('build command or command-group failure')
    return {'status': 'passed-test-only-artifact-identity', 'sourceInputs': 105, 'unchangedSourceInputs': 104,
        'compiledArtifacts': len(artifacts), 'unchangedCompiledArtifacts': len(artifacts) - 3,
        'unchangedAPKEntries': len(entries) - 4, 'apkSHA256': receipt['apkSHA256'],
        'nativeRuntime': 'NOT RUN by artifact verifier', 'nativeCommandsExecuted': 0,
        'nativeInstancesStarted': 0, 'physicalTargetsQueried': False}


if __name__ == '__main__':
    print(json.dumps(check(), indent=2, sort_keys=True))
