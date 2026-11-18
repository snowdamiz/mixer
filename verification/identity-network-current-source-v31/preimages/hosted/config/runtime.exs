import Config

# Tests start their own isolated services explicitly with --no-start. Normal
# startup and releases have no fallback credentials, database, or combined role.
if config_env() != :test do
  env = System.get_env()
  settings = MixerHosted.RuntimeConfig.load!(env)
  installation = MixerHosted.BrowserAuth.Installation.load!(env, settings)
  config :mixer_hosted, :startup, {settings, installation}
  config :mixer_hosted, :role, settings.role
  config :mixer_hosted, :identity_startup, settings.identity_startup
  config :mixer_hosted, MixerHosted.Repo, settings.repo
  config :mixer_hosted, Oban, settings.oban
  config :mixer_hosted, MixerHostedWeb.Endpoint, settings.endpoint
end
