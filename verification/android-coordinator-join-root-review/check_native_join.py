#!/usr/bin/env python3
"""Replay actual API37 receipts, saved packets and cleanup without native tools."""
import datetime
import hashlib
import json
from pathlib import Path
import platform
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
RUN=ROOT/'verification/android-coordinator-apk-packaging/runtime-1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def nodes(root):
    result={}
    def visit(node):
        assert node['id'] not in result
        result[node['id']]=node
        for child in node['children']:visit(child)
    visit(root)
    return result

def main():
    r=read(RUN/'receipt.json');n=read(RUN/'native-results.json');seal=read(RUN/'artifact-seal.json');bindings={}
    for name,item in seal.items():
        p=RUN/name;assert p.is_file() and not p.is_symlink()
        assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256'],name
        bindings[str(p.relative_to(ROOT))]=sha(p)
    assert r['status']=='actual-API37-private-ordinary-join-bounded-subset-passed'
    assert r['native']=={'status':'passed','checks':64,'operations':8}
    assert n['status']=='passed' and n['checks']==64 and n['operations']==8
    checks=[x for x in n['observations'] if 'check' in x]
    assert len(checks)==64 and all(x['passed'] is True for x in checks)
    assert not any('failure' in x for x in n['observations'])
    click=[x for x in n['observations'] if 'nativeSwitchPerformClick' in x]
    assert click==[{'hasOnClickListenersBefore':False,'nativeSwitchPerformClick':'invoked','performClickReturned':False}]
    packets={};parsed={}
    for name,item in n['packets'].items():
        p=RUN/item['file'];assert sha(p)==item['sha256']
        packet=read(p);ns=nodes(packet['document']['root'])
        assert len(ns)==item['nodeCount']==12
        assert str(packet['document']['revision'])==item['revision']
        packets[name]=p.read_bytes();parsed[name]=(packet,ns)
    assert set(packets)=={'jni-initial','jni-committed','joined-initial','joined-toggle','joined-text','joined-environment','joined-relaunched'}
    assert packets['jni-initial']==packets['joined-initial']==packets['joined-relaunched']
    assert packets['jni-committed']==packets['joined-toggle']
    assert packets['joined-text']==packets['joined-environment']
    for name,revision,checked,draft in [('joined-initial',1,False,''),('joined-toggle',2,True,''),('joined-text',3,True,'joined'),('joined-relaunched',1,False,'')]:
        packet,ns=parsed[name]
        assert packet['document']['revision']==revision
        assert ns['task.1']['properties']['value'] is checked
        assert ns['draft']['properties']['value']==draft
        assert packet['identities']==parsed['joined-initial'][0]['identities']
    commands={c['name']:c for c in r['commands']}
    assert len(commands)==len(r['commands'])
    for c in commands.values():
        assert sha(RUN/c['output'])==c['sha256']
        assert c['ownedCommandGroupCleanup']['after']==[]
        if Path(c['argv'][0]).name=='adb' and c['name']!='adb-version':assert c['argv'][1:3]==['-s','emulator-5586']
    for name in ['apk-zipalign-preinstall','install-private-apk','installed-apk-hash','actual-native-join','native-results-export','stop-only-owned-emulator']:
        assert commands[name]['exitCode']==0,name
    assert (RUN/'installed-apk-hash.log').read_text().split()[0]==r['apkSHA256']=='78af8c5df197fb6f163f3010825648a1b1a50427c9ab963b1c5aeca1e513b3ba'
    text=(RUN/'actual-native-join.log').read_bytes()
    assert b'INSTRUMENTATION_RESULT: status=passed' in text and b'INSTRUMENTATION_CODE: -1' in text
    assert r['target']['ro.build.version.sdk']=='37' and r['target']['ro.product.cpu.abi']=='arm64-v8a'
    assert r['target']['ro.kernel.qemu']=='1' and r['target']['sys.boot_completed']=='1'
    assert r['cleanup']=='stopped' and r['ownedEmulatorGroupCleanup']['after']==[]
    assert r['ownedEmulatorGroupCleanup']['group']==r['ownedInstance']['pid']
    for port in [5586,5587]:
        assert commands[f'port-after-{port}']['exitCode']==1
        assert (RUN/f'port-after-{port}.log').read_bytes()==b''
    cleanup=r['extractionCleanup']
    assert cleanup['status']=='removed' and cleanup['pathAbsentAfterCleanup'] and not Path(cleanup['path']).exists()
    assert cleanup['files']==177 and cleanup['openHoldersCheck']['exitCode']==1
    assert not r['physicalTargetsQueried']
    assert read(RUN/'apk-packaging-preinstall.json')==r['packagingPreDispatch']
    for name in ['apk-packaging-dispatch.json','apk-packaging-build-acceptance.json']:
        p=HERE/name;bound=read(p)
        for path,expected in bound['bindings'].items():assert sha(ROOT/path)==expected,path
        bindings[str(p.relative_to(ROOT))]=sha(p)
    for p in [RUN/'receipt.json',RUN/'artifact-seal.json',Path(__file__)]:bindings[str(p.relative_to(ROOT))]=sha(p)
    result={'schema':1,'observedUTC':datetime.datetime.now(datetime.UTC).isoformat(),'status':'accepted-actual-API37-private-ordinary-join-bounded-development-subset','command':['python3','-B',str(Path(__file__).relative_to(ROOT))],'pythonVersion':platform.python_version(),'sourceRevision':r['sourceRevision'],'sourceClosureSHA256':r['sourceClosureSHA256'],'apkSHA256':r['apkSHA256'],'runtimeArtifactFiles':len(seal),'rootBindings':len(bindings),'nativeChecks':64,'nativeOperations':8,'actualPacketsIndependentlyDecoded':7,'environment':r['target'],'ownedInstance':r['ownedInstance'],'ownedProcessGroupCleanup':r['ownedEmulatorGroupCleanup'],'extractionCleanup':cleanup,'scope':'Actual JNI/Swift ordinary registry/ChecklistEngine, coordinator, concrete renderer, performClick callback and direct InputConnection subset. Actual pending-engine token survives environment-only refresh; attachment fault, Activity destruction/relaunch and malformed-input retirement pass.','limitations':['No injected touch/drag/scroll or system keyboard/composition workflow qualification.','No hardware/compositor paint, full native fault/accessibility/lifecycle matrix or cross-platform shared appearance parity.','Private API37 arm64/default environment only; API36, other resources/platforms, public V2 and signed authority remain pending.','Physical phones, immutable published separate-repository FieldLog, stores/customers/operations and GA remain pending.'],'nativeDevelopmentSubsetAccepted':True,'fullNativeAccepted':False,'physicalAccepted':False,'gaAccepted':False,'bindings':bindings}
    (HERE/'native-join-acceptance.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['status','runtimeArtifactFiles','rootBindings','nativeChecks','nativeOperations','actualPacketsIndependentlyDecoded']}))
if __name__=='__main__':main()
