def adapter_namespace(self,f,output):
    namespace={'__file__':str(output/'selected/join_support.py')}
    with mock.patch.dict(sys.modules,{'reference_contract':self.classifier,'auxiliary_inventory':self.auxiliary}):
        exec(compile(self.derived['join_support.py'],namespace['__file__'],'exec'),namespace)
    namespace['configure_root'](f['root'])
    session=output/'runtime/session';session.mkdir(parents=True,mode=0o700);session.chmod(0o700)
    result=session/'session.xcresult';result.mkdir()
    f['session']=session;f['observer']['argv']=i.command_argv(f['root'],session);f['observer']['resultBundle']=str(result)
    observer=session/'command-observer';observer.mkdir();(observer/'observer.json').write_bytes(i.stable(f['observer']))
    namespace['_selected']={'called':True,'session':session,'argv':f['observer']['argv'],'sessionIdentity':namespace['path_identity'](session,0o700),'resultIdentity':namespace['path_identity'](result),'rootSHA256':i.digest(i.stable(f['root']))}
    folder=output/'runtime/attachments';folder.mkdir()
    for role,value in f['values'].items():(folder/(role+'.json')).write_bytes(i.stable(value))
    (folder/'manifest.json').write_bytes(i.stable(f['manifest']))
    retained={'ownedResultPath':str(result),'exitCode':0,'passed':True,'files':{p.name:{'bytes':p.stat().st_size,'sha256':i.digest(p.read_bytes())} for p in folder.iterdir()}}
    (output/'runtime/attachment-export.json').write_bytes(i.stable(retained))
    capture_folder=output/'runtime/captures';capture_folder.mkdir()
    for role,name in [('begin','0001-begin.json'),('before','0001-before-1.json'),('after','0001-after-1.json'),('witness','0001-keyboard-witness-1.json')]:
        if role in f['captures']:(capture_folder/name).write_bytes(i.stable(f['captures'][role]))
    self.summary_writer(types.SimpleNamespace(output=capture_folder,generation=1,current={'case':i.CASE},allowed_cases={i.CASE},verdicts=[f['values']['verdict']] if 'after' in f['captures'] else [],failures=[],last_observation=f['captures'].get('before')))
    calls=[]
    def invoke(command_object,argv,**kwargs):
        calls.append((argv,kwargs))
        self.assertEqual(argv[:4],['/usr/bin/xcrun','xcresulttool','get','test-results'])
        self.assertEqual(argv[-2:],['--path',str(result)])
        return 0,i.stable(f[argv[4]]).decode(),'actual fake tool stderr'
    return namespace,invoke,calls,types.SimpleNamespace(RUN_DIR=output/'runtime')
