#!/usr/bin/env python3
"""Generate design artifacts only; never installs an appearance or changes V1."""
import copy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]
# Once frozen, replay against retained exact design inputs, never later product source.
if (HERE / "inputs/AGENTS.md").is_file(): ROOT = HERE / "inputs"
ROLES = ['body', 'headline', 'title', 'caption', 'sectionHeader', 'navigationExpanded']
PROFILES = ['xs', 's', 'm', 'l', 'xl', 'xxl', 'xxxl', 'a1', 'a2', 'a3', 'a4', 'a5']
KINDS = ['text', 'button', 'textField', 'toggle', 'vStack', 'hStack', 'zStack', 'list', 'section', 'navigation']
D = {}
def obj(fields):
    return {'type': 'object', 'additionalProperties': False, 'required': list(fields), 'properties': fields}
def ref(name): return {'$ref': '#/$defs/' + name}
def uint(lo=0, hi=65536): return {'type': 'integer', 'minimum': lo, 'maximum': hi}
def en(*values): return {'enum': list(values)}
def exact(value): return {'const': value}
def array(item, low, high): return {'type': 'array', 'items': item, 'minItems': low, 'maxItems': high}
def name(maximum=128): return {'type': 'string', 'minLength': 1, 'maxLength': maximum, 'pattern': '^[A-Za-z0-9_.-]+$'}
# Only safe V1 primitive/font/resource shapes are reused, never V1 theme/metrics.
v1 = json.loads((ROOT/'verification/ui-shared-appearance-contract/v2/descriptor-schema.json').read_text())['$defs']
for key in ['UIFontWeightV1', 'UIFontStyleV1', 'UIFontFallbackV1', 'UIFontFaceV1', 'UIFontSourceV1',
            'UIResourceKindV1', 'UIResourceDirectionV1', 'UIAppearanceResourceV1', 'UIInsets64V1',
            'UIHorizontalAlignmentV1', 'UIVerticalAlignmentV1', 'UIOverlayAlignmentV1']:
    D[key] = copy.deepcopy(v1[key])
# Recursive primitive references (font/resource) remain closed and copied exactly.
D['Color'] = {'type': 'string', 'pattern': '^#[0-9A-F]{8}$', 'minLength': 9, 'maxLength': 9}
D['Metric'] = obj({'size64': uint(64, 16384), 'weight': ref('UIFontWeightV1')})
D['Roles'] = obj({r: ref('Metric') for r in ROLES})
D['Profiles'] = obj({p: ref('Roles') for p in PROFILES})
D['Typography'] = obj({'font': ref('UIFontSourceV1'), 'profiles': ref('Profiles'),
    'defaultProfile': en(*PROFILES), 'preferencePolicy': exact('nearestBody64TiesUpRejectOutside')})
D['Outline'] = obj({'color': ref('Color'), 'width64': uint(), 'radius64': uint()})
D['ButtonPaint'] = obj({'label': ref('Color'), 'background': ref('Color')})
D['ButtonStates'] = obj({'enabled': ref('ButtonPaint'), 'pressed': ref('ButtonPaint'),
                         'disabled': ref('ButtonPaint'), 'focus': ref('Outline')})
D['FieldPaint'] = obj({k: ref('Color') for k in ['text', 'placeholder', 'background', 'caret', 'selection']}
                     | {'outline': ref('Outline')})
D['FieldStates'] = obj({s: ref('FieldPaint') for s in ['enabled', 'focused', 'disabled']})
D['TogglePaint'] = obj({k: ref('Color') for k in ['label', 'track', 'thumb', 'overlay']})
D['ToggleStates'] = obj({'enabled': ref('TogglePaint'), 'pressed': ref('TogglePaint'),
                         'disabled': ref('TogglePaint'), 'focus': ref('Outline')})
D['Paints'] = obj({'canvas': ref('Color'), 'surface': ref('Color'), 'separator': ref('Color'),
    'text': obj({r: ref('Color') for r in ROLES}),
    'button': obj({r: ref('ButtonStates') for r in ['normal', 'destructive', 'cancel']}),
    'field': ref('FieldStates'), 'toggle': obj({v: ref('ToggleStates') for v in ['on', 'off']})})
D['Stacks'] = obj({'defaultGap64': uint(), 'bodyCaptionGap64': uint(),
    'missingVStackGap': exact('bodyThenCaptionPairOtherwiseDefault'),
    'vStackAlignment': ref('UIHorizontalAlignmentV1'), 'hStackAlignment': ref('UIVerticalAlignmentV1'),
    'zStackAlignment': ref('UIOverlayAlignmentV1')})
D['GroupedList'] = obj({'outerHorizontal64': uint(), 'contentInsets64': ref('UIInsets64V1'),
    'topPadding64': uint(), 'bottomPadding64': uint(), 'headerToGroup64': uint(),
    'groupToNextHeader64': uint(), 'groupWithoutHeaderGap64': uint(),
    'profileFloors64': obj({p: uint(1) for p in PROFILES}),
    'separatorInset64': uint(), 'separatorThickness64': uint(),
    'outline': exact('fullGroupContinuousCubic2'), 'radius64': uint(),
    'rowPolicy': exact('maxProfileFloorSemanticContentPlusInsets'),
    'separatorPolicy': exact('interiorRowsOnly')})
D['ButtonMetrics'] = obj({'labelInsets64': ref('UIInsets64V1'), 'minimumHitWidth64': uint(1),
    'minimumHitHeight64': uint(1), 'overlayRadius64': uint()})
D['FieldMetrics'] = obj({'insets64': ref('UIInsets64V1'), 'minimumContentHeight64': uint(1),
    'minimumHitHeight64': uint(1)})
D['ToggleMetrics'] = obj({'track': exact('track63x28Continuous2'), 'thumb': exact('thumb37x24Continuous2'),
    'trackWidth64': exact(4032), 'trackHeight64': exact(1792),
    'thumbWidth64': exact(2368), 'thumbHeight64': exact(1536),
    'trackAuthoringRadius64': exact(896), 'thumbAuthoringRadius64': exact(768),
    'thumbInset64': exact(128), 'labelGap64': uint(), 'minimumHitWidth64': uint(1),
    'minimumHitHeight64': uint(1), 'checkedEnd': exact('logicalTrailing')})
D['Navigation'] = obj({'expandedRole': exact('navigationExpanded'), 'compactRole': exact('headline'),
    'expandedAlignment': exact('leading'), 'compactAlignment': exact('center'),
    'expandedInsets64': ref('UIInsets64V1'), 'compactInsets64': ref('UIInsets64V1'),
    'minimumExpandedBar64': uint(1), 'minimumCompactBar64': uint(1),
    'collapse': exact('snapAtExpandedOverflow'), 'titleWrap': exact('growExpandedEllipsizeCompactOneLine')})
D['Theme'] = obj({'recipe': exact('measuredShared2'), 'typography': ref('Typography'),
    'light': ref('Paints'), 'dark': ref('Paints'), 'stacks': ref('Stacks'),
    'groupedList': ref('GroupedList'), 'button': ref('ButtonMetrics'), 'field': ref('FieldMetrics'),
    'toggle': ref('ToggleMetrics'), 'navigation': ref('Navigation')})
shared = {'format': exact('mixer.native-appearance.2'), 'id': name(), 'mode': exact('shared'),
          'resources': array(ref('UIAppearanceResourceV1'), 0, 64), 'theme': ref('Theme')}
platform = {'format': exact('mixer.native-appearance.2'), 'id': name(), 'mode': exact('platformSpecific'),
          'resources': array(ref('UIAppearanceResourceV1'), 0, 64), 'iOS': ref('Theme'), 'android': ref('Theme'),
          'reason': {'type': 'string', 'minLength': 1, 'maxLength': 512, 'pattern': '^[ -~]+$'}}
D['Shared'] = obj(shared); D['PlatformSpecific'] = obj(platform)
schema = {'$schema': 'https://json-schema.org/draft/2020-12/schema',
    '$id': 'https://mixer.invalid/design/native-appearance-v2',
    'title': 'Design only: closed Mixer measured appearance 2', '$defs': D,
    'oneOf': [ref('Shared'), ref('PlatformSpecific')]}
def rgba(rgb): return rgb + 'FF'
def outline(c, width=128, radius=512): return {'color': c, 'width64': width, 'radius64': radius}
clear = '#00000000'
none_outline = outline(clear, 0, 0)
def paints(dark):
    primary, header, accent, destructive, disabled = ('#FFFFFFFF', '#8D8D93FF', '#0091FFFF', '#FF4245FF', '#555556FF') if dark else ('#000000FF','#85858BFF','#0088FFFF','#FF383CFF','#BFBFBFFF')
    placeholder = '#5A5A5EFF' if dark else '#B3B3B5FF'
    out = {'canvas': '#000000FF' if dark else '#F2F2F7FF',
           'surface': '#1C1C1EFF' if dark else '#FFFFFFFF',
           'separator': '#38383BFF' if dark else '#E8E8E8FF',
           'text': {r: header if r == 'sectionHeader' else primary for r in ROLES}, 'button': {}}
    for role in ['normal','destructive','cancel']:
        color = destructive if role == 'destructive' else accent
        out['button'][role] = {'enabled': {'label': color, 'background': clear},
            'pressed': {'label': color, 'background': color[:7] + '1F'},
            'disabled': {'label': disabled, 'background': clear}, 'focus': outline(color)}
    def field(disabled_state=False, focused=False):
        return {'text': disabled if disabled_state else primary, 'placeholder': disabled if disabled_state else placeholder,
            'background': clear, 'caret': clear if disabled_state else accent,
            'selection': clear if disabled_state else accent[:7] + '3D',
            'outline': outline(accent) if focused else copy.deepcopy(none_outline)}
    out['field'] = {'enabled': field(), 'focused': field(focused=True), 'disabled': field(disabled_state=True)}
    out['toggle'] = {}
    for state, track, disabled_track in [('on', '#30D158FF' if dark else '#34C759FF', '#26773BFF' if dark else '#99E3ACFF'),
                                         ('off', '#5A5A5EFF' if dark else '#C5C5C7FF', '#38383BFF' if dark else '#E5E5E7FF')]:
        base = {'label': primary, 'track': track, 'thumb': '#FFFFFFFF', 'overlay': clear}
        out['toggle'][state] = {'enabled': base, 'pressed': base | {'overlay': accent[:7] + '1F'},
            'disabled': {'label': disabled, 'track': disabled_track,
                         'thumb': '#8E8E8FFF' if dark else '#FFFFFFFF', 'overlay': clear}, 'focus': outline(accent,128,896)}
    return out
observed = json.loads((ROOT/'verification/apple-appearance-font-profile/type-profiles.json').read_text())
profiles = {}
for p in observed['profiles']:
    f = p['fonts']; source = {'body':'body','headline':'headline','title':'title','caption':'caption',
                             'sectionHeader':'sectionHeaderCandidate','navigationExpanded':'expandedNavigationCandidate'}
    profiles[p['normalizedProfileID']] = {r: {'size64': int(f[k]['size']*64),
        'weight': 700 if r == 'navigationExpanded' else 600 if r in ['headline','sectionHeader'] else 400} for r,k in source.items()}
zero = {'top':0,'leading':0,'bottom':0,'trailing':0}
theme = {'recipe': 'measuredShared2',
    'typography': {'font': {'kind':'systemSans'}, 'profiles': profiles, 'defaultProfile':'l',
                   'preferencePolicy':'nearestBody64TiesUpRejectOutside'},
    'light': paints(False), 'dark': paints(True),
    'stacks': {'defaultGap64':512,'bodyCaptionGap64':128,'missingVStackGap':'bodyThenCaptionPairOtherwiseDefault',
               'vStackAlignment':'center','hStackAlignment':'center','zStackAlignment':'center'},
    'groupedList': {'outerHorizontal64':1024,'contentInsets64':{'top':960,'leading':1024,'bottom':960,'trailing':1024},
        'topPadding64':640,'bottomPadding64':640,'headerToGroup64':640,'groupToNextHeader64':1771,
        'groupWithoutHeaderGap64':1771,'profileFloors64':dict(zip(PROFILES,[v*64 for v in [49,50,51,52,54,56,59,59,59,59,59,59]])),
        'separatorInset64':1024,'separatorThickness64':43,'outline':'fullGroupContinuousCubic2','radius64':1664,
        'rowPolicy':'maxProfileFloorSemanticContentPlusInsets','separatorPolicy':'interiorRowsOnly'},
    'button': {'labelInsets64':zero,'minimumHitWidth64':2816,'minimumHitHeight64':2816,'overlayRadius64':512},
    'field': {'insets64':zero,'minimumContentHeight64':1408,'minimumHitHeight64':2816},
    'toggle': {'track':'track63x28Continuous2','thumb':'thumb37x24Continuous2','trackWidth64':4032,'trackHeight64':1792,
        'thumbWidth64':2368,'thumbHeight64':1536,'trackAuthoringRadius64':896,'thumbAuthoringRadius64':768,
        'thumbInset64':128,'labelGap64':512,'minimumHitWidth64':4032,'minimumHitHeight64':2816,'checkedEnd':'logicalTrailing'},
    'navigation': {'expandedRole':'navigationExpanded','compactRole':'headline','expandedAlignment':'leading',
        'compactAlignment':'center','expandedInsets64':{'top':0,'leading':1024,'bottom':512,'trailing':1024},
        'compactInsets64':{'top':0,'leading':1024,'bottom':0,'trailing':1024},
        'minimumExpandedBar64':6784,'minimumCompactBar64':2816,'collapse':'snapAtExpandedOverflow',
        'titleWrap':'growExpandedEllipsizeCompactOneLine'}}
default = {'format':'mixer.native-appearance.2','id':'mixer.measured-candidate.v2','mode':'shared','resources':[],'theme':theme}
shape_source = json.loads((ROOT/'verification/apple-appearance-shape-measurement/proposed-shared-recipe.json').read_text())
fixed_paths = {}
for source_name, target in [('track-continuous-r14','track63x28Continuous2'),('thumb-continuous-r12','thumb37x24Continuous2')]:
    p = next(p for p in shape_source['canonicalPaths'] if p['name']==source_name)
    fixed_paths[target] = {'width64':int(p['width']*64),'height64':int(p['height']*64),
        'commands':[{'op':e['op'],'points64':[[int(v['x']*64+0.5),int(v['y']*64+0.5)] for v in e['points']]} for e in p['elements']]}
shapes = {'format':'mixer.authored-continuous-shapes.2','status':'design candidate; authored, not native-exact',
    'group': {'name':'fullGroupContinuousCubic2','coefficientDenominator':1000000,
        'coefficients':{'a':1528665,'b':1088490,'c':868407,'d':631494,'e':74911,'f':169060,'g':372824},
        'radiusClamp':'min(requested64,floor(min(width64,height64)*1000000/(2*a)))',
        'coordinateRounding':'nearestLogical64TiesUp'}, 'fixedPaths':fixed_paths,
    'nativeResiduals':{'groupFirstScanlineAt3xPixels':[9,10],'switchAt3xPixels':[1,2]}}
for filename, data, compact in [('descriptor-schema.json',schema,False),('mixer-measured-default-v2.json',default,True),('shape-definitions.json',shapes,False)]:
    (HERE/filename).write_text(json.dumps(data,sort_keys=True,separators=(',',':'))+'\n' if compact else json.dumps(data,sort_keys=True,indent=2)+'\n')
print('generated closed V2 schema, candidate default, authored shape definitions')
