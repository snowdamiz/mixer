from pathlib import Path
import json,hashlib,datetime,difflib,subprocess
ROOT=Path(__file__).resolve().parent;repo=ROOT.parents[1];measurement=repo/'verification/apple-appearance-measurement';reference=repo/'verification/apple-appearance-reference'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
receipt=json.loads((measurement/'receipt.json').read_text());bindings={}
for e in receipt['artifacts']:
 p=measurement/e['path'];assert p.stat().st_size==e['bytes'] and sha(p)==e['sha256'];bindings[str(p.relative_to(repo))]=sha(p)
assert len(receipt['artifacts'])==359
assert hashlib.sha256(json.dumps(receipt['artifacts'],sort_keys=True,separators=(',',':')).encode()).hexdigest()==receipt['artifactCollectionSHA256']
external=repo/receipt['externalDocument']['path'];assert sha(external)==receipt['externalDocument']['sha256'];bindings[str(external.relative_to(repo))]=sha(external)
base=reference/'frozen/sdk/Sources/MixerApple/MixerNativeView.swift';changed=measurement/'instrumented-sdk/Sources/MixerApple/MixerNativeView.swift'
actual=''.join(difflib.unified_diff(base.read_text().splitlines(True),changed.read_text().splitlines(True),fromfile='frozen/MixerNativeView.swift',tofile='instrumented-sdk/Sources/MixerApple/MixerNativeView.swift'))
assert actual==(measurement/'instrumentation.patch').read_text()
commands=json.loads((ROOT/'commands.json').read_text())['commands'];assert len(commands)==6 and all(c['exit_code']==0 for c in commands)
for c in commands:assert sha(ROOT/c['log'])==c['sha256']
native=json.loads((ROOT/'native-decoder-result.json').read_text());assert len(native['records'])==24 and len(native['comparisons'])==28 and all(c['identical_pixels'] for c in native['comparisons'])
for c in native['comparisons']:
 p=repo/c['reference'];bindings[str(p.relative_to(repo))]=sha(p)
for p in [measurement/'receipt.json',reference/'receipt.json',base]:bindings[str(p.relative_to(repo))]=sha(p)
for p in sorted(ROOT.rglob('*')):
 if p.is_file() and p.name!='acceptance.json' and not any(x in p.relative_to(ROOT).parts for x in ['build','__pycache__']):bindings[str(p.relative_to(repo))]=sha(p)
result={'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'decision':'accepted-isolated-simulator-measurement-reference-only','reviewer':'root','base_revision':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'binding_count':len(bindings),'bindings':dict(sorted(bindings.items())),'evidence':{'producer_artifacts':359,'native_captures':24,'independently_decoded_pixel_digests':24,'independent_exact_historical_comparisons':16,'independent_exact_debug_release_comparisons':12,'pixels_per_image':3162132,'root_visual_review':['debug/controls-light','debug/controls-dark','debug/typography-accessibility-light','debug/controls-accessibility-dark'],'native_commands':'commands.json','first_reviewer_attempt':'first-attempt/result.json'},'findings':['The frozen renderer delta exactly matches its recorded geometry-only instrumentation patch; public measurement records and original reference seals verify.','Per-role Dynamic Type scaling, distinct navigation/section roles, per-control disabled paints and grouped-list/switch geometry require explicit shared contract refinement. Candidate1 is not accepted as an iOS-reference match.','Independent ImageIO decoder reproduced every producer raw pixel digest after explicitly removing native RGBX unused bytes; no pixel transformation or image editing.'],'limits':['Simulator measurement and reference integrity only. This is not shared recipe, native renderer integration or physical parity acceptance.','Four new accessibility LTR profiles lack historical uninstrumented controls; later rows are outside the initial viewport.','Header/control contextual fonts, glyph fallback, switch interior and group/transition/input/accessibility behavior remain unresolved in this slice.','No physical runs, installed signed resources/display/health, immutable published FieldLog, store/customer/operational or GA qualification.']}
(ROOT/'acceptance.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',len(bindings),'root measurement bindings')
