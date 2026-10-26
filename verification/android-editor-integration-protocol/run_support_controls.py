#!/usr/bin/env python3
"""Compile authored support against sealed historical classes; never source acceptance."""
import datetime
import hashlib
import json
import os
import platform
import signal
import subprocess
import tempfile
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
def ident(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
def main():
    output = HERE / 'support-controls'
    output.mkdir(exist_ok=False)
    frozen = HERE / 'inputs/historical-preparation/closure-B-directprobe/classes'
    source = HERE / 'MigrationSupportControls.java'
    jdk = Path('/opt/homebrew/opt/openjdk/libexec/openjdk.jdk/Contents/Home').resolve(strict=True)
    tools = {str(jdk / 'bin' / name): ident((jdk / 'bin' / name).resolve().read_bytes()) for name in ('java', 'javac', 'javap')}
    environment = dict(os.environ)
    for key in ('_JAVA_OPTIONS', 'JAVA_TOOL_OPTIONS', 'JDK_JAVA_OPTIONS', 'CLASSPATH', 'JAVA_OPTS', 'JDK_JAVAC_OPTIONS'):
        environment.pop(key, None)
    scratch = Path(tempfile.mkdtemp(prefix='migration-support-', dir=output))
    classes = output / 'classes'
    classes.mkdir()
    commands = []
    receipt = {'at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'python': platform.python_version(),
        'status': 'failed', 'scope': '9 authored migration controls using immutable historical unaccepted product classes and controlled leaves; no broad suite/native equivalence',
        'corrected_candidate_binding': None, 'tools': tools, 'source': ident(source.read_bytes())}
    def run(label, argv, timeout=30):
        with (output / (label + '.stdout')).open('wb') as out, (output / (label + '.stderr')).open('wb') as err:
            child = subprocess.Popen([str(v) for v in argv], env=environment, stdout=out, stderr=err, start_new_session=True)
            timed = False
            try:
                child.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed = True
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
        command = {'argv': [str(v) for v in argv], 'exit': child.returncode, 'timeout': timed, 'child_reaped': True,
            'stdout': ident((output / (label + '.stdout')).read_bytes()), 'stderr': ident((output / (label + '.stderr')).read_bytes())}
        commands.append(command)
        save(output / 'commands.json', commands)
        if child.returncode or timed:
            raise RuntimeError(label + ' failed')
    try:
        run('java-version', [jdk / 'bin/java', '-version'])
        run('javac-version', [jdk / 'bin/javac', '-version'])
        run('compile', [jdk / 'bin/javac', '--release', '17', '-Xlint:all', '-Werror', '-proc:none',
            '-classpath', frozen, '-sourcepath', scratch, '-d', classes, source])
        run('bytecode', [jdk / 'bin/javap', '-c', '-p', '-s', '-l', '-classpath', classes,
            'dev.mixer.android.MigrationSupportControls'])
        descriptor = HERE / 'inputs/repo/verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json'
        run('host', [jdk / 'bin/java', '-ea', '-Xmx256m', '-cp', str(classes) + os.pathsep + str(frozen),
            'dev.mixer.android.MigrationSupportControls', descriptor])
        receipt['status'] = 'passed-historical-host-support-only'
        save(output / 'class-map.json', {str(p.relative_to(classes)): ident(p.read_bytes()) for p in sorted(classes.rglob('*.class'))})
        print((output / 'host.stdout').read_text().strip())
    except BaseException as failure:
        receipt['failure'] = {'type': type(failure).__name__, 'message': str(failure)}
        raise
    finally:
        shutil.rmtree(scratch)
        receipt['cleanup'] = {'scratch_removed': not scratch.exists(), 'children_reaped': all(c['child_reaped'] for c in commands),
            'native_ui_capture_processes_queried_or_started': False}
        save(output / 'receipt.json', receipt)
if __name__ == '__main__':
    main()
