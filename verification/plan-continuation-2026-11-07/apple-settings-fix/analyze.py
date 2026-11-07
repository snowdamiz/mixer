#!/usr/bin/env python3
import collections,hashlib,json,pathlib,statistics
HERE=pathlib.Path(__file__).resolve().parent
actual=HERE.parent/'apple-runtime';result=json.loads((actual/'result.json').read_bytes());runtime=actual/result['artifacts']['runtimeDirectory']
paths=sorted((runtime/'captures').glob('0000-settings-*.json'));rows=[json.loads(p.read_bytes()) for p in paths]
start=rows[0]['record']['uptime'];first=rows[0]['receivedUptime'];events=[];uploads=collections.defaultdict(list)
for row in rows:
 r=row['record']
 if r['kind']=='chunk':uploads[r['slot']].append(row)
 else:events.append({'sequence':r.get('sequence',0),'kind':r['kind'],'stage':r.get('stage'),'runnerElapsed':r['uptime']-start,'receiverElapsed':row['receivedUptime']-first,'captureSeconds':r.get('captureFinishedUptime',0)-r.get('captureStartedUptime',0),'files':r.get('files',{})})
terminal=next(r for r in rows if r['record'].get('stage')=='terminal');after=next(r for r in rows if r['record'].get('stage')=='after-switch')
png=terminal['record']['files']['png'];prior=runtime/'captures/settings-0083-png.png';assert len(prior.read_bytes())==png['bytes'] and hashlib.sha256(prior.read_bytes()).hexdigest()==png['sha256']
chunks=uploads['settings-0131-png'];gaps=[b['receivedUptime']-a['receivedUptime'] for a,b in zip(chunks,chunks[1:])]
summary={'scope':'retained V9 source/timing analysis; no new native evidence','baselineResult':str((actual/'result.json').relative_to(HERE.parents[2])),
 'baselineFailed':True,'diagnosticSeconds':29,'nativeFirstFailure':json.loads((runtime/'session/local-settings-first-failure.json').read_bytes())['diagnostic']['record'],
 'events':events,'terminalPNG':{'bytes':png['bytes'],'sha256':png['sha256'],'sameDescriptorAsAfterSwitch':png==after['record']['files']['png'],'priorPayloadHashRechecked':True,'expectedChunks':44,'receivedChunks':len(chunks),'missingChunks':44-len(chunks),'firstToLastReceivedSeconds':chunks[-1]['receivedUptime']-chunks[0]['receivedUptime'],'medianInterarrivalSeconds':statistics.median(gaps)},
 'clockCaveat':'receivedUptime is sampled inside Session._request after FullCaseBridge binding checks; runner-to-receiver deltas include more than network time and are not isolated RTT measurements.',
 'hypotheses':[
 {'name':'JSON serialization or HTTP connection churn dominates','test':'host_probe.py: exact 158 retained records, Foundation serializer, HTTP/1.0 vs HTTP/1.1, with and without original TransactionStore','finding':'Not supported as dominant by host measurements: 0.00875s serialization; durable HTTP/1.0 0.40072s vs HTTP/1.1 0.33488s overall. Host is not the iOS URLSession path. HTTP/1.1 candidate rejected for promotion.'},
 {'name':'Cumulative bounded UI and per-request validation/transport work exhausts 29s; redundant PNG transfers are avoidable','test':'retained phase/chunk timings, exact RuntimeBindings checks, actual full composition and terminal payload identity','finding':'Supported for this failure: no in-flight request stall; failure is begin-deadline. Complete source-binding checks cost 2.526s for 158 host invocations. Terminal re-sends an identical validated 219465-byte PNG in 44 serial transactions. Selected correction reuses only identical terminal bytes within the same Session.'},
 {'name':'Provider stall or a universally inadequate observational budget','test':'first-failure branch, switch-action/after/terminal timing and original enabled-within-three-seconds verdict','finding':'No evidence of a provider stall in V9; the switch did enable. This does not establish that 29s is sufficient on a fresh run. Keep the failed baseline and both budgets unchanged; native completion/Tab must be measured after review.'}],
 'selectedCorrection':'Terminal PNG content reuse after fresh terminal metadata, exact descriptor equality, previous complete validated payload, repeat PNG/hash checks and new durable terminal artifact publication.',
 'budgetIncreaseSelected':False,'nativeValidationPending':True,'hostResultsDoNotQualifyNativeSetupOrTab':True}
(HERE/'analysis.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({'terminalPNG':summary['terminalPNG'],'baselinePreserved':True,'nativeValidationPending':True}))
