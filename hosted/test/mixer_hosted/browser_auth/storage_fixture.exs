unless Code.ensure_loaded?(MixerHosted.BrowserAuth.StorageFixture) do
  Code.require_file("../../support/browser_storage_fixture.ex", __DIR__)
end
