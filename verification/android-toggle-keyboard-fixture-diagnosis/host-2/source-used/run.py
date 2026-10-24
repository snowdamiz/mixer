#!/usr/bin/env python3
"""Root-only fresh fixture keyboard setup run; host preparation grants no native authority."""
import argparse,difflib,hashlib,os
from types import ModuleType
import support
def derive(source,contract):
    old=support.read(support.SCROLL/'runner-contract.json')
    pairs=[('new-private-package',"PACKAGE = '"+support.previous.PACKAGE+"'","PACKAGE = '"+support.PACKAGE+"'"),
        ('new-fixture-closure',"SOURCE_CLOSURE_SHA256 = '"+old['sourceClosureSHA256']+"'","SOURCE_CLOSURE_SHA256 = '"+contract['sourceClosureSHA256']+"'"),
        ('candidate-status',"actual-API37-fixture-scroll-reset-fix-component-only-passed","actual-API37-fixture-keyboard-setup-component-only-passed")]
    deltas=[]
    for name,before,after in pairs:
        if source.count(before)!=1:raise ValueError('finite source site '+name)
        source=source.replace(before,after,1);deltas.append({'name':name,'occurrences':1,'beforeSHA256':hashlib.sha256(before.encode()).hexdigest(),'afterSHA256':hashlib.sha256(after.encode()).hexdigest()})
    return source,deltas
def load_runner():
    contract=support.read(support.HERE/'runner-contract.json')
    for name,binding in contract['implementationBindings'].items():
        if support.bind(support.HERE/name)!=binding:raise ValueError('keyboard implementation drift '+name)
    for path,binding in contract['toolBindings'].items():
        if support.bind(path)!=binding:raise ValueError('runner tool drift '+path)
    inherited,original,_=support.repair_runner()
    if hashlib.sha256(original.encode()).hexdigest()!=contract['upstreamConcreteSHA256']:raise ValueError('upstream concrete drift')
    source,deltas=derive(original,contract)
    if hashlib.sha256(source.encode()).hexdigest()!=contract['concreteSHA256'] or deltas!=contract['sourceDeltas'] or source!=(support.HERE/'derived-runner.py').read_text():raise ValueError('reset derived source drift')
    module=ModuleType('isolated_keyboard_setup');module.__file__=str(support.HERE/'run.py')
    for name in ('_accepted_helper','_helper_path','_wifi_identity','_accepted_wifi_sha_globals','_packaging_check_path','_output','_pointer_validate_native','_authored_component_collect','_repair_capture','_repair_bind_diagnostic','_scroll_capture','_scroll_bind'):setattr(module,name,getattr(inherited,name))
    oracle=support.load('keyboard_setup_bound_oracle',support.HERE/'keyboard_oracle.py');module._authored_component_collect=oracle.collect
    module._authored_bind=support.frozen;module._authored_extract=support.extract;module._authored_inventory=support.inventory;module._authored_copy_component_metadata=support.copy_metadata;module._pointer_runtime_directory=support.runtime_directory
    module._authored_content_identity={'contractSHA256':support.sha(support.HERE/'runner-contract.json'),'concreteSHA256':contract['concreteSHA256'],'wrapperSHA256':support.sha(__file__),'sourceClosureSHA256':contract['sourceClosureSHA256'],'sourceUnchanged':False}
    module._ADAPTATION={'ancestry':inherited._ADAPTATION,'fixtureKeyboardSetup':module._authored_content_identity,'sourceDeltas':deltas,'productCause':'undetermined; independently observed keyboard-mode setup candidate; full45 native acceptance pending','nativeAuthority':'explicit root dispatch only','originalGestureSemanticsUnchanged':True,'observerTimingPerturbation':True}
    exec(compile(source,str(support.HERE/'derived-runner.py'),'exec'),module.__dict__)
    return module,source,''.join(difflib.unified_diff(original.splitlines(keepends=True),source.splitlines(keepends=True),fromfile='frozen-extent-fix-concrete',tofile='fixture-scroll-reset-fix-concrete'))
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--build',required=True,choices=['candidate-3']);parser.add_argument('--attempt',required=True);parser.add_argument('--execute-native',action='store_true');args=parser.parse_args()
    if not args.execute_native:parser.error('native NOT RUN; explicit root dispatch required')
    if os.environ.get('JAVA_HOME')!=str(support.JDK):raise ValueError('command-local JAVA_HOME must select bound OpenJDK25')
    support.runtime_directory(args.attempt);support.check_packet();support.frozen();runner,_,_=load_runner();runner.main()
if __name__=='__main__':main()
