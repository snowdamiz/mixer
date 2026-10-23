#!/usr/bin/env python3
"""Initial authoring helper for Mixer-owned closed values/codec; not a runtime dependency."""
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
HERE=ROOT/'verification/ui-appearance-descriptor-v2'
sample=(ROOT/'verification/ui-measured-appearance-v2-contract/ContractTypes.swift').read_text().split('// Internal native-consumer seam.')[0]
schema=json.loads((ROOT/'verification/ui-measured-appearance-v2-contract/descriptor-schema.json').read_text())['$defs']
types={}
for match in re.finditer(r'public struct (\w+): Sendable \{(.*?)\n?\}',sample,re.S):
    fields=[]
    for declaration in re.finditer(r'public let ([\w, ]+): ([\w\[\]]+)',match[2]):
        fields += [(name.strip(),declaration[2]) for name in declaration[1].split(',')]
    types[match[1]]=fields
names={'UIRoleMetricsV2':'Roles','UIProfilesV2':'Profiles','UIProfileFloorsV2':None,'UITypographyV2':'Typography','UIRolePaintsV2':None,'UIOutlineV2':'Outline','UIButtonPaintV2':'ButtonPaint','UIButtonStatesV2':'ButtonStates','UIButtonRolesV2':None,'UIFieldPaintV2':'FieldPaint','UIFieldStatesV2':'FieldStates','UITogglePaintV2':'TogglePaint','UIToggleStatesV2':'ToggleStates','UIToggleValuesV2':None,'UIPaintsV2':'Paints','UIStackMetricsV2':'Stacks','UIGroupedListMetricsV2':'GroupedList','UIButtonMetricsV2':'ButtonMetrics','UIFieldMetricsV2':'FieldMetrics','UIToggleMetricsV2':'ToggleMetrics','UINavigationMetricsV2':'Navigation','UIThemeV2':'Theme','UIAppearanceResourceV1':'UIAppearanceResourceV1','UIFontFaceV1':'UIFontFaceV1','UIInsets64V1':'UIInsets64V1','UISharedTextMetricsV1':'Metric'}
extra={'UIProfileFloorsV2':schema['GroupedList']['properties']['profileFloors64'],'UIRolePaintsV2':schema['Paints']['properties']['text'],'UIButtonRolesV2':schema['Paints']['properties']['button'],'UIToggleValuesV2':schema['Paints']['properties']['toggle']}
values='''// Untrusted, immutable V2 data values. Codec validation supplies no installed
// resource, native rendering, signed presentation, or release authority.
import Foundation

public enum UIRecipeV2: String, Sendable, Equatable { case measuredShared2 }
public enum UIAppearanceModeV2: Sendable, Equatable {
    case shared(UIThemeV2)
    case platformSpecific(iOS: UIThemeV2, android: UIThemeV2, reason: String)
}
public enum UIProfilePreferencePolicyV2: String, Sendable, Equatable { case nearestBody64TiesUpRejectOutside }
public enum UIMissingVStackGapV2: String, Sendable, Equatable { case bodyThenCaptionPairOtherwiseDefault }
public enum UIRowPolicyV2: String, Sendable, Equatable { case maxProfileFloorSemanticContentPlusInsets }
public enum UISeparatorPolicyV2: String, Sendable, Equatable { case interiorRowsOnly }
public enum UICheckedEndV2: String, Sendable, Equatable { case logicalTrailing }
public enum UINavigationCollapseV2: String, Sendable, Equatable { case snapAtExpandedOverflow }
public enum UINavigationTitleWrapV2: String, Sendable, Equatable { case growExpandedEllipsizeCompactOneLine }

/// Data admission errors are distinct from later native/runtime failures.
public enum UIAppearanceErrorV2: Error, Sendable, Equatable {
    case byteLimit, invalidEncoding, syntax, duplicateKey, depthLimit, valueLimit, arrayLimit
    case noncanonical, shape, number, resourceCatalog, fontCatalog, unsupportedProfile, geometry
    case unsupportedNativeOperation, layout, nativeAttachment
}
'''
for name,fields in types.items():
    values+='\npublic struct '+name+': Sendable, Equatable {\n'
    if name=='UIAppearanceConfigurationV2': values+='    public static let format = "mixer.native-appearance.2"\n'
    for key,t in fields: values+=f'    public let {key}: {t}\n'
    args=', '.join(f'{key}: {t}'+(' = []' if name=='UIAppearanceConfigurationV2' and key=='resources' else '') for key,t in fields)
    values+=f'    public init({args}) {{\n'
    values+=''.join(f'        self.{key} = {key}\n' for key,t in fields)+'    }\n}\n'
(ROOT/'sdk/Sources/MixerUI/AppearanceValuesV2.swift').write_text(values)
golden=(ROOT/'verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json').read_text()
(ROOT/'sdk/Sources/MixerUI/AppearanceDefaultV2.swift').write_text('''import Foundation

// One canonical default table. This explicit opt-in does not replace V1 or install
// fonts/resources; the authored recipe still needs native consumer qualification.
private let mixerMeasuredDefaultBytesV2 = Data((##"'''+golden.rstrip('\n')+'''"## + "\\n").utf8)

public extension UIAppearanceDescriptorCodecV2 {
    static func mixerDefaultV2() throws -> UIAppearanceConfigurationV2 {
        try decode(mixerMeasuredDefaultBytesV2)
    }
}
''')
# Reuse only independently owned V1 bounded JSON mechanics, in this private V2 namespace.
v1=(ROOT/'sdk/Sources/MixerUI/AppearanceDescriptorV1.swift').read_text()
base=v1[:v1.index('private extension UIPaletteV1')]
base=base.replace('UIAppearanceDescriptorCodecV1','UIAppearanceDescriptorCodecV2').replace('UIAppearanceConfigurationV1','UIAppearanceConfigurationV2').replace('UIAppearanceErrorV1','UIAppearanceErrorV2')
base=re.sub(r'(AppearanceJSON|AppearanceReader|AppearanceWriter|appearance\w+)V1',r'\1V2',base)
base=base.replace('depth <= 16','depth <= 20').replace('values < 4096','values < 8192').replace('global 4096-value','global 8192-value')
base=base.replace('throw UIAppearanceErrorV2.shape }\n                let child', 'throw UIAppearanceErrorV2.arrayLimit }\n                let child')
# Depth measures containers, so scalar leaves at level20 are legal.
base=base.replace('guard depth <= 20 else { throw UIAppearanceErrorV2.depthLimit }\n        guard values', 'guard values')
base=base.replace('case 123:\n            cursor', 'case 123:\n            guard depth <= 20 else { throw UIAppearanceErrorV2.depthLimit }\n            cursor')
base=base.replace('case 91:\n            cursor', 'case 91:\n            guard depth <= 20 else { throw UIAppearanceErrorV2.depthLimit }\n            cursor')
base=base.replace('case let .object(fields):\n            try byte', 'case let .object(fields):\n            guard depth <= 20 else { throw UIAppearanceErrorV2.depthLimit }\n            try byte')
base=base.replace('case let .array(items):\n            guard items.count <= 64 else { throw UIAppearanceErrorV2.shape }', 'case let .array(items):\n            guard depth <= 20 else { throw UIAppearanceErrorV2.depthLimit }\n            guard items.count <= 64 else { throw UIAppearanceErrorV2.arrayLimit }')
# Private reused V1 type method names cannot shadow the V1 codec.
base=base.replace('appearanceRead(', 'appearanceReadV2(').replace('appearanceWrite()', 'appearanceWriteV2()')
# Types are fixed below; omit the already-present insets codec from this base.
base=base[:base.index('private extension UIInsets64V1')]
for name in ['UIAppearanceResourceV1','UIFontFaceV1','UIInsets64V1','UISharedTextMetricsV1']:
    # Read primitive field declarations from their owned V1 sources.
    source=(ROOT/('sdk/Sources/MixerUI/SharedTextProfilesV1.swift' if name=='UISharedTextMetricsV1' else 'sdk/Sources/MixerUI/AppearanceValuesV1.swift')).read_text()
    body=source.split('public struct '+name+':')[1].split('public init')[0].split('\n}')[0]
    fields=[]
    for dec in re.finditer(r'public let ([\w, ]+): ([\w\[\]]+)',body): fields += [(n.strip(),dec[2]) for n in dec[1].split(',')]
    types[name]=fields

def resolved(s): return schema[s['$ref'].split('/')[-1]] if '$ref' in s else s

def readexpr(key,t,s):
    v=f'f["{key}"]!'; s=resolved(s)
    if t.startswith('UI') and t in types: return f'try {t}.appearanceReadV2({v})'
    if t=='UIRGBA8V1': return f'try UIRGBA8V1.appearanceReadV2({v})'
    if t=='UIFontSourceV1': return f'try UIFontSourceV1.appearanceReadV2({v})'
    if t.startswith('UInt'):
        lo=s.get('const',s.get('minimum',0)); hi=s.get('const',s.get('maximum',65536))
        return f'{t}(try {v}.number({lo}, {hi}))'
    if t=='UIFontWeightV1': return f'try appearanceWeightV2({v})'
    if t=='String':
        special={'id':'ID','resourceID':'ID','path':'Path','locale':'Locale','sha256':'Sha256','provenance':'Printable'}
        if key in special: return f'try appearance{special[key]}V2({v})'
        return f'try appearanceTextV2({v}, 1, 128) {{ (33...126).contains($0) }}'
    if 'const' in s: return f'try appearanceConstantV2({v}, "{s["const"]}", .{s["const"]})'
    return f'try appearanceEnumV2({v}, {t}.self)'

def writeexpr(key,t,s):
    if t in types or t in ('UIRGBA8V1','UIFontSourceV1'): return f'try {key}.appearanceWriteV2()'
    if t.startswith('UInt'): return f'.uint(UInt64({key}))'
    if t=='UIFontWeightV1': return f'.uint(UInt64({key}.rawValue))'
    if t=='String': return f'try appearanceStringV2({key}, {resolved(s).get("maxLength",512)})'
    return f'.string({key}.rawValue)'

for name,fields in types.items():
    if name=='UIAppearanceConfigurationV2': continue
    spec=extra.get(name) or schema[names[name]]
    props=spec['properties']
    base+=f'\nprivate extension {name} {{\n    static func appearanceReadV2(_ value: AppearanceJSONV2) throws -> Self {{\n'
    base+='        let f = try value.fields(['+', '.join('"'+k+'"' for k,t in fields)+'])\n'
    base+='        return Self('+',\n            '.join(k+': '+readexpr(k,t,props[k]) for k,t in fields)+')\n    }\n'
    base+='    func appearanceWriteV2() throws -> AppearanceJSONV2 {\n        .object(['+',\n            '.join('"'+k+'": '+writeexpr(k,t,props[k]) for k,t in fields)+'])\n    }\n}\n'
# Primitive helpers are independent V1 engine code reused in the V2 private namespace.
start=v1.index('private func appearancePathV1')
end=v1.index('private extension UIAppearanceConfigurationV1')
helpers=v1[start:end]
helpers=re.sub(r'(AppearanceJSON|appearance\w+)V1',r'\1V2',helpers).replace('UIAppearanceErrorV1','UIAppearanceErrorV2').replace('appearanceRead(', 'appearanceReadV2(').replace('appearanceWrite()', 'appearanceWriteV2()')
base+='\n'+helpers
config=v1[v1.index('private extension UIAppearanceConfigurationV1'):v1.index('private func appearanceSemanticsV1')]
config=config.replace('UIAppearanceConfigurationV1','UIAppearanceConfigurationV2').replace('UIAppearanceModeV1','UIAppearanceModeV2').replace('UIThemeV1','UIThemeV2').replace('UIAppearanceErrorV1','UIAppearanceErrorV2')
config=re.sub(r'(AppearanceJSON|appearance\w+)V1',r'\1V2',config).replace('appearanceRead(', 'appearanceReadV2(').replace('appearanceWrite()', 'appearanceWriteV2()')
base+='\n'+config
base+='''
private func appearanceConstantV2<T>(_ value: AppearanceJSONV2, _ expected: String, _ result: T) throws -> T {
    guard try value.text() == expected else { throw UIAppearanceErrorV2.shape }
    return result
}
'''
(ROOT/'sdk/Sources/MixerUI/AppearanceDescriptorV2.swift').write_text(base)
