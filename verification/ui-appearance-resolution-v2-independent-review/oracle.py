"""Independent contract oracle: document queries and declarative list partitions.

No product source is imported or transformed. Expected geometry/paint values come
from each authored descriptor; semantic rules come from the frozen contract.
"""
import copy, itertools, json, math, random

PROFILES = ['xs','s','m','l','xl','xxl','xxxl','a1','a2','a3','a4','a5']
CLEAR = '#00000000'
def canonical(value): return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n'
def node(id,kind,children=(),**properties):
    events={'button':'activate','textField':'textChange','toggle':'valueChange'}
    return dict(id=id,kind=kind,properties=properties,children=list(children),actions=[] if kind not in events else [dict(id=id+'Action',event=events[kind])])
def t(id,style='body'): return node(id,'text',text='Original العربية e\u0301 👩🏽‍🚀 '+id,style=style,selectable=True,maxLines=17)
def env(**kw):
    result=dict(scheme='light',direction='leftToRight',profile='l',density1024=1024,width64=25728,height64=55936,
        safeArea64=dict(top=11,leading=13,bottom=17,trailing=19),locale='ar-opaque-🚀',bold=False,contrast=False,motion=False,generation='0')
    result.update(kw);return result
def case(name,root,config,environment=None,platform='iOS',**kw):
    return dict(name=name,document=dict(schemaVersion=1,revision=9223372036854775999,root=root),configuration=canonical(config),
                environment=environment or env(),platform=platform,**kw)
def custom_theme(base,seed):
    rng=random.Random(seed);theme=copy.deepcopy(base)
    def colors(v):
        if isinstance(v,dict): return {k:colors(x) for k,x in v.items()}
        if isinstance(v,list): return [colors(x) for x in v]
        if isinstance(v,str) and v.startswith('#'): return '#'+''.join(f'{rng.randrange(256):02X}' for _ in range(4))
        return v
    for scheme in ['light','dark']:
        theme[scheme]=colors(theme[scheme]);p=theme[scheme]
        for states in p['button'].values(): states['disabled']['background']=CLEAR
        p['field']['disabled']['caret']=p['field']['disabled']['selection']=CLEAR
        for states in p['toggle'].values(): states['disabled']['overlay']=CLEAR
    theme['typography']['defaultProfile']=rng.choice(PROFILES)
    s=theme['stacks'];s['defaultGap64']=rng.randrange(1,900);s['bodyCaptionGap64']=rng.randrange(0,99)
    s['vStackAlignment']=rng.choice(['leading','center','trailing']);s['hStackAlignment']=rng.choice(['top','bottom','firstTextBaseline','lastTextBaseline'])
    s['zStackAlignment']=rng.choice(['topLeading','topTrailing','bottomLeading','bottomTrailing'])
    g=theme['groupedList']
    for k in ['topPadding64','bottomPadding64','headerToGroup64','groupToNextHeader64','groupWithoutHeaderGap64','outerHorizontal64','separatorInset64','separatorThickness64','radius64']:g[k]=rng.randrange(1,1600)
    g['profileFloors64']=dict(zip(PROFILES,sorted(rng.randrange(1792,6500) for _ in PROFILES)))
    for category in ['button','field']:
        for k,v in theme[category].items():
            theme[category][k]={side:rng.randrange(500) for side in v} if isinstance(v,dict) else rng.randrange(100,5000)
    theme['toggle']['labelGap64']=rng.randrange(1,2000)
    theme['navigation']['minimumCompactBar64']=rng.randrange(400,2000)
    theme['navigation']['minimumExpandedBar64']=rng.randrange(2000,5000)
    for k in ['expandedInsets64','compactInsets64']:theme['navigation'][k]={side:rng.randrange(500) for side in theme['navigation'][k]}
    return theme
def combined_tree(seed):
    rng=random.Random(seed)
    # The semantic Section is separated from the immediate List Section by both
    # a row stack and another Section. No additional group is permitted there.
    semantic=node('semantic','section',[t('semBody'),t('semCaption','caption')],title='Semantic original case')
    row=node('row','vStack',[
        t('body'),t('caption','caption'),t('headline','headline'),t('title','title'),
        node('button','button',label='Press',role=rng.choice(['normal','destructive','cancel'])),
        node('field','textField',label='Placeholder',value='Input العربية'),
        node('on','toggle',label='On',value=True),node('off','toggle',label='Off',value=False),
        node('h','hStack',[t('hBody'),t('hCaption','caption')],spacing=1.0078125,alignment='lastTextBaseline'),
        node('z','zStack',[t('zTop'),semantic],alignment='bottomTrailing')],disabled=bool(seed%3==0))
    entries=[node('invisible0','section',title=''),t('directA'),t('directB','caption'),
        node('headed','section',[row,t('lastRow')],title='Header original case'),
        node('invisible1','section'),node('headerOnly','section',title='Only header'),
        node('unheaded','section',[node('disabledAncestor','vStack',[node('cannotEnable','button',label='No',disabled=False)],disabled=True)]),
        node('lastDirect','hStack',[t('nestedA'),t('nestedB','caption')],spacing=0)]
    if seed%2:entries=entries[3:]+entries[:3]
    primary=node('listA','list',entries,disabled=seed%5==0)
    secondary=node('listB','list',[node('invisibleB','section'),node('visibleB','section',title='Sibling')])
    outside=node('outside','section',[t('outsideBody'),t('outsideCaption','caption')],title='Outside')
    return node('nav','navigation',[node('content','vStack',[outside,primary,secondary],spacing=0 if seed%2 else 0.0078125)],title='Navigation')

def build_cases(default):
    cases=[]
    for index,(profile,scheme,direction,platform) in enumerate(itertools.product(PROFILES,['light','dark'],['leftToRight','rightToLeft'],['iOS','android'])):
        a,b=custom_theme(default['theme'],index*2+901),custom_theme(default['theme'],index*2+902)
        c=dict(format=default['format'],id='independent.custom.'+str(index),mode='platformSpecific',iOS=a,android=b,reason='Explicit reviewed data distinction',resources=[])
        e=env(profile=profile,scheme=scheme,direction=direction,density1024=[128,1024,16384][index%3],generation=['0','18446744073709551615'][index%2],motion=bool(index%2))
        cases.append(case('combined-'+str(index),combined_tree(index),c,e,platform))
    # Empty context combinations are checked in addition to the combined tree.
    for index,children in enumerate([[],[node('empty','section')],[node('empty','section',title='')],
        [node('empty','section'),node('header','section',title='Header')],
        [node('header','section',title='Header'),node('empty','section')]]):
        cases.append(case('empty-'+str(index),node('list','list',children),default))
    for title in [None,'']:
        cases.append(case('missing-title-'+str(title),node('nav','navigation',[t('child')],**({} if title is None else dict(title=title))),default))
    # Inclusive raw bounds, opaque locales, and UTF8 byte boundaries.
    for index,e in enumerate([env(width64=2147483647,height64=2147483647,density1024=128),
        env(width64=1,height64=1,density1024=16384,safeArea64=dict(top=1,leading=1,bottom=0,trailing=0),locale='é'*64),
        env(locale='\u2028opaque\u2029')]):cases.append(case('inclusive-env-'+str(index),t('t'),default,e))
    invalid=[]
    for density in [0,127,16385,65535]:invalid.append(('density-'+str(density),env(density1024=density),'MixerUI.UIAppearanceGeometryErrorV2.density'))
    for width,height in [(0,1),(1,0),(2147483648,1),(4294967295,4294967295)]:invalid.append(('viewport-'+str(width)+'-'+str(height),env(width64=width,height64=height),'MixerUI.UIAppearanceErrorV2.geometry'))
    invalid.append(('safe-sum-overflow',env(safeArea64=dict(top=4294967295,bottom=4294967295,leading=0,trailing=0)),'MixerUI.UIAppearanceErrorV2.geometry'))
    invalid.append(('safe-one-over',env(safeArea64=dict(top=55936,bottom=1,leading=0,trailing=0)),'MixerUI.UIAppearanceErrorV2.geometry'))
    for value in ['', 'é'*65, 'en\x7fUS', 'en\u0085US', 'en\x00US']:
        invalid.append(('locale-'+str(len(invalid)),env(locale=value),'MixerUI.UIAppearanceErrorV2.shape'))
    for kw in [dict(bold=True),dict(contrast=True),dict(bold=True,contrast=True,motion=True)]:invalid.append(('accessibility-'+str(len(invalid)),env(**kw),'MixerUI.UIAppearanceErrorV2.unsupportedNativeOperation'))
    for name,e,error in invalid:cases.append(case(name,t('t'),default,e,expectedError=error))
    forbidden=[node('outer','list',[node('wrap','zStack',[node('semantic','section',[node('nested','list')])])]),
        node('outer','list',[node('section','section',[node('nested','list')])]),
        node('outer','section',[node('nav','navigation',[t('t')])]),
        node('nav','navigation',[node('list','list',[node('section','section',[node('innerNav','navigation',[t('t')])])])])]
    for index,root in enumerate(forbidden):cases.append(case('unsupported-context-'+str(index),root,default,expectedError='MixerUI.UIAppearanceErrorV2.unsupportedNativeOperation'))
    # Exact 4096 nodes with 4090 derived rows. This independently stresses the
    # frontier, metadata fanout and last-row separators on sibling Lists.
    lists=[node('list'+str(i),'list',[t('r'+str(i)+'-'+str(j)) for j in range(1000 if i<4 else 90)]) for i in range(5)]
    cases.append(case('node-boundary-4096',node('root','vStack',lists),default))
    oversized=node('root','vStack',lists+[t('extra')])
    cases.append(case('node-boundary-4097',oversized,default,wideLimits=True,expectedError='MixerUI.UIValidationError.limitExceeded("nodes")'))
    # Wide-limit snapshot must be narrowed to standard message/string/child/depth.
    cases.append(case('wide-child-count',node('root','vStack',[t('t'+str(i)) for i in range(1001)]),default,wideLimits=True,expectedError='MixerUI.UIValidationError.limitExceeded("children")'))
    deep=t('deepLeaf')
    for i in range(64):deep=node('depth'+str(i),'vStack',[deep])
    cases.append(case('wide-depth',deep,default,wideLimits=True,expectedError='MixerUI.UIValidationError.limitExceeded("depth")'))
    cases.append(case('wide-string',node('t','text',text='x'*16385),default,wideLimits=True,expectedError='MixerUI.UIValidationError.limitExceeded("stringBytes")'))
    return cases

def expected(case):
    if 'expectedError' in case:return dict(name=case['name'],error=case['expectedError'])
    cfg=json.loads(case['configuration']);e=case['environment'];theme=cfg.get('theme') or cfg[case['platform']];p=theme[e['scheme']]
    preorder=[];ancestors={}
    def flatten(n,path):
        preorder.append(n);ancestors[n['id']]=path
        for child in n['children']:flatten(child,path+[n])
    flatten(case['document']['root'],[])
    ids={n['id']:dict(id=n['id'],generation=str(i+1)) for i,n in enumerate(preorder)}
    def txt(value,role,selectable=False,maximumLines=None):
        return dict(value=value,role=role,selectable=selectable,maximumLines=maximumLines,**theme['typography']['profiles'][e['profile']][role])
    def header(n):return txt(n['properties']['title'],'sectionHeader') if n['properties'].get('title') else None
    group_lists={};section_owners={};row_owners={}
    for owner in [n for n in preorder if n['kind']=='list']:
        # Partition by immediate Sections; run boundaries use groupby, rather
        # than the resolver's append/flush procedure. Hidden groups are retained.
        partitions=[]
        for is_section,sequence in itertools.groupby(owner['children'],key=lambda n:n['kind']=='section'):
            sequence=list(sequence)
            partitions.extend([(s,s['children']) for s in sequence] if is_section else [(None,sequence)])
        groups=[]
        for i,(section,rows) in enumerate(partitions):
            h=header(section) if section else None;visible=h is not None or bool(rows)
            earlier_visible=any(g['visible'] for g in groups)
            gap=0 if not visible else theme['groupedList']['topPadding64' if not earlier_visible else ('groupToNextHeader64' if h else 'groupWithoutHeaderGap64')]
            source={'section':ids[section['id']]} if section else {'directRun':ids[rows[0]['id']]}
            groups.append(dict(source=source,header=h,rows=[ids[r['id']] for r in rows],visible=visible,drawsOutline=bool(rows),leadingGap64=gap,
                headerToRowsGap64=theme['groupedList']['headerToGroup64'] if h and rows else 0))
            if section:section_owners[section['id']]=dict(kind='listGroup',list=ids[owner['id']],groupIndex=i)
            for ri,r in enumerate(rows):row_owners[r['id']]=dict(list=ids[owner['id']],groupIndex=i,rowIndex=ri,separatorAfter=ri<len(rows)-1)
        group_lists[owner['id']]=groups
    def output(n):
        q=n['properties'];k=n['kind'];children=n['children'];id=n['id']
        disabled=any(x['properties'].get('disabled',False) for x in ancestors[id]+[n])
        h=header(n) if k=='section' else None
        if k=='text':r=dict(text=txt(q['text'],q.get('style','body'),q.get('selectable',False),q.get('maxLines')))
        elif k=='button':r=dict(role=q.get('role','normal'),text=txt(q['label'],'body'),metrics=theme['button'])
        elif k=='textField':r=dict(label=q['label'],value=q['value'],text=txt(q['value'],'body'),metrics=theme['field'])
        elif k=='toggle':r=dict(text=txt(q['label'],'body'),checked=q['value'],metrics=theme['toggle'])
        elif k in ['vStack','hStack']:
            gaps=[]
            for a,b in zip(children,children[1:]):
                pair=k=='vStack' and a['kind']==b['kind']=='text' and a['properties'].get('style','body')=='body' and b['properties'].get('style')=='caption'
                gaps.append(math.floor(q['spacing']*64+0.5) if 'spacing' in q else theme['stacks']['bodyCaptionGap64' if pair else 'defaultGap64'])
            r=dict(gaps64=gaps,alignment=q.get('alignment',theme['stacks'][k+'Alignment']))
        elif k=='zStack':r=dict(alignment=q.get('alignment',theme['stacks']['zStackAlignment']))
        elif k=='list':
            groups=group_lists[id];r=dict(groups=groups,metrics=theme['groupedList'],rowHeightFloor64=theme['groupedList']['profileFloors64'][e['profile']],trailingPadding64=theme['groupedList']['bottomPadding64'] if any(g['visible'] for g in groups) else 0)
        elif k=='section':
            list_ancestors=[x for x in ancestors[id] if x['kind']=='list']
            context=section_owners.get(id) or (dict(kind='withinListRow',list=ids[list_ancestors[-1]['id']]) if list_ancestors else dict(kind='outsideList'))
            structural=context['kind']=='listGroup'
            r=dict(header=h,context=context,headerToContentGap64=theme['groupedList']['headerToGroup64'] if not structural and h and children else 0,
                contentGaps64=[] if structural else [theme['stacks']['defaultGap64']]*(max(0,len(children)-1)),alignment='leading')
        elif k=='navigation':r=dict(expandedTitle=txt(q['title'],'navigationExpanded') if q.get('title') else None,compactTitle=txt(q['title'],'headline',maximumLines=1) if q.get('title') else None,metrics=theme['navigation'])
        styles=[]
        for press,focus in itertools.product([False,True],repeat=2):
            pressed=press and not disabled and k in ['button','toggle'];focused=focus and not disabled and k in ['button','toggle','textField']
            state='disabled' if disabled else ('pressed' if pressed else 'enabled')
            if k=='text':paints=dict(foreground=p['text'][q.get('style','body')],background=CLEAR)
            elif k=='button':
                states=p['button'][q.get('role','normal')];paints=dict(paint=states[state],focus=states['focus'] if focused else None)
            elif k=='textField':paints=dict(paint=p['field']['disabled' if disabled else ('focused' if focused else 'enabled')])
            elif k=='toggle':
                states=p['toggle']['on' if q['value'] else 'off'];paints=dict(paint=states[state],focus=states['focus'] if focused else None)
            elif k=='list':paints={key:p[key] for key in ['canvas','surface','separator']}
            elif k=='section':paints=dict(header=p['text']['sectionHeader'] if h else None,background=CLEAR)
            elif k=='navigation':paints=dict(expanded=p['text']['navigationExpanded'] if q.get('title') else None,compact=p['text']['headline'] if q.get('title') else None,background=p['canvas'])
            else:paints=dict(background=CLEAR)
            styles.append(dict(disabled=disabled,pressed=pressed,focused=focused,paints=paints))
        return dict(identity=ids[id],kind=k,children=[x['id'] for x in children],disabled=disabled,row=row_owners.get(id),recipe=r,styles=styles,snapshotIdentityMatches=True)
    environment=dict(scheme=e['scheme'],direction=e['direction'],profile=e['profile'],density1024=e['density1024'],viewport=dict(width64=e['width64'],height64=e['height64']),
        safeArea64=e['safeArea64'],localeIdentifier=e['locale'],accessibility=dict(boldText=e['bold'],increasedContrast=e['contrast'],reduceMotion=e['motion']),generation=e['generation'])
    return dict(name=case['name'],nodes=[output(n) for n in preorder],canvas=p['canvas'],revision=str(case['document']['revision']),configurationID=cfg['id'],platform=case['platform'],
        reason=cfg.get('reason'),environment=environment,stylesPreserveNodes=True,missingReturnsNil=True,resourceCount=len(cfg['resources']))

def mismatch(a,b,path='$'):
    if type(a)!=type(b):return f'{path}: types {type(a).__name__} != {type(b).__name__}: {str(a)[:150]} / {str(b)[:150]}'
    if isinstance(a,dict):
        if a.keys()!=b.keys():return f'{path}: keys {sorted(a)} != {sorted(b)}'
        for k in a:
            problem=mismatch(a[k],b[k],path+'.'+k)
            if problem:return problem
    elif isinstance(a,list):
        if len(a)!=len(b):return f'{path}: length {len(a)} != {len(b)}'
        for i,(x,y) in enumerate(zip(a,b)):
            problem=mismatch(x,y,path+f'[{i}]')
            if problem:return problem
    elif a!=b:return f'{path}: {a!r} != {b!r}'
    return None
