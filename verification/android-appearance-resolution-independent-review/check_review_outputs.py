#!/usr/bin/env python3
"""Independent contract assertions on the actual returned Swift/Java values."""
import base64, hashlib, json, sys
from pathlib import Path
cases=[json.loads(x) for x in Path(sys.argv[1]).read_text().splitlines()]
tsv=[x.split('\t') for x in Path(sys.argv[2]).read_text().splitlines()]
values=[json.loads(x) for x in Path(sys.argv[2]+'.values.jsonl').read_text().splitlines()]
actual=[json.loads(x) for x in Path(sys.argv[3]).read_text().splitlines()]
assert len(cases)==len(tsv)==len(values)==len(actual)
assertions=0
def eq(a,b):
    global assertions
    assertions+=1
    assert a==b,(a,b)
def load(s):return json.loads(base64.b64decode(s))
def strings(v):
    if isinstance(v,dict):return {k:strings(x) for k,x in v.items()}
    if isinstance(v,list):return [strings(x) for x in v]
    return str(v) if isinstance(v,int) and not isinstance(v,bool) else v
def walk(v,disabled=False):
    disabled=disabled or v['properties'].get('disabled',False)
    yield v,disabled
    for c in v['children']:yield from walk(c,disabled)
def paint(color,opacity=1000):return {'color':color,'opacityPermille':str(opacity)}
def rounded(metric,scale):
    # quotient/remainder, a separate formulation of ties-up scale arithmetic.
    quotient,remainder=divmod(metric*scale,1024)
    return quotient+(remainder>=512)
outputs={}
for c,f,value,java in zip(cases,tsv,values,actual):
    eq(c['id'],f[0]);eq(c['expected'],f[1]);eq(java,None if c['boundary'] else value)
    if value is None:continue
    cfg=load(c['descriptor']);t=cfg['theme'] if cfg['mode']=='shared' else cfg[c['platform']]
    e=c['environment'];scale=e['textScale1024'];palette=t[e['scheme']];controls=t['controls'];layout=t['layout']
    eq(value['revision'],str(load(c['document'])['revision']));eq(value['configurationID'],cfg['id'])
    eq(value['platformSpecificReason'],cfg.get('reason'));eq(value['platform'],c['platform']);eq(value['recipe'],t['recipe'])
    eq(value['font'],strings(t['typography']['font']));eq(value['resources'],strings(cfg['resources']))
    eq(value['environment'],strings(e));eq(value['canvas'],paint(palette['canvas']))
    expected=list(walk(load(c['document'])['root']));eq(len(expected),len(value['nodes']))
    for (source,disabled),out in zip(expected,value['nodes']):
        kind=source['kind'];p=source['properties'];recipe=out['recipe'];id=source['id']
        eq(out['identity']['id'],id);eq(out['disabled'],disabled);eq(out['childIDs'],[x['id'] for x in source['children']])
        role=p.get('style','body') if kind=='text' else 'caption' if kind=='section' else 'title' if kind=='navigation' else 'body'
        metric=t['typography'][role]
        expectedText={'role':role,'size64':str(rounded(metric['size64'],scale)),'weight':str(metric['weight']),'minimumLineBox64':str(rounded(metric['minimumLineBox64'],scale)),
                      'selectable':p.get('selectable',False) if kind=='text' else False,'maximumLines':str(p['maxLines']) if kind=='text' and 'maxLines' in p else None}
        if kind in ['text','button','textField','toggle']:eq(recipe['text'],expectedText)
        if kind=='button':
            m=controls['button'];eq(recipe['metrics'],strings(m));eq(recipe['role'],p.get('role','normal'))
            eq(recipe['contentHeightFloor64'],str(max(m['minimumHeight64'],rounded(metric['minimumLineBox64'],scale)+m['labelInsets64']['top']+m['labelInsets64']['bottom'])))
        elif kind=='textField':
            m=controls['field'];eq(recipe['metrics'],strings(m))
            eq(recipe['contentHeightFloor64'],str(max(m['minimumHeight64'],rounded(metric['minimumLineBox64'],scale)+m['insets64']['top']+m['insets64']['bottom'])))
        elif kind=='toggle':
            m=controls['toggle'];eq(recipe['metrics'],strings(m));eq(recipe['checked'],p['value'])
            eq(recipe['contentHeightFloor64'],str(max(m['minimumRow64'],m['trackHeight64'],rounded(metric['minimumLineBox64'],scale))))
        elif kind in ['vStack','hStack']:
            eq(recipe['alignment'],p.get('alignment',layout[kind+'Alignment']))
            eq(recipe['spacing64'],str(int(__import__('math').floor(p['spacing']*64+0.5))) if 'spacing' in p else str(layout['stackGap64']))
        elif kind=='zStack':eq(recipe['alignment'],p.get('alignment',layout['zStackAlignment']))
        elif kind=='list':
            eq(recipe['metrics'],strings(layout['list']));eq(recipe['rowHeightFloor64'],str(max(layout['list']['minimumRow64'],rounded(t['typography']['body']['minimumLineBox64'],scale))))
        elif kind=='section':eq(recipe['header'],expectedText if 'title' in p else None);eq(recipe['headerInsets64'],strings(layout['sectionHeaderInsets64']))
        elif kind=='navigation':
            m=layout['navigation'];eq(recipe['title'],expectedText if 'title' in p else None);eq(recipe['metrics'],strings(m))
            eq(recipe['barHeightFloor64'],str(max(m['minimumBarHeight64'],rounded(metric['minimumLineBox64'],scale)+m['titleInsets64']['top']+m['titleInsets64']['bottom']) if 'title' in p else m['minimumBarHeight64']))
        for state,s in enumerate(out['styles']):
            active=kind in ['button','textField','toggle'] and not disabled
            pressed=active and bool(state&1);focused=active and bool(state&2)
            roleColor=palette['destructive' if kind=='button' and p.get('role')=='destructive' else 'accent']
            expectedStyle={'disabled':disabled,'pressed':pressed,'focused':focused,
                'foreground':paint(palette['disabledText'] if disabled else roleColor if kind=='button' else palette['primaryText']),
                'background':paint(palette['canvas'] if kind in ['list','navigation'] else '#00000000'),
                'rowBackground':paint(palette['surface']) if kind=='list' else None,'separator':paint(palette['separator']) if kind=='list' else None,
                'placeholder':paint(palette['disabledText' if disabled else 'secondaryText']) if kind=='textField' else None,
                'caret':paint(palette['accent']) if kind=='textField' and not disabled else None,
                'selection':paint(palette['accent'],controls['selectionOpacityPermille']) if kind=='textField' and not disabled else None,
                'border':paint(palette['separator']) if kind=='textField' else None,
                'toggleTrack':paint(palette['separator' if disabled else 'accent' if p['value'] else 'toggleOff']) if kind=='toggle' else None,
                'toggleThumb':paint(palette['toggleThumb']) if kind=='toggle' else None,'pressedOverlay':paint(roleColor,controls['pressedOpacityPermille']) if pressed else None,
                'focusOutline':{'paint':paint(palette['focus']),'width64':str(controls['focusWidth64']),'radius64':str(controls['focusRadius64'])} if focused else None}
            eq(s,expectedStyle)
    outputs[c['id']]=value
for seed in [0,1,2,11,23]:
    for scheme in ['light','dark']:
        for direction in ['leftToRight','rightToLeft']:
            ios=outputs[f'all-{seed}-{scheme}-{direction}-iOS'].copy();android=outputs[f'all-{seed}-{scheme}-{direction}-android'].copy()
            ios.pop('platform');android.pop('platform');eq(ios,android)
for density in [128,129,1023,1024,1025,16383,16384]:
    p=outputs['density-'+str(density)].copy();p.pop('environment');baseline=outputs['density-128'].copy();baseline.pop('environment');eq(p,baseline)
identity={x['identity']['id']:x['identity']['generation'] for x in outputs['identity-reordered-kind-replacement']['nodes']}
eq(identity,{'root':'1','replace':'5','insert':'6','survive':'2'})
eq(next(x for x in outputs['aggregate-4096']['nodes'] if x['kind']=='button')['recipe']['contentHeightFloor64'],'393216')
print(json.dumps({'cases':len(cases),'contract_assertions':assertions,'status':'passed'},sort_keys=True))
