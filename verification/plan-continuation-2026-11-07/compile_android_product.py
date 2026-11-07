#!/usr/bin/env python3
"""One bounded SDK compile of the current canonical Android product sources."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / 'android-product-compile'
OUT.mkdir(exist_ok=False)
SCRATCH = Path(tempfile.mkdtemp(prefix='mixer-20261107-product-'))
JDK = Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
SDK = Path('/opt/homebrew/share/android-commandlinetools')
JAR = SDK / 'platforms/android-37.0/android.jar'
D8 = SDK / 'build-tools/37.0.0/d8'
ENV = dict(os.environ)
for key in ('_JAVA_OPTIONS', 'JAVA_TOOL_OPTIONS', 'JDK_JAVA_OPTIONS', 'CLASSPATH', 'JAVA_OPTS', 'JDK_JAVAC_OPTIONS'):
    ENV.pop(key, None)
ENV.update(JAVA_HOME=str(JDK), PATH=str(JDK / 'bin') + os.pathsep + ENV.get('PATH', ''))

def identity(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def save():
    (OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')

receipt = {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'status': 'running', 'scope': 'canonical Java/SDK/D8 compile only; no generated consumer, APK or native runtime acceptance',
           'python': platform.python_version(), 'platform': platform.platform(), 'commands': [],
           'scratch': str(SCRATCH), 'nativeInstancesStarted': 0}

def run(name, args):
    start = time.monotonic()
    args = [str(arg) for arg in args]
    out, err = OUT / (name + '.stdout'), OUT / (name + '.stderr')
    with out.open('wb') as stdout, err.open('wb') as stderr:
        child = subprocess.Popen(args, cwd=ROOT, env=ENV, stdout=stdout, stderr=stderr, start_new_session=True)
        record = {'name': name, 'argv': args, 'pid': child.pid, 'timeoutSeconds': 120, 'streamCapBytes': 8000000}
        receipt['commands'].append(record)
        save()
        while child.poll() is None:
            if time.monotonic() - start > 120 or max(out.stat().st_size, err.stat().st_size) > 8000000:
                record['limitExceeded'] = True
                os.killpg(child.pid, signal.SIGKILL)
                break
            time.sleep(.05)
        record['exit'] = child.wait()
    record.update(seconds=time.monotonic() - start, childReaped=True, stdout=identity(out), stderr=identity(err))
    try:
        os.killpg(child.pid, 0)
        record['ownedGroupAbsent'] = False
    except ProcessLookupError:
        record['ownedGroupAbsent'] = True
    save()
    if record['exit'] or record.get('limitExceeded') or not record['ownedGroupAbsent']:
        raise RuntimeError(name + ' failed or retained an owned process group')
    return out.read_text()

try:
    receipt['revision'] = run('revision', ['git', 'rev-parse', 'HEAD']).strip()
    sources = sorted((ROOT / 'native/android/app/src/dev/mixer/android').glob('*.java'))
    receipt['sources'] = {str(p.relative_to(ROOT)): identity(p) for p in sources}
    receipt['tools'] = {str(p): identity(p.resolve()) for p in (JDK / 'bin/javac', JDK / 'bin/java', JAR, D8)}
    run('javac-version', [JDK / 'bin/javac', '-version'])
    run('java-version', [JDK / 'bin/java', '-version'])
    run('d8-version', [D8, '--version'])
    classes, empty, dex = (SCRATCH / part for part in ('classes', 'empty', 'dex'))
    for folder in (classes, empty, dex):
        folder.mkdir()
    run('javac', [JDK / 'bin/javac', '--release', '17', '-Xlint:all', '-Werror', '-proc:none',
                  '-classpath', JAR, '-sourcepath', empty, '-d', classes, *sources])
    emitted = sorted(classes.rglob('*.class'))
    receipt['classes'] = {str(p.relative_to(classes)): identity(p) for p in emitted}
    run('d8', [D8, '--min-api', '28', '--lib', JAR, '--output', dex, *emitted])
    receipt['dex'] = {str(p.relative_to(dex)): identity(p) for p in dex.rglob('*') if p.is_file()}
    receipt['sourceStable'] = all(identity(ROOT / p) == row for p, row in receipt['sources'].items())
    if not receipt['sourceStable']:
        raise RuntimeError('Product source changed during compilation')
    receipt['status'] = 'passed-crosscompile-only'
except BaseException as error:
    receipt.update(status='failed', error={'type': type(error).__name__, 'message': str(error)})
    raise
finally:
    closed = all(c.get('childReaped') and c.get('ownedGroupAbsent') for c in receipt['commands'])
    if closed:
        shutil.rmtree(SCRATCH)
    receipt['cleanup'] = {'scratchRemoved': not SCRATCH.exists(), 'allOwnedGroupsClosed': closed}
    save()
    print(json.dumps({'status': receipt['status'], 'receipt': str(OUT / 'receipt.json'), 'cleanup': receipt['cleanup']}))
