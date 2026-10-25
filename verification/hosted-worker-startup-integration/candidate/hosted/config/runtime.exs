import Config

# Tests start their own isolated services explicitly with --no-start. Normal
# startup and releases have no fallback credentials, database, or combined role.
if config_env() != :test do
  settings = MixerHosted.RuntimeConfig.load!(System.get_env())
  config :mixer_hosted, :role, settings.role
  config :mixer_hosted, :identity_startup, settings.identity_startup
  config :mixer_hosted, :build_worker_startup, settings.build_worker_startup
  config :mixer_hosted, :build_dispatch, settings.build_dispatch
  config :mixer_hosted, MixerHosted.Repo, settings.repo
  config :mixer_hosted, Oban, settings.oban
  config :mixer_hosted, MixerHostedWeb.Endpoint, settings.endpoint
end
