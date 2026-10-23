#!/usr/bin/env python3
"""Real link controls and omitted fixed-symbol failures; no source replacement."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,os,subprocess,time,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
p=argparse.ArgumentParser();p.add_argument('--reference',required=True);p.add_argument('--name',required=True);a=p.parse_args()
refpath=ROOT/a.reference;ref=json.loads(refpath.read_text());source=Path(ref['commands'][0]['cwd']);mode=ref['mode'];products=source.parent
out=HERE/'.build'/('symbols-'+a.name);out.mkdir(parents=True,exist_ok=False)
logs=HERE/'runs'/('symbols-'+a.name);logs.mkdir(parents=True,exist_ok=False)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
receipt={'reference':a.reference,'reference_sha256':sha(refpath),'mode':mode,'commands':[],'artifacts':{},'inputs':{'script':sha(Path(__file__)),'edge':sha(HERE/'SymbolEntry.swift')},'scope':'Actual full product Swift object compiled separately from verification edge. Original C transport and fixed host object. LLVM symbol-table rename removes one real definition at a time; real linker must reject every missing required hook/native helper. No replacement implementation or success stub.'}
base=json.loads((ROOT/ref['dependency_receipt']).read_text());original=next(c['argv'] for c in base['commands'] if c['name']=='link-current-runtime');prefix=original[:original.index('-emit-library')]
flags=['-O'] if mode=='release' else ['-sanitize=thread'] if mode=='tsan' else ['-Onone']
cmaps=['-I',source/'native/android/signed-guest-ui/binding/include','-I',source/'verification/android-binding-stage4/host-bridge']
objcopy=Path('/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/llvm-objcopy')
env=dict(os.environ,DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer')
def save():(logs/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
def run(name,argv,expected=0):
    start=time.monotonic();r=subprocess.run([str(x) for x in argv],cwd=out,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
    log=logs/(name+'.log');log.write_bytes(r.stdout);receipt['commands'].append({'name':name,'argv':[str(x) for x in argv],'exit':r.returncode,'expected_exit':expected,'seconds':time.monotonic()-start,'log':str(log.relative_to(ROOT)),'sha256':sha(log)})
    save();print(name,r.returncode,flush=True)
    if r.returncode!=expected:print(r.stdout.decode(errors='replace'));raise RuntimeError(name)
    return r.stdout.decode(errors='replace')
try:
    run('objcopy-version',[objcopy,'--version']);receipt['objcopy_sha256']=sha(objcopy)
    sources=sorted((source/'capability-activation/Sources/MixerCapabilityActivation').glob('*.swift'))
    swift=out/'Activation-product.o'
    run('product-swift-object',prefix+flags+cmaps+['-whole-module-optimization','-emit-object','-module-name','MixerCapabilityActivation']+sources+['-o',swift])
    output=run('product-swift-symbols',['xcrun','nm','-g',swift]);assert '_mxish_' not in output and '_mxuit_drain' in output and '_mxuit_complete' in output and '_mxuit_progress' in output
    transport=out/'transport-product.o'
    run('product-transport-object',['xcrun','clang','-std=c11','-Wall','-Wextra','-Werror','-c',source/'native/android/signed-guest-ui/transport/transport.c','-o',transport])
    output=run('product-transport-symbols',['xcrun','nm','-g',transport]);assert '_mxuit_test_' not in output
    edge=out/'Verification-edge.o'
    run('verification-edge-object',prefix[:2]+['-I',products]+prefix[2:]+flags+cmaps+['-emit-object','-module-name','Stage4SymbolEdge',HERE/'SymbolEntry.swift','-o',edge])
    dependencies=[x for x in original if x.endswith(('.o','.a'))]
    ctransport=products/'transport.o';host=products/'host_bridge.o'
    def link(name,s=swift,h=host):
        return prefix+flags+['-emit-library',s,edge,ctransport,h]+dependencies+['-o',out/(name+'.dylib')]
    run('actual-link-control',link('control'))
    for name in ['mxuit_drain','mxuit_complete','mxuit_progress','mxis_apply','mxis_interaction','mxis_retire']:
        modified=out/('without-'+name+'.o');original_object=swift if name.startswith('mxuit_') else host
        run(name+'-remove-definition',[objcopy,'--redefine-sym','_'+name+'=_removed_'+name,original_object,modified])
        output=run(name+'-missing-link',link(name,s=modified if name.startswith('mxuit_') else swift,h=modified if name.startswith('mxis_') else host),expected=1)
        assert 'Undefined symbols' in output and '_'+name in output,name
    receipt['artifacts']={str(path.relative_to(ROOT)):sha(path) for path in [swift,transport,edge,out/'control.dylib']};receipt['result']='actual link control and all six required-symbol omission failures passed; product objects contain no test controls'
except BaseException as error:receipt['result']='failed symbol verification retained';receipt['error']=str(error);raise
finally:receipt['completed_utc']=datetime.now(timezone.utc).isoformat();save()
