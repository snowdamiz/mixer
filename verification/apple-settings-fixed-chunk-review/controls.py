#!/usr/bin/env python3
"""Fresh independent controls using actual receiver/store; fixture data is shared."""
import base64,copy,hashlib,json,math,pathlib,struct,unittest,zlib
import fixtures as f
import settings_telemetry as t
import durable_settings as d
import replay
B=pathlib.Path(__file__).resolve().parent
ROWS=[]
def snap(s):return copy.deepcopy({k:v for k,v in vars(s).items() if k not in ['persist','persist_file','transaction','now']})
def memory(module=t,transaction=None):
    records=[];files=[];clock=[100.0]
    session=module.Session(lambda *a:records.append(a),lambda *a:files.append(a),129.0,now=lambda:clock[0],token='01234567-0123-4123-8123-0123456789ab',transaction=transaction)
    return session,records,files,clock
def start(s):return s.request(dict(kind='start',case=t.CASE,uptime=10.0,chunkBytes=4992))
def seed(data,form='ax',transaction=None):
    s,j,p,c=memory(transaction=transaction);start(s)
    slot='settings-0001-'+form
    s.pending=[slot];s.uploads[slot]=dict(format=form,bytes=len(data),sha256=t.sha(data),count=math.ceil(len(data)/4992),parts=[],complete=False)
    return s,j,p,c,slot
def fragment(s,slot,data,index):
    item=s.uploads[slot]
    return dict(kind='chunk',case=t.CASE,generation=s.token,sequence=s.sequence+1,uptime=10.1,slot=slot,index=index,count=item['count'],bytes=item['bytes'],sha256=item['sha256'],data=base64.b64encode(data[index*4992:(index+1)*4992]).decode())
def png(size):
    def block(kind,payload):return struct.pack('>I',len(payload))+kind+payload+struct.pack('>I',zlib.crc32(kind+payload)&0xffffffff)
    base=f.image();amount=size-len(base)-12;assert amount>=0
    return base[:-12]+block(b'tEXt',(bytes(range(256))*(amount//256+1))[:amount])+base[-12:]
def closed(s):
    v=s.summary()
    return v['setupObservationSatisfied'] and v['terminationMarkers']==['terminate-before','terminate-after'] and v['completionMarkers']==['test-case-finished','suite-finished','bundle-finished'] and not v['persistenceRetirementPending'] and not v['persistenceUncertain']
class Review(unittest.TestCase):
    def reject(self,s,j,p,r,name):
        state=snap(s);journals=copy.deepcopy(j);files=copy.deepcopy(p)
        with self.assertRaises((ValueError,TypeError,KeyError,UnicodeError,OverflowError,OSError)):s.request(r)
        self.assertEqual(state,snap(s));self.assertEqual(journals,j);self.assertEqual(files,p)
        ROWS.append(dict(case=name,rejected=True,cursorUnchanged=True))
    def test_start_and_old_new(self):
        for raw in ['{}','{"chunkBytes":null}','{"chunkBytes":true}','{"chunkBytes":false}','{"chunkBytes":"4992"}','{"chunkBytes":4992.0}','{"chunkBytes":4.992e3}','{"chunkBytes":3072}','{"chunkBytes":4993}','{"chunkBytes":-1}','{"chunkBytes":[]}']:
            s,j,p,c=memory();r=dict(kind='start',case=t.CASE,uptime=10.0);r.update(json.loads(raw));self.reject(s,j,p,r,'start:'+raw)
        s,j,p,c=memory();reply=start(s);self.assertEqual(type(reply['chunkBytes']),int);self.assertEqual(reply['chunkBytes'],4992)
        self.reject(s,j,p,dict(kind='start',case=t.CASE,uptime=10.0,chunkBytes=4992),'duplicate-start')
        namespace={'__name__':'frozen_review_control'};exec(compile((B/'frozen-receiver.py').read_bytes(),str(B/'frozen-receiver.py'),'exec'),namespace)
        old=type('Old',(),namespace)
        s,j,p,c=memory(old);self.reject(s,j,p,dict(kind='start',case=t.CASE,uptime=10.0,chunkBytes=4992),'new-client-old-host')
        s,j,p,c=memory(old);s.request(dict(kind='start',case=t.CASE,uptime=10.0));self.assertEqual(s.requests,1)
        for uptime in [0.0,math.ulp(0.0),float.fromhex('0x1.fffffffffffffp+1023')]:
            s,j,p,c=memory();reply=s.request(dict(kind='start',case=t.CASE,uptime=uptime,chunkBytes=4992))
            self.assertEqual(s.start_runner,uptime);ROWS.append(dict(case='finite-uptime-admission',uptime=uptime,accepted=True))
    def test_actual_descriptor_boundaries(self):
        for form,sizes in [('ax',[1,4991,4992,4993,9984,14976,200000]),('png',[4991,4992,4993,9984,14976,2000000])]:
            for n in sizes:
                flow=f.Flow();data=b'Q'*n if form=='ax' else png(n)
                if form=='png':flow.routes();record,payloads=flow.observe('before-switch',upload=False)
                else:record,payloads=flow.observe('route-search',index=0,upload=False)
                payloads[form]=data;record['files']={k:dict(bytes=len(v),sha256=t.sha(v)) for k,v in payloads.items()}
                flow.send(record);slot=f"settings-{record['sequence']:04d}-{form}"
                self.assertEqual(flow.bridge.settings.uploads[slot]['count'],math.ceil(n/4992))
                flow.upload(payloads);file=flow.bridge.output/(slot+('.txt' if form=='ax' else '.png'))
                self.assertEqual(file.read_bytes(),data);self.assertEqual(replay.replay(flow.bridge.output),flow.bridge.settings.summary())
                rows=[json.loads(p.read_bytes())['record'] for p in sorted(flow.bridge.output.glob('0000-settings-*.json'))]
                parts=[r for r in rows if r['kind']=='chunk' and r['slot']==slot]
                self.assertEqual([r['index'] for r in parts],list(range(math.ceil(n/4992))))
                self.assertEqual([len(base64.b64decode(r['data'])) for r in parts],[min(4992,n-i*4992) for i in range(len(parts))])
                self.assertTrue(all(base64.b64encode(base64.b64decode(r['data'])).decode()==r['data'] for r in parts))
                ROWS.append(dict(case='descriptor-admission',format=form,bytes=n,chunks=len(parts),lastBytes=len(base64.b64decode(parts[-1]['data'])),sha256=t.sha(data),publishedExact=True,durableReplayExact=True))
    def test_mixed_malformed_partial_and_digest(self):
        mutations={'old3072':{'data':base64.b64encode(b'A'*3072).decode()},'mixed4096':{'data':base64.b64encode(b'A'*4096).decode()},'empty':{'data':''},'whitespace':{'data':base64.b64encode(b'A'*4992).decode()+'\n'},'pad':{'data':base64.b64encode(b'A'*4992).decode()+'='},'oversized':{'data':base64.b64encode(b'A'*4993).decode()},'foreign-generation':{'generation':'foreign'},'reordered':{'index':1},'index401':{'index':401},'bool-index':{'index':False},'count':{'count':1},'float-count':{'count':2.0},'slot':{'slot':'settings-0002-ax'},'descriptor-bytes':{'bytes':4992},'sha':{'sha256':'0'*64},'per-chunk-format':{'chunkBytes':4992}}
        data=b'A'*4993
        for name,change in mutations.items():
            s,j,p,c,slot=seed(data);r=fragment(s,slot,data,0);r.update(change);self.reject(s,j,p,r,name)
        s,j,p,c,slot=seed(data);first=fragment(s,slot,data,0);s.request(first)
        self.assertFalse(s.summary()['settingsEvidenceComplete']);self.assertEqual(p,[])
        r=copy.deepcopy(first);r['sequence']=s.sequence+1;self.reject(s,j,p,r,'duplicate-fragment')
        for encoded in ['QR==','QQ','QQ===','Q Q==','QQ==\n',base64.b64encode(b'A'*3072).decode()]:
            r=fragment(s,slot,data,1);r['data']=encoded;self.reject(s,j,p,r,'final-canonical:'+encoded[:16])
        s.request(fragment(s,slot,data,1));self.assertEqual(p[0][2],data)
        for payload,form in [(b'\xff','ax'),(b'\x00','ax'),(b'not PNG','png'),(f.image()[:-1]+b'X','png')]:
            s,j,p,c,slot=seed(payload,form);self.reject(s,j,p,fragment(s,slot,payload,0),'malformed-'+form)
        s,j,p,c,slot=seed(b'A');s.uploads[slot]['sha256']='0'*64;self.reject(s,j,p,fragment(s,slot,b'A',0),'full-digest-mismatch')
    def test_full_proof_and_semantic_rejections(self):
        for initial in ['0','1']:
            flow=f.Flow();flow.finish(initial);self.assertTrue(closed(flow.bridge.settings))
            self.assertEqual(replay.replay(flow.bridge.output),flow.bridge.settings.summary())
            ROWS.append(dict(case='full-strict-proof',initial=initial,action='tap' if initial=='0' else 'no-tap',strict=True,applicationCases=0,native=False))
        source=[json.loads(p.read_bytes()) for p in sorted(flow.bridge.output.glob('0000-settings-*.json'))]
        def accepts(rows):
            clock=[100.0];s=t.Session(lambda *a:None,lambda *a:None,500,now=lambda:clock[0],token=flow.bridge.settings.token)
            try:
                for row in rows:clock[0]=row['receivedUptime'];s.request(row['record'])
                return closed(s)
            except (ValueError,KeyError,TypeError,UnicodeError):return False
        self.assertTrue(accepts(source))
        specs=[('route-search',('routeWitness','target','label'),'foreign'),('route-tap',('detail','searchSequence'),999),('route-tap',('detail','target','identifier'),'foreign'),('route-opened',('routeWitness','destination','identifier'),'foreign'),('before-switch',('switchWitness','leafCount'),2),('before-switch',('switchWitness','leaf','value'),'0'),('switch-action',('detail','beforeSequence'),999),('switch-action',('detail','parent','observedUptime'),0),('switch-action',('detail','deadlineUptime'),99),('terminal',('snapshot','value'),'0'),('terminal',('captureStartedUptime',),0),('terminal',('switchWitness','hitPoint','x'),0)]
        for stage,path,bad in specs:
            rows=copy.deepcopy(source);row=next(x['record'] for x in rows if x['record'].get('stage')==stage);target=row
            for k in path[:-1]:target=target[k]
            target[path[-1]]=bad;self.assertFalse(accepts(rows),(stage,path));ROWS.append(dict(case='strict-semantic',stage=stage,path=list(path),rejected=True))
        for stage in ['settings-launched','route-search','route-tap','route-opened','before-switch','switch-action','after-switch','terminal','terminate-before','terminate-after','test-case-finished','suite-finished','bundle-finished']:
            rows=copy.deepcopy(source);index=next(i for i,x in enumerate(rows) if x['record'].get('stage')==stage);del rows[index]
            self.assertFalse(accepts(rows),stage);ROWS.append(dict(case='missing-required-phase',stage=stage,rejected=True))
        file=next(flow.bridge.output.glob('settings-*-ax.txt'));raw=file.read_bytes();file.write_bytes(b'corruption')
        with self.assertRaisesRegex(ValueError,'Durable AX/PNG differs'):replay.replay(flow.bridge.output)
        file.write_bytes(raw)
        retry=f.Flow();retry.mark('settings-launched')
        for index in range(3):
            if index==0:retry.observe('route-search',index=index,attempt=0)
            retry.observe('route-search',index=index,attempt=1 if index==0 else 0);retry.tap(index);retry.observe('route-opened',index=index)
        retry.observe('before-switch');retry.action();retry.observe('after-switch',value='1');retry.observe('terminal',value='1');retry.completion()
        self.assertTrue(closed(retry.bridge.settings));self.assertEqual(replay.replay(retry.bridge.output),retry.bridge.settings.summary())
        ROWS.append(dict(case='full-strict-proof-with-retry',routeAXCaptures=7,strict=True,native=False))
    def test_enabled_window_exact_boundary(self):
        for outside in [False,True]:
            flow=f.Flow();flow.before();flow.action();flow.observe('after-switch',value='0')
            bound=flow.bridge.settings.observation_deadline
            observed=math.nextafter(bound,math.inf) if outside else bound
            record,payloads=flow.observe('terminal',value='1',upload=False)
            record['captureStartedUptime']=observed-.001;record['captureFinishedUptime']=observed+.001;record['uptime']=observed+.002
            record['snapshot']['observedUptime']=observed;record['switchWitness']['leaf']['observedUptime']=observed+.0001
            flow.runner=record['uptime'];flow.send(record);flow.upload(payloads);flow.completion()
            self.assertEqual(closed(flow.bridge.settings),not outside)
            ROWS.append(dict(case='enabled-window-boundary',nextFloatOutside=outside,strictSatisfied=not outside,actualAnchoredWindow=3.0))
    def test_deadlines_limits_and_origin_preconditions(self):
        for host in [129.0,math.nextafter(129.0,math.inf)]:
            s,j,p,c=memory();start(s);c[0]=host;self.reject(s,j,p,dict(kind='mark',case=t.CASE,generation=s.token,sequence=1,uptime=11,stage='settings-launched',detail={}),'host-deadline')
        s,j,p,c=memory();start(s);self.reject(s,j,p,dict(kind='mark',case=t.CASE,generation=s.token,sequence=1,uptime=math.nextafter(39.0,math.inf),stage='settings-launched',detail={}),'runner-29s')
        for kind in ['requests','events','uploads','total']:
            flow=f.Flow();r,_=flow.observe('route-search',index=0,upload=False)
            if kind=='requests':flow.bridge.settings.requests=2500
            if kind=='events':flow.bridge.settings.events=[{}]*100
            if kind=='uploads':flow.bridge.settings.uploads={str(i):{} for i in range(32)}
            if kind=='total':flow.bridge.settings.total=7000000
            before=snap(flow.bridge.settings)
            with self.assertRaises(ValueError):flow.send(r)
            self.assertEqual(before,snap(flow.bridge.settings));ROWS.append(dict(case='limit:'+kind,rejected=True,cursorUnchanged=True))
        flow=f.Flow();flow.before();flow.action();flow.observe('after-switch',value='1')
        for _ in range(40):flow.observe('poll',value='1')
        r,_=flow.observe('poll',value='1',upload=False)
        with self.assertRaisesRegex(ValueError,'Poll stage/count'):flow.send(r)
        for mode in ['current','generation']:
            flow=f.Flow();setattr(flow.bridge,mode,object() if mode=='current' else 1)
            with self.assertRaisesRegex(ValueError,'before app begin only'):flow.mark('settings-launched')
    def test_real_transaction_recovery_and_irrevocable_commit(self):
        def setup():
            flow=f.Flow();record,payloads=flow.observe('route-search',index=0,upload=False);payloads['ax']=b'Q'*4993;record['files']['ax']=dict(bytes=4993,sha256=t.sha(payloads['ax']));flow.send(record)
            slot=flow.bridge.settings.pending[0];s=flow.bridge.settings;s.request(fragment(s,slot,payloads['ax'],0));return flow,s,slot,payloads['ax']
        for role in ['payload','journal','publication-directory']:
            flow,s,slot,data=setup();store=flow.bridge.persistence;state=snap(s);io=store.io
            class Fault(d.DiskIO):
                def write(self,path,payload,at):
                    if at==role:raise OSError('independent precommit fault '+at)
                    return super().write(path,payload,at)
                def sync(self,path,at):
                    if at==role:raise OSError('independent precommit fault '+at)
                    return super().sync(path,at)
            store.io=Fault()
            with self.assertRaises(OSError):s.request(fragment(s,slot,data,1))
            self.assertEqual(snap(s),state);self.assertFalse(d.unresolved(flow.bridge.output));self.assertFalse((flow.bridge.output/(slot+'.txt')).exists())
            store.io=io;s.request(fragment(s,slot,data,1));self.assertEqual((flow.bridge.output/(slot+'.txt')).read_bytes(),data)
            ROWS.append(dict(case='transaction-rollback',role=role,sameCursorRetry=True,exactPublished=True))
        flow,s,slot,data=setup();store=flow.bridge.persistence;io=store.io;before=s.sequence
        class Retirement(d.DiskIO):
            def unlink(self,path,at):
                if at=='guard-clear':raise OSError('independent retirement fault')
                return super().unlink(path,at)
        store.io=Retirement();reply=s.request(fragment(s,slot,data,1));self.assertTrue(reply['accepted']);self.assertEqual(s.sequence,before+1);self.assertTrue(store.retirement_pending);self.assertTrue(d.unresolved(flow.bridge.output))
        with self.assertRaises(d.PersistenceUncertain):replay.replay(flow.bridge.output)
        self.assertEqual((flow.bridge.output/(slot+'.txt')).read_bytes(),data)
        store.io=io;self.assertTrue(store.resolve_retirement());self.assertFalse(d.unresolved(flow.bridge.output))
        ROWS.append(dict(case='irrevocable-commit-retirement',acceptedCursorAdvanced=True,exactPublished=True,guardBlocksReplay=True,retirementResolved=True))
        flow,s,slot,data=setup();store=flow.bridge.persistence;state=snap(s)
        class Uncertain(d.DiskIO):
            def sync(self,path,at):
                if at in ['publication-directory','rollback-directory']:raise OSError('independent terminal fault '+at)
                return super().sync(path,at)
        store.io=Uncertain()
        with self.assertRaises(d.PersistenceUncertain):s.request(fragment(s,slot,data,1))
        self.assertEqual(snap(s),state);self.assertTrue(store.uncertain);self.assertTrue(d.unresolved(flow.bridge.output))
        with self.assertRaises(d.PersistenceUncertain):replay.replay(flow.bridge.output)
        ROWS.append(dict(case='rollback-terminal-uncertainty',cursorUnchanged=True,guardPresent=True,replayRejected=True))
if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Review))
    (B/'receiver-controls.json').write_text(json.dumps(dict(passed=result.wasSuccessful(),methods=result.testsRun,controls=ROWS,sharedFixtureSHA256=hashlib.sha256((B/'fixtures.py').read_bytes()).hexdigest(),directDispatchAdapter=True,listener=False,network=False,native=False),indent=2,sort_keys=True)+'\n')
    raise SystemExit(not result.wasSuccessful())
