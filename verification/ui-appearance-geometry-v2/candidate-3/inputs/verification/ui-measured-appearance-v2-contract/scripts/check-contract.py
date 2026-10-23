#!/usr/bin/env python3
"""Bounded DESIGN checker. This is not a product codec, renderer, or authority."""
import copy
import hashlib
import json
from pathlib import Path
import re
import sys
import unittest

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]
# Once frozen, replay against retained exact design inputs, never later product source.
if (HERE / "inputs/AGENTS.md").is_file(): ROOT = HERE / "inputs"
SCHEMA = json.loads((HERE/'descriptor-schema.json').read_text())
DEFAULT_BYTES = (HERE/'mixer-measured-default-v2.json').read_bytes()
SHAPES = json.loads((HERE/'shape-definitions.json').read_text())
PROFILES = ['xs','s','m','l','xl','xxl','xxxl','a1','a2','a3','a4','a5']
ROLES = ['body','headline','title','caption','sectionHeader','navigationExpanded']
KINDS = ['text','button','textField','toggle','vStack','hStack','zStack','list','section','navigation']
ROWS = [(14,25,11,31),(15,26,11,32),(16,27,11,33),(17,28,12,34),(19,30,14,36),(21,32,16,38),
        (23,34,18,40),(28,38,22,44),(33,43,26,48),(40,48,32,52),(47,53,37,56),(53,58,43,60)]
CLEAR = '#00000000'
class Rejected(ValueError): pass

def require(condition, reason):
    if not condition: raise Rejected(reason)

def canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')

def read(data):
    require(type(data) is bytes and 0 < len(data) <= 65536, 'byteLimit')
    require(all(v < 128 for v in data), 'encoding')
    # Bound nesting before json allocates a recursive tree. String escapes are
    # handled here only to count depth; json plus canonical equality admits bytes.
    depth = 0; quoted = False; escaped = False
    for byte in data:
        if quoted:
            if escaped: escaped = False
            elif byte == 92: escaped = True
            elif byte == 34: quoted = False
        elif byte == 34: quoted = True
        elif byte in (123,91):
            depth += 1; require(depth <= 20,'depthLimit')
        elif byte in (125,93):
            depth -= 1; require(depth >= 0,'syntax')
    def pairs(items):
        result = {}
        for key,value in items:
            require(key not in result,'duplicateKey'); result[key] = value
        return result
    def bad_number(value): raise Rejected('nonUnsignedInteger')
    try:
        value = json.loads(data,object_pairs_hook=pairs,parse_float=bad_number,parse_constant=bad_number)
    except (ValueError,RecursionError) as error: raise Rejected(str(error)) from error
    count = 0
    def bound(v):
        nonlocal count
        count += 1; require(count <= 8192,'valueLimit')
        require(type(v) in (dict,list,str,int),'valueType')
        if type(v) is dict:
            for x in v.values(): bound(x)
        elif type(v) is list:
            require(len(v) <= 64,'arrayLimit')
            for x in v: bound(x)
    bound(value)
    require(canonical(value) == data,'noncanonical')
    validate(value,SCHEMA)
    semantics(value)
    return value

def validate(value,schema,path='$'):
    if '$ref' in schema:
        return validate(value,SCHEMA['$defs'][schema['$ref'].split('/')[-1]],path)
    if 'oneOf' in schema:
        passes = 0
        for option in schema['oneOf']:
            try: validate(value,option,path); passes += 1
            except Rejected: pass
        require(passes == 1,path+':oneOf'); return
    if 'const' in schema: require(type(value) is type(schema['const']) and value == schema['const'],path+':const')
    if 'enum' in schema: require(value in schema['enum'] and type(value) is type(schema['enum'][0]),path+':enum')
    kind = schema.get('type')
    if kind == 'object':
        require(type(value) is dict,path+':object')
        require(set(value) == set(schema['required']),path+':closedFields')
        for key,child in value.items(): validate(child,schema['properties'][key],path+'.'+key)
    elif kind == 'array':
        require(type(value) is list and schema['minItems'] <= len(value) <= schema['maxItems'],path+':array')
        for index,child in enumerate(value): validate(child,schema['items'],path+f'[{index}]')
    elif kind == 'integer':
        require(type(value) is int and schema['minimum'] <= value <= schema['maximum'],path+':integer')
    elif kind == 'string':
        require(type(value) is str and schema['minLength'] <= len(value) <= schema['maxLength'],path+':string')
        require(re.fullmatch(schema['pattern'],value) is not None,path+':pattern')

def themes(value): return [value['theme']] if value['mode']=='shared' else [value['iOS'],value['android']]
def golden_profiles():
    result = {}
    for p,(body,title,caption,expanded) in zip(PROFILES,ROWS):
        sizes = [body,body,title,caption,body,expanded]
        result[p] = {r:{'size64':size*64,'weight':weight} for r,size,weight in zip(ROLES,sizes,[400,600,400,400,600,700])}
    return result

def semantics(value):
    if value['mode']=='platformSpecific': require(value['reason'].strip() != '' and value['reason']==value['reason'].strip(), 'emptyPlatformReason')
    resources = value['resources']
    require(len({r['id'] for r in resources}) == len(resources),'duplicateResourceID')
    require(len({r['path'].lower() for r in resources}) == len(resources),'duplicateResourcePath')
    require(sum(r['bytes'] for r in resources) <= 16*1024*1024,'resourceTotal')
    fonts=0
    for resource in resources:
        require(all(part not in ('.','..') for part in resource['path'].split('/')),'pathEscape')
        require(resource['provenance']==resource['provenance'].strip() and bool(resource['provenance'].strip()),'resourceProvenance')
        if resource['kind']=='fontSFNT':
            fonts += 1
            require(fonts<=16 and resource['scale']==1 and resource['locale']=='und' and resource['direction']=='neutral','fontResourceMetadata')
    by_id = {r['id']:r for r in resources}
    for theme in themes(value):
        require(theme['typography']['profiles']==golden_profiles(),'profileFamilyMismatch')
        font = theme['typography']['font']
        if font['kind']=='bundled':
            faces = font['faces']; keys = [(f['weight'],f['style']) for f in faces]
            require(len(set(keys))==len(keys),'duplicateFontFace')
            normals = {f['weight'] for f in faces if f['style']=='normal'}
            require({400,600,700} <= normals,'missingNormalWeight')
            require(all(f['weight'] in normals for f in faces),'italicWithoutNormal')
            for face in faces:
                require(face['resourceID'] in by_id and by_id[face['resourceID']]['kind']=='fontSFNT','missingFontResource')
        group = theme['groupedList']; toggle = theme['toggle']
        floors = [group['profileFloors64'][p] for p in PROFILES]
        require(floors==sorted(floors),'descendingRowFloors')
        require(all(f >= toggle['trackHeight64'] for f in floors),'trackDoesNotFitRowFloor')
        require(toggle['thumbWidth64']+2*toggle['thumbInset64'] <= toggle['trackWidth64'],'thumbWidth')
        require(toggle['thumbHeight64']+2*toggle['thumbInset64'] == toggle['trackHeight64'],'thumbHeight')
        require(theme['navigation']['minimumExpandedBar64']>=theme['navigation']['minimumCompactBar64'],'navigationFloors')
        for scheme in ['light','dark']:
            p = theme[scheme]
            for role in ['normal','destructive','cancel']:
                require(p['button'][role]['disabled']['background']==CLEAR,'disabledButtonOverlay')
            require(p['field']['disabled']['caret']==CLEAR and p['field']['disabled']['selection']==CLEAR,'disabledFieldSelection')
            require(p['field']['enabled']['outline']['width64']==0 and p['field']['disabled']['outline']['width64']==0,'inactiveFieldOutline')
            for state in ['on','off']:
                require(p['toggle'][state]['disabled']['overlay']==CLEAR,'disabledToggleOverlay')

def nearest(body64):
    require(type(body64) is int and 896 <= body64 <= 3392,'unsupportedBodySize')
    anchors=[r[0]*64 for r in ROWS]
    return PROFILES[min(range(12),key=lambda i:(abs(anchors[i]-body64),-i))]

def round_ratio(numerator,denominator):
    require(type(numerator) is int and type(denominator) is int and numerator>=0 and denominator>0,'badRational')
    require(denominator<=2**64-1 and numerator<=(2**64-1-denominator)//2,'integerOverflow')
    return (2*numerator+denominator)//(2*denominator)

def group_path(width64,height64,requested64):
    require(all(type(v) is int and 0<=v<=2**31-1 for v in [width64,height64]) and type(requested64) is int and 0<=requested64<=65536,'shapeBounds')
    if not width64 or not height64: return []
    c = SHAPES['group']['coefficients']; den=1000000
    r=min(requested64,min(width64,height64)*den//(2*c['a']))
    a,b,c0,d,e,f,g=[round_ratio(r*c[k],den) for k in ['a','b','c','d','e','f','g']]
    w=width64; h=height64
    def command(op,*points): return {'op':op,'points64':[list(p) for p in points]}
    return [command('move',(w,round_ratio(h,2))),command('line',(w,h-a)),
      command('cubic',(w,h-b),(w,h-c0),(w-e,h-d)),command('cubic',(w-f,h-g),(w-g,h-f),(w-d,h-e)),
      command('cubic',(w-c0,h),(w-b,h),(w-a,h)),command('line',(a,h)),
      command('cubic',(b,h),(c0,h),(d,h-e)),command('cubic',(g,h-f),(f,h-g),(e,h-d)),
      command('cubic',(0,h-c0),(0,h-b),(0,h-a)),command('line',(0,a)),
      command('cubic',(0,b),(0,c0),(e,d)),command('cubic',(f,g),(g,f),(d,e)),
      command('cubic',(c0,0),(b,0),(a,0)),command('line',(w-a,0)),
      command('cubic',(w-b,0),(w-c0,0),(w-d,e)),command('cubic',(w-g,f),(w-f,g),(w-e,d)),
      command('cubic',(w,c0),(w,b),(w,a)),command('close')]

def pixel_edge(metric64,density1024):
    require(type(metric64) is int and 0<=metric64<=2**31-1,'layoutOverflow')
    require(type(density1024) is int and 128<=density1024<=16384,'unsupportedDensity')
    product=metric64*density1024
    require(product<=2**64-1-32768,'integerOverflow')
    return (product+32768)//65536

def thumb_x(checked,rtl): return 1536 if checked != rtl else 128

def state_paint(theme,kind,scheme='light',disabled=False,pressed=False,focused=False,checked=False,role='normal'):
    require(kind in KINDS,'unsupportedKind')
    p=theme[scheme]
    if disabled: pressed=focused=False
    if kind=='button':
        states=p['button'][role]; state='disabled' if disabled else 'pressed' if pressed else 'enabled'
        return {'paint':states[state],'focus':states['focus'] if focused else None}
    if kind=='textField':
        return {'paint':p['field']['disabled' if disabled else 'focused' if focused else 'enabled'],'focus':None}
    if kind=='toggle':
        states=p['toggle']['on' if checked else 'off']; state='disabled' if disabled else 'pressed' if pressed else 'enabled'
        return {'paint':states[state],'focus':states['focus'] if focused else None}
    return {'paint':p['text']['sectionHeader' if kind=='section' else 'navigationExpanded' if kind=='navigation' else 'body'],'focus':None}

def role_for(kind,style='body',compact=False):
    require(kind in KINDS,'unsupportedKind')
    if kind=='text': require(style in ROLES[:4],'unsupportedDocumentStyle'); return style
    if kind=='section': return 'sectionHeader'
    if kind=='navigation': return 'headline' if compact else 'navigationExpanded'
    if kind in ['button','textField','toggle']: return 'body'
    return None

def row_height(theme,profile,semantic_content64):
    require(type(semantic_content64) is int and 0<=semantic_content64<=2**31-1,'layoutOverflow')
    group=theme['groupedList']; inset=group['contentInsets64']
    result=max(group['profileFloors64'][profile],semantic_content64+inset['top']+inset['bottom'])
    require(result<=2**31-1,'layoutOverflow'); return result

class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.value=read(DEFAULT_BYTES); cls.theme=cls.value['theme']
    def reject(self,value):
        with self.assertRaises(Rejected): read(canonical(value))
    def test_default_is_canonical_closed_v2(self):
        self.assertEqual(canonical(self.value),DEFAULT_BYTES)
        self.assertEqual(self.value['format'],'mixer.native-appearance.2')
        self.assertEqual(self.theme['typography']['profiles'],golden_profiles())
    def test_all_nested_objects_reject_unknown_and_missing_fields(self):
        paths=[]
        def walk(v,path):
            if type(v) is dict:
                paths.append(path)
                for key,child in v.items(): walk(child,path+[key])
            elif type(v) is list:
                for i,child in enumerate(v): walk(child,path+[i])
        walk(self.value,[])
        for path in paths:
            unknown=copy.deepcopy(self.value); missing=copy.deepcopy(self.value)
            u=unknown; m=missing
            for key in path: u=u[key]; m=m[key]
            u['unknown']=0; self.reject(unknown)
            if m: del m[next(iter(m))]; self.reject(missing)
    def test_bad_bytes_and_v1_cross_version_reject(self):
        for data in [b'',DEFAULT_BYTES+b' ',b'\xef\xbb\xbf'+DEFAULT_BYTES,DEFAULT_BYTES.replace(b'"format":',b'"format":"x","format":',1),
                     b'['*21+b']'*21,DEFAULT_BYTES.replace(b'1088',b'1088.0',1),
                     DEFAULT_BYTES.replace(b'1088',b'true',1),DEFAULT_BYTES.replace(b'1088',b'-1',1),
                     b' '*65537]:
            with self.assertRaises(Rejected): read(data)
        self.reject(json.loads((ROOT/'verification/ui-shared-appearance-contract/v2/mixer-default-appearance-v1.json').read_text()))
        v=copy.deepcopy(self.value); v['theme']['recipe']='sharedCandidate1'; self.reject(v)
    def test_every_body64_and_midpoint(self):
        anchors=[r[0]*64 for r in ROWS]
        last=-1
        for requested in range(896,3393):
            p=nearest(requested); index=PROFILES.index(p)
            self.assertGreaterEqual(index,last); last=index
            best=min(abs(a-requested) for a in anchors)
            self.assertEqual(abs(anchors[index]-requested),best)
            self.assertEqual(index,max(i for i,a in enumerate(anchors) if abs(a-requested)==best))
        for i in range(1,12): self.assertEqual(nearest((anchors[i-1]+anchors[i])//2),PROFILES[i])
        for x in [0,895,3393,2**32-1,True,17.0]:
            with self.assertRaises(Rejected): nearest(x)
    def test_source_profiles_match_all_six_golden_roles(self):
        measured=json.loads((ROOT/'verification/apple-appearance-font-profile/type-profiles.json').read_text())
        source={'body':'body','headline':'headline','title':'title','caption':'caption','sectionHeader':'sectionHeaderCandidate','navigationExpanded':'expandedNavigationCandidate'}
        for p in measured['profiles']:
            for role,key in source.items(): self.assertEqual(self.theme['typography']['profiles'][p['normalizedProfileID']][role]['size64'],p['fonts'][key]['size']*64)
    def test_every_kind_and_state_has_explicit_role_and_paint(self):
        for kind in KINDS:
            role=role_for(kind)
            if role: self.assertIn(role,ROLES)
            for scheme in ['light','dark']:
                for disabled in [False,True]:
                    for pressed in [False,True]:
                        for focused in [False,True]:
                            for checked in [False,True]:
                                result=state_paint(self.theme,kind,scheme,disabled,pressed,focused,checked)
                                self.assertIsNotNone(result['paint'])
                                if disabled: self.assertIsNone(result['focus'])
        for style in ROLES[:4]: self.assertEqual(role_for('text',style),style)
        for role in ['normal','destructive','cancel']:
            for scheme in ['light','dark']:
                for disabled in [False,True]:
                    for pressed in [False,True]:
                        result=state_paint(self.theme,'button',scheme,disabled,pressed,False,False,role)
                        state='disabled' if disabled else 'pressed' if pressed else 'enabled'
                        self.assertEqual(result['paint'],self.theme[scheme]['button'][role][state])
        self.assertEqual(role_for('navigation',compact=True),'headline')
        self.assertEqual(role_for('section'),'sectionHeader')
        with self.assertRaises(Rejected): role_for('unknown')
        with self.assertRaises(Rejected): role_for('text','sectionHeader')
    def test_component_disabled_is_not_global_dimming(self):
        for scheme in ['light','dark']:
            p=self.theme[scheme]
            self.assertEqual(state_paint(self.theme,'text',scheme,True)['paint'],p['text']['body'])
            self.assertNotEqual(p['button']['normal']['disabled']['label'],p['text']['body'])
        self.assertEqual(self.theme['dark']['toggle']['on']['disabled']['thumb'],'#8E8E8FFF')
        self.assertEqual(self.theme['light']['toggle']['on']['enabled']['track'],'#34C759FF')
    def test_closed_shapes_all_sizes_and_rtl(self):
        for width in [0,1,32,1024,3328,23680,2**20,2**31-1]:
            for height in [0,1,32,1024,3328,4075,13312,2**20,2**31-1]:
                commands=group_path(width,height,1664)
                if not width or not height: self.assertEqual(commands,[]); continue
                self.assertEqual(len(commands),18); self.assertEqual(commands[-1]['op'],'close')
                for command in commands:
                    self.assertEqual(len(command['points64']),{'move':1,'line':1,'cubic':3,'close':0}[command['op']])
                    for x,y in command['points64']:
                        self.assertTrue(0<=x<=width and 0<=y<=height)
                # Reflect all corner controls; the deliberately unpaired mid-side
                # move and straight tangent endpoints are excluded.
                points=[tuple(point) for command in commands if command['op']=='cubic' for point in command['points64']]
                for x,y in points:
                    self.assertIn((width-x,height-y),points)
                self.assertEqual(commands[2]['points64'][2][0],width-commands[10]['points64'][2][0])
        for values in [(-1,10,1664),(10,-1,1664),(2**31,10,1664),(10,2**31,1664),(10,10,65537)]:
            with self.assertRaises(Rejected): group_path(*values)
        for name,p in SHAPES['fixedPaths'].items():
            self.assertEqual(len(p['commands']),18)
            self.assertEqual(p['commands'][-1]['op'],'close')
            for command in p['commands']:
                for x,y in command['points64']: self.assertTrue(0<=x<=p['width64'] and 0<=y<=p['height64'])
        self.assertEqual([thumb_x(on,rtl) for rtl in [False,True] for on in [False,True]],[128,1536,1536,128])
    def test_exact_rounding_density_and_overflow(self):
        self.assertEqual(round_ratio(1,2),1)
        self.assertEqual(round_ratio(3,2),2)
        self.assertEqual(round_ratio(49,100),0)
        self.assertEqual(round_ratio(50,100),1)
        for density in [128,1024,1536,3072,16384]:
            for metric in [0,1,32,43,64,1664,65536,2**31-1]:
                expected=(metric*density*2+65536)//131072
                self.assertEqual(pixel_edge(metric,density),expected)
        self.assertEqual(pixel_edge(32,1024),1)
        self.assertEqual(pixel_edge(31,1024),0)
        for metric,density in [(-1,1024),(2**31,1024),(1,127),(1,16385),(1,True)]:
            with self.assertRaises(Rejected): pixel_edge(metric,density)
        with self.assertRaises(Rejected): round_ratio(2**64-1,1)
    def test_row_semantic_height_and_track_are_distinct(self):
        # Large 20 1/3 label -> 52 row, even with separate 28 high track.
        self.assertEqual(row_height(self.theme,'l',1301),3328)
        self.assertEqual(row_height(self.theme,'l',1408),3328)
        self.assertEqual(row_height(self.theme,'a1',1685),3776)
        self.assertGreater(row_height(self.theme,'a1',5000),5000)
        with self.assertRaises(Rejected): row_height(self.theme,'l',2**31-1)
    def test_custom_platform_declaration_and_font_catalog(self):
        v={'format':self.value['format'],'id':'example.shared2','mode':'platformSpecific','resources':[],
           'iOS':copy.deepcopy(self.theme),'android':copy.deepcopy(self.theme),'reason':'Explicit reviewed app design variant'}
        read(canonical(v)); v['reason']=' '; self.reject(v)
        v=copy.deepcopy(self.value); v['theme']['typography']['profiles']['a5']['body']['size64']=3391; self.reject(v)
        v=copy.deepcopy(self.value); v['theme']['toggle']['thumbWidth64']=1728; self.reject(v)
        v=copy.deepcopy(self.value); v['theme']['typography']['font']={'kind':'bundled','faces':[], 'fallback':'systemSans'}; self.reject(v)
    def test_resource_catalog_positive_and_negative(self):
        v=copy.deepcopy(self.value)
        v['resources']=[{'id':f'font{weight}','kind':'fontSFNT','path':f'fonts/f{weight}.ttf','sha256':'0'*64,
                         'bytes':1,'provenance':'Synthetic design validator only','scale':1,'locale':'und','direction':'neutral'} for weight in [400,600,700]]
        v['theme']['typography']['font']={'kind':'bundled','fallback':'none',
            'faces':[{'resourceID':f'font{w}','postScriptName':f'Design{w}','weight':w,'style':'normal'} for w in [400,600,700]]}
        read(canonical(v)) # References only: this deliberately proves no real font validity.
        wrong=copy.deepcopy(v); wrong['resources'][0]['kind']='iconPNG'; self.reject(wrong)
        wrong=copy.deepcopy(v); wrong['resources'][1]['id']='font400'; self.reject(wrong)
        wrong=copy.deepcopy(v); wrong['resources'][0]['path']='../font.ttf'; self.reject(wrong)
        wrong=copy.deepcopy(v); wrong['resources'][1]['path']='FONTS/F400.TTF'; self.reject(wrong)
        wrong=copy.deepcopy(v); wrong['resources'][0]['scale']=2; self.reject(wrong)
        wrong=copy.deepcopy(v); wrong['resources'][0]['locale']='en'; self.reject(wrong)
        wrong=copy.deepcopy(v); wrong['resources'][0]['direction']='rightToLeft'; self.reject(wrong)
        wrong=copy.deepcopy(v); wrong['resources'][0]['provenance']=' '; self.reject(wrong)
        wrong=copy.deepcopy(v); del wrong['theme']['typography']['font']['faces'][2]; self.reject(wrong)
    def test_native_unsupported_is_failure_not_substitution(self):
        required=set(KINDS)
        def admit(build_owned): require(required<=build_owned,'unsupportedRequiredKind')
        admit(set(KINDS))
        with self.assertRaises(Rejected): admit({'vStack','text','button'})

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(ContractTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({'scope':'design-only; no native or signed authority','testsRun':result.testsRun,
        'success':result.wasSuccessful(),'defaultBytes':len(DEFAULT_BYTES),'defaultSHA256':hashlib.sha256(DEFAULT_BYTES).hexdigest()},sort_keys=True))
    sys.exit(0 if result.wasSuccessful() else 1)
