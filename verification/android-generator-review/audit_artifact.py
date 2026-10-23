#!/usr/bin/env python3
"""Audit committed build evidence and exact unsigned APK without rebuilding or device access."""
import hashlib
import io
import json
import pathlib
import re
import shutil
import subprocess
import tarfile
import zipfile

OUT = pathlib.Path(__file__).resolve().parent
ROOT = OUT.parents[1]
revision = json.loads((OUT / 'freeze.json').read_text())['revision']
EVIDENCE = OUT / '.local/audited-evidence'
EVIDENCE.mkdir()
archive = subprocess.check_output(['git', 'archive', '--format=tar', revision, 'verification/android-generated-consumer'], cwd=ROOT)
with tarfile.open(fileobj=io.BytesIO(archive)) as stream: stream.extractall(EVIDENCE, filter='data')
EVIDENCE /= 'verification/android-generated-consumer'
receipt = json.loads((EVIDENCE / 'receipt.json').read_text())
build = json.loads((EVIDENCE / 'build-receipt.json').read_text())
sha = lambda data: hashlib.sha256(data).hexdigest()
checks = []
manifest = (EVIDENCE / 'source-manifest.sha256').read_bytes()
assert sha(manifest) == receipt['source_tree_sha256']
for line in manifest.decode().splitlines():
    digest, path = line.split('  ', 1)
    committed = subprocess.check_output(['git', 'show', revision + ':' + path], cwd=ROOT)
    assert sha(committed) == digest, path
checks.append({'name': 'committed-source-manifest', 'files': len(manifest.decode().splitlines()), 'sha256': sha(manifest)})
for command in receipt['commands']:
    log = EVIDENCE / pathlib.Path(command['output']).name
    assert sha(log.read_bytes()) == command['output_sha256'], command['name']
    assert (command['exit_code'] == 0) == (command['expected_exit_code'] == 0), command['name']
checks.append({'name': 'implementer-command-log-integrity', 'commands': len(receipt['commands'])})
# Confirm the exported immutable bridge/renderer/profile schema bytes did not change.
unchanged = ['bridge/jni.c', 'bridge/mixer_android.h', 'contracts/android-profile-v1.json', 'app/src/dev/mixer/android/Json.java', 'app/src/dev/mixer/android/UiPacket.java', 'app/src/dev/mixer/android/NativeBridge.java', 'app/src/dev/mixer/android/NativeRenderer.java', 'app/src/dev/mixer/android/MixerActivity.java']
for path in unchanged:
    current = subprocess.check_output(['git', 'show', revision + ':native/android/' + path], cwd=ROOT)
    previous = subprocess.check_output(['git', 'show', revision + '^:native/android/' + path], cwd=ROOT)
    assert current == previous, path
checks.append({'name': 'unchanged-java-jni-schema-contract', 'files': len(unchanged)})
apk = pathlib.Path(receipt['actual_apk']['apk'])
assert sha(apk.read_bytes()) == receipt['actual_apk']['apk_sha256'] == build['apk_sha256']
local_apk = OUT / '.local/audited-unsigned.apk'; shutil.copyfile(apk, local_apk)
assert sha(local_apk.read_bytes()) == build['apk_sha256']
with zipfile.ZipFile(local_apk) as stream:
    assert len(stream.namelist()) == len(set(stream.namelist()))
    content = {name: sha(stream.read(name)) for name in sorted(stream.namelist())}
    assert content == build['apk_entries']
    assert sha(json.dumps(content, sort_keys=True, separators=(',', ':')).encode()) == build['apk_content_sha256']
    assert not any(name.startswith('META-INF/') for name in content)
    assert 'classes.dex' in content and 'AndroidManifest.xml' in content
    assert not any('Checklist' in name for name in content)
    libs = {name: stream.read(name) for name in content if name.startswith('lib/')}
    assert all(name.startswith('lib/arm64-v8a/') and name.endswith('.so') for name in libs)
    extracted = OUT / '.local/apk'; extracted.mkdir()
    for name in ['classes.dex', *libs]:
        target = extracted / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(stream.read(name))
checks.append({'name': 'actual-apk-contents', 'apk_sha256': build['apk_sha256'], 'apk_bytes': local_apk.stat().st_size, 'apk_content_sha256': build['apk_content_sha256'], 'entries': len(content), 'libraries': len(libs), 'unsigned': True})
commands=[]
def run(name, args):
    tool = pathlib.Path(args[0]); expected = next(value for value in build['toolchain']['tools'].values() if value['path'] == str(tool))
    assert sha(tool.read_bytes()) == expected['sha256']
    p = subprocess.run(list(map(str,args)), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log = OUT / ('artifact-' + name + '.log'); log.write_bytes(p.stdout)
    commands.append({'command': list(map(str,args)), 'exit_code': p.returncode, 'output': log.name, 'output_sha256': sha(p.stdout), 'tool_sha256': expected['sha256']})
    assert p.returncode == 0, name
    return p.stdout.decode()
tools={key:pathlib.Path(value['path']) for key,value in build['toolchain']['tools'].items()}
run('alignment', [tools['zipalign'], '-c', '-P', '16', '4', local_apk])
badging=run('badging', [tools['aapt2'], 'dump', 'badging', local_apk])
assert "package: name='dev.mixer.generatedconsumer'" in badging and "native-code: 'arm64-v8a'" in badging
assert 'dev.mixer.android.MixerActivity' in badging
needed={}
system={'libc.so','libdl.so','libm.so','liblog.so','libandroid.so'}
for name in libs:
    path=extracted/name
    headers=run(path.name+'-elf', [tools['readelf'], '-h', '-d', '-l', path])
    assert 'ELF64' in headers and 'AArch64' in headers
    needed[path.name]=re.findall(r'\(NEEDED\).*\[([^\]]+)\]',headers)
    assert set(needed[path.name]).issubset(system | {pathlib.Path(p).name for p in libs})
assert needed == build['native_dependencies']
dex=run('dex', [tools['dexdump'], '-f', extracted/'classes.dex'])
for descriptor in ['Ldev/mixer/android/MixerActivity;','Ldev/mixer/android/NativeBridge;','Ldev/mixer/android/NativeRenderer;']: assert descriptor in dex
assert 'AdapterInstrumentation' not in dex
symbols=run('app-symbols', [tools['nm'], '-D', '--defined-only', extracted/'lib/arm64-v8a/libAppAndroid.so'])
for symbol in ['mixer_android_create','mixer_android_exchange','mixer_android_destroy','AppFeatures','AppModels']: assert symbol in symbols
assert 'ChecklistEngine' not in symbols
checks.append({'name':'independent-pinned-tool-artifact-inspection','commands':len(commands),'native_dependencies':needed,'owned_classes':3,'app_shared_symbols':True})
(OUT/'artifact-audit.json').write_text(json.dumps({'revision':revision,'qualification':'audited actual unsigned arm64 APK; no independent duplicate full cross-build','checks':checks,'commands':commands,'toolchain':build['toolchain'],'pending':['physical Android/iOS','signing/installability','device UI/lifecycle/accessibility/performance','published consumer packages','FieldLog D2','store acceptance','GA']},indent=2)+'\n')
print(json.dumps({'checks':checks,'commands':len(commands)},indent=2))
