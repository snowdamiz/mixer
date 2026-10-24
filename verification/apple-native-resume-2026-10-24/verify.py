#!/usr/bin/env python3
"""Replay a failed native cover receipt; passing integrity never accepts its paint."""
import pathlib,json,hashlib,tarfile,datetime,platform
from PIL import Image
OUT=pathlib.Path(__file__).resolve().parent
REPO=OUT.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
obj=lambda name:json.loads((OUT/name).read_text())
lock=obj('captured-source-lock.json')
assert hashlib.sha256(json.dumps(lock['sha256'],sort_keys=True,separators=(',',':')).encode()).hexdigest()==lock['sourceClosureSHA256']
for name,digest in lock['sha256'].items():assert sha(OUT/'source'/name)==digest,name
built=obj('built-app.json');manifest=obj('built-app-manifest.json')
assert sha(OUT/manifest['archive'])==manifest['sha256']
with tarfile.open(OUT/manifest['archive']) as archive:
 for name,entry in manifest['files'].items():
  data=archive.extractfile('MixerAppearanceV2.app/'+name).read();assert len(data)==entry['bytes'] and hashlib.sha256(data).hexdigest()==entry['sha256'],name
installed=obj('installed-app-receipt.json');assert installed['matchesRetainedBuiltApp'] and all(manifest['files'][name]['sha256']==digest for name,digest in installed['hashes'].items())
for name in ['commands.json','build-commands.json','followup-commands.json']:
 assert all(c.get('exitCode',0)==0 for c in obj(name)),name
initial=obj('observations.json');final=obj('post-cancel-observations.json')
assert len(initial['checks'])==134 and len(final['checks'])==136 and all(c['pass'] for c in final['checks'])
base=obj('cua-baseline-observations.json');cua=obj('cua-observations.json')
delta=cua['actions'][len(base['actions']):]
assert [(a['id'],a['event']) for a in delta]==[('button','activate'),('toggle','valueChange'),('field','textChange'),('field','textChange'),('field','submit')]
bnodes=base['observations'][-1]['after']['nodes'];anodes=cua['observations'][-1]['after']['nodes']
assert anodes['field']['text']==bnodes['field']['text']+'QA' and anodes['field']['firstResponder'] and not anodes['toggle']['checked']
assert anodes['field']['inputIdentity']==bnodes['field']['inputIdentity']
assert anodes['list']['offset'][1]>0
heldbase=obj('held-baseline-observations.json')
assert len(final['actions'])==len(heldbase['actions'])
toggle=final['observations'][-1]['after']['nodes']['toggle']
assert not toggle['authoredPressed'] and toggle['cancellationCount']==1 and toggle['checked']
assert toggle['inputIdentity']==heldbase['observations'][-1]['after']['nodes']['toggle']['inputIdentity']
frames=obj('fixture-frames-roles-states.json');scale=frames['density1024']/1024
nodes={n['id']:n for n in frames['nodes']};t=nodes['toggle'];v=t['visual64'];w=t['windowFrame64'];x=(w[0]+v[0])/64;y=(w[1]+v[1])/64
samples={}
for stage in ['initial','toggle-input','disabled','held-toggle-1','held-toggle-2']:
 image=Image.open(OUT/(stage+'.png')).convert('RGB');assert image.size==(1206,2622)
 off=stage in ['toggle-input','disabled']
 points={'track':(x+(53 if off else 10),y+14),'thumb':(x+(20.5 if off else 42.5),y+14),'aboveVisual':(x+43,y-8)}
 samples[stage]={name:dict(logicalPoint=list(point),rgb=list(image.getpixel(tuple(round(c*scale) for c in point)))) for name,point in points.items()}
assert samples['initial']['track']['rgb']==[52,199,89]
assert samples['toggle-input']['track']['rgb']==[197,197,199]
assert samples['disabled']['track']['rgb']==[229,229,231]
for stage in ['held-toggle-1','held-toggle-2']:
 state=obj(stage+'-observations.json')['observations'][-1]['after']['nodes']['toggle']
 assert state['authoredPressed'] and state['checked'] and state['pressObservationCount']>0 and state['nativeCarrierAlpha']==1 and state['nativeLayerOpacity']==1 and state['coverNoninteractive']
 assert samples[stage]['track']['rgb']!=[46,191,109] and samples[stage]['thumb']['rgb']!=[255,255,255] and samples[stage]['aboveVisual']['rgb']!=[255,255,255]
cleanup=obj('cleanup.json');assert cleanup['allOwnedSimulatorsRetired'] and all(c['exitCode']==0 for c in cleanup['commands']) and cleanup['frontendProcessPresentAfterQuit'] is False
old=json.loads((REPO/'verification/apple-native-appearance-v2/headless-cover-final-coordinates/source-lock.json').read_text())['sha256']
changes={name:dict(prior=digest,captured=lock['sha256'].get(name)) for name,digest in old.items() if lock['sha256'].get(name)!=digest}
assert set(changes)=={'native/apple/appearance-v2/run.py','native/apple/appearance-v2/build-check.py'}
assert (OUT/'fixture-native-packet.bin').read_bytes()==(REPO/'verification/apple-native-appearance-v2/shared-fixture/native-packet-v1.bin').read_bytes()
assert (OUT/'fixture-frames-roles-states.json').read_bytes()==(REPO/'verification/apple-native-appearance-v2/candidate-13/fixture-frames-roles-states.json').read_bytes()
receipt=dict(status='native-assertions-and-input-passed-held-compositor-failed',observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),sourceRevision=lock['revision'],sourceTree=lock['tree'],sourceClosureSHA256=lock['sourceClosureSHA256'],sourceFiles=len(lock['sha256']),sourceSnapshot='source/',runtime=dict(version='26.5',build='23F77',simulator=cleanup['ownedSimulator'],physical=False),deploymentTarget='arm64-apple-ios26.0-simulator',nativeInitialAssertions=134,nativeFinalAssertions=136,nativeAssertionFailures=[],sourceChangesFromHeadless=changes,installedHashesMatchRetainedApp=True,coherentViewport=dict(points=[402,874],scale=3,pixels=[1206,2622]),sharedPacketAndFrameMapIdentical=True,actualCuaActionDelta=delta,nativeHeldObservation=True,disableCancellationAndLateReleaseWithoutAction=True,retainedNativeFieldAndSwitchIdentity=True,compositorPassed=False,expectedHeldPaint=dict(track=[46,191,109],thumb=[255,255,255],aboveVisual=[255,255,255]),actualCompositorSamples=samples,visualReview='Both held compositor captures show native elevated glass above opaque authored cover; root independently confirmed. Cover size is not a demonstrated mechanism for suppression.',cleanup=cleanup['allOwnedSimulatorsRetired'],preservedExistingSimulatorCount=len(cleanup['preservedOtherSimulatorIDs']),frontendQuitVerified=True,nativeAcceptance=False,gaAcceptance=False,limitations=['Current pressed switch paint fails actual compositor review; do not accept Apple appearance from native assertion count.','Private standalone UIKit consumer only: no engine/public facade/signed path join.','Only iOS26.5 simulator executed; other iOS versions remain unqualified.','Default RTL switch fixture and other cover-overlap contexts intentionally fail closed.','Physical phones, real IME workflow, VoiceOver and broader OS preference/window/interaction matrix remain deferred.'],verificationTools=dict(python=platform.python_version(),Pillow=Image.__version__))
if (OUT/'receipt.json').exists():
 retained=obj('receipt.json');receipt['observedUTC']=retained['observedUTC'];assert receipt==retained
else:(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(dict(status=receipt['status'],nativeChecks=136,compositorPassed=False)))
