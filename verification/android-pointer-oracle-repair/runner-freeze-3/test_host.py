#!/usr/bin/env python3
"""Host-only negative controls. These tests never prove actual Android delivery."""
import hashlib
import copy
import io
import json
from pathlib import Path
import sys
import tarfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import common
import bounded_output
import oracle
import run

WORK=None
RUNNER=None

def synthetic_oracle_fixture(directory):
    """Only parser/oracle coverage: no Android calls, never a native receipt."""
    directory.mkdir();exports={};rows=[];summaries=[];sequence_no=0;events_total=0
    metadata={k:'a'*64 for k in ('apkSHA256','sourceClosureSHA256','descriptorSHA256','fixtureSHA256')};metadata.update(sourceRevision='b'*40,sourceTree='c'*40)
    def output(name,data):
        (directory/name).write_bytes(data);exports[name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    def state(revision,values,identifier='task.1',owner=1,closed=False,retired=False,scroll=0):
        children=[{'id':i,'kind':'toggle','properties':{'value':v},'children':[]} for i,v in values.items()]
        data=json.dumps({'document':{'revision':revision,'root':{'id':'screen','kind':'navigation','children':children}}},sort_keys=True).encode();digest=hashlib.sha256(data).hexdigest();name='pointer-packet-'+digest+'.bin'
        if not retired and name not in exports:output(name,data)
        ids={i:{'record':'record-'+str(owner)+'-'+i,'view':'view-'+str(owner)+'-'+i,'generation':i} for i in values}
        return {'packetSHA256':None if retired else digest,'packetReference':None if retired else 'packet-'+digest,'revision':None if retired else str(revision),'values':{} if retired else dict(values),'nativeValues':dict(values),'taskIdentities':ids,'editors':{},'targetRecord':'record-'+str(owner)+'-'+identifier,'targetView':'view-'+str(owner)+'-'+identifier,'targetGeneration':identifier,'targetSameRecord':True,'targetSameView':True,'current':not(closed or retired),'retired':retired,'rendererRetired':retired,'hasCommittedPresentation':not retired,'lastNativeInputFailure':None,'scrollY':scroll}
    revision=1;values={'task.1':False,'task.2':False}
    for ordinal,(identifier,repetition) in enumerate(oracle.ORDER,1):
        if identifier=='P06':
            for i in range(36):
                previous=revision;revision+=1
                if i%2:values['task.'+str(3+i//2)]=False
                rows.append({'kind':'ordinary-setup','ordinal':i+1,'beforeRevision':str(previous),'after':state(revision,values),'pointerEvidence':False})
        if identifier in ('G01','G03'):revision=1;values={'task.1':False,'task.2':False}
        owner=1 if identifier.startswith('P') else 3 if identifier=='G03' else 2;target='add' if identifier=='G01' else 'task.1';retired=identifier=='G03'
        before=state(revision,values,target,owner,identifier=='G02a',retired)
        commit=identifier in ('P01','P02','P03','P04','G02b')
        if commit:revision+=1;values['task.1']=identifier in ('P01','P03','G02b')
        after=state(revision,values,target,owner,identifier=='G02a',retired,100 if identifier=='P06' else 0)
        if retired:
            saved=state(revision,values,target,owner,False,False);raw=(directory/('pointer-packet-'+saved['packetSHA256']+'.bin')).read_bytes();output('pointer-retirement-before.bin',raw)
            output('pointer-retirement-before.json',json.dumps({'file':'pointer-retirement-before.bin','packetReference':saved['packetReference'],'packetSHA256':saved['packetSHA256'],'state':saved}).encode())
            output('pointer-retirement-after.json',json.dumps({'savedPacketReference':saved['packetReference'],'savedPacketSHA256':saved['packetSHA256'],'refreshRejected':True,'state':after}).encode())
        def step(action,offset,x,y):return {'action':action,'offsetMilliseconds':offset,'x':x,'y':y,'pressure':0 if action in (1,3) else 1}
        if identifier in ('P03','P04','P05'):
            left,right=(96,30) if identifier=='P04' else (30,96);planned=[step(0,0,left,50)]+[step(2,80*i,left+(right-left)*i/8,50) for i in range(1,9)]+[step(3 if identifier=='P05' else 1,790,right,50)]
        elif identifier=='P06':planned=[step(0,0,30,500)]+[step(2,80*i,30,500-20*i) for i in range(1,13)]+[step(1,1110,30,260)]
        else:planned=[step(0,0,30,50),step(1,600 if identifier=='P02' else 80,30,50)]
        down=ordinal*10000;start=down-200;end=down+planned[-1]['offsetMilliseconds']+100;sequence=dict(metadata,actionStartUptime=start,actionId=identifier,repetition=repetition,ordinal=ordinal,before=before,downTime=down,events=planned,thresholds={'touchSlop':8,'longPressTimeout':500});data=json.dumps(sequence).encode();filename='pointer-sequence-'+str(ordinal)+'.json';output(filename,data);action=identifier+'-'+str(repetition)
        rows.append({'kind':'sealed-sequence','actionId':action,'file':filename,'sha256':hashlib.sha256(data).hexdigest()})
        for index,p in enumerate(planned):
            event={'actionIndex':0,'flags':0,'action':p['action'],'downTime':down,'eventTime':down+p['offsetMilliseconds'],'source':4098,'pointerCount':1,'pointers':[{'id':0,'toolType':1,'rawX':p['x'],'rawY':p['y'],'x':p['x']-23,'y':p['y']-31,'pressure':p['pressure']}],'history':[]};sequence_no+=1;observed=after if index==len(planned)-1 else before
            rows.extend([{'kind':'worker-send','actionId':action,'event':event,'exception':None,'scheduledUptime':event['eventTime'],'workerBefore':event['eventTime']+1,'workerAfter':event['eventTime']+2},{'kind':'activity-entry','actionId':action,'sequence':sequence_no,'workerIndependentUptime':event['eventTime']+1,'event':event},{'kind':'activity-exit','actionId':action,'sequence':sequence_no,'uptime':event['eventTime']+2,'event':event,'exception':None,'returned':True},{'kind':'after-send','actionId':action,'state':observed}])
        rows.append({'kind':'action-interval','actionId':action,'actionStartUptime':start,'actionEndUptime':end,'durationMilliseconds':end-start,'completed':True})
        summaries.append({'actionStartUptime':start,'actionEndUptime':end,'durationMilliseconds':end-start,'actionId':identifier,'repetition':repetition,'ordinal':ordinal,'status':'passed','directNativeCallbackCount':None,'injectedEvents':len(planned),'nativeDeliveryCount':len(planned),'commitAcknowledgementCount':None if retired else '1' if commit else '0','before':before,'after':after});events_total+=len(planned)
    output('pointer-observations.jsonl',('\n'.join(json.dumps(r) for r in rows)+'\n').encode())
    native=dict(metadata,status='passed',gestureActions=20,operations=20,setupOrdinaryCommits=36,activityOwners=3,checks=1,assertions=[{'passed':True}],directNativeCallbackCount=None,directNativeCallbackObservation='unobserved',cleanupInjectedMotionEvents=0,failure=None,cleanupFailure=None,durationMilliseconds=100000,deliveryAndHistoryRows=248,exports=exports,summaries=summaries,injectedMotionEvents=events_total)
    return native,metadata

def rewrite_rows(directory,native,rows):
    data=('\n'.join(json.dumps(r) for r in rows)+'\n').encode();path=directory/'pointer-observations.jsonl';path.write_bytes(data)
    native['exports'][path.name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}

def coalesce(native,rows):
    # Seven actual historical local samples are delivered with the eighth MOVE.
    action='P03-1';move=[r for r in rows if r['kind']=='activity-entry' and r.get('actionId')==action and r['event']['action']==2]
    times={r['event']['eventTime'] for r in move[:-1]}
    history=[{'eventTime':r['event']['eventTime'],'pointers':[{'id':0,'x':r['event']['pointers'][0]['x'],'y':r['event']['pointers'][0]['y'],'pressure':1}]} for r in move[:-1]]
    rows[:]=[r for r in rows if not(r['kind'] in ('activity-entry','activity-exit') and r.get('actionId')==action and r['event']['eventTime'] in times)]
    for r in rows:
        if r['kind'] in ('activity-entry','activity-exit') and r.get('actionId')==action and r['event']['action']==2:r['event']['history']=copy.deepcopy(history)
    native['summaries'][2]['nativeDeliveryCount']=3


class HostTests(unittest.TestCase):
    def test_full_synthetic_parser_oracle_path_and_tamper_controls(self):
        directory=WORK/'synthetic-oracle-only';native,metadata=synthetic_oracle_fixture(directory);review=oracle.validate(native,directory,metadata)
        self.assertEqual(review['gestureActions'],20);self.assertEqual(review['requestedEvents'],124)
        native['summaries'][0]['commitAcknowledgementCount']='2';self.assertRaises(ValueError,oracle.validate,native,directory,metadata)
    def test_exact_twenty_action_manifest_and_124_nominal_events(self):
        f=json.loads((common.HERE/'operations.json').read_text());self.assertEqual(f['cycle']*3+f['singleActions'],[x[0] for x in oracle.ORDER]);self.assertEqual(len(oracle.ORDER),20)
        self.assertEqual(3*(2+2+10+10+10)+14+4*2,124);self.assertEqual(f['maxInjectedMotionEvents'],320);self.assertIsNone(f['directNativeCallbackCount'])
    def test_nested_seal_retains_nested_receipts(self):
        root=WORK/'nested-seal';root.mkdir();(root/'child').mkdir();(root/'child/artifact-seal.json').write_text('{}');(root/'artifact-seal.json').write_text('{}')
        self.assertEqual(set(common.exact_seal(root)),{'child/artifact-seal.json'})
        common.save(root/'artifact-seal.json',common.exact_seal(root));common.validate_seal(root)
        (root/'child/artifact-seal.json').write_text('{"changed":true}')
        self.assertRaises(ValueError,common.validate_seal,root)
    def test_seal_rejects_symlink(self):
        root=WORK/'symlink-seal';root.mkdir();(root/'data').write_text('x');(root/'link').symlink_to('data')
        try:self.assertRaises(ValueError,common.exact_seal,root)
        finally:(root/'link').unlink()
    def test_archive_rejects_unsafe_and_duplicate_members(self):
        for names in [['a','a'],['../a'],['/a']]:
            members=[]
            for name in names:m=tarfile.TarInfo(name);m.type=tarfile.REGTYPE;members.append(m)
            self.assertRaises(ValueError,RUNNER.validate_members,members,{n:{} for n in names})
    def test_archive_rejects_symlink(self):
        member=tarfile.TarInfo('a');member.type=tarfile.SYMTYPE;self.assertRaises(ValueError,RUNNER.validate_members,[member],{'a':{}})
    def test_target_requires_exact_fingerprint_and_tuple(self):
        target={'ro.kernel.qemu':'1','ro.product.model':'sdk_gphone64_arm64','ro.build.version.sdk':'37','ro.product.cpu.abi':'arm64-v8a','ro.build.fingerprint':RUNNER.FINGERPRINT,'ro.boot.qemu.avd_name':RUNNER.AVD,'sys.boot_completed':'1'}
        RUNNER.validate_target(target)
        for key in target:self.assertRaises(ValueError,RUNNER.validate_target,dict(target,**{key:'unsupported'}))
    def test_owned_identity_refuses_neighbor_port_and_wifi_drift(self):
        command='42 42 /opt/homebrew/share/android-commandlinetools/emulator/qemu/darwin-aarch64/qemu-system-aarch64-headless -avd megpt-parity-api37 -port 5586 -read-only -no-snapshot -no-window -no-audio -no-boot-anim -gpu swiftshader_indirect -feature -WiFiPacketStream'
        self.assertTrue(RUNNER.owned_identity(command,42));self.assertFalse(RUNNER.owned_identity(command.replace('5586','5588'),42));self.assertFalse(RUNNER.owned_identity(command.replace(' -feature -WiFiPacketStream',''),42));self.assertFalse(RUNNER.owned_identity(command,43))
    def test_no_dispatch_switch_fails_before_native_or_output(self):
        result=RUNNER.execute([sys.executable,'-B',str(common.HERE/'run.py'),'--build','candidate-5','--attempt','runtime-987654'],cwd=common.ROOT,timeout=20)
        self.assertEqual(result.returncode,2);self.assertIn(b'requires explicit root dispatch',result.stdout);self.assertFalse((common.RUNTIME/'runtime-987654').exists());self.assertEqual(result.groupCleanup['after'],[])
    def test_contract_drift_fails_before_parent_loading(self):
        with patch.object(run,'CONTRACT_SHA256','0'*64),patch.object(common,'accepted',side_effect=AssertionError('must not load accepted runner')):self.assertRaises(ValueError,run.load_runner)
    def test_exact_transform_rejects_missing_source_site(self):
        contract=json.loads(run.CONTRACT.read_text());original=(common.HERE/'runner-source-3/accepted_packaging_concrete.py').read_text()
        with self.assertRaises(ValueError):run.transform(original.replace("BUILDS = ROOT / 'verification/android-coordinator-apk-packaging'",'BUILDS = None'),contract)
    def test_exact_transform_rejects_duplicate_source_site(self):
        contract=json.loads(run.CONTRACT.read_text());original=(common.HERE/'runner-source-3/accepted_packaging_concrete.py').read_text()
        with self.assertRaises(ValueError):run.transform(original+"\nBUILDS = ROOT / 'verification/android-coordinator-apk-packaging'\n",contract)
    def test_implementation_drift_is_fail_closed(self):
        original=common.sha
        def sha(path):return '0'*64 if Path(path)==common.HERE/'CoordinatorJoinActivity.java' else original(path)
        with patch.object(common,'sha',side_effect=sha):self.assertRaises(ValueError,run.load_runner)
    def test_log_budget_reserves_cleanup_and_rejects_overflow(self):
        with patch.object(bounded_output,'LIMIT',1024),patch.object(bounded_output,'RESERVED_CLEANUP',128):
            b=bounded_output.Budget();stream=io.BytesIO();b.append(stream,b'a'*1000);self.assertEqual(len(stream.getvalue()),896);self.assertTrue(b.overflow)
            b.append(stream,b'z'*128,cleanup=True);self.assertEqual(len(stream.getvalue()),1024)
    def test_emulator_output_reader_is_bounded(self):
        with patch.object(bounded_output,'LIMIT',1024),patch.object(bounded_output,'RESERVED_CLEANUP',128):
            b=bounded_output.Budget();stream=io.BytesIO();reader=bounded_output.Reader(SimpleNamespace(stdout=io.BytesIO(b'x'*4096)),stream,b);reader.finish();self.assertTrue(b.overflow);self.assertEqual(len(stream.getvalue()),896)
    def test_json_duplicate_keys_rejected(self):self.assertRaises(ValueError,oracle.parse,'{"a":1,"a":2}')
    def test_uint64_revision_comparison_is_exact(self):
        state={'packetSHA256':'x','revision':str(2**64-1),'values':{'task.1':True},'nativeValues':{'task.1':True}}
        oracle.state_packet(state,{'x':{'revision':str(2**64-1),'values':{'task.1':True}}})
        self.assertRaises(ValueError,oracle.state_packet,dict(state,revision=str(2**64-2)),{'x':{'revision':str(2**64-1),'values':{'task.1':True}}})
    def test_no_current_packet_is_not_zero_revision_after_retirement(self):
        oracle.state_packet({'revision':None,'packetReference':None,'packetSHA256':None},{},retired=True)
        self.assertRaises(ValueError,oracle.state_packet,{'revision':'0','packetReference':None,'packetSHA256':None},{},retired=True)
    def test_endpoint_source_and_time_mismatch_rejected(self):
        expected={'pressure':0,'x':30,'y':50,'action':1,'offsetMilliseconds':80};event={'flags':0,'actionIndex':0,'pointerCount':1,'source':4098,'downTime':100,'eventTime':180,'action':1,'pointers':[{'id':0,'toolType':1,'rawX':30,'rawY':50,'pressure':0}]};oracle.point(event,expected,100)
        for key,bad in [('source',8194),('eventTime',181),('downTime',101),('pointerCount',2),('action',3)]:self.assertRaises(ValueError,oracle.point,dict(event,**{key:bad}),expected,100)
    def test_native_callback_claim_is_rejected(self):
        fake={'status':'passed','gestureActions':20,'operations':20,'setupOrdinaryCommits':36,'activityOwners':3,'checks':1,'assertions':[{'passed':True}],'directNativeCallbackCount':1,'directNativeCallbackObservation':'unobserved'}
        self.assertRaisesRegex(ValueError,'callbacks',oracle.validate,fake,WORK,{})
    def test_suppressed_assertion_or_partial_action_cannot_pass(self):
        fake={'status':'passed','gestureActions':19,'operations':19,'setupOrdinaryCommits':36,'activityOwners':3}
        self.assertRaises(ValueError,oracle.validate,fake,WORK,{})
    def test_child_descendant_cleanup_is_limited_to_new_group(self):
        code="import subprocess,sys;subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);print('owned-child-created',flush=True)"
        result=RUNNER.execute([sys.executable,'-c',code],cwd=common.ROOT,timeout=10)
        self.assertEqual(result.returncode,-2);self.assertEqual(result.groupCleanup['after'],[]);self.assertTrue(result.groupCleanup['before']);self.assertIn(b'owned-child-created',result.stdout)
        print(json.dumps({'ownedHostTestCommandGroup':result.groupCleanup,'exitCode':result.returncode},sort_keys=True))


class RepairTests(unittest.TestCase):
    def probe(self,name,mutation=None,accepted=False):
        directory=WORK/('repair-'+name);native,metadata=synthetic_oracle_fixture(directory)
        rows=[json.loads(line) for line in (directory/'pointer-observations.jsonl').read_text().splitlines()]
        if mutation:mutation(native,rows,directory)
        rewrite_rows(directory,native,rows)
        if accepted:return oracle.validate(native,directory,metadata)
        with self.assertRaises((ValueError,KeyError,TypeError)):oracle.validate(native,directory,metadata)
    def mutate_delivery(self,key,value,*,move=False):
        def mutate(native,rows,directory):
            for row in rows:
                if row['kind'] in ('activity-entry','activity-exit') and row.get('actionId')=='P03-1' and (not move or row['event']['action']==2):row['event'][key]=value
        return mutate
    def test_F01_obscured_and_partially_obscured_reject(self):
        for flag in (1,2,3):self.probe('obscured-'+str(flag),self.mutate_delivery('flags',flag))
    def test_action_index_rejects_nonzero(self):self.probe('index',self.mutate_delivery('actionIndex',1))
    def test_F02_move_pressure_zero_rejects(self):
        def mutate(native,rows,directory):
            for r in rows:
                if r['kind'] in ('activity-entry','activity-exit') and r.get('actionId')=='P03-1' and r['event']['action']==2:r['event']['pointers'][0]['pressure']=0
        self.probe('pressure',mutate)
    def test_F03_impossible_history_rejects(self):
        def mutate(native,rows,directory):
            for r in rows:
                if r['kind'] in ('activity-entry','activity-exit') and r.get('actionId')=='P03-1' and r['event']['action']==2:r['event']['history']=[{'eventTime':r['event']['downTime']+17,'pointers':[{'id':0,'x':999999,'y':-999999,'pressure':1}]}]
        self.probe('impossible-history',mutate)
    def test_F04_no_activity_moves_rejects(self):
        def mutate(native,rows,directory):
            rows[:]=[r for r in rows if not(r['kind'] in ('activity-entry','activity-exit') and r.get('actionId')=='P03-1' and r['event']['action']==2)];native['summaries'][2]['nativeDeliveryCount']=2
        self.probe('missing-moves',mutate)
    def test_F05_worker_beyond_action_deadline_rejects(self):
        def mutate(native,rows,directory):
            for r in rows:
                if r['kind']=='worker-send' and r.get('actionId')=='P01-1':r['workerAfter']=r['workerBefore']+999999
        self.probe('worker-overrun',mutate)
    def test_worker_send_intervals_cannot_overlap_within_action(self):
        def mutate(native,rows,directory):
            sends=[r for r in rows if r['kind']=='worker-send' and r.get('actionId')=='P01-1'];sends[0]['workerAfter']=sends[1]['workerBefore']+1
        self.probe('overlapping-worker-intervals',mutate)
    def test_positive_worker_send_intervals_allow_equal_boundary(self):
        def mutate(native,rows,directory):
            sends=[r for r in rows if r['kind']=='worker-send' and r.get('actionId')=='P01-1'];sends[0]['workerAfter']=sends[1]['workerBefore']
        self.probe('equal-worker-interval-boundary',mutate,accepted=True)
    def test_positive_coalesced_history_uses_raw_local_offset(self):
        result=self.probe('coalesced',lambda n,r,d:coalesce(n,r),accepted=True)
        self.assertEqual(result['requestedEvents'],124);self.assertEqual(result['observedActivityEntries'],117)
    def test_positive_dropped_intermediate_moves_with_endpoint(self):
        def mutate(native,rows,directory):
            rows[:]=[r for r in rows if not(r['kind'] in ('activity-entry','activity-exit') and r.get('actionId')=='P03-1' and r['event']['action']==2 and r['event']['eventTime']!=r['event']['downTime']+640)];native['summaries'][2]['nativeDeliveryCount']=3
        self.probe('dropped-intermediate',mutate,accepted=True)
    def test_positive_zero_gap_consecutive_action_intervals(self):
        def mutate(native,rows,directory):
            summary=native['summaries'][1];shift=native['summaries'][0]['actionEndUptime']-summary['actionStartUptime'];action='P02-1'
            for key in ('actionStartUptime','actionEndUptime'):summary[key]+=shift
            sequence_path=directory/'pointer-sequence-2.json';sequence=json.loads(sequence_path.read_text())
            for key in ('actionStartUptime','downTime'):sequence[key]+=shift
            data=json.dumps(sequence).encode();sequence_path.write_bytes(data);digest=hashlib.sha256(data).hexdigest();native['exports'][sequence_path.name]={'bytes':len(data),'sha256':digest}
            for row in rows:
                if row.get('actionId')!=action:continue
                if row['kind']=='sealed-sequence':row['sha256']=digest
                for key in ('scheduledUptime','workerBefore','workerAfter','workerIndependentUptime','uptime','actionStartUptime','actionEndUptime'):
                    if key in row:row[key]+=shift
                if 'event' in row:
                    for key in ('downTime','eventTime'):row['event'][key]+=shift
                    for sample in row['event']['history']:sample['eventTime']+=shift
            self.assertEqual(summary['actionStartUptime'],native['summaries'][0]['actionEndUptime'])
        self.probe('zero-gap-action-interval',mutate,accepted=True)
    def test_history_mapped_coordinate_and_pressure_reject(self):
        for key,value in (('x',999999),('y',-999999),('pressure',0)):
            def mutate(native,rows,directory,key=key,value=value):
                coalesce(native,rows)
                for r in rows:
                    if r['kind'] in ('activity-entry','activity-exit') and r.get('actionId')=='P03-1' and r['event']['history']:r['event']['history'][0]['pointers'][0][key]=value
            self.probe('history-'+key,mutate)
    def test_history_reordering_and_duplicate_times_reject(self):
        for mode in ('reverse','duplicate','future'):
            def mutate(native,rows,directory,mode=mode):
                coalesce(native,rows)
                for r in rows:
                    if r['kind'] in ('activity-entry','activity-exit') and r.get('actionId')=='P03-1' and r['event']['history']:
                        h=r['event']['history']
                        if mode=='reverse':h.reverse()
                        elif mode=='duplicate':h[1]['eventTime']=h[0]['eventTime']
                        else:h[-1]['eventTime']=r['event']['eventTime']
            self.probe('history-'+mode,mutate)
    def test_activity_entry_and_exit_outside_interval_reject(self):
        for kind,key in (('activity-entry','workerIndependentUptime'),('activity-exit','uptime')):
            def mutate(native,rows,directory,kind=kind,key=key):
                next(r for r in rows if r['kind']==kind and r.get('actionId')=='P01-1')[key]=999999
            self.probe('time-'+kind,mutate)
    def test_action_interval_missing_mismatch_and_overrun_reject(self):
        for mode in ('missing','mismatch','overrun'):
            def mutate(native,rows,directory,mode=mode):
                if mode=='missing':rows[:]=[r for r in rows if not(r['kind']=='action-interval' and r['actionId']=='P01-1')]
                elif mode=='mismatch':native['summaries'][0]['durationMilliseconds']+=1
                else:
                    summary=native['summaries'][0];summary['actionEndUptime']=summary['actionStartUptime']+5001;summary['durationMilliseconds']=5001
                    interval=next(r for r in rows if r['kind']=='action-interval' and r['actionId']=='P01-1')
                    for k in ('actionEndUptime','durationMilliseconds'):interval[k]=summary[k]
            self.probe('interval-'+mode,mutate)
    def test_duplicate_acknowledgement_still_rejects(self):self.probe('duplicate-ack',lambda n,r,d:n['summaries'][0].update(commitAcknowledgementCount='2'))
    def test_saved_G03_packet_hash_still_rejects(self):
        def mutate(native,rows,directory):
            path=directory/'pointer-retirement-after.json';data=json.loads(path.read_text());data['savedPacketSHA256']='f'*64;raw=json.dumps(data).encode();path.write_bytes(raw);native['exports'][path.name]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        self.probe('saved-G03-hash',mutate)
    def test_runtime_output_rejects_escape_reuse_and_symlink(self):
        for attempt in ('../runtime-1','runtime/runtime-1','runtime-0','runtime-01','/tmp/runtime-1'):self.assertRaises(ValueError,common.runtime_directory,attempt)
        container=WORK/'runtime-policy';container.mkdir();existing=container/'runtime-1';existing.mkdir()
        with patch.object(common,'RUNTIME',container):self.assertRaises(ValueError,common.runtime_directory,'runtime-1')
        link=WORK/'runtime-policy-link';link.symlink_to(container,target_is_directory=True)
        try:
            with patch.object(common,'RUNTIME',link):self.assertRaises(ValueError,common.runtime_directory,'runtime-2')
        finally:link.unlink()


class HostPacketPolicyTests(unittest.TestCase):
    def test_exact_host_membership_excludes_only_designated_runtime(self):
        import check_packet
        root=WORK/'packet-policy-root';here=root/'verification/android-pointer-oracle-repair';here.mkdir(parents=True);(root/'docs').mkdir();(root/'docs/android-pointer-oracle-repair.md').write_text('bound document')
        (here/'host.json').write_text('{}');(here/'packet-seal.json').write_text('{}');(here/'nested').mkdir();(here/'nested/artifact-seal.json').write_text('{}');runtime=here/'runtime';runtime.mkdir();(runtime/'runtime-1').mkdir();(runtime/'runtime-1/receipt.json').write_text('{}')
        with patch.object(common,'HERE',here),patch.object(common,'ROOT',root):
            bound=check_packet.files();self.assertEqual(len(bound),3);self.assertIn('verification/android-pointer-oracle-repair/nested/artifact-seal.json',bound)
            (runtime/'runtime-1/receipt.json').write_text('{"runtimeChanged":true}');self.assertEqual(check_packet.files(),bound)
            (here/'additional.json').write_text('{}');self.assertNotEqual(check_packet.files(),bound)
    def test_host_packet_symlink_is_rejected_even_in_excluded_runtime(self):
        import check_packet
        root=WORK/'packet-symlink-root';here=root/'verification/android-pointer-oracle-repair';here.mkdir(parents=True);(root/'docs').mkdir();(root/'docs/android-pointer-oracle-repair.md').write_text('bound document');runtime=here/'runtime';runtime.mkdir();target=here/'host.json';target.write_text('{}');link=runtime/'escape';link.symlink_to(target)
        try:
            with patch.object(common,'HERE',here),patch.object(common,'ROOT',root):self.assertRaises(ValueError,check_packet.files)
        finally:link.unlink()

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--work',required=True);args=parser.parse_args();WORK=Path(args.work);RUNNER,_,_=run.load_runner()
    suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(c) for c in (HostTests,RepairTests,HostPacketPolicyTests)]);result=unittest.TextTestRunner(verbosity=2).run(suite);raise SystemExit(0 if result.wasSuccessful() else 1)
