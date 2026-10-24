#!/usr/bin/env python3
"""Separate root-dispatch wrapper for frozen authored candidate-3 and component supplement-3."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
from types import ModuleType
import support

CONTRACT_SHA256 = 'db6d4b31ffaa128802d4cdd17bb923cc20baa04f4c0abe1c76330232f52b8db4'

def replacements(source, variant):
    begin = source.index('def bind_candidate(built):\n')
    end = source.index('\n\nclass ExtractionCleanupRefused', begin)
    archive_begin = source.index("        archive_path = built / 'built-artifacts.tar.gz'\n")
    archive_end = source.index("        apk = work / 'coordinator-join.apk'\n", archive_begin)
    git_begin = source.index("        _, revision = run('runner-source-revision'")
    git_end = source.index("        run('python-version'", git_begin)
    pairs = [
        ('build-directory', "BUILDS = ROOT / 'verification/android-pointer-oracle-repair'", "BUILDS = ROOT / 'verification/android-authored-toggle-input'"),
        ('candidate-identity', "SOURCE_CLOSURE_SHA256 = '9082e2de1327bd0784d752db5dfbe4484751d565b3410e01e78664321467f5ce'", "SOURCE_CLOSURE_SHA256 = '"+(support.CLOSURE if variant=='baseline' else support.SUPPLEMENT_CLOSURE)+"'"),
        ('explicit-new-bind', source[begin:end], "def bind_candidate(built):\n    if built != BUILDS / 'candidate-3': raise ValueError('only frozen candidate-3 input allowed')\n    return _authored_bind('"+variant+"')\n"),
        ('candidate-help', "help='frozen private actual-pointer candidate-5 only'", "help='authored candidate-3; explicit new source identity'"),
        ('candidate-cli', "if args.build != 'candidate-5'", "if args.build != 'candidate-3'"),
        ('candidate-error', "bound pointer candidate-5 and fresh runtime-N required", "bound authored candidate-3 and fresh runtime-N required"),
        ('truthful-source-repair', "if metadata['status'] != 'actual-private-apk-built-runtime-NOT-RUN' or not metadata['sourceUnchanged']:", "if metadata['status'] != 'authored-frozen-candidate-ready-runtime-NOT-RUN' or metadata['sourceUnchanged']:"),
        ('truthful-source-repair-error', "successful unchanged-source build required", "selected repaired-source build required; sourceUnchanged must be false"),
        ('exact183-payload', source[archive_begin:archive_end], "        artifacts = _authored_inventory('"+variant+"')\n        _authored_extract(work, '"+variant+"')\n"),
        ('source-identity-predispatch', source[source.index("        save(out / 'source-identity-predispatch.json'"):source.index("        run('apk-zipalign-predispatch'", source.index("        save(out / 'source-identity-predispatch.json'"))], "        save(out / 'source-identity-predispatch.json', metadata)\n"),
        ('contextual-revision-no-git', source[git_begin:git_end], "        receipt['adaptation']['runnerSourceRevisionContext'] = metadata['sourceRevision']\n        receipt['adaptation']['runnerContentIdentity'] = _authored_content_identity\n"),
        ('source-identity-preinstall', source[source.index("        save(out / 'source-identity-preinstall.json'"):source.index("        _, signature = run('apk-apksigner-preinstall'", source.index("        save(out / 'source-identity-preinstall.json'"))], "        save(out / 'source-identity-preinstall.json', preinstall)\n"),
        ('strict-json-native', 'native = json.loads(content)', 'native = _authored_parse(content)'),
    ]
    if variant == 'supplement':
        export_begin = source.index("        code, instrument = run('actual-native-pointer'")
        export_end = source.index('    except BaseException as failure:', export_begin)
        pairs += [
            ('component-package', "PACKAGE = 'dev.mixer.android.coordinatorjoin'", "PACKAGE = 'dev.mixer.android.authoredtoggle'"),
            ('component-build-receipt-copy', "        for name in ['receipt.json', 'source-lock.json', 'built-artifacts.json']:\n            (out / ('build-' + name)).write_bytes((built / name).read_bytes())\n", "        _authored_copy_component_metadata(out)\n"),
            ('component-instrumentation-and-exports', source[export_begin:export_end], """        code, instrument = run('actual-native-component', adb + ['shell', 'am', 'instrument', '-w',
            '-e', 'apkSHA256', metadata['apkSHA256'], '-e', 'sourceClosureSHA256', metadata['sourceClosureSHA256'],
            PACKAGE + '/dev.mixer.android.AuthoredToggleSupplementInstrumentation'], timeout=120, allow_failure=True)
        receipt['native'] = _authored_component_collect(run, adb, PACKAGE, out, metadata, code, instrument)
        receipt['status'] = 'actual-API37-authored-toggle-component-only-passed'
"""),
            ('component-scope', "'scope': 'bounded actual API37 private pointer delivery/state subset only; internal callbacks unobserved; native IME/accessibility/public/signed/physical/FieldLog/store/operational/GA pending'", "'scope': 'actual View component supplement only; direct View touch except worker ScrollView arbitration; fixture acknowledgements are not engine commits; screenshot pixels/TalkBack/renderer authority/physical/Apple/public/FieldLog/store/operational/GA pending'"),
        ]
        # The full component replacement already contains strict parsing in its collector.
        pairs = [p for p in pairs if p[0] not in ('strict-json-native',)]
    return pairs

def derive(source, variant):
    deltas = []
    for name, old, new in replacements(source, variant):
        count = source.count(old)
        if count != 1: raise ValueError('finite source site '+name+' observed '+str(count))
        source = source.replace(old,new,1)
        deltas.append({'name':name, 'count':count, 'beforeSHA256':hashlib.sha256(old.encode()).hexdigest(), 'afterSHA256':hashlib.sha256(new.encode()).hexdigest()})
    return source, deltas

def load_runner(variant='baseline'):
    path = support.HERE / 'runner-contract.json'
    if support.sha(path) != CONTRACT_SHA256: raise ValueError('authored runner contract drift')
    contract = support.read(path)
    for name,digest in contract['implementationBindings'].items():
        if support.sha(support.HERE/name) != digest: raise ValueError('runner implementation drift '+name)
    for name,digest in contract['toolBindings'].items():
        if support.sha(name) != digest: raise ValueError('runner tool drift '+name)
    inherited, original = support.prior()
    source, deltas = derive(original,variant)
    selected = contract['variants'][variant]
    if hashlib.sha256(source.encode()).hexdigest() != selected['concreteSHA256'] or deltas != selected['sourceDeltas']: raise ValueError('derived concrete drift')
    if source != (support.HERE/selected['concreteFile']).read_text(): raise ValueError('retained concrete differs')
    module = ModuleType('authored_private_'+variant)
    module.__file__ = str(support.HERE / 'run.py')
    for name in ('_accepted_helper','_helper_path','_wifi_identity','_accepted_wifi_sha_globals','_packaging_check_path','_output','_pointer_validate_native'):
        setattr(module,name,getattr(inherited,name))
    module._authored_bind = support.frozen
    module._authored_extract = support.extract
    module._authored_inventory = support.inventory
    module._authored_parse = support.read_bytes
    module._authored_copy_component_metadata = support.copy_component_metadata
    module._pointer_runtime_directory = support.runtime_directory
    module._authored_content_identity = {'contractSHA256':CONTRACT_SHA256,'concreteSHA256':selected['concreteSHA256'],'wrapperSHA256':support.sha(__file__),'sourceTree':support.CLOSURE}
    component = support.load('authored_component_oracle', support.HERE / 'supplement_oracle.py')
    module._authored_component_collect = component.collect
    module._ADAPTATION = {'ancestry':inherited._ADAPTATION, 'authoredToggle':dict(module._authored_content_identity, variant=variant, sourceDeltas=deltas, concreteSourceChanged=True, sourceUnchanged=False, nativeAuthority='explicit root dispatch only; host controls do not grant acceptance')}
    exec(compile(source,str(support.HERE/selected['concreteFile']),'exec'),module.__dict__)
    return module,source,''.join(difflib.unified_diff(original.splitlines(keepends=True),source.splitlines(keepends=True),fromfile='reviewed-candidate5-concrete.py',tofile=selected['concreteFile']))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', required=True, choices=['candidate-3'])
    parser.add_argument('--attempt', required=True)
    parser.add_argument('--supplement', choices=['supplement-3'])
    parser.add_argument('--execute-native', action='store_true')
    args = parser.parse_args()
    if not args.execute_native: parser.error('native NOT RUN; explicit root dispatch required')
    support.runtime_directory(args.attempt)
    support.load('authored_runner_verify',support.HERE/'verify.py').check()
    variant = 'supplement' if args.supplement else 'baseline'
    runner,_,_ = load_runner(variant)
    # Derived concrete uses the original baseline CLI and untouched cleanup/input schedule.
    # The optional supplement selector has already chosen its own frozen concrete source.
    import sys
    original_argv = sys.argv
    sys.argv = [original_argv[0], '--build', args.build, '--attempt', args.attempt, '--execute-native']
    try: runner.main()
    finally: sys.argv = original_argv

if __name__ == '__main__': main()
