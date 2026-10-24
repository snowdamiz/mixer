#!/usr/bin/env python3
"""Root-only finite diagnostic dispatch for the isolated authored-toggle fixture repair."""
import argparse,difflib,hashlib,os,sys
from types import ModuleType
import support

def derive(source,contract):
    begin=source.index("        code, instrument = run('actual-native-component'")
    end=source.index('    except BaseException as failure:',begin)
    pairs=[
        ('new-private-package',"PACKAGE = 'dev.mixer.android.authoredtoggle'","PACKAGE = 'dev.mixer.android.authoredtogglerepair'"),
        ('new-fixture-closure',"SOURCE_CLOSURE_SHA256 = '"+support.old.SUPPLEMENT_CLOSURE+"'","SOURCE_CLOSURE_SHA256 = '"+contract['sourceClosureSHA256']+"'"),
        ('independent-owned-diagnostics-before-unchanged-cleanup',source[begin:end],'''        instrument = b''
        try:
            code, instrument = run('actual-native-component', adb + ['shell', 'am', 'instrument', '-w',
                '-e', 'apkSHA256', metadata['apkSHA256'], '-e', 'sourceClosureSHA256', metadata['sourceClosureSHA256'],
                PACKAGE + '/dev.mixer.android.AuthoredToggleSupplementInstrumentation'], timeout=120, allow_failure=True)
            receipt['native'] = _authored_component_collect(run, adb, PACKAGE, out, metadata, code, instrument)
        finally:
            _repair_capture(execute, owned_identity, process, adb, PACKAGE, out, receipt, ROOT)
            _repair_bind_diagnostic(receipt['diagnostics'], instrument)
        if not receipt['diagnostics']['fixtureDiagnosticBindingVerified']:
            raise ValueError('private fixture diagnostics missing or unbound')
        receipt['status'] = 'actual-API37-authored-toggle-component-only-passed'
''')]
    deltas=[]
    for name,before,after in pairs:
        if source.count(before)!=1:raise ValueError('finite source site '+name)
        source=source.replace(before,after,1);deltas.append({'name':name,'occurrences':1,'beforeSHA256':hashlib.sha256(before.encode()).hexdigest(),'afterSHA256':hashlib.sha256(after.encode()).hexdigest()})
    return source,deltas

def load_runner():
    contract=support.read(support.HERE/'runner-contract.json')
    for name,binding in contract['implementationBindings'].items():
        if support.bind(support.HERE/name)!=binding:raise ValueError('repair implementation drift '+name)
    for path,binding in contract['toolBindings'].items():
        if support.bind(path)!=binding:raise ValueError('runner tool drift '+path)
    inherited,original,_=support.old_runner()
    if hashlib.sha256(original.encode()).hexdigest()!=contract['originalConcreteSHA256']:raise ValueError('original concrete drift')
    source,deltas=derive(original,contract)
    if hashlib.sha256(source.encode()).hexdigest()!=contract['concreteSHA256'] or deltas!=contract['sourceDeltas'] or source!=(support.HERE/'derived-runner.py').read_text():raise ValueError('repair derived source drift')
    module=ModuleType('isolated_authored_supplement_repair');module.__file__=str(support.HERE/'run.py')
    for name in ('_accepted_helper','_helper_path','_wifi_identity','_accepted_wifi_sha_globals','_packaging_check_path','_output','_pointer_validate_native','_authored_component_collect'):setattr(module,name,getattr(inherited,name))
    module._authored_bind=support.frozen;module._authored_extract=support.extract;module._authored_inventory=support.inventory;module._authored_copy_component_metadata=support.copy_metadata;module._pointer_runtime_directory=support.runtime_directory
    module._authored_content_identity={'contractSHA256':support.sha(support.HERE/'runner-contract.json'),'concreteSHA256':contract['concreteSHA256'],'wrapperSHA256':support.sha(__file__),'sourceClosureSHA256':contract['sourceClosureSHA256'],'sourceUnchanged':False}
    diag=support.load('isolated_repair_diagnostics',support.HERE/'diagnostics.py');module._repair_capture=diag.capture;module._repair_bind_diagnostic=diag.bind_fixture
    module._ADAPTATION={'ancestry':inherited._ADAPTATION,'isolatedSupplementRepair':module._authored_content_identity,'sourceDeltas':deltas,'productCause':'not inferred; root native probe required','diagnosticRetainedBudgetBytes':2*diag.LIMIT+131072+8192,'inheritedLogBudgetBytes':33554432,'nativeAuthority':'explicit root dispatch only'}
    exec(compile(source,str(support.HERE/'derived-runner.py'),'exec'),module.__dict__)
    return module,source,''.join(difflib.unified_diff(original.splitlines(keepends=True),source.splitlines(keepends=True),fromfile='immutable-original-supplement-concrete',tofile='isolated-repair-concrete'))

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--build',required=True,choices=['candidate-3']);parser.add_argument('--attempt',required=True);parser.add_argument('--execute-native',action='store_true');args=parser.parse_args()
    if not args.execute_native:parser.error('native NOT RUN; explicit root dispatch required')
    if os.environ.get('JAVA_HOME')!=str(support.JDK):raise ValueError('command-local JAVA_HOME must select bound OpenJDK25')
    support.runtime_directory(args.attempt);support.check_packet();support.frozen();runner,_,_=load_runner();runner.main()
if __name__=='__main__':main()
