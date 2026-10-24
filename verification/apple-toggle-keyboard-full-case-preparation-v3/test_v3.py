"""Actual composed allocation-failure controls; native/Popen boundaries are mocked."""
import contextlib
import json
import os
import pathlib
import shutil
import stat
import unittest
from unittest import mock
import composition as c
import test_v2 as repair
import workspace_ownership

class AllocationControls(unittest.TestCase):
    setUp=repair.ReportingCleanup.setUp
    restore=repair.ReportingCleanup.restore
    official=repair.ReportingCleanup.official
    def allocation_case(self,stage='chmod',cleanup='none',replacement=None):
        products=self.root/'build/Build/Products';products.mkdir(parents=True)
        (products/'synthetic.xctestrun').write_bytes(c.h.plistlib.dumps(dict(MixerToggleUITests=dict(EnvironmentVariables={},TestingEnvironmentVariables={}))))
        factory=c.h.tempfile.mkdtemp;real_chmod=c.h.pathlib.Path.chmod;real_stat=c.h.pathlib.Path.stat;real_resolve=c.h.pathlib.Path.resolve
        real_write=c.h.write;real_server=c.h.server_for;real_thread=c.h.threading.Thread;real_rmdir=workspace_ownership.os.rmdir;real_os_stat=workspace_ownership.os.stat;real_remove=c.h.remove_ephemeral;real_rmtree=c.h.shutil.rmtree
        created=[];servers=[];threads=[];rmdir_calls=[];recursive=[];rmdir_returned=[False]
        first=OSError('synthetic first workspace '+stage+' failure')
        protected=self.root/'protected-fixture';protected.mkdir();marker=protected/'keep.txt';marker.write_bytes(b'protected synthetic fixture\n')
        mode=stat.S_IMODE(protected.stat().st_mode)
        identity_report_failed=[False]
        def allocated(path):return path.name.startswith(workspace_ownership.PREFIX)
        def temporary(*args,**kwargs):
            path=factory(prefix=workspace_ownership.PREFIX,dir=self.root);created.append(pathlib.Path(path));return path
        def replace(path):
            if replacement=='nonempty':(path/'keep.txt').write_bytes(b'owned test marker retained\n')
            elif replacement=='symlink':real_rmdir(path);path.symlink_to(protected,target_is_directory=True)
            elif replacement=='file':real_rmdir(path);path.write_bytes(b'owned replacement file retained\n')
            elif replacement=='absent':real_rmdir(path)
        def chmod(path,*args,**kwargs):
            if allocated(path) and stage=='chmod':replace(path);raise first
            return real_chmod(path,*args,**kwargs)
        def path_stat(path,*args,**kwargs):
            if allocated(path) and stage=='stat':raise first
            return real_stat(path,*args,**kwargs)
        def resolve(path,*args,**kwargs):
            if allocated(path) and stage=='resolve':raise first
            return real_resolve(path,*args,**kwargs)
        def write(path,value):
            if stage=='identity-report' and path.name=='lifecycle.json' and 'ephemeralWorkspace' in value and not identity_report_failed[0]:
                identity_report_failed[0]=True;raise first
            return real_write(path,value)
        def rmdir(name,*args,**kwargs):
            if kwargs.get('dir_fd') is not None and str(name).startswith(workspace_ownership.PREFIX):
                rmdir_calls.append(str(name))
                if cleanup=='rmdir-fail':raise OSError('synthetic narrow rmdir failure')
                if cleanup=='rmdir-noop':return None
                result=real_rmdir(name,*args,**kwargs);rmdir_returned[0]=True;return result
            return real_rmdir(name,*args,**kwargs)
        def os_stat(name,*args,**kwargs):
            if kwargs.get('dir_fd') is not None and str(name).startswith(workspace_ownership.PREFIX) and cleanup=='absence-stat-fail' and rmdir_returned[0]:
                raise OSError('synthetic absence stat failure')
            return real_os_stat(name,*args,**kwargs)
        def remove(life):
            if cleanup=='identity-remove-noop':return None
            return real_remove(life)
        def rmtree(path,*args,**kwargs):
            if created and pathlib.Path(path)==created[0]:recursive.append(str(path))
            return real_rmtree(path,*args,**kwargs)
        def server(bridge):value=real_server(bridge);servers.append(value);return value
        def thread(*args,**kwargs):value=real_thread(*args,**kwargs);threads.append(value);return value
        patches=[mock.patch.object(c.h,'verify',return_value=dict(sealSHA256='synthetic-reviewed')),mock.patch.object(c.h,'frontends',return_value=[]),mock.patch.object(c.h.packet,'restore'),mock.patch.object(c.h.packet,'verify_installed',return_value={}),mock.patch.object(c.h,'validate_container',return_value=self.docs),mock.patch.object(c.h.tempfile,'mkdtemp',side_effect=temporary),mock.patch.object(c.h.tempfile,'gettempdir',return_value=str(self.root)),mock.patch.object(c.h.pathlib.Path,'chmod',chmod),mock.patch.object(c.h.pathlib.Path,'stat',path_stat),mock.patch.object(c.h.pathlib.Path,'resolve',resolve),mock.patch.object(c.h,'write',side_effect=write),mock.patch.object(c.h,'server_for',side_effect=server),mock.patch.object(c.h.threading,'Thread',side_effect=thread),mock.patch.object(workspace_ownership.os,'rmdir',side_effect=rmdir),mock.patch.object(workspace_ownership.os,'stat',side_effect=os_stat),mock.patch.object(c.h,'remove_ephemeral',side_effect=remove),mock.patch.object(c.h.shutil,'rmtree',side_effect=rmtree)]
        with contextlib.ExitStack() as stack:
            for patch in patches:stack.enter_context(patch)
            real_rmtree(self.runtime)
            with self.assertRaises(OSError) as caught:c.h.run('synthetic-reviewed','interaction')
            self.assertIs(caught.exception,first)
        self.assertEqual(len(created),1);path=created[0];life=c.h.last_lifecycle
        rows=life['cleanupResults'];self.assertEqual(len(rows),5)
        workspace=next(row for row in rows if row['resource']=='ephemeral-capability-workspace-removal')
        blocked=cleanup in ['rmdir-fail','rmdir-noop','absence-stat-fail','identity-remove-noop'] or replacement in ['nonempty','symlink','file']
        self.assertEqual(workspace['passed'],not blocked)
        self.assertTrue(all(row['passed'] for row in rows if row is not workspace))
        self.assertEqual(life['cleanedUp'],not blocked)
        self.assertEqual(life['ephemeralAllocation']['path'],str(path))
        self.assertEqual(life['ephemeralAllocation']['identityComplete'],stage=='identity-report')
        self.assertFalse(any(thread.is_alive() for thread in threads));self.assertTrue(all(server.fileno()==-1 for server in servers));self.assertIsNone(self.device)
        self.assertIs(c.h.last_outcome.first,first);self.assertFalse(c.h.last_runtime_summary['runPassed'])
        if stage!='identity-report':self.assertEqual(recursive,[])
        if not blocked:self.assertFalse(path.exists());self.assertTrue(life['ephemeralWorkspaceAbsent'])
        else:self.assertFalse(life['ephemeralWorkspaceAbsent'])
        self.assertEqual(marker.read_bytes(),b'protected synthetic fixture\n');self.assertEqual(stat.S_IMODE(protected.stat().st_mode),mode)
        if replacement=='nonempty':self.assertEqual((path/'keep.txt').read_bytes(),b'owned test marker retained\n')
        if replacement=='symlink':self.assertTrue(path.is_symlink())
        if replacement=='file':self.assertEqual(path.read_bytes(),b'owned replacement file retained\n')
        retained=dict(schema=1,stage=stage,cleanupFault=cleanup,replacement=replacement,firstExceptionObjectRetained=True,allocation=life['ephemeralAllocation'],identityMissing='ephemeralWorkspace' not in life,cleanupResults=rows,absenceFlag=life['ephemeralWorkspaceAbsent'],allocatedEntryStillPresent=path.exists() or path.is_symlink(),narrowRmdirCalls=rmdir_calls,recursiveRemovalOfAllocatedPath=recursive,protectedFixturePreserved=True,threadsJoined=True,serversClosed=True,ownedSyntheticDeviceAbsent=True,nativeExecuted=False)
        (self.root/'allocation-control.json').write_text(json.dumps(retained,sort_keys=True,indent=2)+'\n')
        # Fault fixtures are owned by this test. Recover only known test entries
        # after recording their failed cleanup, using unlink + empty rmdir.
        if path.is_symlink() or path.is_file():path.unlink()
        elif path.exists():
            if replacement=='nonempty':(path/'keep.txt').unlink()
            path.rmdir()
        self.assertFalse(path.exists() or path.is_symlink())
        (self.root/'allocation-recovery.json').write_text(json.dumps(dict(schema=1,ownedAllocationAbsent=True,fixtureRecoveryOnly=True,recursiveRecovery=False,nativeExecuted=False),sort_keys=True,indent=2)+'\n')
    def test_exact_review_chmod_failure_removes_empty_allocation(self):self.allocation_case('chmod')
    def test_stat_failure_removes_empty_allocation(self):self.allocation_case('stat')
    def test_resolve_failure_removes_empty_allocation(self):self.allocation_case('resolve')
    def test_identity_receipt_failure_uses_verified_cleanup_and_proves_absence(self):self.allocation_case('identity-report')
    def test_narrow_rmdir_failure_reports_failed_cleanup(self):self.allocation_case(cleanup='rmdir-fail')
    def test_narrow_rmdir_noop_cannot_false_pass_absence(self):self.allocation_case(cleanup='rmdir-noop')
    def test_absence_stat_failure_remains_failed_after_real_removal(self):self.allocation_case(cleanup='absence-stat-fail')
    def test_verified_cleanup_noop_cannot_false_pass_absence(self):self.allocation_case('identity-report',cleanup='identity-remove-noop')
    def test_nonempty_preidentity_directory_is_preserved_without_recursion(self):self.allocation_case(replacement='nonempty')
    def test_symlink_preidentity_entry_preserves_target(self):self.allocation_case(replacement='symlink')
    def test_file_preidentity_entry_is_preserved(self):self.allocation_case(replacement='file')
    def test_already_absent_allocation_passes_only_after_positive_absence_check(self):self.allocation_case(replacement='absent')

if __name__=='__main__':unittest.main(verbosity=2)
