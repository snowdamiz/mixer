#!/usr/bin/env python3
"""Offline source/native-assertion/compositor verification; no device discovery."""
import pathlib,json,hashlib,argparse,sys,tarfile
from PIL import Image
BASE=pathlib.Path(__file__).resolve().parent
REPO=BASE.parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--candidate',required=True);parser.add_argument('--check-live',action='store_true');args=parser.parse_args()
OUT=BASE/args.candidate
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
lock=json.loads((OUT/'source-lock.json').read_text())
supportingDrift=[]
for name,digest in lock['sha256'].items():
    assert sha(OUT/'inputs'/name)==digest,('captured input changed',name)
    if args.check_live and sha(REPO/name)!=digest:
        if name!='AGENTS.md': raise AssertionError(('live input changed',name))
        supportingDrift.append({'path':name,'capturedSHA256':digest,'currentSHA256':sha(REPO/name),'scope':'Supporting execution policy updated by root after source-bound native capture; captured bytes retained; no product/harness change accepted'})
manifest=json.loads((BASE/'intermediate-archive-manifest.json').read_text())
assert sha(BASE/'intermediate-attempts.tar.gz')==manifest['archiveSHA256']
with tarfile.open(BASE/'intermediate-attempts.tar.gz','r:gz') as archive:
    for entry in manifest['files']:
        data=archive.extractfile(entry['path']).read()
        assert len(data)==entry['bytes'] and hashlib.sha256(data).hexdigest()==entry['sha256']
later=json.loads((BASE/'later-intermediate-archive-manifest.json').read_text())
assert sha(BASE/later['archive'])==later['archiveSHA256']
with tarfile.open(BASE/later['archive'],'r:gz') as archive:
    for entry in later['files']:
        data=archive.extractfile(entry['path']).read()
        assert len(data)==entry['bytes'] and hashlib.sha256(data).hexdigest()==entry['sha256']
built=json.loads((OUT/'built-app.json').read_text())
appManifest=json.loads((OUT/'built-app-manifest.json').read_text())
assert sha(OUT/appManifest['archive'])==appManifest['sha256']
with tarfile.open(OUT/appManifest['archive'],'r:gz') as archive:
    for name,entry in appManifest['files'].items():
        data=archive.extractfile('MixerAppearanceV2.app/'+name).read()
        assert len(data)==entry['bytes'] and hashlib.sha256(data).hexdigest()==entry['sha256'],name
assert appManifest['files']['MixerAppearanceV2Harness']['sha256']==built['binarySHA256']
for name,digest in built['libraries'].items(): assert appManifest['files']['Frameworks/'+name]['sha256']==digest
installed=json.loads((OUT/'installed-app-receipt.json').read_text())
assert installed['matchesRetainedBuiltApp'] and all(c['exitCode']==0 for c in installed['commands'])
assert installed['hashes']['MixerAppearanceV2Harness']==built['binarySHA256']
for name,digest in built['libraries'].items():assert installed['hashes']['Frameworks/'+name]==digest
observations=json.loads((OUT/'observations.json').read_text())
assert observations['checks'] and all(x['pass'] for x in observations['checks'])
for command in json.loads((OUT/'commands.json').read_text()):
    if 'argv' in command: assert command['exitCode']==0,command
assert (OUT/'fixture-native-packet.bin').read_bytes()==(BASE/'shared-fixture/native-packet-v1.bin').read_bytes()
frames=json.loads((OUT/'fixture-frames-roles-states.json').read_text())
assert len({x['kind'] for x in frames['nodes']})==10
stages={x['stage']:x['after'] for x in observations['observations']}
# Samples are actual decoded compositor pixels, never drawn reference images.
scale=frames['density1024']/1024
nodes={x['id']:x for x in frames['nodes']}
def pixel(stage,x,y):
    image=Image.open(OUT/(stage+'.png')).convert('RGB')
    return list(image.getpixel((int(round(x*scale)),int(round(y*scale)))))
def toggle(stage,checked):
    node=nodes['toggle']; frame=node['windowFrame64'];visual=node['visual64']
    x=(frame[0]+visual[0])/64+(10 if checked else 53);y=(frame[1]+visual[1])/64+14
    return pixel(stage,x,y)
samples={'toggleEnabledOn':toggle('initial',True),'toggleNativeInputOff':toggle('toggle-input',False),'toggleDisabledOff':toggle('disabled',False)}
assert samples['toggleEnabledOn']==[52,199,89],samples
assert samples['toggleNativeInputOff']==[197,197,199],samples
assert samples['toggleDisabledOff']==[229,229,231],samples
blink=[]
for stage in ['blink-a','blink-b','blink-c','blink-d']:
    r=stages[stage]['nodes']['field']['cursorRectInWindow']
    sample=pixel(stage,r[0]+r[2]/2,r[1]+r[3]/2)
    blink.append({'stage':stage,'rgb':sample,'nativePresentationOpacity':stages[stage]['nodes']['field']['cursorPresentationOpacity']})
assert any(x['rgb']==[0,136,255] for x in blink),blink
assert any(x['rgb']==[255,255,255] for x in blink),blink
samples['managedCursorBlink']=blink
# Native held observer, checked state and exact authored track/thumb samples.
held=[]
for stage in ['held-toggle-1','held-toggle-2']:
    state=json.loads((OUT/(stage+'-observations.json')).read_text())['observations'][-1]['after']['nodes']['toggle']
    assert state['authoredPressed'] and state['checked'] and state['pressObservationCount']>0
    assert state['nativeCarrierAlpha']==1 and state['nativeLayerOpacity']==1 and state['coverNoninteractive']
    node=nodes['toggle'];frame=node['windowFrame64'];visual=node['visual64']
    x=(frame[0]+visual[0])/64;y=(frame[1]+visual[1])/64+14
    track=pixel(stage,x+10,y);thumb=pixel(stage,x+42.5,y)
    assert track==[46,191,109],track
    assert thumb==[255,255,255],thumb
    held.append(dict(stage=stage,trackRGB=track,thumbRGB=thumb,native=state))
samples['heldSwitch']=held
cancel=json.loads((OUT/'post-cancel-observations.json').read_text())
assert all(c['pass'] for c in cancel['checks'])
cancelState=cancel['observations'][-1]['after']['nodes']['toggle']
assert not cancelState['authoredPressed'] and cancelState['cancellationCount']==1 and cancelState['checked']
assert cancel['actions']==observations['actions']
# Focus outline is inside semantic visual bounds, with no half-stroke bleed.
field=nodes['field'];x=(field['windowFrame64'][0]+field['visual64'][0]+field['visual64'][2]/2)/64
y=(field['windowFrame64'][1]+field['visual64'][1])/64
outline={'outsideRGB':pixel('focus',x,y-1/3),'insideRGB':pixel('focus',x,y+1/3)}
assert outline=={'outsideRGB':[255,255,255],'insideRGB':[0,136,255]},outline
samples['focusedFieldInsideOutline']=outline

cua=json.loads((OUT/'cua-interactions.json').read_text())
assert [(x['id'],x['event']) for x in cua['nativeActionDelta']]==[('button','activate'),('toggle','valueChange'),('field','textChange'),('field','textChange'),('field','submit')]
cuaState=json.loads((OUT/'cua-observations.json').read_text())['observations'][-1]['after']['nodes']
baseline=json.loads((OUT/'cua-baseline-observations.json').read_text())
baseField=baseline['observations'][-1]['after']['nodes']['field']
assert cuaState['field']['text'].replace('QA','',1)==baseField['text'] and cuaState['field']['firstResponder'] and not cuaState['toggle']['checked']
assert all(c['pass'] for c in json.loads((OUT/'cua-observations.json').read_text())['checks'])
assert cuaState['field']['inputIdentity']==stages['interactive']['nodes']['field']['inputIdentity']
cleanup=json.loads((BASE/'owned-simulator-cleanup.json').read_text())
assert cleanup['allOwnedSimulatorsRetired'] and all(x['exitCode']==0 for x in cleanup['commands'])
(OUT/'pixel-analysis.json').write_text(json.dumps(samples,indent=2)+'\n')
receipt={'scope':'Offline captured-input integrity, actual native assertion outputs and decoded compositor paint/blink pixels; no physical/store/signed authority',
         'nativeCheckCount':len(observations['checks']),'nativeFinalCheckCount':len(json.loads((OUT/'cua-observations.json').read_text())['checks']),'builtAppArchiveVerified':True,'inputCount':len(lock['sha256']),'liveSourceClosureChecked':args.check_live,'supportingLiveInputDrift':supportingDrift,'pixelSamples':samples}
(OUT/'offline-verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
