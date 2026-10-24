"""Independent host decoding of actual private pointer exports; fabricated host fixtures never qualify native acceptance."""
import hashlib
import json
import math
from pathlib import Path

ORDER=[(i,r) for r in range(1,4) for i in ('P01','P02','P03','P04','P05')]+[(i,1) for i in ('P06','G01','G02a','G02b','G03')]
SOURCE=4098

def unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('duplicate observed JSON key')
        result[key]=value
    return result

def parse(data):return json.loads(data,object_pairs_hook=unique)
def need(condition,message):
    if not condition:raise ValueError(message)

def actual_packet(path):
    data=path.read_bytes();packet=parse(data);nodes={}
    def node(value):
        need(value['id'] not in nodes,'duplicate packet node');nodes[value['id']]=value
        for child in value['children']:node(child)
    node(packet['document']['root'])
    return {'sha256':hashlib.sha256(data).hexdigest(),'revision':str(packet['document']['revision']),'values':{i:n['properties']['value'] for i,n in nodes.items() if n['kind']=='toggle'}}

def state_packet(state,packets,*,retired=False):
    if retired:need(state['revision'] is None and state['packetReference'] is None and state['packetSHA256'] is None,'retired authoritative packet must be null');return
    digest=state['packetSHA256'];need(digest in packets,'actual boundary packet export missing')
    p=packets[digest];need(state['revision']==p['revision'] and state['values']==p['values'],'actual packet decoded revision/state differs from snapshot')
    need(state['values']==state['nativeValues'],'native/packet values differ')

def finite(value):return type(value) in (int,float) and math.isfinite(value)
def uptime(value):return type(value) is int and value>=0

def pressure(pointer,expected):
    need(finite(pointer['pressure']) and finite(expected['pressure']) and abs(pointer['pressure']-expected['pressure'])<=0.000001,'actual pointer pressure differs')

def coordinates(pointer,expected,*,offset=(0,0),local=False):
    x,y=('x','y') if local else ('rawX','rawY')
    need(all(finite(v) for v in (pointer[x],pointer[y],*offset,expected['x'],expected['y'])),'nonfinite pointer coordinate')
    need(abs(pointer[x]+offset[0]-expected['x'])<=1 and abs(pointer[y]+offset[1]-expected['y'])<=1,'actual pointer screen coordinates differ')

def point(event,expected,down):
    need(event['pointerCount']==1 and len(event['pointers'])==1 and event['source']==SOURCE and event['downTime']==down,'actual touchscreen pointer metadata differs')
    need(type(event['flags']) is int and event['flags'] & 3==0,'actual Activity pointer is obscured or partially obscured')
    need(type(event['actionIndex']) is int and event['actionIndex']==0,'actual pointer action index differs')
    p=event['pointers'][0];need(p['id']==0 and p['toolType']==1,'actual pointer identity/tool differs')
    coordinates(p,expected);pressure(p,expected)
    need(event['action']==expected['action'] and event['eventTime']==down+expected['offsetMilliseconds'],'actual pointer action/time differs')

def historical(event,sample,expected):
    need(expected['action']==2 and len(sample['pointers'])==1 and sample['pointers'][0]['id']==0,'actual MOVE history pointer metadata differs')
    current=event['pointers'][0]
    need(all(finite(current[k]) for k in ('rawX','rawY','x','y')),'historical raw/local offset is nonfinite')
    offset=(current['rawX']-current['x'],current['rawY']-current['y'])
    coordinates(sample['pointers'][0],expected,offset=offset,local=True);pressure(sample['pointers'][0],expected)

def validate(native,out,metadata):
    out=Path(out)
    need(native['status']=='passed','native fixture did not pass')
    need(native['gestureActions']==native['operations']==20 and native['setupOrdinaryCommits']==36 and native['activityOwners']==3,'exact action/setup/owner counts required')
    need(1<=native['checks']<=512 and native['checks']==len(native['assertions']) and all(r['passed'] for r in native['assertions']),'assertion budget/outcome differs')
    need(native['directNativeCallbackCount'] is None and native['directNativeCallbackObservation']=='unobserved','internal callbacks must remain explicitly null/unobserved')
    need(native['cleanupInjectedMotionEvents']==0 and native['failure'] is None and native['cleanupFailure'] is None,'successful action cannot depend on cleanup input or a suppressed failure')
    need(native['durationMilliseconds']<=180000 and native['deliveryAndHistoryRows']<=2048,'native wall/observation budget exceeded')
    for key in ('apkSHA256','sourceRevision','sourceTree','sourceClosureSHA256','descriptorSHA256','fixtureSHA256'):need(native[key]==metadata[key],'native frozen identity differs '+key)
    exports=native['exports'];need(len(exports)<=128 and sum(v['bytes'] for v in exports.values())<=33554432,'metadata export budget differs')
    for name,value in exports.items():
        data=(out/name).read_bytes();need(len(data)==value['bytes'] and hashlib.sha256(data).hexdigest()==value['sha256'],'export identity differs '+name)
    log=(out/'pointer-observations.jsonl').read_bytes();need(len(log)<=8388608,'observation JSONL exceeds eight MiB')
    rows=[parse(line) for line in log.splitlines()];packets={}
    for name in exports:
        if name.endswith('.bin'):
            need((out/name).stat().st_size<=262144,'packet byte bound exceeded');p=actual_packet(out/name);need(name=='pointer-packet-'+p['sha256']+'.bin' or name=='pointer-retirement-before.bin','packet filename/hash differs');packets[p['sha256']]=p
    setup=[r for r in rows if r['kind']=='ordinary-setup'];need(len(setup)==36 and [r['ordinal'] for r in setup]==list(range(1,37)),'36 individually logged ordinary setup commits required')
    for r in setup:
        need(int(r['after']['revision'])==int(r['beforeRevision'])+1 and r['pointerEvidence'] is False,'setup scope or revision differs');state_packet(r['after'],packets)
    summaries=native['summaries'];need([(r['actionId'],r['repetition']) for r in summaries]==ORDER,'exact twenty action order differs')
    requested=0;delivery=0;previous_action_end=-1
    for ordinal,(summary,(identifier,repetition)) in enumerate(zip(summaries,ORDER),1):
        need(summary['status']=='passed' and summary['ordinal']==ordinal and summary['directNativeCallbackCount'] is None,'summary outcome or callback scope differs')
        sealed=(out/('pointer-sequence-'+str(ordinal)+'.json')).read_bytes();sequence=parse(sealed);action=identifier+'-'+str(repetition)
        binding=[r for r in rows if r['kind']=='sealed-sequence' and r['actionId']==action]
        need(len(binding)==1 and binding[0]['sha256']==hashlib.sha256(sealed).hexdigest(),'sealed sequence binding missing')
        need(sequence['actionId']==identifier and sequence['repetition']==repetition and sequence['ordinal']==ordinal,'sealed action identity differs')
        for key in ('apkSHA256','sourceRevision','sourceTree','sourceClosureSHA256','descriptorSHA256','fixtureSHA256'):need(sequence[key]==metadata[key],'sealed identity differs '+key)
        planned=sequence['events'];need(2<=len(planned)<=16 and len(planned)==summary['injectedEvents'],'per-action event budget differs');requested+=len(planned)
        need(planned[0]['action']==0 and planned[0]['offsetMilliseconds']==0,'sealed DOWN missing')
        need(planned[-1]['action']==(3 if identifier=='P05' else 1),'sealed terminal differs')
        need(all(b['offsetMilliseconds']>a['offsetMilliseconds'] for a,b in zip(planned,planned[1:])),'sealed event times not strictly monotonic')
        need(sequence['thresholds']['longPressTimeout']<=1500,'unsupported long press precondition')
        if identifier in ('P03','P04','P05'):
            need(len(planned)==10 and [p['offsetMilliseconds'] for p in planned[1:9]]==[80*i for i in range(1,9)] and planned[-1]['offsetMilliseconds']==790,'eight MOVE 640ms drag plus 150ms hold differs')
            need(abs(planned[-1]['x']-planned[0]['x'])>sequence['thresholds']['touchSlop'] and all(p['y']==planned[0]['y'] for p in planned),'authored horizontal slop path differs')
        elif identifier=='P06':need(len(planned)==14 and planned[0]['y']-planned[-1]['y']>4*sequence['thresholds']['touchSlop'],'vertical drag trajectory differs')
        elif identifier=='P02':need(planned[-1]['offsetMilliseconds']==sequence['thresholds']['longPressTimeout']+100,'held-tap timeout differs')
        else:need(planned[-1]['offsetMilliseconds']==80,'80ms tap differs')
        sends=[r for r in rows if r['kind']=='worker-send' and r['actionId']==action];need(len(sends)==len(planned),'one worker send log per sealed event required')
        down=sequence['downTime'];start=summary['actionStartUptime'];end=summary['actionEndUptime'];duration=summary['durationMilliseconds']
        need(all(uptime(v) for v in (down,start,end,duration)) and start>=previous_action_end and start<=down<=down+planned[-1]['offsetMilliseconds']<=end and end-start==duration<=5000,'actual complete action interval exceeds five seconds or is inconsistent')
        need(sequence['actionStartUptime']==start,'sealed action start differs from measured interval')
        intervals=[r for r in rows if r['kind']=='action-interval' and r['actionId']==action]
        need(len(intervals)==1 and intervals[0]['completed'] is True and all(intervals[0][k]==summary[k] for k in ('actionStartUptime','actionEndUptime','durationMilliseconds')),'independent action interval row missing or differs')
        previous_action_end=end
        for sent,expected in zip(sends,planned):
            need(all(uptime(sent[k]) and start<=sent[k]<=end for k in ('scheduledUptime','workerBefore','workerAfter')),'worker timestamp outside bounded action interval')
            point(sent['event'],expected,down);need(sent['exception'] is None and sent['scheduledUptime']==down+expected['offsetMilliseconds'] and 0<=sent['workerBefore']-sent['scheduledUptime']<=100 and sent['workerAfter']>=sent['workerBefore'],'actual worker injection timing/exception differs')
        entries=[r for r in rows if r['kind']=='activity-entry' and r['actionId']==action];exits=[r for r in rows if r['kind']=='activity-exit' and r['actionId']==action]
        need(len(entries)==len(exits)==summary['nativeDeliveryCount'] and len(entries)>=2,'Activity entry/exit count differs')
        need([r['sequence'] for r in entries]==[r['sequence'] for r in exits],'Activity entry/exit pairing differs');delivery+=len(entries)
        times={down+p['offsetMilliseconds']:p for p in planned};previous=down-1;previous_dispatch=start;observed_moves=set()
        for i,(entry,exit_) in enumerate(zip(entries,exits)):
            entry_time=entry['workerIndependentUptime'];exit_time=exit_['uptime']
            need(uptime(entry_time) and uptime(exit_time) and start<=previous_dispatch<=entry_time<=exit_time<=end,'Activity timestamp outside bounded action interval or dispatch order')
            previous_dispatch=exit_time
            e=entry['event'];need(uptime(e['eventTime']) and e['eventTime'] in times,'actual delivery time outside sealed events');point(e,times[e['eventTime']],down)
            need(exit_['exception'] is None and type(exit_['returned']) is bool,'Activity must preserve successful Boolean super return')
            need(exit_['event']==e,'Activity observation transformed event')
            need(e['action']==(0 if i==0 else planned[-1]['action'] if i==len(entries)-1 else 2),'unexpected terminal or unpaired gesture')
            for sample in e['history']:
                time=sample['eventTime']
                need(uptime(time) and previous<time<e['eventTime'] and time in times and times[time]['action']==2,'actual MOVE history not strictly ordered at a sealed MOVE time')
                historical(e,sample,times[time]);observed_moves.add(time);previous=time
            need(previous<e['eventTime'],'actual delivery and history samples not strictly ordered')
            if e['action']==2:observed_moves.add(e['eventTime'])
            previous=e['eventTime']
        final_moves=[down+p['offsetMilliseconds'] for p in planned if p['action']==2]
        if final_moves:need(final_moves[-1] in observed_moves,'actual final MOVE endpoint sample missing before terminal hold')
        before,after=summary['before'],summary['after'];retired=identifier=='G03'
        need(sequence['before']==before,'sealed starting snapshot differs');state_packet(before,packets,retired=retired);state_packet(after,packets,retired=retired)
        need(before['editors']==after['editors'] and before['taskIdentities']==after['taskIdentities'] and before['targetRecord']==after['targetRecord'] and before['targetView']==after['targetView'] and before['targetGeneration']==after['targetGeneration'] and after['targetSameRecord'] and after['targetSameView'],'unintended editor or native identity change')
        commit=identifier in ('P01','P02','P03','P04','G02b');expected_delta=None if retired else '1' if commit else '0'
        need(summary['commitAcknowledgementCount']==expected_delta,'commit acknowledgement count differs')
        if not retired:
            need(int(after['revision'])-int(before['revision'])==int(expected_delta),'actual authoritative revision delta differs')
            wanted=dict(before['values'])
            if commit:wanted['task.1']=identifier in ('P01','P03','G02b')
            need(after['values']==wanted and after['lastNativeInputFailure'] is None and not after['retired'],'exact task values or retirement differs')
            if not commit:need(before['packetReference']==after['packetReference'] and before['packetSHA256']==after['packetSHA256'],'no-commit packet object/bytes changed')
            need(after['current']==(identifier!='G02a'),'forwarding gate outcome differs')
        else:need(after['retired'] and after['rendererRetired'] and not after['current'] and not after['hasCommittedPresentation'] and before['nativeValues']==after['nativeValues'],'retirement reopened or mutated native value')
        probes=[r['state'] for r in rows if r['kind']=='after-send' and r['actionId']==action];need(len(probes)==len(planned),'per-event main probe missing')
        for probe in probes[:-1]:need(probe['revision']==before['revision'] and probe['packetSHA256']==before['packetSHA256'] and probe['packetReference']==before['packetReference'],'acknowledgement occurred before terminal')
        if identifier=='P06':need(after['scrollY']-before['scrollY']>sequence['thresholds']['touchSlop'],'actual list did not scroll beyond slop')
        else:need(after['scrollY']==before['scrollY'],'non-scroll action changed list scroll')
    gate_before=summaries[17]['after'];gate_after=summaries[18]['before']
    need(all(gate_before[k]==gate_after[k] for k in ('packetReference','packetSHA256','revision','values','nativeValues','taskIdentities','targetRecord','targetView','targetGeneration')),'explicit refresh changed retained packet or native identity')
    retirement_before=parse((out/'pointer-retirement-before.json').read_bytes());retirement_after=parse((out/'pointer-retirement-after.json').read_bytes())
    saved=actual_packet(out/retirement_before['file']);state_packet(retirement_before['state'],packets)
    need(retirement_before['packetSHA256']==saved['sha256']==retirement_after['savedPacketSHA256'] and retirement_before['packetReference']==retirement_after['savedPacketReference'],'saved pre-retirement packet bytes/reference changed')
    need(retirement_after['refreshRejected'] is True,'retirement refresh rejection not observed');state_packet(retirement_after['state'],packets,retired=True)
    need(requested==native['injectedMotionEvents']<=320 and not any(r['kind']=='cleanup-terminal-cancel' for r in rows),'global event count or cleanup input differs')
    return {'status':'passed-independent-private-pointer-export-oracle','gestureActions':20,'requestedEvents':requested,'observedActivityEntries':delivery,'actualPacketsDecoded':len(packets),'directNativeCallbackCount':None,'scope':'only this actual fixture receipt; host synthetic oracle tests do not qualify native execution'}
