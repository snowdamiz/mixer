# FieldLog project-site map island

The seven imported host-replay files were copied from the completed experiment in
`t3-e3d4a647` at checkout revision `33784e5c780aba6494c6471dbdedec93b78c6391`.
[`upstream.sha256`](upstream.sha256) records their pre-change hashes. The native
fixture and host executable compile the same registry, verifier adapter, and
signing fixtures.

## macOS host replay

Run from this checkout with macOS and Swift 6.2 or later.

```sh
compiler/experiments/native-map-island/replay.sh
```

The executable mounts a map above the details, then applies a signed update that moves it below the details and changes its coordinates and style. It checks the exact provider instance and SDK node identity. The same refusal controls run before the first mount and after the accepted update. They cover an unknown ID with a signed grant, a registered ID without a grant, independently mismatched placement and grant hashes, an unsupported version, invalid coordinates, a grant inserted after signing, a same-length payload edit, and an unpinned signer. After the refusals, the host and the provider still hold the accepted placement.

## Authority and wire format

The experiment's installed registry has one entry, `fieldlog.project-site-map`, with placement schema version 1. The host derives its fixture runtime fingerprint from that registration and its canonical schema digest. It authenticates the exact payload bytes against the pinned test root using the existing `ReleaseVerifierV3`. The test signer generates its key in memory for each replay.

The current v3 capability grant table admits HTTP and storage. This fixture keeps that table empty and uses a versioned experiment-local island grant manifest inside the payload covered by the signed v3 payload digest. The host requires the exact installed ID, the signed grant for that ID, and equality of the installed, granted, and requested schema digests. It then validates the slot, style, and coordinate bounds before any provider access. The schema permits signed decimal coordinate strings with up to six fractional digits and has an empty event set. The installed host owns the node identity. The placement carries data for one map and cannot supply a factory or a platform selector.

## iOS Simulator fixture

Build, sign, and verify both the app and its XCTest runner without a simulator
destination. Run from the repository root.

```sh
compiler/experiments/native-map-island/build-simulator.sh
```

The script retains the signed bundles, an `.xctestrun` file, source hashes,
and verification logs under the reported `verification/local/gc3-map-products.*`
directory. It clears the disposable build directory on exit. It checks the
retained signatures, the arm64 Simulator executables, and their iOS 17.0
deployment floor. Both replay commands resolve pinned SwiftPM build dependencies.

From the reported `Products` directory, root can run the built journey on an
owned iOS 26.5 Simulator using its UUID and a fresh result-bundle path.

```sh
set -- ./*.xctestrun
xcodebuild -xctestrun "$1" -destination "platform=iOS Simulator,id=$SIMULATOR_UDID" \
  -parallel-testing-enabled NO -resultBundlePath "$RESULT_BUNDLE" \
  -only-testing:NativeMapIslandUITests/MapIslandUITests/testSignedSiteMoveAndRefusedPlacementsPreserveVisibleMap \
  test-without-building
```

The app mounts a SwiftUI MapKit annotation at the first signed site. The
journey checks its accessible coordinates and screen position above the details
row. A second signed release moves the annotation to a new site, switches the
requested map style to imagery, and places the map below the details. XCTest
reads MapKit's camera feedback and checks the provider instance, SwiftUI view
state, and installed node identity across the move. Subsequent signed requests
for an unknown island, a missing grant, and a mismatched schema carry different
coordinates, style, and slot. XCTest checks each refusal and the retained pin,
camera, position, style, surface identity, and provider apply count.

The macOS executable uses a recording provider and runs offline. The iOS
fixture uses Apple MapKit without provider credentials. Offline basemap tiles
may be blank. The XCTest assertions cover the annotation and camera, independent
of tile appearance. Android, production UI-schema and release-grant integration,
and UP5 acceptance remain separate work.
