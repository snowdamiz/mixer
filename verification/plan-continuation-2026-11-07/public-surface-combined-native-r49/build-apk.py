from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
import zipfile

p = Path(__file__).resolve().parent
root = p.parents[2]
prior = p.parent / 'public-android-surface-consumer-r42'
frozen = json.loads((prior / 'build-result.json').read_text())
source_apk = Path(frozen['apk'])
sha = lambda f: hashlib.sha256(f.read_bytes()).hexdigest()
assert sha(source_apk) == frozen['sha256']
overlay = json.loads((p / 'overlay-inputs.json').read_text())
assert not (p / 'build-result.json').exists()
scratch = Path(tempfile.mkdtemp(prefix='mixer-public-r49-', dir='/Users/andreyyurlov/.t3/userdata'))
(p / 'scratch.json').write_text(json.dumps({'ownedBuild': str(scratch)}, indent=2) + '\n')
sdk = Path('/opt/homebrew/share/android-commandlinetools')
bt = sdk / 'build-tools/37.0.0'
jar = sdk / 'platforms/android-37.0/android.jar'
jdk = Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
env = os.environ.copy()
env.update(JAVA_HOME=str(jdk), JAVA_TOOL_OPTIONS='-XX:ActiveProcessorCount=2')
env['PATH'] = str(jdk / 'bin') + os.pathsep + env['PATH']
commands = []
started = time.monotonic()

def run(name, argv):
    args = list(map(str, argv))
    t = time.monotonic()
    with (p / (name + '.stdout')).open('wb') as out, (p / (name + '.stderr')).open('wb') as err:
        child = subprocess.Popen(args, cwd=root, env=env, stdout=out, stderr=err, start_new_session=True)
        row = {'name': name, 'argv': args, 'cwd': str(root), 'pid': child.pid, 'pgid': child.pid}
        commands.append(row)
        (p / 'build-commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        try:
            code = child.wait(timeout=90)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, 15)
            child.wait(timeout=10)
            raise
        row.update(exitCode=code, elapsedSeconds=time.monotonic() - t)
        try:
            os.killpg(child.pid, 0)
            row['groupAbsent'] = False
        except ProcessLookupError:
            row['groupAbsent'] = True
        (p / 'build-commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        print(name, code, flush=True)
        assert row['groupAbsent'], 'Preserve owned build: command group absence unproven'
        assert code == 0, name + ': inspect raw stderr'

profile_text = (root / 'cli/Sources/MixerBuild/AndroidSDKCompatibility.swift').read_text()
profile = json.loads(profile_text.split('Data(#"""', 1)[1].split('"""#', 1)[0])
sources = {}
for name, pin in profile['adapter_files'].items():
    if not name.endswith('.java'):
        continue
    f = root / 'native/android' / name
    assert sha(f) == pin['sha256']
    sources[f.name] = f
assert len(sources) == 20
sources['AndroidUINativeSurface.java'] = prior / 'afterimages/native/android/app/src/dev/mixer/android/AndroidUINativeSurface.java'
for row in overlay:
    f = Path(row['source'])
    assert sha(f) == row['sha256'] and f.name in sources
    sources[f.name] = f
inputs = {}
for name, src in sources.items():
    dst = scratch / 'sdk' / name
    dst.parent.mkdir(exist_ok=True)
    shutil.copy2(src, dst)
    inputs[name] = {'source': str(src), 'sha256': sha(src)}
(p / 'product-inputs.json').write_text(json.dumps(inputs, indent=2) + '\n')
flags = ['--release', '17', '-Xlint:all', '-Werror', '-proc:none', '-sourcepath', '']
for name in ['sdk-classes', 'app-classes', 'test-classes', 'dex']:
    (scratch / name).mkdir()
run('sdk-javac', [jdk / 'bin/javac', *flags, '-classpath', jar, '-d', scratch / 'sdk-classes', *sorted((scratch / 'sdk').glob('*.java'))])
app_sources = sorted((prior / 'afterimages/app').rglob('*.java'))
run('external-app-javac', [jdk / 'bin/javac', *flags, '-classpath', str(jar) + os.pathsep + str(scratch / 'sdk-classes'), '-d', scratch / 'app-classes', *app_sources])
instrumentation = prior / 'testconsumer/FieldLogInstrumentation.java'
run('instrumentation-javac', [jdk / 'bin/javac', *flags, '-classpath', os.pathsep.join(map(str, [jar, scratch / 'sdk-classes', scratch / 'app-classes'])), '-d', scratch / 'test-classes', instrumentation])
classes = [f for d in ['sdk-classes', 'app-classes', 'test-classes'] for f in sorted((scratch / d).rglob('*.class'))]
run('d8', [bt / 'd8', '--min-api', '28', '--lib', jar, '--output', scratch / 'dex', *classes])
package = 'dev.fieldlog.publicsurface49'
manifest = (prior / 'AndroidManifest.xml').read_text().replace('dev.fieldlog.publicsurface', package)
(p / 'AndroidManifest.xml').write_text(manifest)
run('manifest', [bt / 'aapt2', 'link', '-I', jar, '--manifest', p / 'AndroidManifest.xml', '-o', scratch / 'manifest.apk'])
with zipfile.ZipFile(source_apk) as old, zipfile.ZipFile(scratch / 'manifest.apk') as mf, zipfile.ZipFile(scratch / 'unaligned.apk', 'w') as apk:
    for item in old.infolist():
        if item.filename == 'AndroidManifest.xml' or item.filename.endswith('.dex') or item.filename.startswith('META-INF/'):
            continue
        apk.writestr(item, old.read(item.filename))
    apk.writestr('AndroidManifest.xml', mf.read('AndroidManifest.xml'))
    for f in sorted((scratch / 'dex').glob('*.dex')):
        apk.write(f, f.name, compress_type=zipfile.ZIP_DEFLATED)
apk_path = p / 'FieldLog-public-surface-r49-unsigned.apk'
run('zipalign', [bt / 'zipalign', '-f', '-P', '16', '4', scratch / 'unaligned.apk', apk_path])
run('alignment', [bt / 'zipalign', '-c', '-P', '16', '4', apk_path])
with zipfile.ZipFile(source_apk) as old, zipfile.ZipFile(apk_path) as new:
    libraries = [n for n in old.namelist() if n.startswith('lib/') and n.endswith('.so')]
    assert len(libraries) == 18 and all(old.read(n) == new.read(n) for n in libraries)
result = {'buildPassed': True, 'apk': str(apk_path), 'sha256': sha(apk_path), 'package': package,
          'instrumentationComponent': package + '/dev.mixer.android.FieldLogInstrumentation',
          'expectedPASS': frozen['expectedPASS'], 'nativeLibrariesUnchanged': 18,
          'externalPackageAppUnchanged': True, 'fullR39InstrumentationUnchanged': True,
          'elapsedSeconds': time.monotonic() - started, 'allOwnedCommandGroupsAbsent': all(r['groupAbsent'] for r in commands),
          'runtime': 'PENDING signed emulator test', 'canonicalApplied': False}
(p / 'build-result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result), flush=True)
