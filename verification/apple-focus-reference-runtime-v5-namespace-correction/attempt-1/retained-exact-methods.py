def test_011_derived_modules_compile_without_tools(self):
        for name,raw in self.derived.items():
            if name.endswith('.py'):compile(raw,name,'exec')

def test_015_fresh_root_selection_requires_now_and_packet(self):
        f=self.fixture()
        with self.assertRaises(ValueError):i.validate_root(f['root'],'b'*64)
        f['root']['selectedAtUTC']='2000-01-01T00:00:00+00:00'
        with self.assertRaises(ValueError):i.validate_root(f['root'],fresh=True)
        f['root']['selectedAtUTC']=datetime.datetime.now(datetime.timezone.utc).isoformat();self.assertEqual(i.validate_root(f['root'],fresh=True),f['root'])

def test_021_archive_round_trip_and_corruption_rejected(self):
        h=prepare.helpers();rows=prepare.manifest(self.derived)
        with tempfile.TemporaryDirectory(prefix='archive-control-',dir=prepare.BASE) as temp:
            base=Path(temp);h.materialize(base/'selected',rows,self.derived);arc=h.archive_sources(base/'sources.tar.gz',base/'selected',rows);self.assertEqual(h.archive_payload(base/'sources.tar.gz',rows,arc['archive']['sha256'],'selected/'),self.derived)
            with (base/'sources.tar.gz').open('ab') as stream:stream.write(b'corrupt')
            with self.assertRaises(ValueError):h.archive_payload(base/'sources.tar.gz',rows,arc['archive']['sha256'],'selected/')

def test_023_adapter_actual_tool_capture_and_one_shot_binding(self):
        f=self.fixture();namespace={'select_command':lambda *args:None,'run_observed':lambda *args:None,'require':prepare.require,'Path':Path,'sha':prepare.sha,'_selected':{'called':True,'session':f['session'],'argv':f['observer']['argv']}}
        with mock.patch.dict(sys.modules,{'reference_contract':self.classifier,'auxiliary_inventory':self.auxiliary}):
            exec(compile((prepare.BASE/'adapter.py').read_bytes(),'adapter.py','exec'),namespace)
        namespace['configure_root'](f['root'])
        with self.assertRaises(ValueError):namespace['configure_root'](f['root'])
        # Reading stale receipt fields cannot mint a selected execution capability.
        namespace['_selected']['called']=False
        with self.assertRaises(ValueError):namespace['capture_official'](None,None,None,None)

def test_024_dispatch_refuses_unreviewed_packet_before_native_import(self):
        with mock.patch.object(prepare,'verify',return_value={'packetSHA256':'a'*64}):
            with self.assertRaises(ValueError):prepare.dispatch('b'*64,'absent','c'*64)
