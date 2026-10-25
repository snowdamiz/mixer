#!/usr/bin/env python3
"""Preserve exact hostile inputs through the actual adapter with fake tool returns."""
import copy
import datetime
from decimal import Decimal, getcontext
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import bindings

BASE=bindings.BASE;ROOT=bindings.ROOT;stable=bindings.stable;sha=bindings.sha

def audit(event,args):
    if event in ('subprocess.Popen','os.system','os.exec','os.posix_spawn','socket.bind','socket.connect','socket.connect_ex'):
        raise AssertionError('No process/native/network action authorized in precision reproduction')

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module;spec.loader.exec_module(module);return module

def main():
    output=BASE/'precision-reproduction-1';output.mkdir()
    before=bindings.verify();sys.dont_write_bytecode=True;sys.addaudithook(audit)
    copies=BASE/'attempt-1/producer-copy';sys.path.insert(0,str(copies))
    prepare=load('prepare',copies/'prepare.py');prepare.ROOT=ROOT;prepare.BASE=copies
    prepare.OLD=ROOT/'verification/apple-focus-diagnostic-runtime-v1';prepare.V1=ROOT/'verification/apple-focus-reference-diagnostic-v1'
    prepare.V2=ROOT/'verification/apple-focus-reference-diagnostic-v2';prepare.REVIEW=ROOT/'verification/apple-focus-reference-diagnostic-v2-independent-review'
    tests=load('test_importer',copies/'test_importer.py');i=tests.i
    tests.RuntimeControls.setUpClass();ref=tests.RuntimeControls('test_001_one_complete_strict_original_pass_is_diagnostic_only')
    cases=[
        ('premise-nine-exact','before','1792893615.123456789',0,True),
        ('premise-nine-plus-one-ns','before','1792893615.123456789',1,False),
        ('witness-nine-exact','after','1792893620.987654321',0,True),
        ('witness-nine-plus-one-ns','after','1792893620.987654321',1,False),
        ('premise-ten-digits','before','1792893615.1234567891',0,False),
        ('premise-deep-tail','before','1792893615.123456789000000000000000001',0,False),
        ('premise-rounds-future','before','1792893615.999999999999999999999999999',1,False),
        ('witness-deep-tail','after','1792893620.123456789000000000000000001',0,False),
    ]
    results=[]
    try:
        for name,role,token,offset,expected in cases:
            retained=output/name;retained.mkdir();f=ref.fixture()
            decimal=Decimal(token);tuple_=decimal.as_tuple();coefficient=int(''.join(map(str,tuple_.digits)));power=tuple_.exponent+9
            floor_ns=coefficient*10**power if power>=0 else coefficient//10**(-power)
            signature_ns=floor_ns+offset;f['captures'][role]['signature'][1]=signature_ns
            if role=='before':f['captures']['after']['signature'][1]=signature_ns
            try:converted=i.decimal_timestamp_ns(decimal);conversion_error=None
            except ValueError as error:converted=None;conversion_error=str(error)
            with tempfile.TemporaryDirectory(prefix='precision-adapter-',dir=BASE) as tmp:
                sandbox=Path(tmp);namespace,invoke,calls,h=ref.adapter_namespace(f,sandbox)
                manifest=sandbox/'runtime/attachments/manifest.json';raw=manifest.read_bytes()
                old=b'1792893615.0' if role=='before' else b'1792893620.0';assert raw.count(old)==1
                raw=raw.replace(old,token.encode());manifest.write_bytes(raw)
                export=sandbox/'runtime/attachment-export.json';value=json.loads(export.read_bytes())
                value['files']['manifest.json']={'bytes':len(raw),'sha256':sha(raw)};export.write_bytes(stable(value))
                namespace['capture_official'](object(),invoke,h,sandbox)
                official=namespace['_OFFICIAL']
                result=i.import_selected(f['root'],f['session'],f['observer'],f['streams'],official['official'],official['payloads'],official['captures'],f['cleanup'],ref.oracle,ref.classifier)
                # Preserve the original captured raw bytes and complete app/observer inputs.
                shutil.copytree(sandbox/'runtime',retained/'runtime-inputs-and-capture')
                (retained/'root.json').write_bytes(stable(f['root']));(retained/'cleanup.json').write_bytes(stable(f['cleanup']))
                (retained/'observer.json').write_bytes(stable(f['observer']))
                (retained/'stdout.log').write_bytes(f['streams']['stdout']);(retained/'stderr.log').write_bytes(f['streams']['stderr'])
                (retained/'result.json').write_bytes(stable(result))
                accepted=result['diagnosticOutcome']=='one-strict-original-verdict-passed'
                # Exact integer comparison with original decimal coefficient, independent of Decimal context.
                after_true_endpoint=(signature_ns*10**(-power)>coefficient) if power<0 else signature_ns>coefficient*10**power
                record={'case':name,'role':role,'originalRawTimestampToken':token,'ambientDecimalPrecision':getcontext().prec,'exactCoefficient':str(coefficient),'decimalExponent':tuple_.exponent,'floorNS':floor_ns,'signatureNS':signature_ns,'signatureAfterTrueEndpoint':after_true_endpoint,'actualConverterNS':converted,'conversionError':conversion_error,'expectedAccepted':expected,'actualAccepted':accepted,'controlPassed':accepted==expected,'diagnosticOutcome':result['diagnosticOutcome'],'keyInjectionCount':result['keyInjectionCount'],'actualAdapterCaptured':True,'officialToolCalls':[row[0] for row in calls],'syntheticOnly':True,'nativeExecuted':False}
                (retained/'control.json').write_bytes(stable(record));results.append(record)
    finally:tests.RuntimeControls.tearDownClass()
    assert bindings.verify()==before
    rows={str(p.relative_to(output)):bindings.row(p) for p in sorted(output.rglob('*')) if p.is_file()}
    receipt={'schema':'mixer.apple-focus-reference-runtime-v3-independent-precision-reproduction.1','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,'-B',str(Path(__file__).resolve())],'python':sys.version,'pythonExecutable':str(Path(sys.executable).resolve()),'hostUname':dict(zip(('sysname','nodename','release','version','machine'),os.uname())),'sourceSHA256':sha(Path(__file__).read_bytes()),'handoffSHA256':bindings.EXPECTED_HANDOFF,'packetSHA256':bindings.EXPECTED_PACKET,'controls':len(results),'controlsPassed':sum(row['controlPassed'] for row in results),'controlsFailed':sum(not row['controlPassed'] for row in results),'results':results,'outputs':rows,'outputTreeSHA256':sha(stable(rows)),'nativeExecuted':False,'cleanup':{'allFrozenInputsUnchanged':True,'ownedAdapterScratchAbsent':not list(BASE.glob('precision-adapter-*')),'nativeCommandsInvoked':0,'nativeInstancesCreatedOrQueried':0,'servicesStarted':0,'otherProjectsTouched':False}}
    (output/'receipt.json').write_bytes(stable(receipt))
    print(json.dumps({'controls':receipt['controls'],'passed':receipt['controlsPassed'],'failed':receipt['controlsFailed'],'receiptSHA256':sha((output/'receipt.json').read_bytes()),'futureEndpointAccepted':[r['case'] for r in results if r['signatureAfterTrueEndpoint'] and r['actualAccepted']]},sort_keys=True))

if __name__=='__main__':main()
