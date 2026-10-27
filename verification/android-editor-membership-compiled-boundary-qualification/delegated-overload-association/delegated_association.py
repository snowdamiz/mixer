"""One source-selected host delegation; this module never admits a product or runtime."""
import collections
INNER='(II)Z'
OUTER='(IILandroid/view/inputmethod/TextAttribute;)Z'
CALLER=('dev/mixer/android/NativeEditorConnectionV2$Api33','lambda$setComposingRegion$4','(IILandroid/view/inputmethod/TextAttribute;)Ljava/lang/Boolean;',7)
def require(value,message):
 if not value:raise ValueError(message)
def validate_row(row):
 require(type(row)is dict and row.get('family')=='setComposingRegionWithAttributes','exact selected family')
 require(type(row.get('actual_native_outcomes'))is list and type(row.get('original_target'))is str and bool(row['original_target']),'structured actual native observations and original receiver')
 own=[item for item in row['actual_native_outcomes']if item['method']=='BaseInputConnection.setComposingRegion'and item['receiver_identity']==row['original_target']and item['completion']=='return'];groups=collections.defaultdict(list)
 for item in own:
  index=item['native_event_sequence_index'];require(type(index)is int and index>=0,'delegated actual integer event index');groups[index].append(item)
 if row['state']in('current','successor'):require(len(groups)==1 and type(row['native_target_entries'])is int and row['native_target_entries']==1,'mandatory actual delegated normal completion and exactly one native entry')
 for index,items in groups.items():
  require(len(items)==2,'missing or doubled actual delegated completion');inner,outer=items
  require([item['descriptor']for item in items]==[INNER,OUTER],'selected actual delegated descriptor order')
  require(type(inner['value'])is dict and type(outer['value'])is dict and inner['value'].get('kind')==outer['value'].get('kind')=='boolean'and type(inner['value'].get('value'))is bool and type(outer['value'].get('value'))is bool and inner['value']==outer['value'],'actual delegated typed boolean value equality')
  require(inner['receiver_identity']==outer['receiver_identity']==row['original_target']and inner['production_frames']==outer['production_frames'],'actual delegated own receiver and full frame-chain equality')
  require(inner['native_event_phase']==outer['native_event_phase']=='beforeReturn','delegated source hook phase')
  require(inner['native_outcome_association']=='original-own-hook-event'and outer['native_outcome_association']=='selected-original-delegated-overload-return'and outer['delegated_leaf_descriptor_pair']==[INNER,OUTER],'explicit selected delegated association, no generic event reuse')
  frames=inner['production_frames'];require(type(frames)is list and 0<len(frames)<=128,'actual complete selected product frame chain');first=frames[0];require(type(first)is dict and type(first['bci'])is int and (first['class'].replace('.','/'),first['method'],first['descriptor'],first['bci'])==CALLER,'independently fixed exact original adapter-overload caller, no coherent neighbor substitution')
 return {'actual_pairs':len(groups),'observed_normal_returns':len(own),'scope':'Two actual typed returned values share one original hook event. No second native entry, missing outcome or enclosing authority is inferred.'}
