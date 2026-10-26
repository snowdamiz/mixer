#!/usr/bin/env python3
"""Descriptor inventory and navigable source spans; no runtime inference."""
from pathlib import Path
import hashlib,json,re,xml.etree.ElementTree as ET
O=Path(__file__).resolve().parents[1]
root=O.parents[1]
collection=json.loads((O/'collection.json').read_text())
for rel in ['native/android/tests/NativeOwnerV2ConcreteHostTests.java',
 *['native/android/tests/NativeOwnerV2ConcreteHostLeaves/'+n for n in [
 'android/view/inputmethod/InputConnection.java','android/view/inputmethod/InputConnectionWrapper.java',
 'android/view/inputmethod/BaseInputConnection.java','android/widget/EditText.java']]]:
    src=root/rel; dest=O/'inputs'/rel; dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(src.read_bytes());b=dest.read_bytes()
    collection['sources']=[x for x in collection['sources'] if x['path']!=rel]
    collection['sources'].append({'path':rel,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
(O/'collection.json').write_text(json.dumps(collection,indent=2)+'\n')
raw=(O/'logs/javap-2.stdout.txt').read_text().split('Compiled from "InputConnectionWrapper.java"')[0]
methods=[]
for decl,desc in re.findall(r'  (public (?:abstract |default )?[^\n]*\([^\n]*\);)\n    descriptor: (\S+)',raw):
    name=re.search(r'(\w+)\(',decl).group(1);methods.append({'name':name,'declaration':decl,'descriptor':desc,'default':' default ' in decl})
api=ET.parse(O/'official/sdk37/api-versions.xml').getroot().find("class[@name='android/view/inputmethod/InputConnection']")
metadata={m.attrib['name']:m.attrib for m in api.findall('method')}
views=(O/'inputs/native/android/app/src/dev/mixer/android/NativeAppearanceViewsV2.java').read_text()
wrapper=views[views.index('return new android.view.inputmethod.InputConnectionWrapper'):views.index('    private static final class NativeSwitch')]
implemented=re.findall(r'@Override public [^\n]*? (\w+)\(([^)]*)\)',wrapper.split('            };')[0])
impl_counts={n:sum(1 for x,_ in implemented if x==n) for n,_ in implemented}
for m in methods:
    key=m['name']+m['descriptor']; m['sdk37_metadata']=metadata.get(key)
    assert m['sdk37_metadata'],key
    m['api_since']=int(m['sdk37_metadata'].get('since',api.attrib.get('since','1')))
    m['current_route']='explicit_nativefield_override' if m['name'] in impl_counts else 'inherited_wrapper_direct_target'
    m['wrapper_forwarding']='API36 InputConnectionWrapper calls mTarget.'+m['name']+' directly; it does not invoke this proxy sibling methods'
assert len(methods)==38,len(methods)
assert len(implemented)==24,len(implemented)
(O/'method-inventory.json').write_text(json.dumps({'source':'official SDK37 android.jar javap descriptors, API versions metadata; Android16_r1 wrapper source route','methods':methods,'method_count':len(methods),'overridden_count':len(implemented),'inherited_count':len(methods)-len(implemented),'setTarget':'extra wrapper method (not InputConnection); nonnull target + mutable=false => SecurityException; no present retarget bypass'},indent=2)+'\n')
print(json.dumps({'methods':len(methods),'overrides':len(implemented),'inherited':[(m['name'],m['descriptor'],m['api_since']) for m in methods if m['current_route'].startswith('inherited') ]},indent=2))
