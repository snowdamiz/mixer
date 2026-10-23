#!/usr/bin/env python3
"""Freeze and qualify explicit Swift v3 proof verification; no device or execution authority."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OLD='1ab4d4ee76a5d4ba206bd370cbeeeb73a7c6c636'
LEGACY='3886a064552bdd0573362909f4f6fe0973ddf5a6982cb4369c5a92b328a52d60'
VECTORS={'signed-release-v3.json':'ee4935fedca51b728e78801cb05c5732e8547bda1e26f109330e6659a0a2f77a',
         'release-v3-cases.json':'8f62ae6bc91e951c3c66ab16689dd20f9465c7b671b2f24ad44b5960923c2b44'}

def sha(data):return hashlib.sha256(data).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def require(value,message):
    if not value:raise RuntimeError(message)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label',required=True)
    args=parser.parse_args();require(re.fullmatch(r'[a-z0-9-]+',args.label),'simple label required')
    out=HERE/args.label;out.mkdir(exist_ok=False)
    work=ROOT/'updates/.build'/('qualification-release-v3-'+args.label);work.mkdir(exist_ok=False)
    source=work/'source';source.mkdir()
    excluded={'.build','.swiftpm','__pycache__'}
    inputs=[p for p in (ROOT/'updates').rglob('*') if p.is_file() and not excluded.intersection(p.relative_to(ROOT).parts)]
    inputs += [ROOT/'docs/release-v3-swift-api-design.md',ROOT/'verification/capability-authority-contract-freeze-2026-10-23.json',Path(__file__).resolve()]
    inputs += [p for p in (ROOT/'contracts').glob('*.json')]
    inputs += [ROOT/'services/protocol/testdata'/n for n in VECTORS]
    for directory in ['PublicClient','CompileNegative']:
        inputs += [p for p in (HERE/directory).rglob('*') if p.is_file() and not excluded.intersection(p.relative_to(HERE).parts)]
    records={}
    for p in sorted(set(inputs)):
        require(not p.is_symlink(),'regular input '+str(p))
        relative=str(p.relative_to(ROOT));data=p.read_bytes();records[relative]=sha(data)
        target=source/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    manifest=''.join(d+'  '+p+'\n' for p,d in sorted(records.items())).encode()
    (out/'source-manifest.sha256').write_bytes(manifest)
    require(records['updates/Sources/MixerUpdates/Verifier.swift']==LEGACY,'legacy verifier exact bytes')
    oldpaths=subprocess.check_output(['git','ls-tree','-r','--name-only',OLD,'--','updates/Sources','updates/Tests'],cwd=ROOT,text=True).splitlines()
    preserved={}
    for relative in oldpaths:
        baseline=subprocess.check_output(['git','show',OLD+':'+relative],cwd=ROOT)
        require((ROOT/relative).read_bytes()==baseline,'old update source/test changed '+relative)
        preserved[relative]=sha(baseline)
    for name,digest in VECTORS.items():
        for base in [ROOT/'services/protocol/testdata',ROOT/'updates/Tests/MixerUpdatesTests/Fixtures']:
            require(sha((base/name).read_bytes())==digest,'frozen shared vector '+name)
    receipt={'status':'running','started_at':now(),'head_at_start':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
             'source_files':records,'source_manifest_sha256':sha(manifest),'immutable_source_export':str(source),
             'legacy_baseline':OLD,'legacy_verifier_sha256':LEGACY,'preserved_old_source_test_files':preserved,
             'shared_fixture_sha256':VECTORS,'commands':[],'driver_sha256':sha(Path(__file__).read_bytes()),
             'scope':'Pure signatures/metadata/payload proofs, host only; no v3 updater/factory/coordinator/VM/effects/hosted route/device authority',
             'limitations':['Swift/C shim TSan only; system CryptoKit/framework code not instrumented',
                            'Caller schedules synchronous verification; no process-wide memory or task bound claimed',
                            'No mobile execution, Wasm validation, installed material, OTA/health/recovery, publication or GA qualification']}
    def save():(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    def unchanged():
        for relative,digest in records.items():
            require(sha((ROOT/relative).read_bytes())==digest,'input changed '+relative)
            require(sha((source/relative).read_bytes())==digest,'export changed '+relative)
    env=dict(os.environ,DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer')
    def run(name,argv,scope,expected=0,count=None,diagnostic=None,timeout=240):
        unchanged();start=time.monotonic()
        try:
            r=subprocess.run(argv,cwd=source,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout);data,code=r.stdout,r.returncode
        except subprocess.TimeoutExpired as e:data,code=(e.stdout or b'')+b'\nQualification timeout\n',124
        log=out/(name+'.log');log.write_bytes(data)
        row={'name':name,'argv':argv,'cwd':str(source),'environment':{'DEVELOPER_DIR':env['DEVELOPER_DIR']},'exit_code':code,
             'expected_exit':expected,'elapsed_seconds':time.monotonic()-start,'log':str(log.relative_to(ROOT)),'sha256':sha(data),'scope':scope}
        if count is not None:
            observed=[int(v) for v in re.findall(rb'Test run with (\d+) tests? in \d+ suites? passed',data)]
            row.update(expected_tests=count,observed_tests=observed)
        if diagnostic:row['required_diagnostic_fragment']=diagnostic
        receipt['commands'].append(row);save();unchanged()
        require(code==expected,name+': unexpected exit '+str(code))
        if count is not None:require(observed==[count],name+': unexpected test count')
        if diagnostic:require(diagnostic.encode() in data,name+': wrong negative-compile reason')
        print(name+': '+str(code),flush=True)
    save()
    try:
        for name,argv in [('swift-version',['swift','--version']),('xcode-version',['xcodebuild','-version']),('host-version',['uname','-a']),('python-version',['python3','--version'])]:run(name,argv,'Observed qualification tools')
        build=work/'build'
        base=['swift','test','--package-path',str(source/'updates'),'--scratch-path',str(build),'-Xswiftc','-warnings-as-errors']
        for mode in ['debug','release']:run('all-'+mode,base+['--configuration',mode],'All original old and new updates tests; no VM activation',count=55)
        products=build/'out/Products/Debug'
        require((products/'libMixerUpdates.a').is_file(),'expected static library product')
        module=build/'out/Intermediates.noindex/GeneratedModuleMaps/MixerDurableIO.modulemap'
        common=['swiftc','-swift-version','6','-warnings-as-errors','-I',str(products),'-Xcc','-fmodule-map-file='+str(module)]
        client=work/'v3-public-client'
        run('public-client-link',common+['-L',str(products),'-lMixerUpdates',str(source/'verification/release-v3-swift/PublicClient/Sources/proof-client/main.swift'),'-o',str(client)],'External non-testable public API consumer compile and static link')
        receipt['public_client']={'path':str(client),'sha256':sha(client.read_bytes()),'bytes':client.stat().st_size};save()
        run('public-client-run',[str(client),str(source/'services/protocol/testdata/signed-release-v3.json')],'Public signed-fixture proof consumption; string payload, no Wasm')
        run('public-client-file',['file',str(client)],'Identify actual host consumer binary')
        negatives=source/'verification/release-v3-swift/CompileNegative'
        run('public-typecheck-positive',common+['-typecheck',str(negatives/'positive-control.swift')],'Positive external import/typecheck control')
        fragments={'artifact-constructor':'inaccessible','grants-constructor':'inaccessible','assignment-constructor':'inaccessible','entry-constructor':'inaccessible',
                   'artifact-decoder':"conform to 'Decodable'",'grants-decoder':"conform to 'Decodable'",'legacy-artifact-substitution':"to expected argument type 'VerifiedArtifactV3'",'private-evidence':'inaccessible'}
        for name,fragment in fragments.items():run('reject-'+name,common+['-typecheck',str(negatives/(name+'.swift'))],'Intentional negative compile: public proof/authority remains opaque',expected=1,diagnostic=fragment)
        run('v3-tsan',base+['--configuration','debug','--sanitize','thread','--filter','v3'],'V3 tests including32 concurrent value copies under Swift/C-shim TSan; no system-framework instrumentation',count=15)
        unchanged();receipt.update(status='scoped checks passed; independent review/integration pending',completed_at=now(),source_and_export_unchanged=True)
    except Exception as e:
        receipt.update(status='failed check preserved',completed_at=now(),problem=str(e));save();raise
    save();print(json.dumps({'status':receipt['status'],'source_manifest_sha256':sha(manifest),'receipt_sha256':sha((out/'receipt.json').read_bytes())}))

if __name__=='__main__':main()
