#if os(iOS) && targetEnvironment(simulator) && MIXER_F11_IOS_FIXTURE
import MixerApple
import MixerUI
import SwiftUI
import UIKit

@MainActor
struct F11NativeNote: UIViewRepresentable {
    static let field = "entry.f1100000-0000-4000-8000-000000000001.note"
    let presentation: GuestUIPresentation
    let host: MixerUIHost
    let attachment: CapabilityGuestUIAttachmentIdentity

    func makeCoordinator() -> Coordinator { Coordinator() }

    func makeUIView(context: Context) -> UIStackView {
        let coordinator = context.coordinator
        let note = coordinator.note
        note.delegate = coordinator
        note.font = .preferredFont(forTextStyle: .body)
        note.accessibilityIdentifier = "f11.note"
        note.accessibilityLabel = "Note"
        note.autocorrectionType = .no
        note.smartQuotesType = .no
        note.smartDashesType = .no
        note.heightAnchor.constraint(equalToConstant: 160).isActive = true

        let paste = coordinator.paste
        paste.target = note
        paste.accessibilityIdentifier = "f11.paste"
        paste.heightAnchor.constraint(equalToConstant: 44).isActive = true

        let layout = UIStackView(arrangedSubviews: [note, paste])
        layout.axis = .vertical
        layout.spacing = 8
        return layout
    }

    func updateUIView(_ view: UIStackView, context: Context) {
        let coordinator = context.coordinator
        let document = host.snapshot.document
        let value = document.root.children.first?.properties["value"]?.string ?? ""
        if coordinator.revision != document.revision {
            coordinator.note.text = value
            coordinator.revision = document.revision
            coordinator.submitted = false
        }
        coordinator.note.isEditable = document.revision == 1 && presentation.f11NativeRevision == 1 && presentation.inputEnabled
        coordinator.paste.isEnabled = coordinator.note.isEditable && !coordinator.submitted
        coordinator.submit = nil
        guard coordinator.note.isEditable, let identity = host.snapshot.identity(for: Self.field) else { return }
        let send = presentation.actionHandler(host: host, attachment: attachment)
        coordinator.submit = { complete in
            let envelope = UIEventEnvelope(revision: document.revision, identity: identity,
                event: .textChange, value: .string(complete))
            if let action = try? host.route(envelope) { send(action) }
        }
    }

    @MainActor
    final class Coordinator: NSObject, UITextViewDelegate {
        let note = UITextView()
        let paste = UIPasteControl()
        var revision: UInt64?
        var submitted = false
        var submit: ((String) -> Void)?

        func textViewDidBeginEditing(_ textView: UITextView) {
            textView.selectedRange = NSRange(location: textView.text.utf16.count, length: 0)
        }

        func textView(_ textView: UITextView, shouldChangeTextIn range: NSRange, replacementText text: String) -> Bool {
            !submitted && submit != nil && range.location == textView.text.utf16.count
                && range.length == 0 && text.utf8.elementsEqual("Edited".utf8)
        }

        func textViewDidChange(_ textView: UITextView) {
            guard !submitted, let submit else { return }
            submitted = true
            paste.isEnabled = false
            submit(textView.text)
        }
    }
}
#endif
