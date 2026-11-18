"""Validate durable FieldLog records across an install and a real edit."""
import uuid

TITLE = "Migration photo draft"
NOTE = "Keep  two spaces."
EDITED = NOTE + " Checked on site."


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_workspace(state, phase):
    require(phase in {"draft", "entry"}, f"Unknown workspace phase {phase}")
    [project], [task], [photo] = (state[key] for key in ("projects", "tasks", "attachments"))
    live_records, empty_records = ("drafts", "entries") if phase == "draft" else ("entries", "drafts")
    [record] = state[live_records]
    outbox = state["outbox"]
    for item in (state, project, task, record, photo, *outbox):
        uuid.UUID(item["id"])
    operation_ids = {change["id"] for change in outbox}
    expected_operations = [("projectCreated", project["id"]), ("taskSaved", task["id"])]
    if phase == "entry":
        expected_operations.append(("entrySaved", record["id"]))
    revisions = [change["revision"] for change in outbox]
    require(
        state["schema"] == 1 and state["revision"] > 0 and state[empty_records] == []
        and project["title"] == "Migration pump station"
        and task["title"] == "Inspect pump" and task["completed"] is False
        and record["title"] == TITLE and record["note"] == (NOTE if phase == "draft" else EDITED)
        and task["projectID"] == record["projectID"] == project["id"]
        and record["attachmentIDs"] == [photo["id"]]
        and photo["filename"] == str(uuid.UUID(photo["id"])) + ".jpg"
        and 0 < photo["byteCount"] <= 6_291_456
        and state["restoration"].get("selectedProjectID") == project["id"]
        and state["restoration"].get("openDraftID") == (record["id"] if phase == "draft" else None)
        and [(change["kind"], change["recordID"]) for change in outbox] == expected_operations
        and len(operation_ids) == len(outbox)
        and revisions == sorted(set(revisions))
        and 0 < revisions[0] <= revisions[-1] <= state["revision"],
        f"Wrong durable {phase} state, record links, restoration or outbox",
    )
    return photo


def compare_containers(baseline, observed, operation):
    marker = baseline.get("containerMarkerSHA256", "")
    require(len(marker) == 64 and observed.get("containerMarkerSHA256") == marker,
            f"Application data continuity marker changed during {operation}")
    same_path = observed["container"] == baseline["container"]
    before, after = (snap["containerFilesystemID"] for snap in (baseline, observed))
    same_directory = before == after if before is not None and after is not None else None
    if operation == "install":
        require(same_directory is not False, "The replacement install changed the physical data directory")
    require(not same_path or same_directory is not False,
            f"Application data directory was replaced at the same path during {operation}")
    return {"samePath": same_path, "sameFilesystemID": same_directory}


def compare(baseline, observed, operation):
    continuity = compare_containers(baseline, observed, operation)
    require(observed["photoSHA256"] == baseline["photoSHA256"], f"JPEG changed during {operation}")
    before, after = (snap["workspace"] for snap in (baseline, observed))
    if operation in {"install", "restore", "readback"}:
        require(observed["workspaceSHA256"] == baseline["workspaceSHA256"] and after == before,
                f"Workspace bytes changed during {operation}")
        return continuity
    require(operation == "edit", f"Unknown comparison: {operation}")
    for key in ("schema", "id", "createdAt", "projects", "tasks", "attachments"):
        require(after[key] == before[key], f"{key} changed while committing the draft")
    require(after["revision"] > before["revision"], "Commit did not advance workspace revision")
    [draft], [entry] = before["drafts"], after["entries"]
    for key in ("id", "projectID", "category", "occurredAt", "title", "attachmentIDs"):
        require(entry[key] == draft[key], f"Draft {key} changed on commit")
    require(after["outbox"][:-1] == before["outbox"], "The original queued operations changed")
    require(after["outbox"][-1]["revision"] == after["revision"],
            "The new entry operation must match the commit revision")
    return continuity
