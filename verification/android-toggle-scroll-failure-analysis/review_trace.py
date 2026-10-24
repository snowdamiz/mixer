#!/usr/bin/env python3
"""Read an already exported private trace without native tools or cause inference."""
import argparse,hashlib,json,re
from pathlib import Path
def summarize(value):
    if value['schema']!=1 or value['mode']!='original-protocol' or value['dropped'] or value['observerFailures'] or value['listenerConsumes'] is not False:raise ValueError('trace invalid or incomplete')
    entries=value['entries']
    if not 0<len(entries)<=2048 or [row['sequence'] for row in entries]!=list(range(len(entries))):raise ValueError('ordered bounded trace required')
    cases=[]
    for case in sorted({row['case'] for row in entries}):
        rows=[row for row in entries if row['case']==case]
        select=lambda stage:[row for row in rows if row['stage']==stage]
        before=select('worker.injection.before');after=select('worker.injection.after')
        delivered=select('activity.dispatch.before');child=select('toggle.OnTouchListener.before-return-false')
        intercept=[row for row in select('scroll.intercept.after') if row['returned'] is True]
        geometryBefore=select('scroll.geometry.before');geometryAfter=select('scroll.geometry.after')
        cases.append({'case':case,'injectionCount':len(before),'completedInjectionCount':len(after),
            'injectionActions':[row['event']['masked'] for row in before],
            'injectionTimestampOffsets':[row['event']['eventTime']-before[0]['event']['eventTime'] for row in before],
            'injectionTimestampLead':[row['event']['eventTimeLead'] for row in before],
            'injectionUptimeOffsets':[row['uptime']-before[0]['uptime'] for row in before],
            'activityDeliveryCount':len(delivered),'activityActions':[row['event']['masked'] for row in delivered],
            'activityUptimeOffsets':[row['uptime']-delivered[0]['uptime'] for row in delivered],
            'childDeliveryCount':len(child),'childActions':[row['event']['masked'] for row in child],
            'childCancelCount':sum(row['event']['masked']==3 for row in child),'interceptTrueCount':len(intercept),
            'initialState':None if not geometryBefore else geometryBefore[0]['state'],
            'finalConjunctState':None if not geometryAfter else geometryAfter[-1]['state'],
            'initialGeometry':None if not geometryBefore else geometryBefore[0]['geometry']})
    return {'schema':1,'status':'summarized-observed-private-trace-only','entries':len(entries),'cases':cases,
        'cause':'not inferred; compare actual hierarchy, extent, assertion conjuncts and injection/delivery timing','observerTimingPerturbation':True,'full45CaseAcceptance':False}
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--trace',type=Path,required=True);parser.add_argument('--instrumentation',type=Path,required=True);args=parser.parse_args()
    data=args.trace.read_bytes()
    if len(data)>524288:raise ValueError('trace too large')
    declared=re.findall(rb'INSTRUMENTATION_RESULT: scrollTraceSHA256=([0-9a-f]{64})',args.instrumentation.read_bytes())
    if declared!=[hashlib.sha256(data).hexdigest().encode()]:raise ValueError('instrumentation trace binding mismatch')
    result=summarize(json.loads(data));result['traceSHA256']=hashlib.sha256(data).hexdigest();print(json.dumps(result,indent=2,sort_keys=True))
if __name__=='__main__':main()
