"""Run one exact independent method; writes only inside this correction packet."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent
NAMES = (
    "test_closed_retained_wrapper_cannot_reauthorize_reused_descriptor",
    "test_close_failure_still_accounts_for_and_closes_remaining_owned_descriptors",
    "test_preclose_error_does_not_forget_known_open_descriptor",
)


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("old", "corrected") or sys.argv[2] not in NAMES:
        raise ValueError("closed witness argv")
    variant, name = sys.argv[1:]
    spec = importlib.util.spec_from_file_location("unchanged_witness", ROOT / variant / "test_independent.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    suite = unittest.TestSuite([module.Independent(name)])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    state = module.p.ownership_snapshot() if hasattr(module.p, "ownership_snapshot") else {"legacy_open_fd_view":len(module.p.OPEN_FDS)}
    output = {"schema":1,"variant":variant,"method":name,"methods":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),"skips":len(result.skipped),"observations":module.OBSERVATIONS,"ownership_at_process_exit":state,"source_unchanged":True,"process_exit_is_not_ambiguous_close_resolution":True}
    (ROOT / "raw-witnesses" / (variant + "-" + name + ".json")).write_text(json.dumps(output, indent=2, sort_keys=True)+"\n")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
