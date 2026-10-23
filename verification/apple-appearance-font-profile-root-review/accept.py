from pathlib import Path
import hashlib,json,datetime,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];src=ROOT/'verification/apple-appearance-font-profile';base=ROOT/'verification/apple-appearance-measurement';bindings={}
def bind(p,digest=None):
 h=hashlib.sha256(p.read_bytes()).hexdigest();assert digest is None or h==digest,str(p);bindings[str(p.relative_to(ROOT))]=h;return h
commands=[]
for name in ['verify.py','verify-seal.py']:
 cmd=['python3','-B',str(src/'scripts'/name)];p=subprocess.run(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);log=HERE/(name+'.log');log.write_bytes(p.stdout);commands.append({'command':cmd,'exit_code':p.returncode,'log':str(log.relative_to(ROOT)),'sha256':bind(log)});assert p.returncode==0,p.stdout.decode()
r=json.loads((src/'receipt.json').read_text());assert len(r['artifacts'])==550
for e in r['artifacts']:assert (src/e['path']).stat().st_size==e['bytes'];bind(src/e['path'],e['sha256'])
assert hashlib.sha256(json.dumps(r['artifacts'],sort_keys=True,separators=(',',':')).encode()).hexdigest()==r['artifactCollectionSHA256']
bind(ROOT/r['externalDocument']['path'],r['externalDocument']['sha256']);bind(src/'receipt.json');bind(base/'receipt.json',r['priorMeasurementReceiptSHA256'])
m=json.loads((src/'observation-manifest.json').read_text());profiles=json.loads((src/'type-profiles.json').read_text())['profiles'];assert len(profiles)==12
for p in profiles:
 ident=p['normalizedProfileID'];d=json.loads((src/f'observations/debug/profile-{ident}/font-profile.json').read_text());o=json.loads((src/f'observations/release/profile-{ident}/font-profile.json').read_text())
 for key in ['resolvedSemanticFonts','nativeLineBoxProbes','nativePreferredContentSizeCategory','swiftUIDynamicTypeSize','largestNavigationTitleUILabel']:assert d[key]==o[key],(ident,key)
 assert p['fonts']==d['resolvedSemanticFonts'];assert p['nativeLineBoxProbes']==d['nativeLineBoxProbes'];assert p['swiftUIDynamicTypeSize']==d['swiftUIDynamicTypeSize'];assert p['nativePreferredContentSizeCategory']==d['nativePreferredContentSizeCategory']
 assert p['actualExpandedNavigationUIFont']==d['largestNavigationTitleUILabel']['font']
 for role in ['body','headline','title','caption']:
  first=d['nativeLineBoxProbes'][role+'.one']['height'];second=d['nativeLineBoxProbes'][role+'.two']['height'];assert second>first>0
  assert abs((second-first)-p['observedRepeatLineHeightIncrements'][role])<1e-8
comparisons=json.loads((src/'candidate-comparisons.json').read_text())['comparisons'];assert len(comparisons)==18
for c in comparisons:
 entry=next(e for e in m['captures'] if e['name']==c['name'] and e['configuration']==c['configuration']);a=src/entry['path']/'screenshot.png';b=base/'captures'/c['configuration'].lower()/c['baselineCase']/'screenshot.png'
 assert a.read_bytes()==b.read_bytes(),c['name'];bind(a,c['screenshotSHA256']);bind(b,c['baselineSHA256'])
 assert c['differentPixels']==0 and c['totalPixels']==3162132
bind(HERE/'accept.py')
result={'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reviewer':'root','decision':'accepted-native-type-profile-reference-and-bounded-contextual-font-candidates','source_revision':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'commands':commands,'binding_count':len(bindings),'bindings':dict(sorted(bindings.items())),'scope':{'native_type_profiles':12,'debug_release_exports':24,'independently_recomputed_role_line_advances':48,'byte_identical_candidate_pngs':15,'byte_identical_nonperturbation_pngs':3,'public_semantic_and_expanded_title_fonts':'Debug/Release raw exports and summary table agree'},'accepted_reference':['Twelve fixed profile sizes/weights and separate first-line boxes/line advances as measured in this native environment.','Expanded navigation uses measured largeTitle bold, independently from document title. Header headline and Button/Toggle body preserve observed pixels in the bounded large/accessibility1 matrix.'],'limitations':['Reference measurement only: neither current native renderer consumes a new shared recipe.','Proposed Android preference normalization is not accepted here. In particular scalar values beyond available profile anchors must not silently cap an unsupported accessibility request; root must freeze an explicit supported mapping before implementation.','Contextual equivalence at the other ten profiles, other fonts/scripts/OS settings, native Android conversion/glyphs/input/accessibility and physical parity remain pending.','First-line box and repeated-line advance are distinct; neither is a universal clipping bound.','No signed installed-resource/display/health, immutable published FieldLog, store/customer/operational or GA acceptance.']}
(HERE/'acceptance.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',len(bindings),'root font-profile bindings,18 byte-identical PNGs,12 independently reconstructed D/R tables')
