"""Host-only summary controls with synthetic trace data; no native claim."""
import json
import review_trace
def test():
    rows=[]
    def add(stage,action=None,time=1000,uptime=1000,returned=None,state=None,geometry=None):
        row={'sequence':len(rows),'case':18,'stage':stage,'uptime':uptime,'returned':returned,'state':state}
        if action is not None:row['event']={'masked':action,'eventTime':time,'eventTimeLead':time-uptime}
        if geometry is not None:row['geometry']=geometry
        rows.append(row)
    add('scroll.geometry.before',state={'scrollPositive':False,'zeroProposals':True,'notPressed':True,'positiveContentExtent':True},geometry={'contentHeight':6000,'viewportHeight':1900})
    for i,action in enumerate([0,2,2,2,2,2,2,2,1]):
        add('worker.injection.before',action,1000+25*i,1000+3*i);add('activity.dispatch.before',action,1000+25*i,1001+3*i);add('worker.injection.after',action,1000+25*i,1002+3*i)
    add('toggle.OnTouchListener.before-return-false',0);add('scroll.intercept.after',2,returned=True);add('toggle.OnTouchListener.before-return-false',3)
    add('scroll.geometry.after',state={'scrollPositive':False,'zeroProposals':True,'notPressed':True,'positiveContentExtent':True})
    value={'schema':1,'mode':'original-protocol','dropped':0,'observerFailures':0,'listenerConsumes':False,'entries':rows}
    result=review_trace.summarize(value);case=result['cases'][0];checks=0
    def need(value):
        nonlocal checks
        checks+=1
        if not value:raise AssertionError('summary host check '+str(checks))
    need(case['injectionCount']==case['completedInjectionCount']==case['activityDeliveryCount']==9)
    need(case['injectionTimestampOffsets']==[25*i for i in range(9)] and case['injectionUptimeOffsets']==[3*i for i in range(9)])
    need(case['childCancelCount']==case['interceptTrueCount']==1)
    need(case['finalConjunctState']['scrollPositive'] is False and case['finalConjunctState']['positiveContentExtent'] is True)
    need(result['full45CaseAcceptance'] is False and result['cause'].startswith('not inferred'))
    for field,bad in [('dropped',1),('observerFailures',1),('listenerConsumes',True)]:
        changed=dict(value);changed[field]=bad
        try:review_trace.summarize(changed)
        except ValueError:checks+=1
        else:raise AssertionError('incomplete trace admitted')
    rows[0]['sequence']=9
    try:review_trace.summarize(value)
    except ValueError:checks+=1
    else:raise AssertionError('out of order trace admitted')
    return {'status':'passed-host-only-synthetic-trace-summary-controls','checks':checks,'nativeBehaviorVerified':False}
if __name__=='__main__':print(json.dumps(test(),sort_keys=True))
