#!/usr/bin/env python3
"""Bounded owned-workspace allocation failure at the new finally boundary."""
import contextlib
import json
import pathlib
import shutil
import sys
import unittest
from unittest import mock
import repair_controls as repair
c=repair.c

class Allocation(repair.Cleanup):
    def test_ephemeral_chmod_failure_does_not_false_pass_removal(self):
        products=self.root/'build/Build/Products';products.mkdir(parents=True)
        (products/'synthetic.xctestrun').write_bytes(c.h.plistlib.dumps(dict(MixerToggleUITests=dict(EnvironmentVariables={},TestingEnvironmentVariables={}))))
        factory=c.h.tempfile.mkdtemp;chmod=c.h.pathlib.Path.chmod;servers=[];threads=[];created=[]
        sf=c.h.server_for;tf=c.h.threading.Thread
        first=OSError('independent fresh workspace chmod failure')
        def temporary(*a,**kw):
            path=factory(prefix='mixer-toggle-xctest-',dir=self.root);created.append(pathlib.Path(path));return path
        def fail_chmod(path,*a,**kw):
            if path.name.startswith('mixer-toggle-xctest-'):raise first
            return chmod(path,*a,**kw)
        def server(bridge):
            value=sf(bridge);servers.append(value);return value
        def thread(*a,**kw):
            value=tf(*a,**kw);threads.append(value);return value
        patches=[mock.patch.object(c.h,'verify',return_value=dict(sealSHA256='review-synthetic')),mock.patch.object(c.h.packet,'restore'),mock.patch.object(c.h.packet,'verify_installed',return_value={}),mock.patch.object(c.h,'validate_container',return_value=self.docs),mock.patch.object(c.h.tempfile,'mkdtemp',side_effect=temporary),mock.patch.object(c.h.tempfile,'gettempdir',return_value=str(self.root)),mock.patch.object(c.h.pathlib.Path,'chmod',fail_chmod),mock.patch.object(c.h,'server_for',side_effect=server),mock.patch.object(c.h.threading,'Thread',side_effect=thread)]
        try:
            with contextlib.ExitStack() as stack:
                for patch in patches:stack.enter_context(patch)
                shutil.rmtree(self.runtime)
                with self.assertRaises(OSError) as caught:c.h.run('review-synthetic','interaction')
                self.assertIs(caught.exception,first)
            self.assertEqual(len(created),1)
            life=c.h.last_lifecycle
            row=next(row for row in life['cleanupResults'] if row['resource']=='ephemeral-capability-workspace-removal')
            reproduced=created[0].is_dir() and row['passed'] is True and 'ephemeralWorkspace' not in life
            repaired=not created[0].exists() and row['passed'] is True and 'ephemeralWorkspace' not in life and life['ephemeralWorkspaceAbsent'] is True
            repair.support.write('allocation-failure.json',dict(reproduced=reproduced,repaired=repaired,firstExceptionObjectRetained=True,
                allocatedWorkspace=str(created[0]),allocatedWorkspaceStillPresent=created[0].is_dir(),
                workspaceIdentityMissing='ephemeralWorkspace' not in life,cleanupResults=life['cleanupResults'],
                removalReportedPassed=row['passed'],threadsJoined=all(not t.is_alive() for t in threads),
                serversClosed=all(s.fileno()==-1 for s in servers),ownedSyntheticDeviceAbsent=self.device is None,nativeExecuted=False))
            self.assertFalse(reproduced);self.assertTrue(repaired)
        finally:
            for s in servers:
                if any(t.is_alive() for t in threads):s.shutdown()
                s.server_close()
            for t in threads:t.join(timeout=3);self.assertFalse(t.is_alive())

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([Allocation('test_ephemeral_chmod_failure_does_not_false_pass_removal')]))
    raise SystemExit(0 if result.wasSuccessful() else 1)
