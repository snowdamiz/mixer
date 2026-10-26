#!/usr/bin/env python3
"""Independently authored fixture from admitted decoder grammar; no producer fixture reads."""
from pathlib import Path
import json

HERE=Path(__file__).resolve().parent
def main():
    names=['xs','s','m','l','xl','xxl','xxxl','a1','a2','a3','a4','a5']
    family=[[14,25,11,31],[15,26,11,32],[16,27,11,33],[17,28,12,34],[19,30,14,36],[21,32,16,38],[23,34,18,40],[28,38,22,44],[33,43,26,48],[40,48,32,52],[47,53,37,56],[53,58,43,60]]
    roles=['body','headline','title','caption','sectionHeader','navigationExpanded']
    profiles={}
    for name,(body,title,caption,nav) in zip(names,family,strict=True):
        profiles[name]={r:dict(size64=s*64,weight=w) for r,s,w in zip(roles,[body,body,title,caption,body,nav],[400,600,400,400,600,700],strict=True)}
    clear='#00000000';ink='#112233FF';surface='#F6F4F2FF'
    outline=lambda width:dict(color=ink,width64=width,radius64=0)
    button=dict(enabled=dict(label=ink,background=surface),pressed=dict(label=ink,background='#CDDDEEAA'),disabled=dict(label=ink,background=clear),focus=outline(64))
    field=lambda width:dict(text=ink,placeholder='#445566FF',background=surface,caret=ink,selection='#778899AA',outline=outline(width))
    field_off=field(0);field_off.update(caret=clear,selection=clear)
    toggle=dict(enabled=dict(label=ink,track='#334455FF',thumb=surface,overlay=clear),pressed=dict(label=ink,track='#334455FF',thumb=surface,overlay='#11223322'),disabled=dict(label=ink,track='#778899FF',thumb=surface,overlay=clear),focus=outline(64))
    paints=dict(canvas=surface,surface=surface,separator=ink,text={r:ink for r in roles},button={r:button for r in ['normal','destructive','cancel']},field=dict(enabled=field(0),focused=field(64),disabled=field_off),toggle=dict(on=toggle,off=toggle))
    inset=lambda value:dict(top=value,leading=value,bottom=value,trailing=value)
    theme=dict(recipe='measuredShared2',typography=dict(font=dict(kind='systemSans'),profiles=profiles,defaultProfile='l',preferencePolicy='nearestBody64TiesUpRejectOutside'),light=paints,dark=paints,
        stacks=dict(defaultGap64=512,bodyCaptionGap64=256,missingVStackGap='bodyThenCaptionPairOtherwiseDefault',vStackAlignment='leading',hStackAlignment='center',zStackAlignment='center'),
        groupedList=dict(outerHorizontal64=0,contentInsets64=inset(0),topPadding64=0,bottomPadding64=0,headerToGroup64=0,groupToNextHeader64=0,groupWithoutHeaderGap64=0,profileFloors64={name:3072 for name in names},separatorInset64=0,separatorThickness64=64,outline='fullGroupContinuousCubic2',radius64=0,rowPolicy='maxProfileFloorSemanticContentPlusInsets',separatorPolicy='interiorRowsOnly'),
        button=dict(labelInsets64=inset(128),minimumHitWidth64=2816,minimumHitHeight64=2816,overlayRadius64=0),field=dict(insets64=inset(256),minimumContentHeight64=1536,minimumHitHeight64=2816),
        toggle=dict(track='track63x28Continuous2',thumb='thumb37x24Continuous2',trackWidth64=4032,trackHeight64=1792,thumbWidth64=2368,thumbHeight64=1536,trackAuthoringRadius64=896,thumbAuthoringRadius64=768,thumbInset64=128,labelGap64=384,minimumHitWidth64=4096,minimumHitHeight64=2816,checkedEnd='logicalTrailing'),
        navigation=dict(expandedRole='navigationExpanded',compactRole='headline',expandedAlignment='leading',compactAlignment='center',expandedInsets64=inset(256),compactInsets64=inset(128),minimumExpandedBar64=4096,minimumCompactBar64=2816,collapse='snapAtExpandedOverflow',titleWrap='growExpandedEllipsizeCompactOneLine'))
    descriptor=dict(format='mixer.native-appearance.2',id='independent.owner.review.1',mode='shared',resources=[],theme=theme)
    (HERE/'independent-descriptor.json').write_text(json.dumps(descriptor,sort_keys=True,separators=(',',':'))+'\n')
    for revision,value in [(1,'alpha'),(2,'beta')]:
        node=dict(id='field',kind='textField',properties=dict(label='Review',value=value),children=[],actions=[dict(id='change',event='textChange')])
        packet=dict(schemaVersion=1,document=dict(schemaVersion=1,revision=revision,root=node),identities=[dict(id='field',generation=1)])
        (HERE/f'independent-packet-{revision}.json').write_text(json.dumps(packet,sort_keys=True,separators=(',',':'))+'\n')
    def node(identifier,kind,properties=None,children=None):
        return dict(id=identifier,kind=kind,properties=properties or {},children=children or [],actions=[])
    field=node('field','textField',dict(label='Review',value='alpha'));field['actions']=[dict(id='change',event='textChange')]
    row=node('row','text',dict(text='Independent row'))
    root=node('container','vStack',children=[field,node('list','list',children=[row])])
    packet=dict(schemaVersion=1,document=dict(schemaVersion=1,revision=1,root=root),identities=[dict(id=name,generation=1) for name in ['container','field','list','row']])
    (HERE/'independent-helper-packet.json').write_text(json.dumps(packet,sort_keys=True,separators=(',',':'))+'\n')
    print('Independent descriptor and two packet literals authored; not a decoder pass until actual Java execution.')

if __name__=='__main__':main()
