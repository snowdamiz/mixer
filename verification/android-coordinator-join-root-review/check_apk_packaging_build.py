#!/usr/bin/env python3
"""Independent artifact/ZIP metadata review; no extraction or native execution."""
import datetime
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import platform
import struct
import tarfile
import zipfile
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
BASE=ROOT/'verification/android-coordinator-click-fixture/candidate-1'
NEW=ROOT/'verification/android-coordinator-apk-packaging/candidate-1'
def sha(data): return hashlib.sha256(data).hexdigest()
def read(p): return json.loads(p.read_text())
def zip_metadata(folder):
    with tarfile.open(folder/'built-artifacts.tar.gz') as tar:
        data=tar.extractfile('coordinator-join.apk').read()
    result={}
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for entry in archive.infolist():
            h=struct.unpack_from('<IHHHHHIIIHH',data,entry.header_offset)
            offset=entry.header_offset+30+h[-2]+h[-1]
            assert h[0]==0x04034B50 and h[3]==entry.compress_type
            assert h[6:9]==(entry.CRC,entry.compress_size,entry.file_size)
            assert offset+entry.compress_size<=len(data)
            result[entry.filename]={'method':entry.compress_type,'localDataOffset':offset,'bytesSHA256':sha(archive.read(entry))}
    return result

def main():
    spec=importlib.util.spec_from_file_location('mixer_root_click_archive_inspector',HERE/'check_click_fixture_build.py')
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    before, old, old_entries=helper.inspect(BASE)
    after, new, new_entries=helper.inspect(NEW)
    assert old.keys()==new.keys()
    delta=[name for name in old if old[name]!=new[name]]
    assert delta==['coordinator-join.apk']
    assert old_entries.keys()==new_entries.keys()
    entry_delta=[name for name in old_entries if old_entries[name]!=new_entries[name]]
    assert entry_delta==['META-INF/DEBUG.RSA']
    inputs=read(BASE/'source-lock.json')['files']
    assert inputs==read(NEW/'source-lock.json')['files'] and len(inputs)==105
    for folder in [BASE,NEW]:
        for name,expected in inputs.items(): assert sha((folder/'inputs'/name).read_bytes())==expected
    production={name:expected for name,expected in inputs.items()
        if not name.startswith(('verification/','docs/')) and Path(name).suffix in ['.swift','.java','.c','.h','.json']}
    assert len(production)==88
    for name,expected in production.items(): assert sha((ROOT/name).read_bytes())==expected,name
    old_zip=zip_metadata(BASE);new_zip=zip_metadata(NEW)
    methods=[name for name in old_zip if old_zip[name]['method']!=new_zip[name]['method']]
    assert methods==['resources.arsc']
    assert old_zip['resources.arsc']['method']==8 and new_zip['resources.arsc']['method']==0
    for name,item in new_zip.items():
        if item['method']==0: assert item['localDataOffset']%4==0,name
        if name.endswith('.so'): assert item['method']==0 and item['localDataOffset']%16384==0,name
    for c in after['commands']:
        assert c['exitCode']==(2 if c['name']=='zipalign-help' else 0),c['name']
        assert sha((NEW/c['output']).read_bytes())==c['sha256']
    assert after['sourceClosureSHA256']==before['sourceClosureSHA256']
    assert after['productionArtifactsRecompiled']==0 and after['correctedInstrumentationUnchanged']
    assert not after['privateKeyRetained'] and after['buildScratchCleanup']['status']=='removed'
    assert not (NEW/'.build').exists()
    paths=[BASE/'receipt.json',BASE/'built-artifacts.json',BASE/'source-lock.json',NEW/'receipt.json',NEW/'built-artifacts.json',NEW/'source-lock.json',HERE/'check_click_fixture_build.py',Path(__file__)]
    result={'schema':1,'observedUTC':datetime.datetime.now(datetime.UTC).isoformat(),'status':'accepted-APK-only-packaging-build-derivation','command':['python3','-B',str(Path(__file__).relative_to(ROOT))],'pythonVersion':platform.python_version(),'sourceRevision':after['sourceRevision'],'sourceClosureSHA256':after['sourceClosureSHA256'],'apkSHA256':after['apkSHA256'],'archiveSHA256':after['builtArchiveSHA256'],'actualArchivesInspected':2,'actualArtifactsInspected':354,'actualSourceInputsInspected':210,'unchangedArtifacts':176,'changedArtifacts':delta,'changedAPKEntryBytes':entry_delta,'unchangedAPKEntries':len(old_entries)-1,'changedCompressionMethods':methods,'originalZIPMetadata':old_zip,'correctedZIPMetadata':new_zip,'officialZipalign':'pre-sign and post-sign exit0; help exit2 is separately identified','scope':'Artifact and packaging acceptance only. Actual emulator installation and all eight app operations remain pending; no native/physical/public/GA acceptance.','bindings':{str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in paths}}
    result['productionInputsMatchingCurrentCheckout']=len(production)
    (HERE/'apk-packaging-build-acceptance.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['status','actualArtifactsInspected','unchangedArtifacts','changedAPKEntryBytes','changedCompressionMethods']}))
if __name__=='__main__': main()
