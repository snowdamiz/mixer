import MixerAndroidRuntime

func cannotCommit<E: AndroidApplicationEngine>(_ registry: AndroidSessionRegistry<E>) {
    _ = registry.commitV2(1, 1)
}
