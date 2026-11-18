import ApplicationServices
import Foundation

struct PressFailure: Error, CustomStringConvertible {
    let description: String
    init(_ message: String) { description = message }
}

func pressOwnedButton(pid: pid_t, windowTitle: String, label: String) throws {
    let app = AXUIElementCreateApplication(pid)
    AXUIElementSetMessagingTimeout(app, 1)
    func attribute(_ element: AXUIElement, _ name: String) -> CFTypeRef? {
        var value: CFTypeRef?
        let result = AXUIElementCopyAttributeValue(element, name as CFString, &value)
        return result == .success ? value : nil
    }
    let deadline = ContinuousClock.now + .seconds(4)
    while ContinuousClock.now < deadline {
        let windows = attribute(app, kAXWindowsAttribute) as? [AXUIElement] ?? []
        if let window = windows.first(where: { attribute($0, kAXTitleAttribute) as? String == windowTitle }) {
            var pending = [window]
            for _ in 0..<64 {
                guard ContinuousClock.now < deadline, let current = pending.popLast() else { break }
                let role = attribute(current, kAXRoleAttribute) as? String
                let identifier = attribute(current, kAXIdentifierAttribute) as? String
                let title = attribute(current, kAXTitleAttribute) as? String
                if role == kAXButtonRole && (identifier == "toggle" || title == label) {
                    let result = AXUIElementPerformAction(current, kAXPressAction as CFString)
                    guard result == .success else {
                        throw PressFailure("Native button press returned \(result.rawValue)")
                    }
                    print("FIELDLOG native AX press \(label)")
                    return
                }
                pending.append(contentsOf: attribute(current, kAXChildrenAttribute) as? [AXUIElement] ?? [])
            }
        }
        Thread.sleep(forTimeInterval: 0.05)
    }
    throw PressFailure("Native accessibility button \(label) was absent from the owned window")
}

do {
    let args = CommandLine.arguments
    guard args.count == 4, let target = pid_t(args[1]), target == getppid(), AXIsProcessTrusted() else {
        throw PressFailure("The accessibility client requires a trusted parent test application")
    }
    try pressOwnedButton(pid: target, windowTitle: args[2], label: args[3])
} catch {
    FileHandle.standardError.write(Data("\(error)\n".utf8))
    exit(1)
}
