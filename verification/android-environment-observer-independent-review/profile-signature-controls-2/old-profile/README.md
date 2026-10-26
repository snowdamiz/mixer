# IndependentConsumer

Created with the mixer development preview. Run `mixer test` or `swift test`.
`mixer.yml` uses JSON, a valid YAML 1.2 subset. The bundled SDK source snapshot
is hashed in mixer.lock and allows offline builds without a cloud account.
Source edits to that snapshot invalidate the lock until explicitly regenerated.

The iOS app entry point is in Platforms/iOS. An explicit `--platform android`
creation also generates a locked native Android host; see Platforms/Android.
Android is an unsigned local cross-build, pending device qualification.
SDK installation, Android UI, and signed OTA delivery are still being qualified. A passing host
test is not a mobile release. Do not publish this preview as a qualified SDK.
