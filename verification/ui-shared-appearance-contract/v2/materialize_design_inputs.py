#!/usr/bin/env python3
"""Design fixture generator; not a Mixer build tool or production implementation."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
D = {}
SWIFT = []
STRUCT_FIELDS = {}
ENUM_NAMES = set()

def ref(name): return {"$ref": "#/$defs/" + name}
def integer(low, high): return {"type": "integer", "minimum": low, "maximum": high}
def text(low, high, pattern=None):
    result = {"type": "string", "minLength": low, "maxLength": high}
    if pattern is not None: result["pattern"] = pattern
    return result
def array(item, low=0, high=64): return {"type": "array", "items": item, "minItems": low, "maxItems": high}
def obj(fields): return {"type": "object", "additionalProperties": False, "required": list(fields), "properties": fields}
def enum(name, values, swift):
    ENUM_NAMES.add(name)
    D[name] = {"enum": values}
    SWIFT.append(f'public enum {name}: {swift}, Sendable, Equatable {{\n' + "\n".join(
        f'    case {value} = "{value}"' if swift == "String" else f'    case w{value} = {value}' for value in values) + '\n}')
def struct(name, fields):
    STRUCT_FIELDS[name] = fields
    D[name] = obj({key: schema for key, _, schema in fields})
    SWIFT.append(f'public struct {name}: Sendable, Equatable {{\n' +
                 "\n".join(f'    public let {key}: {kind}' for key, kind, _ in fields) +
                 '\n    public init(' + ", ".join(f'{key}: {kind}' for key, kind, _ in fields) + ') {\n' +
                 "\n".join(f'        self.{key} = {key}' for key, _, _ in fields) + '\n    }\n}')

metric = integer(0, 65536)
identifier = text(1, 128, '^[A-Za-z0-9_.-]+$')
path = text(1, 256, '^[A-Za-z0-9_-][A-Za-z0-9_.-]*(/[A-Za-z0-9_-][A-Za-z0-9_.-]*)*$')
digest = text(64, 64, '^[0-9a-f]{64}$')
color = text(9, 9, '^#[0-9A-F]{8}$')
enum('UIRecipeV1', ['sharedCandidate1'], 'String')
enum('UIFontWeightV1', [400, 500, 600, 700], 'UInt16')
enum('UIFontStyleV1', ['normal', 'italic'], 'String')
enum('UIFontFallbackV1', ['none', 'systemSans'], 'String')
enum('UIResourceKindV1', ['fontSFNT', 'iconPNG'], 'String')
enum('UIResourceDirectionV1', ['neutral', 'leftToRight', 'rightToLeft'], 'String')
enum('UIHorizontalAlignmentV1', ['leading', 'center', 'trailing'], 'String')
enum('UIVerticalAlignmentV1', ['top', 'center', 'bottom', 'firstTextBaseline', 'lastTextBaseline'], 'String')
enum('UIOverlayAlignmentV1', ['center', 'leading', 'trailing', 'top', 'bottom', 'topLeading', 'topTrailing', 'bottomLeading', 'bottomTrailing'], 'String')
enum('UIColorSchemeV1', ['light', 'dark'], 'String')
enum('UILayoutDirectionV1', ['leftToRight', 'rightToLeft'], 'String')
struct('UIInsets64V1', [(key, 'UInt32', metric) for key in ('top', 'leading', 'bottom', 'trailing')])
struct('UIPaletteV1', [(key, 'UIRGBA8V1', color) for key in (
    'canvas', 'surface', 'primaryText', 'secondaryText', 'accent', 'destructive',
    'disabledText', 'separator', 'focus', 'toggleOff', 'toggleThumb')])
struct('UITextMetricV1', [('size64', 'UInt32', integer(64, 16384)),
    ('weight', 'UIFontWeightV1', ref('UIFontWeightV1')), ('minimumLineBox64', 'UInt32', integer(64, 65536))])
struct('UIFontFaceV1', [('resourceID', 'String', identifier), ('postScriptName', 'String', text(1, 128, '^[!-~]+$')),
    ('weight', 'UIFontWeightV1', ref('UIFontWeightV1')), ('style', 'UIFontStyleV1', ref('UIFontStyleV1'))])
D['UIFontSourceV1'] = {'oneOf': [obj({'kind': {'const': 'systemSans'}}), obj({
    'kind': {'const': 'bundled'}, 'faces': array(ref('UIFontFaceV1'), 1, 16), 'fallback': ref('UIFontFallbackV1')})]}
SWIFT.append('public enum UIFontSourceV1: Sendable, Equatable {\n    case systemSans\n    case bundled(faces: [UIFontFaceV1], fallback: UIFontFallbackV1)\n}')
struct('UITypographyV1', [('font', 'UIFontSourceV1', ref('UIFontSourceV1'))] + [
    (key, 'UITextMetricV1', ref('UITextMetricV1')) for key in ('body', 'headline', 'title', 'caption')])
struct('UIListMetricsV1', [('insets64', 'UIInsets64V1', ref('UIInsets64V1'))] + [
    (key, 'UInt32', metric) for key in ('minimumRow64', 'rowGap64', 'groupGap64', 'separator64')])
struct('UINavigationMetricsV1', [('titleInsets64', 'UIInsets64V1', ref('UIInsets64V1')),
    ('minimumBarHeight64', 'UInt32', metric), ('titleAlignment', 'UIHorizontalAlignmentV1', ref('UIHorizontalAlignmentV1'))])
struct('UILayoutMetricsV1', [('stackGap64', 'UInt32', metric),
    ('vStackAlignment', 'UIHorizontalAlignmentV1', ref('UIHorizontalAlignmentV1')),
    ('hStackAlignment', 'UIVerticalAlignmentV1', ref('UIVerticalAlignmentV1')),
    ('zStackAlignment', 'UIOverlayAlignmentV1', ref('UIOverlayAlignmentV1')),
    ('list', 'UIListMetricsV1', ref('UIListMetricsV1')),
    ('sectionHeaderInsets64', 'UIInsets64V1', ref('UIInsets64V1')),
    ('navigation', 'UINavigationMetricsV1', ref('UINavigationMetricsV1'))])
struct('UIButtonMetricsV1', [('labelInsets64', 'UIInsets64V1', ref('UIInsets64V1'))] + [
    (key, 'UInt32', metric) for key in ('minimumWidth64', 'minimumHeight64', 'radius64')])
struct('UIFieldMetricsV1', [('insets64', 'UIInsets64V1', ref('UIInsets64V1'))] + [
    (key, 'UInt32', metric) for key in ('minimumHeight64', 'border64')])
struct('UIToggleMetricsV1', [(key, 'UInt32', metric) for key in (
    'trackWidth64', 'trackHeight64', 'thumb64', 'inset64', 'labelGap64', 'minimumRow64')])
struct('UIControlMetricsV1', [('button', 'UIButtonMetricsV1', ref('UIButtonMetricsV1')),
    ('field', 'UIFieldMetricsV1', ref('UIFieldMetricsV1')), ('toggle', 'UIToggleMetricsV1', ref('UIToggleMetricsV1')),
    ('focusWidth64', 'UInt32', metric), ('focusRadius64', 'UInt32', metric),
    ('pressedOpacityPermille', 'UInt16', integer(0, 1000)), ('selectionOpacityPermille', 'UInt16', integer(0, 1000))])
struct('UIThemeV1', [('recipe', 'UIRecipeV1', ref('UIRecipeV1')), ('light', 'UIPaletteV1', ref('UIPaletteV1')),
    ('dark', 'UIPaletteV1', ref('UIPaletteV1')), ('typography', 'UITypographyV1', ref('UITypographyV1')),
    ('layout', 'UILayoutMetricsV1', ref('UILayoutMetricsV1')), ('controls', 'UIControlMetricsV1', ref('UIControlMetricsV1'))])
struct('UIAppearanceResourceV1', [('id', 'String', identifier), ('kind', 'UIResourceKindV1', ref('UIResourceKindV1')),
    ('path', 'String', path), ('sha256', 'String', digest), ('bytes', 'UInt32', integer(1, 4194304)),
    ('provenance', 'String', text(1, 512, '^[ -~]+$')), ('scale', 'UInt8', integer(1, 4)),
    ('locale', 'String', text(1, 64, '^[A-Za-z0-9]+(-[A-Za-z0-9]+)*$')),
    ('direction', 'UIResourceDirectionV1', ref('UIResourceDirectionV1'))])
resources = array(ref('UIAppearanceResourceV1'))
common = {'format': {'const': 'mixer.native-appearance.1'}, 'id': identifier}
D['shared'] = obj({**common, 'mode': {'const': 'shared'}, 'theme': ref('UIThemeV1'), 'resources': resources})
D['platformSpecific'] = obj({**common, 'mode': {'const': 'platformSpecific'}, 'iOS': ref('UIThemeV1'),
    'android': ref('UIThemeV1'), 'reason': text(1, 512, '^[ -~]+$'), 'resources': resources})
schema = {'$schema': 'https://json-schema.org/draft/2020-12/schema',
    '$id': 'https://mixer.invalid/design/native-appearance-v1',
    'title': 'Design proposal only: Mixer native appearance descriptor 1',
    'oneOf': [ref('shared'), ref('platformSpecific')], '$defs': D}

def insets(top=0, leading=0, bottom=0, trailing=0):
    return dict(top=top*64, leading=leading*64, bottom=bottom*64, trailing=trailing*64)
def text_metric(size, weight, line): return dict(size64=size*64, weight=weight, minimumLineBox64=line*64)
def palette(values):
    keys = ('canvas','surface','primaryText','secondaryText','accent','destructive','disabledText','separator','focus','toggleOff','toggleThumb')
    return {k: '#' + v + 'FF' for k, v in zip(keys, values.split(), strict=True)}
theme = dict(recipe='sharedCandidate1',
    light=palette('FFFFFF F2F2F7 000000 606068 007AFF FF3B30 8E8E93 D1D1D6 007AFF E5E5EA FFFFFF'),
    dark=palette('000000 1C1C1E FFFFFF AEAEB2 0A84FF FF453A 8E8E93 38383A 0A84FF 39393D FFFFFF'),
    typography=dict(font=dict(kind='systemSans'), body=text_metric(17,400,22), headline=text_metric(17,600,22),
                    title=text_metric(28,400,34), caption=text_metric(12,400,16)),
    layout=dict(stackGap64=512, vStackAlignment='center', hStackAlignment='center', zStackAlignment='center',
        list=dict(insets64=insets(8,16,8,16),minimumRow64=2816,rowGap64=0,groupGap64=1024,separator64=64),
        sectionHeaderInsets64=insets(16,0,8,0), navigation=dict(titleInsets64=insets(8,16,8,16),
        minimumBarHeight64=2816,titleAlignment='leading')),
    controls=dict(button=dict(labelInsets64=insets(),minimumWidth64=2816,minimumHeight64=2816,radius64=512),
        field=dict(insets64=insets(),minimumHeight64=2816,border64=0),
        toggle=dict(trackWidth64=3264,trackHeight64=1984,thumb64=1728,inset64=128,labelGap64=512,minimumRow64=2816),
        focusWidth64=128,focusRadius64=512,pressedOpacityPermille=120,selectionOpacityPermille=240))
default = dict(format='mixer.native-appearance.1',id='mixer.default.v1',mode='shared',theme=theme,resources=[])
canonical = lambda value: (json.dumps(value,sort_keys=True,ensure_ascii=True,separators=(',', ':'))+'\n').encode()
(HERE/'descriptor-schema.json').write_bytes(canonical(schema))
(HERE/'mixer-default-appearance-v1.json').write_bytes(canonical(default))
prefix = '''// DESIGN ONLY: concrete proposed value types, no production codec/renderer.
// Raw constructors do not validate; every codec/prepare entry validates the whole graph.
import Foundation
public struct UIRGBA8V1: Sendable, Equatable {
    public let red, green, blue, alpha: UInt8
    public init(red: UInt8, green: UInt8, blue: UInt8, alpha: UInt8) {
        self.red = red; self.green = green; self.blue = blue; self.alpha = alpha
    }
}
'''
suffix = '''
public enum UIAppearanceModeV1: Sendable, Equatable {
    case shared(UIThemeV1)
    case platformSpecific(iOS: UIThemeV1, android: UIThemeV1, reason: String)
}
public struct UIAppearanceConfigurationV1: Sendable, Equatable {
    public static let format = "mixer.native-appearance.1"
    public let id: String
    public let mode: UIAppearanceModeV1
    public let resources: [UIAppearanceResourceV1]
    public init(id: String, mode: UIAppearanceModeV1, resources: [UIAppearanceResourceV1] = []) {
        self.id = id; self.mode = mode; self.resources = resources
    }
}
public struct UIAppearanceEnvironmentV1: Sendable, Equatable {
    public let scheme: UIColorSchemeV1
    public let direction: UILayoutDirectionV1
    public let textScale1024, density1024: UInt16
    public init(scheme: UIColorSchemeV1, direction: UILayoutDirectionV1,
                textScale1024: UInt16, density1024: UInt16) {
        self.scheme = scheme; self.direction = direction
        self.textScale1024 = textScale1024; self.density1024 = density1024
    }
}
public enum UIAppearanceErrorV1: Error, Sendable, Equatable {
    case byteLimit, invalidEncoding, syntax, duplicateKey, depthLimit, valueLimit
    case noncanonical, shape, number, resourceCatalog, fontCatalog, geometry
}
// These function-typed parameters typecheck the proposed concrete codec signatures.
// No codec implementation, extension point or authority protocol is supplied here.
func requireCodecSignatures(
    decode: (Data) throws -> UIAppearanceConfigurationV1,
    canonicalData: (UIAppearanceConfigurationV1) throws -> Data,
    validate: (UIAppearanceConfigurationV1) throws -> Void
) {}
func requireMetricSignatures(
    scaled64: (UInt32, UInt16) throws -> UInt32,
    pixels: (UInt32, UInt16) throws -> UInt32,
    spacing64: (Double) throws -> UInt32,
    normalizeTextScale: (Double) throws -> UInt16,
    normalizeDensity: (Double) throws -> UInt16
) {}
'''
def literal(kind, value):
    if kind.startswith('UInt'): return str(value)
    if kind == 'String': return json.dumps(value)
    if kind == 'UIRGBA8V1':
        values = [int(value[i:i+2], 16) for i in (1,3,5,7)]
        return 'UIRGBA8V1('+', '.join(f'{key}: {v}' for key,v in zip(('red','green','blue','alpha'),values,strict=True))+')'
    if kind in ENUM_NAMES: return '.w'+str(value) if kind == 'UIFontWeightV1' else '.'+value
    if kind == 'UIFontSourceV1' and value == {'kind':'systemSans'}: return '.systemSans'
    return kind+'('+', '.join(f'{key}: '+literal(field_type,value[key]) for key,field_type,_ in STRUCT_FIELDS[kind])+')'
typed_default = '''
// Construct the actual default fixture through every proposed initializer.
// This is not a decoder or the production default implementation.
func typedDefaultProbe() -> UIAppearanceConfigurationV1 {
    UIAppearanceConfigurationV1(id: "mixer.default.v1", mode: .shared(
        '''+literal('UIThemeV1', theme)+'''), resources: [])
}
'''
(HERE/'AppearanceV1Declarations.swift').write_text(prefix+'\n\n'.join(SWIFT)+'\n'+suffix+typed_default)
print(json.dumps({'generated': ['descriptor-schema.json','mixer-default-appearance-v1.json','AppearanceV1Declarations.swift'],
                  'default_bytes': len(canonical(default)), 'scope': 'design fixtures only'}))
