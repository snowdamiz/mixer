#!/usr/bin/env python3
"""Immutable keyboard runtime reuse with only the selected v2 oracle wrapper."""
import argparse
import hashlib
import importlib.util
import json
import pathlib
import signal
import subprocess
import sys
BASE=pathlib.Path(__file__).resolve().parent;ROOT=BASE.parents[1];PREVIOUS=BASE.parent/'apple-toggle-keyboard-focus'
# Keep this v2 module ahead of immutable runtime dependencies. Its oracle is
# selected explicitly; original runtime methods and source remain unchanged.
sys.path.append(str(PREVIOUS))
import keyboard_oracle as oracle
spec=importlib.util.spec_from_file_location('immutable_keyboard_runtime',PREVIOUS/'run.py')
runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)
sha=runtime.sha;read=runtime.read;require=runtime.require
runtime.BASE=BASE;runtime.inherited.BASE=BASE;runtime.inherited.PRODUCTS=BASE/'build/Build/Products';runtime.inherited.PRODUCT_ARCHIVE=BASE/'test-runner-products.tar.gz'


def verify():
    seal=read(BASE/'packet-seal.json');require(seal['schema']=='mixer.apple-toggle.keyboard-focus-v2.1','Wrong keyboard v2 seal')
    for name,digest in seal['files'].items():
        p=ROOT/runtime.artifact.relative_name(name);require(p.is_file() and not p.is_symlink() and sha(p)==digest,'Sealed v2 source changed: '+name)
    p=subprocess.run([sys.executable,'-B',str(PREVIOUS/'run.py'),'verify'],cwd=ROOT,capture_output=True,text=True,timeout=60)
    require(p.returncode==0,'Immutable keyboard preflight failed: '+p.stderr);prior=json.loads(p.stdout)
    require(prior['sealSHA256']=='da6c8a03853d8fa3b3a0361030d063d841efe510eff8a6e8bc81ff36dc7e5378','Original81file keyboard seal changed')
    reuse=read(BASE/'immutable-reuse.json')
    require(all(sha(ROOT/n)==d for n,d in reuse['copiedFiles'].items()),'Reused v2 app/runner/source bytes changed')
    require(all(sha(ROOT/n)==d for n,d in reuse['previousBindings'].items()),'Immutable parent or root repair selection changed')
    lock=read(BASE/'source-lock.json');source=BASE/'source';actual={str(p.relative_to(source)):sha(p) for p in sorted(source.rglob('*')) if p.is_file()}
    digest=hashlib.sha256(json.dumps(actual,sort_keys=True,separators=(',',':')).encode()).hexdigest();require(actual==lock['sha256'] and digest==seal['candidateSourceClosureSHA256']=='f9ddf3e2615a80930d551351e1496f12ea476cac3e8d1bfd38d8cd101a1d2a46','App source changed')
    app=read(BASE/'built-app-manifest.json');require(app['archiveSHA256']==seal['candidateArchiveSHA256']=='b9a864d11182ac546d76110d7d4ea342821df98d1e32b3474e57cf07de04b393','App manifest changed');runtime.artifact.archive_payload(BASE/'built-app.tar.gz',app,runtime.artifact.CONFIGS['diagnostic'])
    runner=read(BASE/'build-products-manifest.json');require(runtime.inherited.tree(runtime.inherited.PRODUCTS)==runner['products'],'Identical runner Products changed');runtime.inherited.product_archive_payload(runner)
    require(runner['productTreeSHA256']==seal['testRunnerProductTreeSHA256']=='121fdd3e3cf2416914a341ff3f2fbc6d9280e40c07bb46a59d50643b0f2d9bd7' and runner['productArchiveSHA256']==seal['testRunnerArchiveSHA256']=='8451ac5d484b2f8f5ddb9a83e096e25215a36445b161c2b4acac0dbf65d9cc18','Exact runner reuse mismatch')
    for name,digest in runner['sourceFiles'].items():
        require(sha(ROOT/name)==digest and sha(ROOT/name.replace('verification/apple-toggle-keyboard-focus/','verification/apple-toggle-keyboard-focus-v2/',1))==digest,'Runner source reuse changed')
    require(all(sha(pathlib.Path(name))==digest for name,digest in runner['toolFiles'].items()),'Official runner tool identity changed')
    controls=read(BASE/'host-controls.json');require(controls['exitCode']==0 and controls['testsRun']==controls['expectedTestsRun'] and controls['stderr'].rstrip().endswith('OK'),'V2 host controls failed')
    require(all(sha(ROOT/n)==d for n,d in controls['sourceFiles'].items()),'V2 control sources changed')
    require(runtime.oracle is oracle and runtime.transport.verdict is oracle.verdict,'V2 oracle not selected in inherited bridge')
    return {'schema':'mixer.apple-toggle.keyboard-v2-preflight.1','sealSHA256':sha(BASE/'packet-seal.json'),'prior81FileSealSHA256':prior['sealSHA256'],
            'candidateSourceClosureSHA256':seal['candidateSourceClosureSHA256'],'candidateArchiveSHA256':seal['candidateArchiveSHA256'],
            'testRunnerProductTreeSHA256':runner['productTreeSHA256'],'testRunnerArchiveSHA256':runner['productArchiveSHA256'],
            'pairedFocusPolicy':'Equality required; discrepancy remains failed evidence. Existing didUpdateFocus app signal required on app focus changes.',
            'acquisitionScope':'Strict three fixed elements, every Tab changes to observed fixed element, atmost12; no general system navigation.',
            'panPrerequisite':runtime.prerequisite(),'nativeExecution':False,'appOrRunnerRecompiled':False,'gaAccepted':False}

runtime.inherited.verify=verify
# Class methods remain the exact reviewed runtime implementation. Attribute
# forwarding also makes their immutable provenance available to host controls.
def __getattr__(name):return getattr(runtime,name)

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['verify','run','cleanup']);p.add_argument('--scope',choices=['interaction'],default='interaction');p.add_argument('--reviewed-seal');a=p.parse_args()
    if a.action=='verify':print(json.dumps(verify(),sort_keys=True))
    elif a.action=='run':runtime.prerequisite();runtime.inherited.run(a.reviewed_seal,a.scope)
    else:
        h=runtime.inherited;h.RUN_DIR=h.select_runtime_directory(a.scope);life=read(h.RUN_DIR/'lifecycle.json');require(life['verifiedHandoff']['sealSHA256']==verify()['sealSHA256'],'Cleanup v2 handoff changed');commands=runtime.ExportingCommands(h.RUN_DIR/'recovery-commands.json')
        values=h.cleanup_independently([('owned-simulator-and-baseline-reconciliation',lambda:h.cleanup(life,commands)),('ephemeral-capability-workspace-removal',lambda:h.remove_ephemeral(life))]);life.update(cleanedUp=all(x['passed'] for x in values),recoveryCleanupResults=values);h.write(h.RUN_DIR/'lifecycle.json',life);require(life['cleanedUp'],'V2 recovery cleanup incomplete')
if __name__=='__main__':
    def stop(signum,frame):raise KeyboardInterrupt('Root keyboard v2 harness interrupted')
    signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop);main()
