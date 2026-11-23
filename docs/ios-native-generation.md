# Add native files to the generated iOS app

Add an optional `iosNative` object to `mixer.yml`.

```json
{
  "iosNative": {
    "swiftSources": ["ChecklistView.swift"],
    "resourceFolders": ["CheckoutRelease/ChecklistRelease"],
    "localNetworkUsageDescription": "Connect to the developer checklist service on this local network.",
    "allowsLocalNetworking": true
  }
}
```

Declare paths relative to `Platforms/iOS`. The app target compiles the listed
Swift files alongside the generated app entry point. Xcode copies each listed
folder by its final name, so the example folder is available as
`Bundle.main.url(forResource: "ChecklistRelease", withExtension: nil)`.
Use simple ASCII paths without symlinks. Each Swift filename must be unique
across the target, including the generated app entry point. Filenames that
differ only by case count as duplicates.

The network fields set `NSLocalNetworkUsageDescription` and the Boolean
`NSAppTransportSecurity.NSAllowsLocalNetworking` in the app's Info.plist.
Each field is optional. To change the generated target, edit `mixer.yml` and
run `mixer build --platform ios` again. If generation is interrupted, rerun
the same command to recover the project and apply the current configuration.
Mixer stores generated plist inputs by SHA-256 under `.mixer/ios-plists`.
Reconfiguration updates the project reference and leaves existing inputs in
place. If a file exists at `MixerNativeInfo.plist` inside the Xcode project,
generation stops so the app owner can reconcile that file.

## Link a static archive on iOS Simulator

Set `simulatorArchive` to the archive's `.a` path relative to `Platforms/iOS`.
Set `simulatorArchiveSHA256` to its 64-character lowercase SHA-256. Keep the
archive outside the declared resource folders. Mixer checks the archive bytes
before generating the project and restricts the generated app target to iOS
Simulator. Supply any matching C headers and module map through your package.
