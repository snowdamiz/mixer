#!/usr/bin/env python3
"""Independent bounded actual-source compilation and scalar-tail evidence.

This is a host/source review only. It does not authorize native, OTA or GA use.
"""
from pathlib import Path
import datetime, hashlib, json, os, re, shutil, subprocess, sys, tempfile, time

D = Path(__file__).resolve().parent
R = D.parents[1]
C = D.parent / 'android-editor-preservation-completion-implementation'
B = D.parent / 'android-editor-focus-history-correction'
J = Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
EXPECTED_SEAL = '8f355ae83ec4d734e8d28451fc64a45200967a718eecb7c1987fa0fcc69d9920'

def ident(p):
    data = p.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def save(name, data):
    (D / name).write_text(json.dumps(data, indent=2) + '\n')

def mapping(folder):
    return {str(p.relative_to(folder)): ident(p) for p in sorted(folder.rglob('*')) if p.is_file()}

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

assert not (D / 'seal.json').exists(), 'Already frozen'
assert ident(C / 'seal.json')['sha256'] == EXPECTED_SEAL
seal = json.loads((C / 'seal.json').read_text())
assert ident(C / 'manifest.json') == seal['manifest']
count = total = 0
for member in seal['members']:
    rel = Path(member['path'])
    assert not rel.is_absolute() and '..' not in rel.parts
    assert ident(C / rel) == {'bytes': member['bytes'], 'sha256': member['sha256']}, str(rel)
    count += 1
    total += member['bytes']
assert (count, total) == (9791, 49981814) == (seal['member_count'], seal['member_bytes'])
contracts = {
    'verification/android-editor-boundary-root-review/preservation-completion-candidate-custody.json': '38d52481b561c8514b9dfe8cda7dcb9955d8e9b20e4bbb164ecfaffcf9743148',
    'verification/android-editor-boundary-root-review/preservation-completion-implementation-selection.json': '7bc0948928801e5d04ea73267bd2dec01b2d71ae93b7169dfeaaf7893d543a91',
    'verification/android-editor-preservation-protocol-independent/required-amendment.md': 'c50fc837fec612bdf51054ca435557e585477adc56ae1489f85d4f6bf65f93c9',
    'verification/android-editor-preservation-completion/protocol-1/seal.json': 'e575641c10d690bf4b6e02843355a60d5b3077233c94fc5cb443be7f490584bd',
}
for rel, sha in contracts.items():
    assert ident(R / rel)['sha256'] == sha, rel
assert (C/'protocol.md').read_bytes() == (R/'verification/android-editor-preservation-completion/protocol-1/protocol.md').read_bytes()
assert (C/'required-amendment.md').read_bytes() == (R/'verification/android-editor-preservation-protocol-independent/required-amendment.md').read_bytes()

source = mapping(C / 'source')
base = mapping(B / 'source')
assert len(source) == 16 and source.keys() == base.keys()
assert digest(source) == seal['product_tree'] == 'cb5c2b813b9cb375f2907bafcb066ba9c556a2713ffd04c9d74777d9595d01e4'
changed = [name for name in source if source[name] != base[name]]
assert changed == ['NativeAppearanceViewsV2.java', 'NativeCoordinatorV2.java', 'NativeRenderer.java']
assert mapping(C / 'host-leaves') == mapping(B / 'host-leaves')
assert mapping(C / 'cross-source') == mapping(B / 'cross-source')
assert ident(C/'tests/EditorImplementationTests.java') == ident(B/'tests/EditorImplementationTests.java')
hook = '''            if (candidate != null) {
                try { renderer.completeFailedV2(candidate, ledger.primary, ledger.firstFatal); }
                catch (RuntimeException | Error cleanup) { remember(cleanup); }
            }
'''
coordinator = (C/'source/NativeCoordinatorV2.java').read_text()
assert coordinator.count(hook) == 2
assert coordinator.replace(hook, '') == (B/'source/NativeCoordinatorV2.java').read_text()
save('custody.json', {
    'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'candidate_seal': ident(C/'seal.json'), 'manifest': ident(C/'manifest.json'),
    'members_verified': count, 'member_bytes_verified': total,
    'product_tree': digest(source), 'changed_product_files': changed,
    'unchanged_product_files': [name for name in source if name not in changed],
    'host_leaf_count': len(mapping(C/'host-leaves')), 'host_leaves_unchanged': True,
    'cross_JNI_and_original52_source_unchanged': True,
    'coordinator_two_exact_hooks_removed_reconstitutes_entire_base': True,
    'contracts': {rel: ident(R/rel) for rel in contracts},
})

inputs = D/'inputs'
inputs.mkdir()
for folder in ('source', 'host-leaves'):
    shutil.copytree(C/folder, inputs/folder)
frozen = mapping(inputs)
save('source-map.json', frozen)
save('tools.json', {
    'python': sys.version, 'python_executable': str(Path(sys.executable).resolve()),
    'python_binary': ident(Path(sys.executable).resolve()),
    'jdk_home': str(J.resolve()),
    'tools': {str(p): ident(p.resolve()) for p in (J/'bin/javac', J/'bin/java', J/'bin/javap', J/'lib/modules', J/'lib/server/libjvm.dylib')},
})
scratch = Path(tempfile.mkdtemp(prefix='owned-tail-review-', dir=D))
commands = []
env = dict(os.environ)
for name in ('_JAVA_OPTIONS', 'JAVA_TOOL_OPTIONS', 'JDK_JAVA_OPTIONS', 'CLASSPATH', 'JAVA_OPTS', 'JDK_JAVAC_OPTIONS'):
    env.pop(name, None)
env['JAVA_HOME'] = str(J)
env['PATH'] = str(J/'bin') + os.pathsep + env.get('PATH', '')
env['TMPDIR'] = str(scratch)
env['TMP'] = str(scratch)
env['TEMP'] = str(scratch)
classes = scratch/'classes'
empty = scratch/'empty'
classes.mkdir()
empty.mkdir()

def run(name, argv):
    start = time.monotonic()
    with (D/(name+'.stdout')).open('wb') as out, (D/(name+'.stderr')).open('wb') as err:
        child = subprocess.Popen([str(x) for x in argv], cwd=R, env=env, stdout=out, stderr=err, start_new_session=True)
        try:
            child.wait(timeout=60)
        except BaseException:
            child.kill()
            child.wait()
            raise
    commands.append({'name': name, 'argv': [str(x) for x in argv], 'exit': child.returncode, 'elapsed_seconds': time.monotonic()-start, 'bound_seconds': 60, 'reaped': True, 'stdout': ident(D/(name+'.stdout')), 'stderr': ident(D/(name+'.stderr'))})
    save('commands.json', commands)
    assert child.returncode == 0, name

status = 'failed'
try:
    run('javac-version', [J/'bin/javac', '-version'])
    run('java-version', [J/'bin/java', '-version'])
    run('javap-version', [J/'bin/javap', '-version'])
    assert (D/'javac-version.stdout').read_text().startswith('javac 25')
    files = sorted((inputs/'source').glob('*.java')) + sorted((inputs/'host-leaves').rglob('*.java'))
    assert len(files) == 102
    run('compile', [J/'bin/javac', '-J-Djava.io.tmpdir='+str(scratch), '--release', '17', '-Xlint:all', '-Werror', '-proc:none', '-classpath', empty, '-sourcepath', empty, '-d', classes, *files])
    shutil.copytree(classes, D/'classes')
    save('class-map.json', mapping(D/'classes'))
    run('completion-bytecode', [J/'bin/javap', '-p', '-c', '-classpath', classes, 'dev.mixer.android.NativeRenderer', 'dev.mixer.android.NativeRenderer$2', 'dev.mixer.android.NativeRenderer$Candidate', 'dev.mixer.android.NativeRenderer$AttachmentJournal', 'dev.mixer.android.NativeAppearanceViewsV2$FieldPreservation', 'dev.mixer.android.NativeAppearanceViewsV2$Mutation', 'dev.mixer.android.NativeAppearanceViewsV2$NativeField', 'dev.mixer.android.NativeCoordinatorV2'])
    bytecode = (D/'completion-bytecode.stdout').read_text()
    def method(signature, next_signature):
        start = bytecode.index(signature)
        return bytecode[start:bytecode.index(next_signature, start)]
    proof = {}
    for name, sig, after in [
        ('finishV2', '  void finishV2(', '  void validateAttachedV2('),
        ('fieldPreservationBegin', '  public void fieldPreservationBegin(', '  public void fieldPreservationEnd('),
        ('fieldPreservationEnd', '  public void fieldPreservationEnd(', '  public void replacementEvent('),
    ]:
        body = method(sig, after)
        instructions = [line for line in body.splitlines() if re.match(r'\s+\d+:', line)]
        last_throw = max(i for i, line in enumerate(instructions) if re.search(r': athrow\b', line))
        tail = instructions[last_throw+1:]
        assert tail
        forbidden = [line for line in tail if re.search(r': (?:invoke\w*|new\w*|anewarray|multianewarray|athrow|monitor\w*)\b', line)]
        assert not forbidden, (name, forbidden)
        (D/(name+'-scalar-tail.bytecode')).write_text('\n'.join(tail)+'\n')
        (D/(name+'-full.bytecode')).write_text(body)
        proof[name] = {'tail_start': tail[0].strip(), 'instruction_count': len(tail), 'tail': ident(D/(name+'-scalar-tail.bytecode')), 'full_method': ident(D/(name+'-full.bytecode')), 'no_invocation_allocation_athrow_monitor': True}
    for name, sig, after in [
        ('fieldPreservationIdentityV2', '  boolean fieldPreservationIdentityV2(', '  private boolean preservationCohortV2('),
        ('preservationCohortV2', '  private boolean preservationCohortV2(', '  private boolean preservationFailureFundedV2('),
    ]:
        body = method(sig, after)
        assert not re.search(r': (?:invoke\w*|new\w*|anewarray|multianewarray|athrow|monitor\w*)\b', body), name
        (D/(name+'.bytecode')).write_text(body)
        proof[name] = {'direct_scalar_array_reference_only': True, 'method': ident(D/(name+'.bytecode'))}
    save('bytecode-proof.json', {'scope': 'Independent compilation of exact 16 product files plus unchanged 86 host leaves; no behavioral suite rerun', 'proofs': proof})
    assert mapping(inputs) == frozen
    assert mapping(C/'source') == source
    status = 'passed-scoped-host-compilation-and-bytecode-only'
finally:
    shutil.rmtree(scratch)
    save('execution-receipt.json', {'at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'status': status, 'commands': len(commands), 'source_map': ident(D/'source-map.json'), 'cleanup': {'owned_scratch_removed': not scratch.exists(), 'all_owned_children_reaped': all(row['reaped'] for row in commands), 'native_UI_capture_or_process_inventory_started_or_queried': False, 'other_projects_touched': False}, 'canonical_native_OTA_or_GA_accepted': False})
print(status)
