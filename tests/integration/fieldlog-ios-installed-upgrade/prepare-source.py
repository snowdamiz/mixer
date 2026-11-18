"""Apply the local package path and Files import overlays to a fresh Git export."""
import sys
from pathlib import Path

app = Path(sys.argv[1])
here = Path(__file__).resolve().parent


def replace(path, old, new):
    source = path.read_text()
    if source.count(old) != 1:
        raise ValueError(f"Pin does not match overlay for {path}: {old}")
    path.write_text(source.replace(old, new))


replace(
    app / "Package.swift",
    '.package(url: "https://github.com/snowdamiz/mixer.git", revision: "56ff14c925168284761c5aca4f0bd4129cf3c995")',
    '.package(path: "../mixer")',
)
for lock in (
    app / "Package.resolved",
    app / "ios/FieldLog.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved",
):
    lock.unlink()

editor = app / "ios/FieldLog/EntryEditor.swift"
replace(editor, "  @State private var attaching = false", """  @State private var attaching = false
  @State private var choosingFile = false""")
replace(editor, '          if attaching { ProgressView("Preparing photo…") }', '''          Button("Import image from Files", systemImage: "folder") { choosingFile = true }
            .disabled(attaching || currentPhotoIDs.count >= 8)
            .accessibilityIdentifier("attach-file")
          if attaching { ProgressView("Preparing photo…") }''')
replace(editor, """          let jpeg = try Self.resizedJPEG(picked.file)
          let ids = try await model.addPhoto(jpeg, draftID: draft.id)
          draft.attachmentIDs = ids""", """          try await attachPhoto(from: picked.file)""")
replace(editor, """    .alert(
      "Photo couldn't be attached",""", """    .sheet(isPresented: $choosingFile) {
      ImageDocumentPicker { file in
        choosingFile = false
        guard let file else { return }
        attaching = true
        Task {
          let scoped = file.startAccessingSecurityScopedResource()
          defer {
            if scoped { file.stopAccessingSecurityScopedResource() }
            attaching = false
          }
          do {
            try SelectedPhoto.checkSize(file)
            try await attachPhoto(from: file)
          } catch { photoError = error.localizedDescription }
        }
      }
    }
    .alert(
      "Photo couldn't be attached",""")
replace(editor, "  private var currentPhotoIDs: [UUID] {", """  private func attachPhoto(from file: URL) async throws {
    let jpeg = try Self.resizedJPEG(file)
    draft.attachmentIDs = try await model.addPhoto(jpeg, draftID: draft.id)
  }

  private var currentPhotoIDs: [UUID] {""")
replace(editor, """      let attrs = try FileManager.default.attributesOfItem(atPath: received.file.path)
      guard let bytes = attrs[.size] as? NSNumber, bytes.intValue > 0,
        bytes.intValue <= 32 * 1024 * 1024
      else { throw FieldLogError.validation("Choose an image smaller than 32 MiB.") }""",
        """      try checkSize(received.file)""")
replace(editor, """}

struct PhotoPreview: View {""", """  static func checkSize(_ file: URL) throws {
    let attrs = try FileManager.default.attributesOfItem(atPath: file.path)
    guard let bytes = attrs[.size] as? NSNumber, bytes.intValue > 0,
      bytes.intValue <= 32 * 1024 * 1024
    else { throw FieldLogError.validation("Choose an image smaller than 32 MiB.") }
  }
}

private struct ImageDocumentPicker: UIViewControllerRepresentable {
  let onPick: (URL?) -> Void

  func makeCoordinator() -> Coordinator { Coordinator(onPick: onPick) }

  func makeUIViewController(context: Context) -> UIDocumentPickerViewController {
    let picker = UIDocumentPickerViewController(forOpeningContentTypes: [.image], asCopy: true)
    picker.directoryURL = URL.documentsDirectory
    picker.delegate = context.coordinator
    return picker
  }

  func updateUIViewController(_ picker: UIDocumentPickerViewController, context: Context) {}

  final class Coordinator: NSObject, UIDocumentPickerDelegate {
    let onPick: (URL?) -> Void

    init(onPick: @escaping (URL?) -> Void) {
      self.onPick = onPick
    }

    func documentPicker(_ controller: UIDocumentPickerViewController, didPickDocumentsAt urls: [URL]) {
      onPick(urls.first)
    }

    func documentPickerWasCancelled(_ controller: UIDocumentPickerViewController) {
      onPick(nil)
    }
  }
}

struct PhotoPreview: View {""")

(app / "ios/FieldLogUITests/FieldLogUITests.swift").write_bytes(
    (here / "FieldLogInstalledUpgradeTests.swift").read_bytes()
)
