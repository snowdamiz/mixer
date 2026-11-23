@_spi(GuestUIV1) @_spi(PrivateFieldLogEditor) import MixerGuest

func makeInstalledExchange() throws -> GuestUIExchangeV1 {
    #if F11_CONTROL_STOCK
    return try GuestUIExchangeV1(generation: 1, allowsDeferredStartup: true)
    #else
    return try GuestUIExchangeV1(fieldLogNoteFixtureGeneration: 1)
    #endif
}
