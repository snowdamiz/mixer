"""Exact selected actual ZIP data phase only. No subject analyzer import."""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import types
import json
HERE = Path(__file__).resolve().parent
BASE = HERE / "local/actual-40854344723"


def own(path, name):
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), "exec", dont_inherit=True), module.__dict__)
    return module


guard = own(HERE / "guarded_inspector.py", "actual_archive_guard")
guard_record = guard.install_guards()
data = guard.load_data_module(HERE / "audit_data.py", "actual_archive_data")
report = {"schema": 1, "scope": "exact selected actual archive data validation only; no subject analyzer import",
          "command": list(sys.orig_argv), "python": {"executable": sys.executable, "version": sys.version},
          "guard": guard_record, "subject_analyzer_imports": 0, "new_network_requests": 0,
          "sources": [{"path": p.name, **data.identity(p.read_bytes())}
                      for p in (Path(__file__), HERE / "audit_data.py", HERE / "guarded_inspector.py")]}
try:
    binding = data.validate_binding(data.strict_json(data.read_regular(BASE / "binding.json", BASE)))
    raw = data.read_regular(BASE / "artifact.zip", BASE, maximum=4194304)
    data.need(len(raw) == binding["artifact_size_bytes"] and data.identity(raw)["sha256"] == binding["artifact_digest"].removeprefix("sha256:"), "actual artifact byte binding")
    files, inventory = data.inspect_zip(raw)
    (BASE / "archive-inventory.json").open("x").write(json.dumps(inventory, sort_keys=True, indent=2) + "\n")
    target = BASE / "extracted"
    target.mkdir(exist_ok=False)
    for name, content in files.items():
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(content)
    for row in inventory["members"]:
        data.need(data.identity(data.read_regular(target / row["path"], target)) == {"bytes": row["bytes"], "sha256": row["sha256"]}, "extracted member differs")
    report.update(status="validated-and-extracted-exact-dedicated-artifact", archive=inventory["archive"],
                  member_files=inventory["files"], member_map_sha256=inventory["member_map_sha256"],
                  extraction_rehashed=True, retained_raw_zip_unchanged=data.identity(data.read_regular(BASE / "artifact.zip", BASE)) == inventory["archive"])
except BaseException as error:
    report.update(status="refused-archive-data-phase-retained", error=type(error).__name__ + ": " + str(error)[:2000])
(BASE / "archive-data-review.json").open("x").write(json.dumps(report, sort_keys=True, indent=2) + "\n")
print(json.dumps({k: report.get(k) for k in ("status", "member_files", "error")}))
if "error" in report:
    raise data.Refusal(report["error"])
