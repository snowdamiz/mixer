"""Narrow v2 wrapper: explicit paired focus and stable native semantic metadata."""
import importlib.util
import pathlib
BASE=pathlib.Path(__file__).resolve().parent;ROOT=BASE.parents[1]
PREVIOUS=BASE.parent/'apple-toggle-keyboard-focus'
spec=importlib.util.spec_from_file_location('immutable_keyboard_v1_oracle',PREVIOUS/'keyboard_oracle.py')
original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
for name in ['state_contract','SPECS','CASES','ACTIONS','CASE_ACTION','COMMANDS','CASE_COMMAND_SEQUENCE','IDS','API','ENABLED_PHASES','STALE_PHASES','DISABLED_PHASES','PHASE_KEYS','require','number','natural','geometry_valid','focused','ax','witness']:
    globals()[name]=getattr(original,name)

def native_metadata(snapshot):
    ax(snapshot)
    return {name:{'identifier':snapshot['elements'][name]['identifier'],'label':snapshot['elements'][name]['label']} for name in IDS}

class Cursor(original.Cursor):
    def __init__(self,name):super().__init__(name);self.native_metadata=None
    def check(self,w):
        super().check(w)
        before,after=native_metadata(w['before']),native_metadata(w['after'])
        require(before==after,'Fixed native identifier/label changed during keyboard action')
        if self.native_metadata is not None:require(before==self.native_metadata,'Fixed native identifier/label changed between keyboard actions')
    def advance(self,w):
        super().advance(w);self.native_metadata=native_metadata(w['after'])

def verdict(candidate,case,action,before,after,file_changed=True):
    result=original.verdict(candidate,case,action,before,after,file_changed)
    result['schema']='mixer.apple-toggle.keyboard-v2-verdict.1';result['originalOraclePassed']=result['passed']
    try:
        w=before['keyboardWitness'];b,a=before['state'],after['state'];left=w['before']['elements'];right=w['after']['elements']
        p=result['predicates']
        p['pairedNativeFocusBefore']=type(b['focused']) is bool and b['focused'] is left['authored-toggle']['hasFocus']
        p['pairedNativeFocusAfter']=type(a['focused']) is bool and a['focused'] is right['authored-toggle']['hasFocus']
        p['authoredAXLabelMatchesAppBefore']=left['authored-toggle']['label']==b['label']
        p['authoredAXLabelMatchesAppAfter']=right['authored-toggle']['label']==a['label']
        p['allFixedNativeIdentifiersStable']=all(left[name]['identifier']==right[name]['identifier']==name for name in IDS)
        p['allFixedNativeLabelsStable']=all(type(left[name]['label']) is str and left[name]['label']==right[name]['label'] for name in IDS)
        changed=b['focused'] is not a['focused']
        focus_events=[event for event in after['events'][len(before['events']):] if event['reason']=='focus']
        signal=not changed or (file_changed is True and bool(focus_events) and focus_events[-1]['state']['focused'] is a['focused'])
        p['appFocusUpdateSignalObserved']=signal
        result['missingAppFocusUpdateSignal']=changed and not signal
        result['pairedFocusDisagreement']=not (p['pairedNativeFocusBefore'] and p['pairedNativeFocusAfter'])
        result['focusRequirement']='App UIFocusItem.isFocused must equal paired authored AX.hasFocus; disagreement is failing evidence pending native analysis. No platform equivalence waiver.'
    except (KeyError,TypeError,ValueError,IndexError,AttributeError):
        result['predicates']['pairedNativeFocusAndMetadataComplete']=False
    result['passed']=all(v is True for v in result['predicates'].values())
    result['scope']='Strict three-fixed-element native keyboard scope only. Every acquisition Tab must change to an observed fixed element within12steps. No general system navigation, physical keyboard/VoiceOver, live adapter, compositor, dogfood or GA acceptance.'
    return result
