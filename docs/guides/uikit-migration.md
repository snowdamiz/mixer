# Add a Mixer screen to a UIKit app

Keep your app delegate, UIKit navigation, and data store. Move one screen at
a time. Link the `MixerApple` product from your pinned Mixer SDK and push a
`UIHostingController` whose root is `MixerNativeView`. Your UIKit controller
can read its existing state and pass a document to that view. [Apple's hosting controller documentation](https://developer.apple.com/documentation/swiftui/uihostingcontroller)

This example keeps an inspection switch in UIKit and moves the progress
screen to Mixer. Each time the user opens progress, the app projects its
current switch value and validates the resulting document through
`MixerUIHost`. The generated `AppFeatures` package supplies the projector.

## Prepare a buildable example

Use the `mixer` CLI and `sdk/` from the same pinned checkout. Select Xcode for
both creation and build so they use the same Swift version. Set `sdk` to the
absolute path of the pinned checkout's `sdk/` directory.

```sh
work=$(mktemp -d)
project="$work/UIKitNotebook"
mixer create UIKitNotebook --platform ios --application dev.example.uikitnotebook \
  --directory "$project" --sdk-path "$sdk"
```

Replace the sample's `Platforms/iOS/UIKitNotebookApp.swift` with the code
below. In an existing UIKit app, keep its entry point and use the
progress action in the controller that already owns the state.

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
mixer import "$project/Platforms/iOS"
mixer test --platform host --directory "$project"
mixer build --platform ios --directory "$project"
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
