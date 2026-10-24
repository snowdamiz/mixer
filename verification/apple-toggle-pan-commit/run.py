#!/usr/bin/env python3
"""Private unified runner. Native lifecycle/cleanup remains the immutable parent implementation."""
import argparse
import hashlib
import importlib.util
import json
import pathlib
import signal
import subprocess
import sys

BASE=pathlib.Path(__file__).resolve().parent;ROOT=BASE.parents[1]
PARENT=ROOT/'verification/apple-toggle-pan-origin-correction'
sys.path.insert(0,str(PARENT))
import harness as inherited
import apps as artifact
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_bytes())
require=artifact.require
original_manifest=artifact.expected_manifest

def expected_manifest(key):
    return read(BASE/'built-app-manifest.json') if key=='diagnostic' else original_manifest(key)
artifact.expected_manifest=expected_manifest

class CandidateApps:
    CONFIGS=artifact.CONFIGS
    @staticmethod
    def restore(destination,key):
        config=artifact.CONFIGS[key];manifest=expected_manifest(key)
        folder=BASE if key=='diagnostic' else artifact.ORIGINAL/config['folder']
        payload,modes=artifact.archive_payload(folder/'built-app.tar.gz',manifest,config)
        require(not destination.exists() and not destination.is_symlink() and destination.resolve()==destination,'Fresh canonical restore destination required')
        destination.mkdir(parents=True);app=destination/config['app']
        for directory in [app,app/'Frameworks',app/'_CodeSignature']:directory.mkdir(exist_ok=True);directory.chmod(0o755)
        for name,value in payload.items():
            target=app/artifact.relative_name(name);target.write_bytes(value);target.chmod(modes[name])
        return artifact.verify_restored(app,key)
    verify_installed=staticmethod(artifact.verify_installed)


def verify():
    seal=read(BASE/'packet-seal.json')
    require(seal['schema']=='mixer.apple-toggle.pan-commit.1','Wrong pan commit packet')
    for name,digest in seal['files'].items():
        p=ROOT/artifact.relative_name(name);require(p.is_file() and not p.is_symlink() and sha(p)==digest,'Sealed source changed: '+name)
    # Parent native and original packets, original strict oracles, archived apps,
    # original runner and historical failure observations are verified unchanged.
    parent_path=ROOT/'verification/apple-toggle-native-interruption'
    cmd=[sys.executable,'-B',str(parent_path/'run.py'),'verify']
    p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=60)
    require(p.returncode==0,'Parent verifier failed: '+p.stderr)
    parent=json.loads(p.stdout)
    selection=read(BASE/'selection.json')
    require(parent['sealSHA256']==selection['baselineSealSHA256']=='2e3b03b2833a53364f15f327e0d25b320ad81b5f6c1048b56c933a0af136baa7','Baseline identity changed')
    source=BASE/'source'
    actual={str(p.relative_to(source)):sha(p) for p in sorted(source.rglob('*')) if p.is_file() and not p.is_symlink()}
    lock=read(BASE/'source-lock.json');require(actual==lock['sha256'],'Candidate source lock mismatch')
    digest=hashlib.sha256(json.dumps(actual,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    require(digest==lock['sourceClosureSHA256']==seal['candidateSourceClosureSHA256'],'Candidate closure mismatch')
    changed=sorted(k for k in set(actual)|set(selection['sourceBefore']) if actual.get(k)!=selection['sourceBefore'].get(k))
    require(changed==['Prototype/AuthoredToggleCarrier.swift','Prototype/PanCommitChecks.swift','Prototype/main.swift'],'Candidate escaped private repair/fixture changes')
    require(sha(ROOT/selection['contract'])==selection['contractSHA256'],'Contract changed')
    receipt=read(BASE/'receipt.json');manifest=expected_manifest('diagnostic');commands=read(BASE/receipt['buildCommands'])
    require(receipt['sourceClosureSHA256']==digest and receipt['archiveSHA256']==manifest['archiveSHA256']==seal['candidateArchiveSHA256'],'Build receipt mismatch')
    require(commands and all(x['exitCode']==0 for x in commands),'Candidate build failed')
    compiled={v.split('/source/',1)[1] for command in commands for v in command['argv'] if '/source/' in v and v.endswith('.swift')}
    require(compiled=={n for n in actual if n.endswith('.swift')},'Exact compile source set mismatch')
    require(all(sha(pathlib.Path(n))==d for n,d in receipt['toolFiles'].items()),'Candidate compiler/tools changed')
    payload,_=artifact.archive_payload(BASE/'built-app.tar.gz',manifest,artifact.CONFIGS['diagnostic'])
    binaries={n:artifact.frozen.macho(payload[n]) for n in [artifact.CONFIGS['diagnostic']['executable'],'Frameworks/libMixerCore.dylib','Frameworks/libMixerUI.dylib']}
    runner=read(BASE/'build-products-manifest.json')
    require(inherited.tree(inherited.PRODUCTS)==runner['products'],'Unified runner tree changed')
    require(hashlib.sha256(inherited.json_bytes(runner['products'])).hexdigest()==runner['productTreeSHA256'],'Runner tree digest mismatch')
    inherited.product_archive_payload(runner)
    require(all(sha(ROOT/n)==d for n,d in runner['sourceFiles'].items()),'Runner build sources changed')
    require(all(sha(pathlib.Path(n))==d for n,d in runner['toolFiles'].items()),'Runner tools changed')
    controls=read(BASE/'host-controls.json')
    require(controls['exitCode']==0 and controls['testsRun']==10 and controls['stderr'].rstrip().endswith('OK'),'Host controls failed')
    require(all(sha(ROOT/n)==d for n,d in controls['sourceFiles'].items()),'Host control sources changed')
    require(len(oracle.CASES)==len(METHODS)==43,'Closed unified coverage changed')
    return {'schema':'mixer.apple-toggle.pan-commit-preflight.1','sealSHA256':sha(BASE/'packet-seal.json'),
            'candidateSourceClosureSHA256':digest,'candidateArchiveSHA256':manifest['archiveSHA256'],
            'testRunnerProductTreeSHA256':runner['productTreeSHA256'],'testRunnerArchiveSHA256':runner['productArchiveSHA256'],
            'binaryBuildVersions':binaries,'parent':parent,'changedDiagnosticFiles':changed,
            'harnessScope':'43publicXCTest methods:45native input actions plus one scoped36direct-component result. Original19diagnostic strict checks retain four reference failures.',
            'nativeExecution':False,'physicalDevicesQueried':False,'physicalPhones':'disconnected-deferred','gaAccepted':False}

# Dedicated-process adaptation only: originals remain immutable; no new HTTP
# endpoints, process/device authority, command grammar or cleanup operations.
spec=importlib.util.spec_from_file_location('pan_commit_unified_oracle',BASE/'commit_oracle.py')
oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
import bridge as inherited_bridge
for name in ['ACTIONS','CASES','CASE_ACTION','CASE_COMMAND_SEQUENCE','COMMANDS','geometry_valid','verdict']:
    setattr(inherited_bridge,name,getattr(oracle,name))
METHODS=inherited.INTERACTION_METHODS+[x['method'] for x in oracle.interruption.SPECS.values()]+[x['method'] for x in oracle.SPECS.values()]+['testSemanticScopedCallbackComponents']
inherited.BASE=BASE
inherited.PRODUCTS=BASE/'build/Build/Products'
inherited.PRODUCT_ARCHIVE=BASE/'test-runner-products.tar.gz'
inherited.packet=CandidateApps
inherited.verify=verify
inherited.SCOPES={'interaction':{'cases':oracle.CASES,'methods':METHODS}}
original_summary=inherited.runtime_summary

def summary(*args,**kwargs):
    value=original_summary(*args,**kwargs)
    direct=value.pop('directOriginalVerdicts')
    value.update(schema='mixer.apple-toggle.pan-commit-runtime.1',
                 expectedXCTestMethods=43,expectedNativeInputActions=45,expectedScopedDirectResults=1,
                 scopedDirectComponentVerdicts=direct,
                 directOriginalVerdicts=None if direct is None else [r.get('originalStrictVerdict') for r in direct],
                 directOriginalScope='Original19strict diagnostic suite retained unchanged and failed; comparator direct failure suite omitted',
                 qualification='Private native45input actions and36scoped direct components only; no physical VoiceOver, production Apple adapter, full parity, external dogfood or GA')
    native=value['nativeUserInteractionVerdicts']
    value['strictQualifiedVerdictsPassed']=value['strictNativeVerdictsPassed']
    value['strictNativeVerdictsPassed']=None if native is None else len(native)==45 and all(r['passed'] is True for r in native)
    value['scopedDirectComponentsPassed']=None if direct is None else len(direct)==1 and all(r['passed'] is True for r in direct)
    value['nativeInputActionsObserved']=None if native is None else len(native)
    value['scopedDirectResultsObserved']=None if direct is None else len(direct)
    return value
inherited.runtime_summary=summary


def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['verify','run','cleanup']);parser.add_argument('--reviewed-seal');parser.add_argument('--scope',choices=['interaction'],default='interaction');a=parser.parse_args()
    if a.action=='verify':print(json.dumps(verify(),sort_keys=True))
    elif a.action=='run':inherited.run(a.reviewed_seal,a.scope)
    else:
        inherited.RUN_DIR=inherited.select_runtime_directory(a.scope);life=read(inherited.RUN_DIR/'lifecycle.json')
        require(life['verifiedHandoff']['sealSHA256']==verify()['sealSHA256'],'Recovery identity changed')
        commands=inherited.Commands(inherited.RUN_DIR/'recovery-commands.json')
        results=inherited.cleanup_independently([('owned-simulator-and-baseline-reconciliation',lambda:inherited.cleanup(life,commands)),('ephemeral-capability-workspace-removal',lambda:inherited.remove_ephemeral(life))])
        life.update(cleanedUp=all(v['passed'] for v in results),recoveryCleanupResults=results)
        inherited.write(inherited.RUN_DIR/'lifecycle.json',life);require(life['cleanedUp'],'Recovery incomplete')

if __name__=='__main__':
    def stop(signum,frame):raise KeyboardInterrupt('Root pan commit harness interruption')
    signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop);main()
