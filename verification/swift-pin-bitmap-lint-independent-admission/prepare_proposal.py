#!/usr/bin/env python3
"""Copy only the already reviewed command helper and generic data functions."""
import offline
offline.install()
import ast
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OLD = ROOT / "verification/swift-pin-bitmap-format-lint-host-correction"
old = (OLD / "bounded_commands.py").read_text()
new = old.replace("MAX_COMMANDS=5", "MAX_COMMANDS=6").replace("seconds in (30,300)", "seconds in (30,60,300,600)").replace("CHILD_SECONDS=300", "CHILD_SECONDS=600")
(HERE / "bounded_commands.py").write_text(new)
(HERE / "bounded_commands.diff").write_text("".join(difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True), fromfile="reviewed/bounded_commands.py", tofile="proposal/bounded_commands.py")))
source = (OLD / "admit.py").read_text()
names = {"digest", "closure", "file_row", "inventory", "exact_source", "format_evidence", "cargo_configs_absent", "lint_evidence", "component_evidence"}
functions = {n.name: ast.get_source_segment(source, n) for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name in names}
text = "\n\n".join(functions.values()).replace("outside the four overlays", "outside the fifteen overlays") + "\n"
(HERE / "generic_source.py.fragment").write_text(text)
admission = (HERE / "admit.py").read_text()
marker = "# Generic source/evidence helpers copied from the reviewed prior admission are\n# inserted below by the source-only preparation script, before main executes.\n"
assert admission.count(marker) == 1
start = admission.index(marker) + len(marker)
end = admission.index("\ndef main():", start)
(HERE / "admit.py").write_text(admission[:start] + "\n\n" + text + "\n" + admission[end:])
(HERE / "reuse.json").write_text(json.dumps({"schema": 1, "helperPreimage": {"path": str((OLD / "bounded_commands.py").relative_to(ROOT)), "sha256": hashlib.sha256(old.encode()).hexdigest()}, "genericPreimage": {"path": str((OLD / "admit.py").relative_to(ROOT)), "sha256": hashlib.sha256(source.encode()).hexdigest()}, "genericFunctions": sorted(names), "helperChanges": ["MAX_COMMANDS 5 to 6", "accepted finite seconds add 60 and 600", "unused CHILD_SECONDS constant 300 to 600"], "processLifecycleImplementationChanged": False}, sort_keys=True, indent=2) + "\n")
