import Testing
import MixerUI
@testable import MixerApple

@MainActor
@Test(arguments: [true, false])
func textBindingAdvancesOnlyWhenOptedIn(tracking: Bool) throws {
    func document(revision: UInt64, value: String) -> MixerUI.UIDocument {
        MixerUI.TextField("field", "Field", value: value, action: "edit").document(revision: revision)
    }

    let host = try MixerUIHost(document: document(revision: 1, value: ""))
    let snapshot = host.snapshot
    var errors: [UIRoutingError] = []
    let binding = mixerNativeTextBinding(node: snapshot.document.root, snapshot: snapshot,
                                         host: tracking ? host : nil) { event in
        do {
            let issued = try host.routeIssued(event)
            try host.update(document(revision: issued.action.revision + 1, value: issued.action.value.string!))
            return true
        } catch let error as UIRoutingError {
            errors.append(error)
        } catch {
            Issue.record(error)
        }
        return false
    }

    binding.wrappedValue = "a"
    binding.wrappedValue = "ab"
    #expect(host.snapshot.document == document(revision: tracking ? 3 : 2, value: tracking ? "ab" : "a"))
    #expect(binding.wrappedValue == (tracking ? "ab" : ""))
    #expect(errors == (tracking ? [] : [.staleRevision]))
    #expect(host.snapshot.identity(for: "field") == snapshot.identity(for: "field"))

    try host.update(MixerUI.Text("field", "Replacement").document(revision: 4))
    try host.update(document(revision: 5, value: "new"))
    let current = host.snapshot
    let retired = try #require(snapshot.identity(for: "field"))
    #expect(current.identity(for: "field") != retired)
    #expect(throws: UIRoutingError.staleIdentity) {
        try host.routeIssued(UIEventEnvelope(revision: 5, identity: retired, event: .textChange, value: .string("late")))
    }
    binding.wrappedValue = "late"
    #expect(errors.last == .staleRevision)
    #expect(host.snapshot.document == current.document)
}

@MainActor
@Test(arguments: [("Caf\u{00e9}", "Original"), ("Other", "Original"), ("Cafe\u{0301}", "Caf\u{00e9}")])
func textBindingDoesNotAdvanceWhenTheInstalledTreeDiffers(installed: String, sibling: String) throws {
    func document(revision: UInt64, value: String, sibling: String) -> MixerUI.UIDocument {
        MixerUI.VStack("root") {
            MixerUI.TextField("field", "Field", value: value, action: "edit")
            MixerUI.Text("sibling", sibling)
        }.document(revision: revision)
    }

    let originalSibling = sibling == "Original" ? "Original" : "Cafe\u{0301}"
    let host = try MixerUIHost(document: document(revision: 1, value: "", sibling: originalSibling))
    let snapshot = host.snapshot
    var errors: [UIRoutingError] = []
    let field = try #require(snapshot.document.root.children.first)
    let binding = mixerNativeTextBinding(node: field, snapshot: snapshot, host: host) { event in
        do {
            let issued = try host.routeIssued(event)
            try host.update(document(revision: issued.action.revision + 1, value: installed, sibling: sibling))
            return true
        } catch let error as UIRoutingError {
            errors.append(error)
        } catch {
            Issue.record(error)
        }
        return false
    }

    binding.wrappedValue = "Cafe\u{0301}"
    #expect(binding.wrappedValue.isEmpty)
    binding.wrappedValue = "late"
    #expect(errors == [.staleRevision])
    #expect(host.snapshot.document.revision == 2)
    let accepted = host.snapshot.document.root.children[0].properties["value"]?.string
    #expect(accepted?.utf8.elementsEqual(installed.utf8) == true)
}
