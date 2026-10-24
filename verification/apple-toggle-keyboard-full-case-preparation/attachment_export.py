"""One immutable attachment-export attempt per selected test command."""
import hashlib
import json
import os
import pathlib
import stat


def publish_first_receipt(receipt,data):
    fd=os.open(receipt,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as stream:
        stream.write(data);stream.flush();os.fsync(stream.fileno())
    directory=os.open(receipt.parent,os.O_RDONLY)
    try:os.fsync(directory)
    finally:os.close(directory)


def exporting_commands(base, h, output_base, settings_passed, inventory):
    """Compose from the bound canonical Commands, never from inherited exporters."""
    if base.__name__ != 'Commands' or pathlib.Path(base.run.__code__.co_filename).name != 'harness.py' or base.__bases__ != (object,):
        raise ValueError('Canonical bound Commands required at composition boundary')
    h.attachment_export_state=dict(receiptDurablyCommitted=False,failure=None)
    class FullCaseExportingCommands(base):
        _full_case_export_owner = True
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._selected_exports = set()
        def run(self, argv, *args, **kwargs):
            values = [str(value) for value in argv]
            selected = len(values) > 1 and values[0] == str(h.DEVELOPER/'usr/bin/xcodebuild') and values[1] == 'test-without-building'
            try:
                return super().run(argv, *args, **kwargs)
            finally:
                if selected:
                    key = tuple(values)
                    if key not in self._selected_exports:
                        self._selected_exports.add(key)
                        self.export_owned_attachments(values)
                        self.export_official_results(values)
        def export_official_results(self, argv):
            # The unchanged harness checks strict evidence immediately after the
            # selected command returns. Export official terminal proof before it.
            try:
                if argv.count('-resultBundlePath') != 1: return
                result = pathlib.Path(argv[argv.index('-resultBundlePath')+1])
                retained = json.loads((output_base/'runtime/attachment-export.json').read_bytes())
                h.require(retained.get('ownedResultPath') == str(result), 'Official result export requires the same validated owned bundle')
                for kind in ['summary','tests']:
                    code, output, _ = super().run(['/usr/bin/xcrun','xcresulttool','get','test-results',kind,'--path',str(result)],check=False)
                    if code == 0:
                        h.write(output_base/('runtime/xctest-'+kind+'.json'),json.loads(output))
            except BaseException as error:
                try: self.record('official-result-export-unavailable',dict(type=type(error).__name__,message=self.redact(str(error))))
                except BaseException: pass
        def export_owned_attachments(self, argv):
            record = dict(schema='mixer.apple-toggle.keyboard-attachment-export.1', passed=False,
                          settingsSetupObservedPassed=False, scope='Official owned xcresult attachments only; export failure never suppresses inherited cleanup')
            receipt = output_base/'runtime/attachment-export.json'
            try:
                runtime = output_base/'runtime'
                h.require(h.RUN_DIR == runtime and runtime.resolve() == runtime and self.output == runtime/'commands.json', 'Only fixed keyboard runtime export permitted')
                # A prior receipt is immutable, including a failed attempt. Never
                # adopt an arbitrary existing directory or replace first success.
                if receipt.exists() or receipt.is_symlink():
                    raise ValueError('Immutable export attempt already retained')
                h.require(argv.count('-resultBundlePath') == 1, 'Exactly one owned result path required')
                result = pathlib.Path(argv[argv.index('-resultBundlePath')+1])
                life = json.loads((runtime/'lifecycle.json').read_bytes()); workspace=life['ephemeralWorkspace']
                parent = pathlib.Path(workspace['path']); info=parent.lstat()
                h.require(parent.resolve() == parent and result.parent == parent and result.name == 'session.xcresult' and result.resolve() == result, 'Owned canonical result bundle required')
                h.require(stat.S_ISDIR(info.st_mode) and not parent.is_symlink() and info.st_dev == workspace['device'] and info.st_ino == workspace['inode'] and info.st_uid == workspace['uid'] and stat.S_IMODE(info.st_mode) == 0o700, 'Owned result workspace identity changed')
                h.require(result.is_dir() and not result.is_symlink(), 'Owned result bundle unavailable after test command')
                record['ownedResultPath'] = str(result)
                output = runtime/'attachments'
                h.require(not output.exists() and not output.is_symlink() and output.parent == runtime, 'Fresh fixed attachment output required')
                command=['/usr/bin/xcrun','xcresulttool','export','attachments','--path',str(result),'--output-path',str(output)]
                code, stdout, stderr = super().run(command, timeout=30, check=False)
                files = inventory(output) if output.is_dir() else {}
                record.update(argv=command,timeoutSeconds=30,exitCode=code,files=files,
                    artifactInventorySHA256=hashlib.sha256(h.json_bytes(files)).hexdigest(),
                    settingsSetupObservedPassed=settings_passed(output,files))
                record['passed'] = code == 0 and bool(files) and 'manifest.json' in files
            except BaseException as error:
                record['failure'] = dict(type=type(error).__name__,message=self.redact(str(error)))
                try: self.record('attachment-export-failure',record['failure'])
                except BaseException: pass
            # O_EXCL preserves the first receipt even if an accidental second
            # owner reaches this point. Failure remains visible in Commands.
            try:
                data=h.json_bytes(record)+b'\n'
                publish_first_receipt(receipt,data)
                h.attachment_export_state.update(receiptDurablyCommitted=True,failure=None)
            except BaseException as error:
                # A duplicate attempt cannot revoke the first successful receipt.
                # Any first-attempt persistence error blocks live qualification
                # even if intended JSON bytes happen to be readable.
                if not h.attachment_export_state['receiptDurablyCommitted']:
                    h.attachment_export_state['failure']=dict(type=type(error).__name__,message=self.redact(str(error)))
                try: self.record('attachment-export-receipt-unavailable',dict(type=type(error).__name__,message=self.redact(str(error))))
                except BaseException: pass
    return FullCaseExportingCommands
