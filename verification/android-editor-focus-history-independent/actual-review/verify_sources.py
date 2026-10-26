#!/usr/bin/env python3
from pathlib import Path
import datetime,difflib,hashlib,json,sys
D=Path(__file__).resolve().parent
P=D.parent
ROOT=P.parents[1]
def row(path):
    data=path.read_bytes();return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def exact(directory,name,expected):
    seal=directory/name;assert row(seal)['sha256']==expected
    data=json.loads(seal.read_text())
    for member in data['members']:
        path=directory/member['path'];assert not path.is_symlink() and path.resolve().is_relative_to(directory.resolve());assert row(path)=={key:member[key] for key in ['bytes','sha256']},str(path)
    return {'seal':str(seal.relative_to(ROOT)),**row(seal),'members':len(data['members']),'member_bytes':sum(member['bytes'] for member in data['members'])},data
protected=[]
for directory,name,expected in [(P,'preaccess-seal.json','169a0f581e0871e1ac273b88f653dc4d87381628fb8a39b8b2ec4bf7c80dbc62'),(ROOT/'verification/android-editor-focus-history-correction','seal.json','2ebf7634886be778b06ecdfa0ab2a9ac69d14a473b88a7f6ea623ccddfcd5af8'),(ROOT/'verification/android-editor-replacement-independent','review-seal.json','11cd26bbc78f54e48de297b931fab2fcb9becce4d4aa4884d145641f2a615b15'),(D/'findings-1','seal.json','a0cf5e8bff8ffee66f277b5e83c76b2778db13bd8eac558ae3ef65cdc007f5fd')]:
    record,data=exact(directory,name,expected);protected.append(record)
    if directory.name=='android-editor-focus-history-correction':producer=data
old=ROOT/'verification/android-editor-replacement-independent/actual-review/frozen'
new=D/'frozen';sources={path.name:row(path) for path in sorted((new/'source').glob('*.java'))};changed=[];unchanged=[]
for name,current in sources.items():
    if current==row(old/'source'/name):unchanged.append(name)
    else:
        changed.append(name);(D/(name+'.diff')).write_text(''.join(difflib.unified_diff((old/'source'/name).read_text().splitlines(keepends=True),(new/'source'/name).read_text().splitlines(keepends=True),fromfile='previous/'+name,tofile='focus-history/'+name)))
assert changed==['NativeAppearanceViewsV2.java','NativeRenderer.java']
members={member['path']:member for member in producer['members']}
for run in ['host-8','cross-3']:
    for name,current in sources.items():
        member=members['runs/'+run+'/inputs/source/'+name];assert current=={key:member[key] for key in ['bytes','sha256']},(run,name)
for run in ['host-1','cross-1']:
    assert {path.name:row(path) for path in (new/'runs'/run/'inputs/source').glob('*.java')}==sources,run
assert {str(path.relative_to(new/'host-leaves')):row(path) for path in (new/'host-leaves').rglob('*.java')}=={str(path.relative_to(old/'host-leaves')):row(path) for path in (old/'host-leaves').rglob('*.java')}
assert row(new/'tests/EditorImplementationTests.java')==row(old/'tests/EditorImplementationTests.java')
def body(text,marker):
    start=text.index(marker);brace=text.index('{',start);depth=0
    for end in range(brace,len(text)):
        if text[end]=='{':depth+=1
        elif text[end]=='}':
            depth-=1
            if depth==0:return text[start:end+1].encode()
    raise AssertionError(marker)
critical={}
for marker in ['void finishV2(Candidate c,AttachmentJournal journal)','private void requireV2Live()']:
    before=body((old/'source/NativeRenderer.java').read_text(),marker);after=body((new/'source/NativeRenderer.java').read_text(),marker);assert before==after;critical[marker]=hashlib.sha256(after).hexdigest()
guards={}
for name in sources:
    before=[line.strip() for line in (old/'source'/name).read_text().splitlines() if 'SDK_INT' in line and '<36' in line.replace(' ','') and ('unsupported()' in line or 'AppearanceDescriptorV2.Failure' in line)]
    after=[line.strip() for line in (new/'source'/name).read_text().splitlines() if 'SDK_INT' in line and '<36' in line.replace(' ','') and ('unsupported()' in line or 'AppearanceDescriptorV2.Failure' in line)]
    assert before==after
    if after:guards[name]=after
assert sum(len(lines) for lines in guards.values())==2
tools={}
for name in ['/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home/bin/java','/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home/bin/javac','/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home/bin/javap','/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home/release','/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home/lib/modules','/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home/lib/ct.sym','/opt/homebrew/share/android-commandlinetools/platforms/android-37.0/android.jar','/opt/homebrew/share/android-commandlinetools/build-tools/37.0.0/d8','/opt/homebrew/share/android-commandlinetools/build-tools/37.0.0/lib/d8.jar']:
    tools[name]=row(Path(name))
result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':sys.argv,'python':sys.version,'protected':protected,'source':sources,'changed':changed,'unchanged':unchanged,'host_leaves_and_original52_tests_byte_identical':True,'producer_final_host8_cross3_and_own_host1_cross1_use_exact_source':True,'critical_unchanged_bodies':critical,'both_SDK36_guards':guards,'tools':tools,'scope':'Exact custody/hash/body checks supplement complete actual-source review; no release/native authorization'}
(D/'source-verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'protected':protected,'changed':changed,'unchanged':len(unchanged),'host_and_cross_source_exact':True}))
