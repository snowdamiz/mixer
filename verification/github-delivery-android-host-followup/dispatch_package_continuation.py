"""One package-only dispatch from independently pinned root evidence; no axis authority."""
import sys
sys.dont_write_bytecode = True
assert sys.flags.isolated == 1 and sys.flags.no_site == 1 and sys.flags.optimize == 0
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('android_host_followup_package_continuation_common', Path(__file__).with_name('selection_common_package_continuation.py'))
common = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = common
spec.loader.exec_module(common)
common.dispatch_manual('package')
