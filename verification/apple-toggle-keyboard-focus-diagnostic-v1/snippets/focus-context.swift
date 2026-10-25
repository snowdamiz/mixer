    // Diagnostic-only context trace, separate from the original strict trace.
    private(set) var focusContextEntries: [[String: Any]] = []
    private(set) var focusContextDropped = 0
    private(set) var focusContextRevision = 0
    private func focusEndpoint(_ item: (any UIFocusItem)?) -> [String: Any] {
        guard let item else {
            return ["state": "null", "identifier": NSNull(), "class": NSNull(),
                    "identity": NSNull(), "frame": NSNull(), "frameInWindow": NSNull(), "attachedToWindow": NSNull()]
        }
        let frame = item.frame
        var value: [String: Any] = ["state": "item", "class": String(describing: type(of: item)),
            "identity": String(describing: ObjectIdentifier(item)),
            "identifier": (item as? any UIAccessibilityIdentification)?.accessibilityIdentifier as Any? ?? NSNull(),
            "frame": ["x": frame.minX, "y": frame.minY, "width": frame.width, "height": frame.height],
            "frameInWindow": NSNull(), "attachedToWindow": NSNull()]
        if let view = item as? UIView {
            value["attachedToWindow"] = view.window != nil
            if view.window != nil {
                let attached = view.convert(view.bounds, to: nil)
                value["frameInWindow"] = ["x": attached.minX, "y": attached.minY, "width": attached.width, "height": attached.height]
            }
        }
        return value
    }
    func focusContext(_ source: String, _ context: UIFocusUpdateContext) {
        focusContextRevision += 1
        guard focusContextEntries.count < 128 else { focusContextDropped += 1; return }
        focusContextEntries.append(["sequence": focusContextRevision, "uptime": ProcessInfo.processInfo.systemUptime,
            "source": source, "heading": context.focusHeading.rawValue,
            "previous": focusEndpoint(context.previouslyFocusedItem), "next": focusEndpoint(context.nextFocusedItem)])
    }
