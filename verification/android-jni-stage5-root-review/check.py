#!/usr/bin/env python3
"""Compile proposed declarations only; this does not build a JNI implementation."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
PROPOSAL = ROOT / 'verification/android-jni-stage5-contract'
BUILD = OUT / '.build'
BUILD.mkdir(exist_ok=False)
sha = lambda data: hashlib.sha256(data).hexdigest()
lock = json.loads((PROPOSAL / 'input-lock.json').read_text())
for path, expected in lock['files_sha256'].items():
    if sha((ROOT / path).read_bytes()) != expected:
        raise RuntimeError('Proposal input changed: ' + path)
api = json.loads((PROPOSAL / 'api.json').read_text())
struct = '''struct mxis_native_slot {
    uint64_t facade, slot_generation, attach_serial, final_entry;
    uint64_t attachment, input, probe;
    uint32_t disposition, packet_bytes;
};
'''
header = '''/* Declaration fixture only. No implementations, witnesses or native authority. */
#include <stdint.h>
#include <stddef.h>
#include "mixer_ui_binding.h"
'''+struct+'\n'.join(api['fixed_c_declarations'])+'''
#if defined(__cplusplus)
static_assert(sizeof(mxis_native_slot) == 64, "slot size");
static_assert(alignof(mxis_native_slot) == 8, "slot alignment");
static_assert(offsetof(mxis_native_slot, disposition) == 56, "slot fields");
#else
_Static_assert(sizeof(struct mxis_native_slot) == 64, "slot size");
_Static_assert(_Alignof(struct mxis_native_slot) == 8, "slot alignment");
_Static_assert(offsetof(struct mxis_native_slot, disposition) == 56, "slot fields");
#endif
'''
(OUT/'declarations.h').write_text(header)

def java_arguments(descriptor):
    tokens = re.findall(r'\[B|L[^;]+;|[JI]', descriptor.split(')')[0][1:])
    names = {'J': 'long', 'I': 'int', '[B': 'byte[]'}
    return ', '.join((names[token] if token in names else token[1:-1].replace('/', '.'))
                     + f' arg{index}' for index, token in enumerate(tokens))

java = '''package dev.mixer.android;
// Declaration fixture only. Every Java body is permanently unavailable.
final class SignedGuestScreen {
    private SignedGuestScreen(android.app.Activity activity, long lifecycle, long presentation) {
        throw new UnsupportedOperationException("declaration-only");
    }
'''
for method in api['java_origin_methods']:
    java += '    private static native int ' + method['name'] + '(' + java_arguments(method['descriptor']) + ');\n'
for method in api['native_to_java_methods']:
    java += '    private int ' + method['name'] + '(' + java_arguments(method['descriptor']) + ') { throw new UnsupportedOperationException("declaration-only"); }\n'
java += '}\n'
(OUT/'SignedGuestScreen.java').write_text(java)
commands = []

def run(name, argv):
    result = subprocess.run(list(map(str, argv)), cwd=ROOT, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'),
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
    log = OUT/(name+'.log')
    log.write_bytes(result.stdout)
    commands.append({'name': name, 'argv': list(map(str, argv)), 'cwd': str(ROOT),
                     'exit_code': result.returncode, 'log': log.name, 'sha256': sha(result.stdout)})
    if result.returncode:
        raise RuntimeError(name+' failed; see '+str(log))
    return result.stdout.decode()

jdk = Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
jar = Path('/opt/homebrew/share/android-commandlinetools/platforms/android-37.0/android.jar')
ndk = Path('/Users/andreyyurlov/.swiftpm/swift-sdks/swift-6.3.3-RELEASE_android.artifactbundle/swift-android/android-ndk-r27d/toolchains/llvm/prebuilt/darwin-x86_64')
includes = ['-I'+str(ROOT/'native/android/signed-guest-ui/binding/include'),
            '-I'+str(ROOT/'native/android/signed-guest-ui/transport/include')]
run('clang-version', ['xcrun','clang','--version'])
run('ndk-version', [ndk/'bin/clang','--version'])
run('java-version', [jdk/'bin/javac','-version'])
for label, compiler, language, standard in [
    ('host-c11',['xcrun','clang'],'c','c11'),
    ('host-cpp17',['xcrun','clang++'],'c++','c++17'),
    ('android-api30-c11',[ndk/'bin/aarch64-linux-android30-clang'],'c','c11'),
    ('android-api30-cpp17',[ndk/'bin/aarch64-linux-android30-clang++'],'c++','c++17')]:
    run(label, [*compiler,'-x',language,'-std='+standard,'-Wall','-Wextra','-Werror','-fsyntax-only',*includes,OUT/'declarations.h'])
run('javac-declarations',[jdk/'bin/javac','--release','17','-cp',jar,'-d',BUILD,OUT/'SignedGuestScreen.java'])
listing=run('javap-descriptors',[jdk/'bin/javap','-s','-p','-classpath',BUILD,'dev.mixer.android.SignedGuestScreen'])
for method in api['java_origin_methods']+api['native_to_java_methods']:
    lines=listing.splitlines(); index=next(i for i,line in enumerate(lines) if method['name']+'(' in line)
    if lines[index+1].strip() != 'descriptor: '+method['descriptor']:
        raise RuntimeError('Java descriptor differs: '+method['name'])
if 'descriptor: '+api['constructor_descriptor'] not in listing:
    raise RuntimeError('Constructor descriptor differs')
for label, args in [('normal',[]),('optimized',['-O'])]:
    run('collector-tests-'+label,[sys.executable,*args,'-B','-m','unittest','discover','-s',PROPOSAL,'-p','test_*.py','-v'])
for path, expected in lock['files_sha256'].items():
    if sha((ROOT/path).read_bytes()) != expected:
        raise RuntimeError('Proposal source changed during checks')
receipt={'scope':'Declaration compilation, exact JVM descriptors, immutable input checks and collector tests only. No JNI implementation or native execution.',
         'input_tree_sha256':lock['input_tree_sha256'],'input_checks':len(lock['files_sha256']),
         'declarations':{'c_prototypes':len(api['fixed_c_declarations']),'java_methods':10,'constructor':1,
                         'slot_size_bytes':64,'slot_alignment_bytes':8},
         'commands':commands,'android_jar_sha256':sha(jar.read_bytes()),
         'files':{str(p.relative_to(OUT)):sha(p.read_bytes()) for p in OUT.iterdir() if p.is_file()},
         'native_cases_executed':0,'ga_pass':False,'status':'passed'}
(OUT/'declarations-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'status':'passed','commands':len(commands),'inputs':len(lock['files_sha256'])}))
