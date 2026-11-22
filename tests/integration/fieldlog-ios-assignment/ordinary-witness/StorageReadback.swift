
#if DEBUG
private struct OrdinaryWitnessStorage: ViewModifier {
  @EnvironmentObject private var model: WorkspaceModel
  @State private var value = "waiting"

  func body(content: Content) -> some View {
    if model.isTestWorkspace,
      ProcessInfo.processInfo.arguments.contains("--fieldlog-ordinary-witness-readback")
    {
      content
        .accessibilityIdentifier("ordinary-witness-storage")
        .accessibilityValue(value)
        .task {
          await model.flush()
          do {
            value = try readDisk()
          } catch {
            value = "read failed: \(error)"
          }
        }
    } else {
      content
    }
  }

  private func readDisk() throws -> String {
    guard let directory = model.workspaceDirectory else { return "workspace directory missing" }
    let snapshot = try Data(contentsOf: directory.appending(path: "workspace.json"))
    let workspace = try JSONDecoder().decode(Workspace.self, from: snapshot)
    try workspace.validate()
    guard workspace == model.workspace,
      workspace.projects.count == 1, let project = workspace.projects.first,
      project.title == "Pump station witness", project.siteCoordinate?.latitude == 37.42,
      project.siteCoordinate?.longitude == -122.08,
      workspace.restoration.selectedProjectID == project.id,
      workspace.restoration.openDraftID == nil,
      workspace.entries.isEmpty, workspace.tasks.isEmpty,
      workspace.drafts.count == 1, let draft = workspace.drafts.first,
      draft.projectID == project.id, draft.title == "Pressure reading", draft.note == "Gauge stable at 42 psi.",
      workspace.attachments.count == 1, let photo = workspace.attachments.first,
      draft.attachmentIDs == [photo.id],
      workspace.outbox.count == 1, let event = workspace.outbox.first,
      event.kind == .projectCreated, event.recordID == project.id
    else { return "unexpected workspace, draft, pin, attachment reference or outbox" }

    let jpeg = try Data(contentsOf: directory.appending(path: "photos").appending(path: photo.filename))
    guard jpeg.count == photo.byteCount, jpeg.starts(with: [0xff, 0xd8, 0xff]),
      let source = CGImageSourceCreateWithData(jpeg as CFData, nil),
      CGImageSourceCreateImageAtIndex(source, 0, nil) != nil
    else { return "attachment is not the expected decodable JPEG" }

    let settings = try Data(contentsOf: URL.applicationSupportDirectory.appending(path: "FieldLog-Preferences.json"))
    guard let values = try JSONSerialization.jsonObject(with: settings) as? [String: Any],
      values["version"] as? Int == 1, values["appearance"] as? String == "dark"
    else { return "unexpected stored Settings record" }

    let digests = [snapshot, jpeg, settings].map { bytes in
      SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined()
    }
    return "verified:" + digests.joined(separator: ":")
  }
}
#endif
