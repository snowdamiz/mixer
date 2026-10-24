#!/usr/bin/env python3
"""Immediately adjacent allocation/absence controls of the actual V3 runner."""
import contextlib
import json
import pathlib
import shutil
import unittest
from unittest import mock
import allocation_probe as original
repair=original.repair
c=original.c
import workspace_ownership as ownership

class Adjacent(original.Allocation):
    def exercise(self,stage):
        products=self.root/'build/Build/Products';products.mkdir(parents=True)
        (products/'synthetic.xctestrun').write_bytes(c.h.plistlib.dumps(dict(MixerToggleUITests=dict(EnvironmentVariables={},TestingEnvironmentVariables={}))))
        factory=c.h.tempfile.mkdtemp;chmod=pathlib.Path.chmod;pathstat=pathlib.Path.stat;resolve=pathlib.Path.resolve
        sf=c.h.server_for;tf=c.h.threading.Thread;write=c.h.write;rmdir=ownership.os.rmdir;osstat=ownership.os.stat
        created=[];servers=[];threads=[];deleted=[False];report_failed=[False];recursive=[];rmtree=c.h.shutil.rmtree
        protected=self.root/'protected';protected.mkdir();marker=protected/'keep';marker.write_bytes(b'independent protected fixture\n')
        first=OSError('independent allocation '+stage+' failure')
        target=lambda path:path.name.startswith(ownership.PREFIX)
        def temporary(*a,**kw):
            path=factory(prefix=ownership.PREFIX,dir=self.root);created.append(pathlib.Path(path));return path
        def fault_chmod(path,*a,**kw):
            if target(path) and stage in ['rmdir-noop','absence-check','nonempty','symlink','file']:
                if stage=='nonempty':(path/'owned-marker').write_bytes(b'preserve\n')
                elif stage=='symlink':rmdir(path);path.symlink_to(protected,target_is_directory=True)
                elif stage=='file':rmdir(path);path.write_bytes(b'preserve file\n')
                raise first
            return chmod(path,*a,**kw)
        def fault_stat(path,*a,**kw):
            if target(path) and stage=='stat':raise first
            return pathstat(path,*a,**kw)
        def fault_resolve(path,*a,**kw):
            if target(path) and stage=='resolve':raise first
            return resolve(path,*a,**kw)
        def fault_write(path,value):
            if stage=='identity-report' and path.name=='lifecycle.json' and 'ephemeralWorkspace' in value and not report_failed[0]:report_failed[0]=True;raise first
            return write(path,value)
        def fault_rmdir(name,*a,**kw):
            if kw.get('dir_fd') is not None and str(name).startswith(ownership.PREFIX):
                if stage=='rmdir-noop':return None
                result=rmdir(name,*a,**kw);deleted[0]=True;return result
            return rmdir(name,*a,**kw)
        def fault_osstat(name,*a,**kw):
            if kw.get('dir_fd') is not None and str(name).startswith(ownership.PREFIX) and deleted[0] and stage=='absence-check':raise OSError('independent absence proof unavailable')
            return osstat(name,*a,**kw)
        def observed_rmtree(path,*a,**kw):
            if created and pathlib.Path(path)==created[0]:recursive.append(str(path))
            return rmtree(path,*a,**kw)
        def server(bridge):s=sf(bridge);servers.append(s);return s
        def thread(*a,**kw):t=tf(*a,**kw);threads.append(t);return t
        patches=[mock.patch.object(c.h,'verify',return_value=dict(sealSHA256='review-synthetic')),mock.patch.object(c.h.packet,'restore'),mock.patch.object(c.h.packet,'verify_installed',return_value={}),mock.patch.object(c.h,'validate_container',return_value=self.docs),mock.patch.object(c.h.tempfile,'mkdtemp',side_effect=temporary),mock.patch.object(c.h.tempfile,'gettempdir',return_value=str(self.root)),mock.patch.object(pathlib.Path,'chmod',fault_chmod),mock.patch.object(pathlib.Path,'stat',fault_stat),mock.patch.object(pathlib.Path,'resolve',fault_resolve),mock.patch.object(c.h,'write',side_effect=fault_write),mock.patch.object(ownership.os,'rmdir',side_effect=fault_rmdir),mock.patch.object(ownership.os,'stat',side_effect=fault_osstat),mock.patch.object(c.h.shutil,'rmtree',side_effect=observed_rmtree),mock.patch.object(c.h,'server_for',side_effect=server),mock.patch.object(c.h.threading,'Thread',side_effect=thread)]
        try:
            with contextlib.ExitStack() as stack:
                for p in patches:stack.enter_context(p)
                rmtree(self.runtime)
                with self.assertRaises(OSError) as caught:c.h.run('review-synthetic','interaction')
                self.assertIs(caught.exception,first)
            self.assertEqual(len(created),1);path=created[0];life=c.h.last_lifecycle;rows=life['cleanupResults']
            self.assertEqual(len(rows),5);row=next(r for r in rows if r['resource']=='ephemeral-capability-workspace-removal')
            success=stage in ['stat','resolve','identity-report']
            self.assertEqual(row['passed'],success);self.assertEqual(life['ephemeralWorkspaceAbsent'],success)
            self.assertTrue(all(r['passed'] for r in rows if r is not row));self.assertEqual(life['cleanedUp'],success)
            self.assertEqual(life['ephemeralAllocation']['path'],str(path));self.assertEqual(life['ephemeralAllocation']['identityComplete'],stage=='identity-report')
            self.assertTrue(all(not t.is_alive() for t in threads));self.assertTrue(all(s.fileno()==-1 for s in servers));self.assertIsNone(self.device)
            self.assertIs(c.h.last_outcome.first,first);self.assertFalse(c.h.last_runtime_summary['runPassed'])
            if stage!='identity-report':self.assertEqual(recursive,[])
            present=path.exists() or path.is_symlink()
            self.assertEqual(present,stage in ['rmdir-noop','nonempty','symlink','file'])
            self.assertEqual(marker.read_bytes(),b'independent protected fixture\n')
            if stage=='nonempty':self.assertEqual((path/'owned-marker').read_bytes(),b'preserve\n')
            if stage=='symlink':self.assertTrue(path.is_symlink())
            if stage=='file':self.assertEqual(path.read_bytes(),b'preserve file\n')
            repair.support.write('adjacent-'+stage+'.json',dict(stage=stage,firstExceptionObjectRetained=True,cleanupResults=rows,
                absenceReported=life['ephemeralWorkspaceAbsent'],allocatedEntryPresent=present,allocation=life['ephemeralAllocation'],
                protectedFixturePreserved=True,recursiveAllocatedRemoval=recursive,threadsJoined=True,serversClosed=True,ownedSyntheticDeviceAbsent=True,nativeExecuted=False))
        finally:
            for s in servers:
                if any(t.is_alive() for t in threads):s.shutdown()
                s.server_close()
            for t in threads:t.join(timeout=3);self.assertFalse(t.is_alive())
            # Recover only the exact controlled fault fixture, after retaining
            # its failed cleanup receipt. Never recurse on an unverified path.
            for path in created:
                if path.is_symlink() or path.is_file():path.unlink()
                elif path.exists():
                    if stage=='nonempty':(path/'owned-marker').unlink()
                    path.rmdir()
            self.assertTrue(all(not p.exists() and not p.is_symlink() for p in created))
            repair.support.write('adjacent-'+stage+'-recovery.json',dict(ownedFaultEntriesAbsent=True,threadsJoined=True,serversClosed=True,recursiveRecovery=False,nativeExecuted=False))

for stage in ['stat','resolve','identity-report','rmdir-noop','absence-check','nonempty','symlink','file']:
    def test(self,stage=stage):self.exercise(stage)
    setattr(Adjacent,'test_adjacent_'+stage.replace('-','_'),test)

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(Adjacent(name) for name in dir(Adjacent) if name.startswith('test_adjacent_')))
    raise SystemExit(0 if result.wasSuccessful() else 1)
