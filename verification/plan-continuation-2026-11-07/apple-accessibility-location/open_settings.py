"""Open the existing public permission pane; do not modify permissions."""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import plistlib

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
resource = Path('/System/Library/ExtensionKit/Extensions/SecurityPrivacyExtension.appex/Contents/Resources/Localizable.loctable')
raw = resource.read_bytes()
label = plistlib.loads(raw)['en']['ACCESSIBILITY']
system = plistlib.loads(Path('/System/Library/CoreServices/SystemVersion.plist').read_bytes())
spec = importlib.util.spec_from_file_location('settings_commands', ROOT / 'scripts/ci/check-android-generated-java.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
out = HERE / 'commands'
out.mkdir()
commands = runner.Commands(out, dict(os.environ), seconds=30, command_seconds=15)
receipt = {'schema': 1, 'recordedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'system': system, 'resource': str(resource), 'resourceSHA256': hashlib.sha256(raw).hexdigest(),
           'resourceKey': 'en.ACCESSIBILITY', 'displayedPermissionName': label,
           'permissionMutation': False, 'simulatorOrTestStarted': False,
           'systemSettingsRetainedForUser': True}
try:
    commands.run('open-public-permission-pane', ['/usr/bin/open',
        'x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility'])
    receipt['openURLRequestAccepted'] = True
    receipt['visiblePaneIndependentlyVerified'] = False
finally:
    receipt['terminalCommandCustody'] = commands.custody_terminal()
    (HERE / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))
