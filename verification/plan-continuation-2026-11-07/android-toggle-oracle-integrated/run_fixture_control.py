#!/usr/bin/env python3
"""Exercise the fixture checks with the fixed leaf and the unchanged candidate leaf."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from cleanup_control import stop

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
JDK = Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
CLASSES = OUT / 'fullB/classes'
CANDIDATE = Path('/Users/andreyyurlov/.t3/worktrees/mixer/t3-5a390519')
LEAF = 'native/android/tests/NativeOwnerV2ConcreteHostLeaves/android/widget/Switch.java'
WORK = Path(tempfile.mkdtemp(prefix='mixer-toggle-fixture-control-', dir='/tmp'))
receipt = {'commands': [], 'scope': 'controlled fixture behavior only; no full B replay or native instance'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(name, arguments, expected=0):
    argv = [str(value) for value in arguments]
    output = OUT / (name + '.log')
    env = dict(os.environ)
    for key in ('_JAVA_OPTIONS', 'JAVA_TOOL_OPTIONS', 'JDK_JAVA_OPTIONS', 'CLASSPATH', 'JAVA_OPTS', 'JDK_JAVAC_OPTIONS'):
        env.pop(key, None)
    with output.open('wb') as stream:
        process = subprocess.Popen(argv, cwd=WORK, env=env, stdin=subprocess.DEVNULL,
                                   stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = process.wait(timeout=30)
        finally:
            cleanup = stop(process)
    receipt['commands'].append({'argv': argv, 'output': output.name, 'exitCode': code,
                                'outputSHA256': sha(output), 'cleanup': cleanup})
    assert cleanup['groupAbsent'] and cleanup['leaderReaped'], cleanup
    assert code == expected, (name, code, expected)
    return output.read_text()


try:
    fixed = WORK / 'fixed'; fixed.mkdir()
    run('fixture-control-compile', [JDK / 'bin/javac', '--release', '17', '-Xlint:all', '-Werror',
                                  '-proc:none', '-sourcepath', fixed, '-classpath', CLASSES,
                                  '-d', fixed, OUT / 'FixtureClickControl.java'])
    positive = run('fixture-control-fixed', [JDK / 'bin/java', '-ea', '-Xmx128m', '-cp',
                                            str(fixed) + os.pathsep + str(CLASSES),
                                            'dev.mixer.android.FixtureClickControl'])
    assert positive.startswith('PASS controlled fixture checks='), positive
    old = WORK / 'old'; old.mkdir()
    original = old / 'Switch.java'; original.write_bytes((CANDIDATE / LEAF).read_bytes())
    run('fixture-control-old-compile', [JDK / 'bin/javac', '--release', '17', '-Xlint:all', '-Werror',
                                      '-proc:none', '-sourcepath', fixed, '-classpath', CLASSES,
                                      '-d', old, original])
    negative = run('fixture-control-old', [JDK / 'bin/java', '-ea', '-Xmx128m', '-cp',
                                          os.pathsep.join(map(str, [old, fixed, CLASSES])),
                                          'dev.mixer.android.FixtureClickControl'], expected=1)
    assert 'no click listener still toggles but returns false' in negative, negative
    receipt.update(status='passed', fixedResult=positive.strip(),
                   unchangedCandidateLeafRejected=True, oldLeafSHA256=sha(original),
                   correctedLeafSHA256=sha(ROOT / LEAF),
                   tools={str(JDK / 'bin' / name): sha(JDK / 'bin' / name) for name in ('java', 'javac')})
finally:
    shutil.rmtree(WORK)
    receipt['scratchRemoved'] = not WORK.exists()
    (OUT / 'fixture-control.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({key: receipt[key] for key in ('status', 'fixedResult', 'unchangedCandidateLeafRejected', 'scratchRemoved')}))
