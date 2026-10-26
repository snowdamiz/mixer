"""Read-only frozen closure verification. No network, source import or execution."""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parent
repo=root.parents[1]
seal=json.loads((root/"seal.json").read_text())
for row in seal["members"]:
 data=(repo/row["path"]).read_bytes()
 assert len(data)==row["bytes"] and hashlib.sha256(data).hexdigest()==row["sha256"],row["path"]
ledger=json.loads((root/"operation-ledger.json").read_text())
for owner,total in ledger["totals"].items():
 assert total["scalar_groups"]==(total["scalars"]+15)//16
 assert total["groups"]==total["scalar_groups"]+total["copy_groups"]<=total["cap"]
groups=json.loads((root/"group-assignment.json").read_text())["static_upper_inventory_assignment"]
assert len({g["id"] for g in groups})==len(groups)
seen=set()
for g in groups:
 ids=g.get("scalar_events",[g["copy_event"]] if "copy_event" in g else [])
 assert len(ids)<=16 and g.get("copy_bytes",0)<=128
 assert not seen.intersection(ids);seen.update(ids)
assert not seal["source_accounting_accepted"] and not seal["root_selected"]
print(json.dumps(dict(status="frozen source-only proposal verified",members=len(seal["members"]),
 member_bytes=sum(x["bytes"] for x in seal["members"]),seal_sha256=hashlib.sha256((root/"seal.json").read_bytes()).hexdigest(),
 affected_group_bounds=ledger["totals"],compiler_or_runtime_execution=False),indent=2,sort_keys=True))
