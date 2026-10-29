"""One package allowance only; immediate zero visible runs remains submitted/pending without replay."""
import sys
sys.dont_write_bytecode = True
assert sys.flags.isolated == 1 and sys.flags.no_site == 1 and sys.flags.optimize == 0
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('android_host_followup_delivery_common', Path(__file__).with_name('selection_common_delivery_followup.py'))
common = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = common
spec.loader.exec_module(common)
common.dispatch_manual('package')
