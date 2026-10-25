"""Archive failed owned fixtures, then remove only explicitly marked review scratch."""
import datetime
import hashlib
import json
import pathlib
import shutil
import tarfile

OWN=pathlib.Path(__file__).resolve().parent
ROOT=OWN.parents[1]
rows=[]
scratch_root=OWN/"scratch"
if scratch_root.exists():
    for scratch in sorted(scratch_root.iterdir()):
        assert scratch.is_dir() and not scratch.is_symlink()
        marker=json.loads((scratch/"ownership.json").read_bytes())
        assert marker["owner"]=="/root/swift_analyzer_framing_review"
        assert pathlib.Path(marker["path"]).resolve()==scratch.resolve()
        members=[]
        for path in sorted(scratch.rglob("*")):
            assert not path.is_symlink()
            if path.is_file():
                members.append({"path":str(path.relative_to(scratch)),"bytes":path.stat().st_size,
                                "sha256":hashlib.sha256(path.read_bytes()).hexdigest()})
        retained_inputs=any(path.is_dir() for path in scratch.iterdir())
        attempt=json.loads((OWN/"commands"/scratch.name/"result.json").read_bytes())
        archive=None
        if retained_inputs:
            destination=OWN/"commands"/scratch.name/"retained-owned-inputs.tar.gz"
            assert not destination.exists()
            with tarfile.open(destination,"w:gz") as out:
                for path in sorted(scratch.iterdir()):
                    if path.is_dir():
                        out.add(path,arcname=path.name,recursive=True)
            archive={"path":str(destination.relative_to(ROOT)),"bytes":destination.stat().st_size,
                     "sha256":hashlib.sha256(destination.read_bytes()).hexdigest()}
        shutil.rmtree(scratch)
        rows.append({"scratch":str(scratch.relative_to(ROOT)),"members":members,
                     "retained_owned_inputs_archive":archive,"attempt_passed":attempt["passed"],"removed":not scratch.exists()})
    scratch_root.rmdir()
cache=OWN/"__pycache__"
if cache.exists():
    assert cache.is_dir() and not cache.is_symlink()
    shutil.rmtree(cache)
receipt={"schema":1,"at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"owned_scratch":rows,
         "all_synchronous_children_returned_before_cleanup":True,
         "native_capture_target_or_unrelated_processes_started_or_queried":False,
         "other_projects_touched":False,"scratch_root_absent":not scratch_root.exists()}
(OWN/"cleanup.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print(json.dumps({"owned_scratch_removed":len(rows),"retained_input_archives":sum(row["retained_owned_inputs_archive"] is not None for row in rows)}))
