from runner import HERE,run
import shutil,json,os
scratch=HERE/'scratch';base=scratch/'consumer-release';sentinel=scratch/'sentinels';hit=scratch/'tool-hit';results=[]
for mode in ['debug','release']:
    exe=scratch/'harness-build/out/Products'/mode.capitalize()/'ReviewDriver'
    for context in ['config-only','lock-only','requested-only']:
        for operation in ['verify','host-build','host-test','ios','android','export']:
            if context=='requested-only' and operation not in ['android']:continue
            root=scratch/('or-'+mode+'-'+context+'-'+operation);shutil.copytree(base,root);dest=scratch/('or-export-'+mode+'-'+context+'-'+operation)
            config=json.loads((root/'mixer.yml').read_text());lock=json.loads((root/'mixer.lock').read_text())
            if context=='config-only':lock.pop('android')
            elif context=='requested-only':config['targets']=['ios'];lock.pop('android')
            else:
                config['targets']=['ios'];asset=root/'Generated/MixerAndroid/app/assets/MixerAppearanceV2/descriptor.json';asset.write_bytes(asset.read_bytes()+b' ')
            (root/'mixer.yml').write_text(json.dumps(config));(root/'mixer.lock').write_text(json.dumps(lock));hit.unlink(missing_ok=True)
            if operation=='verify':argv=[exe,'verify',root]
            elif operation=='export':argv=[exe,'export',root,dest]
            else:argv=[exe,'run',root,{'host-build':'host','host-test':'host','ios':'ios','android':'android'}[operation],'test' if operation=='host-test' else 'build']
            try:
                text=run('or-'+mode+'-'+context+'-'+operation,argv,env={'PATH':str(sentinel)+os.pathsep+os.environ.get('PATH','')},timeout=20,allowed=(23,))
                assert 'android.sdk-' in text and not hit.exists() and not dest.exists() and not (root/'.mixer').exists()
                results.append({'mode':mode,'context':context,'operation':operation,'refused_before_tools_or_output':True})
            finally:shutil.rmtree(root)
(HERE/'or-context-results.json').write_text(json.dumps({'schema':1,'checks':results,'count':len(results)},indent=2)+'\n')
