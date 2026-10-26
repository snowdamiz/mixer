#!/usr/bin/env python3
"""Exact frozen-input closure verification, separate from executable controls."""
from pathlib import Path
import datetime, difflib, hashlib, json, sys
D=Path(__file__).resolve().parent
P=D.parent
ROOT=P.parents[1]
def row(path):
    data=path.read_bytes();return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def verify(directory,seal_name,expected):
    path=directory/seal_name;assert row(path)['sha256']==expected
    seal=json.loads(path.read_text());total=0
    for member in seal['members']:
        relative=Path(member['path']);assert not relative.is_absolute() and '..' not in relative.parts
        target=directory/relative;assert not target.is_symlink() and target.resolve().is_relative_to(directory.resolve())
        assert row(target)=={k:member[k] for k in ['bytes','sha256']},str(target)
        total+=member['bytes']
    return {'seal':str(path.relative_to(ROOT)),**row(path),'members':len(seal['members']),'member_bytes':total}
seals=[verify(P,'preaccess-seal.json','dec2610cb92d635322866d650ed52ab82263db198e203eb49c88b5bfd9592161'),verify(P.parent/'android-editor-implementation-independent','audit-seal.json','c4db2ee776cac85b4a9589d10826fdfda519f7d16e627e4b8df86f837c8047ee'),verify(P.parent/'android-editor-replacement-implementation','seal.json','4c906824fe5e2e925c3ad5ca7c4ae94ba3b1e7dd6c58e77805dd3862c165c9a3')]
old=P.parent/'android-editor-implementation-independent/actual-review/frozen/source'
new=D/'frozen/source';changed=[];unchanged=[];sources={}
for path in sorted(new.glob('*.java')):
    sources[path.name]=row(path)
    original=old/path.name
    if path.read_bytes()==original.read_bytes():unchanged.append(path.name)
    else:
        changed.append(path.name)
        diff=''.join(difflib.unified_diff(original.read_text().splitlines(keepends=True),path.read_text().splitlines(keepends=True),fromfile='original/'+path.name,tofile='correction/'+path.name))
        (D/(path.name+'.diff')).write_text(diff)
assert changed==['NativeAppearanceViewsV2.java','NativeRenderer.java']
def body(text,marker):
    start=text.index(marker);brace=text.index('{',start);count=0
    for end in range(brace,len(text)):
        if text[end]=='{':count+=1
        elif text[end]=='}':
            count-=1
            if count==0:return text[start:end+1].encode()
    raise AssertionError(marker)
bodies={}
for marker in ['void finishV2(Candidate c,AttachmentJournal journal)','private void requireV2Live()']:
    a=body((old/'NativeRenderer.java').read_text(),marker);b=body((new/'NativeRenderer.java').read_text(),marker);assert a==b
    bodies[marker]=hashlib.sha256(b).hexdigest()
guards={}
for path in sorted(new.glob('*.java')):
    before=[line.strip() for line in (old/path.name).read_text().splitlines() if 'SDK_INT' in line and '<36' in line.replace(' ','') and ('unsupported()' in line or 'AppearanceDescriptorV2.Failure' in line)]
    after=[line.strip() for line in path.read_text().splitlines() if 'SDK_INT' in line and '<36' in line.replace(' ','') and ('unsupported()' in line or 'AppearanceDescriptorV2.Failure' in line)]
    assert before==after,path.name
    if after:guards[path.name]=after
assert sum(len(lines) for lines in guards.values())==2
contracts={}
for name,expected in [('replacement-amendment.md','b386f832479884f2487df114fb080f14ebac99c747208bffd0428477c32d844b'),('replacement-dispatch-amendment.md','eb35fe8f9c9d9ee093ad0f40d687fbd2b4fb4382dc32cd7a74acbcc98c5da6ff')]:
    source=ROOT/'verification/android-editor-boundary-root-review'/name;assert row(source)['sha256']==expected;contracts[name]=row(source)
for run in ['host-1','cross-1']:
    run_source=D/'frozen/runs'/run/'inputs/source'
    assert {p.name:row(p) for p in run_source.glob('*.java')}==sources,run
result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':sys.argv,'python':sys.version,'script':row(Path(__file__)),'verified_seals':seals,'contracts':contracts,'product_source':sources,'changed_from_independently_reviewed_baseline':changed,'unchanged_from_independently_reviewed_baseline':unchanged,'critical_unchanged_bodies':bodies,'SDK36_guards':guards,'host_and_cross_exact_product_source':True,'coordinator_only_preexisting_two_guards_and_otherwise_identical_to_prior_candidate':True,'scope':'Exact file/body/hash verification only; executable actual-source controls recorded separately; no release authorization'}
(D/'source-verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'seals':seals,'changed':changed,'unchanged_count':len(unchanged),'host_and_cross_source_identical':True}))
