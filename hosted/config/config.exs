import Config

config :mixer_hosted, ecto_repos: [MixerHosted.Repo]
config :phoenix, :json_library, Jason

config :mixer_hosted, MixerHostedWeb.Endpoint,
  adapter: Bandit.PhoenixAdapter,
  server: false,
  render_errors: [formats: [json: MixerHostedWeb.ErrorJSON], layout: false],
  debug_errors: false

config :logger, level: :warning
