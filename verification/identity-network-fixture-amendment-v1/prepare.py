"""Materialize the exact independently accepted fixture/source amendment; no runtime."""
import ast
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
META = OUT / "metadata"
COLLECTOR = ROOT / "hosted/scripts/test-identity-network.py"
REVIEW = ROOT / "verification/identity-tls-fixture-independent"
PRODUCER = ROOT / "verification/identity-startup-socket-close-investigation"
OLD = "023df04c9a4599c3d5a6cdf2afb53a95e2faf37765d8b96ba2bcc0e1b007c92e"
NEW = "ab8f8dbec5894ca96dd673db828a01afdc39a54ad008a2a2d4e598c1c62ce2f7"

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def row(body):
    return {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")

source = COLLECTOR.read_text()
assignments = {node.targets[0].id: ast.literal_eval(node.value) for node in ast.parse(source).body
               if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
               and node.targets[0].id in {"FROZEN_MANIFEST", "PREREQUISITES_EXS", "BOOTSTRAP_EXS", "BOOTSTRAP", "MANIFEST_EXS", "NETNS_EXS", "OBSERVER_EXS", "MOUNTS_EXS", "TEST_ROOTS", "EXPECTED_METHODS"}}
predecessor = assignments["FROZEN_MANIFEST"]
assert len(predecessor) == 177 and digest(predecessor) == OLD
proposal = json.loads((PRODUCER / "source-binding-proposal.json").read_bytes())
selected = dict(predecessor)
for path, change in proposal["exact_delta"].items():
    assert predecessor.get(path) == change["before"]
    body = (REVIEW / "inputs/candidate" / path).read_bytes()
    assert row(body) == change["after"]
    target = ROOT / path
    if change["before"] is None:
        assert not target.exists()
    else:
        assert row(target.read_bytes()) == change["before"]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)
    selected[path] = change["after"]
assert len(selected) == 178 and digest(selected) == NEW
assert selected == json.loads((PRODUCER / "candidate-product-source-manifest.json").read_bytes())
review_body = (REVIEW / "packet-manifest.json").read_bytes()
assert row(review_body)["sha256"] == "613876f8c91fb07e08100ba8cf02906cf61b67ae8573703ecced44073c84fa5e"
review_packet = json.loads(review_body)
assert digest(review_packet["files"]) == review_packet["tree_digest_sha256"] == "f8d04d5f4f118f940f7183f16b217ca401b34fcda5558dd7929ce2d5657d446d"
for path, expected in review_packet["files"].items():
    assert row((REVIEW / path).read_bytes()) == expected
    target = META / "independent-review" / path
    target.parent.mkdir(parents=True, exist_ok=True)
    assert not target.exists()
    shutil.copyfile(REVIEW / path, target)
(META / "independent-review/packet-manifest.json").write_bytes(review_body)
save(META / "predecessor-source-manifest.json", predecessor)
save(META / "selected-source-manifest.json", selected)
patch = (PRODUCER / "integration-candidate.patch").read_bytes()
assert row(patch)["sha256"] == "24477b79356bfcdf32287c70ee8c39596b93e506ac64be9ba50ec3e6fdd875a1"
(META / "integration-candidate.patch").write_bytes(patch)
for placeholder, value in {"HEX_URL": assignments["BOOTSTRAP"]["hex"]["url"], "HEX_SHA": assignments["BOOTSTRAP"]["hex"]["sha512"],
                           "REBAR_URL": assignments["BOOTSTRAP"]["rebar"]["url"], "REBAR_SHA": assignments["BOOTSTRAP"]["rebar"]["sha512"]}.items():
    assignments["BOOTSTRAP_EXS"] = assignments["BOOTSTRAP_EXS"].replace(placeholder, value)
helpers = {"collector-" + name.lower() + ".exs": assignments[name.upper() + "_EXS"].encode()
           for name in ("prerequisites", "bootstrap", "manifest", "netns", "observer", "mounts")}
helpers["frozen-manifest.json"] = json.dumps(selected, sort_keys=True, separators=(",", ":")).encode()
amendment = {
    "schema": 1, "operation": "replace-exact-test-fixture-and-add-executable-regression-test",
    "predecessor": {"product_commit": "9e860ea12074ca31bef4087ce34177a03f295dd8", "source_count": 177, "source_digest_sha256": OLD,
                    "contract_sha256": "695a165d41e9d4eac5fdc582b835a60f5c3bbdd6f0fb3131c0ad27ffbbe135bc",
                    "image_amendment_sha256": "6a2ec88721d89a28e40961f834b856598ba0f6f14d88708906cf3931e0e33afa",
                    "execution_amendment_sha256": "b447fe5919c4e73d86aee4da707570127de2c35ecdae5a7b90b0163eb9bc436c"},
    "selected": {"source_count": 178, "source_digest_sha256": NEW, "manifest": {"path": "selected-source-manifest.json", **row((META / "selected-source-manifest.json").read_bytes())}},
    "exact_delta": proposal["exact_delta"],
    "independent_review": {"namespace": "independent-review/", "packet_manifest_sha256": row(review_body)["sha256"], "packet_tree_digest_sha256": review_packet["tree_digest_sha256"]},
    "integration_patch": {"path": "integration-candidate.patch", **row(patch)},
    "preserved": {"lock_sha256": "1eada39dcaf4863d02d39f51e218d2bad8908b36a0cba47ff2d16037b7bcf837", "original_test_files": proposal["unchanged_tests"],
                  "test_roots": assignments["TEST_ROOTS"], "expected_methods": assignments["EXPECTED_METHODS"],
                  "runtime": "all selected image/execution/namespace/resource/bootstrap/custody contracts unchanged"},
    "literal_helpers": {path: row(body) for path, body in helpers.items()},
    "ordinary_phoenix_controls": ["stalled response stays silent and reports client EOF within the unchanged startup wait",
                                  "an accepted TCP client that aborts before handshake records exactly one peer EOF",
                                  "local receive timeout cleans the handler without counting a peer EOF",
                                  "unexpected client data does not count as peer EOF or enter diagnostics"],
    "remote_execution_only": True, "runtime_or_GA_accepted": False,
}
save(META / "source-amendment.json", amendment)
files = {str(path.relative_to(META)): row(path.read_bytes()) for path in sorted(META.rglob("*")) if path.is_file()}
packet = {"schema": 1, "files": files, "tree_digest_sha256": digest(files)}
save(META / "packet-manifest.json", packet)
save(OUT / "preparation.json", {"schema": 1, "command": ["python3", "-B", str(Path(__file__).relative_to(ROOT))],
                              "source_count": len(selected), "source_digest_sha256": NEW,
                              "source_amendment_sha256": row((META / "source-amendment.json").read_bytes())["sha256"],
                              "packet_manifest": row((META / "packet-manifest.json").read_bytes()), "packet_tree_digest_sha256": packet["tree_digest_sha256"],
                              "packet_members": len(files), "review_model": "gpt-6-astra", "review_reasoning": "xhigh",
                              "review_model_basis": "parent root confirmed actual fresh reviewer spawn metadata", "runtime_resources_created": 0})
print(json.dumps({"source": NEW, "amendment": row((META / "source-amendment.json").read_bytes())["sha256"],
                  "packet": packet["tree_digest_sha256"], "packet_sha256": row((META / "packet-manifest.json").read_bytes())["sha256"], "members": len(files)}))
