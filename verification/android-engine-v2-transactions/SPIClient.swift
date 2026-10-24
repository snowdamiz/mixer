@_spi(MixerNativeAppearanceV2) import MixerAndroidRuntime

func stagedDecision<E: AndroidApplicationEngine>(_ registry: AndroidSessionRegistry<E>, handle: UInt64, token: UInt64) -> Int32 {
    registry.commitV2(handle, token)
}
