#!/usr/bin/env python3
"""Read retained CI artifacts only; execute no packaged product or test source."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
COMMIT = "9f15b11fe07194f28f620c5814a305519643cc56"
RUN = 40239406899


def digest(data):
    return hashlib.sha256(data).hexdigest()


def committed(path):
    return subprocess.check_output(["git", "show", f"{COMMIT}:{path}"], cwd=ROOT)


def review():
    artifacts = json.loads((BASE / "artifacts.json").read_bytes())["artifacts"]
    assert len(artifacts) == 2
    archives = {}
    for prefix, local in (("phoenix-foundation-", "phoenix-artifact.zip"),
                          ("callback-source-inputs-", "callback-source-inputs.zip")):
        metadata = next(a for a in artifacts if a["name"] == prefix + COMMIT)
        assert metadata["workflow_run"]["head_sha"] == COMMIT
        assert metadata["workflow_run"]["id"] == RUN and not metadata["expired"]
        raw = (BASE / local).read_bytes()
        assert "sha256:" + digest(raw) == metadata["digest"]
        assert len(raw) == metadata["size_in_bytes"]
        archives[local] = metadata

    with zipfile.ZipFile(BASE / "phoenix-artifact.zip") as broad, \
            zipfile.ZipFile(BASE / "callback-source-inputs.zip") as hidden:
        names = broad.namelist()
        assert len(names) == len(set(names))
        hidden_names = hidden.namelist()
        assert len(hidden_names) == len(set(hidden_names)) == 2
        candidates = [p for p in names if p.startswith("_temp/browser-callback/")
                      and p.endswith("/receipt.json")]
        assert len(candidates) == 1
        member = candidates[0]
        prefix = member.removesuffix("receipt.json")
        raw = broad.read(member)
        selected = json.loads(raw)
        assert selected["revision"] == COMMIT and selected["platform"] == "linux"
        assert selected["success"] and selected["passed"]
        assert selected["sources"] == selected["sources_after"]
        assert selected["dependencies"] == selected["dependencies_after"]
        assert selected["source_changes"] == [] and selected["dependency_changes"] is False
        assert selected["source_tree_sha256"] == selected["source_tree_after_sha256"]
        assert selected["dependency_tree_sha256"] == selected["dependency_tree_after_sha256"]
        assert all(selected["cleanup"].values())
        assert all(all(v.values()) for v in selected["beam_cleanup"].values())

        hidden_sources = {}
        for path in (".github/workflows/hosted.yml", "hosted/.tool-versions"):
            matches = [n for n in hidden_names if n.endswith("inputs/" + path)]
            assert len(matches) == 1, (path, hidden_names)
            hidden_sources["inputs/" + path] = hidden.read(matches[0])
        assert set(hidden_names) == {
            next(n for n in hidden_names if n.endswith(k)) for k in hidden_sources
        }

        def selected_bytes(relative):
            if prefix + relative in names:
                assert relative not in hidden_sources
                return broad.read(prefix + relative)
            assert relative in hidden_sources, relative
            return hidden_sources[relative]

        for path, expected in selected["outputs"].items():
            assert digest(selected_bytes(path)) == expected, path
        for path, expected in selected["sources"].items():
            assert digest(selected_bytes("inputs/" + path)) == expected, path
            assert digest(committed(path)) == expected, path
        assert selected["sources"]["hosted/test/mixer_hosted/browser_auth/run_callback_fixture.py"] == \
            "d469af3f63aa98d45ffb232b42433fddfbdd6b592238f3587e4a78c37b9173c5"
        registry = json.loads(selected_bytes(
            "inputs/verification/hosted-browser-callback-ci/selected-methods.json"))
        counts = {k: len(v) for k, v in selected["checks"].items()}
        assert counts == {"preauth": 30, "begin": 30, "callback": 35}
        for group, checks in selected["checks"].items():
            assert [x["name"] for x in checks] == registry["methods"][group]
            assert all(x["passed"] for x in checks)

        ordinary_prefix = "_temp/phoenix-foundation/"
        ordinary_raw = broad.read(ordinary_prefix + "receipt.json")
        ordinary = json.loads(ordinary_raw)
        assert ordinary["status"] == "passed" and all(ordinary["cleanup"].values())
        for command in ordinary["commands"]:
            assert digest(broad.read(ordinary_prefix + command["log"])) == command["sha256"]
            assert command["exit_code"] == command.get("expected_exit_code", 0)
        assert broad.read(ordinary_prefix + "revision.log").decode().strip() == COMMIT
        assert "Result: 664 passed, 2 skipped" in broad.read(ordinary_prefix + "tests.log").decode()
        # The full source archive stays opaque: frozen implementation lanes are not opened.
        assert digest(broad.read(ordinary_prefix + "source.tar.gz")) == ordinary["source_archive_sha256"]

    return {
        "schema": 1,
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "commit": COMMIT,
        "run_id": RUN,
        "status": "ordinary-ci-and-complete-selected-artifact-passed-independent-acceptance-pending",
        "artifacts": {name: {k: m[k] for k in ("id", "name", "digest", "size_in_bytes")}
                      for name, m in archives.items()},
        "selected_receipt_member": member,
        "selected_receipt_sha256": digest(raw),
        "selected_source_tree_sha256": selected["source_tree_sha256"],
        "selected_source_members_verified_against_commit_and_combined_artifacts": len(selected["sources"]),
        "selected_output_members_verified": len(selected["outputs"]),
        "hidden_artifact_exact_members": hidden_names,
        "method_counts": counts,
        "method_names_exact_registry": True,
        "source_and_dependency_unchanged": True,
        "selected_cleanup": selected["cleanup"],
        "selected_beam_cleanup": selected["beam_cleanup"],
        "versions": selected["versions"],
        "ordinary_receipt_sha256": digest(ordinary_raw),
        "ordinary_source_tree_sha256": ordinary["source_tree_sha256"],
        "ordinary_source_archive_sha256": ordinary["source_archive_sha256"],
        "ordinary_source_archive_opaque_unopened": True,
        "ordinary_verified_command_logs": len(ordinary["commands"]),
        "ordinary_methods": {"passed": 664, "existing_skips": 2, "failed": 0},
        "ordinary_cleanup": ordinary["cleanup"],
        "local_product_execution": False,
        "independent_storage_acceptance": False,
        "pending": ["Interrupted independent UnitA acceptance review", "ClaimOwner and retained wall handoff",
                    "Provider/HTTP/Application integration", "Native/device/customer/FieldLog/GA"],
    }


if __name__ == "__main__":
    print(json.dumps(review(), indent=2))
