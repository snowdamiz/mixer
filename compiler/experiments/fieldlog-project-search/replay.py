"""Run FieldLog's exact native project-search API and its Embedded boundary."""

import argparse
import hashlib
from pathlib import Path
import runpy
import shutil
import tempfile


FIXTURE = Path(__file__).resolve().parent
FOUNDATION_REPLAY = FIXTURE.with_name("foundation-date")
WORKSPACE_SHA256 = "a6c08ae0aa83400aef8c8a6cc045415cf7a9075367d81001bd5e3f505fbc5c21"
SEARCH_RESULTS = (
    "Café Service|Inspection",
    "Café Service",
    "الورشة",
    "",
    "الورشة|Café Service|Remote|Inspection",
    "Inspection",
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path, help="Exact FieldLog Workspace.swift")
    parser.add_argument("receipt", type=Path, help="New file with an existing parent")
    args = parser.parse_args()
    source = args.workspace.read_bytes()
    if hashlib.sha256(source).hexdigest() != WORKSPACE_SHA256:
        raise SystemExit("FieldLog workspace source does not match the tested product")

    support = runpy.run_path(str(FOUNDATION_REPLAY / "replay.py"))
    output = args.receipt.parent.resolve(strict=True) / args.receipt.name
    with output.open("x", encoding="utf-8") as receipt:
        scratch = Path(tempfile.mkdtemp(prefix="project-search-", dir=output.parent))
        with (scratch / "journal.json").open("x", encoding="utf-8") as journal:
            campaign = support["Campaign"](scratch, journal)
            campaign.record.update(
                mixerRevision="8e8d75c3368d2b8153bc3f86c5c281cda11d31e2",
                mixerTree="31903bfa0d00d5b60a994c95818d4519ddbb5e46",
                scope="L03 §7.3 FieldLog project search on arm64 macOS",
                fieldLogTree="26bbde4aae443e77452761022ee344b075077431",
                workspaceSHA256=WORKSPACE_SHA256,
            )
            campaign.save()
            try:
                check_search(campaign, support, source)
                campaign.record["status"] = "pass"
            except BaseException as error:
                campaign.record.update(status="incomplete", error=str(error))
                raise
            finally:
                if campaign.active is None:
                    campaign.record["scratch"]["cleanup"] = "after receipt publication"
                else:
                    campaign.record["scratch"]["hold"] = campaign.active
                support["publish"](output, receipt, campaign.save())
                if campaign.active is None:
                    shutil.rmtree(scratch)


def check_search(campaign, support, source):
    model = campaign.scratch / "Workspace.swift"
    model.write_bytes(source)
    fixture = FIXTURE / "Search.swift"
    swift, sdk = campaign.tools()
    executable = campaign.scratch / "search"
    campaign.record["fixture"] = support["identity"](fixture)
    campaign.run(
        "native-build", swift, "-target", support["NATIVE"], "-sdk", sdk,
        "-swift-version", "6", "-parse-as-library", "-module-cache-path",
        campaign.scratch / "native-cache", model, fixture, "-o", executable, bound=70,
    )
    campaign.record["readbacks"] = []
    for name, indices in (("ordered", (0, 1, 2, 3, 4, 5)), ("reordered", (3, 5, 0, 5, 2, 4, 1))):
        expected = "".join(SEARCH_RESULTS[index] + "\n" for index in indices).encode()
        output, _, _ = campaign.run(name, executable, *map(str, indices), raw=True)
        support["check"](output.read_bytes() == expected, f"{name}: project search differs")
        campaign.record["readbacks"].append({"indices": indices, "expectedAndObserved": expected.decode()})
    campaign.embedded(swift, "embedded-project-search", [model, fixture], failed_import=model)
    campaign.embedded(
        swift, "embedded-control", [FOUNDATION_REPLAY / "Cases.swift", FOUNDATION_REPLAY / "Control.swift"],
    )


if __name__ == "__main__":
    main()
