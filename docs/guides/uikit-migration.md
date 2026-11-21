# Add a Mixer screen to a UIKit app

Keep your app delegate, UIKit navigation, and data store. Move one screen at
a time. The Mixer v80 SDK requires iOS 26.0 or later. Link `MixerApple` and
push a `UIHostingController` whose root is `MixerNativeView`. The UIKit
controller reads its existing state and projects a document for that view. [Apple's hosting controller documentation](https://developer.apple.com/documentation/swiftui/uihostingcontroller)

This example keeps an inspection switch in UIKit and moves the progress
screen to Mixer. Each time the user opens progress, the app projects its
current switch value and validates the resulting document through
`MixerUIHost`. The generated `AppFeatures` package supplies the projector.

## Prepare a buildable example

Use Mixer v80 `5f4277e12e4872df43483307ec607a65e87dbae1` and Xcode 27.2
(build `27B52`). Keep the same Xcode selected for `create`, `test`, and
`build`. Creation records the Swift identity and the later commands check it.

```sh
export DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer
export PATH="$DEVELOPER_DIR/Toolchains/XcodeDefault.xctoolchain/usr/bin:$PATH"
xcodebuild -version

work=$(mktemp -d)
work=$(cd "$work" && pwd -P)
git clone https://github.com/snowdamiz/mixer.git "$work/mixer"
git -C "$work/mixer" switch --detach 5f4277e12e4872df43483307ec607a65e87dbae1
swift build --package-path "$work/mixer/cli" --scratch-path "$work/cli-build" --product mixer
bin=$(swift build --package-path "$work/mixer/cli" --scratch-path "$work/cli-build" --show-bin-path)
mixer="$bin/mixer"
project="$work/UIKitNotebook"
"$mixer" create UIKitNotebook --platform ios --application dev.example.uikitnotebook \
  --directory "$project" --sdk-path "$work/mixer/sdk"
```

Replace the sample's `Platforms/iOS/UIKitNotebookApp.swift` with the code
below. In an existing UIKit target, also link the sample's `AppFeatures`
product to use `ProjectFeature`, or replace that call with your own
`MixerUI.UIDocument` projector. Keep your existing entry point and add the
progress action to the controller that already owns the state.

```swift
import AppFeatures
import MixerApple
import SwiftUI
import UIKit

@main
final class UIKitNotebookApp: UIResponder, UIApplicationDelegate {
    func application(
        _ application: UIApplication,
        configurationForConnecting session: UISceneSession,
        options: UIScene.ConnectionOptions
    ) -> UISceneConfiguration {
        let configuration = UISceneConfiguration(name: nil, sessionRole: session.role)
        configuration.delegateClass = NotebookScene.self
        return configuration
    }
}

final class NotebookScene: UIResponder, UIWindowSceneDelegate {
    var window: UIWindow?

    func scene(
        _ scene: UIScene,
        willConnectTo session: UISceneSession,
        options: UIScene.ConnectionOptions
    ) {
        guard let scene = scene as? UIWindowScene else { return }
        let window = UIWindow(windowScene: scene)
        window.rootViewController = UINavigationController(rootViewController: NotebookViewController())
        self.window = window
        window.makeKeyAndVisible()
    }
}

final class NotebookViewController: UIViewController {
    private let inspection = UISwitch()

    override func viewDidLoad() {
        super.viewDidLoad()
        title = "Notebook"
        view.backgroundColor = .systemBackground

        let label = UILabel()
        label.text = "Inspection complete"
        label.font = .preferredFont(forTextStyle: .body)
        label.adjustsFontForContentSizeCategory = true
        inspection.accessibilityLabel = "Inspection complete"

        let button = UIButton(type: .system, primaryAction: UIAction(title: "Show progress") {
            [weak self] _ in self?.showProgress()
        })

        let controls = UIStackView(arrangedSubviews: [label, inspection, button])
        controls.axis = .vertical
        controls.alignment = .leading
        controls.spacing = 12
        controls.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(controls)
        NSLayoutConstraint.activate([
            controls.leadingAnchor.constraint(equalTo: view.layoutMarginsGuide.leadingAnchor),
            controls.trailingAnchor.constraint(equalTo: view.layoutMarginsGuide.trailingAnchor),
            controls.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor, constant: 20),
        ])
    }

    private func showProgress() {
        let document = ProjectFeature.document(entries: [
            .init(title: "Inspect site", completed: inspection.isOn)
        ])

        do {
            let host = try MixerUIHost(document: document)
            let progress = UIHostingController(rootView: MixerNativeView(host: host, onAction: { _ in }))
            progress.title = "Project progress"
            navigationController?.pushViewController(progress, animated: true)
        } catch {
            let alert = UIAlertController(
                title: "Progress unavailable",
                message: "The progress screen could not be opened.",
                preferredStyle: .alert
            )
            alert.addAction(UIAlertAction(title: "OK", style: .default))
            present(alert, animated: true)
        }
    }
}
```

## Verify the native build

```sh
"$mixer" import "$project/Platforms/iOS"
"$mixer" test --platform host --directory "$project"
"$mixer" build --platform ios --directory "$project"
```

The import report classifies UIKit as platform-specific. Keep UIKit imports
in the Apple target when moving shared state or reducers into a Swift
package. The host tests exercise the generated feature model and action
routing. The last command builds an unsigned app for a generic iOS Simulator
destination. To check the screen on a local simulator later, switch
**Inspection complete** on and select **Show progress**. The progress view
should show one of one completed. Go back, switch it off, and reopen progress
to check that it reflects the UIKit state.

The example uses an in-memory switch and a native Mixer renderer. An existing
app should read from its own repository. Guest admission, signed updates, and
native interaction each need their own verification.

[Build verification](../../verification/receipts/uikit-migration-guide-v80.json)
