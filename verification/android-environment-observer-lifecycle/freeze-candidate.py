from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[2]
PACKET=Path(__file__).resolve().parent

def identity(data): return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def profile(path): return json.loads(path.read_text().split('Data(#"""\n',1)[1].split('\n        """#.utf8)',1)[0])
def save(path,value): path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
old=profile(ROOT/'verification/android-owner-effect-contract/inputs/cli/Sources/MixerBuild/AndroidSDKCompatibility.swift')
current=profile(ROOT/'cli/Sources/MixerBuild/AndroidSDKCompatibility.swift')
assert old['id']=='mixer.android-source-pair.1' and current['id']=='mixer.android-source-pair.2'
assert old['sdk_files']==current['sdk_files'] and len(current['sdk_files'])==22 and len(current['adapter_files'])==20
changed=[p for p in old['adapter_files'] if old['adapter_files'][p]!=current['adapter_files'][p]]
assert changed==['app/src/dev/mixer/android/NativeEnvironmentV2.java']
for key in ['schema','sdk_compatibility_sha256','default_descriptor','wire']: assert old[key]==current[key]
paths=[]
for kind in ['sdk','adapter']:
    records=''
    for relative,expected in sorted(current[kind+'_files'].items()):
        source='sdk/'+relative if kind=='sdk' else 'native/android/'+('engine/' if relative.startswith('Sources/') else '')+relative
        assert identity((ROOT/source).read_bytes())==expected,source
        records+=relative+'\0'+expected['sha256']+'\n';paths.append(source)
    assert hashlib.sha256(records.encode()).hexdigest()==current[kind+'_compatibility_sha256']
paths+=['cli/Sources/MixerBuild/AndroidSDKCompatibility.swift','cli/Sources/MixerBuild/Resources/android-build.py',
        'cli/Tests/MixerBuildTests/AndroidSDKCompatibilityTests.swift','cli/build-tests/test_android_sdk_compatibility.py']
inputs=PACKET/'candidate-inputs';inputs.mkdir(exist_ok=False)
files={}
for relative in sorted(paths):
    data=(ROOT/relative).read_bytes();target=inputs/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);files[relative]=identity(data)
save(PACKET/'candidate-profile-2.json',current)
proposal={'schema':1,'context_revision':'4e48ac1a3c1593d46c0dcbaf207053ff5e1b6d5d',
    'selection':identity((ROOT/'verification/android-environment-observer-root-review/implementation-selection.json').read_bytes()),
    'status':'frozen-candidate-awaiting-root-profile-qualification-admission',
    'profile':identity((PACKET/'candidate-profile-2.json').read_bytes()),
    'profile_id':current['id'],'changed_mapped_sources':changed,'sdk_members':22,'adapter_members':20,
    'sdk_compatibility_sha256':current['sdk_compatibility_sha256'],'adapter_compatibility_sha256':current['adapter_compatibility_sha256'],
    'observer':current['adapter_files'][changed[0]],'files':files,
    'host_source_freeze':identity((PACKET/'host-source-freeze.json').read_bytes()),
    'host_receipt':identity((PACKET/'host-attempt-3/receipt.json').read_bytes()),
    'host_result':'161 production Observer host cases passed; leaves only',
    'profile_qualification_executed':False,'native_runtime_or_capture_authorized':False,'GA_qualified':False}
save(PACKET/'candidate-proposal.json',proposal)
print(json.dumps({'proposal':str(PACKET/'candidate-proposal.json'),**identity((PACKET/'candidate-proposal.json').read_bytes()),'profile':proposal['profile'],'observer':proposal['observer'],'adapter_digest':proposal['adapter_compatibility_sha256']},sort_keys=True))
