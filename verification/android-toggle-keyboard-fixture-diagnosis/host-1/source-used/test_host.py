"""Host-only finite source, native-export schema, counter and focus-evidence controls."""
import copy,json
import support,stage_sources,oracle_adapter

def test():
    checks=0;rejections=[]
    def need(value,label):
        nonlocal checks
        checks+=1
        if not value:raise AssertionError(label)
    def reject(label,action,contains=None):
        nonlocal checks
        try:action()
        except (AssertionError,ValueError,TypeError,KeyError) as error:
            if contains is not None:need(contains in str(error),label+' failure identity')
            checks+=1;rejections.append(label);return
        raise AssertionError(label+' unexpectedly accepted')
    adaptation=support.read(support.HERE/'source-adaptation.json')
    for name,binding in adaptation['files'].items():
        text,changes=stage_sources.transformed(name)
        need((support.HERE/name).read_text()==text and support.sha(support.HERE/name)==binding['candidateSHA256'] and support.sha(support.SCROLL/name)==binding['upstreamSHA256'] and changes==binding['changes'],'finite source '+name)
    instrument=(support.HERE/'fixture/AuthoredToggleSupplementInstrumentation.java').read_text();original=(support.SCROLL/'fixture/AuthoredToggleSupplementInstrumentation.java').read_text()
    begin='            for(boolean direction:new boolean[]{false,true})for(boolean initial:';end='        }catch(Throwable caught){failure=caught;}'
    need(instrument[instrument.index(begin):instrument.index(end,instrument.index(begin))]==original[original.index(begin):original.index(end,original.index(begin))],'all original45 case bodies exact')
    begin='    private void dispatchScroll(boolean diagonal)';end='    @Override public void onStart()'
    need(instrument[instrument.index(begin):instrument.index(end)]==original[original.index(begin):original.index(end)],'all original scroll setup and nine event actions coordinates times exact')
    need(instrument.count('toggle.requestFocus()')==1 and 'require(admitted,"native focus admitted")' in instrument,'one original focus predicate call')
    need(instrument.count('keyboardRequire(')==6,'five setup assertions plus one helper declaration')
    need(instrument.count('sendKeySync(')==1 and 'for(int action=0;action<=1;action++)' in instrument,'one finite navigation pair loop')
    added=(support.HERE/'keyboard-activity.fragment').read_text()+(support.HERE/'keyboard-instrumentation.fragment').read_text()
    need(all(token not in added for token in ('setFocusable(','setFocusableInTouchMode(','setInTouchMode(','setDescendantFocusability(','setAccessible(','getDeclaredField(','UiAutomation.injectInputEvent','adoptShellPermissionIdentity','SystemClock.sleep(')),'no altered product focus flags internal privilege bypass reflection or arbitrary sleep')
    focus=instrument[instrument.index('    private void focus(){'):instrument.index('    private void cancelCase')]
    need(focus.index('keyboardObserve("keyboard.control.install.before"')<focus.index('new Button(window)') and focus.index('parent.removeView(control)')<focus.index('boolean admitted=toggle.requestFocus()'),'capture original state before control install and remove control before original focus')
    need(focus.index('keyboardObserve("keyboard.toggle.focus.after"')<focus.index('require(admitted,"native focus admitted")') and 'finally{' in focus and 'FixtureFailures.attempt(failure' in focus,'focus observation before failure and preserving cleanup')
    for token in ('requestFocus()','KEYCODE_DPAD_DOWN','SOURCE_KEYBOARD','window.deliveredKeyboardPair(traceStart,cases)','keyboardObserve("keyboard.toggle.focus.after"','keyboardRequire(control.getParent()==null'):
        name='fixture/AuthoredToggleSupplementInstrumentation.java'
        mutated=instrument.replace(token,token+'/* unauthorized mutation */',1)
        need(mutated!=stage_sources.transformed(name)[0],'reject changed source '+token)
    for kind,name in [('reset-counter','reset_counter_oracle.py'),('keyboard','keyboard_oracle.py')]:need((support.HERE/name).read_text()==oracle_adapter.derive(kind),'finite oracle derivation '+kind)
    reject('original oracle source mutation',lambda:oracle_adapter.derive('keyboard',oracle_adapter.ORIGINAL.read_text()+'\n'))
    reset=support.load('keyboard_host_reset_oracle',support.HERE/'reset_counter_oracle.py');oracle=support.load('keyboard_host_focus_oracle',support.HERE/'keyboard_oracle.py')
    failed=support.read(support.SCROLL/'runtime/runtime-1/toggle-supplement-results.json');metadata={key:failed[key] for key in ('apkSHA256','sourceClosureSHA256')}
    reject('actual failed retained reset export remains native failure after finite schema repair',lambda:reset.validate(failed,support.HERE,metadata),'component native fixture failed')
    value=synthetic(oracle,failed);result=oracle.validate(value,support.HERE,metadata)
    need(result['cases']==45 and result['authoritativeCommits'] is None and result['addedSetupAssertions']==26,'host fabricated full candidate accepted only as component export control')
    resetSynthetic={k:v for k,v in value.items() if k in reset.RESET_FIELDS};resetSynthetic['assertions']=306;resetSynthetic['addedSetupAssertions']=6
    need(reset.validate(resetSynthetic,support.HERE,metadata)['originalAssertionCounter']==300,'host fabricated reset export control')
    def mutated(label,mutation):
        candidate=copy.deepcopy(value);mutation(candidate);reject(label,lambda:oracle.validate(candidate,support.HERE,metadata))
    for key in ('assertions','addedSetupAssertions','originalAssertionCounter','addedScrollSetupAssertions','addedKeyboardSetupAssertions','keyboardSetupEvents'):
        for invalid in (True,-1,0.5,float('nan'),9999999):mutated('invalid counter '+key+' '+str(invalid),lambda v,k=key,x=invalid:v.__setitem__(k,x))
    mutated('unknown top field',lambda v:v.__setitem__('unauthorized',True))
    mutated('counter total mismatch',lambda v:v.__setitem__('assertions',v['assertions']+1))
    mutated('setup subtotal mismatch',lambda v:v.__setitem__('addedScrollSetupAssertions',5))
    mutated('partial matrix must fail',lambda v:v['cases'].pop())
    mutated('native failed status must fail',lambda v:v.update(status='failed-retained',failure='native focus admitted'))
    mutated('original assertion minimum not inflated by setup',lambda v:v.update(originalAssertionCounter=89,assertions=115))
    mutated('missing setup pair',lambda v:v['keyboardSetup']['requests'].pop())
    mutated('missing actual key delivery',lambda v:v['keyboardSetup']['nativeKeyTrace'].pop())
    mutated('direct key route not window delivery',lambda v:v['keyboardSetup']['nativeKeyTrace'][0].update(stage='toggle.dispatchKeyEvent'))
    mutated('activation key not navigation',lambda v:v['keyboardSetup']['requests'][0].update(keyCode=23))
    mutated('actual source mismatch',lambda v:v['keyboardSetup']['nativeKeyTrace'][0].update(source=0))
    mutated('actual key repeat not setup',lambda v:v['keyboardSetup']['nativeKeyTrace'][0].update(repeat=1))
    mutated('key time mismatch',lambda v:v['keyboardSetup']['nativeKeyTrace'][0].update(eventTime=999))
    mutated('trace drop',lambda v:v['keyboardSetup'].update(dropped=1))
    mutated('observer failure',lambda v:v['keyboardSetup'].update(observerFailures=1))
    mutated('missing focus observation',lambda v:v['keyboardSetup']['observations'].pop())
    mutated('wrong focus stage',lambda v:v['keyboardSetup']['observations'][2].update(stage='skip'))
    mutated('touch mode persists',lambda v:v['keyboardSetup']['observations'][2]['state']['toggle'].update(inTouchMode=True))
    mutated('native Button positive control failed',lambda v:v['keyboardSetup']['observations'][3].update(requestReturned=False))
    mutated('native toggle original request failed',lambda v:v['keyboardSetup']['observations'][5].update(requestReturned=False))
    mutated('control remained attached',lambda v:v['keyboardSetup']['observations'][4]['state']['control'].update(attached=True))
    mutated('toggle lost focus',lambda v:v['keyboardSetup']['observations'][6]['state'].update(toggleIsFocusOwner=False))
    mutated('native owner identity wrong',lambda v:v['keyboardSetup']['observations'][6]['state']['decorFocusOwner'].update(identity=999))
    mutated('ancestor blocks focus',lambda v:v['keyboardSetup']['observations'][2]['state']['ancestors'][0].update(descendantFocusability=393216))
    mutated('incomplete ancestors',lambda v:v['keyboardSetup']['observations'][2]['state'].update(ancestorChainComplete=False))
    mutated('view focusability changed',lambda v:v['keyboardSetup']['observations'][2]['state']['toggle'].update(focusableInTouchMode=True))
    mutated('control not ordinary Button',lambda v:v['keyboardSetup']['observations'][3]['state']['control'].update(**{'class':'fixture.FocusOverrideButton'}))
    mutated('toggle outside owned input area',lambda v:v['keyboardSetup']['observations'][2]['state'].update(toggleOwnedVisible=False))
    mutated('setup activated toggle',lambda v:v['keyboardSetup']['observations'][2].update(proposals=1))
    mutated('setup altered geometry',lambda v:v['keyboardSetup']['observations'][4]['state']['toggle']['frame'].__setitem__(1,999))
    partial=copy.deepcopy(value);partial.update(status='failed-retained',failure='java.lang.AssertionError: native focus admitted',addedKeyboardSetupAssertions=4,addedSetupAssertions=10,originalAssertionCounter=183,assertions=193,keyboardSetupEvents=2)
    reject('valid finite partial counters still preserve native failure',lambda:oracle.validate(partial,support.HERE,metadata),'component native fixture failed')
    import run
    _,source,_=run.load_runner();_,prior,_=support.repair_runner();marker='    except BaseException as failure:\n'
    need(source[source.index(marker):]==prior[prior.index(marker):],'unchanged inherited failure and owned cleanup tail')
    need(run.load_runner()[0]._authored_component_collect.__code__.co_filename==str(support.HERE/'keyboard_oracle.py'),'new exact collector selected')
    return {'schema':1,'status':'passed-host-only-finite-keyboard-fixture-and-export-controls','checks':checks,'rejectedControls':rejections,'nativeCommandsExecuted':0,'full45CaseSuiteAccepted':False,'fabricatedPositiveControlsOnly':True,'actualFailedExportRemainsFailed':True,'originalCaseBodiesAndScrollProtocolUnchanged':True}

def synthetic(oracle,failed):
    """Fabricated host oracle control. Never native runtime evidence."""
    value=copy.deepcopy(failed);value.update(status='passed-component-only',failure=None,assertions=326,originalAssertionCounter=300,addedSetupAssertions=26,addedScrollSetupAssertions=6,addedKeyboardSetupAssertions=20,keyboardSetupEvents=8)
    value['cases']=[{'id':i,'name':name,'status':'passed-component-native','proposals':p,'fixtureAcknowledgements':a,'authoritativeCommits':None,'rawCheckedListenerCallbacks':None}for i,(name,p,a)in enumerate(oracle.expected_cases(),1)]
    trace=support.read_bytes((support.SCROLL/'runtime/runtime-1/scroll-private-trace.log').read_bytes())
    geometry=copy.deepcopy(next(row['geometry'] for row in trace['entries'] if row['stage']=='scroll.geometry.before'))
    requests=[];native=[];rows=[]
    def view(base,identity,cls,focused=False,attached=True):
        state=copy.deepcopy(base);state.update(**{'class':cls,'identity':identity,'id':-1,'focusable':True,'focusableInTouchMode':False,'inTouchMode':False,'hasFocus':focused,'visibility':0,'windowVisibility':0,'focused':focused,'attached':attached,'enabled':True})
        return state
    for helper in range(4):
        case=40+helper
        for action in (0,1):
            request={'case':case,'action':action,'keyCode':20,'source':257,'repeat':0,'downTime':1000+100*helper,'eventTime':1000+100*helper+action,'dispatched':True};requests.append(request)
            for half in (0,1):native.append({**{k:v for k,v in request.items() if k!='dispatched'},'stage':'activity.key.before' if half==0 else 'activity.key.after','uptime':2000+helper*100+action*2+half,'returned':None if half==0 else True,'canceled':False,'deviceId':-1})
        for index,stage in enumerate(oracle.STAGES):
            toggleFocused=index in (2,4,5,6,7);controlFocused=index==3
            toggle=view(geometry['toggle'],101+helper,'dev.mixer.android.NativeAppearanceViewsV2$NativeSwitch',toggleFocused)
            control=None if index==0 else view(geometry['toggle'],201+helper,'android.widget.Button',controlFocused,index<4)
            ancestor=view(geometry['content'],301+helper,'android.widget.FrameLayout');ancestor['descendantFocusability']=262144
            owner=copy.deepcopy(toggle if toggleFocused else control if controlFocused else None)
            geo=copy.deepcopy(geometry);geo['toggle']={k:copy.deepcopy(v) for k,v in toggle.items() if k in geometry['toggle']}
            state={'toggle':toggle,'control':control,'ancestors':[ancestor],'ancestorChainComplete':True,'ancestorFocusBlocked':False,'toggleOwnedVisible':True,'controlOwnedVisible':index in (1,2,3),'controlPresent':index in (1,2,3),'decorFocusOwner':copy.deepcopy(owner),'activityFocusOwner':copy.deepcopy(owner),'toggleIsFocusOwner':toggleFocused,'controlIsFocusOwner':controlFocused,'geometry':geo}
            before=5*helper+[0,0,1,2,3,4,4,5][index]
            rows.append({'case':case,'stage':stage,'uptime':3000+100*helper+index,'requestReturned':True if index in (3,5) else None,'state':state,'inputOpen':True,'permit':True,'proposals':0,'fixtureAcknowledgements':0,'nativeChecked':False,'boundChecked':False,'pressed':False,'stableToggle':True,'quiet':True,'addedKeyboardSetupAssertionsBefore':before,'addedSetupAssertionsBefore':6+before})
    value['keyboardSetup']={'schema':1,'requests':requests,'observations':rows,'nativeKeyTrace':native,'dropped':0,'observerFailures':0}
    return value

def source_checks():return test()
if __name__=='__main__':print(json.dumps(test(),sort_keys=True))
