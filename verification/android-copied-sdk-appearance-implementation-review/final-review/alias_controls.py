from runner import HERE,run,identity
import shutil,json,hashlib,os
base=HERE/'scratch/consumer-release';scratch=HERE/'scratch';results=[]
for case in ['kelvin-base','kelvin-selector','unrelated-unicode']:
    for entry in ['swift','python']:
        root=scratch/('alias-'+case+'-'+entry);shutil.copytree(base,root);sdk=root/'Generated/MixerSDK'
        if case=='kelvin-base':(sdk/'Package.swift').rename(sdk/'Pac\u212aage.swift')
        else:(sdk/('Pac\u212aage@swift-6.4.swift' if case=='kelvin-selector' else 'caf\u00e9.txt')).write_text('inert named entry\n')
        names=[p.name for p in sdk.iterdir()];nonascii=[{'name':n,'codepoints':[ord(c) for c in n],'utf8_hex':n.encode().hex()} for n in names if not n.isascii()]
        assert len(nonascii)==1
        actual=sdk/nonascii[0]['name'];lookup=sdk/('Package.swift' if case=='kelvin-base' else 'Package@swift-6.4.swift' if case=='kelvin-selector' else 'cafe\u0301.txt')
        alias_observed=lookup.exists() and (actual.lstat().st_dev,actual.lstat().st_ino)==(lookup.lstat().st_dev,lookup.lstat().st_ino)
        # This fixture has no excluded/cache names, symlinks or special files.
        records=[(p.relative_to(sdk).as_posix(),identity(p.read_bytes())['sha256']) for p in sdk.rglob('*') if p.is_file()]
        lock=json.loads((root/'mixer.lock').read_text());lock['sdkDigest']=hashlib.sha256(''.join(p+'\0'+h+'\n' for p,h in sorted(records)).encode()).hexdigest();(root/'mixer.lock').write_text(json.dumps(lock))
        args=[scratch/'harness-build/out/Products/Release/ReviewDriver','verify',root] if entry=='swift' else [os.sys.executable,'-B',root/'Generated/MixerAndroid/android-build.py','build',root]
        try:
            text=run('alias-'+case+'-'+entry,args,allowed=(1,23),timeout=20)
            assert 'Non-ASCII' in text or 'non-ASCII' in text
            assert not (root/'.mixer').exists()
            results.append({'case':case,'entrypoint':entry,'actual_nonascii_entries':nonascii,'ordinary_lookup':lookup.name,'ordinary_lookup_same_device_inode':alias_observed,'independent_sdk_lock':lock['sdkDigest'],'refused_before_output':True})
        finally:shutil.rmtree(root)
(HERE/'alias-control-results.json').write_text(json.dumps({'schema':1,'count':len(results),'checks':results},indent=2,ensure_ascii=True)+'\n')
