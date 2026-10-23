#!/usr/bin/env python3
"""Bind the repaired committed driver, exact source closure and rebuilt unsigned APK."""
import hashlib
import json
import pathlib
import re
import runpy
import shutil
import subprocess
import zipfile

OUT=pathlib.Path(__file__).resolve().parent
ROOT=OUT.parents[1]
EVIDENCE=OUT/'.local/final-evidence'
shutil.copytree(ROOT/'verification/android-staging-fix-2026-10-22',EVIDENCE)
source_receipt=json.loads((EVIDENCE/'receipt.json').read_text())
revision=json.loads((OUT/'freeze-repair.json').read_text())['revision']
assert source_receipt['sourceRevision']==revision
sha=lambda data:hashlib.sha256(data).hexdigest()
checks=[]
manifest=(EVIDENCE/'source-manifest.sha256').read_bytes()
assert sha(manifest)==source_receipt['sourceDigest']
for line in manifest.decode().splitlines():
    expected,path=line.split('  ',1)
    assert sha(subprocess.check_output(['git','show',revision+':'+path],cwd=ROOT))==expected,path
checks.append({'name':'repaired-commit-source-manifest','files':len(manifest.decode().splitlines()),'sha256':sha(manifest)})
for command in source_receipt['commands']:
    assert command['exitCode']==0
    assert sha((EVIDENCE/pathlib.Path(command['output']).name).read_bytes())==command['sha256']
for name,expected in source_receipt['buildReceipts'].items():assert sha((EVIDENCE/name).read_bytes())==expected
for name in source_receipt['buildReceipts']:
    record=json.loads((EVIDENCE/name).read_text())
    assert record['source_tree_sha256']==record['source_tree_after_sha256']
    assert all(command['exit_code']==0 for command in record['commands'])
checks.append({'name':'build-and-real-cache-rebuild-log-integrity','commands':len(source_receipt['commands']),'build_receipts':source_receipt['buildReceipts']})
build=json.loads((EVIDENCE/'rebuild-receipt.json').read_text())
app=pathlib.Path(source_receipt['application'])
module=runpy.run_path(str(OUT/'.local/source-repair/cli/Sources/MixerBuild/Resources/android-build.py'))
assert module['source_tree'](app)==build['source_tree_sha256']
assert module['source_tree'](app/'Generated/MixerSDK')==build['sdk_digest']
assert module['source_tree'](app/'Generated/MixerAndroid')==build['adapter_digest']
assert (app/'Generated/MixerAndroid/android-build.py').read_bytes()==(OUT/'.local/source-repair/cli/Sources/MixerBuild/Resources/android-build.py').read_bytes()
for path in (app/'Generated/MixerSDK').rglob('*'):
    if path.is_file() and '.build' not in path.parts:
        relative=path.relative_to(app/'Generated/MixerSDK').as_posix()
        assert path.read_bytes()==subprocess.check_output(['git','show',revision+':sdk/'+relative],cwd=ROOT),relative
checks.append({'name':'actual-rebuilt-app-sdk-adapter-locks','source_tree_sha256':build['source_tree_sha256'],'sdk_digest':build['sdk_digest'],'adapter_digest':build['adapter_digest'],'fixed_driver_sha256':sha((app/'Generated/MixerAndroid/android-build.py').read_bytes())})
apk=pathlib.Path(source_receipt['apk']['apk'])
assert sha(apk.read_bytes())==source_receipt['apk']['apk_sha256']==build['apk_sha256']
local=OUT/'.local/final-audited-unsigned.apk';shutil.copyfile(apk,local)
assert sha(local.read_bytes())==build['apk_sha256']
extracted=OUT/'.local/final-apk';extracted.mkdir()
with zipfile.ZipFile(local) as stream:
    names=stream.namelist();assert len(names)==len(set(names))
    content={name:sha(stream.read(name)) for name in sorted(names)}
    assert content==build['apk_entries']
    assert sha(json.dumps(content,sort_keys=True,separators=(',',':')).encode())==build['apk_content_sha256']
    assert not any(name.startswith('META-INF/') or 'Checklist' in name for name in names)
    libs=[name for name in names if name.startswith('lib/')]
    assert all(name.startswith('lib/arm64-v8a/') and name.endswith('.so') for name in libs)
    for name in ['classes.dex',*libs]:
        target=extracted/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(stream.read(name))
checks.append({'name':'actual-fixed-driver-rebuilt-apk','apk_sha256':build['apk_sha256'],'apk_bytes':local.stat().st_size,'apk_content_sha256':build['apk_content_sha256'],'entries':len(content),'libraries':len(libs),'unsigned':True})
commands=[]
tools={key:pathlib.Path(value['path']) for key,value in build['toolchain']['tools'].items()}
def run(name,args):
    expected=next(value for value in build['toolchain']['tools'].values() if value['path']==str(args[0]))
    assert sha(pathlib.Path(args[0]).read_bytes())==expected['sha256']
    p=subprocess.run(list(map(str,args)),stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    log=OUT/('final-artifact-'+name+'.log');log.write_bytes(p.stdout)
    commands.append({'command':list(map(str,args)),'exit_code':p.returncode,'output':log.name,'output_sha256':sha(p.stdout),'tool_sha256':expected['sha256']})
    assert p.returncode==0,name
    return p.stdout.decode()
run('alignment',[tools['zipalign'],'-c','-P','16','4',local])
badging=run('badging',[tools['aapt2'],'dump','badging',local])
assert "package: name='dev.mixer.stagingfixed'" in badging and "native-code: 'arm64-v8a'" in badging and 'dev.mixer.android.MixerActivity' in badging
needed={};system={'libc.so','libdl.so','libm.so','liblog.so','libandroid.so'}
for name in libs:
    path=extracted/name
    headers=run(path.name+'-elf',[tools['readelf'],'-h','-d','-l',path])
    assert 'ELF64' in headers and 'AArch64' in headers
    needed[path.name]=re.findall(r'\(NEEDED\).*\[([^\]]+)\]',headers)
    assert set(needed[path.name]).issubset(system|{pathlib.Path(p).name for p in libs})
assert needed==build['native_dependencies']
dex=run('dex',[tools['dexdump'],'-f',extracted/'classes.dex'])
for descriptor in ['Ldev/mixer/android/MixerActivity;','Ldev/mixer/android/NativeBridge;','Ldev/mixer/android/NativeRenderer;']:assert descriptor in dex
assert 'AdapterInstrumentation' not in dex
symbols=run('symbols',[tools['nm'],'-D','--defined-only',extracted/'lib/arm64-v8a/libAppAndroid.so'])
for name in ['mixer_android_create','mixer_android_exchange','mixer_android_destroy','AppModels','AppFeatures']:assert name in symbols
assert 'ChecklistEngine' not in symbols
checks.append({'name':'independent-pinned-official-tool-inspection','commands':len(commands),'native_dependencies':needed,'owned_classes':3,'app_shared_symbols':True})
result={'revision':revision,'source_evidence_receipt_sha256':sha((EVIDENCE/'receipt.json').read_bytes()),'qualification':'independently audited actual repaired-driver APK and real cache rebuild evidence; no duplicate full cross-build','checks':checks,'commands':commands,'scope':'Exact committed source, fixed source-locked driver, successful first and cached cross-build receipts, actual arm64 APK ZIP/ELF/DEX/symbol inspection. No device/signing/store qualification.'}
(OUT/'final-artifact-audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'revision':revision,'checks':checks[:4],'inspection_commands':len(commands)},indent=2))
